"""Figuras sobre o que o modelo aprendeu. Nenhuma delas calcula nada de novo.

Todo numero desenhado aqui ja e produzido por `ml/importancia.py`,
`ml/calibracao.py` ou `ml/modelo.py`, e ja aparece em texto nos comandos
existentes. Este modulo **so** escolhe eixo, escala e rotulo — o que evita a
armadilha de um grafico virar uma segunda implementacao da metrica, com
liberdade de discordar da primeira sem ninguem perceber.

🚨 **Tres leituras erradas que estas figuras convidam, e o que cada uma faz
para desencorajar:**

**1. "O coeficiente e o efeito da variavel."** Nao e. As features sao
*variacoes de 7 dias*, entao um coeficiente positivo de `sst_variacao_7d`
significa "aquecer nos ultimos 7 dias aumenta o risco", e **nao** "estar quente
aumenta o risco". Sao afirmacoes diferentes, e a segunda nem esta sendo
testada. Por isso o eixo diz "variacao em 7 dias" e nunca so o nome da
variavel.

**2. "A media resume os anos."** So quando eles concordam. Um coeficiente que
vale +0,8 em 2021 e -0,6 em 2022 tem media +0,1, que se le como "quase sem
efeito" — quando o que houve foi troca de sinal. O painel por ano existe
exatamente para essa media nao ser a unica coisa visivel, e por isso ele mostra
os pontos individuais **junto** da linha da media, nunca so a linha.

**3. "A probabilidade e continua."** A calibracao isotonica e funcao escada:
degraus sao esperados na linha do tempo, e dois dias com entradas diferentes
podem sair no mesmo valor. Ver docs/RESULTADOS.md secao 22.8.

⚠️ **Sobre qual modelo cada figura descreve.** As figuras por ano usam os
ajustes do leave-year-out — modelos que **nao** viram o ano que estao medindo.
A figura de resposta a variavel usa o modelo final, que e o que o painel serve.
Sao objetos diferentes de proposito: o primeiro responde "isso generaliza?", o
segundo responde "o que esta no ar faz o que?". Misturar os dois seria medir
memoria num caso e servir outra coisa no outro.
"""

from dataclasses import dataclass

# Nomes legiveis. O eixo de um grafico que vai para o TCC nao pode dizer
# `oxigenio_variacao_7d` — mas tambem nao pode dizer so "oxigenio", que apagaria
# a informacao de que a feature e uma variacao. Ver a leitura errada 1 acima.
ROTULOS = {
    'sst_variacao_7d': 'Temperatura\n(variação em 7 dias)',
    'dhw_variacao_7d': 'Calor acumulado / DHW\n(variação em 7 dias)',
    'salinidade_variacao_7d': 'Salinidade\n(variação em 7 dias)',
    'oxigenio_variacao_7d': 'Oxigênio\n(variação em 7 dias)',
}

UNIDADES = {
    'sst_variacao_7d': '°C',
    'dhw_variacao_7d': '°C·semana',
    'salinidade_variacao_7d': 'PSU',
    'oxigenio_variacao_7d': 'mmol/m³',
}

# Uma cor por variavel, estavel entre as quatro figuras: a mesma variavel muda
# de grafico mas nao de cor, senao comparar duas figuras lado a lado exige
# reler a legenda das duas.
CORES = {
    'sst_variacao_7d': '#c1443c',
    'dhw_variacao_7d': '#d98b26',
    'salinidade_variacao_7d': '#2f7d8f',
    'oxigenio_variacao_7d': '#4a7c3f',
}

COR_NEUTRA = '#5b6670'
COR_ALERTA = '#b3261e'
COR_EPISODIO = '#f2c9c6'
COR_CORAL = '#8e5ea8'

TAMANHO_PADRAO = (10, 6)
DPI = 200

