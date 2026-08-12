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

🚨 **Este modulo passou a ter DUAS metades, e elas respondem perguntas
diferentes.** A distincao foi o que faltava quando os sete locais novos entraram
(12/08/2026): eles tinham serie ingerida no banco, previsao no painel — e a
pagina de cada um dizia *"Ainda nao ha datasets relacionados a esta
localizacao"*. Nao era bug de tela. O catalogo inteiro descrevia **arquivos**, e
todo arquivo do acervo tinha sido extraido num unico ponto, o Banco dos Abrolhos
(ver `LOCAL_PADRAO` abaixo). Um recife sem CSV proprio em `backend/dados/` nao
tinha como aparecer, por mais medicao que tivesse.

| Metade | Descreve | Cobertura vem de | Vale para |
|---|---|---|---|
| `DATASETS_REAIS` | o arquivo em `backend/dados/` | `ler_metadados_arquivo` | so `abrolhos-ba` |
| `SERIES_INGERIDAS` | a serie em `MedicaoAmbiental` | o proprio banco | todo local ingerido |

⚠️ **A segunda metade nao substitui a primeira, e nem poderia.** Metade dos
arquivos catalogados (pH, nitrato, thetao, clorofila, KD490) sao variaveis que a
ingestao **nao** grava: eles so existem como arquivo. Apagar a primeira metade
perderia esse acervo do catalogo; apagar a segunda devolveria os sete locais ao
vazio. As duas convivem, e `DatasetCatalogo.fonte_medicao` continua sendo o que
diz, item a item, se o projeto **serve** aquilo ou apenas **aponta** para ele.
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

    # 🚨 Vinculo com o que o projeto **serve pela API**, acrescentado em
    # 27/07/2026. Medido: a pagina anunciava os nove datasets abaixo, e o banco
    # tinha medicao de **tres**. Os outros seis apareciam com titulo, formato e
    # periodo sem uma unica linha em `MedicaoAmbiental`.
    #
    # ⚠️ **O periodo lido do CSV nao e a cobertura da API.** Ele descreve o
    # arquivo em `backend/dados/`, uma pasta legada que nada mais le e que o
    # roadmap manda apagar. Enquanto ela existir, os dois convivem — mas quem
    # responde "ate quando o projeto tem dado" e `aquaculture/cobertura.py`,
    # derivando do banco.
    #
    # Vazio = referencia externa: legitimo num catalogo, desde que declarado.
    fonte_medicao: str = ''
    variaveis_medicao: str = ''

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
        fonte_medicao='noaa_crw',
        variaveis_medicao='sst,sst_anomalia,hotspot,dhw,baa,baa_area_alerta',
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
        fonte_medicao='copernicus',
        variaveis_medicao='salinidade',
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
        fonte_medicao='copernicus',
        variaveis_medicao='oxigenio',
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

    # --- acrescentados em 28/07/2026, ao auditar os arquivos orfaos ---------
    #
    # Estes sete existiam sem estar nem catalogados nem excluidos: ninguem os
    # tinha aberto. A regra que a secao 6.14 deixou e clara — nao se decide
    # sobre arquivo pelo nome —, entao cada um foi lido antes de sair.
    'cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m_1764629291619.csv': (
        'Duplicata de valor do arquivo de pH ja catalogado (..._1764629137159): '
        'MD5 diferente pelo cabecalho, mas os 1.501 valores sao identicos em '
        'todas as datas.'
    ),
    'clorofila_recente.csv': (
        'Produto de analise, enquanto clorofila.csv e reanalise. Sobrepoem '
        '1.501 datas com diferenca de ate 0,0044 mg/m3 - nao e duplicata, e a '
        'mistura que a secao 6.11 registra. Nenhum dos dois entra no modelo.'
    ),
    'nitrato_recente.csv': (
        'Mesmo caso: analise contra a reanalise de nitrato.csv, sobrepondo '
        '1.430 datas com diferenca de ate 0,235 mmol/m3 - divergencia grande '
        'para a mesma data e o mesmo ponto. Ver secao 6.11.'
    ),
    'cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m_1764629196586.csv': (
        'Contem dissic (carbono inorganico dissolvido), variavel que o projeto '
        'nao usa e que nao tem nome canonico.'
    ),
    'cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m_1764629434573.csv': (
        'Contem nppv (produtividade primaria liquida), nunca avaliada.'
    ),
    'cmems_mod_glo_bgc-co2_anfc_0.25deg_P1D-m_1764629112534.csv': (
        'Contem spco2 (pressao parcial de CO2 na superficie), nunca avaliada.'
    ),
    'cmems_mod_glo_phy_anfc_0.083deg_PT1H-m_1764628183519.csv': (
        'Contem thetao horario a 13,47 m. O vocabulario canonico recusa thetao '
        'desde 28/07/2026 justamente por nao ser temperatura de superficie - '
        'ver ingestao/normalizacao.py::COLUNAS_RECUSADAS.'
    ),
}


