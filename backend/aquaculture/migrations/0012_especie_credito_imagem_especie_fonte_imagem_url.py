from django.db import migrations, models


def preencher_credito_imagem(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')

    for especie in Especie.objects.exclude(foto=''):
        updates = {}
        if not especie.credito_imagem:
            updates['credito_imagem'] = 'Acervo local do projeto'
        if updates:
            Especie.objects.filter(pk=especie.pk).update(**updates)


def limpar_credito_imagem(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')
    Especie.objects.filter(credito_imagem='Acervo local do projeto').update(credito_imagem='')


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0011_seed_especies_e_monitoramento'),
    ]

    operations = [
        migrations.AddField(
            model_name='especie',
            name='credito_imagem',
            field=models.CharField(blank=True, max_length=200, verbose_name='Credito da imagem'),
        ),
        migrations.AddField(
            model_name='especie',
            name='fonte_imagem_url',
            field=models.URLField(blank=True, max_length=500, verbose_name='Link da fonte da imagem'),
        ),
        migrations.RunPython(preencher_credito_imagem, limpar_credito_imagem),
    ]
