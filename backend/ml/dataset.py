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

**4. As janelas retrospectivas olham so para tras**, e sao medidas em dias.
Ver `Janela` e a nota sobre trajetoria abaixo.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from aquaculture.models import MedicaoAmbiental
from ingestao.conectores.noaa_crw import LIMIAR_ALERTA

# As variaveis do baseline, conforme docs/VARIAVEIS.md secao 1. KD490 saiu por
# so existir de 2023-11 em diante e nao ter reanalise (secao 3.5).
VARIAVEIS_BASELINE = ('sst', 'dhw', 'salinidade', 'oxigenio')

# **Nenhum nivel entra como feature, por decisao medida** (versao D de
# docs/RESULTADOS.md secao 8). O modelo usa so as trajetorias.
#
# Parece contraintuitivo tirar o valor absoluto, entao vale o numero: com so
# os niveis a logistica faz F1 0,489; so com trajetorias, 0,728; com os dois,
# 0,674. O nivel nao acrescenta e ainda piora - o que faz sentido para um alvo
# que e *mudanca de estado* daqui a N dias, nao o estado de hoje.
#
# Passe `features=VARIAVEIS_BASELINE` para reproduzir a versao com niveis.
FEATURES_PADRAO = ()

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

# Variaveis lidas em `t` para as **linhas de base**, nunca para o modelo.
#
# 🚨 A distincao e o ponto todo. `hotspot` esta em `PROIBIDAS_COMO_FEATURE`
# logo acima porque, junto com o DHW, ele *determina* o BAA pela regra da NOAA
# — um modelo que o visse estaria lendo a resposta. Mas uma **linha de base**
# pode le-lo: ela nao preve nada, so aplica hoje a regra publicada e deixa esse
# resultado ser comparado com a previsao de daqui a N dias. E justamente essa
# comparacao que diz se o modelo acrescenta alguma coisa.
#
# Por isso as colunas saem com sufixo `_atual`, do mesmo jeito que `alvo_atual`
# — que existe desde o inicio pelo mesmo motivo, e pela mesma razao nao e
# feature. `colunas_de_entrada` continua sendo `(*features, *janelas)`, e um
# teste garante que nenhuma coluna `_atual` entre ali por acidente.
VARIAVEIS_DE_LINHA_DE_BASE = ('dhw', 'hotspot')


@dataclass(frozen=True)
class Janela:
    """Uma feature retrospectiva: `operacao` de `variavel` nos ultimos `dias`.

    Sempre olhando **para tras**, incluindo o proprio dia `t`. Nunca para
    frente - seria vazamento direto.
    """

    variavel: str
    dias: int
    operacao: str  # 'variacao' | 'media' | 'maximo'

    @property
    def nome(self):
        return f'{self.variavel}_{self.operacao}_{self.dias}d'


# **Por que janela existe.** O valor instantaneo nao diz a direcao: DHW = 6
# hoje descreve tanto um recife que subiu de 2 na ultima semana - evento
# comecando, vai piorar - quanto um que caiu de 10 - evento terminando. Sao
# situacoes opostas com a mesma feature.
#
# A linha de base de persistencia acerta 84% em 7 dias justamente porque
# episodio longo e estavel no meio; onde ela erra e no comeco e no fim (2026,
# de episodios curtos, caiu para F1 0,471). E ali que a trajetoria decide.
# Sem janela, o modelo competiria com a persistencia usando menos informacao
# do que ela usa implicitamente - e perder assim nao ensinaria nada sobre o
# fenomeno, so sobre a pobreza das features.
#
# **Por que o conjunto padrao e pequeno.** Sao ~4 anos-evento de amostra
# efetiva (docs/VARIAVEIS.md secao 7.2). Tres operacoes x quatro variaveis x
# duas janelas dariam 24 features sobre 4 eventos independentes, que e receita
# de sobreajuste. O padrao fica na hipotese central - trajetoria - e as outras
# operacoes ficam disponiveis para quem quiser testar explicitamente.
OPERACOES = ('variacao', 'media', 'maximo')

