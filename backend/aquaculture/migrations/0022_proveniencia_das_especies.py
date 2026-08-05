"""Da as especies a mesma proveniencia que o lado ambiental sempre teve.

🚨 **Era a metade sem procedencia do projeto.** Cada valor de
`MedicaoAmbiental` grava `fonte`, `dataset_id` e `quality_flag`; as especies
vieram de uma lista digitada a mao na migracao 0011, e a conservacao era
**texto livre**. Nas 9 especies, `fonte_url` estava vazio em **todas**.

Isso pesava mais que as outras lacunas por um motivo especifico: a categoria de
conservacao e **o unico campo do banco que alguem vai citar**.

⚠️ **A decisao dificil desta migracao: o que fazer com "Nao avaliado".**

Cinco das nove especies tinham esse valor, e ha duas leituras:

1. a IUCN avaliou e devolveu a categoria **NE** (*Not Evaluated*);
2. quem digitou a lista nao consultou.

**As duas sao indistinguiveis no dado**, e mapear para `NE` afirmaria a
primeira. Pior: ela e **provavelmente falsa** para pelo menos duas das cinco —
`Holacanthus ciliaris` e `Ocyurus chrysurus` sao especies comerciais com
avaliacao publicada na Lista Vermelha. Gravar `NE` nelas inventaria uma
afirmacao errada onde hoje ha so uma lacuna.

Por isso **"Nao avaliado" vira categoria vazia**: nao sabemos. As quatro
categorias restantes viram o codigo oficial (`VU`, `LC`, `NT`, `CR`), que e o
que a IUCN publica — traducao livre nao volta ao original sem ambiguidade.

⚠️ **Nenhuma das nove ganha ano**, porque nenhum foi registrado. Consequencia
imediata e deliberada: **o site deixa de exibir categoria de conservacao para
todas elas** ate alguem preencher `iucn_avaliado_em`. Nao e regressao — e parar
de afirmar o que nao se consegue datar.

O exemplo que torna isso concreto esta no proprio acervo: `Dendrogyra
cylindrus` foi **Vulneravel de 2008 a 2022**, quando passou a **Criticamente
Ameacada**. As duas afirmacoes estao certas, em anos diferentes; sem o ano, a
tela nao distingue "e CR" de "era VU quando alguem digitou isto".

🚨 **E nao era so falta de lastro: um dos quatro valores estava ERRADO.**
Conferido em 31/07/2026, ao coletar a procedencia: `Mussismilia braziliensis`
estava gravada como **VU** e a IUCN a registra como **CR** desde a versao
2022-2. E o coral-cerebro brasileiro, endemico, a especie que abre a pagina de
Abrolhos — e o site a exibia dois degraus abaixo.

Isso decide a favor de esconder tudo ate haver ano. A alternativa "menos
destrutiva" — manter as categorias exibiveis enquanto a procedencia nao chega —
deixaria essa afirmacao errada no ar por mais tempo, com aparencia de dado
corrigido.

⚠️ Por isso existe `iucn_consultado_em` **separado** de `iucn_versao`. Os dois
respondem perguntas diferentes, e so o primeiro pega este erro:

| Campo | Responde |
|---|---|
| `iucn_avaliado_em` + `iucn_versao` | **qual** avaliacao foi lida |
| `iucn_consultado_em` | **ha quanto tempo** ninguem confere |

A categoria nao envelhece porque a avaliacao muda de conteudo; envelhece porque
a IUCN publica **outra** e o registro local continua apontando para a antiga.

📌 **`iucn_origem` registra COMO o dado foi obtido**, e nao so qual e. Sem
isso o acervo vira mistura indistinguivel de API, conferencia manual e
terceiro, e nao ha como auditar o que pode ser citado como IUCN. A opcao
`terceiro` existe para ser honesta sobre um caminho que pode vir a ser usado —
Wikidata e GBIF publicam a categoria sem token, e sao fonte legitima **se
declarada**; o que nao pode e apresenta-las como se fossem a IUCN.

**Reversivel:** o caminho de volta recompoe `status_conservacao` a partir do
codigo. As cinco que viraram vazio voltam como "Nao avaliado", que e exatamente
o que elas eram.
"""

from django.db import migrations, models

