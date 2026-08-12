"""Proveniencia da foto do local de recife.

🚨 A migracao `0026` corrigiu a proveniencia das fotos de **especie**, e parou
ali. `LocalRecife.imagem` — a foto que aparece no topo da pagina do recife e no
cartao da lista — nunca teve onde registrar autor, fonte ou local de captura.
Nao e o caso das especies (credito errado, auditavel): aqui era a ausencia do
campo, que nao deixa nem rastro para conferir.

Nenhum dado a corrigir: os locais cadastrados estao todos com `imagem` vazia,
entao esta migracao so abre os tres campos. Ver docs/FONTES.md secao 2.2.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0029_datasetcatalogo_download_exige_conta'),
    ]

    operations = [
        migrations.AddField(
            model_name='localrecife',
            name='credito_imagem',
            field=models.CharField(
                blank=True,
                help_text='Site, instituicao ou nome de quem tirou/cedeu a foto.',
                max_length=200,
                verbose_name='Credito da imagem',
            ),
        ),
        migrations.AddField(
            model_name='localrecife',
            name='fonte_imagem_url',
            field=models.URLField(
                blank=True,
                help_text='A pagina de origem da foto — nunca a URL da copia local.',
                max_length=500,
                verbose_name='Link da fonte da imagem',
            ),
        ),
        migrations.AddField(
            model_name='localrecife',
            name='local_captura_foto',
            field=models.CharField(
                blank=True,
                help_text=(
                    'Onde a foto foi tirada, quando se souber. Nao e a coordenada '
                    'monitorada: pode ser outro ponto do mesmo recife, ou uma vista '
                    'aerea. Deixe vazio se nao souber.'
                ),
                max_length=200,
                verbose_name='Local de captura da foto',
            ),
        ),
    ]
