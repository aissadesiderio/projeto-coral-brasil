"""O que estes testes travam.

🚨 **Cache errado nao aparece como erro — aparece como resposta desatualizada
com cara de atual.** E o painel e o unico endpoint do projeto que *afirma
risco*. Um item servido de um calculo anterior a ingestao de hoje diz "risco
baixo" com a mesma confianca que o valor certo.

Por isso os testes aqui sao quase todos sobre **invalidacao**: cada coisa que
pode mudar a resposta precisa mudar a chave. O teste que garante o ganho de
desempenho e um so; os outros seis garantem que o ganho nao foi comprado com
mentira.
"""

from datetime import date

from django.core.cache import caches
from django.test import SimpleTestCase, TestCase, override_settings

import memoria
from aquaculture.models import LocalRecife, MedicaoAmbiental


class ChaveTests(SimpleTestCase):
    def test_partes_diferentes_dao_chaves_diferentes(self):
        self.assertNotEqual(memoria.chave('painel', 'a'), memoria.chave('painel', 'b'))

    def test_mesma_entrada_da_a_mesma_chave(self):
        self.assertEqual(
            memoria.chave('painel', 'a', {'x': 1}),
            memoria.chave('painel', 'a', {'x': 1}),
        )

    def test_ordem_de_dicionario_nao_muda_a_chave(self):
        """Senao a chave dependeria da ordem de insercao, que e detalhe de
        implementacao - e o cache erraria de forma intermitente."""
        self.assertEqual(
            memoria.chave('painel', {'a': 1, 'b': 2}),
            memoria.chave('painel', {'b': 2, 'a': 1}),
        )

    def test_nao_contem_espaco(self):
        """O memcached recusa chave com espaco; `data_base` e listas de colunas
        entrariam cheias deles se a chave fosse concatenacao."""
        gerada = memoria.chave('painel', 'abrolhos-ba', (date(2026, 8, 11), 19278))
        self.assertNotIn(' ', gerada)
        self.assertTrue(gerada.startswith('coral:painel:'))


class LembrarTests(SimpleTestCase):
    def setUp(self):
        caches['default'].clear()

    def test_calcula_uma_vez_e_reaproveita(self):
        chamadas = []

        def calcular():
            chamadas.append(1)
            return {'valor': 42}

        chave = memoria.chave('teste', 'a')
        self.assertEqual(memoria.lembrar(chave, calcular), {'valor': 42})
        self.assertEqual(memoria.lembrar(chave, calcular), {'valor': 42})
        self.assertEqual(len(chamadas), 1)

    def test_chave_diferente_recalcula(self):
        chamadas = []

        def calcular():
            chamadas.append(1)
            return 1

        memoria.lembrar(memoria.chave('teste', 'a'), calcular)
        memoria.lembrar(memoria.chave('teste', 'b'), calcular)
        self.assertEqual(len(chamadas), 2)

    def test_cache_quebrado_nao_derruba_a_requisicao(self):
        """⚠️ O painel funcionava sem cache ate ontem.

        Se um Redis fora do ar passasse a produzir 500, a otimizacao teria
        tornado o sistema menos disponivel do que antes dela.
        """
        class Quebrado:
            def get(self, chave):
                raise RuntimeError('redis fora do ar')

            def set(self, chave, valor, ttl):
                raise RuntimeError('redis fora do ar')

        resultado = memoria.lembrar(
            memoria.chave('teste', 'a'), lambda: 'calculado', backend=Quebrado()
        )
        self.assertEqual(resultado, 'calculado')


class AssinaturaTests(TestCase):
    def setUp(self):
        self.local, _ = LocalRecife.objects.get_or_create(
            slug='abrolhos-ba',
            defaults={
                'nome': 'Abrolhos', 'estado': 'BA', 'cidade': 'Caravelas',
                'latitude': -17.972, 'longitude': -38.688, 'ativo': True,
            },
        )
        MedicaoAmbiental.objects.filter(local_recife=self.local).delete()

    def _medir(self, dia, variavel='sst'):
        return MedicaoAmbiental.objects.create(
            local_recife=self.local, data=dia, variavel=variavel, valor=27.0,
            unidade='degree_C', fonte='noaa_crw', dataset_id='dhw_5km',
        )

    def test_medicao_nova_muda_a_assinatura(self):
        self._medir(date(2026, 1, 1))
        antes = memoria.assinatura_das_series(['abrolhos-ba'])['abrolhos-ba']

        self._medir(date(2026, 1, 2))
        depois = memoria.assinatura_das_series(['abrolhos-ba'])['abrolhos-ba']

        self.assertNotEqual(antes, depois)

    def test_backfill_de_data_antiga_muda_a_assinatura(self):
        """🚨 O caso que o `MAX` sozinho nao pega.

        Preencher um buraco de 2020 nao mexe na data maxima. Sem o `COUNT`, o
        painel continuaria servindo o resultado calculado **antes** de o buraco
        ser preenchido, e nada indicaria isso.
        """
        self._medir(date(2026, 1, 10))
        antes = memoria.assinatura_das_series(['abrolhos-ba'])['abrolhos-ba']

        self._medir(date(2020, 3, 2))
        depois = memoria.assinatura_das_series(['abrolhos-ba'])['abrolhos-ba']

        self.assertEqual(antes[0], depois[0], 'a data maxima nao mudou mesmo')
        self.assertNotEqual(antes, depois, 'mas a assinatura precisava mudar')

    def test_serie_intacta_mantem_a_assinatura(self):
        """Sem isto o cache nunca acertaria - toda requisicao recalcularia."""
        self._medir(date(2026, 1, 1))
        self.assertEqual(
            memoria.assinatura_das_series(['abrolhos-ba']),
            memoria.assinatura_das_series(['abrolhos-ba']),
        )

    def test_uma_consulta_para_todos_os_locais(self):
        """⚠️ Uma agregacao por local trocaria 30 ms de pandas por N consultas -
        mais barato, e ainda linear no numero de recifes."""
        outro, _ = LocalRecife.objects.get_or_create(
            slug='picaozinho-pb',
            defaults={
                'nome': 'Picaozinho', 'estado': 'PB', 'cidade': 'Joao Pessoa',
                'latitude': -7.1, 'longitude': -34.8, 'ativo': True,
            },
        )
        self._medir(date(2026, 1, 1))
        MedicaoAmbiental.objects.create(
            local_recife=outro, data=date(2026, 1, 1), variavel='sst',
            valor=28.0, unidade='degree_C', fonte='noaa_crw',
        )

        with self.assertNumQueries(1):
            assinaturas = memoria.assinatura_das_series(
                ['abrolhos-ba', 'picaozinho-pb']
            )
        self.assertEqual(len(assinaturas), 2)

    def test_local_sem_serie_fica_de_fora(self):
        """Quem nao tem medicao nao tem assinatura - e `avaliar` sem assinatura
        calcula sempre, que e o comportamento certo."""
        self.assertEqual(memoria.assinatura_das_series(['abrolhos-ba']), {})
