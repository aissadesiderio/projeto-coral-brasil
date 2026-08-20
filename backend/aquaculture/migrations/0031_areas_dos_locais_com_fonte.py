"""Duas areas por local, cada uma com a sua fonte — e os valores conferidos.

🚨 **`area_km2` sai, e nao e renomeacao.** O campo antigo dizia "area
aproximada da zona recifal" e ficou **nulo nos 10 locais** desde a migracao
`0014` — deliberadamente, "para nao inventar numero sem fonte"
(docs/FONTES.md §2.3). Ao procurar as fontes em 13/08/2026, descobriu-se que a
lacuna nao vinha de falta de dado: vinha de a pergunta ter **duas respostas
certas**, separadas por tres ordens de grandeza.

Abrolhos, todos com fonte publicada:

| Numero | O que e |
|---|---|
| ~8 km² | os recifes mapeados dentro do parque |
| 879,43 km² | o **parque** (87.943 ha, ICMBio) |
| 6.000 km² | o ecossistema recifal do Banco norte |
| 45.000 km² | o **Banco dos Abrolhos** |

Guardar qualquer um deles sozinho, sob um rotulo que diz "zona recifal", seria
o erro de categoria que docs/FONTES.md §6.3 ja registra (alcalinidade gravada
como pH). Como o campo estava nulo em toda parte, remove-lo nao perde nada.

⚠️ **Sete locais recebem area da UC; tres ficam nulos de proposito.**
`parrachos-de-maracajau-rn`, `picaozinho-pb` e `porto-de-galinhas-pe` **nao sao
unidades de conservacao** — sao feicoes recifais dentro de UCs maiores (ou, no
caso de Picaozinho, sem protecao legal ainda). Gravar neles a area da APA que
os contem diria que o parracho tem 1.360 km², que e a area da APA dos Recifes
de Corais inteira. E a area do continente atribuida a ilha.

🚨 **`area_recifal_km2` nasce nula nos 10, e isso e o resultado, nao a
pendencia.** Ha um numero circulando para Abrolhos — ~8 km², ~3,4% da area de
estudo, de um mapeamento WorldView-2. A **referencia foi identificada** (Zoffoli
et al., 2022, Continental Shelf Research 246:104808, DOI
10.1016/j.csr.2022.104808, confirmada no Crossref e pela noticia do proprio
INPE, instituicao dos autores), mas o artigo esta atras de paywall e **o numero
nao foi lido na fonte** — so em resumos de terceiros.

⚠️ Isso e suficiente para citar o artigo e insuficiente para gravar o numero, e
a distincao ja tem precedente no projeto: em §2.4 as categorias da IUCN
conferidas so no Wikidata **nao foram gravadas** ("e forte mas e copia"). Mesmo
criterio aqui.

Ver docs/FONTES.md secao 2.5 para a tabela completa, com as divergencias entre
fontes secundarias que motivaram usar o ICMBio como autoridade.
"""

from django.core.validators import MinValueValidator
from django.db import migrations, models


# (slug, area_km2, fonte)
#
# ⚠️ Os valores sao a conversao exata de hectares para km² (divisao por 100),
# sem arredondar. A fonte guarda o numero **como publicado**, na unidade
# publicada, para a conversao poder ser conferida sem sair daqui.
AREAS_DE_UC = [
    (
        'abrolhos-ba',
        879.43,
        'ICMBio (PARNA Marinho dos Abrolhos) - 87.943 ha, em dois poligonos '
        '(Recife de Timbebas e Arquipelago dos Abrolhos). Criado pelo Dec. '
        '88.218 de 06/04/1983.',
    ),
    (
        'fernando-de-noronha-pe',
        109.2947,
        'ICMBio (PARNA Marinho de Fernando de Noronha) - 10.929,47 ha. Criado '
        'pelo Dec. 96.693 de 14/09/1988.',
    ),
    (
        'atol-das-rocas-rn',
        351.8641,
        'ICMBio (REBIO do Atol das Rocas) - 35.186,41 ha. Criada pelo Dec. '
        '83.549 de 05/06/1979, primeira UC marinha do Brasil.',
    ),
    (
        'apa-costa-dos-corais',
        4950.84,
        'Dec. 12.490 de 05/06/2025 (ampliacao, +89.441,64 ha) - 495.084 ha no '
        'total. Criada por decreto de 23/10/1997. Maior UC marinha costeira '
        'federal do pais.',
    ),
    (
        'parcel-manuel-luis-ma',
        459.379,
        'SEMA-MA, Plano de Manejo de Especies e Habitats do PEM do Parcel de '
        'Manuel Luis, p.10 - 45.937,9 ha. Criado pelo Dec. Estadual 11.902 de '
        '11/06/1991, primeiro parque marinho estadual do pais.',
    ),
    (
        'recife-de-fora-ba',
        17.5,
        'Parque Natural Municipal Marinho do Recife de Fora (Porto Seguro/BA) '
        '- 1.750 ha, Lei municipal 260/97 de 16/12/1997. Conferido na Rede de '
        'Gestores de UCs Costeiras e Marinhas; texto da lei nao lido.',
    ),
    (
        'areia-vermelha-pb',
        2.31,
        'Dec. estadual PB 21.263 de 28/08/2000 - 231,00 ha. O Plano de Manejo '
        '(SUDEMA/PB, p.38) remede 230,915 ha; mantido aqui o valor legal.',
    ),
]

