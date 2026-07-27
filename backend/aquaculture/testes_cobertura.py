"""Testes da cobertura real do catalogo.

O que protegem, em ordem de gravidade:

1. 🚨 **Dataset sem medicao no banco nao pode parecer disponivel.** Era o
   defeito: seis dos nove anunciavam periodo e formato sem uma unica linha
   gravada.
2. **A cobertura e derivada, e nunca lida dos campos gravados.** Se voltar a
   sair do `data_fim` guardado, envelhece de novo — e em silencio.
3. **O numero anunciado tem recibo.** `consulta` precisa devolver exatamente o
   que `n_medicoes` afirma; senao e afirmacao sem prova.
4. **Uma consulta so para a lista inteira.** Nove agregacoes separadas
   passariam despercebidas ate a pagina ficar lenta.
"""

from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from aquaculture import cobertura
from aquaculture.models import DatasetCatalogo, LocalRecife, MedicaoAmbiental


class BaseCatalogo(TestCase):
    def setUp(self):
        MedicaoAmbiental.objects.all().delete()
        DatasetCatalogo.objects.all().delete()
        LocalRecife.objects.all().delete()

        self.local = LocalRecife.objects.create(
            slug='teste-abrolhos', nome='Abrolhos', estado='BA',
            cidade='Caravelas', latitude=-17.9, longitude=-38.6,
        )

        for dia, variavel in (
            (date(2026, 7, 20), 'sst'),
            (date(2026, 7, 21), 'sst'),
            (date(2026, 7, 21), 'dhw'),
        ):
            MedicaoAmbiental.objects.create(
                local_recife=self.local, data=dia, variavel=variavel,
                valor=25.0, unidade='°C', fonte='noaa_crw',
                dataset_id='dhw_5km',
            )

        self.espelhado = DatasetCatalogo.objects.create(
            id='teste-crw', titulo='CRW', fonte='NOAA', tipo_dado='Oceanografico',
            local_slug='teste-abrolhos',
            data_inicio=date(1985, 1, 1), data_fim=date(2025, 11, 30),
            fonte_medicao='noaa_crw', variaveis_medicao='sst,dhw',
        )
        self.externo = DatasetCatalogo.objects.create(
            id='teste-kd490', titulo='KD490', fonte='Copernicus',
            tipo_dado='Oceanografico', local_slug='teste-abrolhos',
            data_inicio=date(2023, 11, 15), data_fim=date(2025, 12, 11),
        )


class CalculoTests(BaseCatalogo):
    def cobertura_de(self, dataset):
        return cobertura.calcular([self.espelhado, self.externo])[dataset.id]

    def test_dataset_espelhado_reporta_o_que_existe(self):
        c = self.cobertura_de(self.espelhado)

        self.assertTrue(c['espelhado'])
        self.assertEqual(c['n_medicoes'], 3)
        self.assertEqual(c['variaveis'], ['dhw', 'sst'])

    def test_as_datas_vem_do_banco_e_nao_do_campo_gravado(self):
        """🚨 O defeito inteiro morava nesta diferenca.

        O catalogo declara 1985–2025; o banco tem 20–21/07/2026. Se a
        cobertura repetisse o campo gravado, nada disto apareceria.
        """
        c = self.cobertura_de(self.espelhado)

        self.assertEqual(c['data_inicio'], date(2026, 7, 20))
        self.assertEqual(c['data_fim'], date(2026, 7, 21))
        self.assertNotEqual(c['data_fim'], self.espelhado.data_fim)

    def test_dataset_externo_e_marcado_como_nao_espelhado(self):
        """🚨 Seis dos nove estavam assim, e nada dizia."""
        c = self.cobertura_de(self.externo)

        self.assertFalse(c['espelhado'])
        self.assertEqual(c['n_medicoes'], 0)
        self.assertIsNone(c['data_inicio'])

    def test_o_externo_explica_por_que_nao_tem_dado(self):
        self.assertIn('nao o espelha', self.cobertura_de(self.externo)['motivo'])

    def test_espelhado_sem_medicao_e_estado_diferente_de_externo(self):
        """Declarado e vazio e defeito; nao declarado e escolha."""
        orfao = DatasetCatalogo.objects.create(
            id='teste-orfao', titulo='Orfao', fonte='X', tipo_dado='Y',
            fonte_medicao='copernicus', variaveis_medicao='clorofila',
        )

        c = cobertura.calcular([orfao])['teste-orfao']

        self.assertTrue(c['espelhado'])
        self.assertEqual(c['n_medicoes'], 0)
        self.assertIn('Rode a ingestao', c['motivo'])

    def test_variaveis_vazias_pegam_todas_da_fonte(self):
        todas = DatasetCatalogo.objects.create(
            id='teste-todas', titulo='Tudo', fonte='NOAA', tipo_dado='Y',
            local_slug='teste-abrolhos', fonte_medicao='noaa_crw',
        )

        c = cobertura.calcular([todas])['teste-todas']

        self.assertEqual(c['variaveis'], ['dhw', 'sst'])

    def test_variavel_declarada_que_nao_existe_nao_entra(self):
        self.espelhado.variaveis_medicao = 'sst,clorofila'
        self.espelhado.save()

        c = cobertura.calcular([self.espelhado])['teste-crw']

        self.assertEqual(c['variaveis'], ['sst'])
        self.assertEqual(c['n_medicoes'], 2)

    def test_filtra_pelo_local_do_dataset(self):
        outro = LocalRecife.objects.create(
            slug='teste-picao', nome='Picao', estado='PB', cidade='JP',
            latitude=-7.1, longitude=-34.8,
        )
        MedicaoAmbiental.objects.create(
            local_recife=outro, data=date(2026, 7, 21), variavel='sst',
            valor=28.0, unidade='°C', fonte='noaa_crw', dataset_id='dhw_5km',
        )

        c = cobertura.calcular([self.espelhado])['teste-crw']

        self.assertEqual(c['locais'], ['teste-abrolhos'])
        self.assertEqual(c['n_medicoes'], 3)

    def test_lista_vazia_nao_consulta_o_banco(self):
        with self.assertNumQueries(0):
            self.assertEqual(cobertura.calcular([]), {})

    def test_uma_consulta_serve_a_lista_inteira(self):
        """🚨 Uma agregacao por item passaria despercebida ate ficar lento."""
        datasets = list(DatasetCatalogo.objects.all())

        with self.assertNumQueries(1):
            cobertura.calcular(datasets)


