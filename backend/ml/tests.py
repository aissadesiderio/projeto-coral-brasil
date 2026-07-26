"""Testes da montagem do conjunto supervisionado e da linha de base.

O que estes testes protegem, em ordem de gravidade: que o horizonte seja mesmo
em dias e nao em posicoes (a lacuna do CRW e real e faria `shift` mentir), que
nenhuma variavel derivada do alvo entre como feature, e que a metrica por
episodio nao seja confundida com a metrica por dia.
"""

from datetime import date, timedelta

import pandas as pd
from django.test import TestCase

from aquaculture.models import LocalRecife, MedicaoAmbiental
from ml.baseline import (
    agrupar_episodios,
    avaliar,
    avaliar_episodios,
    avaliar_persistencia,
    dividir_deixando_um_ano_de_fora,
    prever_persistencia,
)
from ml.dataset import (
    FeatureComVazamento,
    carregar_largo,
    montar,
    montar_todos,
)

FEATURES = ('sst', 'dhw')
UNIDADES = {'sst': '°C', 'dhw': '°C·semana', 'baa': 'categoria'}


def gravar(local, data, valores, fonte='noaa_crw'):
    for variavel, valor in valores.items():
        MedicaoAmbiental.objects.create(
            local_recife=local, data=data, variavel=variavel, valor=valor,
            unidade=UNIDADES.get(variavel, ''), fonte=fonte, quality_flag='ok',
        )


def serie(local, inicio, dias, baa=lambda i: 0, pular=(), fonte='noaa_crw'):
    """Serie diaria sintetica. `pular` simula as datas ausentes do produto."""
    for i in range(dias):
        data = inicio + timedelta(days=i)
        if data in pular:
            continue
        gravar(local, data, {'sst': 28.0 + i * 0.01, 'dhw': float(i) / 10,
                             'baa': float(baa(i))}, fonte)


class MontagemTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-ml', nome='ML', estado='Bahia', cidade='Caravelas',
            latitude=-17.972, longitude=-38.688,
        )

    def test_alvo_vem_do_futuro_e_features_do_presente(self):
        serie(self.local, date(2024, 1, 1), 20, baa=lambda i: i % 5)

        conjunto = montar(self.local, horizonte=7, features=FEATURES)
        linha = conjunto.quadro.iloc[0]

        self.assertEqual(linha['data'], date(2024, 1, 1))
        self.assertEqual(linha['alvo_data'], date(2024, 1, 8))
        self.assertEqual(linha['alvo'], 7 % 5)
        self.assertEqual(linha['alvo_atual'], 0)

    def test_horizonte_e_em_dias_e_nao_em_posicoes(self):
        """A regressao mais perigosa deste modulo.

        Com uma data faltando, deslocar por posicao pareia t com t+8 e grava
        isso como horizonte 7 - um horizonte que nunca existiu.
        """
        buraco = date(2024, 1, 10)
        serie(self.local, date(2024, 1, 1), 20, baa=lambda i: i, pular={buraco})

        conjunto = montar(self.local, horizonte=7, features=FEATURES)

        for linha in conjunto.quadro.itertuples():
            self.assertEqual(
                (linha.alvo_data - linha.data).days, 7,
                'o alvo precisa estar exatamente 7 dias a frente',
            )

    def test_amostra_cujo_alvo_caiu_na_lacuna_e_descartada(self):
        buraco = date(2024, 1, 10)
        serie(self.local, date(2024, 1, 1), 20, pular={buraco})

        conjunto = montar(self.local, horizonte=7, features=FEATURES)

        datas = set(conjunto.quadro['data'])
        self.assertNotIn(date(2024, 1, 3), datas)  # alvo cairia em 10/01
        self.assertNotIn(buraco, datas)            # sem feature em t

    def test_lacuna_nao_e_interpolada(self):
        """Interpolar o alvo seria ensinar o modelo a prever a interpolacao."""
        buraco = date(2024, 1, 10)
        serie(self.local, date(2024, 1, 1), 20, baa=lambda i: i, pular={buraco})

        conjunto = montar(self.local, horizonte=1, features=FEATURES)

        alvos = dict(zip(conjunto.quadro['alvo_data'], conjunto.quadro['alvo']))
        self.assertNotIn(buraco, alvos)

    def test_valor_nulo_de_feature_descarta_a_amostra(self):
        """Reprovado na validacao fisica vira NULL, e NULL nao vira zero."""
        serie(self.local, date(2024, 1, 1), 10)
        MedicaoAmbiental.objects.filter(
            data=date(2024, 1, 3), variavel='sst'
        ).update(valor=None, quality_flag='invalido')

        conjunto = montar(self.local, horizonte=1, features=FEATURES)

        self.assertNotIn(date(2024, 1, 3), set(conjunto.quadro['data']))
        self.assertEqual(conjunto.descartadas_sem_feature, 1)

    def test_contagens_explicam_o_que_foi_descartado(self):
        serie(self.local, date(2024, 1, 1), 10)

        conjunto = montar(self.local, horizonte=3, features=FEATURES)

        self.assertEqual(conjunto.dias_na_serie, 10)
        self.assertEqual(conjunto.descartadas_sem_alvo, 3)  # os 3 ultimos dias
        self.assertEqual(conjunto.n, 7)
        self.assertIn('horizonte 3d', conjunto.resumo())

    def test_serie_vazia_nao_quebra(self):
        conjunto = montar(self.local, horizonte=7, features=FEATURES)

        self.assertEqual(conjunto.n, 0)

    def test_horizonte_zero_e_recusado(self):
        with self.assertRaises(ValueError):
            montar(self.local, horizonte=0, features=FEATURES)

    def test_mesma_variavel_em_duas_fontes_falha_alto(self):
        """Escolher em silencio esconderia mistura de produtos."""
        serie(self.local, date(2024, 1, 1), 5)
        gravar(self.local, date(2024, 1, 1), {'sst': 27.0}, fonte='copernicus')

        with self.assertRaises(ValueError) as ctx:
            montar(self.local, horizonte=1, features=FEATURES)

        self.assertIn('mais de uma fonte', str(ctx.exception))

    def test_reindex_torna_a_lacuna_visivel(self):
        serie(self.local, date(2024, 1, 1), 5, pular={date(2024, 1, 3)})

        largo, _ = carregar_largo(self.local, ('sst', 'baa'))

        self.assertEqual(len(largo), 5)
        self.assertTrue(pd.isna(largo.loc[date(2024, 1, 3), 'sst']))


class VazamentoTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-vazamento', nome='Vaz', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )

    def test_hotspot_e_recusado_como_feature(self):
        with self.assertRaises(FeatureComVazamento) as ctx:
            montar(self.local, 7, features=('sst', 'hotspot'))

        self.assertIn('determina o BAA', str(ctx.exception))

    def test_area_de_alerta_e_recusada_como_feature(self):
        with self.assertRaises(FeatureComVazamento):
            montar(self.local, 7, features=('sst', 'baa_area_alerta'))

    def test_o_proprio_alvo_e_recusado_como_feature(self):
        with self.assertRaises(FeatureComVazamento):
            montar(self.local, 7, features=('sst', 'baa'))

    def test_alvo_atual_existe_mas_nao_esta_entre_as_features(self):
        serie(self.local, date(2024, 1, 1), 10)

        conjunto = montar(self.local, horizonte=3, features=FEATURES)

        self.assertIn('alvo_atual', conjunto.quadro.columns)
        self.assertNotIn('alvo_atual', conjunto.features)


class PersistenciaTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-baseline', nome='Base', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )

    def test_persistencia_repete_o_valor_de_hoje(self):
        serie(self.local, date(2024, 1, 1), 20, baa=lambda i: i % 5)

        conjunto = montar(self.local, horizonte=7, features=FEATURES)
        previsto = prever_persistencia(conjunto.quadro)

        pd.testing.assert_series_equal(
            previsto, conjunto.quadro['alvo_atual'], check_names=False
        )

    def test_acuracia_alta_com_zero_alerta_detectado(self):
        """O motivo de a acuracia nao poder ser reportada sozinha."""
        verdadeiro = pd.Series([0] * 95 + [4] * 5)
        previsto = pd.Series([0] * 100)

        d = avaliar(verdadeiro, previsto)

        self.assertAlmostEqual(d.acerto_exato, 0.95)
        self.assertAlmostEqual(d.taxa_majoritaria, 0.95)
        self.assertEqual(d.revocacao_alerta, 0.0)
        self.assertEqual(d.falsos_negativos, 5)

    def test_alerta_e_contado_a_partir_do_nivel_3(self):
        d = avaliar(pd.Series([2, 3]), pd.Series([3, 3]))

        self.assertEqual(d.falsos_positivos, 1)   # previu 3 onde era 2
        self.assertEqual(d.verdadeiros_positivos, 1)

    def test_sem_alerta_previsto_a_precisao_e_zero_e_nao_erro(self):
        d = avaliar(pd.Series([0, 0]), pd.Series([0, 0]))

        self.assertEqual(d.precisao_alerta, 0.0)
        self.assertEqual(d.f1_alerta, 0.0)


class EpisodioTests(TestCase):
    def test_agrupa_dias_contiguos(self):
        datas = [date(2024, 3, 1), date(2024, 3, 2), date(2024, 5, 1)]

        episodios = agrupar_episodios(datas)

        self.assertEqual(len(episodios), 2)
        self.assertEqual(len(episodios[0]), 2)

    def test_folga_de_ate_tres_dias_nao_parte_o_episodio(self):
        """Uma lacuna do produto nao deveria virar dois eventos."""
        datas = [date(2024, 3, 1), date(2024, 3, 4)]

        self.assertEqual(len(agrupar_episodios(datas)), 1)

    def test_folga_maior_parte(self):
        datas = [date(2024, 3, 1), date(2024, 3, 10)]

        self.assertEqual(len(agrupar_episodios(datas)), 2)

    def test_um_dia_acertado_ja_detecta_o_episodio(self):
        """Errar o dia exato importa menos que perder o evento."""
        quadro = pd.DataFrame(
            {
                'alvo_data': [date(2024, 3, d) for d in range(1, 11)],
                'alvo': [4] * 10,
            }
        )
        previsto = pd.Series([0] * 9 + [4])

        d = avaliar_episodios(quadro, previsto)

        self.assertEqual(d.episodios_reais, 1)
        self.assertEqual(d.episodios_detectados, 1)
        self.assertEqual(d.detalhes[0]['dias_previstos'], 1)

    def test_episodio_totalmente_perdido_nao_conta_como_detectado(self):
        quadro = pd.DataFrame(
            {
                'alvo_data': [date(2024, 3, d) for d in range(1, 6)],
                'alvo': [4] * 5,
            }
        )

        d = avaliar_episodios(quadro, pd.Series([0] * 5))

        self.assertEqual(d.episodios_detectados, 0)
        self.assertEqual(d.taxa_deteccao, 0.0)

    def test_alarme_falso_e_episodio_previsto_sem_evento_real(self):
        quadro = pd.DataFrame(
            {
                'alvo_data': [date(2024, 3, d) for d in range(1, 11)],
                'alvo': [0] * 10,
            }
        )
        previsto = pd.Series([0, 0, 4, 4, 0, 0, 0, 0, 0, 0])

        d = avaliar_episodios(quadro, previsto)

        self.assertEqual(d.episodios_reais, 0)
        self.assertEqual(d.episodios_falsos, 1)

    def test_episodios_simultaneos_em_locais_diferentes_nao_se_fundem(self):
        """Regressao real: sem agrupar por local, 19 episodios viraram 7.

        Os eventos caem nos mesmos dias nos tres recifes - agrupar so por data
        conta um evento onde ha tres.
        """
        dias = [date(2024, 3, d) for d in range(1, 6)]
        quadro = pd.DataFrame(
            {
                'local': ['a'] * 5 + ['b'] * 5,
                'alvo_data': dias + dias,
                'alvo': [4] * 10,
            }
        )

        d = avaliar_episodios(quadro, pd.Series([4] * 10))

        self.assertEqual(d.episodios_reais, 2)
        self.assertEqual(d.episodios_detectados, 2)
        self.assertEqual({x['local'] for x in d.detalhes}, {'a', 'b'})

    def test_acerto_num_local_nao_credita_o_outro(self):
        dias = [date(2024, 3, d) for d in range(1, 6)]
        quadro = pd.DataFrame(
            {
                'local': ['a'] * 5 + ['b'] * 5,
                'alvo_data': dias + dias,
                'alvo': [4] * 10,
            }
        )
        # So o local "a" foi previsto em alerta.
        previsto = pd.Series([4] * 5 + [0] * 5)

        d = avaliar_episodios(quadro, previsto)

        self.assertEqual(d.episodios_reais, 2)
        self.assertEqual(d.episodios_detectados, 1)

    def test_quadro_sem_coluna_local_continua_funcionando(self):
        quadro = pd.DataFrame(
            {'alvo_data': [date(2024, 3, d) for d in range(1, 6)], 'alvo': [4] * 5}
        )

        d = avaliar_episodios(quadro, pd.Series([4] * 5))

        self.assertEqual(d.episodios_reais, 1)

    def test_dia_extra_dentro_de_evento_real_nao_e_alarme_falso(self):
        quadro = pd.DataFrame(
            {
                'alvo_data': [date(2024, 3, d) for d in range(1, 6)],
                'alvo': [0, 4, 4, 4, 0],
            }
        )
        previsto = pd.Series([4, 4, 4, 4, 0])

        d = avaliar_episodios(quadro, previsto)

        self.assertEqual(d.episodios_falsos, 0)


class DivisaoTemporalTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-divisao', nome='Div', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )

    def test_ano_de_teste_sai_inteiro_do_treino(self):
        serie(self.local, date(2023, 12, 1), 90, baa=lambda i: i % 5)

        conjunto = montar(self.local, horizonte=7, features=FEATURES)
        treino, teste = dividir_deixando_um_ano_de_fora(conjunto.quadro, 2024)

        self.assertTrue(all(d.year != 2024 for d in treino['alvo_data']))
        self.assertTrue(all(d.year == 2024 for d in teste['alvo_data']))
        self.assertEqual(len(treino) + len(teste), len(conjunto.quadro))

    def test_divisao_usa_a_data_do_alvo_e_nao_a_das_features(self):
        """O que define a dobra e o dia sobre o qual a previsao fala."""
        serie(self.local, date(2023, 12, 28), 10, baa=lambda i: 1)

        conjunto = montar(self.local, horizonte=7, features=FEATURES)
        _, teste = dividir_deixando_um_ano_de_fora(conjunto.quadro, 2024)

        self.assertTrue(all(d.year == 2023 for d in teste['data']))
        self.assertTrue(all(d.year == 2024 for d in teste['alvo_data']))


class ConjuntoMultiLocalTests(TestCase):
    def test_empilha_locais_com_coluna_de_origem(self):
        locais = []
        for slug in ('a-ml', 'b-ml'):
            local = LocalRecife.objects.create(
                slug=slug, nome=slug, estado='Bahia', cidade='Caravelas',
                latitude=-17.9, longitude=-38.6,
            )
            serie(local, date(2024, 1, 1), 15)
            locais.append(local)

        conjunto = montar_todos(locais, horizonte=7, features=FEATURES)

        self.assertEqual(set(conjunto.quadro['local']), {'a-ml', 'b-ml'})
        self.assertEqual(conjunto.n, 16)

    def test_persistencia_roda_ponta_a_ponta(self):
        local = LocalRecife.objects.create(
            slug='ponta-a-ponta', nome='PP', estado='Bahia',
            cidade='Caravelas', latitude=-17.9, longitude=-38.6,
        )
        serie(local, date(2024, 1, 1), 60, baa=lambda i: 4 if 20 <= i < 40 else 0)

        conjunto = montar(local, horizonte=7, features=FEATURES)
        diario, episodio = avaliar_persistencia(conjunto)

        self.assertEqual(diario.n, conjunto.n)
        self.assertEqual(episodio.episodios_reais, 1)
        self.assertEqual(episodio.episodios_detectados, 1)