# Uma janela por variavel, e so.
#
# Ate 25/07/2026 o padrao tinha duas - 7 e 14 dias para as termicas. A medicao
# mostrou que as duas sao quase a mesma coluna: `dhw_variacao_7d` e
# `dhw_variacao_14d` tem **r = 0,976**. Isso tornava os coeficientes
# ininterpretaveis (o do `dhw` saia negativo, dizendo que calor acumulado
# protege o coral) sem comprar desempenho: com uma janela so, o F1 sobe de
# 0,707 para 0,728 e o PR-AUC de 0,760 para 0,790, com 4 entradas em vez de 10.
#
# Ver docs/RESULTADOS.md secao 8 para as cinco versoes comparadas.
DIAS_DA_JANELA = 7


def janelas_para(variaveis):
    """Janela padrao das variaveis pedidas: a trajetoria de 7 dias de cada uma.

    Derivado das variaveis, e nao uma lista fixa: um conjunto montado com
    `('sst',)` nao deveria passar a exigir salinidade so porque ela esta no
    padrao do projeto.
    """
    return tuple(Janela(v, DIAS_DA_JANELA, 'variacao') for v in variaveis)


JANELAS_PADRAO = janelas_para(VARIAVEIS_BASELINE)


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
    janelas: tuple = ()
    dias_na_serie: int = 0
    descartadas_sem_alvo: int = 0
    descartadas_sem_feature: int = 0
    descartadas_sem_janela: int = 0
    conflitos_de_fonte: list = field(default_factory=list)

    @property
    def n(self):
        return len(self.quadro)

    @property
    def colunas_de_entrada(self):
        """Tudo o que o modelo pode ver. Nao inclui `alvo_atual`."""
        return (*self.features, *(j.nome for j in self.janelas))

    def resumo(self):
        janela = (
            f', -{self.descartadas_sem_janela} sem janela completa'
            if self.janelas
            else ''
        )
        return (
            f'horizonte {self.horizonte}d: {self.n} amostras de '
            f'{self.dias_na_serie} dias '
            f'(-{self.descartadas_sem_alvo} sem alvo em t+{self.horizonte}, '
            f'-{self.descartadas_sem_feature} sem feature em t{janela})'
        )


def _recusar_vazamento(features, alvo):
    for nome in features:
        motivo = PROIBIDAS_COMO_FEATURE.get(nome)
        if motivo:
            raise FeatureComVazamento(f'"{nome}" nao pode ser feature de "{alvo}": {motivo}')


def _validar_janelas(janelas, alvo):
    """Janela sobre variavel proibida continua sendo vazamento.

    A media de 7 dias do HotSpot nao e menos derivada do alvo que o HotSpot -
    so e mais dificil de perceber lendo o nome da coluna.
    """
    for janela in janelas:
        motivo = PROIBIDAS_COMO_FEATURE.get(janela.variavel)
        if motivo:
            raise FeatureComVazamento(
                f'janela sobre "{janela.variavel}" nao pode ser feature de '
                f'"{alvo}": {motivo}'
            )
        if janela.operacao not in OPERACOES:
            raise ValueError(
                f'Operacao "{janela.operacao}" desconhecida. Disponiveis: '
                f'{list(OPERACOES)}.'
            )
        if janela.dias < 1:
            raise ValueError(f'Janela precisa ter pelo menos 1 dia, veio {janela.dias}.')