# Os rotulos digitados na 0011 -> codigo oficial da Lista Vermelha.
# "Nao avaliado" **nao** entra: ver o cabecalho.
PARA_CODIGO = {
    'Criticamente ameacado': 'CR',
    'Em perigo': 'EN',
    'Vulneravel': 'VU',
    'Quase ameacado': 'NT',
    'Pouco preocupante': 'LC',
    'Dados insuficientes': 'DD',
}

DE_CODIGO = {codigo: rotulo for rotulo, codigo in PARA_CODIGO.items()}


def para_codigo_iucn(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')
    for especie in Especie.objects.all():
        codigo = PARA_CODIGO.get((especie.status_conservacao or '').strip())
        if codigo:
            especie.iucn_categoria = codigo
            especie.save(update_fields=['iucn_categoria'])


def de_volta_para_texto(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')
    for especie in Especie.objects.all():
        especie.status_conservacao = DE_CODIGO.get(
            especie.iucn_categoria, 'Nao avaliado'
        )
        especie.save(update_fields=['status_conservacao'])


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0021_remover_statuspredicao'),
    ]

    operations = [
        # --- 1. identificadores taxonomicos --------------------------------
        migrations.AddField(
            model_name='especie',
            name='aphia_id',
            field=models.PositiveIntegerField(
                blank=True, null=True, unique=True,
                help_text='Identificador do World Register of Marine Species.',
                verbose_name='AphiaID (WoRMS)',
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='gbif_key',
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name='usageKey (GBIF)',
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='status_taxonomico',
            field=models.CharField(
                blank=True, max_length=40,
                help_text='O que o WoRMS respondeu: accepted, unaccepted, etc.',
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='nome_aceito',
            field=models.CharField(
                blank=True, max_length=200,
                help_text='Preenchido so quando difere de nome_cientifico.',
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='taxonomia_conferida_em',
            field=models.DateField(blank=True, null=True),
        ),

        # --- 2. conservacao com proveniencia -------------------------------
        migrations.AddField(
            model_name='especie',
            name='iucn_origem',
            field=models.CharField(
                blank=True, max_length=10, verbose_name='Como foi obtida',
                choices=[
                    ('api', 'API da IUCN'),
                    ('ficha', 'Ficha da IUCN, conferida a mao'),
                    ('terceiro', 'Terceiro (Wikidata, GBIF) — cita-se o terceiro'),
                ],
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='iucn_categoria',
            field=models.CharField(
                blank=True, max_length=2, verbose_name='Categoria IUCN',
                choices=[
                    ('EX', 'Extinta'), ('EW', 'Extinta na natureza'),
                    ('CR', 'Criticamente ameacada'), ('EN', 'Em perigo'),
                    ('VU', 'Vulneravel'), ('NT', 'Quase ameacada'),
                    ('LC', 'Pouco preocupante'), ('DD', 'Dados insuficientes'),
                    ('NE', 'Nao avaliada'),
                ],
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='iucn_taxon_id',
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name='ID do taxon na IUCN',
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='iucn_avaliado_em',
            field=models.PositiveSmallIntegerField(
                blank=True, null=True, verbose_name='Ano da avaliacao',
                help_text='O ano da avaliacao publicada, nao o ano da consulta.',
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='iucn_versao',
            field=models.CharField(
                blank=True, max_length=20,
                verbose_name='Versao em que a avaliacao foi publicada',
                help_text=(
                    'A versao da Lista Vermelha em que ESTA avaliacao saiu '
                    '(ex: 2022-2), e nao a versao que voce esta consultando '
                    'hoje.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='iucn_consultado_em',
            field=models.DateField(
                blank=True, null=True, verbose_name='Ultima conferencia',
                help_text=(
                    'Quando alguem abriu a ficha e confirmou que continua '
                    'valendo.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='especie',
            name='fonte_iucn_url',
            field=models.URLField(
                blank=True, max_length=500, verbose_name='Ficha na IUCN',
            ),
        ),

        # --- 3. so entao mover o dado, e so entao apagar a coluna ----------
        migrations.RunPython(para_codigo_iucn, de_volta_para_texto),
        migrations.RemoveField(model_name='especie', name='status_conservacao'),
    ]
