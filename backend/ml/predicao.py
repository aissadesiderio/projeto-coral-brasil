"""Aplica o modelo treinado a serie de hoje. E o que o painel consome.

Todo o resto de `backend/ml/` existe para **medir**: monta conjunto com alvo
conhecido, treina, avalia. Este modulo faz a operacao inversa e menos vistosa —
pega o estado atual de um recife, para o qual o alvo **ainda nao existe**, e
devolve uma probabilidade.

🚨 **O risco principal deste arquivo e silencioso, e vale entender antes de
mexer.** O modelo foi treinado com quatro colunas de nome
`<variavel>_variacao_7d`. Se aqui a janela fosse recalculada com outra
convencao — outro sinal, outro numero de dias, outro tratamento de dia
faltante — o `Pipeline` receberia uma matriz com **os nomes certos e o conteudo
errado**, e responderia com aparente normalidade. Nao existe excecao que
apareca: `predict_proba` aceita qualquer matriz com quatro colunas numericas.

A defesa nao e disciplina, e construcao: `_janela_do_nome` **traduz o nome da
coluna de volta num `dataset.Janela`** e o calculo passa pelo mesmo
`dataset.aplicar_janela` que o treino usou. Se a traducao nao fechar exatamente
(`Janela(...).nome == nome`), o modulo levanta erro em vez de adivinhar. Nao ha
segunda implementacao da janela para divergir da primeira, porque nao ha
segunda implementacao.

**Tres decisoes de comportamento**, registradas em docs/arquitetura.md:

**1. Recusar em vez de preencher.** Janela incompleta vira `SemDadoSuficiente`,
nunca zero. O motivo nao e purismo: **zero e valor legitimo para uma
variacao**. `sst_variacao_7d = 0` afirma "a temperatura nao mudou". Preencher
lacuna com zero nao produz um numero suspeito que alguem note — produz a
afirmacao mais tranquilizadora possivel, exatamente quando o dado sumiu. E o
mesmo defeito do `carregar_historico.py` legado, que gravava pH 0.

**2. A data-base viaja junto.** As duas fontes tem latencia, e ela varia. Um
risco sem a data sobre a qual foi calculado e lido como "agora", que e
justamente o que ele nao e. Por isso `Risco` carrega `data_base`, `data_alvo`,
`dias_de_atraso` e `limitado_por`.

**3. Local fora do treino nao recebe resposta.** O modelo viu tres pontos do
litoral; responder sobre um quarto seria inventar cobertura.
"""

import threading
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import NamedTuple

from .dataset import Janela, aplicar_janela, carregar_largo

# Sufixo que fecha o nome de uma feature de janela: `..._7d`.
SUFIXO_DIAS = 'd'


class SemDadoSuficiente(Exception):
    """A janela do modelo nao esta completa na data mais recente da serie.

    Carrega `faltando`: a lista de `(variavel, data)` que o calculo precisaria
    e nao encontrou. Sem isso a mensagem seria "sem dado", que nao diz a quem
    opera se o problema e a ingestao de ontem ou uma lacuna de tres semanas.
    """

    def __init__(self, mensagem, faltando=()):
        super().__init__(mensagem)
        self.faltando = tuple(faltando)


class ColunaNaoTraduzivel(ValueError):
    """O nome da coluna do modelo nao corresponde a uma janela conhecida."""


def _janela_do_nome(nome):
    """`'sst_variacao_7d'` -> `Janela('sst', 7, 'variacao')`.

    ⚠️ **A volta e conferida.** Depois de partir o nome, o resultado e
    remontado por `Janela.nome` e comparado com a entrada. Uma coluna que o
    modelo tenha visto e que este codigo nao saiba reproduzir **para o
    programa** — o contrario seria calcular uma coisa parecida e chamar pelo
    mesmo nome.

    O corte e pela direita (`rsplit`) porque a variavel pode ter underscore
    (`baa_area_alerta`), enquanto operacao e dias nunca tem.
    """
    partes = nome.rsplit('_', 2)
    if len(partes) != 3:
        raise ColunaNaoTraduzivel(
            f'A coluna "{nome}" nao tem o formato <variavel>_<operacao>_<dias>d. '
            f'O painel so sabe reconstruir features de janela.'
        )

    variavel, operacao, sufixo = partes
    if not sufixo.endswith(SUFIXO_DIAS) or not sufixo[:-1].isdigit():
        raise ColunaNaoTraduzivel(
            f'A coluna "{nome}" nao termina em numero de dias (ex.: "7d").'
        )

    janela = Janela(variavel=variavel, dias=int(sufixo[:-1]), operacao=operacao)
    if janela.nome != nome:
        raise ColunaNaoTraduzivel(
            f'A coluna "{nome}" foi lida como {janela} mas isso remonta '
            f'"{janela.nome}". Traducao ambigua: recusada.'
        )
    return janela


