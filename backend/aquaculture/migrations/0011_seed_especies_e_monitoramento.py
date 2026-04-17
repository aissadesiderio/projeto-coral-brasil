from datetime import date

from django.db import migrations


def seed_especies_e_monitoramento(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')
    LocalRecife = apps.get_model('aquaculture', 'LocalRecife')
    StatusPredicao = apps.get_model('aquaculture', 'StatusPredicao')

    locais = {local.slug: local for local in LocalRecife.objects.all()}
    if not locais:
        return

    especies = [
        {
            'nome_cientifico': 'Mussismilia braziliensis',
            'nome_comum': 'Coral-cerebro brasileiro',
            'tipo': 'CORAL',
            'descricao': 'Especie endemica do Brasil e importante formadora de recifes no Banco dos Abrolhos.',
            'status_conservacao': 'Vulneravel',
            'foto': 'especies/Mussismilia_braziliensis.jpg',
            'local_slugs': ['abrolhos-ba'],
        },
        {
            'nome_cientifico': 'Montastraea cavernosa',
            'nome_comum': 'Coral-estrela',
            'tipo': 'CORAL',
            'descricao': 'Coral construtor frequente em substratos consolidados, relevante para a estrutura recifal.',
            'status_conservacao': 'Pouco preocupante',
            'foto': 'especies/Montastraea_cavernosa.jpg',
            'local_slugs': ['abrolhos-ba'],
        },
        {
            'nome_cientifico': 'Holacanthus ciliaris',
            'nome_comum': 'Peixe-anjo-rainha',
            'tipo': 'PEIXE',
            'descricao': 'Peixe recifal colorido, comum em ambientes coralineos com abrigo e alimento disponiveis.',
            'status_conservacao': 'Nao avaliado',
            'foto': 'especies/Holacanthus_ciliaris.jpeg',
            'local_slugs': ['abrolhos-ba'],
        },
        {
            'nome_cientifico': 'Condylactis gigantea',
            'nome_comum': 'Anemona-gigante',
            'tipo': 'INVERTEBRADO',
            'descricao': 'Invertebrado cnidario comum em ambientes recifais rasos e iluminados.',
            'status_conservacao': 'Nao avaliado',
            'foto': 'especies/Condylactis_gigantea.jpg',
            'local_slugs': ['picaozinho-pb'],
        },
        {
            'nome_cientifico': 'Ocyurus chrysurus',
            'nome_comum': 'Cioba',
            'tipo': 'PEIXE',
            'descricao': 'Peixe recifal associado a fundos rochosos e coralineos do Atlantico tropical.',
            'status_conservacao': 'Nao avaliado',
            'foto': 'especies/Ocyurus_chrysurus.jpeg',
            'local_slugs': ['picaozinho-pb'],
        },
        {
            'nome_cientifico': 'Sparisoma axillare',
            'nome_comum': 'Budiao-azul',
            'tipo': 'PEIXE',
            'descricao': 'Peixe herbivoro importante para a dinamica do recife e controle de algas.',
            'status_conservacao': 'Quase ameacado',
            'foto': 'especies/Sparisoma_axillare.jpg',
            'local_slugs': ['picaozinho-pb'],
        },
        {
            'nome_cientifico': 'Phyllogorgia dilatata',
            'nome_comum': 'Gorgonia-roxa',
            'tipo': 'CORAL',
            'descricao': 'Gorgonia ramificada encontrada em ambientes recifais do litoral brasileiro.',
            'status_conservacao': 'Nao avaliado',
            'foto': 'especies/Phyllogorgia_dilatata.jpg',
            'local_slugs': ['porto-de-galinhas-pe'],
        },
        {
            'nome_cientifico': 'Muricea flamma',
            'nome_comum': 'Coral-fogo-vermelho',
            'tipo': 'CORAL',
            'descricao': 'Octocoral associado a ambientes recifais com boa circulacao de agua.',
            'status_conservacao': 'Nao avaliado',
            'foto': 'especies/Muricea_flamma.jpg',
            'local_slugs': ['porto-de-galinhas-pe'],
        },
        {
            'nome_cientifico': 'Dendrogyra cylindrus',
            'nome_comum': 'Coral-pilar',
            'tipo': 'CORAL',
            'descricao': 'Coral de formato colunar com registros em areas recifais tropicais.',
            'status_conservacao': 'Criticamente ameacado',
            'foto': 'especies/Dendrogyra_cylindrus.jpeg',
            'local_slugs': ['porto-de-galinhas-pe'],
        },
    ]

    for especie_data in especies:
        local_slugs = especie_data.pop('local_slugs')
        especie, _ = Especie.objects.update_or_create(
            nome_cientifico=especie_data['nome_cientifico'],
            defaults=especie_data,
        )
        especie.locais.set([locais[slug].id for slug in local_slugs if slug in locais])

    monitoramentos = [
        {
            'local_slug': 'abrolhos-ba',
            'data': date(2026, 4, 14),
            'sst_atual': 29.4,
            'limite_termico': 27.0,
            'anomalia': 2.4,
            'dhw_calculado': 6.3,
            'irradiancia': 31.8,
            'turbidez': 0.17,
            'salinidade': 36.1,
            'ph': 8.09,
            'oxigenio': 6.42,
            'nitrato': 0.36,
            'clorofila': 0.64,
            'risco_integrado': 78.0,
            'nivel_alerta': 'ALERTA_1',
        },
        {
            'local_slug': 'picaozinho-pb',
            'data': date(2026, 4, 10),
            'sst_atual': 28.7,
            'limite_termico': 27.0,
            'anomalia': 1.7,
            'dhw_calculado': 3.9,
            'irradiancia': 29.6,
            'turbidez': 0.28,
            'salinidade': 35.7,
            'ph': 8.05,
            'oxigenio': 6.31,
            'nitrato': 0.51,
            'clorofila': 0.82,
            'risco_integrado': 58.0,
            'nivel_alerta': 'OBSERVACAO',
        },
        {
            'local_slug': 'porto-de-galinhas-pe',
            'data': date(2026, 4, 15),
            'sst_atual': 29.0,
            'limite_termico': 27.0,
            'anomalia': 2.0,
            'dhw_calculado': 5.1,
            'irradiancia': 30.4,
            'turbidez': 0.22,
            'salinidade': 35.9,
            'ph': 8.07,
            'oxigenio': 6.27,
            'nitrato': 0.43,
            'clorofila': 0.71,
            'risco_integrado': 69.0,
            'nivel_alerta': 'ALERTA_1',
        },
    ]

    for monitoramento in monitoramentos:
        local = locais.get(monitoramento.pop('local_slug'))
        if not local:
            continue
        StatusPredicao.objects.update_or_create(
            local_recife=local,
            data=monitoramento['data'],
            defaults=monitoramento,
        )


def unseed_especies_e_monitoramento(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')
    StatusPredicao = apps.get_model('aquaculture', 'StatusPredicao')

    Especie.objects.filter(
        nome_cientifico__in=[
            'Mussismilia braziliensis',
            'Montastraea cavernosa',
            'Holacanthus ciliaris',
            'Condylactis gigantea',
            'Ocyurus chrysurus',
            'Sparisoma axillare',
            'Phyllogorgia dilatata',
            'Muricea flamma',
            'Dendrogyra cylindrus',
        ]
    ).delete()
    StatusPredicao.objects.filter(
        data__in=[date(2026, 4, 14), date(2026, 4, 10), date(2026, 4, 15)]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0010_seed_locais_recife'),
    ]

    operations = [
        migrations.RunPython(seed_especies_e_monitoramento, unseed_especies_e_monitoramento),
    ]
