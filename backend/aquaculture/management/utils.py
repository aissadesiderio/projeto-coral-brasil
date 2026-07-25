"""Verificacoes compartilhadas pelos comandos de gerenciamento."""

from django.core.management.base import CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor


def migrations_pendentes(alias=DEFAULT_DB_ALIAS):
    """Lista as migrations ainda nao aplicadas no banco.

    Retorna nomes no formato "app.0001_nome", em ordem de aplicacao.
    """
    executor = MigrationExecutor(connections[alias])
    alvos = executor.loader.graph.leaf_nodes()
    return [
        f'{migration.app_label}.{migration.name}'
        for migration, _ in executor.migration_plan(alvos)
    ]


def exigir_migrations_aplicadas(comando=None):
    """Interrompe com mensagem acionavel se o banco estiver desatualizado.

    Sem isto, um banco em schema antigo produz um `OperationalError` cru do
    SQLite ("no such column: aquaculture_localrecife.latitude") com dezenas de
    linhas de traceback - tecnicamente correto e praticamente inutil para
    quem so precisa saber que falta rodar `migrate`.

    Acontece com facilidade em qualquer maquina que puxou codigo novo sem
    migrar, ja que o banco e local e nao vem no repositorio.
    """
    pendentes = migrations_pendentes()
    if not pendentes:
        return

    amostra = pendentes[:5]
    resto = len(pendentes) - len(amostra)
    lista = '\n'.join(f'    - {nome}' for nome in amostra)
    if resto > 0:
        lista += f'\n    ... e mais {resto}'

    raise CommandError(
        f'O banco esta desatualizado: {len(pendentes)} migration(s) pendente(s).\n\n'
        f'{lista}\n\n'
        'Rode antes de continuar:\n'
        '    python backend/manage.py migrate\n\n'
        'O banco e local e nao vem no repositorio, entao toda maquina que '
        'puxa codigo novo precisa migrar.'
    )
