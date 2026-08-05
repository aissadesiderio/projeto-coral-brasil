"""Confere a camada de persistencia contra o banco real.

Sai com codigo 1 quando alguma conferencia falha, para poder virar portao de
deploy em vez de relatorio que ninguem le.
"""

import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Confere indices, constraints e o tempo das consultas quentes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sem-neo4j', action='store_true',
            help='Pula a conferencia do grafo (util quando ele nao subiu).',
        )

    def handle(self, *args, **opcoes):
        from db import conferencia

        achados = conferencia.conferir_tudo(
            incluir_neo4j=not opcoes['sem_neo4j']
        )

        titulos = {
            'indices': 'Indices e constraints (PostgreSQL)',
            'consultas': f'Consultas quentes (limite {conferencia.LIMITE_MS:.0f} ms)',
            'neo4j': 'Constraints de unicidade (Neo4j)',
        }

        self.stdout.write('')
        area_atual = None
        for achado in achados:
            if achado.area != area_atual:
                area_atual = achado.area
                self.stdout.write(
                    self.style.MIGRATE_HEADING(titulos.get(area_atual, area_atual))
                )
            linha = str(achado)
            self.stdout.write(
                linha if achado.ok else self.style.ERROR(linha)
            )

        falhas = [a for a in achados if not a.ok]
        self.stdout.write('')

        if falhas:
            self.stdout.write(self.style.ERROR(
                f'{len(falhas)} conferencia(s) falharam de {len(achados)}.'
            ))
            # O recado importa mais que o codigo de saida: indice ausente e
            # quase sempre migracao nao aplicada, e a pessoa precisa saber
            # disso sem ir ler o modulo.
            self.stdout.write(
                '  Indice ausente costuma ser migracao nao aplicada: '
                'rode "manage.py migrate".\n'
                '  Constraint do Neo4j ausente: rode "manage.py neo4j_projetar", '
                'que as cria de forma idempotente.'
            )
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS(
            f'{len(achados)} conferencias, todas ok.'
        ))
