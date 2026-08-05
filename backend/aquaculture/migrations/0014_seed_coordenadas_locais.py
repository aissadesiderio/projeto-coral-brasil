"""Preenche as coordenadas dos locais de recife ja semeados.

Sem latitude/longitude os conectores de ingestao (Fase B) nao conseguem
extrair dados por local - ficam presos a uma bbox fixa de Abrolhos.

Rastreabilidade: cada registro guarda a origem da coordenada em
`fonte_coordenadas`. As marcadas como "aproximada" foram derivadas da
localizacao da zona recifal e precisam ser conferidas contra uma fonte
oficial (ICMBio, Allen Coral Atlas) antes do go-live.
Ver docs/FONTES.md.
"""

from django.db import migrations

COORDENADAS = {
    'abrolhos-ba': {
        'latitude': -17.972,
        'longitude': -38.688,
        'profundidade_media_m': 10.0,
        'fonte_coordenadas': (
            'Seed original do projeto (backend/db/setup_graph.py) - '
            'Arquipelago dos Abrolhos. Conferir contra ICMBio.'
        ),
    },
    'picaozinho-pb': {
        'latitude': -7.108,
        'longitude': -34.810,
        'fonte_coordenadas': (
            'Aproximada - zona recifal a ~1,5 km da praia de Tambau, '
            'Joao Pessoa/PB. PENDENTE de verificacao em fonte oficial.'
        ),
    },
    'porto-de-galinhas-pe': {
        'latitude': -8.510,
        'longitude': -34.998,
        'fonte_coordenadas': (
            'Aproximada - piscinas naturais a ~500 m da praia, Ipojuca/PE. '
            'PENDENTE de verificacao em fonte oficial.'
        ),
    },
}


def seed_coordenadas(apps, schema_editor):
    LocalRecife = apps.get_model('aquaculture', 'LocalRecife')
    for slug, valores in COORDENADAS.items():
        LocalRecife.objects.filter(slug=slug).update(**valores)


def unseed_coordenadas(apps, schema_editor):
    LocalRecife = apps.get_model('aquaculture', 'LocalRecife')
    LocalRecife.objects.filter(slug__in=COORDENADAS).update(
        latitude=None,
        longitude=None,
        profundidade_media_m=None,
        fonte_coordenadas='',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0013_localrecife_area_km2_localrecife_fonte_coordenadas_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_coordenadas, unseed_coordenadas),
    ]