# ---------------------------------------------------------------------------
# Segunda metade: a serie que a ingestao grava, catalogada por local.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SerieIngerida:
    """Um conector, descrito como o conjunto de dados que ele produz por local.

    Nao ha `arquivo` aqui, e a ausencia e o ponto: o que se cataloga e a serie
    no banco, nao uma copia dela em disco.

    ⚠️ **`variaveis_medicao` fica vazio de proposito.** `cobertura.py` le vazio
    como "todas as variaveis desta fonte", e e isso que se quer: o conector
    define quais variaveis produz, e repetir a lista aqui criaria uma segunda
    declaracao para divergir da primeira. Foi exatamente assim que a cobertura
    gravada a mao envelheceu em 27/07/2026.
    """

    fonte_medicao: str
    titulo: str
    fonte: str
    tipo_dado: str
    produto: str
    dataset_id: str
    url_fonte: str
    descricao: str
    ordem: int = 0
    ressalvas: tuple = field(default=())

    def resumo(self, local):
        partes = [
            self.descricao,
            f'Extraida na caixa de {local.nome} ({local.latitude}, '
            f'{local.longitude}).',
            f'Produto: {self.produto} (dataset {self.dataset_id}).',
            f'Fonte oficial: {self.url_fonte}',
        ]
        if self.ressalvas:
            partes.append('Ressalvas: ' + ' '.join(self.ressalvas))
        partes.append(
            'O download sai do proprio banco deste projeto, com as colunas de '
            'proveniencia (fonte, dataset_id, quality_flag) em cada linha.'
        )
        return ' '.join(partes)


SERIES_INGERIDAS = [
    SerieIngerida(
        fonte_medicao='noaa_crw',
        titulo='Estresse termico coralino (CoralTemp/DHW)',
        fonte='NOAA',
        tipo_dado='Oceanografico',
        produto='Daily Global 5 km Coral Bleaching Heat Stress v3.1',
        dataset_id='dhw_5km',
        url_fonte=URL_CRW,
        descricao=(
            'Serie diaria de temperatura da superficie do mar e das metricas '
            'oficiais de estresse termico (anomalia, HotSpot, DHW, BAA) '
            'agregadas dos pixels de 5 km que cobrem o recife.'
        ),
        ressalvas=(
            'O BAA e agregado por maximo, e nao por media - e categoria '
            'ordinal. A fracao da area em alerta vai na serie ao lado. '
            'Ver docs/VARIAVEIS.md secao 4.5.',
        ),
        ordem=10,
    ),
    SerieIngerida(
        fonte_medicao='copernicus',
        titulo='Salinidade e oxigenio dissolvido',
        fonte='Copernicus',
        tipo_dado='Biogeoquimico',
        produto='GLOBAL_ANALYSISFORECAST_PHY_001_024 e GLOBAL_MULTIYEAR_BGC_001_029',
        dataset_id='cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i, cmems_mod_glo_bgc_my_0.25deg_P1D-m',
        url_fonte=URL_CMEMS,
        descricao=(
            'As duas variaveis nao termicas do baseline do modelo, extraidas '
            'diariamente na caixa do recife.'
        ),
        ressalvas=(
            'O oxigenio vem de reanalise e a salinidade de analise/previsao - '
            'produtos diferentes, com latencias diferentes.',
        ),
        ordem=11,
    ),
]