# Por que os outros tres ficam nulos. Nao vai para o banco — o campo vazio ja
# diz "nao registrado" —, mas fica aqui para a proxima pessoa nao "corrigir" a
# lacuna preenchendo com a area da UC que contem o local.
#
# | Local | Por que |
# |---|---|
# | parrachos-de-maracajau-rn | dentro da APA dos Recifes de Corais/RN (~136.000 ha, Dec. estadual 15.746/2001); o parracho nao e UC |
# | porto-de-galinhas-pe | dentro da APA Costa dos Corais; nao e UC propria |
# | picaozinho-pb | sem protecao legal propria — ha proposta de APA (Naufragio Queimado), ainda nao vigente |


def preencher_areas(apps, schema_editor):
    LocalRecife = apps.get_model('aquaculture', 'LocalRecife')

    for slug, area, fonte in AREAS_DE_UC:
        # ⚠️ `update` sobre o filtro, e nao `get` + `save`: um slug ausente
        # nao pode derrubar a migracao. Os locais vem de seeds anteriores, e um
        # banco que ainda nao os tem e um banco valido.
        LocalRecife.objects.filter(slug=slug).update(
            area_uc_km2=area, fonte_area_uc=fonte,
        )


def limpar_areas(apps, schema_editor):
    LocalRecife = apps.get_model('aquaculture', 'LocalRecife')
    LocalRecife.objects.filter(slug__in=[s for s, _, _ in AREAS_DE_UC]).update(
        area_uc_km2=None, fonte_area_uc='',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0030_proveniencia_da_foto_do_local'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='localrecife',
            name='area_km2',
        ),
        migrations.AddField(
            model_name='localrecife',
            name='area_uc_km2',
            field=models.FloatField(
                blank=True, null=True,
                validators=[MinValueValidator(0.0)],
                verbose_name='Area da unidade de conservacao (km²)',
                help_text=(
                    'Area oficial da UC, quando este local E uma unidade de '
                    'conservacao. Deixe vazio quando o local for so uma feicao '
                    'recifal dentro de uma UC maior — a area da APA nao e a area do '
                    'recife que ela contem.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='localrecife',
            name='fonte_area_uc',
            field=models.CharField(
                blank=True, max_length=300,
                verbose_name='Fonte da area da UC',
                help_text=(
                    'Orgao, decreto e o numero como publicado. Ex: ICMBio, '
                    '87.943 ha, Dec 88.218/1983'
                ),
            ),
        ),
        migrations.AddField(
            model_name='localrecife',
            name='area_recifal_km2',
            field=models.FloatField(
                blank=True, null=True,
                validators=[MinValueValidator(0.0)],
                verbose_name='Area recifal mapeada (km²)',
                help_text=(
                    'So com mapeamento publicado e conferido. Nao derive da area da '
                    'UC nem estime por proporcao.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='localrecife',
            name='fonte_area_recifal',
            field=models.CharField(
                blank=True, max_length=300,
                verbose_name='Fonte da area recifal',
                help_text='Publicacao, sensor e ano do mapeamento.',
            ),
        ),
        migrations.RunPython(preencher_areas, limpar_areas),
    ]
