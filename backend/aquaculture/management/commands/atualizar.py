"""A rotina diaria: busca o dado novo e reconstroi o grafo.

Feita para rodar sem ninguem olhando — cron, Agendador de Tarefas, o que for.
Por isso e curta, idempotente, e **nao retreina o modelo**: ver
`db/atualizacao.py` para o motivo.
"""

import sys
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Ingere o dado novo, reprojeta o grafo e relata o que envelheceu.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sem-grafo', action='store_true',
            help='So ingere. Util quando o Neo4j nao esta no mesmo servidor.',
        )
        parser.add_argument(
            '--silencioso', action='store_true',
            help=(
                'So imprime se houver algo a dizer. Feito para agendamento: '
                'saida vazia = dia normal.'
            ),
        )

    def handle(self, *args, **opcoes):
        from django.core.management import call_command

        from db import atualizacao

        inicio = time.monotonic()
        falou = False

        antes = atualizacao.medir()

        try:
            call_command('ingerir', verbosity=0 if opcoes['silencioso'] else 1)
            if not opcoes['sem_grafo']:
                call_command(
                    'neo4j_projetar',
                    verbosity=0 if opcoes['silencioso'] else 1,
                )
        except Exception as erro:  # noqa: BLE001 - a rotina roda sozinha
            # 🚨 Falha numa rotina agendada e pior que falha manual: nao ha
            # ninguem lendo a tela. Ela precisa gritar no codigo de saida, que
            # e o unico canal que o agendador entende.
            self.stderr.write(self.style.ERROR(
                f'Atualizacao falhou: {type(erro).__name__}: {erro}'
            ))
            sys.exit(1)

        depois = atualizacao.medir()
        novas = depois.medicoes - antes.medicoes
        duracao = time.monotonic() - inicio

        if not opcoes['silencioso']:
            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING('Atualizacao'))
            self.stdout.write(
                f'  {novas:+,} medicoes ({depois.medicoes:,} no total)'
            )
            self.stdout.write(f'  serie ate {depois.fim_da_serie}')
            self.stdout.write(
                f'  modelo {depois.modelo}, treinado em '
                f'{depois.modelo_treinado_em or "nunca"}'
            )
            self.stdout.write(f'  {duracao:.1f}s')
            falou = True

        avisos = atualizacao.recados(depois)
        if avisos:
            self.stdout.write('')
            for aviso in avisos:
                self.stdout.write(self.style.WARNING(f'  (!) {aviso}'))
            falou = True

        if falou:
            self.stdout.write('')
