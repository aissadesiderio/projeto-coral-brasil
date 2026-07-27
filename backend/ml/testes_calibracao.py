"""Testes da medida de calibracao.

O que protegem, em ordem de gravidade: que um modelo que **promete demais seja
denunciado** (era o caso do que estava no ar), que a decomposicao de Murphy
feche a conta, que as faixas por quantil nao colapsem quando a predicao satura,
e que a recalibracao viaje nos metadados do artefato — sem isso ninguem sabe se
a probabilidade gravada e crua ou corrigida, e a diferenca vale 0,081 de ECE.
"""

import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from ml import calibracao, modelo


class CurvaTests(SimpleTestCase):
    def test_modelo_perfeito_tem_desvio_zero(self):
        """Metade dos casos a 0%, metade a 100%, e acontece exatamente isso."""
        y = np.array([0] * 50 + [1] * 50)
        p = np.array([0.0] * 50 + [1.0] * 50)

        faixas = calibracao.curva(y, p, n_faixas=2)

        self.assertTrue(all(abs(f.desvio) < 1e-9 for f in faixas))
        self.assertAlmostEqual(calibracao.erro_esperado(faixas), 0.0)

    def test_denuncia_quem_promete_demais(self):
        """A regressao real: o modelo no ar prometia 0,165 sobre taxa 0,084."""
        y = np.zeros(100)
        y[:8] = 1                      # 8% de eventos
        p = np.full(100, 0.30)         # e o modelo promete 30%

        faixas = calibracao.curva(y, p, n_faixas=5)

        self.assertGreater(calibracao.erro_esperado(faixas), 0.2)
        self.assertTrue(all(f.desvio > 0 for f in faixas))

    def test_denuncia_quem_promete_de_menos(self):
        y = np.ones(100)
        p = np.full(100, 0.10)

        faixas = calibracao.curva(y, p, n_faixas=5)

        self.assertTrue(all(f.desvio < 0 for f in faixas))

    def test_as_faixas_cobrem_todas_as_amostras(self):
        gerador = np.random.default_rng(42)
        p = gerador.random(500)
        y = (gerador.random(500) < p).astype(int)

        faixas = calibracao.curva(y, p, n_faixas=10)

        self.assertEqual(sum(f.n for f in faixas), 500)

    def test_quantil_distribui_o_n_entre_as_faixas(self):
        """Com evento raro, faixa de largura igual concentraria tudo na primeira."""
        gerador = np.random.default_rng(7)
        p = gerador.beta(1, 20, 1000)      # quase tudo perto de zero
        y = (gerador.random(1000) < p).astype(int)

        por_quantil = calibracao.curva(y, p, 10, 'quantil')
        por_largura = calibracao.curva(y, p, 10, 'largura')

        maior_quantil = max(f.n for f in por_quantil) / 1000
        maior_largura = max(f.n for f in por_largura) / 1000
        self.assertLess(maior_quantil, maior_largura)

    def test_predicao_saturada_nao_quebra(self):
        """Quase tudo em zero colapsa as bordas dos quantis."""
        p = np.array([0.0] * 990 + [0.9] * 10)
        y = np.array([0] * 990 + [1] * 10)

        faixas = calibracao.curva(y, p, n_faixas=10)

        self.assertGreater(len(faixas), 0)
        self.assertEqual(sum(f.n for f in faixas), 1000)

    def test_predicao_constante_nao_vira_curva_vazia(self):
        """🚨 A regressao mais perigosa deste modulo.

        Se `qcut` colapsa todas as bordas, a curva sai vazia e o ECE da 0,0 —
        que se le como "calibracao perfeita". Um modelo que responde sempre 30%
        sobre 8% de eventos e o pior possivel, e passava como o melhor.
        """
        y = np.zeros(100)
        y[:8] = 1
        p = np.full(100, 0.30)

        faixas = calibracao.curva(y, p, n_faixas=10)

        self.assertEqual(len(faixas), 1)
        self.assertEqual(faixas[0].n, 100)
        self.assertAlmostEqual(calibracao.erro_esperado(faixas), 0.22, places=2)

    def test_conjunto_vazio(self):
        self.assertEqual(calibracao.curva([], []), [])
        self.assertEqual(calibracao.erro_esperado([]), 0.0)
        self.assertEqual(calibracao.erro_maximo([]), 0.0)

    def test_tamanhos_diferentes_sao_recusados(self):
        with self.assertRaises(ValueError):
            calibracao.curva([0, 1], [0.5])

    def test_estrategia_desconhecida_e_recusada(self):
        with self.assertRaises(ValueError):
            calibracao.curva([0, 1], [0.1, 0.9], estrategia='chute')