class RespostaDaApiTests(BaseCatalogo):
    def buscar(self):
        with override_settings(OFFLINE_MODE=False):
            return self.client.get(reverse('dataset_catalogo_list')).json()

    def item(self, identificador):
        return next(x for x in self.buscar() if x['id'] == identificador)

    def test_a_cobertura_vem_no_payload(self):
        self.assertIn('cobertura', self.item('teste-crw'))

    def test_a_lista_continua_sendo_array_cru(self):
        """Contrato existente: o frontend consome como array."""
        self.assertIsInstance(self.buscar(), list)

    def test_o_periodo_gravado_continua_no_payload(self):
        """As duas datas respondem perguntas diferentes, e as duas ficam.

        A gravada descreve o **arquivo CSV** inventariado em `backend/dados/`;
        a derivada, o que a API tem. O erro nunca foi o numero gravado — foi
        apresenta-lo como se fosse a cobertura do projeto.
        """
        item = self.item('teste-crw')

        self.assertEqual(item['data_fim'], '2025-11-30')
        self.assertEqual(item['cobertura']['data_fim'], '2026-07-21')

    def test_dataset_externo_chega_marcado_a_tela(self):
        self.assertFalse(self.item('teste-kd490')['cobertura']['espelhado'])

    def test_a_consulta_devolve_exatamente_o_que_foi_anunciado(self):
        """🚨 O recibo do numero. Sem ele, "3 medicoes" e so uma afirmacao."""
        with override_settings(OFFLINE_MODE=False):
            item = self.item('teste-crw')
            resposta = self.client.get(item['cobertura']['consulta'])

        self.assertEqual(resposta.json()['count'], item['cobertura']['n_medicoes'])

    def test_dataset_externo_nao_oferece_consulta(self):
        self.assertIsNone(self.item('teste-kd490')['cobertura']['consulta'])

    def test_a_lista_nao_faz_uma_consulta_por_item(self):
        DatasetCatalogo.objects.create(
            id='teste-extra', titulo='Extra', fonte='X', tipo_dado='Y',
            fonte_medicao='noaa_crw',
        )

        with override_settings(OFFLINE_MODE=False):
            with self.assertNumQueries(2):  # os datasets + a agregacao
                self.client.get(reverse('dataset_catalogo_list'))

    def test_serializar_sem_contexto_ainda_mede(self):
        """Campo ausente seria lido como "sem cobertura", que e outra coisa."""
        from aquaculture.serializers import DatasetCatalogoSerializer

        dados = DatasetCatalogoSerializer(self.espelhado).data

        self.assertEqual(dados['cobertura']['n_medicoes'], 3)


class DatasetsDoLocalTests(BaseCatalogo):
    def test_o_endpoint_do_local_tambem_traz_cobertura(self):
        with override_settings(OFFLINE_MODE=False):
            resposta = self.client.get(
                reverse('local_recife_datasets_list', args=['teste-abrolhos'])
            )

        itens = {x['id']: x for x in resposta.json()}
        self.assertTrue(itens['teste-crw']['cobertura']['espelhado'])
        self.assertFalse(itens['teste-kd490']['cobertura']['espelhado'])


class VinculoRealTests(TestCase):
    """A migracao 0020 vinculou os nove registros de producao.

    Este teste roda contra o que as migracoes semeiam, e nao contra fixture:
    o que se quer travar e que **o catalogo real** diga a verdade.
    """

    def test_os_datasets_semeados_declaram_o_vinculo(self):
        reais = DatasetCatalogo.objects.exclude(fonte_medicao='')

        if not reais.exists():
            self.skipTest('O catalogo de producao nao foi semeado neste banco.')

        for dataset in reais:
            self.assertIn(dataset.fonte_medicao, ('noaa_crw', 'copernicus'))

    def test_nenhum_dataset_externo_finge_ter_dado(self):
        for dataset in DatasetCatalogo.objects.filter(fonte_medicao=''):
            c = cobertura.calcular([dataset])[dataset.id]
            self.assertFalse(c['espelhado'])
            self.assertEqual(c['n_medicoes'], 0)
