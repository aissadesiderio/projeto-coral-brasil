"""Testes do endpoint da serie ambiental.

O que protegem, em ordem de gravidade:

1. **A paginacao existe e tem teto.** Sao 57.420 linhas crescendo 24/dia; sem
   paginacao a resposta seria a serie inteira, e sem teto o cliente desfaria a
   paginacao com `?page_size=999999`.
2. **A proveniencia vai no payload.** Servir o numero sem dizer de onde veio
   entregaria exatamente o que este projeto existe para nao fazer.
3. **Valor nulo sai como nulo, nunca como zero.** O pipeline legado gravava pH 0
   e salinidade 0 — fisicamente impossiveis — ao preencher lacuna.
4. **Data invalida falha alto.** Sem isso, `?de=ontem` seria ignorado e o
   cliente receberia tudo achando que recebeu o recorte que pediu.
"""

from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from aquaculture.models import LocalRecife, MedicaoAmbiental


@override_settings(OFFLINE_MODE=False)
class MedicaoAmbientalApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        MedicaoAmbiental.objects.all().delete()
        LocalRecife.objects.all().delete()

        cls.abrolhos = LocalRecife.objects.create(
            slug='teste-abrolhos', nome='Abrolhos', estado='BA',
            cidade='Caravelas', latitude=-17.9, longitude=-38.6,
        )
        cls.picao = LocalRecife.objects.create(
            slug='teste-picao', nome='Picaozinho', estado='PB',
            cidade='Joao Pessoa', latitude=-7.1, longitude=-34.8,
        )

        MedicaoAmbiental.objects.create(
            local_recife=cls.abrolhos, data=date(2026, 7, 24), variavel='sst',
            valor=25.0, unidade='°C', fonte='noaa_crw', dataset_id='dhw_5km',
        )
        MedicaoAmbiental.objects.create(
            local_recife=cls.abrolhos, data=date(2026, 7, 24), variavel='dhw',
            valor=0.0, unidade='°C·semana', fonte='noaa_crw',
            dataset_id='dhw_5km',
        )
        MedicaoAmbiental.objects.create(
            local_recife=cls.abrolhos, data=date(2026, 7, 20),
            variavel='salinidade', valor=37.4, unidade='PSU',
            fonte='copernicus', dataset_id='cmems_phy_my',
        )
        MedicaoAmbiental.objects.create(
            local_recife=cls.picao, data=date(2026, 7, 24), variavel='sst',
            valor=28.0, unidade='°C', fonte='noaa_crw', dataset_id='dhw_5km',
        )
        # A que foi reprovada na validacao fisica.
        cls.reprovada = MedicaoAmbiental.objects.create(
            local_recife=cls.picao, data=date(2026, 7, 23), variavel='ph',
            valor=None, unidade='', fonte='copernicus',
            dataset_id='cmems_bgc_car', quality_flag='invalido',
            observacao='pH 2,5 fora da faixa fisica do oceano',
        )

    def buscar(self, consulta=''):
        return self.client.get(reverse('medicao_list') + consulta)

    # --- paginacao ----------------------------------------------------------

    def test_a_resposta_vem_paginada(self):
        corpo = self.buscar().json()

        for campo in ('count', 'total_paginas', 'page_size', 'results'):
            self.assertIn(campo, corpo)
        self.assertEqual(corpo['count'], 5)

    def test_page_size_e_respeitado(self):
        corpo = self.buscar('?page_size=2').json()

        self.assertEqual(len(corpo['results']), 2)
        self.assertEqual(corpo['count'], 5)
        self.assertEqual(corpo['total_paginas'], 3)
        self.assertIsNotNone(corpo['next'])

    @override_settings(DRF_MAX_PAGE_SIZE=3)
    def test_o_teto_impede_o_cliente_de_desfazer_a_paginacao(self):
        """🚨 Sem teto, `?page_size=999999` devolve a serie inteira."""
        corpo = self.buscar('?page_size=999999').json()

        self.assertEqual(corpo['page_size'], 3)
        self.assertEqual(len(corpo['results']), 3)

    def test_paginar_nao_repete_nem_pula_linha(self):
        """Ordem nao determinista faz linhas trocarem de pagina entre requisicoes."""
        primeira = self.buscar('?page_size=2').json()['results']
        segunda = self.buscar('?page_size=2&page=2').json()['results']
        terceira = self.buscar('?page_size=2&page=3').json()['results']

        ids = [x['id'] for x in primeira + segunda + terceira]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 5)

    # --- proveniencia -------------------------------------------------------

    def test_a_proveniencia_vem_no_payload(self):
        """Nao e opcional nem fica atras de parametro."""
        item = self.buscar('?local=teste-abrolhos&variavel=sst').json()['results'][0]

        self.assertEqual(item['fonte'], 'noaa_crw')
        self.assertEqual(item['dataset_id'], 'dhw_5km')
        self.assertEqual(item['quality_flag'], 'ok')
        self.assertIn('observacao', item)

    def test_o_local_sai_como_slug(self):
        item = self.buscar('?local=teste-picao&variavel=sst').json()['results'][0]

        self.assertEqual(item['local'], 'teste-picao')

    # --- nulo -------------------------------------------------------------

    def test_valor_reprovado_sai_nulo_e_nao_zero(self):
        """🚨 O defeito do pipeline legado: `.fillna(0)` gravava pH 0."""
        corpo = self.buscar('?qualidade=invalido').json()

        self.assertEqual(corpo['count'], 1)
        item = corpo['results'][0]
        self.assertIsNone(item['valor'])
        self.assertNotEqual(item['valor'], 0)

    def test_o_motivo_da_reprovacao_acompanha_o_nulo(self):
        """Nulo sem motivo e lacuna muda; com motivo, e informacao."""
        item = self.buscar('?qualidade=invalido').json()['results'][0]

        self.assertIn('fora da faixa', item['observacao'])

    def test_zero_legitimo_continua_zero(self):
        """DHW 0 quer dizer "sem estresse", e nao "sem dado"."""
        item = self.buscar('?variavel=dhw').json()['results'][0]

        self.assertEqual(item['valor'], 0.0)
        self.assertIsNotNone(item['valor'])

    # --- filtros ------------------------------------------------------------

    def test_filtra_por_local(self):
        self.assertEqual(self.buscar('?local=teste-picao').json()['count'], 2)

    def test_filtra_por_variavel(self):
        self.assertEqual(self.buscar('?variavel=sst').json()['count'], 2)

    def test_variavel_pode_repetir(self):
        corpo = self.buscar('?variavel=sst&variavel=dhw').json()

        self.assertEqual(corpo['count'], 3)

    def test_filtra_por_fonte(self):
        self.assertEqual(self.buscar('?fonte=copernicus').json()['count'], 2)

    def test_filtra_por_periodo(self):
        corpo = self.buscar('?de=2026-07-24&ate=2026-07-24').json()

        self.assertEqual(corpo['count'], 3)

    def test_o_periodo_e_inclusivo_nas_duas_pontas(self):
        self.assertEqual(self.buscar('?de=2026-07-20&ate=2026-07-20').json()['count'], 1)

    def test_os_filtros_se_combinam(self):
        corpo = self.buscar(
            '?local=teste-abrolhos&fonte=noaa_crw&de=2026-07-24'
        ).json()

        self.assertEqual(corpo['count'], 2)

    def test_sem_filtro_devolve_tudo(self):
        self.assertEqual(self.buscar().json()['count'], 5)

    def test_filtro_que_nao_casa_devolve_lista_vazia_e_nao_erro(self):
        corpo = self.buscar('?local=nao-existe').json()

        self.assertEqual(corpo['count'], 0)
        self.assertEqual(corpo['results'], [])

    # --- entrada invalida ---------------------------------------------------

    def test_data_invalida_falha_alto(self):
        """🚨 Sem isto o filtro seria ignorado e o cliente receberia TUDO."""
        resposta = self.buscar('?de=ontem')

        self.assertEqual(resposta.status_code, 400)
        self.assertIn('AAAA-MM-DD', resposta.json()['detail'])

    def test_data_invalida_no_ate_tambem_falha(self):
        self.assertEqual(self.buscar('?ate=32/13/2026').status_code, 400)

    # --- ordenacao ----------------------------------------------------------

    def test_vem_do_mais_recente_para_o_mais_antigo(self):
        datas = [x['data'] for x in self.buscar().json()['results']]

        self.assertEqual(datas, sorted(datas, reverse=True))

    # --- modo offline -------------------------------------------------------

    @override_settings(OFFLINE_MODE=True)
    def test_respeita_o_modo_offline(self):
        resposta = self.buscar()

        self.assertEqual(resposta.status_code, 503)
