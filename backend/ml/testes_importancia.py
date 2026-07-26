"""Testes da medida de importancia de variavel.

O que protegem: que o agrupamento variavel+trajetoria esteja certo, que a
medida seja feita no ano deixado de fora e nao no treino, e que uma coluna
inutil realmente apareca como inutil - senao a medida nao serve para decidir
nada.
"""

from datetime import date, timedelta

import pandas as pd
from django.test import TestCase

from aquaculture.models import LocalRecife, MedicaoAmbiental
from ml.dataset import Janela, montar
from ml.importancia import (
    coeficientes,
    grupos_de_variavel,
    medir,
    queda_por_permutacao,
)
from ml.modelo import treinar

UNIDADES = {'sst': '°C', 'dhw': '°C·semana', 'baa': 'categoria',
            'salinidade': 'PSU'}


def serie_util(local, inicio, dias):
    """O DHW determina o alerta; a salinidade e ruido puro.

    Assim o teste tem uma variavel que importa e outra que nao, e a medida
    precisa saber distinguir as duas.
    """
    import random

    sorteio = random.Random(7)
    for i in range(dias):
        ciclo = i % 150
        dhw = max(0.0, (ciclo - 40) / 8)
        baa = 4.0 if dhw >= 6 else 0.0
        valores = {
            'sst': 28.0 + dhw / 10,
            'dhw': dhw,
            'salinidade': sorteio.uniform(35.0, 37.0),
            'baa': baa,
        }
        for variavel, valor in valores.items():
            MedicaoAmbiental.objects.create(
                local_recife=local, data=inicio + timedelta(days=i),
                variavel=variavel, valor=valor, unidade=UNIDADES[variavel],
                fonte='noaa_crw', quality_flag='ok',
            )


class AgrupamentoTests(TestCase):
    def test_variavel_e_suas_trajetorias_formam_um_grupo(self):
        grupos = grupos_de_variavel(
            ('sst', 'dhw', 'sst_variacao_7d', 'sst_variacao_14d', 'dhw_variacao_7d')
        )

        self.assertEqual(
            grupos['sst'], ['sst', 'sst_variacao_7d', 'sst_variacao_14d']
        )
        self.assertEqual(grupos['dhw'], ['dhw', 'dhw_variacao_7d'])

    def test_agrupa_media_e_maximo_tambem(self):
        grupos = grupos_de_variavel(('sst', 'sst_media_7d', 'sst_maximo_14d'))

        self.assertEqual(len(grupos), 1)
        self.assertEqual(len(grupos['sst']), 3)

    def test_variavel_sem_janela_forma_grupo_de_um(self):
        grupos = grupos_de_variavel(('oxigenio',))

        self.assertEqual(grupos, {'oxigenio': ['oxigenio']})


class PermutacaoTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-import', nome='Imp', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )
        serie_util(self.local, date(2020, 1, 1), 900)
        self.conjunto = montar(
            self.local, 7, features=('dhw', 'salinidade'),
            janelas=(Janela('dhw', 7, 'variacao'),),
        )
        self.ajuste = treinar(
            self.conjunto.quadro, self.conjunto.colunas_de_entrada
        )

    def test_variavel_que_decide_cai_mais_que_ruido(self):
        """Se a medida nao distingue sinal de ruido, ela nao serve."""
        queda_dhw, _ = queda_por_permutacao(
            self.ajuste, self.conjunto.quadro, ['dhw'], repeticoes=5
        )
        queda_ruido, _ = queda_por_permutacao(
            self.ajuste, self.conjunto.quadro, ['salinidade'], repeticoes=5
        )

        self.assertGreater(queda_dhw, queda_ruido)

    def test_ruido_puro_quase_nao_derruba_o_modelo(self):
        queda, _ = queda_por_permutacao(
            self.ajuste, self.conjunto.quadro, ['salinidade'], repeticoes=5
        )

        self.assertLess(abs(queda), 0.05)

    def test_grupo_cai_pelo_menos_tanto_quanto_a_coluna_isolada(self):
        """Embaralhar a variavel e sua trajetoria junto destroi mais informacao."""
        grupo, _ = queda_por_permutacao(
            self.ajuste, self.conjunto.quadro,
            ['dhw', 'dhw_variacao_7d'], repeticoes=5,
        )
        isolada, _ = queda_por_permutacao(
            self.ajuste, self.conjunto.quadro, ['dhw'], repeticoes=5
        )

        self.assertGreaterEqual(grupo, isolada - 1e-9)

    def test_permutacao_nao_altera_o_quadro_original(self):
        antes = self.conjunto.quadro['dhw'].copy()

        queda_por_permutacao(
            self.ajuste, self.conjunto.quadro, ['dhw'], repeticoes=3
        )

        pd.testing.assert_series_equal(antes, self.conjunto.quadro['dhw'])

    def test_repeticao_e_deterministica_com_a_mesma_semente(self):
        a, _ = queda_por_permutacao(
            self.ajuste, self.conjunto.quadro, ['dhw'], repeticoes=3, semente=1
        )
        b, _ = queda_por_permutacao(
            self.ajuste, self.conjunto.quadro, ['dhw'], repeticoes=3, semente=1
        )

        self.assertEqual(a, b)


class CoeficienteTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-coef', nome='Coef', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )
        serie_util(self.local, date(2020, 1, 1), 900)
        self.conjunto = montar(
            self.local, 7, features=('dhw', 'salinidade'), janelas=()
        )

    def test_logistica_expoe_coeficiente_por_variavel(self):
        ajuste = treinar(
            self.conjunto.quadro, self.conjunto.colunas_de_entrada, 'logistica'
        )

        coefs = coeficientes(ajuste)

        self.assertEqual(set(coefs), {'dhw', 'salinidade'})

    def test_calor_acumulado_tem_coeficiente_positivo(self):
        """Direcao precisa fazer sentido fisico, senao algo esta invertido."""
        ajuste = treinar(
            self.conjunto.quadro, self.conjunto.colunas_de_entrada, 'logistica'
        )

        self.assertGreater(coeficientes(ajuste)['dhw'], 0)

    def test_arvore_nao_tem_coeficiente_e_devolve_none(self):
        ajuste = treinar(
            self.conjunto.quadro, self.conjunto.colunas_de_entrada, 'boosting'
        )

        self.assertIsNone(coeficientes(ajuste))


class MedidaLeaveYearOutTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-lyo', nome='LYO', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )
        serie_util(self.local, date(2020, 1, 1), 1100)
        self.conjunto = montar(
            self.local, 7, features=('dhw', 'salinidade'),
            janelas=(Janela('dhw', 7, 'variacao'),),
        )

    def test_mede_em_mais_de_um_ano(self):
        resultado = medir(self.conjunto, repeticoes=3)

        self.assertGreater(len(resultado.anos), 1)

    def test_cobre_todas_as_colunas_e_grupos(self):
        resultado = medir(self.conjunto, repeticoes=3)

        self.assertEqual(
            set(resultado.por_coluna), set(self.conjunto.colunas_de_entrada)
        )
        self.assertEqual(set(resultado.por_grupo), {'dhw', 'salinidade'})

    def test_resumo_mostra_grupo_coluna_e_coeficiente(self):
        texto = medir(self.conjunto, repeticoes=3).resumo()

        self.assertIn('POR GRUPO', texto)
        self.assertIn('POR COLUNA', texto)
        self.assertIn('COEFICIENTES', texto)

    def test_boosting_nao_traz_coeficiente(self):
        resultado = medir(self.conjunto, nome='boosting', repeticoes=3)

        self.assertEqual(resultado.coeficientes, {})
        self.assertNotIn('COEFICIENTES', resultado.resumo())