def janelas_do_modelo(colunas):
    """As janelas que o modelo espera, na ordem em que foi treinado."""
    return tuple(_janela_do_nome(c) for c in colunas)


def _dias_necessarios(janela, data_base):
    """Que dias da serie a janela le para produzir o valor em `data_base`.

    A diferenca entre as operacoes nao e detalhe: `variacao` compara **dois
    instantes** e nao se importa com o meio — a diferenca entre 11/01 e 04/01
    continua sendo de sete dias mesmo que 07/01 falte. Ja `media` e `maximo`
    resumem o intervalo inteiro, e um dia faltando muda o resultado. Mesma
    regra documentada em `dataset.aplicar_janela`; repetida aqui porque e ela
    que decide o que entra em `faltando`.
    """
    if janela.operacao == 'variacao':
        return [data_base - timedelta(days=janela.dias), data_base]
    return [
        data_base - timedelta(days=n) for n in range(janela.dias - 1, -1, -1)
    ]


@dataclass(frozen=True)
class Risco:
    """A resposta para um recife: probabilidade, quando, e sobre o que.

    Nenhum campo aqui e enfeite. `limiar` acompanha `probabilidade` porque nao
    existe corte natural — a recalibracao isotonica moveu o ponto equivalente
    de 0,50 para 0,20 (docs/RESULTADOS.md secao 22.5), e quem consome precisa
    poder discordar do corte sem refazer a conta.
    """

    local: str
    data_base: date
    data_alvo: date
    probabilidade: float
    limiar: float
    dias_de_atraso: int
    entradas: dict = field(default_factory=dict)
    # As variaveis cuja serie para exatamente na `data_base` enquanto outras
    # seguem adiante. Vazio quando a borda e reta. Ver `_borda_completa`: sem
    # este campo, uma fonte quebrada vira "dado um pouco mais velho" e nada na
    # resposta diz de quem e a culpa.
    limitado_por: tuple = ()

    @property
    def alerta(self):
        return self.probabilidade >= self.limiar

    def nivel(self, escala=None):
        """O degrau da escala em que esta probabilidade cai.

        ⚠️ Nao substitui `alerta`, que continua sendo o corte binario que viaja
        no payload desde 27/07. Os dois coexistem porque respondem a perguntas
        diferentes: `alerta` diz *"e para agir?"*, `nivel` diz *"com que
        urgencia, e o que se espera de quem le"*. Ver `ml/niveis.py`.
        """
        from . import niveis

        return niveis.classificar(self.probabilidade, escala)

    @property
    def no_extremo(self):
        """A probabilidade saiu exatamente 0 ou exatamente 1.

        🚨 **Isto acontece, e nao e defeito — e consequencia da recalibracao
        isotonica, que e uma funcao escada.** Medido em 27/07/2026 sobre as
        7.095 amostras de treino: 313 valores distintos, **864 amostras
        (12,2%) em p = 0,000 exato** e 121 em p = 1,000 exato. Duas entradas
        diferentes caem no mesmo degrau e saem com o mesmo numero.

        O que a isotonica diz em p = 0 nao e "impossivel": e "no degrau mais
        baixo, nenhuma das amostras de treino virou alerta". Isso limita a
        probabilidade, nao a zera. Exibir "0% de risco" ou "100% de risco"
        traduz um degrau finito em certeza, e nenhum dos dois e defensavel num
        painel publico.

        Este campo existe para a camada de exibicao poder tratar o caso sem
        que a API precise **falsificar o numero** — cortar para 0,001 e 0,999
        seria inventar precisao que o modelo nao tem, na direcao oposta.
        """
        return self.probabilidade <= 0.0 or self.probabilidade >= 1.0


class Entradas(NamedTuple):
    """O que a predicao leu: em que dia, com que valores, e quem segurou o dia."""

    data_base: date
    valores: dict
    limitado_por: tuple = ()


