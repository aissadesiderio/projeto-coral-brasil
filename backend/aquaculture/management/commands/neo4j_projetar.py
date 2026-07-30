"""Reconstroi o grafo do Neo4j a partir do PostgreSQL.

Substitui o `neo4j_seed`, que derivava os nos de `StatusPredicao` — o modelo
legado, com 3 registros. As 57.420 medicoes reais nunca estiveram no grafo.

(!) **Sentido unico.** O Neo4j e projecao derivada: nunca recebe escrita que nao
venha do PostgreSQL. Se divergir ou for perdido, rode este comando de novo.
Ver docs/arquitetura.md.
"""

import time

from django.core.management.base import BaseCommand, CommandError

from db import projecao


class Command(BaseCommand):
    help = 'Projeta o PostgreSQL no Neo4j (grafo derivado, reconstruivel).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--manter', action='store_true',
            help='Nao apaga a projecao anterior antes de reconstruir. '
                 'Padrao e apagar: o grafo e derivado, nao acumulado.',
        )
        parser.add_argument('--lote', type=int, default=projecao.LOTE)
        parser.add_argument(
            '--conferir', action='store_true',
            help='So compara o grafo com o Postgres e sai, sem escrever.',
        )

    def handle(self, *args, **opcoes):
        if opcoes['conferir']:
            return self._conferir()

        self.stdout.write(self.style.MIGRATE_HEADING('=== PROJETANDO ==='))
        self.stdout.write(
            '  PostgreSQL -> Neo4j, sentido unico.\n'
            '  O grafo e derivado: apagar e reconstruir e a operacao normal.\n'
        )

        def progresso(escritos, total):
            if escritos % (opcoes['lote'] * 10) == 0 or escritos == total:
                self.stdout.write(
                    f'    medicoes: {escritos:,}/{total:,} '
                    f'({escritos / total:.0%})'
                )

        inicio = time.time()
        try:
            resultado = projecao.projetar(
                limpar_antes=not opcoes['manter'],
                lote=opcoes['lote'],
                ao_progredir=progresso,
            )
        except Exception as erro:
            # 🚨 `CommandError`, e nao `stderr.write` + `return`. Ate 30/07/2026
            # este bloco imprimia o erro e saia com **codigo 0**: o
            # `preparar_deploy` registrava o passo do grafo como executado, e um
            # deploy seguia adiante com o Neo4j vazio. Falha que sai como
            # sucesso e o unico formato pior do que falhar.
            raise CommandError(
                f'{type(erro).__name__}: {erro}\n\n'
                'O Neo4j esta de pe? Confira nesta ordem:\n'
                '  1. docker compose ps      -> precisa dizer "Up (healthy)" e '
                'publicar a porta 7687\n'
                '  2. docker compose logs neo4j\n'
                '  3. docker compose up -d\n\n'
                '(!) Um container em "Restarting" nao publica porta nenhuma, e '
                'o "up -d" nao conserta: ele reinicia o mesmo laco. A causa '
                'aparece so no log — senha com menos de 8 caracteres e usuario '
                'diferente de "neo4j" sao as duas que ja aconteceram aqui.'
            ) from erro

        decorrido = time.time() - inicio

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== PROJETADO ==='))
        if resultado.apagados:
            self.stdout.write(
                f'  {resultado.apagados:,} nos da projecao anterior apagados'
            )
        self.stdout.write(f'  Localizacao      : {resultado.localizacoes:,}')
        self.stdout.write(f'  Especie          : {resultado.especies:,}')
        self.stdout.write(f'  FonteDados       : {resultado.fontes:,}')
        self.stdout.write(f'  MedicaoAmbiental : {resultado.medicoes:,}')
        self.stdout.write(f'  ABRIGA_ESPECIE   : {resultado.rel_abriga:,}')
        self.stdout.write(f'  TEM_MEDICAO      : {resultado.rel_tem_medicao:,}')
        self.stdout.write(f'  PROVENIENTE_DE   : {resultado.rel_proveniente:,}')
        self.stdout.write(f'\n  {resultado.resumo()} em {decorrido:.0f}s')

        for aviso in resultado.avisos:
            self.stdout.write(self.style.WARNING(f'  (!) {aviso}'))

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== CONFERINDO ==='))
        self._conferir()

    def _conferir(self):
        try:
            conferencias, orfas = projecao.conferir()
        except Exception as erro:
            self.stderr.write(self.style.ERROR(
                f'{type(erro).__name__}: {erro}'
            ))
            return

        self.stdout.write(
            f'  {"o que":18s} {"Postgres":>10s} {"Neo4j":>10s}'
        )
        divergiu = False
        for nome, esperado, obtido in conferencias:
            marca = 'ok' if esperado == obtido else '<<< DIVERGIU'
            divergiu = divergiu or esperado != obtido
            self.stdout.write(
                f'  {nome:18s} {esperado:10,} {obtido:10,}   {marca}'
            )

        if orfas:
            self.stdout.write(self.style.ERROR(
                f'\n  (!) {orfas:,} medicoes sem PROVENIENTE_DE. '
                'Proveniencia por valor e a razao de o grafo existir.'
            ))
            divergiu = True

        if divergiu:
            self.stdout.write(self.style.ERROR(
                '\n  A projecao NAO confere com o PostgreSQL. '
                'Rode de novo; se persistir, o defeito e no comando.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '\n  [ok] O grafo confere com o PostgreSQL, item a item.'
            ))
