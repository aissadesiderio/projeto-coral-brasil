"""Remove os 8 datasets ficticios semeados por 0014_seed_datasetcatalogo.

Aqueles registros descreviam conjuntos de dados que nao existem: dois eram
atribuidos ao NCBI, fonte da qual o projeto nao tem um unico byte, quatro
apontavam para arquivos inexistentes, e o de SST declarava 1843,2 MB quando o
arquivo real tem 0,65 MB. Como o commit 34879bf passou a servi-los por uma API
real, a ficcao deixou de parecer mock e passou a parecer dado.

Num trabalho academico isso e atribuicao falsa de fonte. Ver docs/FONTES.md,
secao 6.14.

O catalogo real e reconstruido a partir dos arquivos de fato existentes por:

    python backend/manage.py inventariar_datasets

Nao populamos aqui porque o inventario depende de ler os CSVs em
backend/dados/, que nao sao versionados - um clone novo comeca com o catalogo
vazio, o que e a descricao correta do seu estado.
"""

from django.db import migrations

IDS_FICTICIOS = [
    'copernicus_sst_abrolhos_2026_03',
    'noaa_dhw_abrolhos_2026_03',
    'inventario_biodiversidade_abrolhos_2026_q1',
    'microbioma_picaozinho_2026_03',
    'genetico_abrolhos_2026_q1',
    'imagem_porto_2026_04',
    'relatorio_picaozinho_2026_04',
    'modelo_branqueamento_nordeste_2026_q2',
]


def remover_ficticios(apps, schema_editor):
    DatasetCatalogo = apps.get_model('aquaculture', 'DatasetCatalogo')
    DatasetCatalogo.objects.filter(id__in=IDS_FICTICIOS).delete()


def reverter(apps, schema_editor):
    """Intencionalmente sem efeito.

    Reverter significaria reinserir dados falsos no banco. A migration 0014
    permanece no historico para quem precisar inspecionar o que existia.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0015_merge_20260724_2332'),
    ]

    operations = [
        migrations.RunPython(remover_ficticios, reverter),
    ]
