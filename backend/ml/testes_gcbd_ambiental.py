"""Testes da janela ambiental do GCBD (entrega 2, passo 2).

O que protegem, em ordem de gravidade: que a janela **nunca inclua um dia
posterior a visita** (seria vazamento puro — o mergulhador ja tinha visto o
coral branco), que o **raio de busca** seja o menor que acha oceano e fique
gravado, que visita sem janela completa seja **descartada e nunca imputada**, e
que o cache saiba retomar de onde parou.

Nao tocam na rede: usam um `xarray.Dataset` sintetico com uma mascara de terra
desenhada a mao.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from ml import gcbd, gcbd_ambiental
from ml.gcbd_ambiental import SemCelulaDeOceano


def dataset_falso(lat_centro=-13.0, lon_centro=-38.0, dias=400,
                  buraco_de_terra=None, valor_base=36.0):
    """Um cubo (time, latitude, longitude) com valores crescentes no tempo.

    `buraco_de_terra` = (lat_min, lat_max, lon_min, lon_max) vira NaN, imitando
    a mascara de terra dos produtos do CMEMS.
    """
    import xarray as xr

    latitudes = np.round(np.arange(lat_centro - 1.0, lat_centro + 1.0, 0.25), 4)
    longitudes = np.round(np.arange(lon_centro - 1.0, lon_centro + 1.0, 0.25), 4)
    tempos = pd.date_range('1993-01-01', periods=dias, freq='D')

    # Valor = base + indice do dia/1000, para a variacao ser previsivel.
    valores = np.broadcast_to(
        (valor_base + np.arange(dias) / 1000.0)[:, None, None],
        (dias, len(latitudes), len(longitudes)),
    ).copy()

    if buraco_de_terra:
        lat_min, lat_max, lon_min, lon_max = buraco_de_terra
        for i, la in enumerate(latitudes):
            for j, lo in enumerate(longitudes):
                if lat_min <= la <= lat_max and lon_min <= lo <= lon_max:
                    valores[:, i, j] = np.nan

    return xr.Dataset(
        {'so': (('time', 'latitude', 'longitude'), valores)},
        coords={'time': tempos, 'latitude': latitudes, 'longitude': longitudes},
    )


class JanelaOlhaSoParaTrasTests(SimpleTestCase):
    """A garantia central: nada depois da visita pode entrar."""

    def setUp(self):
        self.ds = dataset_falso()
        self.mascara = gcbd_ambiental.mascara_de_oceano(self.ds, 'so')

    def test_a_janela_termina_no_dia_da_visita(self):
        visita = date(1993, 6, 1)

        quadro, _, _ = gcbd_ambiental.extrair_janela(
            self.ds, 'so', self.mascara, -13.0, -38.0, visita, dias=90
        )

        datas = pd.to_datetime(quadro['time']).dt.date
        self.assertEqual(datas.max(), visita)
        self.assertLessEqual(datas.max(), visita, 'a janela passou da visita')

    def test_a_janela_comeca_dias_antes(self):
        visita = date(1993, 6, 1)

        quadro, _, _ = gcbd_ambiental.extrair_janela(
            self.ds, 'so', self.mascara, -13.0, -38.0, visita, dias=90
        )

        datas = pd.to_datetime(quadro['time']).dt.date
        self.assertEqual(datas.min(), visita - timedelta(days=90))
        self.assertEqual(len(quadro), 91)   # inclui os dois extremos

    def test_janela_menor_e_respeitada(self):
        quadro, _, _ = gcbd_ambiental.extrair_janela(
            self.ds, 'so', self.mascara, -13.0, -38.0, date(1993, 6, 1), dias=30
        )

        self.assertEqual(len(quadro), 31)


class RaioDeBuscaTests(SimpleTestCase):
    def test_usa_o_menor_raio_que_acha_oceano(self):
        ds = dataset_falso()
        mascara = gcbd_ambiental.mascara_de_oceano(ds, 'so')

        raio = gcbd_ambiental.raio_util(mascara, -13.0, -38.0)

        self.assertEqual(raio, gcbd_ambiental.RAIOS_BUSCA[0])

    def test_alarga_o_raio_quando_o_ponto_cai_em_terra(self):
        """69 das 166 visitas estao a menos de 1 km da costa."""
        ds = dataset_falso(buraco_de_terra=(-13.2, -12.8, -38.2, -37.8))
        mascara = gcbd_ambiental.mascara_de_oceano(ds, 'so')

        raio = gcbd_ambiental.raio_util(mascara, -13.0, -38.0)

        self.assertGreater(raio, gcbd_ambiental.RAIOS_BUSCA[0])

    def test_ponto_sem_oceano_nenhum_levanta_erro(self):
        """Melhor falhar do que devolver valor de lugar nenhum."""
        ds = dataset_falso(buraco_de_terra=(-99, 99, -99, 99))
        mascara = gcbd_ambiental.mascara_de_oceano(ds, 'so')

        with self.assertRaises(SemCelulaDeOceano):
            gcbd_ambiental.raio_util(mascara, -13.0, -38.0)

    def test_o_raio_usado_volta_junto_com_os_valores(self):
        ds = dataset_falso(buraco_de_terra=(-13.2, -12.8, -38.2, -37.8))
        mascara = gcbd_ambiental.mascara_de_oceano(ds, 'so')

        _, raio, n_celulas = gcbd_ambiental.extrair_janela(
            ds, 'so', mascara, -13.0, -38.0, date(1993, 6, 1)
        )

        self.assertGreater(raio, 0.15)
        self.assertGreater(n_celulas, 0)


class ResumirTests(SimpleTestCase):
    def _cache(self, valores, variavel='salinidade'):
        base = date(1993, 6, 1)
        return pd.DataFrame({
            'Site_ID': 1,
            'Date_obs': base,
            'data': [base - timedelta(days=len(valores) - 1 - i)
                     for i in range(len(valores))],
            'variavel': variavel,
            'valor': valores,
            'dataset_id': 'x',
            'raio_graus': 0.15,
            'n_celulas': 4,
        })

    def test_media_e_variacao(self):
        resumido = gcbd_ambiental.resumir(
            self._cache([10.0, 20.0, 30.0]), variaveis=('salinidade',)
        )

        self.assertAlmostEqual(resumido.loc[0, 'salinidade_media_90d'], 20.0)
        # variacao = ultimo - primeiro
        self.assertAlmostEqual(resumido.loc[0, 'salinidade_variacao_90d'], 20.0)

    def test_variacao_negativa_quando_a_variavel_cai(self):
        resumido = gcbd_ambiental.resumir(
            self._cache([30.0, 20.0, 10.0]), variaveis=('salinidade',)
        )

        self.assertAlmostEqual(resumido.loc[0, 'salinidade_variacao_90d'], -20.0)

    def test_nan_no_meio_nao_contamina_a_media(self):
        resumido = gcbd_ambiental.resumir(
            self._cache([10.0, np.nan, 30.0]), variaveis=('salinidade',)
        )

        self.assertAlmostEqual(resumido.loc[0, 'salinidade_media_90d'], 20.0)
        self.assertEqual(resumido.loc[0, 'salinidade_dias_validos'], 2)

    def test_janela_toda_nan_vira_none(self):
        resumido = gcbd_ambiental.resumir(
            self._cache([np.nan, np.nan]), variaveis=('salinidade',)
        )

        self.assertTrue(pd.isna(resumido.loc[0, 'salinidade_media_90d']))

    def test_o_raio_atravessa_para_o_resumo(self):
        resumido = gcbd_ambiental.resumir(
            self._cache([1.0, 2.0]), variaveis=('salinidade',)
        )

        self.assertEqual(resumido.loc[0, 'salinidade_raio_graus'], 0.15)

    def test_cache_vazio_nao_quebra(self):
        vazio = pd.DataFrame(columns=list(gcbd_ambiental.COLUNAS_CACHE))

        self.assertTrue(gcbd_ambiental.resumir(vazio).empty)

    def test_duas_visitas_nao_se_misturam(self):
        primeira = self._cache([10.0, 10.0])
        segunda = self._cache([50.0, 50.0])
        segunda['Date_obs'] = date(1994, 6, 1)

        resumido = gcbd_ambiental.resumir(
            pd.concat([primeira, segunda]), variaveis=('salinidade',)
        )

        self.assertEqual(len(resumido), 2)
        self.assertEqual(
            sorted(resumido['salinidade_media_90d']), [10.0, 50.0]
        )


class NomesTests(SimpleTestCase):
    def test_nome_da_feature(self):
        self.assertEqual(
            gcbd_ambiental.nome_da_feature('salinidade', 'media', 90),
            'salinidade_media_90d',
        )

    def test_features_de_lista_todas_as_combinacoes(self):
        nomes = gcbd_ambiental.features_de(('salinidade', 'oxigenio'),
                                           ('media', 'variacao'), 90)

        self.assertEqual(nomes, (
            'salinidade_media_90d', 'salinidade_variacao_90d',
            'oxigenio_media_90d', 'oxigenio_variacao_90d',
        ))


class JuntarTests(SimpleTestCase):
    def _conjunto(self, n=6):
        linhas = []
        for i in range(n):
            linhas.append({
                'Site_ID': i,
                'Date': f'{2000 + i}-06-15',
                'Date_Year': 2000 + i,
                'Percent_Bleaching': 10.0 if i % 2 else 0.0,
                'TSA_DHW': float(i),
                'TSA': float(i) / 4,
                'Windspeed': 5.0,
                'Latitude_Degrees': -13.0,
                'Longitude_Degrees': -38.0,
            })
        quadro = pd.DataFrame(linhas)
        quadro['alvo'] = (quadro['Percent_Bleaching'] > 0).astype(int)
        return gcbd.ConjuntoGCBD(
            quadro=quadro, features=('TSA_DHW', 'TSA', 'Windspeed'), limiar=0.0,
        )

    def _cache_para(self, conjunto, faltando=()):
        linhas = []
        for sitio, data in zip(conjunto.quadro['Site_ID'], conjunto.quadro['Date']):
            if sitio in faltando:
                continue
            obs = pd.to_datetime(data).date()
            for variavel in ('salinidade', 'oxigenio'):
                for k in range(3):
                    linhas.append({
                        'Site_ID': sitio, 'Date_obs': obs,
                        'data': obs - timedelta(days=2 - k),
                        'variavel': variavel, 'valor': 30.0 + k,
                        'dataset_id': 'x', 'raio_graus': 0.15, 'n_celulas': 4,
                    })
        return pd.DataFrame(linhas)

    def test_as_features_ambientais_entram(self):
        conjunto = self._conjunto()

        juntado = gcbd_ambiental.juntar(conjunto, cache=self._cache_para(conjunto))

        for nome in gcbd_ambiental.features_de():
            self.assertIn(nome, juntado.features)
            self.assertIn(nome, juntado.quadro.columns)
        self.assertEqual(juntado.n, conjunto.n)

    def test_as_termicas_continuam_presentes(self):
        conjunto = self._conjunto()

        juntado = gcbd_ambiental.juntar(conjunto, cache=self._cache_para(conjunto))

        for nome in conjunto.features:
            self.assertIn(nome, juntado.features)

    def test_visita_sem_janela_e_descartada_nunca_imputada(self):
        """Imputar salinidade inventaria a variavel que o experimento mede."""
        conjunto = self._conjunto(n=6)

        juntado = gcbd_ambiental.juntar(
            conjunto, cache=self._cache_para(conjunto, faltando={0, 1})
        )

        self.assertEqual(juntado.n, 4)
        self.assertEqual(juntado.descartadas_sem_feature, 2)
        self.assertFalse(juntado.quadro[list(juntado.features)].isna().any().any())

    def test_cache_vazio_descarta_tudo_em_vez_de_preencher(self):
        conjunto = self._conjunto()
        vazio = pd.DataFrame(columns=list(gcbd_ambiental.COLUNAS_CACHE))

        juntado = gcbd_ambiental.juntar(conjunto, cache=vazio)

        self.assertEqual(juntado.n, 0)


class CacheTests(SimpleTestCase):
    def test_cache_inexistente_devolve_quadro_vazio_com_as_colunas(self):
        cache = gcbd_ambiental.carregar_cache('/nao/existe/x.csv')

        self.assertTrue(cache.empty)
        self.assertEqual(list(cache.columns), list(gcbd_ambiental.COLUNAS_CACHE))

    def test_so_a_reanalise_e_usada(self):
        """A reanalise cobre 1993+; o GCBD comeca em 1994. Sem emenda."""
        for variavel in gcbd_ambiental.VARIAVEIS:
            self.assertEqual(gcbd_ambiental._fonte_de(variavel).tipo, 'reanalise')

    def test_qualidade_da_agua_sai_do_mesmo_produto_do_oxigenio(self):
        """Nao ha fonte nova: sao mais colunas do arquivo que ja abrimos."""
        do_oxigenio = gcbd_ambiental._fonte_de('oxigenio')

        for variavel in gcbd_ambiental.QUALIDADE_DA_AGUA:
            fonte = gcbd_ambiental._fonte_de(variavel)
            self.assertEqual(fonte.dataset_id, do_oxigenio.dataset_id)
            self.assertEqual(fonte.tipo, 'reanalise')

    def test_cada_variavel_de_agua_tem_coluna_propria(self):
        colunas = {gcbd_ambiental._fonte_de(v).variavel
                   for v in gcbd_ambiental.QUALIDADE_DA_AGUA}

        self.assertEqual(colunas, {'chl', 'no3', 'si'})

    def test_variavel_desconhecida_e_recusada_com_a_lista(self):
        with self.assertRaises(ValueError) as contexto:
            gcbd_ambiental._fonte_de('fosfato')

        mensagem = str(contexto.exception)
        self.assertIn('fosfato', mensagem)
        self.assertIn('clorofila', mensagem)

    def test_a_agua_nao_polui_as_series_do_conector(self):
        """Elas gravam em CSV, nao em MedicaoAmbiental.

        Listar em `conectores/copernicus.py::SERIES` faria o comando `ingerir`
        oferece-las, e ai quebrariam na normalizacao por nao terem nome
        canonico. Ficam declaradas onde sao usadas.
        """
        from ingestao.conectores.copernicus import SERIES

        for variavel in gcbd_ambiental.QUALIDADE_DA_AGUA:
            self.assertNotIn(variavel, SERIES)

    def test_com_agua_e_o_conjunto_ampliado(self):
        self.assertEqual(
            gcbd_ambiental.VARIAVEIS_COM_AGUA,
            (*gcbd_ambiental.VARIAVEIS, *gcbd_ambiental.QUALIDADE_DA_AGUA),
        )

    def test_features_de_acompanha_as_variaveis_pedidas(self):
        nomes = gcbd_ambiental.features_de(
            gcbd_ambiental.QUALIDADE_DA_AGUA, ('media',), 90
        )

        self.assertEqual(
            nomes,
            ('clorofila_media_90d', 'nitrato_media_90d', 'silicato_media_90d'),
        )

    def test_visitas_de_nao_repete_par_sitio_data(self):
        quadro = pd.DataFrame({
            'Site_ID': [1, 1, 2],
            'Date': ['2005-04-05', '2005-04-05', '2005-04-05'],
            'Latitude_Degrees': [-13.0, -13.0, -14.0],
            'Longitude_Degrees': [-38.0, -38.0, -39.0],
        })
        conjunto = gcbd.ConjuntoGCBD(quadro=quadro, features=(), limiar=0.0)

        self.assertEqual(len(gcbd_ambiental.visitas_de(conjunto)), 2)
