"""Testes da metade do catalogo que descreve a serie, e nao o arquivo.

O que protegem, em ordem de gravidade:

1. 🚨 **Um recife com serie ingerida nao pode aparecer sem dataset nenhum.** Era
   o defeito: os sete locais que entraram em 11/08/2026 tinham 19.278 medicoes
   cada um, previsao no painel, e a pagina de cada um dizia "Ainda nao ha
   datasets relacionados". O catalogo inteiro descrevia arquivos de
   `backend/dados/`, todos extraidos num ponto so.
2. 🚨 **E o inverso tambem:** um par (fonte, local) sem medicao **nao** pode
   virar registro. E o mesmo defeito de 27/07/2026 numa roupa nova — catalogo
   anunciando o que o banco nao tem.
3. **O download precisa apontar para este projeto, e dizer que exige conta.**
   Um botao "Baixar conjunto" que devolve 401 em JSON e pior que nenhum botao.
4. **Um recife sem coordenada explica a propria ausencia.** Sem isso, decisao
   registrada e pipeline quebrado ficam com a mesma cara na tela.
"""

from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from aquaculture.inventario_datasets import construir_inventario_das_series
from aquaculture.models import DatasetCatalogo, LocalRecife, MedicaoAmbiental


class BaseSeries(TestCase):
    def setUp(self):
        MedicaoAmbiental.objects.all().delete()
        DatasetCatalogo.objects.all().delete()
        LocalRecife.objects.all().delete()

        self.com_serie = LocalRecife.objects.create(
            slug='noronha-teste', nome='Fernando de Noronha',
            estado='Pernambuco', cidade='Fernando de Noronha',
            latitude=-3.8522, longitude=-32.4208,
        )
        # Cadastrado, com coordenada, e sem uma medicao sequer: o caso de um
        # recife novo antes da primeira ingestao.
        self.sem_ingestao = LocalRecife.objects.create(
            slug='recem-cadastrado', nome='Recife Novo', estado='BA',
            cidade='Ilheus', latitude=-14.8, longitude=-39.0,
        )
        # Sem coordenada de proposito, como a APA Costa dos Corais.
        self.sem_coordenadas = LocalRecife.objects.create(
            slug='area-teste', nome='Area de Protecao',
            estado='Alagoas/Pernambuco', cidade='Diversos',
            fonte_coordenadas='Sem coordenada: e uma area, nao um ponto.',
        )

        for variavel, fonte in (
            ('sst', 'noaa_crw'),
            ('dhw', 'noaa_crw'),
            ('salinidade', 'copernicus'),
        ):
            MedicaoAmbiental.objects.create(
                local_recife=self.com_serie, data=date(2026, 7, 21),
                variavel=variavel, valor=25.0, unidade='°C', fonte=fonte,
            )

    def registros_por_id(self):
        return {r['id']: r['defaults'] for r in construir_inventario_das_series()}


class InventarioDasSeriesTests(BaseSeries):
    def test_cada_par_fonte_local_com_medicao_vira_um_dataset(self):
        registros = self.registros_por_id()

        self.assertEqual(
            sorted(registros),
            ['serie-copernicus-noronha-teste', 'serie-noaa_crw-noronha-teste'],
        )

    def test_local_sem_medicao_nao_vira_registro_nem_desativado(self):
        """🚨 O ponto todo: ausencia no banco e ausencia no catalogo.

        Criar o registro com `ativo=False` seria "quase certo" e errado do
        mesmo jeito — a pagina passaria a listar um dataset que nunca existiu
        para aquele recife, e a lista de datasets voltaria a ser uma promessa
        em vez de um inventario.
        """
        ids = self.registros_por_id()

        for slug in ('recem-cadastrado', 'area-teste'):
            self.assertNotIn(f'serie-noaa_crw-{slug}', ids)
            self.assertNotIn(f'serie-copernicus-{slug}', ids)

    def test_o_download_aponta_para_a_api_deste_projeto(self):
        defaults = self.registros_por_id()['serie-noaa_crw-noronha-teste']

        self.assertEqual(
            defaults['url_download'],
            '/api/medicoes/?local=noronha-teste&fonte=noaa_crw&formato=csv',
        )
        self.assertTrue(defaults['download_exige_conta'])

    def test_o_periodo_nao_e_gravado_no_registro(self):
        """A cobertura sai derivada do banco, e nunca de uma copia guardada.

        Gravar `data_inicio`/`data_fim` aqui reintroduziria exatamente a copia
        que envelheceu em silencio em 27/07/2026 — e desta vez em 16 registros
        em vez de 9.
        """
        defaults = self.registros_por_id()['serie-noaa_crw-noronha-teste']

        self.assertIsNone(defaults['data_inicio'])
        self.assertIsNone(defaults['data_fim'])
        self.assertIsNone(defaults['tamanho_mb'])

    def test_a_fonte_e_declarada_para_a_cobertura_poder_medir(self):
        defaults = self.registros_por_id()['serie-copernicus-noronha-teste']

        self.assertEqual(defaults['fonte_medicao'], 'copernicus')
        # Vazio = todas as variaveis daquela fonte. Repetir a lista aqui criaria
        # uma segunda declaracao para divergir da que o conector ja faz.
        self.assertEqual(defaults['variaveis_medicao'], '')

    def test_o_local_do_registro_e_o_recife_e_nao_abrolhos(self):
        """O `LOCAL_PADRAO` da outra metade nao pode vazar para esta.

        Era o defeito de origem: todo registro do catalogo saia com
        `local_slug='abrolhos-ba'`, porque todo arquivo do acervo tinha sido
        extraido ali.
        """
        defaults = self.registros_por_id()['serie-noaa_crw-noronha-teste']

        self.assertEqual(defaults['local_slug'], 'noronha-teste')
        self.assertEqual(defaults['localizacao'], 'Fernando de Noronha')
        self.assertEqual(defaults['estado'], 'Pernambuco')


