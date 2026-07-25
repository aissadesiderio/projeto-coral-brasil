"""NOAA Coral Reef Watch - SST, DHW, HotSpot, anomalia e BAA.

Fonte das tres variaveis mais importantes do projeto: `sst` e `dhw` como
features, e `baa` como target. Acesso publico via ERDDAP, sem credenciais.

Produto: Daily Global 5 km Coral Bleaching Heat Stress v3.1
https://coralreefwatch.noaa.gov/product/5km/

Nota sobre o DHW: usar a coluna `CRW_DHW` oficial, nunca recalcular. O
`carregar_historico.py` calculava um DHW proprio com limiar fixo de 27 °C
somando todos os hotspots positivos - a norma NOAA usa a MMM por pixel e so
acumula hotspots >= 1 °C. Ver docs/VARIAVEIS.md secao 3.2.
"""

import logging

from django.conf import settings

from ..base import ConectorBase, Observacao, ResultadoColeta
from ..erros import resumir_erro
from ..retentativa import TENTATIVAS_PADRAO, executar_com_retentativa

logger = logging.getLogger(__name__)

# Colunas pedidas ao ERDDAP. HOTSPOT e SSTANOMALY entram porque sao baratos e
# uteis para diagnostico - a decisao de usa-los ou nao como feature e do
# modelo, nao da ingestao. Ver docs/VARIAVEIS.md secao 5.
VARIAVEIS_ERDDAP = (
    'CRW_SST',
    'CRW_DHW',
    'CRW_BAA',
    'CRW_HOTSPOT',
    'CRW_SSTANOMALY',
)


# Servidor e dataset padrao. Escolhidos por evidencia, nao por preferencia:
#
# - `coastwatch.pfeg.noaa.gov` + `NOAA_DHW` foi verificado respondendo com as
#   cinco variaveis (incluindo CRW_BAA, o target) em 25/07/2026. E tambem o
#   servidor que o `coleta_de_dados.py` original usava.
# - PACIOOS (`pae-paha.pacioos.hawaii.edu` + `dhw_5km`) gerou os CSVs que o
#   projeto ja tem, mas em 25/07/2026 falhava com CERTIFICATE_VERIFY_FAILED em
#   duas redes independentes - problema de certificado do servidor, nao de
#   bloqueio local.
# - `coastwatch.noaa.gov` + `noaacrwdhwDaily` respondeu 403 nas mesmas redes.
#
# Servidor e dataset SEMPRE andam em par: cada espelho publica o mesmo produto
# sob um id proprio. Use `manage.py testar_fontes` para descobrir o par que
# funciona numa rede nova.
SERVIDOR_PADRAO = 'https://coastwatch.pfeg.noaa.gov/erddap'
DATASET_PADRAO = 'NOAA_DHW'


