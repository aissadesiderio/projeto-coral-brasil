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


# Servidor e dataset padrao: o par que comprovadamente produziu os dados que o
# projeto ja tem em maos. O arquivo dados/dhw_5km_6006_cdf9_04d9.csv veio deste
# dataset - o sufixo do nome e o identificador de consulta do ERDDAP do
# PACIOOS - e suas colunas sao exatamente as cinco de VARIAVEIS_ERDDAP.
#
# O espelho da NOAA (coastwatch.noaa.gov/erddap) serve o mesmo produto sob o
# dataset_id `noaacrwdhwDaily`. Para usa-lo, ajuste as duas variaveis de
# ambiente juntas - servidor e dataset_id andam em par.
SERVIDOR_PADRAO = 'https://pae-paha.pacioos.hawaii.edu/erddap'
DATASET_PADRAO = 'dhw_5km'


class ConectorNoaaCrw(ConectorBase):
    slug = 'noaa_crw'
    nome = 'NOAA Coral Reef Watch 5 km v3.1'
    url_fonte = 'https://coralreefwatch.noaa.gov/product/5km/'
    variaveis = ('sst', 'dhw', 'baa', 'hotspot', 'sst_anomalia')
    exige_credenciais = False

    def __init__(self, servidor=None, dataset_id=None, cliente=None):
        self.servidor = servidor or getattr(
            settings, 'NOAA_ERDDAP_SERVER', SERVIDOR_PADRAO
        )
        self.dataset_id = dataset_id or getattr(
            settings, 'NOAA_ERDDAP_DATASET', DATASET_PADRAO
        )
        # `cliente` existe para injetar um duble nos testes; em producao o
        # conector monta o proprio ERDDAP.
        self._cliente = cliente

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

    def coletar(self, local, inicio, fim):
        try:
            bbox = self.verificar_local(local)
        except ValueError as exc:
            return ResultadoColeta(erro=str(exc), dataset_id=self.dataset_id)

        # A construcao do cliente precisa estar dentro do try: o erddapy em
        # modo griddap faz uma requisicao HTTP ja no construtor (busca o .dds
        # para descobrir as dimensoes do dataset). Monta-la fora deixaria a
        # falha de rede escapar sem virar ResultadoColeta.
        try:
            cliente = self._cliente or self._montar_cliente(bbox, inicio, fim)
            df = cliente.to_pandas()
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
