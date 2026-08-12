"""Semeia locais que apareciam numa tabela de referencia trazida pelo usuario
e ainda nao existiam no banco. `abrolhos-ba` ja existia (migration `0010`) e
foi deixado de fora de proposito - a tabela trazia coordenadas um pouco
diferentes das ja gravadas (17o57'47" S, 38o42'12" W -> -17,9631/-38,7033,
contra -17,972/-38,688 do seed original) e esta migration nao decide qual
prevalece.

Nenhuma coordenada aqui vem de fonte oficial citavel - foram convertidas de
graus/minutos/segundos que a tabela trazia, sem fonte primaria declarada.
Cada `fonte_coordenadas` registra isso e fica PENDENTE de verificacao
(ICMBio / Marinha do Brasil), mesmo padrao dos tres locais originais em
`0014_seed_coordenadas_locais.py`. Ver docs/FONTES.md secao 2.3.

Duas entradas ficam sem latitude/longitude, de proposito:

- `apa-costa-dos-corais`: area de protecao que atravessa 12 municipios entre
  AL e PE, nao um ponto - qualquer lat/lon unico aqui seria inventado.
- `recife-de-fora-ba`: a propria tabela de origem registrava "nao encontrei
  coordenadas exatas publicadas - nao vou inventar um numero aqui".

Um local sem coordenadas nao entra no pipeline de ingestao por local (ver
`LocalRecife.tem_coordenadas`) - fica cadastrado, sem serie ambiental.
"""

from django.db import migrations

LOCAIS = [
    {
        'slug': 'fernando-de-noronha-pe',
        'nome': 'Arquipelago de Fernando de Noronha',
        'estado': 'Pernambuco',
        'cidade': 'Fernando de Noronha',
        'descricao': (
            'Arquipelago vulcanico com 21 ilhas; Parque Nacional Marinho, '
            'unidade de conservacao federal.'
        ),
        'latitude': -3.8522,
        'longitude': -32.4208,
        'fonte_coordenadas': (
            'Convertida de 3o51\'08" S, 32o25\'15" W, de tabela de '
            'referencia trazida pelo usuario sem fonte primaria citada. '
            'PENDENTE de verificacao em fonte oficial (ICMBio).'
        ),
    },
    {
        'slug': 'atol-das-rocas-rn',
        'nome': 'Atol das Rocas',
        'estado': 'Rio Grande do Norte',
        'cidade': 'Natal',
        'descricao': (
            'Unico atol do Atlantico Sul; Reserva Biologica, visitacao '
            'proibida.'
        ),
        'latitude': -3.8631,
        'longitude': -33.8061,
        'fonte_coordenadas': (
            'Convertida de 3o51\'47" S, 33o48\'22" W, de tabela de '
            'referencia trazida pelo usuario sem fonte primaria citada. '
            'Municipio (Natal) e coordenadas PENDENTES de verificacao em '
            'fonte oficial (ICMBio).'
        ),
    },
    {
        'slug': 'parcel-manuel-luis-ma',
        'nome': 'Parcel de Manuel Luis',
        'estado': 'Maranhao',
        'cidade': 'Cururupu',
        'descricao': (
            'Um dos maiores bancos de corais da America do Sul; Parque '
            'Estadual Marinho.'
        ),
        'latitude': -0.9133,
        'longitude': -44.3194,
        'fonte_coordenadas': (
            'Convertida de 0o54\'48" S, 44o19\'10" W, de tabela de '
            'referencia trazida pelo usuario sem fonte primaria citada. '
            'PENDENTE de verificacao em fonte oficial (ICMBio).'
        ),
    },
    {
        'slug': 'parrachos-de-maracajau-rn',
        'nome': 'Parrachos de Maracajau',
        'estado': 'Rio Grande do Norte',
        'cidade': 'Maxaranguape',
        'descricao': (
            'Piscinas naturais recifais; ponto turistico conhecido para '
            'mergulho de superficie.'
        ),
        'latitude': -5.4025,
        'longitude': -35.2969,
        'fonte_coordenadas': (
            'Convertida de 5o24\'09" S, 35o17\'49" W, de tabela de '
            'referencia trazida pelo usuario sem fonte primaria citada. '
            'PENDENTE de verificacao em fonte oficial (ICMBio).'
        ),
    },
    {
        'slug': 'apa-costa-dos-corais',
        'nome': 'APA Costa dos Corais',
        'estado': 'Alagoas/Pernambuco',
        'cidade': 'Diversos municipios (AL/PE)',
        'descricao': (
            'Area de Protecao Ambiental que se estende por 12 municipios '
            'entre Alagoas e Pernambuco - nao e um ponto unico, por isso '
            'sem latitude/longitude aqui.'
        ),
        'latitude': None,
        'longitude': None,
        'fonte_coordenadas': (
            'Sem coordenada: e uma area, nao um ponto. Um lat/lon unico '
            'para 12 municipios seria inventado.'
        ),
    },
    {
        'slug': 'recife-de-fora-ba',
        'nome': 'Parque Marinho de Recife de Fora',
        'estado': 'Bahia',
        'cidade': 'Porto Seguro',
        'descricao': (
            'Recife costeiro protegido a cerca de 5 milhas nauticas da '
            'costa de Porto Seguro, area de uso publico para mergulho.'
        ),
        'latitude': None,
        'longitude': None,
        'fonte_coordenadas': (
            'Sem coordenadas exatas publicadas na tabela de referencia '
            'trazida pelo usuario - nao estimadas para nao fabricar '
            'posicao. Localizacao aproximada: ~5 milhas nauticas da costa '
            'de Porto Seguro/BA.'
        ),
    },
    {
        'slug': 'areia-vermelha-pb',
        'nome': 'Parque Estadual Marinho de Areia Vermelha',
        'estado': 'Paraiba',
        'cidade': 'Cabedelo',
        'descricao': (
            'Banco de areia recifal que emerge apenas na mare baixa, em '
            'frente a Cabedelo.'
        ),
        'latitude': -7.0047,
        'longitude': -34.8125,
        'fonte_coordenadas': (
            'Convertida de 7o00\'17" S, 34o48\'45" W, de tabela de '
            'referencia trazida pelo usuario sem fonte primaria citada. '
            'PENDENTE de verificacao em fonte oficial (ICMBio).'
        ),
    },
]


def seed_novos_locais(apps, schema_editor):
    LocalRecife = apps.get_model('aquaculture', 'LocalRecife')
    for local in LOCAIS:
        campos = dict(local)
        slug = campos.pop('slug')
        campos['ativo'] = True
        LocalRecife.objects.update_or_create(slug=slug, defaults=campos)


def unseed_novos_locais(apps, schema_editor):
    LocalRecife = apps.get_model('aquaculture', 'LocalRecife')
    LocalRecife.objects.filter(
        slug__in=[local['slug'] for local in LOCAIS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0024_conferencia_iucn_agosto_2026'),
    ]

    operations = [
        migrations.RunPython(seed_novos_locais, unseed_novos_locais),
    ]