# ---------------------------------------------------------------------------
# 🚨 A confusao que estas figuras precisam impedir
# ---------------------------------------------------------------------------
# O modelo preve **alerta de estresse termico** — `baa >= 3` em t+7, a escala
# da NOAA calculada a partir de calor acumulado. Ele **nao** preve
# branqueamento observado, que e o coral expulsando as algas e alguem
# registrando isso debaixo d'agua.
#
# As duas coisas nao sao sinonimos, e a diferenca esta medida
# (docs/RESULTADOS.md secao 11.2, sobre 166 visitas do GCBD no Brasil):
#
#   - Quando a regra da NOAA dispara, houve branqueamento: 10 de 10 casos.
#   - Mas 78 dos 88 branqueamentos observados aconteceram com DHW = 0, ou
#     seja, **sem nenhum alerta**.
#
# Um grafico que rotula a faixa de alerta como "episodio" ou "evento" convida
# a leitura errada — e a primeira versao destas figuras fazia exatamente isso.
# Para um publico leigo o estrago e maior: "o modelo acerta 4 de 5 eventos" vira
# "o modelo prevê branqueamento", que e falso e mais tranquilizador do que a
# verdade.
#
# A defesa nao e lembrar de escrever certo: e `_selar()`, aplicado por **toda**
# funcao que devolve `Figura`, com teste exigindo o carimbo em cada uma.
NOME_DO_ALVO = 'alerta de estresse térmico (critério NOAA)'

AVISO_DO_ALVO = (
    'Esta figura trata de ALERTA DE ESTRESSE TÉRMICO — o aviso que a NOAA '
    'emite a partir de calor acumulado no mar. Não é o mesmo que branqueamento '
    'observado: quando o alerta dispara houve branqueamento em 10 de 10 casos, '
    'mas 78 dos 88 branqueamentos registrados no Brasil ocorreram sem alerta '
    'nenhum.'
)

AVISO_CURTO = (
    'Previsão de ALERTA TÉRMICO (critério NOAA) — não de branqueamento '
    'observado.'
)

ONDE_ENTENDER = ' Ver a figura "o_que_e_previsto".'


def _selar(nome, figura, legenda, aponta_para_o_esquema=True):
    """Carimba o aviso do alvo na figura e na legenda, e devolve `Figura`.

    ⚠️ **Toda funcao publica deste modulo termina aqui.** O aviso e estrutural,
    e nao editorial: uma figura que escape sem ele fica com aparencia de
    previsao de branqueamento, que e a afirmacao que o projeto passou tres
    secoes de RESULTADOS.md mostrando ser falsa.

    `aponta_para_o_esquema=False` no proprio esquema — um rodape mandando ver
    a figura que ele esta rodapeando manda o leitor procurar onde ele ja esta.
    """
    figura.text(
        0.5, -0.012,
        AVISO_CURTO + (ONDE_ENTENDER if aponta_para_o_esquema else ''),
        ha='center', va='top', fontsize=7.5, color=COR_ALERTA,
        transform=figura.transFigure,
    )
    return Figura(nome, figura, f'{AVISO_DO_ALVO}\n\n{legenda}')


def rotulo(coluna):
    return ROTULOS.get(coluna, coluna)


def rotulo_curto(coluna):
    return rotulo(coluna).split('\n')[0]


def _plt():
    """Importa o matplotlib ja no backend sem tela.

    O import fica dentro da funcao porque este modulo e carregado pelo
    `manage.py` em qualquer comando, e o matplotlib custa ~300 ms de import
    para nada quando ninguem vai desenhar.
    """
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    return plt


@dataclass
class Figura:
    """Uma figura pronta e o texto que explica o que ela mostra.

    A legenda anda junto da figura de proposito: um PNG solto numa pasta perde
    em uma semana a informacao de sobre que dado ele foi feito, e um grafico
    sem procedencia num TCC e um grafico que a banca vai perguntar de onde
    veio.
    """

    nome: str
    figura: object
    legenda: str

    def salvar(self, pasta, formatos=('png',)):
        caminhos = []
        for formato in formatos:
            caminho = pasta / f'{self.nome}.{formato}'
            self.figura.savefig(caminho, dpi=DPI, bbox_inches='tight')
            caminhos.append(caminho)
        (pasta / f'{self.nome}.txt').write_text(self.legenda, encoding='utf-8')
        return caminhos


