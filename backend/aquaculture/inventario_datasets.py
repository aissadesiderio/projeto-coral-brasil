"""Inventario real dos conjuntos de dados que o projeto possui.

Substitui o seed ficticio de `0014_seed_datasetcatalogo`, que cadastrava 8
datasets inventados (inclusive dois atribuidos ao NCBI, fonte da qual o
projeto nao tem um unico byte). Ver docs/FONTES.md, secao 6.14.

Regras deste modulo:

1. **Nada e inventado.** Tamanho e periodo sao lidos do arquivo real no
   momento do inventario, nunca digitados aqui.
2. **Arquivo ausente nao vira registro.** Se o CSV nao esta em backend/dados/,
   o dataset e desativado em vez de aparecer como disponivel.
3. **Nada de download falso.** `url_download` fica vazio porque o projeto nao
   serve esses arquivos; a origem e declarada no resumo. Quando existir um
   endpoint real de download (Fase D), o campo passa a ser preenchido.
4. **Arquivos com problema de integridade ficam de fora**, com o motivo
   registrado em `EXCLUIDOS` - eles existem no disco, mas nao sao dados
   publicaveis. Ver docs/FONTES.md secao 6.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from django.conf import settings

# Todos os arquivos abaixo foram extraidos em pontos proximos a
# -38,71 / -17,97, ou seja, o Banco dos Abrolhos.
LOCAL_PADRAO = 'abrolhos-ba'


@dataclass(frozen=True)
class FonteDataset:
    """Metadados de proveniencia de um conjunto de dados real."""

    id: str
    arquivo: str
    titulo: str
    fonte: str
    tipo_dado: str
    variavel: str
    produto: str
    dataset_id: str
    url_fonte: str
    descricao: str
    formato: str = 'CSV'
    local_slug: str = LOCAL_PADRAO
    ordem: int = 0
    ressalvas: tuple = field(default=())

    def resumo(self):
        partes = [
            self.descricao,
            f'Variavel: {self.variavel}.',
            f'Produto: {self.produto} (dataset {self.dataset_id}).',
            f'Fonte oficial: {self.url_fonte}',
        ]
        if self.ressalvas:
            partes.append('Ressalvas: ' + ' '.join(self.ressalvas))
        partes.append(
            'Arquivo mantido localmente para processamento; o projeto ainda '
            'nao oferece download direto.'
        )
        return ' '.join(partes)


URL_CMEMS = 'https://marine.copernicus.eu'
URL_CRW = 'https://coralreefwatch.noaa.gov/product/5km/'

DATASETS_REAIS = [
    FonteDataset(
        id='noaa_crw_dhw_abrolhos',
        arquivo='dhw.csv',
        titulo='Estresse termico coralino (CoralTemp/DHW) - Abrolhos',
        fonte='NOAA',
        tipo_dado='Oceanografico',
        variavel='CRW_SST, CRW_SSTANOMALY, CRW_HOTSPOT, CRW_DHW, CRW_BAA',
        produto='Daily Global 5 km Coral Bleaching Heat Stress v3.1',
        dataset_id='dhw_5km',
        url_fonte=URL_CRW,
        descricao=(
            'Grade diaria de 5 km com temperatura da superficie do mar e as '
            'metricas oficiais de estresse termico usadas para alerta de '
            'branqueamento.'
        ),
        ordem=1,
    ),
    FonteDataset(
        id='metoffice_sst_l4_abrolhos',
        arquivo='sst.csv',
        titulo='Temperatura da superficie do mar (serie historica) - Abrolhos',
        fonte='Met Office / Copernicus',
        tipo_dado='Climatico',
        variavel='analysed_sst',
        produto='SST_GLO_SST_L4_REP_OBSERVATIONS_010_011',
        dataset_id='METOFFICE-GLO-SST-L4-REP-OBS-SST',
        url_fonte=URL_CMEMS,
        descricao=(
            'Serie reprocessada de temperatura da superficie do mar, a mais '
            'longa do acervo do projeto.'
        ),
        ressalvas=(
            'O cabecalho declara kelvin mas os valores estao em graus Celsius; '
            'confirmar a unidade antes de usar.',
        ),
        ordem=2,
    ),
    FonteDataset(
        id='cmems_thetao_abrolhos',
        arquivo='temperatura.csv',
        titulo='Temperatura potencial da agua do mar - Abrolhos',
        fonte='Copernicus',
        tipo_dado='Oceanografico',
        variavel='thetao',
        produto='GLOBAL_ANALYSISFORECAST_PHY_001_024',
        dataset_id='cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m',
        url_fonte=URL_CMEMS,
        descricao='Temperatura potencial diaria da agua do mar.',
        ressalvas=('Extraida a 13,47 m de profundidade, nao em superficie.',),
        ordem=3,
    ),
    FonteDataset(
        id='cmems_salinidade_abrolhos',
        arquivo='salinidade.csv',
        titulo='Salinidade da agua do mar - Abrolhos',
        fonte='Copernicus',
        tipo_dado='Oceanografico',
        variavel='so',
        produto='GLOBAL_ANALYSISFORECAST_PHY_001_024',
        dataset_id='cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i',
        url_fonte=URL_CMEMS,
        descricao='Salinidade pratica em intervalos de 6 horas.',
        ordem=4,
    ),
    FonteDataset(
        id='cmems_clorofila_abrolhos',
        arquivo='clorofila.csv',
        titulo='Clorofila-a - Abrolhos',
        fonte='Copernicus',
        tipo_dado='Biogeoquimico',
        variavel='chl',
        produto='GLOBAL_ANALYSISFORECAST_BGC_001_028',
        dataset_id='cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m',
        url_fonte=URL_CMEMS,
        descricao=(
            'Concentracao de clorofila-a, usada como indicador de produtividade '
            'e de sombreamento sobre o recife.'
        ),
        ordem=5,
    ),
    FonteDataset(
        id='cmems_ph_abrolhos',
        arquivo='cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m_1764629137159.csv',
        titulo='pH da agua do mar - Abrolhos',
        fonte='Copernicus',
        tipo_dado='Biogeoquimico',
        variavel='ph',
        produto='GLOBAL_ANALYSISFORECAST_BGC_001_028',
        dataset_id='cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m',
        url_fonte=URL_CMEMS,
        descricao=(
            'pH em escala total, indicador de acidificacao. Este e o arquivo '
            'de pH de fato - nao confundir com dados/ph.csv, que contem '
            'alcalinidade.'
        ),
        ordem=6,
    ),
    FonteDataset(
        id='cmems_oxigenio_abrolhos',
        arquivo='oxigenio.csv',
        titulo='Oxigenio dissolvido - Abrolhos',
        fonte='Copernicus',
        tipo_dado='Biogeoquimico',
        variavel='o2',
        produto='GLOBAL_MULTIYEAR_BGC_001_029 (reanalise)',
        dataset_id='cmems_mod_glo_bgc_my_0.25deg_P1D-m',
        url_fonte=URL_CMEMS,
        descricao='Concentracao de oxigenio dissolvido na agua do mar.',
        ressalvas=(
            'Produto de reanalise, nao de previsao - nao misturar com as '
            'series *_recente sem registrar a diferenca.',
        ),
        ordem=7,
    ),
    FonteDataset(
        id='cmems_nitrato_abrolhos',
        arquivo='nitrato.csv',
        titulo='Nitrato - Abrolhos',
        fonte='Copernicus',
        tipo_dado='Biogeoquimico',
        variavel='no3',
        produto='GLOBAL_MULTIYEAR_BGC_001_029 (reanalise)',
        dataset_id='cmems_mod_glo_bgc_my_0.25deg_P1D-m',
        url_fonte=URL_CMEMS,
        descricao='Concentracao de nitrato, usada como indicador de aporte de nutrientes.',
        ressalvas=('Produto de reanalise, nao de previsao.',),
        ordem=8,
    ),
    FonteDataset(
        id='cmems_kd490_abrolhos',
        arquivo='turbidez.csv',
        titulo='Atenuacao da luz (Kd) - Abrolhos',
        fonte='Copernicus',
        tipo_dado='Biogeoquimico',
        variavel='kd',
        produto='GLOBAL_ANALYSISFORECAST_BGC_001_028',
        dataset_id='cmems_mod_glo_bgc-optics_anfc_0.25deg_P1D-m',
        url_fonte=URL_CMEMS,
        descricao=(
            'Coeficiente de atenuacao da luz descendente - medida direta de '
            'turbidez, que substitui a estimativa derivada de clorofila.'
        ),
        ordem=9,
    ),
]

# Arquivos que existem em backend/dados/ mas nao entram no catalogo publico.
# Mantidos aqui para que a exclusao seja uma decisao registrada, nao um
# esquecimento. Detalhes em docs/FONTES.md, secao 6.
EXCLUIDOS = {
    'ph.csv': 'Contem alcalinidade (talk), nao pH - rotulo do arquivo engana.',
    'NOAA_DHW_monthly_1c77_436e_401f.csv': (
        'Coordenadas no hemisferio errado (18,975 N / 38,025 E = Mar Vermelho).'
    ),
    'par.csv': (
        'Valores existem (63,3% preenchidos) mas latitude/longitude sairam com '
        'separador de milhar (-17.187.504) e nao convertem para float - dados '
        'nao georreferenciaveis.'
    ),
    'par_recente.csv': 'Contem PAR_error (campo de incerteza), nao PAR.',
    'dhw_5km_6006_cdf9_04d9.csv': 'Duplicata byte-a-byte de dhw.csv.',
    'turbidez_recente.csv': 'Duplicata byte-a-byte de turbidez.csv.',
    'salinidade_recente.csv': 'Contem sob (salinidade no fundo), nao em superficie.',
}


def caminho_dados():
    return Path(settings.BASE_DIR) / 'dados'


def ler_metadados_arquivo(caminho):
    """Le tamanho real e intervalo temporal real de um CSV.

    Retorna (tamanho_mb, data_inicio, data_fim) ou None se o arquivo nao
    existir. Datas vem como `datetime.date` ou None quando nao houver coluna
    de tempo legivel.
    """
    if not caminho.exists():
        return None

    tamanho_mb = round(caminho.stat().st_size / (1024 * 1024), 2)

    try:
        df = pd.read_csv(
            caminho,
            comment='#',
            usecols=lambda c: c.strip().lower() == 'time',
            low_memory=False,
        )
        tempos = pd.to_datetime(df.iloc[:, 0], errors='coerce', utc=True).dropna()
        if tempos.empty:
            return tamanho_mb, None, None
        return tamanho_mb, tempos.min().date(), tempos.max().date()
    except Exception:
        # Arquivo ilegivel ainda tem tamanho real; o periodo fica indefinido.
        return tamanho_mb, None, None


def _rotulo_periodo(inicio, fim):
    if inicio and fim:
        return f'{inicio.year}-{fim.year}' if inicio.year != fim.year else str(inicio.year)
    return 'Periodo nao determinado'


def construir_inventario(local=None):
    """Monta os registros do catalogo a partir dos arquivos reais.

    Retorna (registros, ausentes). Cada registro e um dict pronto para
    `DatasetCatalogo.objects.update_or_create`.
    """
    base = caminho_dados()
    registros = []
    ausentes = []

    for fonte in DATASETS_REAIS:
        metadados = ler_metadados_arquivo(base / fonte.arquivo)

        if metadados is None:
            ausentes.append(fonte)
            registros.append(
                {
                    'id': fonte.id,
                    'defaults': {
                        'titulo': fonte.titulo,
                        'resumo': (
                            f'{fonte.resumo()} ARQUIVO AUSENTE em backend/dados/'
                            f'{fonte.arquivo} - registro desativado.'
                        ),
                        'fonte': fonte.fonte,
                        'tipo_dado': fonte.tipo_dado,
                        'formato': fonte.formato,
                        'localizacao': local.nome if local else '',
                        'local_slug': fonte.local_slug,
                        'estado': local.estado if local else '',
                        'cidade': local.cidade if local else '',
                        'recorte_temporal': 'intervalo',
                        'data_inicio': None,
                        'data_fim': None,
                        'periodo_rotulo': 'Indisponivel',
                        'tamanho_mb': None,
                        'url_download': '',
                        'ordem_exibicao': fonte.ordem,
                        'ativo': False,
                    },
                }
            )
            continue

        tamanho_mb, inicio, fim = metadados
        registros.append(
            {
                'id': fonte.id,
                'defaults': {
                    'titulo': fonte.titulo,
                    'resumo': fonte.resumo(),
                    'fonte': fonte.fonte,
                    'tipo_dado': fonte.tipo_dado,
                    'formato': fonte.formato,
                    'localizacao': local.nome if local else '',
                    'local_slug': fonte.local_slug,
                    'estado': local.estado if local else '',
                    'cidade': local.cidade if local else '',
                    'recorte_temporal': 'intervalo',
                    'data_inicio': inicio,
                    'data_fim': fim,
                    'periodo_rotulo': _rotulo_periodo(inicio, fim),
                    'tamanho_mb': tamanho_mb,
                    'url_download': '',
                    'ordem_exibicao': fonte.ordem,
                    'ativo': True,
                },
            }
        )

    return registros, ausentes