def aplicar_janela(serie, janela):
    """Calcula uma feature retrospectiva sobre uma serie de dias corridos.

    ⚠️ **So funciona sobre indice de dias corridos.** `shift` e `rolling`
    contam linhas, e as linhas so equivalem a dias porque `carregar_largo`
    reindexa a serie. Sem isso, uma "media de 7 dias" que atravessasse as 6
    datas ausentes do CRW seria media de 5 - com o nome dizendo 7.

    `min_periods` igual ao tamanho da janela e deliberado: janela incompleta
    vira NaN e a amostra e descartada, em vez de virar um numero que mente
    sobre a propria cobertura. E a decisao que docs/VARIAVEIS.md secao 7.1
    exigia que fosse explicita.

    ⚠️ **`variacao` e `media`/`maximo` reagem a lacuna de formas diferentes**,
    e a diferenca e correta, nao descuido:

    - `variacao` compara dois instantes, `t` e `t - dias`. Se os dois existem,
      a conta e exata mesmo com dias faltando no meio - a diferenca entre 11/01
      e 04/01 continua sendo de sete dias.
    - `media` e `maximo` resumem **todos** os dias do intervalo. Um dia
      faltando muda o resultado, entao a amostra cai.
    """
    if janela.operacao == 'variacao':
        # Diferenca entre hoje e `dias` atras: a trajetoria.
        return serie - serie.shift(janela.dias)
    if janela.operacao == 'media':
        return serie.rolling(window=janela.dias, min_periods=janela.dias).mean()
    if janela.operacao == 'maximo':
        return serie.rolling(window=janela.dias, min_periods=janela.dias).max()
    raise ValueError(f'Operacao "{janela.operacao}" desconhecida.')


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


def montar(local, horizonte, features=FEATURES_PADRAO, alvo=ALVO_PADRAO,
           janelas=None):
    """Tabela supervisionada de um local: features em `t`, alvo em `t+horizonte`.

    Colunas devolvidas: `data` (= t), as features, as janelas, as colunas
    `_atual` das linhas de base, `alvo_data` (= t+horizonte), `alvo`, e
    `alvo_atual` — o alvo medido em `t`.

    ⚠️ Nenhuma coluna terminada em `_atual` **e feature**. Elas existem para as
    linhas de base poderem ser calculadas sobre exatamente as mesmas amostras
    que o modelo ve; compara-las sobre conjuntos diferentes nao diria nada. Ver
    `VARIAVEIS_DE_LINHA_DE_BASE`.

    `janelas=None` usa o padrao derivado das proprias features
    (`janelas_para`); `janelas=()` monta o conjunto sem features
    retrospectivas, util para medir quanto elas acrescentam.
    """
    import pandas as pd

    features = tuple(features)
    # Sem features de nivel, a janela vem das variaveis do baseline; com elas,
    # das proprias - para `features=('sst',)` nao passar a exigir salinidade.
    janelas = tuple(
        janelas_para(features or VARIAVEIS_BASELINE)
        if janelas is None
        else janelas
    )
    _recusar_vazamento(features, alvo)
    _validar_janelas(janelas, alvo)

    if horizonte < 1:
        raise ValueError(f'Horizonte precisa ser de pelo menos 1 dia, veio {horizonte}.')

    # A janela pode pedir uma variavel que nao esta entre as features - ler
    # a serie dela e necessario mesmo assim.
    necessarias = {*features, alvo, *(j.variavel for j in janelas),
                   *VARIAVEIS_DE_LINHA_DE_BASE}
    largo, conflitos = carregar_largo(local, sorted(necessarias))
    dias = len(largo)

    nomes_janela = [j.nome for j in janelas]
    nomes_base = [f'{v}_atual' for v in VARIAVEIS_DE_LINHA_DE_BASE]

    if dias == 0:
        vazio = pd.DataFrame(
            columns=['data', *features, *nomes_janela, *nomes_base,
                     'alvo_atual', 'alvo_data', 'alvo']
        )
        return ConjuntoSupervisionado(vazio, horizonte, features, alvo, janelas)

    # shift(-horizonte) sobre indice de dias corridos = deslocamento em dias.
    # E dessa equivalencia que depende a corretude do horizonte - e tambem a
    # das janelas, que usam shift/rolling pelo mesmo motivo.
    tabela = largo[list(features)].copy()
    for janela in janelas:
        tabela[janela.nome] = aplicar_janela(largo[janela.variavel], janela)

    # ⚠️ Fora de qualquer `dropna` de proposito. Uma linha de base que nao
    # existisse num dia nao pode custar ao MODELO uma amostra que ele teria:
    # isso trocaria em silencio o conjunto medido pelo conjunto que a
    # comparacao conseguiu montar. Dia sem a variavel vira NaN, e a linha de
    # base o descarta na hora de se avaliar.
    for variavel in VARIAVEIS_DE_LINHA_DE_BASE:
        tabela[f'{variavel}_atual'] = (
            largo[variavel] if variavel in largo.columns else float('nan')
        )

    tabela['alvo_atual'] = largo[alvo]
    tabela['alvo'] = largo[alvo].shift(-horizonte)
    tabela = tabela.reset_index()
    tabela['alvo_data'] = tabela['data'].map(lambda d: d + timedelta(days=horizonte))

    sem_alvo = int(tabela['alvo'].isna().sum())
    tabela = tabela.dropna(subset=['alvo'])

    antes = len(tabela)
    tabela = tabela.dropna(subset=[*features, 'alvo_atual'])
    sem_feature = antes - len(tabela)

    # Contado a parte: a janela custa amostra no comeco da serie e em volta de
    # cada lacuna, e esse custo precisa ficar visivel na hora de comparar um
    # conjunto com janela contra um sem.
    antes = len(tabela)
    if nomes_janela:
        tabela = tabela.dropna(subset=nomes_janela)
    sem_janela = antes - len(tabela)

    tabela = tabela[
        ['data', *features, *nomes_janela, *nomes_base, 'alvo_atual',
         'alvo_data', 'alvo']
    ]

    return ConjuntoSupervisionado(
        quadro=tabela.reset_index(drop=True),
        horizonte=horizonte,
        features=features,
        alvo=alvo,
        janelas=janelas,
        dias_na_serie=dias,
        descartadas_sem_alvo=sem_alvo,
        descartadas_sem_feature=sem_feature,
        descartadas_sem_janela=sem_janela,
        conflitos_de_fonte=conflitos,
    )