# ---------------------------------------------------------------------------
# 0. O que e previsto, e o que nao e
# ---------------------------------------------------------------------------
def o_que_e_previsto():
    """A figura que precisa ser lida antes das outras quatro.

    Nao tem dado do banco: e um esquema. Existe porque a pergunta "o que este
    site prevê?" tem uma resposta curta que soa como outra coisa — "risco de
    branqueamento" —, e a resposta correta e mais longa e menos vendavel.

    Os numeros do lado direito sao medidos, nao ilustrativos: 166 visitas do
    GCBD em recifes brasileiros, docs/RESULTADOS.md secao 11.2.
    """
    plt = _plt()
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    figura, eixo = plt.subplots(figsize=(13, 7.2))
    eixo.set_xlim(0, 100)
    eixo.set_ylim(0, 100)
    eixo.axis('off')

    # ⚠️ A altura sai do texto, e nao de um numero escolhido a olho. A primeira
    # versao fixava a altura de cada caixa: bastou um corpo com uma linha a
    # mais para o texto vazar por baixo e invadir a caixa seguinte. Aqui o
    # tamanho e consequencia do conteudo, entao acrescentar uma linha empurra o
    # resto para baixo em vez de sobrepor.
    ALTURA_DA_LINHA = 3.6
    ESPACO_DO_TITULO = 7.0
    INTERVALO = 5.0

    def altura_para(corpo):
        return ESPACO_DO_TITULO + corpo.count('\n') * ALTURA_DA_LINHA + ALTURA_DA_LINHA

    def caixa(x, topo, largura, titulo, corpo, cor, fundo):
        """Desenha a partir do topo e devolve a base, para empilhar em cascata."""
        altura = altura_para(corpo)
        base = topo - altura
        eixo.add_patch(FancyBboxPatch(
            (x, base), largura, altura,
            boxstyle='round,pad=1.1', linewidth=1.6,
            edgecolor=cor, facecolor=fundo,
        ))
        eixo.text(
            x + largura / 2, topo - 2.0, titulo,
            ha='center', va='top', fontsize=10.5, fontweight='bold', color=cor,
        )
        eixo.text(
            x + largura / 2, topo - ESPACO_DO_TITULO, corpo,
            ha='center', va='top', fontsize=9, color='#2b3138', linespacing=1.5,
        )
        return base

    def seta(x1, y1, x2, y2):
        eixo.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=16,
            linewidth=1.4, color=COR_NEUTRA,
        ))

    eixo.text(
        50, 97, 'O que este projeto prevê — e o que ele não prevê',
        ha='center', fontsize=14, fontweight='bold',
    )

    # --- Coluna da esquerda: a cadeia que o projeto mede -------------------
    eixo.text(
        22, 90, 'O QUE PREVEMOS', ha='center', fontsize=11.5,
        fontweight='bold', color=CORES['dhw_variacao_7d'],
    )

    cursor = 85
    passos = (
        ('1. Temperatura do mar',
         'Medida por satélite, todo dia,\nnos três recifes.',
         CORES['sst_variacao_7d'], '#fdf1f0'),
        ('2. Calor acumulado (DHW)',
         'Quanto calor a mais o recife\nlevou nas últimas 12 semanas.',
         CORES['dhw_variacao_7d'], '#fdf6ec'),
        ('3. Alerta de estresse térmico',
         'A escala oficial da NOAA passa\ndo nível 3. É um AVISO,\n'
         'calculado a partir da temperatura.',
         COR_ALERTA, '#fdeceb'),
        ('4. A nossa previsão',
         'A chance de esse aviso acontecer\ndaqui a 7 DIAS — antes\n'
         'que ele aconteça.',
         COR_NEUTRA, '#eef1f3'),
    )
    for indice, (titulo, corpo, cor, fundo) in enumerate(passos):
        cursor = caixa(5, cursor, 34, titulo, corpo, cor, fundo)
        if indice < len(passos) - 1:
            seta(22, cursor, 22, cursor - INTERVALO)
            cursor -= INTERVALO

    # --- Coluna da direita: o fenomeno biologico --------------------------
    eixo.text(
        78, 90, 'O QUE É BRANQUEAMENTO', ha='center', fontsize=11.5,
        fontweight='bold', color=COR_CORAL,
    )

    cursor = 85
    for titulo, corpo, cor, fundo in (
        ('O coral expulsa as algas',
         'Perde a cor e a principal fonte\nde alimento. Pode se recuperar,\n'
         'ou morrer.\nÉ observado debaixo d\'água,\npor pessoas — não por satélite.',
         COR_CORAL, '#f6f0fa'),
        ('Calor é uma das causas.\nNão é a única.',
         'Doença, poluição, sedimento e\nmudança de salinidade também\n'
         'causam. Este projeto não mede\nnenhum desses.',
         COR_CORAL, '#f6f0fa'),
        ('O que foi medido',
         'Em 166 visitas a recifes brasileiros:\n'
         'quando o alerta disparou, houve\nbranqueamento em 10 de 10 casos.\n'
         'Mas 78 dos 88 branqueamentos\nregistrados ocorreram SEM alerta.',
         '#2b3138', '#eceef0'),
    ):
        cursor = caixa(61, cursor, 34, titulo, corpo, cor, fundo) - INTERVALO

    # --- A ponte entre as duas colunas ------------------------------------
    eixo.text(
        50, 55, '≠', ha='center', va='center', fontsize=34,
        color=COR_ALERTA, fontweight='bold',
    )
    eixo.text(
        50, 46, 'não é\no mesmo\nque', ha='center', va='center',
        fontsize=9.5, color=COR_ALERTA, linespacing=1.5,
    )

    figura.tight_layout()

    legenda = (
        'Esquema, não gráfico de dados — exceto os números do quadro inferior '
        'direito, medidos sobre 166 visitas a recifes brasileiros na base GCBD '
        '(docs/RESULTADOS.md §11.2). Lado esquerdo: a cadeia que o projeto '
        'realmente percorre, da temperatura medida por satélite até a previsão '
        'do aviso da NOAA com 7 dias de antecedência. Lado direito: o '
        'branqueamento em si, que é um fenômeno biológico observado por '
        'pessoas. A relação entre os dois é assimétrica: o alerta térmico é '
        'suficiente para haver branqueamento, mas está longe de ser necessário '
        '— a maior parte do branqueamento brasileiro registrado aconteceu sem '
        'nenhum calor acumulado pelo critério da NOAA. Um site que anunciasse '
        '"risco de branqueamento" estaria prometendo o que não entrega.'
    )
    return _selar('o_que_e_previsto', figura, legenda,
                  aponta_para_o_esquema=False)


