"""Corrige a procedencia das fotos das 9 especies, e para de exibir a que nao tem licenca.

🚨 **As 9 especies tinham o mesmo `credito_imagem` — "Acervo local do
projeto" — e nenhuma tinha `fonte_imagem_url` preenchido.** Isso nao e
verdade para nenhuma delas: sao fotos de terceiros, nao producao propria do
projeto. docs/FONTES.md secao 2.1 ja tinha achado esse defeito em **duas**
(comparando o credito com a URL documentada na tabela do proprio
documento) e registrado como risco de violacao de direito autoral, mas
nunca tinha conferido as outras sete.

**Conferido agora, direto na API publica do iNaturalist** (`api.inaturalist.
org/v1/observations/<id>`, que responde sem autenticacao ao contrario da
pagina HTML) para as quatro que tinham URL de observacao documentada:

| Especie | Observador | Licenca | Local da observacao |
|---|---|---|---|
| Mussismilia braziliensis | Kai Lima (@kailimma_nascimento) | CC BY-NC | Caravelas, BA |
| Montastraea cavernosa | Kai Lima (@kailimma_nascimento) | CC BY-NC | Caravelas, BA |
| Muricea flamma | Joao D'Andretta (@jpdandretta) | CC BY | Arquipelago de Abrolhos, BA |
| Dendrogyra cylindrus | Laura Proenca (@lproenca) | **nenhuma** (`license_code` nulo) | Bahia, BR |

🚨 **`Dendrogyra cylindrus` nao tem licenca concedida — "todos os direitos
reservados" e o padrao do iNaturalist quando `license_code` vem nulo.** O
projeto vinha hospedando uma copia do arquivo (`especies/
Dendrogyra_cylindrus.jpeg`) sem nenhuma permissao de reuso. Esta migracao
**limpa o campo `foto`** dela — para de servir o arquivo — mantendo so o
credito e o link da observacao, que e uso legitimo (linkar para a fonte
nunca e violacao; reidistribuir a copia, sem licenca, e).  O arquivo
continua no disco (`backend/media/especies/`), nao apagado, para nao
destruir a unica copia enquanto ninguem decide se vale pedir permissao ao
fotografo.

**As outras cinco (Holacanthus ciliaris, Sparisoma axillare, Ocyurus
chrysurus, Phyllogorgia dilatata, Condylactis gigantea) nao tem URL de
observacao documentada em lugar nenhum do projeto.** Mesmo principio: nao
ha como confirmar licenca de uma foto sem fonte, entao esta migracao tambem
limpa `foto` e `credito_imagem` delas — em vez de continuar afirmando um
credito ja sabido falso. Ficam com o mesmo vazio que `iucn_categoria` ja usa
para "sem procedencia registrada" (migracao 0022), e a modal do site ja
sabe mostrar isso sem inventar texto.

**Reversivel:** volta as 9 especies ao estado exato de antes desta
migracao — mesmo `foto`, mesmo credito generico, nenhuma tinha
`fonte_imagem_url` nem `local_captura_foto`.
"""

from django.db import migrations, models

# (foto original, credito original) — capturado do banco antes desta
# migracao, para o reverso conseguir devolver o estado exato.
FOTO_ORIGINAL = {
    'Condylactis gigantea': 'especies/Condylactis_gigantea.jpg',
    'Dendrogyra cylindrus': 'especies/Dendrogyra_cylindrus.jpeg',
    'Holacanthus ciliaris': 'especies/Holacanthus_ciliaris.jpeg',
    'Montastraea cavernosa': 'especies/Montastraea_cavernosa.jpg',
    'Muricea flamma': 'especies/Muricea_flamma.jpg',
    'Mussismilia braziliensis': 'especies/Mussismilia_braziliensis.jpg',
    'Ocyurus chrysurus': 'especies/Ocyurus_chrysurus.jpeg',
    'Phyllogorgia dilatata': 'especies/Phyllogorgia_dilatata.jpg',
    'Sparisoma axillare': 'especies/Sparisoma_axillare.jpg',
}
CREDITO_ORIGINAL = 'Acervo local do projeto'

# As quatro com fonte iNaturalist conferida pela API publica em 11/08/2026.
# `foto` fica None nas quatro: nenhuma tem copia local que valha manter
# servindo agora que a licenca de cada uma foi conferida de verdade —
# Dendrogyra por nao ter licenca nenhuma, as outras tres porque o campo
# `fonte_imagem_url` (link para a foto na fonte) passa a ser o caminho
# correto de exibir uma foto de terceiro, e nao uma copia redistribuida.
VERIFICADAS = {
    'Mussismilia braziliensis': dict(
        credito_imagem='Kai Lima (iNaturalist, CC BY-NC)',
        fonte_imagem_url='https://www.inaturalist.org/observations/326387144',
        local_captura_foto='Caravelas, BA',
    ),
    'Montastraea cavernosa': dict(
        credito_imagem='Kai Lima (iNaturalist, CC BY-NC)',
        fonte_imagem_url='https://www.inaturalist.org/observations/326387704',
        local_captura_foto='Caravelas, BA',
    ),
    'Muricea flamma': dict(
        credito_imagem="Joao D'Andretta (iNaturalist, CC BY)",
        fonte_imagem_url='https://www.inaturalist.org/observations/137432286',
        local_captura_foto='Arquipelago de Abrolhos, BA',
    ),
    'Dendrogyra cylindrus': dict(
        credito_imagem='Laura Proenca (iNaturalist, todos os direitos reservados)',
        fonte_imagem_url='https://www.inaturalist.org/observations/276213882',
        local_captura_foto='Bahia, BR',
    ),
}

# As cinco sem fonte documentada em lugar nenhum do projeto.
SEM_FONTE = (
    'Holacanthus ciliaris',
    'Sparisoma axillare',
    'Ocyurus chrysurus',
    'Phyllogorgia dilatata',
    'Condylactis gigantea',
)


def corrigir(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')

    for nome, campos in VERIFICADAS.items():
        Especie.objects.filter(nome_cientifico=nome).update(foto=None, **campos)

    Especie.objects.filter(nome_cientifico__in=SEM_FONTE).update(
        foto=None, credito_imagem='', fonte_imagem_url='', local_captura_foto='',
    )


def reverter(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')

    for nome, foto in FOTO_ORIGINAL.items():
        Especie.objects.filter(nome_cientifico=nome).update(
            foto=foto, credito_imagem=CREDITO_ORIGINAL, fonte_imagem_url='',
            local_captura_foto='',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0025_seed_novos_locais_recife'),
    ]

    operations = [
        migrations.AddField(
            model_name='especie',
            name='local_captura_foto',
            field=models.CharField(
                blank=True,
                help_text='Onde a foto foi tirada, nao onde a especie ocorre.',
                max_length=200,
                verbose_name='Local de captura da foto',
            ),
        ),
        migrations.AlterField(
            model_name='especie',
            name='credito_imagem',
            field=models.CharField(
                blank=True,
                help_text='Site, instituicao ou nome de quem tirou/cedeu a foto.',
                max_length=200,
                verbose_name='Credito da imagem',
            ),
        ),
        migrations.RunPython(corrigir, reverter),
    ]
