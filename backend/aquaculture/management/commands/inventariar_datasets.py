"""Reconstroi o catalogo de datasets a partir dos arquivos que existem de fato.

Uso:
    python backend/manage.py inventariar_datasets
    python backend/manage.py inventariar_datasets --dry-run

Substitui o seed ficticio da migration 0014. Ver docs/FONTES.md secao 6.14.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from aquaculture.inventario_datasets import (
    DATASETS_REAIS,
    EXCLUIDOS,
    construir_inventario,
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

    def handle(self, *args, **options):
        exigir_migrations_aplicadas()

        dry_run = options['dry_run']
        local = LocalRecife.objects.filter(slug='abrolhos-ba').first()

        if local is None:
            self.stdout.write(
                self.style.WARNING(
                    'Local abrolhos-ba nao encontrado; os registros ficarao sem '
                    'localizacao preenchida.'
                )
            )

        registros, ausentes = construir_inventario(local=local)
        ids_inventario = {r['id'] for r in registros}
        orfaos = DatasetCatalogo.objects.exclude(id__in=ids_inventario)

        self.stdout.write(f'Datasets no inventario: {len(registros)}')
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
                    self.style.WARNING(f'  [ausente] {fonte.arquivo:<52} desativado')
                )

        if orfaos.exists():
            self.stdout.write('')
            self.stdout.write(
                f'Registros fora do inventario (serao removidos): {orfaos.count()}'
            )
            for item in orfaos:
                self.stdout.write(f'  [remover] {item.id} - {item.titulo}')

        self.stdout.write('')
        self.stdout.write(f'Arquivos deliberadamente excluidos do catalogo: {len(EXCLUIDOS)}')
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
                f'Catalogo atualizado: {ativos} ativos, '
                f'{len(ausentes)} desativados por arquivo ausente, '
                f'{removidos} registros antigos removidos.'
            )
        )
