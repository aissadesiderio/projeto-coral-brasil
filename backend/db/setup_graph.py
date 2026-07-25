"""
Execute com:
    python manage.py shell < backend/db/setup_graph.py

Bootstrap legado do grafo.

O schema oficial do Neo4j agora vive em `aquaculture.neo4j_schema`
e deve ser criado por `python backend/manage.py neo4j_init`.
Este arquivo nao define mais schema proprio: apenas delega
para os comandos oficiais de init e seed.
"""

from django.core.management import call_command


def setup():
    print('Delegando para os comandos oficiais do schema Neo4j...')
    call_command('neo4j_init')
    call_command('neo4j_seed')
    print('\nSetup concluido via neo4j_init + neo4j_seed.')


if __name__ == "__main__":
    setup()
