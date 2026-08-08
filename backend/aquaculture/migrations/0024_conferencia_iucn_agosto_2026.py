"""Preenche a procedencia de conservacao das 9 especies, direto da ficha da IUCN.

A migracao 0022 abriu os campos e deixou todas as 9 sem ano — de proposito,
porque nenhuma tinha um ano registrado (ver o cabecalho de 0022). Esta aqui e
o preenchimento que ficou pendente desde entao (§2.4.1 do FONTES.md).

🚨 **O pedido de acesso a API da IUCN foi recusado duas vezes** — e-mail
institucional em 31/07/2026, e-mail pessoal em 04/08/2026, mesmo texto-modelo
as duas vezes. Isso nao bloqueia esta migracao: `iucn_origem='ficha'` existe
exatamente para o caminho sem token — abrir a pagina publica de cada especie
em iucnredlist.org e conferir a mao. Conferido em 04/08/2026 (05/08/2026 no
relogio do proprio site, que fica a frente do horario local).

**Convencao adotada para `iucn_avaliado_em`**: o ANO PUBLICADO ("YEAR
PUBLISHED" na ficha, e o ano que aparece na citacao formal — ex: "The IUCN Red
List of Threatened Species 2022"), nao a data em que o assessment foi
assinado ("DATE ASSESSED", que costuma ser um ano antes). E o mesmo ano que
0022 already usa no exemplo do Dendrogyra cylindrus (VU ate 2022, CR desde
2022) e o que aparece na citacao que qualquer leitor vai copiar.

Tres das nove **nao tem avaliacao nenhuma na IUCN** — nao e lacuna de
conferencia, e resultado de conferencia: a busca em iucnredlist.org devolveu
zero resultados para as tres, em 04/08/2026. Isso e diferente do caso que 0022
recusou resolver (ambiguidade entre "NE real" e "ninguem consultou") — aqui
foi consultado e a resposta e negativa, entao `iucn_categoria='NE'` e honesto.
Ficam sem `iucn_avaliado_em` (nao ha ano de avaliacao que nao existe) e sem
`fonte_iucn_url` (nao ha ficha para linkar); a evidencia e a propria busca,
registrada aqui e nao no banco.

Duas descobertas que corrigem o que estava especulado:

1. `Mussismilia braziliensis` **era CR** desde 2022-2, confirmando o que 0022
   ja tinha achado via Wikidata (§2.4.2 do FONTES.md) — agora com a fonte
   primaria, nao o terceiro.
2. `Sparisoma axillare` **e DD**, nao NT — resolve o "❓ a confirmar" que
   ficou aberto em §2.4.2. A avaliacao e de 2009/publicada em 2012 e esta
   marcada "Needs updating" pela propria IUCN.

`Holacanthus ciliaris` (LC, 2010) e `Ocyurus chrysurus` (DD, 2016) tambem
estao marcadas "Needs updating" na ficha — nao muda o que se grava agora, mas
e o tipo de sinal que `iucn_conferencia_vencida` (2 anos) vai pegar sozinho
dai pra frente.

**Reversivel:** volta as 9 especies ao estado exato de antes de 0022 rodar —
todos os campos de conservacao vazios.
"""

from datetime import date

from django.db import migrations

CONSULTADO_EM = date(2026, 8, 4)

# YEAR PUBLISHED da ficha, nao DATE ASSESSED — ver cabecalho.
DADOS = {
    'Mussismilia braziliensis': dict(
        iucn_categoria='CR', iucn_taxon_id=133586, iucn_avaliado_em=2022,
        iucn_versao='2022',
        fonte_iucn_url='https://www.iucnredlist.org/species/133586/165962303',
    ),
    'Montastraea cavernosa': dict(
        iucn_categoria='LC', iucn_taxon_id=133237, iucn_avaliado_em=2022,
        iucn_versao='2022',
        fonte_iucn_url='https://www.iucnredlist.org/species/133237/165787295',
    ),
    'Holacanthus ciliaris': dict(
        iucn_categoria='LC', iucn_taxon_id=165883, iucn_avaliado_em=2010,
        iucn_versao='2010',
        fonte_iucn_url='https://www.iucnredlist.org/species/165883/6156566',
    ),
    'Muricea flamma': dict(iucn_categoria='NE'),
    'Dendrogyra cylindrus': dict(
        iucn_categoria='CR', iucn_taxon_id=133124, iucn_avaliado_em=2022,
        iucn_versao='2022-2',
        fonte_iucn_url='https://www.iucnredlist.org/species/133124/129721366',
    ),
    'Phyllogorgia dilatata': dict(iucn_categoria='NE'),
    'Condylactis gigantea': dict(iucn_categoria='NE'),
    'Sparisoma axillare': dict(
        iucn_categoria='DD', iucn_taxon_id=190751, iucn_avaliado_em=2012,
        iucn_versao='2012',
        fonte_iucn_url='https://www.iucnredlist.org/species/190751/17785979',
    ),
    'Ocyurus chrysurus': dict(
        iucn_categoria='DD', iucn_taxon_id=194341, iucn_avaliado_em=2016,
        iucn_versao='2016-1',
        fonte_iucn_url='https://www.iucnredlist.org/species/194341/2316114',
    ),
}


def preencher(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')
    for nome, campos in DADOS.items():
        try:
            especie = Especie.objects.get(nome_cientifico=nome)
        except Especie.DoesNotExist:
            continue
        especie.iucn_origem = 'ficha'
        especie.iucn_consultado_em = CONSULTADO_EM
        for campo, valor in campos.items():
            setattr(especie, campo, valor)
        especie.save()


def limpar(apps, schema_editor):
    Especie = apps.get_model('aquaculture', 'Especie')
    Especie.objects.filter(nome_cientifico__in=DADOS.keys()).update(
        iucn_origem='', iucn_categoria='', iucn_taxon_id=None,
        iucn_avaliado_em=None, iucn_versao='', iucn_consultado_em=None,
        fonte_iucn_url='',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('aquaculture', '0023_contas_e_moderacao_de_especies'),
    ]

    operations = [
        migrations.RunPython(preencher, limpar),
    ]