def montar_todos(locais, horizonte, features=FEATURES_PADRAO, alvo=ALVO_PADRAO,
                 janelas=None):
    """Empilha os locais numa tabela so, com a coluna `local`.

    ⚠️ As linhas **nao sao independentes entre locais**: os episodios caem nos
    mesmos anos nos tres recifes, por serem o mesmo forcante oceanografico.
    Ver docs/VARIAVEIS.md secao 7.2 antes de tratar isso como n = soma.

    Cada local e montado em separado de proposito: concatenar as series antes
    de aplicar janela faria o fim de um recife entrar na janela do proximo.
    """
    import pandas as pd

    features = tuple(features)
    # Sem features de nivel, a janela vem das variaveis do baseline; com elas,
    # das proprias - para `features=('sst',)` nao passar a exigir salinidade.
    janelas = tuple(
        janelas_para(features or VARIAVEIS_BASELINE)
        if janelas is None
        else janelas
    )

    partes, dias, sem_alvo, sem_feature, sem_janela = [], 0, 0, 0, 0
    for local in locais:
        conjunto = montar(local, horizonte, features, alvo, janelas)
        quadro = conjunto.quadro.copy()
        quadro.insert(0, 'local', local.slug)
        partes.append(quadro)
        dias += conjunto.dias_na_serie
        sem_alvo += conjunto.descartadas_sem_alvo
        sem_feature += conjunto.descartadas_sem_feature
        sem_janela += conjunto.descartadas_sem_janela

    juntas = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()

    return ConjuntoSupervisionado(
        quadro=juntas,
        horizonte=horizonte,
        features=features,
        alvo=alvo,
        janelas=janelas,
        dias_na_serie=dias,
        descartadas_sem_alvo=sem_alvo,
        descartadas_sem_feature=sem_feature,
        descartadas_sem_janela=sem_janela,
    )


def em_alerta(serie):
    """Converte BAA ordinal no evento binario "Alerta Nivel 1 ou acima"."""
    return serie >= LIMIAR_ALERTA
