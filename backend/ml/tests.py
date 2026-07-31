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
    CORTE_DHW_ALERTA_1,
    agrupar_episodios,
    avaliar,
    avaliar_episodios,
    avaliar_persistencia,
    dividir_deixando_um_ano_de_fora,
    escolher_corte_dhw,
    prever_persistencia,
    prever_regra_noaa,
)
from ml.dataset import (
    JANELAS_PADRAO,
    VARIAVEIS_DE_LINHA_DE_BASE,
    FeatureComVazamento,
    Janela,
    aplicar_janela,
    carregar_largo,
    janelas_para,
    montar,
    montar_todos,
)

FEATURES = ('sst', 'dhw')
UNIDADES = {
    'sst': '°C', 'dhw': '°C·semana', 'baa': 'categoria', 'hotspot': '°C',
}


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

        conjunto = montar(self.local, horizonte=7, features=FEATURES, janelas=())
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

        conjunto = montar(self.local, horizonte=7, features=FEATURES, janelas=())

        for linha in conjunto.quadro.itertuples():
            self.assertEqual(
                (linha.alvo_data - linha.data).days, 7,
                'o alvo precisa estar exatamente 7 dias a frente',
            )

    def test_amostra_cujo_alvo_caiu_na_lacuna_e_descartada(self):
        buraco = date(2024, 1, 10)
        serie(self.local, date(2024, 1, 1), 20, pular={buraco})

        conjunto = montar(self.local, horizonte=7, features=FEATURES, janelas=())

        datas = set(conjunto.quadro['data'])
        self.assertNotIn(date(2024, 1, 3), datas)  # alvo cairia em 10/01
        self.assertNotIn(buraco, datas)            # sem feature em t

    def test_lacuna_nao_e_interpolada(self):
        """Interpolar o alvo seria ensinar o modelo a prever a interpolacao."""
        buraco = date(2024, 1, 10)
        serie(self.local, date(2024, 1, 1), 20, baa=lambda i: i, pular={buraco})

        conjunto = montar(self.local, horizonte=1, features=FEATURES, janelas=())

        alvos = dict(zip(conjunto.quadro['alvo_data'], conjunto.quadro['alvo']))
        self.assertNotIn(buraco, alvos)

    def test_valor_nulo_de_feature_descarta_a_amostra(self):
        """Reprovado na validacao fisica vira NULL, e NULL nao vira zero."""
        serie(self.local, date(2024, 1, 1), 10)
        MedicaoAmbiental.objects.filter(
            data=date(2024, 1, 3), variavel='sst'
        ).update(valor=None, quality_flag='invalido')

        conjunto = montar(self.local, horizonte=1, features=FEATURES, janelas=())

        self.assertNotIn(date(2024, 1, 3), set(conjunto.quadro['data']))
        self.assertEqual(conjunto.descartadas_sem_feature, 1)

    def test_contagens_explicam_o_que_foi_descartado(self):
        serie(self.local, date(2024, 1, 1), 10)

        conjunto = montar(self.local, horizonte=3, features=FEATURES, janelas=())

        self.assertEqual(conjunto.dias_na_serie, 10)
        self.assertEqual(conjunto.descartadas_sem_alvo, 3)  # os 3 ultimos dias
        self.assertEqual(conjunto.n, 7)
        self.assertIn('horizonte 3d', conjunto.resumo())

    def test_serie_vazia_nao_quebra(self):
        conjunto = montar(self.local, horizonte=7, features=FEATURES, janelas=())

        self.assertEqual(conjunto.n, 0)

    def test_horizonte_zero_e_recusado(self):
        with self.assertRaises(ValueError):
            montar(self.local, horizonte=0, features=FEATURES, janelas=())

    def test_mesma_variavel_em_duas_fontes_falha_alto(self):
        """Escolher em silencio esconderia mistura de produtos."""
        serie(self.local, date(2024, 1, 1), 5)
        gravar(self.local, date(2024, 1, 1), {'sst': 27.0}, fonte='copernicus')

        with self.assertRaises(ValueError) as ctx:
            montar(self.local, horizonte=1, features=FEATURES, janelas=())

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
            montar(self.local, 7, features=('sst', 'hotspot'), janelas=())

        self.assertIn('determina o BAA', str(ctx.exception))

    def test_area_de_alerta_e_recusada_como_feature(self):
        with self.assertRaises(FeatureComVazamento):
            montar(self.local, 7, features=('sst', 'baa_area_alerta'), janelas=())

    def test_o_proprio_alvo_e_recusado_como_feature(self):
        with self.assertRaises(FeatureComVazamento):
            montar(self.local, 7, features=('sst', 'baa'), janelas=())

    def test_alvo_atual_existe_mas_nao_esta_entre_as_features(self):
        serie(self.local, date(2024, 1, 1), 10)

        conjunto = montar(self.local, horizonte=3, features=FEATURES, janelas=())

        self.assertIn('alvo_atual', conjunto.quadro.columns)
        self.assertNotIn('alvo_atual', conjunto.features)