def _borda_completa(largo, variaveis):
    """A ultima data em que **todas** as variaveis do modelo existem.

    Devolve `(data_base, limitado_por)`. `limitado_por` so vem preenchido
    quando a borda e irregular — as variaveis cuja serie para exatamente ali,
    enquanto outras seguem adiante.

    🚨 **Isto mudou em 30/07/2026, e a mudanca merece a explicacao inteira.**
    Ate entao a data-base era `max(...)` sobre a serie inteira: a ultima data
    em que **qualquer** variavel tivesse valor. A intencao era boa e continua
    valendo — nao andar para tras procurando um dia que funcione, porque isso
    mascararia ingestao parada como operacao normal.

    O que a intencao nao previu e que **as duas fontes nunca terminam no mesmo
    dia**. O CoralTemp da NOAA publica com 1 a 3 dias de atraso; a analise do
    Copernicus publica ate ontem. Entao a serie termina sempre irregular, com
    salinidade e oxigenio um a tres dias adiante de `sst` e `dhw`. Como a
    data-base caia na ponta mais adiantada, a janela nunca fechava, e o painel
    respondia `disponivel: false` **nos tres recifes, na maior parte dos dias**
    — esperando um dado que ele nem precisaria estar esperando ali.

    Medido em duas maquinas independentes:

    | Quando | Copernicus | NOAA | Painel |
    |---|---|---|---|
    | 29/07/2026 | ate 27/07 | ate 24/07 | indisponivel nos 3 |
    | 30/07/2026 | ate 29/07 | ate 28/07 | indisponivel nos 3 |

    A correcao **nao** e passar a andar para tras. E reconhecer que havia dois
    estados sendo tratados como um:

    | Estado | Agora | Por que |
    |---|---|---|
    | **borda irregular** — cada fonte com sua latencia | responde na ultima data completa, declarando `limitado_por` | e o formato normal de uma serie multi-fonte, e o atraso ja viaja no payload |
    | **buraco no meio** — falta um dia dentro da janela | **recusa** | continua sendo defeito, e nenhum numero honesto sai dali |

    A diferenca e onde a borda direita da janela cai, e nao varrer para tras
    ate achar um dia que funcione: a janela ainda precisa fechar **na** data
    escolhida, e um buraco interno continua recusando exatamente como antes.

    ⚠️ **O risco que esta mudanca cria, e como ele fica visivel.** Uma fonte
    que quebre de vez deixa de bloquear o painel e passa a apenas atrasa-lo —
    que e o sintoma mais silencioso dos dois. Por isso `limitado_por` existe e
    vai no payload: quem opera consegue ler *qual* conector esta segurando a
    borda, sem precisar cruzar `/api/medicoes/` variavel a variavel. O
    `dias_de_atraso` diz ha quanto tempo; o `limitado_por` diz por causa de
    quem.
    """
    completos = largo[list(variaveis)].dropna(how='any')
    fim_da_serie = max(largo.dropna(how='all').index)

    if not len(completos):
        # Nenhum dia tem tudo. Devolve o fim da serie de proposito: a
        # conferencia da janela, logo adiante, produz o diagnostico por
        # variavel e por dia, que e mais util do que "nao ha dia completo".
        return fim_da_serie, ()

    data_base = max(completos.index)
    if data_base == fim_da_serie:
        return data_base, ()

    limitado_por = tuple(
        v for v in variaveis if largo[v].last_valid_index() == data_base
    )
    return data_base, limitado_por