class ErroTests(SimpleTestCase):
    def test_ece_pondera_pelo_tamanho_da_faixa(self):
        """Uma faixa grande e certa nao deve ser afogada por uma pequena e errada."""
        faixas = [
            calibracao.Faixa(0.0, 0.1, 990, 0.00, 0.00, 0),   # certa, e grande
            calibracao.Faixa(0.4, 0.6, 10, 0.50, 1.00, 10),   # errada, e pequena
        ]

        ece = calibracao.erro_esperado(faixas)
        mce = calibracao.erro_maximo(faixas)

        # A faixa ruim tem 1% do peso: o MCE grita, o ECE quase nao sente.
        self.assertAlmostEqual(mce, 0.5)
        self.assertAlmostEqual(ece, 0.005)
        self.assertLess(ece, mce / 10)

    def test_mce_pega_a_pior_faixa(self):
        faixas = [
            calibracao.Faixa(0.0, 0.1, 100, 0.05, 0.05, 5),
            calibracao.Faixa(0.9, 1.0, 10, 0.95, 0.10, 1),
        ]

        self.assertAlmostEqual(calibracao.erro_maximo(faixas), 0.85)


class DecomposicaoTests(SimpleTestCase):
    def test_a_conta_de_murphy_fecha(self):
        gerador = np.random.default_rng(3)
        p = gerador.random(2000)
        y = (gerador.random(2000) < p).astype(int)

        d = calibracao.decompor(y, p, n_faixas=20)

        self.assertLess(abs(d.residuo), 0.01)

    def test_incerteza_depende_so_da_taxa_base(self):
        y = np.concatenate([np.zeros(80), np.ones(20)])   # 20%

        d = calibracao.decompor(y, np.full(100, 0.5))

        self.assertAlmostEqual(d.incerteza, 0.2 * 0.8, places=6)

    def test_modelo_que_repete_a_taxa_base_tem_resolucao_zero(self):
        """Ele acerta na media e nao separa ninguem. E o caso a denunciar."""
        y = np.concatenate([np.zeros(90), np.ones(10)])

        d = calibracao.decompor(y, np.full(100, 0.1), n_faixas=5)

        self.assertAlmostEqual(d.resolucao, 0.0, places=6)
        self.assertAlmostEqual(d.confiabilidade, 0.0, places=6)

    def test_modelo_que_separa_tem_resolucao_alta(self):
        y = np.concatenate([np.zeros(50), np.ones(50)])
        p = np.concatenate([np.zeros(50), np.ones(50)])

        d = calibracao.decompor(y, p, n_faixas=2)

        self.assertGreater(d.resolucao, 0.2)
        self.assertAlmostEqual(d.brier, 0.0, places=6)

    def test_conjunto_vazio(self):
        d = calibracao.decompor([], [])

        self.assertEqual(d.brier, 0.0)


class RelatorioTests(SimpleTestCase):
    def test_vies_global_positivo_quando_promete_demais(self):
        relatorio = calibracao.Relatorio(
            modelo='x', n=100, taxa_base=0.084, probabilidade_media=0.165,
        )

        self.assertAlmostEqual(relatorio.vies_global, 0.081, places=3)


class CalibracaoNoModeloTests(SimpleTestCase):
    COLUNAS = ('a', 'b')

    def _quadro(self, n=200):
        gerador = np.random.default_rng(11)
        a = gerador.normal(0, 1, n)
        return pd.DataFrame({
            'a': a,
            'b': gerador.normal(0, 1, n),
            'alvo': np.where(a > 1.2, 4.0, 0.0),   # evento raro
        })

    def test_calibracao_desconhecida_e_recusada(self):
        with self.assertRaises(ValueError) as contexto:
            modelo.construir('logistica', calibrar='chute')

        self.assertIn('chute', str(contexto.exception))

    def test_sem_calibrar_devolve_o_pipeline_cru(self):
        from sklearn.pipeline import Pipeline

        self.assertIsInstance(modelo.construir('logistica'), Pipeline)

    def test_com_calibrar_devolve_o_envelope(self):
        from sklearn.calibration import CalibratedClassifierCV

        self.assertIsInstance(
            modelo.construir('logistica', calibrar='isotonic'),
            CalibratedClassifierCV,
        )

    def test_a_calibracao_viaja_nos_metadados(self):
        """Sem isto ninguem sabe se a probabilidade gravada e crua."""
        ajuste = modelo.treinar(
            self._quadro(), self.COLUNAS, calibrar='sigmoid'
        )

        self.assertEqual(ajuste.calibracao, 'sigmoid')
        self.assertEqual(ajuste.metadados()['calibracao'], 'sigmoid')

    def test_sem_calibracao_o_metadado_diz_none(self):
        ajuste = modelo.treinar(self._quadro(), self.COLUNAS)

        self.assertIsNone(ajuste.metadados()['calibracao'])

    def test_recalibrar_aproxima_a_media_da_taxa_base(self):
        """O efeito que se quer: o numero prometido para de inflar.

        `class_weight='balanced'` empurra a probabilidade para cima; o
        recalibrador desfaz isso. Aqui basta comparar as duas medias contra a
        taxa real — nao e medida de desempenho, e sim do vies.
        """
        quadro = self._quadro(400)
        taxa = modelo.alvo_binario(quadro['alvo']).mean()

        cru = modelo.treinar(quadro, self.COLUNAS)
        calibrado = modelo.treinar(quadro, self.COLUNAS, calibrar='isotonic')

        vies_cru = abs(cru.prever_probabilidade(quadro).mean() - taxa)
        vies_cal = abs(calibrado.prever_probabilidade(quadro).mean() - taxa)

        self.assertLess(vies_cal, vies_cru)
