from __future__ import annotations

from typing import Any

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

DJANGO_STATUS_PREDICAO_SOURCE_SLUG = 'django-statuspredicao'
DJANGO_STATUS_PREDICAO_SOURCE_VERSION = 'v1'
DJANGO_STATUS_PREDICAO_MODEL_SLUG = 'status-predicao-django'


def _normalize_slug(value: str) -> str:
    return slugify((value or '').strip())


def serialize_temporal_value(value: Any) -> str | None:
    if value is None:
        return None

    isoformat = getattr(value, 'isoformat', None)
    if callable(isoformat):
        return isoformat()

    return str(value)


def build_localizacao_id(slug: str) -> str:
    return _normalize_slug(slug)


def build_especie_id(nome_cientifico: str) -> str:
    return _normalize_slug(nome_cientifico)


def build_medicao_ambiental_id(local_slug: str, data_iso: str) -> str:
    return f'{build_localizacao_id(local_slug)}:{data_iso}'


def build_predicao_id(
    local_slug: str,
    data_iso: str,
    modelo_slug: str = DJANGO_STATUS_PREDICAO_MODEL_SLUG,
) -> str:
    return f'{build_localizacao_id(local_slug)}:{data_iso}:{_normalize_slug(modelo_slug)}'


def build_fonte_dados_id(
    fonte_slug: str = DJANGO_STATUS_PREDICAO_SOURCE_SLUG,
    versao: str = DJANGO_STATUS_PREDICAO_SOURCE_VERSION,
) -> str:
    return f'{_normalize_slug(fonte_slug)}:{_normalize_slug(versao)}'


DJANGO_STATUS_PREDICAO_SOURCE = {
    'id': build_fonte_dados_id(),
    'slug': DJANGO_STATUS_PREDICAO_SOURCE_SLUG,
    'nome': 'StatusPredicao Django',
    'tipo': 'SINCRONIZACAO_DJANGO',
    'descricao': (
        'Fonte transicional baseada nos registros atuais de StatusPredicao do Django. '
        'As pipelines NOAA e Copernicus serao conectadas em fase posterior.'
    ),
    'versao': DJANGO_STATUS_PREDICAO_SOURCE_VERSION,
    'pipeline': 'neo4j_seed',
    'status': 'ativo',
}


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


UPSERT_FONTE_DADOS_QUERY = f"""
MERGE (f:{FONTE_DADOS_LABEL} {{id: $id}})
SET f += $props
"""

UPSERT_LOCALIZACOES_QUERY = f"""
UNWIND $rows AS row
MERGE (l:{LOCALIZACAO_LABEL} {{slug: row.props.slug}})
SET l += row.props
"""

UPSERT_ESPECIES_QUERY = f"""
UNWIND $rows AS row
MATCH (l:{LOCALIZACAO_LABEL} {{id: row.localizacao_id}})
MERGE (e:{ESPECIE_LABEL} {{nome_cientifico: row.props.nome_cientifico}})
SET e += row.props
MERGE (l)-[:{REL_ABRIGA_ESPECIE}]->(e)
"""

UPSERT_MEDICOES_E_PREDICOES_QUERY = f"""
UNWIND $rows AS row
MATCH (l:{LOCALIZACAO_LABEL} {{id: row.localizacao_id}})
MATCH (f:{FONTE_DADOS_LABEL} {{id: row.fonte_dados_id}})
MERGE (m:{MEDICAO_AMBIENTAL_LABEL} {{id: row.medicao.id}})
SET m += row.medicao.props
MERGE (p:{PREDICAO_LABEL} {{local_slug: row.predicao.props.local_slug, data: row.predicao.props.data}})
SET p += row.predicao.props
REMOVE
    p.sst_atual,
    p.limite_termico,
    p.anomalia,
    p.dhw_calculado,
    p.irradiancia,
    p.turbidez,
    p.salinidade,
    p.ph,
    p.oxigenio,
    p.nitrato,
    p.clorofila,
    p.vento_velocidade
MERGE (l)-[:{REL_TEM_MEDICAO}]->(m)
MERGE (l)-[:{REL_TEM_PREDICAO}]->(p)
MERGE (p)-[:{REL_DERIVADA_DE}]->(m)
MERGE (m)-[:{REL_PROVENIENTE_DE}]->(f)
MERGE (p)-[:{REL_PROVENIENTE_DE}]->(f)
"""


