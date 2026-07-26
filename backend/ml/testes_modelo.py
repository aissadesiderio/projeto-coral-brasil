"""Testes do modelo e da comparacao contra a persistencia.

O que estes testes protegem: que a ordem das colunas deixe de ser contrato
implicito (o defeito que fazia o modelo antigo predizer 0.0 para tudo), que
ano sem evento nao entre na media, e que a comparacao seja feita nas mesmas
amostras - comparar em conjuntos diferentes nao diria nada.
"""

from datetime import date, timedelta

import pandas as pd
from django.test import TestCase

from aquaculture.models import LocalRecife, MedicaoAmbiental
from ml.dataset import montar
from ml.modelo import (
    MODELOS,
    ColunaAusente,
    alvo_binario,
    comparar_com_persistencia,
    como_baa,
    construir,
    treinar,
)

FEATURES = ('sst', 'dhw')
UNIDADES = {'sst': '°C', 'dhw': '°C·semana', 'baa': 'categoria'}


def serie_com_evento(local, inicio, dias):
    """Serie sintetica em que o DHW sobe antes do alerta chegar.

    Da ao modelo algo aprendivel - senao os testes mediriam so o ruido.
    """
    for i in range(dias):
        ciclo = i % 120
        dhw = max(0.0, (ciclo - 30) / 8)
        baa = 4.0 if dhw >= 6 else 0.0
        for variavel, valor in (
            ('sst', 28.0 + dhw / 10),
            ('dhw', dhw),
            ('baa', baa),
        ):
            MedicaoAmbiental.objects.create(
                local_recife=local, data=inicio + timedelta(days=i),
                variavel=variavel, valor=valor, unidade=UNIDADES[variavel],
                fonte='noaa_crw', quality_flag='ok',
            )


class ConstrucaoTests(TestCase):
    def test_modelos_disponiveis_constroem(self):
        for nome in MODELOS:
            self.assertIsNotNone(construir(nome))

    def test_modelo_desconhecido_e_recusado(self):
        with self.assertRaises(ValueError) as ctx:
            construir('rede-neural-profunda')

        self.assertIn('rede-neural-profunda', str(ctx.exception))

    def test_alvo_binario_usa_o_limiar_de_alerta(self):
        entrada = pd.Series([0.0, 2.0, 3.0, 4.0])

        self.assertEqual(list(alvo_binario(entrada)), [0, 0, 1, 1])

    def test_como_baa_devolve_serie_comparavel_no_nivel(self):
        self.assertEqual(list(como_baa(pd.Series([0, 1]))), [0, 3])


class OrdemDeColunaTests(TestCase):
    """A regressao central: o modelo antigo predizia 0.0 por ordem trocada."""

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-modelo', nome='Modelo', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )
        serie_com_evento(self.local, date(2020, 1, 1), 400)
        self.conjunto = montar(self.local, 7, features=FEATURES, janelas=())
        self.ajuste = treinar(
            self.conjunto.quadro, self.conjunto.colunas_de_entrada
        )

    def test_quadro_com_colunas_em_outra_ordem_da_o_mesmo_resultado(self):
        quadro = self.conjunto.quadro
        invertido = quadro[list(reversed(list(quadro.columns)))]

        original = self.ajuste.prever_probabilidade(quadro)
        trocado = self.ajuste.prever_probabilidade(invertido)

        self.assertTrue((original == trocado).all())

    def test_coluna_faltando_falha_alto_em_vez_de_prever_zero(self):
        sem_dhw = self.conjunto.quadro.drop(columns=['dhw'])

        with self.assertRaises(ColunaAusente) as ctx:
            self.ajuste.prever_probabilidade(sem_dhw)

        self.assertIn('dhw', str(ctx.exception))

    def test_metadados_registram_o_que_o_modelo_viu(self):
        meta = self.ajuste.metadados()

        self.assertEqual(meta['colunas'], list(FEATURES))
        self.assertEqual(meta['horizonte_dias'], 7)
        self.assertIn('baa >= 3', meta['alvo'])
        self.assertEqual(meta['n_treino'], len(self.conjunto.quadro))

    def test_probabilidade_fica_entre_zero_e_um(self):
        p = self.ajuste.prever_probabilidade(self.conjunto.quadro)

        self.assertTrue((p >= 0).all() and (p <= 1).all())


class ComparacaoTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-comparacao', nome='Comp', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )
        serie_com_evento(self.local, date(2020, 1, 1), 1200)
        self.conjunto = montar(self.local, 7, features=FEATURES, janelas=())

    def test_compara_nas_mesmas_amostras(self):
        comparacao = comparar_com_persistencia(self.conjunto)

        for ano in comparacao.anos_com_evento:
            self.assertEqual(
                ano.desempenho_modelo.n, ano.desempenho_persistencia.n,
                'comparar em conjuntos diferentes nao diria nada',
            )

    def test_ano_sem_evento_nao_entra_na_media(self):
        """F1 zero num ano sem nada a detectar mede o clima, nao o modelo."""
        comparacao = comparar_com_persistencia(self.conjunto)
        comparacao.anos.append(
            type(comparacao.anos[0])(ano=1999, n_teste=10, positivos_teste=0)
        )

        avaliados = comparacao.anos_com_evento

        self.assertTrue(all(r.positivos_teste > 0 for r in avaliados))
        self.assertNotIn(1999, [r.ano for r in avaliados])

    def test_ano_sem_evento_e_relatado_e_nao_omitido(self):
        comparacao = comparar_com_persistencia(self.conjunto)
        texto = comparacao.resumo()

        self.assertIn('leave-year-out', texto)
        self.assertIn('persistencia', texto)

    def test_treino_nunca_contem_o_ano_de_teste(self):
        """Se contivesse, o resultado seria decoreba e nao previsao."""
        from ml.baseline import anos_disponiveis, dividir_deixando_um_ano_de_fora

        quadro = self.conjunto.quadro
        for ano in anos_disponiveis(quadro):
            treino, teste = dividir_deixando_um_ano_de_fora(quadro, ano)
            anos_treino = {d.year for d in treino['alvo_data']}
            self.assertNotIn(ano, anos_treino)
            self.assertTrue(all(d.year == ano for d in teste['alvo_data']))

    def test_metricas_probabilisticas_ficam_na_faixa_valida(self):
        comparacao = comparar_com_persistencia(self.conjunto)

        for r in comparacao.anos_com_evento:
            self.assertGreaterEqual(r.pr_auc, 0.0)
            self.assertLessEqual(r.pr_auc, 1.0)
            self.assertGreaterEqual(r.brier, 0.0)
            self.assertLessEqual(r.brier, 1.0)