# ---------------------------------------------------------------------------
# 1. Coeficiente por ano
# ---------------------------------------------------------------------------
def coeficientes_por_ano(importancia):
    """Um painel por variavel: o peso que ela teve em cada dobra.

    Responde "o modelo entende a mesma coisa todo ano?". A linha tracejada e a
    media — a mesma que o `--importancia` ja imprime — e os pontos sao os anos
    que a produziram. A faixa cinza em zero marca a fronteira de sinal: cruza-la
    e o modelo mudar de ideia sobre a **direcao** do efeito, nao so sobre o
    tamanho.
    """
    plt = _plt()

    colunas = list(importancia.coeficientes_por_ano)
    if not colunas:
        raise ValueError(
            'Nao ha coeficiente por ano: o modelo medido nao tem `coef_` '
            '(arvore ou boosting). Use --modelo logistica.'
        )

    anos = importancia.anos
    # ⚠️ **Eixo vertical livre em cada painel, e nao compartilhado.** Com eixo
    # comum o DHW — cerca de 30x maior que os demais — achata as outras tres
    # numa linha reta, e a pergunta desta figura ("e estavel?") fica sem
    # resposta justamente para as variaveis em que a resposta e "nao". A
    # comparacao de magnitude nao se perde: a media vai escrita em cada painel,
    # e o quanto o modelo depende de cada uma esta na figura de permutacao.
    figura, eixos = plt.subplots(
        1, len(colunas), figsize=(3.4 * len(colunas), 4.8), sharey=False,
    )
    eixos = [eixos] if len(colunas) == 1 else list(eixos)

    for eixo, coluna in zip(eixos, colunas):
        valores = importancia.coeficientes_por_ano[coluna]
        media = importancia.coeficientes[coluna]
        cor = CORES.get(coluna, COR_NEUTRA)
        troca_de_sinal = min(valores) < 0 < max(valores)

        eixo.axhline(0, color='#4a5560', linewidth=1.2)
        eixo.axhline(media, color=cor, linestyle='--', linewidth=1.4)
        eixo.plot(anos, valores, marker='o', color=cor, linewidth=1.8)

        eixo.set_title(
            f'{rotulo(coluna)}\nmédia {media:+.2f}'
            + ('  — troca de sinal' if troca_de_sinal else ''),
            fontsize=9,
            color=COR_ALERTA if troca_de_sinal else 'black',
        )
        eixo.set_xticks(anos)
        eixo.tick_params(axis='x', labelrotation=45, labelsize=8)
        eixo.tick_params(axis='y', labelsize=8)
        eixo.spines[['top', 'right']].set_visible(False)

    eixos[0].set_ylabel('Peso dado à variável\n(acima de zero = empurra o aviso)')
    figura.suptitle(
        'O modelo dá o mesmo peso a cada variável todo ano?\n'
        'acima da linha escura, aquela variação empurra o aviso para cima; '
        'abaixo, puxa para baixo   |   '
        '⚠️ as alturas dos quatro painéis não são comparáveis entre si',
        fontsize=10,
    )
    figura.tight_layout()

    trocaram = [
        rotulo_curto(c)
        for c, v in importancia.coeficientes_por_ano.items()
        if min(v) < 0 < max(v)
    ]
    legenda = (
        'Peso que o modelo deu a cada variável, medido separadamente em cada '
        'ano. Para o ano X, o modelo foi treinado sem enxergar X — assim o '
        'peso mostrado é o que ele levaria para um ano que nunca viu. Valores '
        'na escala padronizada, que é o que os torna comparáveis entre '
        f'variáveis de unidades diferentes. Anos medidos: {anos}. '
        + (
            'Mudaram de direção de um ano para outro: '
            + ', '.join(trocaram)
            + '. Nesses casos a média engana: ela fica perto de zero e se lê '
            'como "quase sem efeito", quando o que houve foi o modelo '
            'discordar de si mesmo sobre se aquela variação aumenta ou '
            'diminui o aviso.'
            if trocaram
            else 'Nenhuma variável mudou de direção entre os anos.'
        )
    )
    return _selar('coeficientes_por_ano', figura, legenda)


