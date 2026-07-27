"""Gera uma copia .docx de cada documento Markdown do projeto.

O .docx e **artefato derivado**: some com `--limpar`, volta com um comando, e
nao entra no git. O Markdown continua sendo a unica fonte - copia versionada
envelheceria, e em duas semanas ninguem saberia qual das duas vale.
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from documentacao.markdown_docx import converter

# Onde procurar. Relativo a raiz do repositorio (um nivel acima de BASE_DIR,
# que aponta para backend/).
PASTAS = ('docs', 'backend/docs', '.')

# Na raiz, so estes - senao qualquer .md solto entraria.
RAIZ_PERMITIDA = ('README.md', 'PLANEJAMENTO.md')

SAIDA_PADRAO = 'docs/exportado'


class Command(BaseCommand):
    help = 'Exporta a documentacao Markdown para .docx (artefato derivado).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--saida', default=SAIDA_PADRAO,
            help=f'Pasta de destino. Padrao: {SAIDA_PADRAO}',
        )
        parser.add_argument(
            '--limpar', action='store_true',
            help='Apaga a pasta de destino antes de gerar.',
        )
        parser.add_argument(
            '--doc', help='Converte so este arquivo (ex.: docs/FONTES.md).',
        )

    def handle(self, *args, **opcoes):
        raiz = Path(settings.BASE_DIR).parent
        destino = raiz / opcoes['saida']

        if opcoes['limpar'] and destino.exists():
            shutil.rmtree(destino)
            self.stdout.write(f'Pasta {opcoes["saida"]} apagada.')

        if opcoes['doc']:
            arquivos = [raiz / opcoes['doc']]
            if not arquivos[0].exists():
                self.stderr.write(f'Nao encontrado: {opcoes["doc"]}')
                return
        else:
            arquivos = self._encontrar(raiz, destino)

        destino.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f'Destino: {destino}\n')

        total = 0
        for arquivo in arquivos:
            relativo = arquivo.relative_to(raiz)
            # Achata o caminho para nao criar subpastas: backend/docs/x.md
            # vira backend-docs-x.docx, e nada colide.
            nome = str(relativo.with_suffix('')).replace('\\', '-')
            nome = nome.replace('/', '-').lstrip('.-') + '.docx'
            saida = destino / nome

            blocos = converter(arquivo, saida, titulo=arquivo.stem)
            tamanho = saida.stat().st_size / 1024
            self.stdout.write(
                f'  {str(relativo):44s} -> {nome:38s} '
                f'{blocos:4d} blocos, {tamanho:6.1f} KB'
            )
            total += 1

        self.stdout.write(self.style.SUCCESS(f'\n{total} documento(s) exportado(s).'))
        self.stdout.write(
            'Artefato derivado: nao versionado, regeravel com este comando.'
        )

    def _encontrar(self, raiz, destino):
        encontrados = []
        for pasta in PASTAS:
            atual = raiz / pasta
            if not atual.exists():
                continue
            for arquivo in sorted(atual.glob('*.md')):
                if destino in arquivo.parents:
                    continue
                if pasta == '.' and arquivo.name not in RAIZ_PERMITIDA:
                    continue
                encontrados.append(arquivo)
        return encontrados
