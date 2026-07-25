from typing import Any, Iterable

from django.conf import settings

from .neo4j_schema import (
    ESPECIE_LABEL,
    LOCALIZACAO_LABEL,
    MEDICAO_AMBIENTAL_LABEL,
    PREDICAO_LABEL,
    REL_ABRIGA_ESPECIE,
    REL_DERIVADA_DE,
    REL_TEM_PREDICAO,
    build_localizacao_id,
)

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import AuthError, ConfigurationError, Neo4jError, ServiceUnavailable
except ImportError:  # pragma: no cover - depende do ambiente local
    GraphDatabase = None

    class Neo4jError(Exception):
        pass

    class AuthError(Neo4jError):
        pass

    class ConfigurationError(Neo4jError):
        pass

    class ServiceUnavailable(Neo4jError):
        pass


class Neo4jServiceError(Exception):
    """Erro de servico para operacoes com Neo4j."""


_driver = None


LISTAR_LOCALIZACOES_GRAFO_QUERY = """
MATCH (l:{localizacao_label})
OPTIONAL MATCH (l)-[:{rel_abriga_especie}]->(e:{especie_label})
WITH l, count(DISTINCT e) AS quantidade_especies
OPTIONAL MATCH (l)-[:{rel_tem_predicao}]->(p:{predicao_label})
WITH l, quantidade_especies, p
ORDER BY l.slug, p.data DESC
WITH l, quantidade_especies, collect(p) AS predicoes
RETURN
    l.slug AS slug,
    l.nome AS nome,
    l.estado AS estado,
    l.cidade AS cidade,
    l.descricao AS descricao,
    l.ultima_atualizacao AS ultima_atualizacao,
    quantidade_especies,
    size(predicoes) AS quantidade_predicoes,
    predicoes[0].risco_integrado AS risco_atual,
    predicoes[0].nivel_alerta AS nivel_alerta_atual,
    predicoes[0].data AS ultima_predicao_data
ORDER BY nome, slug
""".format(
    localizacao_label=LOCALIZACAO_LABEL,
    especie_label=ESPECIE_LABEL,
    predicao_label=PREDICAO_LABEL,
    rel_abriga_especie=REL_ABRIGA_ESPECIE,
    rel_tem_predicao=REL_TEM_PREDICAO,
)

OBTER_LOCALIZACAO_GRAFO_QUERY = """
MATCH (l:{localizacao_label} {{id: $localizacao_id}})
RETURN
    l.slug AS slug,
    l.nome AS nome,
    l.estado AS estado,
    l.cidade AS cidade,
    l.descricao AS descricao,
    l.ultima_atualizacao AS ultima_atualizacao,
    l.ativo AS ativo
LIMIT 1
""".format(localizacao_label=LOCALIZACAO_LABEL)

LISTAR_ESPECIES_LOCALIZACAO_GRAFO_QUERY = """
MATCH (:{localizacao_label} {{id: $localizacao_id}})-[:{rel_abriga_especie}]->(e:{especie_label})
RETURN
    e.nome_cientifico AS nome_cientifico,
    e.nome_comum AS nome_comum,
    e.tipo AS tipo,
    e.descricao AS descricao,
    e.status_conservacao AS status_conservacao,
    e.credito_imagem AS credito_imagem,
    e.fonte_imagem_url AS fonte_imagem_url,
    e.fonte_url AS fonte_url
ORDER BY coalesce(e.nome_comum, ''), e.nome_cientifico
""".format(
    localizacao_label=LOCALIZACAO_LABEL,
    especie_label=ESPECIE_LABEL,
    rel_abriga_especie=REL_ABRIGA_ESPECIE,
)

LISTAR_PREDICOES_LOCALIZACAO_GRAFO_QUERY = """
MATCH (:{localizacao_label} {{id: $localizacao_id}})-[:{rel_tem_predicao}]->(p:{predicao_label})
OPTIONAL MATCH (p)-[:{rel_derivada_de}]->(m:{medicao_ambiental_label})
RETURN
    p.local_slug AS local_slug,
    p.data AS data,
    m.sst AS sst_atual,
    m.limite_termico AS limite_termico,
    m.anomalia_termica AS anomalia,
    m.dhw AS dhw_calculado,
    m.par AS irradiancia,
    m.kd490 AS turbidez,
    m.salinidade AS salinidade,
    m.ph AS ph,
    m.oxigenio AS oxigenio,
    m.nitrato AS nitrato,
    m.clorofila AS clorofila,
    p.risco_integrado AS risco_integrado,
    p.nivel_alerta AS nivel_alerta
ORDER BY p.data DESC
""".format(
    localizacao_label=LOCALIZACAO_LABEL,
    predicao_label=PREDICAO_LABEL,
    medicao_ambiental_label=MEDICAO_AMBIENTAL_LABEL,
    rel_tem_predicao=REL_TEM_PREDICAO,
    rel_derivada_de=REL_DERIVADA_DE,
)


