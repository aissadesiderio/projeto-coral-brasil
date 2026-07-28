"""Testes da varredura de limiar.

O que protegem, em ordem de gravidade:

1. 🚨 **"Nenhum limiar pega todos os episodios" precisa aparecer como tal.**
   Se `sem_perder_episodio` devolvesse o limiar mais baixo em vez de `None`, a
   tabela sugeriria que basta baixar o corte — e na medicao real **nao basta**.
2. **As contagens viram unidade operacional sem distorcer.** "Precisao 0,719"
   nao e uma frase sobre a qual alguem decide; "10 dias de alarme falso por ano
   e por recife" e — desde que a divisao esteja certa.
3. **Episodio nao e dia.** Um limiar pode perder muitos dias e ainda pegar
   todos os eventos, e e o evento que importa para avisar.
"""

from datetime import date

from django.test import SimpleTestCase

from ml.limiar import LIMIARES_PADRAO, Ponto, Varredura, _matriz


def ponto(limiar=0.5, vp=10, fp=5, fn=2, vn=83, **extras):
    return Ponto(
        limiar=limiar, verdadeiros_positivos=vp, falsos_positivos=fp,
        falsos_negativos=fn, verdadeiros_negativos=vn, **extras,
    )


class MatrizTests(SimpleTestCase):
    def test_conta_os_quatro_casos(self):
        import numpy as np

        y = np.array([1, 1, 0, 0])
        p = np.array([0.9, 0.1, 0.8, 0.2])

        self.assertEqual(_matriz(y, p, 0.5), (1, 1, 1, 1))

    def test_o_limiar_e_inclusivo(self):
        """Coerente com o `alerta` do servidor, que usa `>=`."""
        import numpy as np

        vp, _, fn, _ = _matriz(np.array([1]), np.array([0.2]), 0.2)

        self.assertEqual((vp, fn), (1, 0))


class PontoTests(SimpleTestCase):
    def test_precisao_e_revocacao(self):
        p = ponto(vp=10, fp=5, fn=2)

        self.assertAlmostEqual(p.precisao, 10 / 15)
        self.assertAlmostEqual(p.revocacao, 10 / 12)

    def test_sem_alerta_nenhum_a_precisao_e_zero_e_nao_erro(self):
        """Limiar alto demais nao pode quebrar a tabela."""
        p = ponto(vp=0, fp=0)

        self.assertEqual(p.precisao, 0.0)

    def test_alertas_e_a_soma_dos_dias_avisados(self):
        self.assertEqual(ponto(vp=10, fp=5).alertas, 15)

    def test_por_ano_divide_por_anos_e_locais(self):
        """🚨 A unidade em que a decisao existe de fato."""
        p = ponto(vp=10, fp=42, fn=14)

        ano = p.por_ano(anos=7, locais=3)

        self.assertAlmostEqual(ano['dias_de_alarme_falso'], 2.0)
        self.assertAlmostEqual(ano['dias_de_evento_perdidos'], 14 / 21)

    def test_por_ano_sem_contexto_nao_inventa_numero(self):
        self.assertEqual(ponto().por_ano(anos=0, locais=3), {})

    def test_episodios_perdidos_e_a_diferenca(self):
        p = ponto(episodios_reais=19, episodios_detectados=16)

        self.assertEqual(p.episodios_perdidos, 3)


class VarreduraTests(SimpleTestCase):
    def varredura(self, pontos):
        return Varredura(
            pontos=tuple(pontos), n=7095, positivos=596, anos=7, locais=3
        )

    def test_taxa_base(self):
        self.assertAlmostEqual(self.varredura([]).taxa_base, 596 / 7095, 4)

    def test_melhor_f1(self):
        v = self.varredura([
            ponto(limiar=0.2, vp=10, fp=10, fn=1),
            ponto(limiar=0.5, vp=10, fp=1, fn=1),
        ])

        self.assertEqual(v.melhor_f1().limiar, 0.5)

    def test_sem_perder_episodio_pega_o_limiar_mais_alto_completo(self):
        v = self.varredura([
            ponto(limiar=0.2, episodios_reais=19, episodios_detectados=19),
            ponto(limiar=0.4, episodios_reais=19, episodios_detectados=19),
            ponto(limiar=0.6, episodios_reais=19, episodios_detectados=17),
        ])

        self.assertEqual(v.sem_perder_episodio().limiar, 0.4)

    def test_sem_perder_episodio_devolve_none_quando_nao_existe(self):
        """🚨 O caso real, e o que ele nao pode virar.

        Na medicao de 27/07/2026 nenhum limiar pega os 19 episodios. Se esta
        funcao devolvesse "o melhor disponivel", a tabela sugeriria que basta
        baixar o corte — e nao basta: um episodio escapa em todos.
        """
        v = self.varredura([
            ponto(limiar=0.2, episodios_reais=19, episodios_detectados=18),
            ponto(limiar=0.4, episodios_reais=19, episodios_detectados=16),
        ])

        self.assertIsNone(v.sem_perder_episodio())

    def test_melhor_cobertura_desempata_pelo_limiar_mais_alto(self):
        """Entre limiares que perdem os mesmos eventos, o mais baixo e dominado."""
        v = self.varredura([
            ponto(limiar=0.15, episodios_reais=19, episodios_detectados=16),
            ponto(limiar=0.20, episodios_reais=19, episodios_detectados=16),
            ponto(limiar=0.50, episodios_reais=19, episodios_detectados=14),
        ])

        self.assertEqual(v.melhor_cobertura().limiar, 0.20)

    def test_nunca_detectados_e_a_intersecao(self):
        """Separa o que nenhum limiar resolve do que so o limiar alto perde."""
        sempre = {'local': 'picaozinho-pb', 'inicio': date(2026, 4, 21),
                  'fim': date(2026, 4, 23), 'dias': 3}
        as_vezes = {'local': 'porto-de-galinhas-pe', 'inicio': date(2020, 5, 7),
                    'fim': date(2020, 5, 7), 'dias': 1}

        v = self.varredura([
            ponto(limiar=0.05, perdidos=(sempre,)),
            ponto(limiar=0.50, perdidos=(sempre, as_vezes)),
        ])

        nunca = v.nunca_detectados()

        self.assertEqual(len(nunca), 1)
        self.assertEqual(nunca[0]['local'], 'picaozinho-pb')

    def test_nunca_detectados_vazio_quando_todo_evento_e_pego_em_algum_limiar(self):
        perdido = {'local': 'x', 'inicio': date(2022, 1, 1),
                   'fim': date(2022, 1, 2), 'dias': 2}

        v = self.varredura([
            ponto(limiar=0.05, perdidos=()),
            ponto(limiar=0.50, perdidos=(perdido,)),
        ])

        self.assertEqual(v.nunca_detectados(), ())

    def test_em_acha_o_limiar_pedido(self):
        v = self.varredura([ponto(limiar=0.2), ponto(limiar=0.3)])

        self.assertEqual(v.em(0.2).limiar, 0.2)
        self.assertIsNone(v.em(0.99))


class LimiaresPadraoTests(SimpleTestCase):
    def test_cobrem_a_faixa_util(self):
        self.assertEqual(LIMIARES_PADRAO[0], 0.05)
        self.assertEqual(LIMIARES_PADRAO[-1], 0.95)

    def test_incluem_o_limiar_em_uso(self):
        """Sem ele na tabela, nao da para comparar o atual com as alternativas."""
        self.assertIn(0.20, LIMIARES_PADRAO)

    def test_incluem_o_meio_termo_historico(self):
        self.assertIn(0.50, LIMIARES_PADRAO)
