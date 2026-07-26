"""Montagem do conjunto supervisionado da entrega 1.

Traduz `MedicaoAmbiental` (formato longo: uma linha por variavel, por dia, por
local) na tabela que o modelo consome: **features em `t`, alvo em `t + N`**.

Este modulo e o portao da entrega 1 inteira, porque e onde a regra 2 da
docs/VARIAVEIS.md secao 4 vira codigo - *nenhuma janela pode conter informacao
posterior a `t`*. Tres decisoes aqui existem so para impedir vazamento, e
nenhuma delas e obvia lendo o resultado:

**1. A serie e reindexada para dias corridos antes de deslocar.** O produto do
CRW tem 6 datas ausentes, tres delas consecutivas (04-06/07/2024). Sobre as
linhas como vieram do banco, `shift(-7)` andaria *sete posicoes*, nao sete
dias: atravessando a lacuna de julho de 2024 ele pareria `t` com `t+10` e
gravaria isso como se fosse horizonte 7. O modelo aprenderia um horizonte que
nao existe. Com o indice completo, o dia faltante vira NaN e a amostra e
descartada.

**2. Amostra com lacuna e descartada, nunca interpolada.** Interpolar o alvo
seria inventar o rotulo - o modelo estaria aprendendo a prever a nossa
interpolacao. Para as features vale o mesmo: preencher lacuna com media ou
zero foi exatamente o defeito do `carregar_historico.py` legado.

**3. Variaveis derivadas do alvo sao recusadas na construcao**, e nao por
convencao de quem chama. Ver `PROIBIDAS_COMO_FEATURE`.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from aquaculture.models import MedicaoAmbiental
from ingestao.conectores.noaa_crw import LIMIAR_ALERTA

# As features do baseline, conforme docs/VARIAVEIS.md secao 1. KD490 saiu por
# so existir de 2023-11 em diante e nao ter reanalise (secao 3.5).
FEATURES_PADRAO = ('sst', 'dhw', 'salinidade', 'oxigenio')

ALVO_PADRAO = 'baa'

# Horizontes a testar. N e parametro do experimento, nunca constante escondida.
HORIZONTES = (7, 14, 30)

# Variaveis que nao podem entrar como feature de um modelo que preve `baa`, com
# o motivo. Recusar na construcao, e nao no documento, e o que impede o erro de
# reaparecer daqui a tres meses.
PROIBIDAS_COMO_FEATURE = {
    'baa': (
        'e o proprio alvo em t. Usa-lo como feature transforma o experimento '
        'na linha de base de persistencia - que ja existe em ml/baseline.py e '
        'e o piso a ser batido, nao o modelo.'
    ),
    'hotspot': (
        'junto com o DHW determina o BAA exatamente pela regra da NOAA. '
        'Ver docs/VARIAVEIS.md secao 4.2.'
    ),
    'baa_area_alerta': (
        'sai da mesma grade e do mesmo instante que o BAA: saber que 95% do '
        'recife esta em alerta e praticamente saber o alerta maximo. '
        'Ver docs/VARIAVEIS.md secao 4.5.'
    ),
}


class FeatureComVazamento(ValueError):
    """A feature pedida deriva do alvo."""


@dataclass
class ConjuntoSupervisionado:
    """A tabela pronta, mais o que precisou ser descartado para chega-la.

    As contagens nao sao enfeite: com ~4 anos-evento (docs/VARIAVEIS.md secao
    7.2), saber quantas amostras a lacuna comeu muda a leitura do resultado.
    """

    quadro: object
    horizonte: int
    features: tuple
    alvo: str
    dias_na_serie: int = 0
    descartadas_sem_alvo: int = 0
    descartadas_sem_feature: int = 0
    conflitos_de_fonte: list = field(default_factory=list)

    @property
    def n(self):
        return len(self.quadro)

    def resumo(self):
        return (
            f'horizonte {self.horizonte}d: {self.n} amostras de '
            f'{self.dias_na_serie} dias '
            f'(-{self.descartadas_sem_alvo} sem alvo em t+{self.horizonte}, '
            f'-{self.descartadas_sem_feature} sem feature em t)'
        )


def _recusar_vazamento(features, alvo):
    for nome in features:
        motivo = PROIBIDAS_COMO_FEATURE.get(nome)
        if motivo:
            raise FeatureComVazamento(f'"{nome}" nao pode ser feature de "{alvo}": {motivo}')


def carregar_largo(local, variaveis):
    """Pivota o formato longo para uma linha por data, com dias corridos.

    O reindex para dias corridos e o que torna a lacuna **visivel** como NaN.
    Sem ele, ela ficaria invisivel: as linhas simplesmente nao existiriam, e
    qualquer deslocamento por posicao passaria por cima dela.
    """
    import pandas as pd

    registros = list(
        MedicaoAmbiental.objects.filter(
            local_recife=local, variavel__in=list(variaveis)
        ).values('data', 'variavel', 'valor', 'fonte')
    )

    colunas = list(variaveis)
    if not registros:
        return pd.DataFrame(columns=colunas), []

    quadro = pd.DataFrame.from_records(registros)

    # A mesma variavel pode vir de duas fontes (SST existe no CRW e no
    # Copernicus). Hoje isso nao acontece, mas escolher em silencio seria o
    # tipo de decisao que ninguem consegue auditar depois.
    duplicadas = quadro[quadro.duplicated(subset=['data', 'variavel'], keep=False)]
    conflitos = sorted(
        {(r.variavel, r.fonte) for r in duplicadas.itertuples()}
    )
    if conflitos:
        raise ValueError(
            'A mesma variavel aparece em mais de uma fonte para a mesma data: '
            f'{conflitos}. Filtre por fonte antes de montar o conjunto - '
            'escolher automaticamente esconderia a mistura de produtos.'
        )

    largo = quadro.pivot(index='data', columns='variavel', values='valor')
    largo = largo.reindex(columns=colunas)

    if len(largo):
        corridos = pd.date_range(largo.index.min(), largo.index.max(), freq='D')
        largo = largo.reindex(corridos.date)
    largo.index.name = 'data'

    return largo, conflitos


def montar(local, horizonte, features=FEATURES_PADRAO, alvo=ALVO_PADRAO):
    """Tabela supervisionada de um local: features em `t`, alvo em `t+horizonte`.

    Colunas devolvidas: `data` (= t), as features, `alvo_data` (= t+horizonte),
    `alvo`, e `alvo_atual` — o alvo medido em `t`.

    ⚠️ `alvo_atual` **nao e feature**. Existe para a linha de base de
    persistencia poder ser calculada sobre exatamente as mesmas amostras que o
    modelo ve; compara-los sobre conjuntos diferentes nao diria nada.
    """
    import pandas as pd

    features = tuple(features)
    _recusar_vazamento(features, alvo)

    if horizonte < 1:
        raise ValueError(f'Horizonte precisa ser de pelo menos 1 dia, veio {horizonte}.')

    largo, conflitos = carregar_largo(local, (*features, alvo))
    dias = len(largo)

    if dias == 0:
        vazio = pd.DataFrame(
            columns=['data', *features, 'alvo_atual', 'alvo_data', 'alvo']
        )
        return ConjuntoSupervisionado(vazio, horizonte, features, alvo)

    # shift(-horizonte) sobre indice de dias corridos = deslocamento em dias.
    # E dessa equivalencia que depende a corretude do horizonte.
    tabela = largo[list(features)].copy()
    tabela['alvo_atual'] = largo[alvo]
    tabela['alvo'] = largo[alvo].shift(-horizonte)
    tabela = tabela.reset_index()
    tabela['alvo_data'] = tabela['data'].map(lambda d: d + timedelta(days=horizonte))

    sem_alvo = int(tabela['alvo'].isna().sum())
    tabela = tabela.dropna(subset=['alvo'])

    antes = len(tabela)
    tabela = tabela.dropna(subset=[*features, 'alvo_atual'])
    sem_feature = antes - len(tabela)

    tabela = tabela[['data', *features, 'alvo_atual', 'alvo_data', 'alvo']]

    return ConjuntoSupervisionado(
        quadro=tabela.reset_index(drop=True),
        horizonte=horizonte,
        features=features,
        alvo=alvo,
        dias_na_serie=dias,
        descartadas_sem_alvo=sem_alvo,
        descartadas_sem_feature=sem_feature,
        conflitos_de_fonte=conflitos,
    )


def montar_todos(locais, horizonte, features=FEATURES_PADRAO, alvo=ALVO_PADRAO):
    """Empilha os locais numa tabela so, com a coluna `local`.

    ⚠️ As linhas **nao sao independentes entre locais**: os episodios caem nos
    mesmos anos nos tres recifes, por serem o mesmo forcante oceanografico.
    Ver docs/VARIAVEIS.md secao 7.2 antes de tratar isso como n = soma.
    """
    import pandas as pd

    partes, dias, sem_alvo, sem_feature = [], 0, 0, 0
    for local in locais:
        conjunto = montar(local, horizonte, features, alvo)
        quadro = conjunto.quadro.copy()
        quadro.insert(0, 'local', local.slug)
        partes.append(quadro)
        dias += conjunto.dias_na_serie
        sem_alvo += conjunto.descartadas_sem_alvo
        sem_feature += conjunto.descartadas_sem_feature

    juntas = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()

    return ConjuntoSupervisionado(
        quadro=juntas,
        horizonte=horizonte,
        features=tuple(features),
        alvo=alvo,
        dias_na_serie=dias,
        descartadas_sem_alvo=sem_alvo,
        descartadas_sem_feature=sem_feature,
    )


def em_alerta(serie):
    """Converte BAA ordinal no evento binario "Alerta Nivel 1 ou acima"."""
    return serie >= LIMIAR_ALERTA
