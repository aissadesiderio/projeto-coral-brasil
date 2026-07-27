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
justamente o que ele nao e. Por isso `Risco` carrega `data_base`, `data_alvo` e
`dias_de_atraso`.

**3. Local fora do treino nao recebe resposta.** O modelo viu tres pontos do
litoral; responder sobre um quarto seria inventar cobertura.
"""

import threading
from dataclasses import dataclass, field
from datetime import date, timedelta

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

    @property
    def alerta(self):
        return self.probabilidade >= self.limiar

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


def montar_entradas(local, colunas, hoje=None):
    """Os valores das features na data mais recente da serie do local.

    Devolve `(data_base, {coluna: valor})`. Levanta `SemDadoSuficiente` se a
    serie estiver vazia ou se a janela nao fechar na data mais recente.

    ⚠️ **A data-base e a ultima data da serie, e nao a ultima data que
    funciona.** Andar para tras ate achar um dia com janela completa daria
    sempre uma resposta — e mascararia uma serie furada como operacao normal.

    Isso **nao** e o mesmo que uma serie que simplesmente termina mais cedo.
    Sao dois estados diferentes e o codigo os trata diferente de proposito:

    | Estado | O que acontece | Por que |
    |---|---|---|
    | a serie acaba em `t-2` | responde, com `data_base = t-2` e atraso 2 | ingestao atrasada e normal, e o atraso fica declarado |
    | a serie vai ate `t` mas falta `t-7` | **recusa** | a janela nao fecha, e nao ha numero honesto a dar |

    A primeira e indistinguivel de "a ingestao de hoje ainda nao rodou"; a
    segunda e um buraco no meio do que ja foi coletado.
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

    data_base = max(largo.dropna(how='all').index)

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

    return data_base, valores


def calcular(local, ajuste, limiar, hoje=None):
    """Aplica o modelo carregado ao estado atual de um recife."""
    import pandas as pd

    hoje = hoje or date.today()
    data_base, entradas = montar_entradas(local, ajuste.colunas, hoje)

    quadro = pd.DataFrame([entradas])
    probabilidade = float(ajuste.prever_probabilidade(quadro)[0])

    return Risco(
        local=local.slug,
        data_base=data_base,
        data_alvo=data_base + timedelta(days=ajuste.horizonte),
        probabilidade=probabilidade,
        limiar=limiar,
        dias_de_atraso=(hoje - data_base).days,
        entradas=entradas,
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


def esquecer_modelos():
    """Descarta o cache. Existe para teste e para o retreino em processo vivo."""
    with _TRAVA:
        _CACHE.clear()
