"""Copernicus Marine Service - salinidade e oxigenio dissolvido.

Duas decisoes desta fonte precisam ficar visiveis, porque nenhuma e obvia
olhando so o codigo.

**1. Cada serie emenda dois produtos.** A reanalise (`*_my_*`) cobre 1993 em
diante mas para cerca de um mes atras; a analise/previsao (`*_anfc_*`) comeca
em 2021-2022 e vai ate hoje. Nenhum dos dois sozinho cobre a serie do projeto
(2020 ate agora). O conector usa a reanalise onde ela existe - e o produto
melhor, ja reprocessado - e completa o resto com a analise. Cada medicao grava
o `dataset_id` de onde saiu, entao a costura fica rastreavel valor a valor.

**2. Nada de previsao entra no banco.** Os produtos `anfc` publicam alguns dias
**no futuro**: em 25/07/2026 o catalogo ia ate 2026-08-04. Sao valores
previstos, nao medidos. Grava-los como medicao seria vazamento direto num
modelo com horizonte de N dias - o modelo aprenderia com a previsao do proprio
fenomeno que deve prever. O corte e sempre em ontem.

KD490 (`kd`) existe aqui mas **fora do baseline**, por decisao de 25/07/2026:
so ha dado de 2023-11-15 em diante e nao existe reanalise, o que cortaria o
treino de 6,5 para 2,7 anos e apagaria o evento de branqueamento de 2020. Ver
docs/VARIAVEIS.md secao 3.5. Fica disponivel para o experimento no subperiodo.

Cobertura medida no catalogo real em 25/07/2026 (`copernicusmarine.describe`).
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings

from ..base import ConectorBase, Observacao, PeriodoIndisponivel, ResultadoColeta
from ..erros import resumir_erro
from ..retentativa import TENTATIVAS_PADRAO, executar_com_retentativa

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FonteCmems:
    """Um dataset do CMEMS que publica uma variavel."""

    dataset_id: str
    variavel: str
    tipo: str  # 'reanalise' ou 'analise'


# Ordem importa: a reanalise vem primeiro e tem precedencia no periodo em que
# as duas se sobrepoem.
SERIES = {
    'salinidade': (
        FonteCmems('cmems_mod_glo_phy_my_0.083deg_P1D-m', 'so', 'reanalise'),
        FonteCmems('cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m', 'so', 'analise'),
    ),
    'oxigenio': (
        FonteCmems('cmems_mod_glo_bgc_my_0.25deg_P1D-m', 'o2', 'reanalise'),
        FonteCmems('cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m', 'o2', 'analise'),
    ),
    'kd490': (
        FonteCmems('cmems_mod_glo_bgc-optics_anfc_0.25deg_P1D-m', 'kd', 'analise'),
    ),
}

SERIES_PADRAO = ('salinidade', 'oxigenio')

# Camada de superficie. Os produtos globais tem o primeiro nivel em ~0,494 m;
# pedir de 0 a 1 m pega esse nivel e so ele.
PROFUNDIDADE_MAX_M = 1.0

# Dimensoes agregadas por media. Todas continuas - ao contrario do BAA do NOAA,
# aqui a media espacial e a operacao certa.
DIMENSOES_AGREGADAS = ('latitude', 'longitude', 'depth', 'elevation')


def ultimo_dia_permitido(hoje=None):
    """Ontem. Nunca hoje, nunca o futuro.

    Os produtos `anfc` publicam previsao alem da data corrente, e o dia
    corrente costuma estar incompleto.
    """
    return (hoje or date.today()) - timedelta(days=1)


def _como_data(valor):
    """Converte um instante do xarray em `date`."""
    import pandas as pd

    return pd.Timestamp(valor).date()


class ConectorCopernicus(ConectorBase):
    slug = 'copernicus'
    nome = 'Copernicus Marine Service'
    url_fonte = 'https://data.marine.copernicus.eu'
    variaveis = ('salinidade', 'oxigenio')
    exige_credenciais = True

    def __init__(self, series=None, tentativas=None, dormir=None, abrir=None):
        self.series = tuple(series or getattr(
            settings, 'COPERNICUS_SERIES', SERIES_PADRAO
        ))

        desconhecidas = [s for s in self.series if s not in SERIES]
        if desconhecidas:
            raise ValueError(
                f'Serie(s) desconhecida(s): {desconhecidas}. '
                f'Disponiveis: {sorted(SERIES)}.'
            )

        self.tentativas = tentativas or getattr(
            settings, 'INGESTAO_TENTATIVAS', TENTATIVAS_PADRAO
        )
        self._dormir = dormir
        # `abrir` existe para injetar um duble nos testes: a alternativa seria
        # nao cobrir nada do planejamento da emenda sem bater na rede.
        self._abrir = abrir or self._abrir_cmems

    def _abrir_cmems(self, fonte, bbox):
        """Abre o dataset preguicosamente, sem recortar o tempo ainda.

        O recorte temporal vem depois porque o periodo util depende da
        cobertura real do dataset, que so se conhece com ele aberto.
        """
        import copernicusmarine

        lon_min, lat_min, lon_max, lat_max = bbox
        return copernicusmarine.open_dataset(
            dataset_id=fonte.dataset_id,
            variables=[fonte.variavel],
            minimum_longitude=lon_min,
            maximum_longitude=lon_max,
            minimum_latitude=lat_min,
            maximum_latitude=lat_max,
            minimum_depth=0,
            maximum_depth=PROFUNDIDADE_MAX_M,
        )

    def _observacoes_de(self, fonte, bbox, inicio, fim):
        """Coleta um trecho de uma serie. Devolve (observacoes, ultima_data).

        `ultima_data` e o fim da cobertura do dataset, nao do trecho - quem
        chama usa isso para saber onde a proxima fonte deve continuar.
        """
        ds = self._abrir(fonte, bbox)

        disponivel_ate = _como_data(ds.time.values[-1])
        disponivel_de = _como_data(ds.time.values[0])

        recorte_inicio = max(inicio, disponivel_de)
        recorte_fim = min(fim, disponivel_ate)
        if recorte_inicio > recorte_fim:
            return [], disponivel_ate

        serie = ds[fonte.variavel].sel(
            time=slice(recorte_inicio.isoformat(), recorte_fim.isoformat())
        )
        dimensoes = [d for d in DIMENSOES_AGREGADAS if d in serie.dims]
        if dimensoes:
            serie = serie.mean(dim=dimensoes, skipna=True)

        quadro = serie.to_dataframe().reset_index()

        observacoes = []
        for _, linha in quadro.iterrows():
            valor = linha[fonte.variavel]
            observacoes.append(
                Observacao(
                    data=_como_data(linha['time']),
                    coluna=fonte.variavel,
                    valor=None if valor != valor else float(valor),  # NaN
                    dataset_id=fonte.dataset_id,
                )
            )

        return observacoes, disponivel_ate

    def _coletar_serie(self, nome_serie, bbox, inicio, fim):
        """Percorre as fontes da serie ate cobrir o periodo pedido."""
        observacoes = []
        usados = []
        restante = inicio

        for fonte in SERIES[nome_serie]:
            if restante > fim:
                break

            trecho, disponivel_ate = self._observacoes_de(
                fonte, bbox, restante, fim
            )
            if trecho:
                observacoes.extend(trecho)
                usados.append(f'{nome_serie}:{fonte.tipo}')
                # A proxima fonte continua de onde esta parou.
                restante = max(restante, disponivel_ate + timedelta(days=1))

        return observacoes, usados

    def coletar(self, local, inicio, fim):
        try:
            bbox = self.verificar_local(local)
        except ValueError as exc:
            return ResultadoColeta(erro=str(exc))

        notas = []
        limite = ultimo_dia_permitido()
        if fim > limite:
            notas.append(
                f'Periodo encolhido de {fim.isoformat()} para {limite.isoformat()}: '
                'os produtos de analise publicam previsao alem de hoje, e '
                'previsao nao entra como medicao.'
            )
            fim = limite

        if inicio > fim:
            return ResultadoColeta(
                nota=(
                    f'Nada a coletar: o periodo pedido comeca depois de '
                    f'{limite.isoformat()}, o ultimo dia aceito.'
                )
            )

        try:
            argumentos = {
                'rotulo': 'Copernicus Marine',
                'tentativas': self.tentativas,
            }
            if self._dormir is not None:
                argumentos['dormir'] = self._dormir

            observacoes, usados = executar_com_retentativa(
                lambda: self._coletar_tudo(bbox, inicio, fim), **argumentos
            )
        except PeriodoIndisponivel as exc:
            return ResultadoColeta(nota=str(exc))
        except Exception as exc:
            resumo = resumir_erro(exc)
            logger.warning('Falha ao coletar do Copernicus: %s', resumo)
            logger.debug('Detalhe completo da falha do Copernicus', exc_info=exc)
            return ResultadoColeta(erro=resumo)

        if usados:
            notas.append('Datasets usados: ' + ', '.join(sorted(set(usados))))

        return ResultadoColeta(observacoes=observacoes, nota=' | '.join(notas))

    def _coletar_tudo(self, bbox, inicio, fim):
        observacoes, usados = [], []
        for nome_serie in self.series:
            trecho, fontes = self._coletar_serie(nome_serie, bbox, inicio, fim)
            observacoes.extend(trecho)
            usados.extend(fontes)
        return observacoes, usados
