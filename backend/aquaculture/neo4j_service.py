from typing import Any, Iterable

from django.conf import settings

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
