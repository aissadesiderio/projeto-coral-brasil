"""Tudo o que o projeto guarda de um local — inclusive o que o modelo ignora.

🚨 **Ate 12/08/2026 o site media oito variaveis por recife e mostrava duas.**
A ingestao grava `sst`, `dhw`, `baa`, `baa_area_alerta`, `hotspot` e
`sst_anomalia` do NOAA CRW, mais `salinidade` e `oxigenio` do Copernicus — sao
~7.200 medicoes de cada, por local, desde 2020. A tela do recife desenhava
`sst` e `dhw`, e as outras seis nao apareciam em lugar nenhum: nem numa lista,
nem num numero, nem numa frase dizendo que existiam. Quem visitasse o site
concluiria, corretamente pelo que via, que o projeto so tem duas variaveis.

⚠️ **O recorte da tela nao estava errado — a omissao estava.** `VARIAVEIS_DA_SERIE`
limita o *grafico* a `sst` e `dhw` por um motivo medido (docs/RESULTADOS.md §7:
embaralhar `dhw` derruba a PR-AUC de 0,84 para 0,30; salinidade e oxigenio
derrubam ~0,00), e por um motivo visual: seis curvas no mesmo bloco dao peso
igual a variaveis que nao pesam. Nada disso justifica **nao dizer que as outras
existem**. Sao coisas diferentes: escolher o que desenhar e esconder o que se
tem.

Este modulo responde a segunda pergunta — *o que ha aqui?* — e nao a primeira.
Devolve, por variavel: quantas medicoes, de quando a quando, de que fonte, e
**qual e o papel dela no modelo servido**, que e a informacao que impede a
leitura errada oposta: alguem ver `hotspot` listado e supor que ele entra na
previsao.

**Uma consulta so.** Reaproveita `cobertura.resumo()`, ja agregado por
`(fonte, variavel, local)` — o mesmo que o catalogo usa. Nao ha segunda ida ao
banco para montar o acervo de um local.
"""

from .models import MedicaoAmbiental

# O rotulo e a unidade de cada variavel canonica, lidos do proprio modelo.
#
# ⚠️ Derivado de `MedicaoAmbiental.VARIAVEL_CHOICES`, e nao redigitado: uma
# segunda lista de rotulos diverge da primeira no dia em que alguem acrescentar
# uma variavel — e o sintoma seria uma variavel aparecendo no acervo sem nome.
ROTULOS = dict(MedicaoAmbiental.VARIAVEL_CHOICES)


# --- o papel de cada variavel no modelo servido -----------------------------
#
# 🚨 **Esta e a parte que evita a leitura errada.** Sem ela, listar `hotspot` e
# `baa` ao lado de `sst` sugere que as oito alimentam a previsao — quando o
# artefato servido usa quatro derivadas (`*_variacao_7d` de `sst`, `dhw`,
# `salinidade` e `oxigenio`), e `baa` nao e entrada nenhuma: e o **alvo**, o que
# o modelo tenta prever. Confundir alvo com feature e o mal-entendido mais caro
# que um painel de ML pode induzir.
#
# ⚠️ Os papeis sao declarados aqui, e nao lidos do `.json` do artefato, porque
# descrevem o **desenho do experimento** (docs/VARIAVEIS.md secoes 3, 5 e 6) e
# nao a lista de colunas de uma versao especifica. `colunas_do_modelo` abaixo le
# o artefato para o que e de fato versao-dependente.
FEATURE = 'feature'
ALVO = 'alvo'
OPCIONAL = 'opcional'
CONTEXTO = 'contexto'

PAPEIS = {
    FEATURE: 'Entra na previsao',
    ALVO: 'E o que o modelo preve',
    OPCIONAL: 'Coletada, fora do modelo',
    CONTEXTO: 'Contexto, fora do modelo',
}

PAPEL_DA_VARIAVEL = {
    # As quatro que viram janelas retrospectivas no artefato servido.
    'sst': FEATURE,
    'dhw': FEATURE,
    'salinidade': FEATURE,
    'oxigenio': FEATURE,
    # 🚨 `baa >= 3` em t+7 e o alvo declarado no artefato. Nao e entrada.
    'baa': ALVO,
    # Coletadas do mesmo produto do CRW, mantidas por decisao registrada em
    # docs/VARIAVEIS.md secao 5 ("variaveis opcionais"): custam zero a mais na
    # ingestao e servem para conferir o alvo a mao.
    'hotspot': OPCIONAL,
    'sst_anomalia': OPCIONAL,
    'baa_area_alerta': CONTEXTO,
    # Previstas no contrato canonico, ainda sem conector. Aparecem aqui so se
    # alguem ingerir — a funcao nao inventa linha para variavel sem medicao.
    'kd490': OPCIONAL,
    'clorofila': OPCIONAL,
    'par': OPCIONAL,
}