# O endpoint que devolve exatamente esta serie, em CSV, sem paginacao.
#
# 🚨 **E o primeiro `url_download` do catalogo que aponta para este projeto**, e
# nao para o provedor. Ate aqui todo link do catalogo levava a NOAA ou ao
# Copernicus - ou seja, um banco de dados que nao oferecia forma de baixar o que
# ele mesmo guarda. Ver a nota de `formato=csv` em `views.MedicaoAmbientalList`.
#
# ⚠️ Exige conta aprovada, e por isso todo registro desta metade sai com
# `download_exige_conta=True`.
FORMATO_URL_DOWNLOAD = '/api/medicoes/?local={slug}&fonte={fonte}&formato=csv'


def construir_inventario_das_series(medicoes=None):
    """Uma entrada por (local, fonte) que exista **de fato** em `MedicaoAmbiental`.

    🚨 **Par sem medicao nao vira registro** - nem mesmo desativado. E a regra 2
    do topo deste modulo aplicada ao banco em vez do disco, e ela e o que impede
    a volta do defeito de 27/07/2026: um catalogo que anuncia dez recifes
    enquanto o banco tem oito. Os dois locais sem coordenada
    (`apa-costa-dos-corais`, `recife-de-fora-ba`) caem aqui por consequencia, e
    nao por excecao escrita a mao - eles nao entram na ingestao, entao nao tem
    medicao, entao nao tem dataset.

    `medicoes` e o retorno de `cobertura.resumo()`. Passe-o quando ja tiver.
    """
    from . import cobertura
    from .models import LocalRecife

    if medicoes is None:
        medicoes = cobertura.resumo()

    por_fonte = {serie.fonte_medicao: serie for serie in SERIES_INGERIDAS}
    locais = {local.slug: local for local in LocalRecife.objects.all()}

    # `cobertura.resumo()` agrupa por (fonte, variavel, local); aqui a variavel
    # nao interessa - o dataset e a serie inteira daquela fonte no recife.
    pares = sorted(
        {
            (fonte, slug)
            for (fonte, _variavel, slug) in medicoes
            if fonte in por_fonte and slug in locais
        }
    )

    registros = []
    for fonte, slug in pares:
        serie = por_fonte[fonte]
        local = locais[slug]
        registros.append(
            {
                'id': f'serie-{fonte}-{slug}',
                'defaults': {
                    'titulo': f'{serie.titulo} - {local.nome}',
                    'resumo': serie.resumo(local),
                    'fonte': serie.fonte,
                    'tipo_dado': serie.tipo_dado,
                    'formato': 'CSV',
                    'localizacao': local.nome,
                    'local_slug': local.slug,
                    'estado': local.estado,
                    'cidade': local.cidade,
                    'recorte_temporal': 'intervalo',
                    # ⚠️ Nulos de proposito. Estes dois campos descrevem o
                    # **arquivo** de origem (ver o comentario em cobertura.py),
                    # e esta metade do catalogo nao tem arquivo. O periodo real
                    # sai derivado do banco, no bloco `cobertura` do serializer,
                    # e gravar uma copia dele aqui seria reintroduzir a
                    # cobertura a mao que envelheceu em 27/07/2026.
                    'data_inicio': None,
                    'data_fim': None,
                    'periodo_rotulo': 'Derivado do banco - ver cobertura',
                    'tamanho_mb': None,
                    'url_download': FORMATO_URL_DOWNLOAD.format(
                        slug=local.slug, fonte=fonte,
                    ),
                    'download_exige_conta': True,
                    'fonte_medicao': fonte,
                    'variaveis_medicao': '',
                    'ordem_exibicao': serie.ordem,
                    'ativo': True,
                },
            }
        )

    return registros


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
                    'download_exige_conta': False,
                        'fonte_medicao': fonte.fonte_medicao,
                        'variaveis_medicao': fonte.variaveis_medicao,
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
                    'download_exige_conta': False,
                    'fonte_medicao': fonte.fonte_medicao,
                        'variaveis_medicao': fonte.variaveis_medicao,
                        'ordem_exibicao': fonte.ordem,
                    'ativo': True,
                },
            }
        )

    return registros, ausentes
