"""Testes do conjunto do GCBD (entrega 2, passo 1).

O que protegem, em ordem de gravidade: que a **unidade amostral seja a visita**
(tratar linha como amostra inflaria n em 1,9x), que a **sentinela do ClimSST**
nunca entre como numero, que a **validacao agrupada** nao ponha o mesmo sitio
dos dois lados, e que uma coluna recusada nao volte como feature por descuido.

Nao dependem do CSV real - montam quadros pequenos a mao. Assim os testes
rodam sem o arquivo de 16 MB, que nao e versionado.
"""

import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from ml import gcbd


def visita(site, data, pb, dhw=0.0, tsa=0.0, vento=5.0, temp=300.0,
           substrato='Hard Coral'):
    """Uma linha crua no formato do GCBD."""
    return {
        'Site_ID': site,
        'Date': data,
        'Date_Year': int(data[:4]),
        'Country_Name': 'Brazil',
        'Substrate_Name': substrato,
        'Percent_Bleaching': pb,
        'Temperature_Kelvin': temp,
        'SSTA': tsa / 2,
        'SSTA_Frequency': 0.0,
        'SSTA_DHW': dhw / 2,
        'TSA': tsa,
        'TSA_Frequency': 0.0,
        'TSA_DHW': dhw,
        'Windspeed': vento,
        'ClimSST': 300.0,
        'Latitude_Degrees': -13.0,
        'Longitude_Degrees': -38.0,
    }


class AgregarPorVisitaTests(SimpleTestCase):
    def test_linhas_de_substrato_viram_uma_visita(self):
        """A regressao central: 313 linhas brasileiras sao 166 visitas."""
        cru = pd.DataFrame([
            visita(1, '2005-04-05', 2.0, substrato='Hard Coral'),
            visita(1, '2005-04-05', 2.0, substrato='Nutrient Indicator Algae'),
            visita(1, '2005-04-05', 2.0, substrato='Fleshy Seaweed'),
        ])

        visitas = gcbd.agregar_por_visita(cru)

        self.assertEqual(len(visitas), 1)
        self.assertEqual(visitas.loc[0, 'Percent_Bleaching'], 2.0)

    def test_visitas_diferentes_do_mesmo_sitio_nao_se_fundem(self):
        cru = pd.DataFrame([
            visita(1, '2005-04-05', 2.0),
            visita(1, '2007-11-13', 0.0),
        ])

        self.assertEqual(len(gcbd.agregar_por_visita(cru)), 2)

    def test_alvo_divergente_na_visita_usa_o_maximo(self):
        """Media diluiria branqueamento real de coral duro contra zero de alga."""
        cru = pd.DataFrame([
            visita(1, '2005-04-05', 40.0, substrato='Hard Coral'),
            visita(1, '2005-04-05', 0.0, substrato='Fleshy Seaweed'),
        ])

        visitas = gcbd.agregar_por_visita(cru)

        self.assertEqual(len(visitas), 1)
        self.assertEqual(visitas.loc[0, 'Percent_Bleaching'], 40.0)

    def test_sitios_diferentes_na_mesma_data_ficam_separados(self):
        cru = pd.DataFrame([
            visita(1, '2005-04-05', 2.0),
            visita(2, '2005-04-05', 0.0),
        ])

        self.assertEqual(len(gcbd.agregar_por_visita(cru)), 2)


class SentinelaTests(SimpleTestCase):
    def test_climsst_sentinela_vira_nan(self):
        """262,15 K = -11 C. Ausencia codificada como numero, em 115 de 313."""
        cru = pd.DataFrame([visita(1, '2005-04-05', 2.0)])
        cru.loc[0, 'ClimSST'] = 262.15

        limpo, trocados = gcbd.limpar_sentinelas(cru)

        self.assertTrue(np.isnan(limpo.loc[0, 'ClimSST']))
        self.assertEqual(trocados, {'ClimSST': 1})

    def test_climsst_valido_atravessa_intacto(self):
        cru = pd.DataFrame([visita(1, '2005-04-05', 2.0)])

        limpo, trocados = gcbd.limpar_sentinelas(cru)

        self.assertEqual(limpo.loc[0, 'ClimSST'], 300.0)
        self.assertEqual(trocados, {})