# Motivo curto de cada papel nao-feature, para a tela nao precisar redigi-lo.
MOTIVOS = {
    ALVO: (
        'O modelo servido preve "baa >= 3 daqui a 7 dias". Esta variavel e a '
        'resposta que ele tenta acertar, nao um dado de entrada.'
    ),
    OPCIONAL: (
        'Coletada porque vem no mesmo produto e nao custa nada a mais. Ficou '
        'fora do modelo por decisao registrada em docs/VARIAVEIS.md.'
    ),
    CONTEXTO: (
        'Descreve quanto da area do recife esta em alerta. Serve para ler o '
        'alerta, nao para calcula-lo.'
    ),
}


def _unidade(rotulo: str) -> str:
    """`'Salinidade (PSU)'` -> `'PSU'`. Vazio quando o rotulo nao traz unidade."""
    if rotulo.endswith(')') and '(' in rotulo:
        return rotulo[rotulo.rindex('(') + 1:-1]
    return ''


def _nome(rotulo: str) -> str:
    """`'Salinidade (PSU)'` -> `'Salinidade'`."""
    if rotulo.endswith(')') and '(' in rotulo:
        return rotulo[:rotulo.rindex('(')].strip()
    return rotulo


def _consulta(slug: str, variavel: str) -> str:
    """A URL que devolve exatamente estas medicoes.

    Mesmo principio de `cobertura._consulta_de_medicoes`: um numero anunciado
    sem forma de conferir e uma afirmacao sem recibo.
    """
    return f'/api/medicoes/?local={slug}&variavel={variavel}'


def para_local(slug: str, medicoes=None) -> list:
    """O acervo de um local: uma linha por variavel **que tem medicao**.

    Ordenado por papel (entradas do modelo primeiro, depois o alvo, depois o
    resto) e, dentro de cada papel, por nome — para a tela nao precisar decidir
    ordem e para a lista nao mudar de ordem entre requisicoes.

    ⚠️ **Nao lista variavel sem medicao.** Uma linha "kd490 — 0 medicoes" seria
    lida como lacuna deste recife, quando na verdade nenhum recife tem: falta o
    conector, nao o dado deste local. Isso e assunto do catalogo, que ja diz
    quais datasets sao referencia externa (`cobertura.MOTIVO_EXTERNO`).
    """
    from . import cobertura

    if medicoes is None:
        medicoes = cobertura.resumo()

    por_variavel = {}
    for (fonte, variavel, local), dados in medicoes.items():
        if local != slug:
            continue

        linha = por_variavel.setdefault(
            variavel,
            {'n_medicoes': 0, 'fontes': set(), 'inicio': None, 'fim': None},
        )
        linha['n_medicoes'] += dados['n']
        linha['fontes'].add(fonte)
        # Uma variavel pode vir de duas fontes (SST vem do CRW e do Copernicus).
        # A cobertura da variavel e a uniao das duas, nao a de uma delas.
        if dados['inicio'] and (not linha['inicio'] or dados['inicio'] < linha['inicio']):
            linha['inicio'] = dados['inicio']
        if dados['fim'] and (not linha['fim'] or dados['fim'] > linha['fim']):
            linha['fim'] = dados['fim']

    ordem_dos_papeis = {FEATURE: 0, ALVO: 1, CONTEXTO: 2, OPCIONAL: 3}

    acervo = []
    for variavel, linha in por_variavel.items():
        rotulo = ROTULOS.get(variavel, variavel)
        papel = PAPEL_DA_VARIAVEL.get(variavel, OPCIONAL)
        acervo.append({
            'variavel': variavel,
            'nome': _nome(rotulo),
            'unidade': _unidade(rotulo),
            'n_medicoes': linha['n_medicoes'],
            'data_inicio': linha['inicio'],
            'data_fim': linha['fim'],
            'fontes': sorted(linha['fontes']),
            'papel': papel,
            'papel_rotulo': PAPEIS[papel],
            'entra_no_modelo': papel == FEATURE,
            'motivo': MOTIVOS.get(papel),
            'consulta': _consulta(slug, variavel),
        })

    acervo.sort(key=lambda item: (ordem_dos_papeis[item['papel']], item['nome']))
    return acervo