# ---------------------------------------------------------------------------
# 2. Importancia por permutacao, por ano
# ---------------------------------------------------------------------------
def importancia_por_ano(importancia):
    """Quanto o desempenho cai ao embaralhar cada variavel, dobra a dobra.

    Complementa a figura anterior e nao a repete: o coeficiente diz **direcao e
    forca** dentro do modelo ajustado; a permutacao diz **do que ele realmente
    depende** para acertar num ano que nao viu. Uma variavel pode ter
    coeficiente grande e queda quase nula quando outra carrega a mesma
    informacao.
    """
    plt = _plt()

    por_ano = importancia.por_coluna_por_ano
    if not por_ano:
        raise ValueError('Nao ha importancia por ano medida.')

    anos = importancia.anos
    figura, eixo = plt.subplots(figsize=TAMANHO_PADRAO)

    for coluna, valores in por_ano.items():
        eixo.plot(
            anos, valores, marker='o', linewidth=1.8,
            color=CORES.get(coluna, COR_NEUTRA), label=rotulo_curto(coluna),
        )

    eixo.axhline(0, color='#9aa3ab', linewidth=1)
    eixo.set_xticks(anos)
    eixo.set_xlabel('Ano que o modelo não viu no treino')
    eixo.set_ylabel('Quanto a previsão piora sem essa variável')
    eixo.set_title(
        'De qual variável a previsão realmente depende\n'
        'quanto mais alto, mais o aviso deixa de funcionar sem ela — '
        'perto de zero, ela não estava fazendo diferença',
        fontsize=11,
    )
    eixo.legend(fontsize=9, frameon=False)
    eixo.spines[['top', 'right']].set_visible(False)
    figura.tight_layout()

    legenda = (
        'Teste de dependência: para cada ano, os valores de uma variável são '
        'embaralhados — como se aquela informação tivesse sido perdida — e '
        'mede-se quanto a qualidade da previsão cai (queda do PR-AUC). Curva '
        'alta significa que o aviso depende daquela variável; curva colada no '
        'zero significa que ela não estava sendo usada para acertar. O modelo '
        'de cada ano foi treinado sem aquele ano, então isto mede previsão e '
        f'não memória. Anos medidos: {anos}. '
        'Queda negativa não é erro: embaralhar ruído pode melhorar por acaso, '
        'e o tamanho dessa oscilação é a régua do que conta como diferença '
        'real nas outras curvas.'
    )
    return _selar('importancia_por_ano', figura, legenda)