def _get_neo4j_settings() -> tuple[str, str, str]:
    uri = (getattr(settings, 'NEO4J_URI', '') or '').strip()
    user = (getattr(settings, 'NEO4J_USER', '') or '').strip()
    password = getattr(settings, 'NEO4J_PASSWORD', '') or ''

    if not uri:
        raise Neo4jServiceError('NEO4J_URI nao configurado.')
    if not user:
        raise Neo4jServiceError('NEO4J_USER nao configurado.')
    if not password.strip():
        raise Neo4jServiceError(
            'NEO4J_PASSWORD vazio. Configure as credenciais do Neo4j antes de executar este comando.'
        )

    return uri, user, password


def get_neo4j_driver():
    global _driver

    if GraphDatabase is None:
        raise Neo4jServiceError(
            "Pacote 'neo4j' nao instalado no ambiente atual. Instale as dependencias antes de executar os comandos Neo4j."
        )

    if _driver is None:
        uri, user, password = _get_neo4j_settings()
        try:
            _driver = GraphDatabase.driver(uri, auth=(user, password))
        except ConfigurationError as exc:
            raise Neo4jServiceError(f"Configuracao Neo4j invalida para '{uri}': {exc}") from exc
        except Exception as exc:
            raise Neo4jServiceError(
                f"Nao foi possivel inicializar o driver Neo4j em '{uri}': {exc}"
            ) from exc

    return _driver


def _raise_neo4j_operation_error(action: str, exc: Exception) -> None:
    uri = getattr(settings, 'NEO4J_URI', '')

    if isinstance(exc, AuthError):
        raise Neo4jServiceError(
            'Falha de autenticacao no Neo4j. Verifique NEO4J_USER e NEO4J_PASSWORD.'
        ) from exc
    if isinstance(exc, ServiceUnavailable):
        raise Neo4jServiceError(
            f"Nao foi possivel conectar ao Neo4j em '{uri}' durante {action}. "
            'Verifique se o servidor esta ativo e acessivel.'
        ) from exc
    if isinstance(exc, Neo4jError):
        raise Neo4jServiceError(f'Erro no Neo4j durante {action}: {exc}') from exc

    raise Neo4jServiceError(f'Falha inesperada durante {action}: {exc}') from exc


def _normalize_neo4j_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_neo4j_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_neo4j_value(item) for item in value]

    isoformat = getattr(value, 'isoformat', None)
    if callable(isoformat):
        try:
            return isoformat()
        except TypeError:
            return value

    return value


def verificar_conexao_neo4j() -> bool:
    driver = get_neo4j_driver()

    try:
        driver.verify_connectivity()
    except Exception as exc:
        _raise_neo4j_operation_error('a verificacao de conectividade', exc)

    return True


def executar_queries_schema(queries: Iterable[str]) -> int:
    driver = get_neo4j_driver()
    total_queries = 0

    try:
        with driver.session() as session:
            for query in queries:
                session.run(query).consume()
                total_queries += 1
    except Exception as exc:
        _raise_neo4j_operation_error('a criacao do schema', exc)

    return total_queries


def executar_write(query: str, parameters: dict[str, Any] | None = None):
    driver = get_neo4j_driver()
    query_parameters = parameters or {}

    def _write_transaction(tx):
        result = tx.run(query, query_parameters)
        return result.consume()

    try:
        with driver.session() as session:
            return session.execute_write(_write_transaction)
    except Exception as exc:
        _raise_neo4j_operation_error('a escrita no Neo4j', exc)


def executar_read(
    query: str,
    parameters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    driver = get_neo4j_driver()
    query_parameters = parameters or {}

    def _read_transaction(tx):
        result = tx.run(query, query_parameters)
        return [_normalize_neo4j_value(record) for record in result.data()]

    try:
        with driver.session() as session:
            return session.execute_read(_read_transaction)
    except Exception as exc:
        _raise_neo4j_operation_error('a leitura no Neo4j', exc)


def listar_localizacoes_grafo() -> list[dict[str, Any]]:
    return executar_read(LISTAR_LOCALIZACOES_GRAFO_QUERY)


def obter_localizacao_grafo(slug: str) -> dict[str, Any] | None:
    parameters = {'localizacao_id': build_localizacao_id(slug)}
    localizacoes = executar_read(OBTER_LOCALIZACAO_GRAFO_QUERY, parameters)
    if not localizacoes:
        return None

    localizacao = localizacoes[0]
    localizacao['especies'] = executar_read(
        LISTAR_ESPECIES_LOCALIZACAO_GRAFO_QUERY,
        parameters,
    )
    localizacao['predicoes'] = executar_read(
        LISTAR_PREDICOES_LOCALIZACAO_GRAFO_QUERY,
        parameters,
    )
    return localizacao