class ConectorNoaaCrw(ConectorBase):
    slug = 'noaa_crw'
    nome = 'NOAA Coral Reef Watch 5 km v3.1'
    url_fonte = 'https://coralreefwatch.noaa.gov/product/5km/'
    variaveis = ('sst', 'dhw', 'baa', 'hotspot', 'sst_anomalia')
    exige_credenciais = False

    def __init__(
        self, servidor=None, dataset_id=None, cliente=None, tentativas=None, dormir=None
    ):
        self.servidor = servidor or getattr(
            settings, 'NOAA_ERDDAP_SERVER', SERVIDOR_PADRAO
        )
        self.dataset_id = dataset_id or getattr(
            settings, 'NOAA_ERDDAP_DATASET', DATASET_PADRAO
        )
        self.tentativas = tentativas or getattr(
            settings, 'INGESTAO_TENTATIVAS', TENTATIVAS_PADRAO
        )
        # `cliente` e `dormir` existem para injetar dubles nos testes; em
        # producao o conector monta o proprio ERDDAP e espera de verdade.
        self._cliente = cliente
        self._dormir = dormir

    def _montar_cliente(self, bbox, inicio, fim):
        from erddapy import ERDDAP

        lon_min, lat_min, lon_max, lat_max = bbox
        e = ERDDAP(server=self.servidor, protocol='griddap')
        e.dataset_id = self.dataset_id
        e.variables = list(VARIAVEIS_ERDDAP)
        e.constraints = {
            'time>=': inicio.isoformat(),
            'time<=': fim.isoformat(),
            'latitude>=': lat_min,
            'latitude<=': lat_max,
            'longitude>=': lon_min,
            'longitude<=': lon_max,
        }
        return e

    def _buscar(self, bbox, inicio, fim):
        """Uma tentativa completa de busca.

        Montar o cliente faz parte da tentativa, e nao de um passo anterior: o
        erddapy em modo griddap ja faz HTTP no construtor (busca o `.dds` para
        descobrir as dimensoes do dataset). Se o servidor devolver 503 nesse
        momento, reaproveitar um cliente meio construido nao adiantaria.
        """
        cliente = self._cliente or self._montar_cliente(bbox, inicio, fim)
        return cliente.to_pandas()

    def coletar(self, local, inicio, fim):
        try:
            bbox = self.verificar_local(local)
        except ValueError as exc:
            return ResultadoColeta(erro=str(exc), dataset_id=self.dataset_id)

        # O try precisa envolver toda a busca, inclusive a montagem do cliente:
        # deixar qualquer parte de fora faria a falha de rede escapar sem virar
        # ResultadoColeta.
        try:
            argumentos = {'rotulo': f'NOAA CRW ({self.dataset_id})',
                          'tentativas': self.tentativas}
            if self._dormir is not None:
                argumentos['dormir'] = self._dormir

            df = executar_com_retentativa(
                lambda: self._buscar(bbox, inicio, fim), **argumentos
            )
        except Exception as exc:
            # Falha de rede nunca sobe: viraria queda de todo o pipeline.
            resumo = resumir_erro(exc)
            logger.warning('Falha ao coletar do NOAA CRW: %s', resumo)
            logger.debug('Detalhe completo da falha do NOAA CRW', exc_info=exc)
            return ResultadoColeta(erro=resumo, dataset_id=self.dataset_id)

        return self._extrair(df)

    def _extrair(self, df):
        """Converte o DataFrame do ERDDAP em observacoes brutas.

        O produto e uma grade: varios pixels por data dentro da bbox. Agregamos
        por media diaria, que e o valor representativo do recife - a alternativa
        (escolher um pixel) descartaria informacao sem criterio.
        """
        import pandas as pd

        if df is None or len(df) == 0:
            return ResultadoColeta(dataset_id=self.dataset_id)

        # O ERDDAP devolve nomes como "CRW_SST (degree_C)".
        renomeadas = {c: c.split('(')[0].strip() for c in df.columns}
        df = df.rename(columns=renomeadas)

        coluna_tempo = next(
            (c for c in df.columns if c.strip().lower() == 'time'), None
        )
        if coluna_tempo is None:
            return ResultadoColeta(
                erro='Resposta do ERDDAP sem coluna "time".',
                dataset_id=self.dataset_id,
            )

        df[coluna_tempo] = pd.to_datetime(df[coluna_tempo], errors='coerce', utc=True)
        df = df.dropna(subset=[coluna_tempo])
        df['__data'] = df[coluna_tempo].dt.date

        presentes = [c for c in VARIAVEIS_ERDDAP if c in df.columns]
        if not presentes:
            return ResultadoColeta(
                erro=(
                    'Nenhuma variavel esperada na resposta. '
                    f'Colunas recebidas: {list(df.columns)}'
                ),
                dataset_id=self.dataset_id,
            )

        for coluna in presentes:
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce')

        agregado = df.groupby('__data')[presentes].mean()

        observacoes = []
        for data, linha in agregado.iterrows():
            for coluna in presentes:
                valor = linha[coluna]
                observacoes.append(
                    Observacao(
                        data=data,
                        coluna=coluna,
                        valor=None if pd.isna(valor) else float(valor),
                    )
                )

        return ResultadoColeta(
            observacoes=observacoes,
            dataset_id=self.dataset_id,
        )