class JanelaTests(TestCase):
    """As janelas olham so para tras, e contam dias - nunca posicoes."""

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-janela', nome='Janela', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )

    def test_variacao_e_a_diferenca_para_n_dias_atras(self):
        # dhw = i/10, entao a variacao em 7 dias e sempre 0,7.
        serie(self.local, date(2024, 1, 1), 30)
        janelas = (Janela('dhw', 7, 'variacao'),)

        conjunto = montar(self.local, 3, features=FEATURES, janelas=janelas)

        valores = conjunto.quadro['dhw_variacao_7d']
        self.assertTrue(all(abs(v - 0.7) < 1e-9 for v in valores))

    def test_variacao_distingue_subida_de_descida(self):
        """A razao de a janela existir: DHW=6 hoje nao diz a direcao."""
        subindo = pd.Series([2.0, 3.0, 4.0, 5.0, 6.0])
        descendo = pd.Series([10.0, 9.0, 8.0, 7.0, 6.0])
        janela = Janela('dhw', 4, 'variacao')

        self.assertEqual(aplicar_janela(subindo, janela).iloc[-1], 4.0)
        self.assertEqual(aplicar_janela(descendo, janela).iloc[-1], -4.0)

    def test_variacao_conta_dias_e_nao_linhas(self):
        """Sem o reindex, `shift(7)` andaria 7 linhas e pularia a lacuna.

        A variação compara dois instantes: basta que `t` e `t-7` existam. Um
        dia faltando no meio não invalida — a diferença entre 11/01 e 04/01
        continua sendo de sete dias. O que não pode é `t-7` virar `t-8`.
        """
        buraco = date(2024, 1, 10)
        serie(self.local, date(2024, 1, 1), 30, pular={buraco})
        janelas = (Janela('dhw', 7, 'variacao'),)

        conjunto = montar(self.local, 3, features=FEATURES, janelas=janelas)

        # dhw = i/10 por construção, então a variação de 7 dias é sempre 0,7 -
        # e só continua sendo se o deslocamento for mesmo de 7 dias.
        for linha in conjunto.quadro.itertuples():
            self.assertAlmostEqual(linha.dhw_variacao_7d, 0.7, places=9)
            self.assertNotEqual(linha.data, buraco)
            self.assertNotEqual(linha.data - timedelta(days=7), buraco)

    def test_media_descarta_amostra_com_lacuna_dentro_da_janela(self):
        """Diferente da variação: média resume todos os dias do intervalo."""
        buraco = date(2024, 1, 10)
        serie(self.local, date(2024, 1, 1), 30, pular={buraco})
        janelas = (Janela('dhw', 7, 'media'),)

        conjunto = montar(self.local, 3, features=FEATURES, janelas=janelas)

        for linha in conjunto.quadro.itertuples():
            dias_da_janela = {linha.data - timedelta(days=k) for k in range(7)}
            self.assertNotIn(buraco, dias_da_janela)

    def test_media_de_janela_incompleta_e_descartada_e_nao_encurtada(self):
        """Uma "media de 7 dias" que fosse de 5 mentiria sobre a cobertura."""
        entrada = pd.Series([1.0, 2.0, float('nan'), 4.0, 5.0, 6.0, 7.0])

        resultado = aplicar_janela(entrada, Janela('sst', 3, 'media'))

        self.assertTrue(pd.isna(resultado.iloc[2]))
        self.assertTrue(pd.isna(resultado.iloc[3]))
        self.assertTrue(pd.isna(resultado.iloc[4]))
        self.assertAlmostEqual(resultado.iloc[5], 5.0)

    def test_janela_nao_enxerga_o_futuro(self):
        """Vazamento seria uma janela centrada ou adiantada."""
        entrada = pd.Series([1.0, 2.0, 3.0, 100.0])

        media = aplicar_janela(entrada, Janela('sst', 3, 'media'))

        # Em t=2 o valor 100 (em t=3) nao pode ter entrado.
        self.assertAlmostEqual(media.iloc[2], 2.0)

    def test_maximo_da_janela(self):
        entrada = pd.Series([1.0, 9.0, 3.0, 2.0])

        maximo = aplicar_janela(entrada, Janela('sst', 3, 'maximo'))

        self.assertEqual(maximo.iloc[2], 9.0)
        self.assertEqual(maximo.iloc[3], 9.0)

    def test_janela_sobre_variavel_proibida_e_recusada(self):
        """Media de 7 dias do HotSpot nao e menos derivada do alvo."""
        with self.assertRaises(FeatureComVazamento) as ctx:
            montar(self.local, 7, features=FEATURES,
                   janelas=(Janela('hotspot', 7, 'media'),))

        self.assertIn('hotspot', str(ctx.exception))

    def test_operacao_desconhecida_e_recusada(self):
        with self.assertRaises(ValueError):
            montar(self.local, 7, features=FEATURES,
                   janelas=(Janela('sst', 7, 'mediana'),))

    def test_janela_pode_usar_variavel_fora_das_features(self):
        serie(self.local, date(2024, 1, 1), 30)
        janelas = (Janela('baa_area_alerta', 7, 'media'),)

        # `baa_area_alerta` e proibida - confirma que a recusa vale mesmo
        # quando ela nao esta entre as features.
        with self.assertRaises(FeatureComVazamento):
            montar(self.local, 7, features=('sst',), janelas=janelas)

    def test_custo_da_janela_aparece_no_resumo(self):
        serie(self.local, date(2024, 1, 1), 30)

        com = montar(self.local, 3, features=FEATURES,
                     janelas=(Janela('dhw', 7, 'variacao'),))
        sem = montar(self.local, 3, features=FEATURES, janelas=())

        self.assertEqual(com.descartadas_sem_janela, 7)
        self.assertEqual(com.n, sem.n - 7)
        self.assertIn('sem janela completa', com.resumo())
        self.assertNotIn('sem janela', sem.resumo())

    def test_colunas_de_entrada_juntam_features_e_janelas(self):
        serie(self.local, date(2024, 1, 1), 30)
        janelas = (Janela('dhw', 7, 'variacao'),)

        conjunto = montar(self.local, 3, features=FEATURES, janelas=janelas)

        self.assertEqual(
            conjunto.colunas_de_entrada, ('sst', 'dhw', 'dhw_variacao_7d')
        )
        self.assertNotIn('alvo_atual', conjunto.colunas_de_entrada)

    def test_padrao_do_projeto_traz_trajetoria_das_quatro_variaveis(self):
        variacoes = {j.variavel for j in JANELAS_PADRAO if j.operacao == 'variacao'}

        self.assertEqual(
            variacoes, {'sst', 'dhw', 'salinidade', 'oxigenio'}
        )

    def test_padrao_deriva_das_variaveis_e_nao_e_lista_fixa(self):
        """Pedir ('sst',) nao pode passar a exigir salinidade."""
        janelas = janelas_para(('sst',))

        self.assertEqual({j.variavel for j in janelas}, {'sst'})

    def test_uma_janela_por_variavel_e_so_uma(self):
        """Trava a correcao de 25/07/2026 - ver docs/RESULTADOS.md secao 8.

        Duas janelas da mesma variavel tinham r = 0,976 entre si, o que
        tornava os coeficientes ininterpretaveis sem comprar desempenho.
        """
        janelas = janelas_para(('sst', 'dhw', 'salinidade', 'oxigenio'))

        por_variavel = {}
        for janela in janelas:
            por_variavel.setdefault(janela.variavel, []).append(janela.dias)

        for variavel, dias in por_variavel.items():
            self.assertEqual(
                len(dias), 1,
                f'{variavel} tem mais de uma janela: {dias}',
            )

    def test_nenhum_nivel_entra_como_feature_por_padrao(self):
        """Versao D: so trajetorias. Ver docs/RESULTADOS.md secao 8."""
        from ml.dataset import FEATURES_PADRAO

        self.assertEqual(FEATURES_PADRAO, ())

    def test_conjunto_sem_janela_e_possivel_para_comparacao(self):
        serie(self.local, date(2024, 1, 1), 30)

        conjunto = montar(self.local, 3, features=FEATURES, janelas=())

        self.assertEqual(conjunto.janelas, ())
        self.assertEqual(conjunto.colunas_de_entrada, FEATURES)

    def test_janela_nao_atravessa_a_fronteira_entre_locais(self):
        """Concatenar antes de aplicar janela misturaria dois recifes."""
        locais = []
        for slug in ('a-janela', 'b-janela'):
            local = LocalRecife.objects.create(
                slug=slug, nome=slug, estado='Bahia', cidade='Caravelas',
                latitude=-17.9, longitude=-38.6,
            )
            serie(local, date(2024, 1, 1), 20)
            locais.append(local)

        conjunto = montar_todos(
            locais, horizonte=3, features=FEATURES,
            janelas=(Janela('dhw', 7, 'variacao'),),
        )

        # Cada local perde os 7 primeiros dias: 20 - 3 (alvo) - 7 = 10.
        for slug in ('a-janela', 'b-janela'):
            parte = conjunto.quadro[conjunto.quadro['local'] == slug]
            self.assertEqual(len(parte), 10)
            self.assertEqual(parte['data'].min(), date(2024, 1, 8))


class PersistenciaTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-baseline', nome='Base', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )

    def test_persistencia_repete_o_valor_de_hoje(self):
        serie(self.local, date(2024, 1, 1), 20, baa=lambda i: i % 5)

        conjunto = montar(self.local, horizonte=7, features=FEATURES, janelas=())
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


def quadro_da_regra(linhas):
    """Quadro minimo para a regra: (dhw_atual, hotspot_atual, alvo)."""
    return pd.DataFrame(
        linhas, columns=['dhw_atual', 'hotspot_atual', 'alvo']
    )


class RegraDaNoaaTests(TestCase):
    """A segunda linha de base: `HotSpot >= 1 e DHW >= 4`, aplicada em `t`.

    Ela existe porque a persistencia sozinha e um adversario fraco - copia o
    BAA de hoje e nao tem corte que se possa mover. A regra da NOAA e o que
    qualquer gestor ja tem de graca, e e contra ela que o modelo precisa se
    justificar.
    """

    def test_precisa_das_duas_metades_para_disparar(self):
        quadro = quadro_da_regra([
            (6.0, 1.5, 0.0),   # quente e acumulado -> avisa
            (6.0, 0.2, 0.0),   # acumulado, mas a agua ja esfriou -> nao avisa
            (1.0, 1.5, 0.0),   # quente, mas sem acumulo -> nao avisa
            (1.0, 0.2, 0.0),
        ])

        previsto = prever_regra_noaa(quadro)

        self.assertEqual(list(previsto), [3.0, 0.0, 0.0, 0.0])

    def test_sem_hotspot_a_regra_dispara_no_calor_que_ja_passou(self):
        """A metade que falta, medida: 479 dias assim na serie real."""
        quadro = quadro_da_regra([(6.0, 0.2, 0.0)])

        self.assertEqual(list(prever_regra_noaa(quadro)), [0.0])
        self.assertEqual(
            list(prever_regra_noaa(quadro, usar_hotspot=False)), [3.0]
        )

    def test_dia_sem_a_variavel_nao_vira_alerta(self):
        """🚨 NaN nao pode virar aviso. Nao saber nao e motivo para avisar."""
        quadro = quadro_da_regra([
            (float('nan'), 1.5, 0.0),
            (6.0, float('nan'), 0.0),
        ])

        self.assertEqual(list(prever_regra_noaa(quadro)), [0.0, 0.0])

    def test_devolve_serie_no_nivel_do_baa_e_nao_binaria(self):
        """Sem isso `avaliar` compararia 1 contra 3 e contaria erro."""
        quadro = quadro_da_regra([(6.0, 1.5, 4.0)])

        d = avaliar(quadro['alvo'], prever_regra_noaa(quadro))

        self.assertEqual(d.verdadeiros_positivos, 1)
        self.assertEqual(d.falsos_positivos, 0)

    def test_o_corte_padrao_e_o_publicado_pela_noaa(self):
        self.assertEqual(CORTE_DHW_ALERTA_1, 4.0)

    def test_escolher_corte_prefere_o_que_mede_melhor_no_treino(self):
        # Alerta so acima de 8; um corte baixo enche de alarme falso.
        treino = quadro_da_regra(
            [(float(d), 1.5, 4.0 if d >= 8 else 0.0) for d in range(0, 16)]
        )

        corte, f1 = escolher_corte_dhw(treino)

        self.assertEqual(corte, 8.0)
        self.assertEqual(f1, 1.0)

    def test_empate_no_treino_resolve_pelo_corte_mais_conservador(self):
        """Entre dois cortes que medem igual, o maior erra menos fora."""
        treino = quadro_da_regra(
            [(float(d), 1.5, 4.0 if d >= 12 else 0.0) for d in range(0, 16)]
        )

        corte, _ = escolher_corte_dhw(treino, cortes=(12.0, 11.0))

        self.assertEqual(corte, 12.0)


