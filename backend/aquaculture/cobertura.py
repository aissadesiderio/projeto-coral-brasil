"""Cobertura real de cada dataset do catalogo, derivada do banco.

Existe por um defeito medido em 27/07/2026. A pagina "Banco de Dados"
anunciava **9 datasets**; o projeto espelha **3**. Os outros seis — pH,
clorofila, nitrato, thetao, KD490 e o SST do Met Office — apareciam com titulo,
resumo, formato e periodo, e nao tinham **uma unica medicao** no banco. Os tres
reais declaravam `data_fim` em 2025 enquanto a serie ja ia ate 24/07/2026.

🚨 **A causa e estrutural, e nao humana.** A cobertura estava gravada a mao nos
campos `data_inicio`/`data_fim`. Toda copia guardada envelhece em silencio — e
esta envelheceu do jeito pior possivel, num projeto cuja contribuicao central e
proveniencia. E a mesma regra que ja levou o `.docx`, o `.joblib` e o grafo do
Neo4j a serem derivados: **o que da para recalcular nao se guarda**.

⚠️ **As duas datas continuam existindo, e nao sao redundantes** — mas a
diferenca entre elas nao e a que parece a primeira vista, e vale ser exato:

| Campo | Responde |
|---|---|
| `data_inicio`/`data_fim` (gravados) | o periodo do **arquivo CSV** em `backend/dados/` |
| `cobertura.data_inicio`/`data_fim` (derivados) | ate onde **a API** tem dado |

Os gravados sao lidos do proprio arquivo por `inventario_datasets.py`, e
naquele contexto sao honestos: descrevem o acervo em disco. O erro nunca foi o
numero — foi **a pagina apresenta-los como se fossem a cobertura do projeto**.

E ha uma consequencia que precisa ficar dita: `backend/dados/` e a pasta legada
que nada mais le e que o roadmap manda apagar. No dia em que ela sumir, os nove
registros viram `ativo=False` pela regra 2 deste inventario — e a unica
cobertura que sobrevive e a derivada daqui.

**Uma consulta so, e nao uma por dataset.** O agrupamento
`(fonte, variavel, local)` tem 24 linhas no total; nove agregacoes separadas
custariam nove idas ao banco para responder o que uma responde.
"""

from django.db.models import Count, Max, Min

from .models import MedicaoAmbiental

# Chave do agrupamento que a consulta unica devolve.
CAMPOS_GRUPO = ('fonte', 'variavel', 'local_recife__slug')

MOTIVO_EXTERNO = (
    'Referencia externa: o dataset existe no provedor e este projeto nao o '
    'espelha. Nenhuma medicao dele esta no banco.'
)
MOTIVO_SEM_DADO = (
    'Declarado como espelhado, mas nao ha medicao correspondente no banco. '
    'Rode a ingestao ou corrija o vinculo do catalogo.'
)


def resumo():
    """`{(fonte, variavel, local): {n, inicio, fim}}` — uma consulta.

    ⚠️ **Nao depende de quais datasets vao ser descritos**, e e por isso que
    ela e o que viaja no contexto do serializer. A primeira versao passava o
    mapa ja montado, o que obrigava a view a avaliar o queryset uma segunda vez
    so para monta-lo — tres consultas onde bastavam duas. Um teste de contagem
    pegou.
    """
    agrupado = (
        MedicaoAmbiental.objects
        .values(*CAMPOS_GRUPO)
        .annotate(n=Count('id'), inicio=Min('data'), fim=Max('data'))
    )

    return {
        (linha['fonte'], linha['variavel'], linha['local_recife__slug']): {
            'n': linha['n'],
            'inicio': linha['inicio'],
            'fim': linha['fim'],
        }
        for linha in agrupado
    }


def _consulta_de_medicoes(dataset, variaveis):
    """A URL que devolve exatamente estas medicoes.

    Nao e enfeite: e o que permite a quem le a pagina **conferir** o numero
    anunciado, em vez de acreditar nele. Sem isso, "4.794 medicoes" e uma
    afirmacao sem recibo.
    """
    partes = [f'fonte={dataset.fonte_medicao}']
    if dataset.local_slug:
        partes.append(f'local={dataset.local_slug}')
    partes += [f'variavel={v}' for v in sorted(variaveis)]
    return '/api/medicoes/?' + '&'.join(partes)


def para(dataset, medicoes=None):
    """A cobertura de **um** dataset. Mede sozinha se o resumo nao vier."""
    return _cobertura_de(dataset, resumo() if medicoes is None else medicoes)


def _cobertura_de(dataset, medicoes):
    if not dataset.espelhado:
        return {
            'espelhado': False,
            'motivo': MOTIVO_EXTERNO,
            'n_medicoes': 0,
            'variaveis': [],
            'locais': [],
            'data_inicio': None,
            'data_fim': None,
            'consulta': None,
        }

    declaradas = set(dataset.variaveis)
    encontradas = {}

    for (fonte, variavel, local), dados in medicoes.items():
        if fonte != dataset.fonte_medicao:
            continue
        # Variaveis vazias = todas as daquela fonte. E deliberado: um dataset
        # que descreve "o produto CRW inteiro" nao deveria precisar repetir a
        # lista de variaveis que o conector ja define.
        if declaradas and variavel not in declaradas:
            continue
        if dataset.local_slug and local != dataset.local_slug:
            continue
        encontradas[(variavel, local)] = dados

    if not encontradas:
        return {
            'espelhado': True,
            'motivo': MOTIVO_SEM_DADO,
            'n_medicoes': 0,
            'variaveis': sorted(declaradas),
            'locais': [],
            'data_inicio': None,
            'data_fim': None,
            'consulta': None,
        }

    variaveis = sorted({v for v, _ in encontradas})
    locais = sorted({l for _, l in encontradas})
    inicios = [d['inicio'] for d in encontradas.values() if d['inicio']]
    fins = [d['fim'] for d in encontradas.values() if d['fim']]

    return {
        'espelhado': True,
        'motivo': None,
        'n_medicoes': sum(d['n'] for d in encontradas.values()),
        'variaveis': variaveis,
        'locais': locais,
        'data_inicio': min(inicios) if inicios else None,
        'data_fim': max(fins) if fins else None,
        'consulta': _consulta_de_medicoes(dataset, variaveis),
    }


def calcular(datasets, medicoes=None):
    """`{dataset_id: cobertura}` para uma colecao de datasets.

    `medicoes` e o retorno de `resumo()`. Passe-o quando ja tiver — e o que
    evita repetir a agregacao.
    """
    datasets = list(datasets)
    if not datasets:
        return {}

    if medicoes is None:
        medicoes = resumo()

    return {d.id: _cobertura_de(d, medicoes) for d in datasets}
