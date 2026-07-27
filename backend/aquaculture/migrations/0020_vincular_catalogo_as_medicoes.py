"""Liga cada dataset do catalogo ao que existe (ou nao) no banco.

🚨 **O que esta migracao conserta.** Medido em 27/07/2026: a pagina "Banco de
Dados" anunciava **9 datasets** e o projeto espelhava **3**. pH, clorofila,
nitrato, thetao, KD490 e o SST do Met Office apareciam com titulo, resumo,
formato e periodo — e nao existia **uma unica medicao** deles no banco.

Nenhum registro e apagado. Um catalogo pode e deve apontar para produtos que o
projeto nao guarda; o que nao podia era **nao dizer qual e qual**. Depois desta
migracao, `fonte_medicao` vazio significa "referencia externa", e o serializer
passa a declarar isso na resposta.

⚠️ Os `data_inicio`/`data_fim` gravados **nao sao corrigidos aqui**, de
proposito. Eles descrevem o produto no provedor, e continuam certos: o L4 do
Met Office comeca em 1981 mesmo. O que estava errado era usa-los como se
fossem a cobertura do projeto — e isso quem resolve e a cobertura derivada, nao
uma correcao pontual que envelheceria de novo.
"""

from django.db import migrations

# id do catalogo -> (fonte da medicao, variaveis canonicas)
#
# Vazio = referencia externa. Os motivos, um a um:
#
# - `kd490`: descartada por decisao medida — so existe de 2023-11 em diante e
#   nao tem reanalise, o que cortaria o treino de 6,5 para 2,7 anos
#   (docs/VARIAVEIS.md secao 3.5).
# - `ph`, `clorofila`, `nitrato`: ingeridas apenas para o experimento do GCBD,
#   em CSV fora do banco, e nenhuma acrescentou sinal (docs/RESULTADOS.md
#   secao 21).
# - `thetao`: a temperatura do Copernicus nao entra porque a SST do projeto vem
#   do CRW, e misturar dois produtos na mesma variavel destruiria a
#   proveniencia por valor.
# - `metoffice_sst_l4`: mesma razao — o projeto le o CRW.
VINCULOS = {
    'noaa_crw_dhw_abrolhos': (
        'noaa_crw',
        'sst,sst_anomalia,hotspot,dhw,baa,baa_area_alerta',
    ),
    'cmems_salinidade_abrolhos': ('copernicus', 'salinidade'),
    'cmems_oxigenio_abrolhos': ('copernicus', 'oxigenio'),
    'cmems_kd490_abrolhos': ('', ''),
    'cmems_ph_abrolhos': ('', ''),
    'cmems_clorofila_abrolhos': ('', ''),
    'cmems_nitrato_abrolhos': ('', ''),
    'cmems_thetao_abrolhos': ('', ''),
    'metoffice_sst_l4_abrolhos': ('', ''),
}


def vincular(apps, schema_editor):
    DatasetCatalogo = apps.get_model('aquaculture', 'DatasetCatalogo')

    for identificador, (fonte, variaveis) in VINCULOS.items():
        DatasetCatalogo.objects.filter(pk=identificador).update(
            fonte_medicao=fonte, variaveis_medicao=variaveis
        )


def desvincular(apps, schema_editor):
    DatasetCatalogo = apps.get_model('aquaculture', 'DatasetCatalogo')
    DatasetCatalogo.objects.update(fonte_medicao='', variaveis_medicao='')


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0019_datasetcatalogo_fonte_medicao_and_more'),
    ]

    operations = [
        migrations.RunPython(vincular, desvincular),
    ]