class ColunasRecusadasTests(SimpleTestCase):
    def test_climsst_recusada_como_feature(self):
        with self.assertRaises(ValueError) as contexto:
            gcbd.montar(features=('TSA_DHW', 'ClimSST'))

        self.assertIn('262,15', str(contexto.exception))

    def test_ssta_mean_recusada_como_feature(self):
        with self.assertRaises(ValueError) as contexto:
            gcbd.montar(features=('TSA_DHW', 'SSTA_Mean'))

        self.assertIn('constante', str(contexto.exception))

    def test_as_recusadas_nao_estao_nos_conjuntos_padrao(self):
        for conjunto in (gcbd.TERMICAS_DO_DIA, gcbd.CLIMATOLOGIA_DO_SITIO,
                         gcbd.CONTEXTO_DO_SITIO, gcbd.FEATURES_PADRAO,
                         gcbd.FEATURES_INTERPRETAVEIS):
            for recusada in gcbd.COLUNAS_RECUSADAS:
                self.assertNotIn(recusada, conjunto)

    def test_do_dia_e_climatologia_nao_se_sobrepoem(self):
        self.assertEqual(
            set(gcbd.TERMICAS_DO_DIA) & set(gcbd.CLIMATOLOGIA_DO_SITIO), set()
        )

    def test_interpretaveis_saem_das_termicas_do_dia(self):
        for coluna in gcbd.FEATURES_INTERPRETAVEIS:
            self.assertIn(coluna, gcbd.TERMICAS_DO_DIA)

    def test_windspeed_ficou_fora_do_conjunto_interpretavel(self):
        """A regressao de 27/07/2026, e o motivo nao e cosmetico.

        O `Windspeed` do GCBD dava o melhor numero, mas o efeito nao sobrevive
        a troca por vento medido do ERA5 (docs/RESULTADOS.md secao 20): as duas
        fontes concordam sobre o vento e discordam sobre o coral. Reintroduzi-lo
        sem reexaminar essa medicao seria reintroduzir o erro.
        """
        self.assertNotIn('Windspeed', gcbd.FEATURES_INTERPRETAVEIS)

    def test_interpretaveis_sao_so_as_duas_termicas_com_mecanismo(self):
        self.assertEqual(gcbd.FEATURES_INTERPRETAVEIS, ('TSA_DHW', 'TSA'))


class AvaliarTests(SimpleTestCase):
    def test_metricas_binarias(self):
        verdadeiro = pd.Series([1, 1, 1, 0, 0, 0])
        previsto = pd.Series([1, 1, 0, 1, 0, 0])

        d = gcbd.avaliar(verdadeiro, previsto)

        self.assertEqual((d.verdadeiros_positivos, d.falsos_positivos,
                          d.falsos_negativos), (2, 1, 1))
        self.assertAlmostEqual(d.precisao, 2 / 3)
        self.assertAlmostEqual(d.revocacao, 2 / 3)
        self.assertAlmostEqual(d.f1, 2 / 3)
        self.assertAlmostEqual(d.taxa_majoritaria, 0.5)

    def test_conjunto_vazio_nao_quebra(self):
        d = gcbd.avaliar(pd.Series([], dtype=int), pd.Series([], dtype=int))

        self.assertEqual(d.n, 0)
        self.assertEqual(d.f1, 0.0)

    def test_sem_positivo_previsto_a_precisao_e_zero_e_nao_nan(self):
        d = gcbd.avaliar(pd.Series([1, 0]), pd.Series([0, 0]))

        self.assertEqual(d.precisao, 0.0)
        self.assertEqual(d.f1, 0.0)


class RegraNoaaTests(SimpleTestCase):
    def test_limiar_de_alerta_nivel_1(self):
        quadro = pd.DataFrame({'TSA_DHW': [0.0, 3.9, 4.0, 8.0]})

        previsto = gcbd.prever_regra_noaa(quadro)

        self.assertEqual(list(previsto), [0, 0, 1, 1])

    def test_dhw_ausente_nao_vira_alerta(self):
        """NaN nao pode virar alerta - seria alarme sobre ausencia de dado."""
        quadro = pd.DataFrame({'TSA_DHW': [np.nan, 5.0]})

        self.assertEqual(list(gcbd.prever_regra_noaa(quadro)), [0, 1])


