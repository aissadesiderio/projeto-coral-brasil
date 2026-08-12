"""Reconstroi o catalogo de datasets a partir do que existe de fato.

Uso:
    python backend/manage.py inventariar_datasets
    python backend/manage.py inventariar_datasets --dry-run

Substitui o seed ficticio da migration 0014. Ver docs/FONTES.md secao 6.14.

**"De fato" quer dizer duas coisas**, porque o catalogo tem duas metades (ver o
cabecalho de `aquaculture/inventario_datasets.py`):

| Metade | "existe" significa | Nao existe vira |
|---|---|---|
| arquivos | o CSV esta em `backend/dados/` | registro **desativado** |
| series | ha medicao daquele par (fonte, local) no banco | **nenhum registro** |

⚠️ A assimetria e deliberada. Um arquivo que sumiu ja foi anunciado e precisa
continuar visivel dizendo que sumiu; uma serie que nunca foi ingerida nunca foi
anunciada, e cria-la desativada so encheria a pagina de promessas.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from aquaculture.inventario_datasets import (
    DATASETS_REAIS,
    EXCLUIDOS,
    construir_inventario,
    construir_inventario_das_series,
)
from aquaculture.management.utils import exigir_migrations_aplicadas
from aquaculture.models import DatasetCatalogo, LocalRecife


class Command(BaseCommand):
    help = 'Reconstroi o catalogo de datasets a partir dos arquivos reais em backend/dados/.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria gravado sem tocar no banco.',
        )
        parser.add_argument(
            '--remover-orfaos',
            action='store_true',
            default=True,
            help='Remove registros do catalogo que nao estao no inventario (padrao).',
        )
        parser.add_argument(
            '--somente-series',
            action='store_true',
            help=(
                'Atualiza so a metade derivada do banco, sem reler '
                'backend/dados/. Use numa maquina que nao tem os CSVs.'
            ),
        )

    def handle(self, *args, **options):
        exigir_migrations_aplicadas()

        dry_run = options['dry_run']
        somente_series = options['somente_series']
        local = LocalRecife.objects.filter(slug='abrolhos-ba').first()

        if local is None:
            self.stdout.write(
                self.style.WARNING(
                    'Local abrolhos-ba nao encontrado; os registros ficarao sem '
                    'localizacao preenchida.'
                )
            )

        series = construir_inventario_das_series()

        if somente_series:
            # 🚨 **Existe por um estrago real, e nao por gosto de flag.** Os
            # CSVs de `backend/dados/` sao ignorados pelo git (`.gitignore`
            # linha 47), entao numa maquina que clonou o projeto eles
            # simplesmente nao estao la. A execucao completa leria isso como
            # "os nove arquivos sumiram" e gravaria `ativo=False` com
            # `tamanho_mb=None` por cima do que ja estava medido — apagando,
            # sem aviso, o inventario do acervo em disco de quem TEM os
            # arquivos.
            #
            # ⚠️ Os orfaos passam a ser calculados **dentro da metade das
            # series**, e nao sobre o catalogo inteiro. Sem esse recorte, uma
            # execucao com esta flag apagaria os nove registros de arquivo em
            # vez de so ignora-los — trocando um estrago por outro maior.
            registros, ausentes = [], []
            orfaos = DatasetCatalogo.objects.filter(id__startswith='serie-').exclude(
                id__in={r['id'] for r in series}
            )
        else:
            registros, ausentes = construir_inventario(local=local)
            orfaos = DatasetCatalogo.objects.exclude(
                # As duas metades entram no MESMO conjunto antes de calcular
                # orfaos. Calcular sobre so uma delas apagaria a outra a cada
                # execucao - e como `--remover-orfaos` e o padrao, o estrago
                # seria silencioso.
                id__in={r['id'] for r in registros} | {r['id'] for r in series}
            )

        registros += series

        self.stdout.write(f'Datasets no inventario: {len(registros)}')
        self.stdout.write('')

        if somente_series:
            self.stdout.write(
                self.style.WARNING(
                    '  --somente-series: backend/dados/ nao foi lido, e os '
                    'registros de arquivo ficaram como estavam.'
                )
            )
        else:
            self.stdout.write('  Arquivos em backend/dados/:')
            for fonte in DATASETS_REAIS:
                registro = next(r for r in registros if r['id'] == fonte.id)
                d = registro['defaults']
                if d['ativo']:
                    self.stdout.write(
                        f"  [ok]     {fonte.arquivo:<52} {d['tamanho_mb']:>8.2f} MB  "
                        f"{d['data_inicio']} -> {d['data_fim']}"
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [ausente] {fonte.arquivo:<52} desativado'
                        )
                    )

        self.stdout.write('')
        self.stdout.write('  Series ingeridas, por local:')
        if series:
            for registro in series:
                self.stdout.write(
                    f"  [serie]  {registro['id']:<52} "
                    f"-> {registro['defaults']['url_download']}"
                )
        else:
            # Sem isto, um banco vazio produziria uma secao em branco que se
            # le como "nao ha o que catalogar" em vez de "rode a ingestao".
            self.stdout.write(
                self.style.WARNING(
                    '  [nenhuma] Nenhum par (fonte, local) com medicao no banco. '
                    'Rode "manage.py ingerir" antes.'
                )
            )

        if orfaos.exists():
            self.stdout.write('')
            self.stdout.write(
                f'Registros fora do inventario (serao removidos): {orfaos.count()}'
            )
            for item in orfaos:
                self.stdout.write(f'  [remover] {item.id} - {item.titulo}')

        if not somente_series:
            self.stdout.write('')
            self.stdout.write(
                f'Arquivos deliberadamente excluidos do catalogo: {len(EXCLUIDOS)}'
            )
            for arquivo, motivo in EXCLUIDOS.items():
                self.stdout.write(f'  [excluido] {arquivo}: {motivo}')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('--dry-run: nada foi gravado.'))
            return

        with transaction.atomic():
            for registro in registros:
                DatasetCatalogo.objects.update_or_create(
                    id=registro['id'],
                    defaults=registro['defaults'],
                )
            removidos = orfaos.count()
            orfaos.delete()

        ativos = sum(1 for r in registros if r['defaults']['ativo'])
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Catalogo atualizado: {ativos} ativos '
                f'({len(series)} deles series ingeridas), '
                f'{len(ausentes)} desativados por arquivo ausente, '
                f'{removidos} registros antigos removidos.'
            )
        )