def montar_entradas(local, colunas, hoje=None):
    """Os valores das features na ultima data completa da serie do local.

    Devolve `Entradas(data_base, valores, limitado_por)`. Levanta
    `SemDadoSuficiente` se a serie estiver vazia ou se a janela nao fechar na
    data escolhida.

    A escolha da data-base — e a razao de ela nao ser mais simplesmente a
    ultima data da serie — esta em `_borda_completa`.
    """
    import pandas as pd

    janelas = janelas_do_modelo(colunas)
    variaveis = sorted({j.variavel for j in janelas})

    largo, _ = carregar_largo(local, variaveis)
    if not len(largo) or largo.dropna(how='all').empty:
        raise SemDadoSuficiente(
            f'Nao ha medicao de {variaveis} para "{local.slug}". '
            f'Rode a ingestao antes de pedir predicao.'
        )

    data_base, limitado_por = _borda_completa(largo, variaveis)

    valores, faltando = {}, []
    for janela in janelas:
        serie = largo[janela.variavel]
        # 🚨 O mesmo `aplicar_janela` do treino. Ver o cabecalho do modulo.
        calculada = aplicar_janela(serie, janela)
        valor = calculada.get(data_base)

        if valor is None or pd.isna(valor):
            faltando += [
                (janela.variavel, dia)
                for dia in _dias_necessarios(janela, data_base)
                if dia not in serie.index or pd.isna(serie.get(dia))
            ]
            continue
        valores[janela.nome] = float(valor)

    if faltando:
        resumo = ', '.join(
            f'{v} em {d.isoformat()}' for v, d in sorted(set(faltando))[:6]
        )
        raise SemDadoSuficiente(
            f'A janela do modelo nao fecha em {data_base.isoformat()} para '
            f'"{local.slug}": falta {resumo}'
            + (' (e outros)' if len(set(faltando)) > 6 else '')
            + '. Recusado em vez de preenchido: zero e um valor legitimo para '
            'uma variacao, entao preencher lacuna aqui devolveria "nada '
            'mudou" justamente onde o dado sumiu.',
            faltando=sorted(set(faltando)),
        )

    return Entradas(data_base, valores, limitado_por)


def calcular(local, ajuste, limiar, hoje=None):
    """Aplica o modelo carregado ao estado atual de um recife."""
    import pandas as pd

    hoje = hoje or date.today()
    lidas = montar_entradas(local, ajuste.colunas, hoje)

    quadro = pd.DataFrame([lidas.valores])
    probabilidade = float(ajuste.prever_probabilidade(quadro)[0])

    return Risco(
        local=local.slug,
        data_base=lidas.data_base,
        data_alvo=lidas.data_base + timedelta(days=ajuste.horizonte),
        probabilidade=probabilidade,
        limiar=limiar,
        dias_de_atraso=(hoje - lidas.data_base).days,
        entradas=lidas.valores,
        limitado_por=lidas.limitado_por,
    )


# ---------------------------------------------------------------------------
# Carregamento do artefato
# ---------------------------------------------------------------------------
# `joblib.load` de um Pipeline nao e caro, mas tambem nao e de graca, e o painel
# e um endpoint publico: carregar o mesmo arquivo a cada requisicao seria pagar
# leitura de disco e desserializacao por visita.
#
# ⚠️ **O cache e invalidado por mtime, e nao por tempo.** `treinar_final`
# reescreve o artefato; um cache por TTL continuaria servindo o modelo antigo
# por N minutos depois de retreinar, sem nada indicando isso. O mtime muda no
# instante em que o arquivo muda.
_TRAVA = threading.Lock()
_CACHE = {}


def carregar_modelo(nome, pasta=None):
    """Devolve `(ajuste, metadados)`, reaproveitando o artefato ja lido."""
    from . import persistencia

    caminho_modelo, _ = persistencia._caminhos(nome, pasta)
    try:
        marca = caminho_modelo.stat().st_mtime_ns
    except OSError:
        marca = None

    chave = (nome, str(pasta or ''))
    with _TRAVA:
        guardado = _CACHE.get(chave)
        if guardado and guardado[0] == marca and marca is not None:
            return guardado[1], guardado[2]

    metadados = persistencia.ler_metadados(nome, pasta)
    ajuste = persistencia.carregar(nome, pasta)

    with _TRAVA:
        _CACHE[chave] = (marca, ajuste, metadados)
    return ajuste, metadados


def marca_do_modelo(nome, pasta=None):
    """A identidade do artefato no disco: `mtime` em nanossegundos, ou `None`.

    🚨 Existe para entrar em chave de cache de quem depende do modelo. Sem ela,
    retreinar nao mudaria o painel ate a proxima ingestao — o cache serviria a
    probabilidade do modelo anterior com cara de atual, e essa e a forma mais
    silenciosa possivel de estar errado: o numero muda de significado sem mudar
    de aparencia.

    ⚠️ Devolve `None` quando o arquivo nao existe. Quem monta chave com `None`
    passa a nao reaproveitar nada — que e o comportamento certo, porque sem
    artefato o painel responde 503 e nao ha resultado para guardar.
    """
    from . import persistencia

    caminho_modelo, _ = persistencia._caminhos(nome, pasta)
    try:
        return caminho_modelo.stat().st_mtime_ns
    except OSError:
        return None


def esquecer_modelos():
    """Descarta o cache. Existe para teste e para o retreino em processo vivo."""
    with _TRAVA:
        _CACHE.clear()
