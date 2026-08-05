"""Confere que a camada de persistencia esta como o projeto declara.

Existe porque "validada" precisava virar algo **reproduzivel**. Ate 28/07/2026
a validacao da camada de persistencia era uma afirmacao: as constraints estavam
no modelo, os indices apareciam nas migracoes, e ninguem nunca tinha conferido
que o banco de fato os tinha — nem medido as consultas que dependem deles.

Mesmo padrao do `neo4j_projetar`, que confere sozinho ao final: uma verificacao
que so existe na cabeca de quem a fez nao e verificacao.

**O que este modulo cobre, e o que fica de fora.**

| Aqui | Na suite de testes |
|---|---|
| o banco **real** tem os indices e constraints | a constraint **recusa** duplicata |
| as consultas quentes rodam dentro do limite | as regras de negocio |
| o Neo4j tem as constraints de unicidade | a projecao monta o Cypher certo |

A suite roda contra um banco vazio, entao nao consegue dizer nada sobre
desempenho com 57 mil linhas. Este modulo roda contra o banco de verdade, e por
isso nao pode virar teste automatico.
"""

from dataclasses import dataclass

# Limite acima do qual uma consulta quente vira falha, e nao observacao.
#
# ⚠️ O numero e generoso de proposito. As medicoes de 28/07/2026 sobre 57.420
# registros ficaram entre **4 e 53 ms**; 500 ms e cerca de dez vezes a pior
# delas. Um limite apertado transformaria variacao de maquina em alarme falso —
# e o que se quer pegar aqui e **indice que sumiu**, que muda a ordem de
# grandeza, nao ruido de medicao.
LIMITE_MS = 500.0

# Constraints e indices que precisam existir no PostgreSQL.
#
# Declarados por colunas, e nao por nome: o Django gera nomes com hash
# (`aquaculture_variave_b4854a_idx`) que mudam quando a migracao e recriada.
# Conferir pelo nome quebraria a cada renomeacao sem que nada estivesse errado.
INDICES_ESPERADOS = {
    'aquaculture_medicaoambiental': (
        # A unicidade que sustenta a idempotencia da ingestao.
        ('local_recife_id', 'data', 'variavel', 'fonte'),
        # Serve `/api/medicoes/?variavel=...`
        ('variavel', 'data'),
        # Serve a janela do painel e o recorte por recife.
        ('local_recife_id', 'data'),
    ),
    'aquaculture_localrecife': (
        ('slug',),
    ),
    'aquaculture_execucaoingestao': (
        ('fonte', 'iniciado_em'),
    ),
}

# Rotulo -> propriedades que precisam ter constraint de unicidade no grafo.
CONSTRAINTS_NEO4J = {
    'Localizacao': ('id', 'slug'),
    'Especie': ('id',),
    'FonteDados': ('id',),
    'MedicaoAmbiental': ('id',),
}

# As consultas que a aplicacao roda de verdade, com o nome do endpoint que as
# dispara. Nao sao exemplos: cada uma foi copiada do plano gerado pelo ORM.
CONSULTAS_QUENTES = {
    'GET /api/medicoes/ (1a pagina, sem filtro)': """
        SELECT m.id FROM aquaculture_medicaoambiental m
        JOIN aquaculture_localrecife l ON m.local_recife_id = l.id
        ORDER BY m.data DESC, l.slug, m.variavel, m.fonte
        LIMIT 100
    """,
    'GET /api/medicoes/?local=&variavel=': """
        SELECT m.id FROM aquaculture_medicaoambiental m
        JOIN aquaculture_localrecife l ON m.local_recife_id = l.id
        WHERE l.slug = %(slug)s AND m.variavel IN ('sst', 'dhw')
        ORDER BY m.data DESC
        LIMIT 100
    """,
    'GET /api/datasets/ (cobertura derivada)': """
        SELECT m.fonte, m.variavel, l.slug, COUNT(*), MIN(m.data), MAX(m.data)
        FROM aquaculture_medicaoambiental m
        JOIN aquaculture_localrecife l ON m.local_recife_id = l.id
        GROUP BY 1, 2, 3
    """,
    'GET /api/painel-risco/ (janela de 7 dias)': """
        SELECT m.data, m.variavel, m.valor, m.fonte
        FROM aquaculture_medicaoambiental m
        JOIN aquaculture_localrecife l ON m.local_recife_id = l.id
        WHERE l.slug = %(slug)s
          AND m.variavel IN ('sst', 'dhw', 'salinidade', 'oxigenio')
    """,
}