# ---------------------------------------------------------------------------
# 3. Linha do tempo por recife
# ---------------------------------------------------------------------------
def linha_do_tempo(quadro, coluna_probabilidade, limiar, local, colunas):
    """As quatro variacoes, a probabilidade prevista e os episodios reais.

    Responde "o que estava acontecendo quando o modelo levantou o risco?". A
    probabilidade e **fora da dobra** — de um modelo que nao viu aquele ano —,
    senao a figura mostraria memoria e nao previsao.

    ⚠️ As faixas rosa sao o alvo **real** (`baa >= 3` em t+7). Elas nao vem do
    modelo: sao o que aconteceu. Sem elas o grafico viraria "o modelo concorda
    consigo mesmo".
    """
    plt = _plt()

    do_local = quadro[quadro['local'] == local].sort_values('data')
    if do_local.empty:
        raise ValueError(f'Sem linhas para "{local}".')

    # 🚨 Um painel por variavel, e nao as quatro sobrepostas. A primeira versao
    # empilhava tudo num eixo so: o oxigenio varia +-5 mmol/m3 e a temperatura
    # +-1 C, entao a curva do oxigenio ocupava a figura inteira e as outras
    # tres viravam uma linha reta em zero. A legenda avisava que as alturas nao
    # eram comparaveis — o que nao ajuda quem simplesmente **nao consegue ver**
    # tres das quatro curvas. Padronizar resolveria a altura e custaria a
    # unidade fisica, que e o que torna a figura lida por alguem que conhece o
    # oceano e nao o modelo.
    colunas = list(colunas)
    figura, eixos = plt.subplots(
        len(colunas) + 1, 1, figsize=(12, 2.0 * len(colunas) + 4),
        sharex=True,
        gridspec_kw={'height_ratios': [1] * len(colunas) + [2.4]},
    )
    *acima, base = eixos

    datas = do_local['data']

    for eixo, coluna in zip(acima, colunas):
        eixo.plot(
            datas, do_local[coluna], linewidth=0.9,
            color=CORES.get(coluna, COR_NEUTRA),
        )
        eixo.axhline(0, color='#9aa3ab', linewidth=0.8)
        eixo.set_ylabel(
            f'{rotulo_curto(coluna)}\n({UNIDADES.get(coluna, "")} em 7 dias)',
            fontsize=8,
        )
        eixo.tick_params(axis='y', labelsize=8)
        eixo.spines[['top', 'right']].set_visible(False)
        # As mesmas faixas do painel de baixo, para o olho ligar o que estava
        # acontecendo na variavel ao que aconteceu no recife.
        for inicio, fim in _intervalos(datas, do_local['alvo_binario']):
            eixo.axvspan(inicio, fim, color=COR_EPISODIO, zorder=0)

    base.plot(
        datas, do_local[coluna_probabilidade], linewidth=1.2,
        color=COR_NEUTRA,
        label='o que PREVIMOS: chance de haver alerta térmico daqui a 7 dias',
    )
    base.axhline(
        limiar, color=COR_ALERTA, linestyle='--', linewidth=1.2,
        label=f'a partir daqui o site emite o aviso ({limiar:.0%})',
    )

    # As faixas do que realmente aconteceu, desenhadas por tras da curva.
    for inicio, fim in _intervalos(datas, do_local['alvo_binario']):
        base.axvspan(inicio, fim, color=COR_EPISODIO, zorder=0)
    # 🚨 O rotulo mais importante da figura inteira. "episodio real", que era o
    # texto anterior, le-se como "houve branqueamento" — e essa faixa nao diz
    # isso. Ela diz que a NOAA emitiu o alerta termico naqueles dias.
    base.plot(
        [], [], color=COR_EPISODIO, linewidth=8,
        label='o que ACONTECEU: a NOAA de fato emitiu o alerta térmico '
              '(não é registro de branqueamento)',
    )

    base.set_ylabel('Chance de alerta térmico\ndaqui a 7 dias')
    base.set_xlabel('Data')
    base.set_ylim(-0.02, 1.02)
    base.legend(fontsize=8, frameon=False, loc='center left')
    base.spines[['top', 'right']].set_visible(False)

    figura.suptitle(
        f'{local}\nO que o modelo viu, o que ele previu, e o que aconteceu',
        fontsize=12,
    )
    figura.tight_layout()

    alertas = len(list(_intervalos(datas, do_local['alvo_binario'])))
    legenda = (
        f'Recife: {local}. Painéis de cima: o que o modelo enxerga — quanto '
        'cada variável mudou em relação a sete dias antes, uma por linha, '
        'cada uma na sua própria unidade. Estão separadas porque o oxigênio '
        'oscila numa faixa cinco vezes maior que a temperatura e, num eixo '
        'único, apagaria as outras. Painel de baixo, e é aqui que estão as '
        'duas coisas que não devem ser confundidas: a LINHA CINZA é a nossa '
        'previsão — a chance de haver alerta térmico dali a sete dias, sempre '
        'calculada por um modelo que não tinha visto aquele ano. As FAIXAS '
        'ROSA são o que de fato aconteceu: os dias em que a NOAA emitiu o '
        f'alerta térmico ({alertas} períodos no intervalo mostrado). '
        'As faixas rosa NÃO são registros de branqueamento — ninguém mergulhou '
        'para observá-los. Onde a linha sobe dentro de uma faixa, o modelo '
        'antecipou o aviso; onde sobe fora dela, deu alarme falso; onde uma '
        'faixa passa sem a linha subir, o aviso escapou. Degraus na linha são '
        'esperados e não são defeito: a probabilidade é recalibrada por uma '
        'função escada.'
    )
    return _selar(f'linha_do_tempo_{local}', figura, legenda)