@override_settings(OFFLINE_MODE=False)
class DatasetsRelacionadosNaApiTests(BaseSeries):
    def test_o_recife_com_serie_recebe_os_datasets_dele(self):
        for registro in construir_inventario_das_series():
            DatasetCatalogo.objects.create(id=registro['id'], **registro['defaults'])

        resposta = self.client.get(
            reverse('local_recife_datasets_list', args=['noronha-teste'])
        )

        self.assertEqual(resposta.status_code, 200)
        ids = sorted(item['id'] for item in resposta.json())
        self.assertEqual(
            ids, ['serie-copernicus-noronha-teste', 'serie-noaa_crw-noronha-teste']
        )

    def test_a_cobertura_do_dataset_da_serie_vem_medida_do_banco(self):
        for registro in construir_inventario_das_series():
            DatasetCatalogo.objects.create(id=registro['id'], **registro['defaults'])

        resposta = self.client.get(
            reverse('local_recife_datasets_list', args=['noronha-teste'])
        )
        por_id = {item['id']: item for item in resposta.json()}
        crw = por_id['serie-noaa_crw-noronha-teste']['cobertura']

        self.assertTrue(crw['espelhado'])
        self.assertEqual(crw['n_medicoes'], 2)
        self.assertEqual(crw['variaveis'], ['dhw', 'sst'])
        self.assertEqual(crw['data_inicio'], '2026-07-21')


@override_settings(OFFLINE_MODE=False)
class MotivoSemSerieTests(BaseSeries):
    def test_recife_com_coordenada_nao_tem_motivo(self):
        self.assertIsNone(self.com_serie.motivo_sem_serie)

    def test_recife_sem_coordenada_explica_a_ausencia(self):
        motivo = self.sem_coordenadas.motivo_sem_serie

        self.assertEqual(motivo['codigo'], 'sem_coordenadas')
        # O detalhe e o que separa "decidimos nao inventar a coordenada" de
        # "esquecemos de preencher". Sem ele o resumo generico sozinho nao
        # distingue os dois.
        self.assertIn('nao um ponto', motivo['detalhe'])

    def test_o_motivo_viaja_na_api(self):
        resposta = self.client.get(reverse('local_recife_list'))
        por_slug = {item['slug']: item for item in resposta.json()}

        self.assertIsNone(por_slug['noronha-teste']['motivo_sem_serie'])
        self.assertTrue(por_slug['noronha-teste']['tem_coordenadas'])

        sem = por_slug['area-teste']
        self.assertFalse(sem['tem_coordenadas'])
        self.assertEqual(sem['motivo_sem_serie']['codigo'], 'sem_coordenadas')

    def test_recife_novo_com_coordenada_nao_recebe_o_motivo(self):
        """⚠️ A distincao que o campo existe para preservar.

        `recem-cadastrado` tem coordenada e nao tem medicao: a serie **vai**
        existir na proxima ingestao. Devolver o mesmo aviso dos dois locais sem
        coordenada apagaria a diferenca entre "ainda nao rodou" e "nunca vai
        rodar" — que e justamente a diferenca que o visitante precisa ler.
        """
        self.assertIsNone(self.sem_ingestao.motivo_sem_serie)
