"""Testes do retrato de envelhecimento da rotina diaria.

O que protegem, em ordem de gravidade:

1. 🚨 **Modelo ausente e um estado, nao um erro.** Um servidor recem-provisionado
   esta assim, e a rotina precisa relatar em vez de morrer — a ingestao do dia
   ainda vale.
2. **Silencio quando esta tudo bem.** Rotina que sempre imprime aviso treina
   quem a le a ignorar todos.
3. **Ingestao parada e modelo velho sao problemas diferentes**, com acoes
   diferentes, e nao podem virar o mesmo recado.
"""

from datetime import date

from django.test import TestCase

from db import atualizacao


def estado(**extras):
    campos = {
        'fim_da_serie': date(2026, 7, 27),
        'dias_desde_ultima_medicao': 1,
        'medicoes': 57426,
        'modelo': 'entrega1_baa',
        'modelo_treinado_em': date(2026, 7, 28),
        'dias_desde_o_treino': 0,
    }
    campos.update(extras)
    return atualizacao.Estado(**campos)


class LimiaresTests(TestCase):
    def test_dia_normal_e_saudavel(self):
        self.assertTrue(estado().saudavel)

    def test_ingestao_parada_a_partir_do_limiar(self):
        limite = atualizacao.DIAS_ATE_INGESTAO_PARADA

        self.assertFalse(estado(dias_desde_ultima_medicao=limite - 1).ingestao_parada)
        self.assertTrue(estado(dias_desde_ultima_medicao=limite).ingestao_parada)

    def test_modelo_velho_a_partir_do_limiar(self):
        limite = atualizacao.DIAS_ATE_MODELO_VELHO

        self.assertFalse(estado(dias_desde_o_treino=limite - 1).modelo_velho)
        self.assertTrue(estado(dias_desde_o_treino=limite).modelo_velho)

    def test_os_dois_problemas_sao_independentes(self):
        """Ingestao parada nao implica modelo velho, nem o contrario."""
        so_ingestao = estado(dias_desde_ultima_medicao=30)
        so_modelo = estado(dias_desde_o_treino=200)

        self.assertTrue(so_ingestao.ingestao_parada)
        self.assertFalse(so_ingestao.modelo_velho)
        self.assertFalse(so_modelo.ingestao_parada)
        self.assertTrue(so_modelo.modelo_velho)


class RecadosTests(TestCase):
    def test_dia_normal_nao_diz_nada(self):
        """🚨 Aviso todo dia e aviso que ninguem le."""
        self.assertEqual(atualizacao.recados(estado()), [])

    def test_banco_vazio_e_o_unico_recado(self):
        """Sem dado, falar do modelo seria ruido: nada funciona mesmo."""
        avisos = atualizacao.recados(estado(medicoes=0))

        self.assertEqual(len(avisos), 1)
        self.assertIn('vazio', avisos[0])

    def test_ingestao_parada_diz_ha_quantos_dias_e_o_que_fazer(self):
        avisos = atualizacao.recados(estado(dias_desde_ultima_medicao=30))

        self.assertEqual(len(avisos), 1)
        self.assertIn('30', avisos[0])
        self.assertIn('testar_fontes', avisos[0])

    def test_modelo_ausente_avisa_do_503(self):
        """🚨 O sintoma que o usuario ve, e nao o nome do arquivo."""
        avisos = atualizacao.recados(estado(modelo_treinado_em=None))

        self.assertEqual(len(avisos), 1)
        self.assertIn('503', avisos[0])
        self.assertIn('treinar_final', avisos[0])

    def test_modelo_velho_nao_e_apresentado_como_erro(self):
        """O retreino e deliberado de proposito — o recado precisa dizer isso.

        Se soar como defeito, a reacao natural e automatizar o retreino, que e
        exatamente o que este projeto decidiu **nao** fazer.
        """
        avisos = atualizacao.recados(estado(dias_desde_o_treino=200))

        self.assertEqual(len(avisos), 1)
        self.assertIn('nao e erro', avisos[0])
        self.assertIn('treinar_modelo', avisos[0])

    def test_os_dois_problemas_juntos_geram_dois_recados(self):
        avisos = atualizacao.recados(
            estado(dias_desde_ultima_medicao=30, dias_desde_o_treino=200)
        )

        self.assertEqual(len(avisos), 2)


class MedirTests(TestCase):
    def setUp(self):
        from aquaculture.models import LocalRecife, MedicaoAmbiental

        MedicaoAmbiental.objects.all().delete()
        LocalRecife.objects.all().delete()

        self.local = LocalRecife.objects.create(
            slug='teste-abrolhos', nome='Abrolhos', estado='BA',
            cidade='Caravelas', latitude=-17.9, longitude=-38.6,
        )

    def test_banco_vazio_nao_quebra(self):
        from aquaculture.models import MedicaoAmbiental

        MedicaoAmbiental.objects.all().delete()

        medido = atualizacao.medir(hoje=date(2026, 7, 28))

        self.assertEqual(medido.medicoes, 0)
        self.assertIsNone(medido.fim_da_serie)

    def test_le_o_fim_da_serie_e_conta_os_dias(self):
        from aquaculture.models import MedicaoAmbiental

        MedicaoAmbiental.objects.create(
            local_recife=self.local, data=date(2026, 7, 20), variavel='sst',
            valor=25.0, unidade='°C', fonte='noaa_crw', dataset_id='dhw_5km',
        )

        medido = atualizacao.medir(hoje=date(2026, 7, 28))

        self.assertEqual(medido.fim_da_serie, date(2026, 7, 20))
        self.assertEqual(medido.dias_desde_ultima_medicao, 8)

    def test_modelo_inexistente_nao_levanta(self):
        """🚨 Servidor novo esta nesse estado; a rotina precisa seguir."""
        medido = atualizacao.medir(
            hoje=date(2026, 7, 28), nome_modelo='modelo-que-nao-existe'
        )

        self.assertIsNone(medido.modelo_treinado_em)
        self.assertIn('ausente', medido.modelo)

    def test_data_futura_nao_produz_defasagem_negativa(self):
        """Relogio do servidor atrasado nao pode virar "-3 dias"."""
        from aquaculture.models import MedicaoAmbiental

        MedicaoAmbiental.objects.create(
            local_recife=self.local, data=date(2026, 7, 30), variavel='sst',
            valor=25.0, unidade='°C', fonte='noaa_crw', dataset_id='dhw_5km',
        )

        medido = atualizacao.medir(hoje=date(2026, 7, 28))

        self.assertEqual(medido.dias_desde_ultima_medicao, 0)
