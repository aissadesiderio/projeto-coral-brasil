"""Nomes e constraints do grafo. **Nao escreve nada.**

Este modulo declara o vocabulario do Neo4j — rotulos, relacoes e as constraints
de unicidade — e mais nada. Quem escreve e `db/projecao.py`, via
`manage.py neo4j_projetar`, derivando do PostgreSQL.

🚨 **Ate 30/07/2026 havia aqui uma segunda camada, morta.** Quatro consultas
`UPSERT_*`, tres construtores de linha e a `DJANGO_STATUS_PREDICAO_SOURCE` — a
fonte "transicional" cujo `pipeline` dizia `neo4j_seed`, comando que nao existe
mais desde que o grafo passou a sair do PostgreSQL. Nenhuma delas era chamada
por codigo de producao; **as unicas chamadas vinham dos proprios testes**, o
que dava a essa camada uma aparencia de coberta e viva.

Isso importava mais do que ocupar espaco: o vocabulario de IDs daquela camada
(`slug:data:modelo`) descrevia um mundo em que uma linha de `StatusPredicao`
era ao mesmo tempo medicao e predicao. Mantido ao lado do schema real, ele
convidava a proxima pessoa a escrever no grafo pelo caminho errado.

O que sobrou e o que tem consumidor:

| O que | Quem usa |
|---|---|
| rotulos e relacoes | `neo4j_service` (leitura), `db/projecao.py` (escrita) |
| `build_localizacao_id` | `neo4j_service` |
| `SCHEMA_QUERIES` | `manage.py neo4j_init` |
"""

from __future__ import annotations

from django.utils.text import slugify

LOCALIZACAO_LABEL = 'Localizacao'
ESPECIE_LABEL = 'Especie'
PREDICAO_LABEL = 'Predicao'
MEDICAO_AMBIENTAL_LABEL = 'MedicaoAmbiental'
FONTE_DADOS_LABEL = 'FonteDados'

REL_ABRIGA_ESPECIE = 'ABRIGA_ESPECIE'
REL_TEM_MEDICAO = 'TEM_MEDICAO'
REL_TEM_PREDICAO = 'TEM_PREDICAO'
REL_DERIVADA_DE = 'DERIVADA_DE'
REL_PROVENIENTE_DE = 'PROVENIENTE_DE'


def _normalize_slug(value: str) -> str:
    return slugify((value or '').strip())


def build_localizacao_id(slug: str) -> str:
    return _normalize_slug(slug)


SCHEMA_QUERIES = [
    f"""
    CREATE CONSTRAINT localizacao_id_unique IF NOT EXISTS
    FOR (l:{LOCALIZACAO_LABEL})
    REQUIRE l.id IS UNIQUE
    """,
    f"""
    CREATE CONSTRAINT localizacao_slug_unique IF NOT EXISTS
    FOR (l:{LOCALIZACAO_LABEL})
    REQUIRE l.slug IS UNIQUE
    """,
    f"""
    CREATE CONSTRAINT especie_id_unique IF NOT EXISTS
    FOR (e:{ESPECIE_LABEL})
    REQUIRE e.id IS UNIQUE
    """,
    f"""
    CREATE CONSTRAINT especie_nome_cientifico_unique IF NOT EXISTS
    FOR (e:{ESPECIE_LABEL})
    REQUIRE e.nome_cientifico IS UNIQUE
    """,
    f"""
    CREATE CONSTRAINT medicao_ambiental_id_unique IF NOT EXISTS
    FOR (m:{MEDICAO_AMBIENTAL_LABEL})
    REQUIRE m.id IS UNIQUE
    """,
    f"""
    CREATE CONSTRAINT predicao_id_unique IF NOT EXISTS
    FOR (p:{PREDICAO_LABEL})
    REQUIRE p.id IS UNIQUE
    """,
    f"""
    CREATE CONSTRAINT fonte_dados_id_unique IF NOT EXISTS
    FOR (f:{FONTE_DADOS_LABEL})
    REQUIRE f.id IS UNIQUE
    """,
]