def _intervalos(datas, binario):
    """Os trechos contiguos em que o alvo vale 1, como pares (inicio, fim)."""
    inicio = anterior = None
    for data, valor in zip(datas, binario):
        if valor and inicio is None:
            inicio = data
        elif not valor and inicio is not None:
            yield inicio, anterior
            inicio = None
        anterior = data
    if inicio is not None:
        yield inicio, anterior


# ---------------------------------------------------------------------------
# 4. Resposta a cada variavel
# ---------------------------------------------------------------------------
def resposta_a_variavel(ajuste, quadro, colunas, limiar, pontos=60):
    """Como a probabilidade responde a uma variavel, com as outras paradas.

    Traduz o coeficiente — que vive em desvio-padrao — para a unidade fisica em
    que a pergunta e feita: quantos °C de aquecimento em 7 dias o modelo precisa
    ver para cruzar o limiar.

    🚨 **Uma linha aqui nao e uma previsao.** Ela e "se so esta variavel
    mudasse", e no oceano elas nao mudam sozinhas: aquecer altera oxigenio
    dissolvido. A curva descreve o **modelo**, nao o mar — e por isso os
    valores observados aparecem no rodape, para mostrar em que faixa a curva
    tem lastro e onde ela e extrapolacao.
    """
    import numpy as np
    import pandas as pd

    plt = _plt()

    medianas = {c: float(quadro[c].median()) for c in colunas}

    figura, eixos = plt.subplots(
        1, len(colunas), figsize=(3.4 * len(colunas), 4.4), sharey=True,
    )
    eixos = [eixos] if len(colunas) == 1 else list(eixos)

    for eixo, coluna in zip(eixos, colunas):
        observados = quadro[coluna].dropna()
        # Percentil 1 a 99: os extremos sao poucos pontos e esticariam o eixo
        # ate onde a curva nao tem lastro nenhum.
        baixo, alto = np.percentile(observados, [1, 99])
        faixa = np.linspace(baixo, alto, pontos)

        cenario = pd.DataFrame(
            {c: [medianas[c]] * pontos for c in colunas}
        )
        cenario[coluna] = faixa
        probabilidade = ajuste.prever_probabilidade(cenario)

        cor = CORES.get(coluna, COR_NEUTRA)
        eixo.plot(faixa, probabilidade, linewidth=2, color=cor)
        eixo.axhline(
            limiar, color=COR_ALERTA, linestyle='--', linewidth=1.2,
            label=f'o site avisa a partir daqui ({limiar:.0%})',
        )
        eixo.axvline(medianas[coluna], color='#9aa3ab', linewidth=1)

        # Onde os dados de fato estao. Sem isto, a curva parece valer em toda a
        # largura do eixo.
        eixo.plot(
            observados, np.full(len(observados), -0.03),
            '|', color=cor, alpha=0.05, markersize=6,
        )

        eixo.set_title(rotulo(coluna), fontsize=9)
        eixo.set_xlabel(UNIDADES.get(coluna, ''))
        eixo.set_ylim(-0.06, 1.02)
        # O eixo acompanha a varredura, e nao os extremos observados: com os
        # 2% de cauda dentro do quadro a curva termina no meio do painel e
        # parece truncada por defeito. A cauda continua declarada na legenda.
        folga = 0.03 * (alto - baixo)
        eixo.set_xlim(baixo - folga, alto + folga)
        eixo.legend(fontsize=8, frameon=False)
        eixo.spines[['top', 'right']].set_visible(False)

    eixos[0].set_ylabel('Chance de alerta térmico\ndaqui a 7 dias')
    figura.suptitle(
        'Quanto cada variável precisa mudar para o site emitir o aviso\n'
        'cada painel move uma variável de cada vez, com as outras três paradas '
        'no valor típico   |   os traços embaixo mostram onde os dados '
        'realmente existem',
        fontsize=10,
    )
    figura.tight_layout()

    legenda = (
        'Comportamento do modelo que está no ar agora. Cada painel varia uma '
        'única variável ao longo dos valores observados, mantendo as outras '
        'três no valor típico (mediana), e mostra a chance de alerta térmico '
        'resultante. A linha vertical cinza marca esse valor típico; a '
        'tracejada vermelha, o ponto a partir do qual o site emite o aviso. '
        'Os traços na base são os valores realmente registrados — onde eles '
        'rareiam, a curva é suposição. Atenção, e isto não é detalhe: a curva '
        'descreve o MODELO, não o mar. No oceano as variáveis não se movem '
        'isoladamente (aquecer altera o oxigênio dissolvido), então nenhuma '
        'linha aqui é uma previsão do que aconteceria de fato.'
    )
    return _selar('resposta_a_variavel', figura, legenda)