class ColunasDeLinhaDeBaseTests(TestCase):
    """As colunas `_atual` sao para as linhas de base, nunca para o modelo."""

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-linha-base', nome='LB', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )

    def test_nenhuma_coluna_atual_entra_como_entrada_do_modelo(self):
        """🚨 `hotspot` e proibido como feature: junto com o DHW da o alvo."""
        serie(self.local, date(2024, 1, 1), 40)

        conjunto = montar(self.local, horizonte=7, features=FEATURES, janelas=())

        for variavel in VARIAVEIS_DE_LINHA_DE_BASE:
            self.assertIn(f'{variavel}_atual', conjunto.quadro.columns)
            self.assertNotIn(f'{variavel}_atual', conjunto.colunas_de_entrada)

    def test_falta_de_hotspot_nao_custa_amostra_ao_modelo(self):
        """🚨 A linha de base nao pode encolher em silencio o conjunto medido.

        `serie` nao grava `hotspot`. Se a coluna entrasse em algum `dropna`, o
        conjunto inteiro sumiria - e a comparacao passaria a ser feita sobre
        outros dados sem ninguem perceber.
        """
        serie(self.local, date(2024, 1, 1), 40)

        conjunto = montar(self.local, horizonte=7, features=FEATURES, janelas=())

        self.assertEqual(conjunto.n, 33)   # 40 dias - 7 de horizonte
        self.assertTrue(conjunto.quadro['hotspot_atual'].isna().all())
        self.assertFalse(conjunto.quadro['dhw_atual'].isna().any())


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

        conjunto = montar(self.local, horizonte=7, features=FEATURES, janelas=())
        treino, teste = dividir_deixando_um_ano_de_fora(conjunto.quadro, 2024)

        self.assertTrue(all(d.year != 2024 for d in treino['alvo_data']))
        self.assertTrue(all(d.year == 2024 for d in teste['alvo_data']))
        self.assertEqual(len(treino) + len(teste), len(conjunto.quadro))

    def test_divisao_usa_a_data_do_alvo_e_nao_a_das_features(self):
        """O que define a dobra e o dia sobre o qual a previsao fala."""
        serie(self.local, date(2023, 12, 28), 10, baa=lambda i: 1)

        conjunto = montar(self.local, horizonte=7, features=FEATURES, janelas=())
        _, teste = dividir_deixando_um_ano_de_fora(conjunto.quadro, 2024)

        self.assertTrue(all(d.year == 2023 for d in teste['data']))
        self.assertTrue(all(d.year == 2024 for d in teste['alvo_data']))


