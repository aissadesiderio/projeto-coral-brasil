from django.core.management.base import BaseCommand, CommandError

from aquaculture.neo4j_schema import SCHEMA_QUERIES
from aquaculture.neo4j_service import (
    Neo4jServiceError,
    executar_queries_schema,
    verificar_conexao_neo4j,
)


class Command(BaseCommand):
    help = 'Cria o schema canonico do Neo4j adotado pelo backend.'

    def handle(self, *args, **options):
        try:
            verificar_conexao_neo4j()
            total = executar_queries_schema(SCHEMA_QUERIES)
        except Neo4jServiceError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f'Schema Neo4j inicializado com sucesso. {total} constraints processadas.'))
