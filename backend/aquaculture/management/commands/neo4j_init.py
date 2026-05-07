from django.core.management.base import BaseCommand, CommandError

from aquaculture.neo4j_service import (
    Neo4jServiceError,
    executar_queries_schema,
    verificar_conexao_neo4j,
)


SCHEMA_QUERIES = [
    """
    CREATE CONSTRAINT localizacao_slug IF NOT EXISTS
    FOR (l:Localizacao)
    REQUIRE l.slug IS UNIQUE
    """,
    """
    CREATE CONSTRAINT especie_nome_cientifico IF NOT EXISTS
    FOR (e:Especie)
    REQUIRE e.nome_cientifico IS UNIQUE
    """,
    """
    CREATE CONSTRAINT predicao_local_data IF NOT EXISTS
    FOR (p:Predicao)
    REQUIRE (p.local_slug, p.data) IS UNIQUE
    """,
    """
    CREATE CONSTRAINT dataset_id IF NOT EXISTS
    FOR (d:Dataset)
    REQUIRE d.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT fonte_nome IF NOT EXISTS
    FOR (f:FonteDados)
    REQUIRE f.nome IS UNIQUE
    """,
    """
    CREATE CONSTRAINT modelo_versao IF NOT EXISTS
    FOR (m:ModeloVersao)
    REQUIRE m.versao IS UNIQUE
    """,
]


class Command(BaseCommand):
    help = 'Cria as constraints iniciais do schema Neo4j.'

    def handle(self, *args, **options):
        try:
            verificar_conexao_neo4j()
            total = executar_queries_schema(SCHEMA_QUERIES)
        except Neo4jServiceError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f'Schema Neo4j inicializado com sucesso. {total} constraints processadas.'))