class ConjuntoMultiLocalTests(TestCase):
    def test_padrao_de_janela_tambem_vale_para_montar_todos(self):
        """Regressao: `montar_todos` nao resolvia `janelas=None` e estourava."""
        local = LocalRecife.objects.create(
            slug='todos-padrao', nome='TP', estado='Bahia', cidade='Caravelas',
            latitude=-17.9, longitude=-38.6,
        )
        serie(local, date(2024, 1, 1), 40)

        conjunto = montar_todos([local], horizonte=7, features=('sst',))

        self.assertEqual([j.nome for j in conjunto.janelas], ['sst_variacao_7d'])
        self.assertIn('sst_variacao_7d', conjunto.quadro.columns)

    def test_empilha_locais_com_coluna_de_origem(self):
        locais = []
        for slug in ('a-ml', 'b-ml'):
            local = LocalRecife.objects.create(
                slug=slug, nome=slug, estado='Bahia', cidade='Caravelas',
                latitude=-17.9, longitude=-38.6,
            )
            serie(local, date(2024, 1, 1), 15)
            locais.append(local)

        conjunto = montar_todos(locais, horizonte=7, features=FEATURES, janelas=())

        self.assertEqual(set(conjunto.quadro['local']), {'a-ml', 'b-ml'})
        self.assertEqual(conjunto.n, 16)

    def test_persistencia_roda_ponta_a_ponta(self):
        local = LocalRecife.objects.create(
            slug='ponta-a-ponta', nome='PP', estado='Bahia',
            cidade='Caravelas', latitude=-17.9, longitude=-38.6,
        )
        serie(local, date(2024, 1, 1), 60, baa=lambda i: 4 if 20 <= i < 40 else 0)

        conjunto = montar(local, horizonte=7, features=FEATURES, janelas=())
        diario, episodio = avaliar_persistencia(conjunto)

        self.assertEqual(diario.n, conjunto.n)
        self.assertEqual(episodio.episodios_reais, 1)
        self.assertEqual(episodio.episodios_detectados, 1)