class ValidarTests(SimpleTestCase):
    """Usa um conjunto sintetico: o CSV real nao e versionado."""

    def _conjunto(self, n_sitios=20, por_sitio=3):
        """Conjunto sintetico em que **`TSA_DHW` e quem gera o alvo**.

        ⚠️ O ruido no `tsa` nao e enfeite. Ate 27/07/2026 este gerador fazia
        `tsa = dhw / 4` exato, o que torna as duas colunas **perfeitamente
        colineares**. Enquanto o conjunto interpretavel tinha uma terceira
        coluna isso passou despercebido; ao reduzi-lo para (`TSA_DHW`, `TSA`),
        a importancia por permutacao passou a atribuir o credito a qualquer uma
        das duas - e o teste quebrou.

        Colinearidade perfeita torna a pergunta "qual coluna importa mais"
        indefinida, e nao errada. E o mesmo fenomeno que docs/RESULTADOS.md
        secao 12 mede no dado real, aqui reproduzido por acidente no fixture.
        """
        gerador = np.random.default_rng(42)
        linhas = []
        for site in range(n_sitios):
            for k in range(por_sitio):
                dhw = float(gerador.uniform(0, 8))
                # Relacao real e monotona, para o modelo ter o que aprender.
                pb = 20.0 if dhw > 4 else 0.0
                linhas.append(visita(
                    site, f'{2000 + k}-06-15', pb, dhw=dhw,
                    tsa=dhw / 4 + float(gerador.normal(0, 0.6)),
                    vento=float(gerador.uniform(3, 9)),
                ))
        quadro = gcbd.agregar_por_visita(pd.DataFrame(linhas))
        quadro['alvo'] = (quadro['Percent_Bleaching'] > 0).astype(int)
        return gcbd.ConjuntoGCBD(
            quadro=quadro, features=gcbd.FEATURES_INTERPRETAVEIS, limiar=0.0,
        )

    def test_o_mesmo_sitio_nunca_cai_nos_dois_lados(self):
        """A garantia central da validacao agrupada."""
        from sklearn.model_selection import GroupKFold

        conjunto = self._conjunto()
        quadro = conjunto.quadro
        X = quadro[list(conjunto.features)]
        grupos = quadro['Site_ID']

        for treino, teste in GroupKFold(n_splits=5).split(X, quadro['alvo'], grupos):
            self.assertEqual(
                set(grupos.iloc[treino]) & set(grupos.iloc[teste]), set(),
                'um sitio apareceu no treino e no teste',
            )

    def test_validacao_por_sitio_roda_e_avalia_todas_as_visitas(self):
        conjunto = self._conjunto()

        resultado = gcbd.validar(conjunto, agrupar_por='sitio', n_dobras=5)

        self.assertEqual(len(resultado.verdadeiro), conjunto.n)
        self.assertGreater(resultado.pr_auc, resultado.taxa_base)

    def test_validacao_por_ano_roda(self):
        resultado = gcbd.validar(self._conjunto(), agrupar_por='ano', n_dobras=3)

        self.assertGreater(resultado.n_dobras, 0)

    def test_agrupamento_desconhecido_e_recusado(self):
        with self.assertRaises(ValueError):
            gcbd.validar(self._conjunto(), agrupar_por='estacao')

    def test_um_grupo_so_nao_valida(self):
        conjunto = self._conjunto(n_sitios=1, por_sitio=6)

        with self.assertRaises(ValueError) as contexto:
            gcbd.validar(conjunto, agrupar_por='sitio')

        self.assertIn('grupo', str(contexto.exception))

    def test_ganho_sobre_acaso_e_relativo_a_taxa_base(self):
        """PR-AUC de 0,53 com 53% de positivos nao e resultado nenhum."""
        resultado = gcbd.ResultadoValidacao(
            modelo='x', agrupamento='sitio', n_dobras=5,
            pr_auc=0.530, taxa_base=0.530,
        )

        self.assertAlmostEqual(resultado.ganho_sobre_acaso, 1.0)


class ImportanciaTests(SimpleTestCase):
    def test_o_fixture_nao_e_perfeitamente_colinear(self):
        """Guarda do proprio teste seguinte.

        Se `TSA` voltar a ser funcao exata de `TSA_DHW`, a pergunta "qual
        importa mais" fica indefinida e o teste abaixo passa ou falha por
        sorte. Melhor descobrir aqui, com a mensagem certa.
        """
        quadro = ValidarTests()._conjunto().quadro

        self.assertLess(abs(quadro['TSA_DHW'].corr(quadro['TSA'])), 0.95)

    def test_a_variavel_que_gera_o_alvo_e_a_mais_importante(self):
        conjunto = ValidarTests()._conjunto()

        importancia = gcbd.medir_importancia(
            conjunto, agrupar_por='sitio', repeticoes=3, n_dobras=3
        )

        mais_importante = max(importancia.por_coluna.items(), key=lambda p: p[1])
        self.assertEqual(mais_importante[0], 'TSA_DHW')

    def test_coeficiente_do_dhw_e_positivo(self):
        """Estresse termico acumulado tem que aumentar o risco, nao diminuir."""
        conjunto = ValidarTests()._conjunto()

        importancia = gcbd.medir_importancia(
            conjunto, agrupar_por='sitio', repeticoes=2, n_dobras=3
        )

        self.assertGreater(importancia.coeficientes['TSA_DHW'], 0)


class CaminhoTests(SimpleTestCase):
    def test_argumento_vence_o_ambiente(self):
        self.assertEqual(
            gcbd.caminho_do_csv('/tmp/x.csv').name, 'x.csv'
        )

    def test_arquivo_ausente_diz_como_obter(self):
        with self.assertRaises(gcbd.ArquivoAusente) as contexto:
            gcbd.carregar(caminho='/nao/existe/gcbd.csv')

        mensagem = str(contexto.exception)
        self.assertIn('docs/GCBD.md', mensagem)
        self.assertIn('GCBD_CSV', mensagem)
