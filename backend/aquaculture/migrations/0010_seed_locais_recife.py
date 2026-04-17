from datetime import date

from django.db import migrations


def seed_locais_recife(apps, schema_editor):
    LocalRecife = apps.get_model('aquaculture', 'LocalRecife')
    StatusPredicao = apps.get_model('aquaculture', 'StatusPredicao')

    locais = [
        {
            'slug': 'abrolhos-ba',
            'nome': 'Parque Nacional Marinho de Abrolhos',
            'estado': 'Bahia',
            'cidade': 'Caravelas',
            'descricao': 'Area de referencia para monitoramento e biodiversidade coralinea.',
            'ultima_atualizacao': date(2026, 4, 14),
            'ativo': True,
        },
        {
            'slug': 'picaozinho-pb',
            'nome': 'Recife de Picaozinho',
            'estado': 'Paraiba',
            'cidade': 'Joao Pessoa',
            'descricao': 'Recife costeiro raso com especies recifais e monitoramento ambiental.',
            'ultima_atualizacao': date(2026, 4, 10),
            'ativo': True,
        },
        {
            'slug': 'porto-de-galinhas-pe',
            'nome': 'Piscinas Naturais de Porto de Galinhas',
            'estado': 'Pernambuco',
            'cidade': 'Ipojuca',
            'descricao': 'Zona recifal turistica com ocorrencia de corais e peixes costeiros.',
            'ultima_atualizacao': date(2026, 4, 15),
            'ativo': True,
        },
    ]

    instancias = {}
    for local in locais:
        instancia, _ = LocalRecife.objects.update_or_create(
            slug=local['slug'],
            defaults=local,
        )
        instancias[local['slug']] = instancia

    abrolhos = instancias['abrolhos-ba']
    StatusPredicao.objects.filter(local_recife__isnull=True).update(local_recife=abrolhos)


def unseed_locais_recife(apps, schema_editor):
    LocalRecife = apps.get_model('aquaculture', 'LocalRecife')
    LocalRecife.objects.filter(
        slug__in=['abrolhos-ba', 'picaozinho-pb', 'porto-de-galinhas-pe']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0009_localrecife_alter_statuspredicao_options_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_locais_recife, unseed_locais_recife),
    ]