@dataclass(frozen=True)
class Achado:
    """Uma conferencia e seu resultado."""

    area: str
    item: str
    ok: bool
    detalhe: str = ''

    def __str__(self):
        # Sem travessao nem emoji: o console do Windows usa cp1252 e os
        # substitui por "?", o que suja justamente a saida que alguem le
        # quando algo falhou.
        marca = 'ok  ' if self.ok else 'FALHA'
        sufixo = f' - {self.detalhe}' if self.detalhe else ''
        return f'  [{marca}] {self.item}{sufixo}'


def _indices_da_tabela(cursor, tabela):
    cursor.execute(
        'SELECT indexdef FROM pg_indexes WHERE tablename = %s', [tabela]
    )
    return [linha[0] for linha in cursor.fetchall()]


def conferir_indices():
    """Todo indice declarado existe no banco?"""
    from django.db import connection

    if connection.vendor != 'postgresql':
        return [Achado('indices', 'PostgreSQL', False, 'banco nao e PostgreSQL')]

    achados = []
    with connection.cursor() as cursor:
        for tabela, grupos in INDICES_ESPERADOS.items():
            definicoes = _indices_da_tabela(cursor, tabela)
            for colunas in grupos:
                achou = any(
                    all(c in definicao for c in colunas)
                    for definicao in definicoes
                )
                achados.append(Achado(
                    'indices',
                    f'{tabela} ({", ".join(colunas)})',
                    achou,
                    '' if achou else 'nenhum indice cobre estas colunas',
                ))
    return achados


def medir_consultas(slug=None):
    """Roda cada consulta quente e mede o tempo real de execucao.

    Usa `EXPLAIN (ANALYZE)` em vez de cronometrar no Python: o que interessa e
    o tempo do banco, sem a latencia de transporte e a montagem de objetos do
    ORM, que variam por motivo alheio ao indice.
    """
    from django.db import connection

    from aquaculture.models import LocalRecife

    if connection.vendor != 'postgresql':
        return [Achado('consultas', 'PostgreSQL', False, 'banco nao e PostgreSQL')]

    if slug is None:
        primeiro = LocalRecife.objects.order_by('slug').first()
        slug = primeiro.slug if primeiro else ''

    achados = []
    with connection.cursor() as cursor:
        for nome, sql in CONSULTAS_QUENTES.items():
            cursor.execute('EXPLAIN (ANALYZE, FORMAT JSON) ' + sql, {'slug': slug})
            plano = cursor.fetchone()[0]
            if isinstance(plano, list):
                plano = plano[0]
            ms = float(plano['Execution Time'])

            achados.append(Achado(
                'consultas', nome, ms <= LIMITE_MS,
                f'{ms:.1f} ms' + ('' if ms <= LIMITE_MS else f' (limite {LIMITE_MS:.0f})'),
            ))
    return achados


def conferir_neo4j():
    """As constraints de unicidade do grafo existem?

    ⚠️ Sem elas o `MERGE` da projecao continua rodando — e passa a criar
    duplicatas em vez de casar com o no existente. A projecao ficaria "bem
    sucedida" com o grafo crescendo a cada execucao.
    """
    from db.connection import Neo4jConnection

    try:
        linhas = list(Neo4jConnection.run('SHOW CONSTRAINTS'))
    except Exception as erro:  # noqa: BLE001 - qualquer falha aqui e informativa
        return [Achado('neo4j', 'conexao', False, f'{type(erro).__name__}: {erro}')]

    existentes = set()
    for linha in linhas:
        rotulos = linha.get('labelsOrTypes') or []
        propriedades = linha.get('properties') or []
        for rotulo in rotulos:
            for propriedade in propriedades:
                existentes.add((rotulo, propriedade))

    achados = []
    for rotulo, propriedades in CONSTRAINTS_NEO4J.items():
        for propriedade in propriedades:
            achou = (rotulo, propriedade) in existentes
            achados.append(Achado(
                'neo4j', f'{rotulo}.{propriedade}', achou,
                '' if achou else 'constraint de unicidade ausente',
            ))
    return achados


def conferir_tudo(incluir_neo4j=True):
    achados = conferir_indices() + medir_consultas()
    if incluir_neo4j:
        achados += conferir_neo4j()
    return achados