def build_fonte_dados_seed_payload() -> dict[str, Any]:
    return {
        'id': DJANGO_STATUS_PREDICAO_SOURCE['id'],
        'props': dict(DJANGO_STATUS_PREDICAO_SOURCE),
    }


def build_localizacao_row(local: Any) -> dict[str, Any]:
    localizacao_id = build_localizacao_id(local.slug)
    return {
        'id': localizacao_id,
        'props': {
            'id': localizacao_id,
            'slug': local.slug,
            'nome': local.nome,
            'estado': local.estado,
            'cidade': local.cidade,
            'descricao': local.descricao,
            'ultima_atualizacao': serialize_temporal_value(local.ultima_atualizacao),
            'ativo': local.ativo,
            'origem_registro': 'LocalRecife',
            'django_pk': local.pk,
        },
    }


def build_especie_row(local: Any, especie: Any) -> dict[str, Any]:
    especie_id = build_especie_id(especie.nome_cientifico)
    return {
        'id': especie_id,
        'localizacao_id': build_localizacao_id(local.slug),
        'props': {
            'id': especie_id,
            'nome_cientifico': especie.nome_cientifico,
            'nome_comum': especie.nome_comum,
            'tipo': especie.tipo,
            'descricao': especie.descricao,
            'status_conservacao': especie.status_conservacao,
            'credito_imagem': especie.credito_imagem,
            'fonte_imagem_url': especie.fonte_imagem_url,
            'fonte_url': especie.fonte_url,
            'origem_registro': 'Especie',
            'django_pk': especie.pk,
        },
    }


def build_status_predicao_row(predicao: Any) -> dict[str, Any]:
    local_slug = predicao.local_recife.slug
    localizacao_id = build_localizacao_id(local_slug)
    data_iso = serialize_temporal_value(predicao.data)
    medicao_id = build_medicao_ambiental_id(local_slug, data_iso)
    predicao_id = build_predicao_id(local_slug, data_iso)
    fonte_dados_id = DJANGO_STATUS_PREDICAO_SOURCE['id']

    return {
        'localizacao_id': localizacao_id,
        'fonte_dados_id': fonte_dados_id,
        'medicao': {
            'id': medicao_id,
            'props': {
                'id': medicao_id,
                'localizacao_id': localizacao_id,
                'local_slug': local_slug,
                'data': data_iso,
                'fonte_dados_id': fonte_dados_id,
                'origem_registro': 'StatusPredicao',
                'sst': predicao.sst_atual,
                'limite_termico': predicao.limite_termico,
                'anomalia_termica': predicao.anomalia,
                'dhw': predicao.dhw_calculado,
                'vento_velocidade': predicao.vento_velocidade,
                'par': predicao.irradiancia,
                'kd490': predicao.turbidez,
                'salinidade': predicao.salinidade,
                'ph': predicao.ph,
                'oxigenio': predicao.oxigenio,
                'nitrato': predicao.nitrato,
                'clorofila': predicao.clorofila,
                'django_pk': predicao.pk,
            },
        },
        'predicao': {
            'id': predicao_id,
            'props': {
                'id': predicao_id,
                'localizacao_id': localizacao_id,
                'local_slug': local_slug,
                'data': data_iso,
                'modelo_slug': DJANGO_STATUS_PREDICAO_MODEL_SLUG,
                'medicao_id': medicao_id,
                'fonte_dados_id': fonte_dados_id,
                'origem_registro': 'StatusPredicao',
                'risco_integrado': predicao.risco_integrado,
                'nivel_alerta': predicao.nivel_alerta,
                'django_pk': predicao.pk,
            },
        },
    }
