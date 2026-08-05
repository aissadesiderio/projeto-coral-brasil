"""Testes do conector Copernicus.

Sem rede: `abrir` e substituido por um duble que devolve um xarray com
cobertura temporal controlada. E o que permite testar a parte dificil - a
emenda entre reanalise e analise, e o corte que impede previsao de entrar como
medicao.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import xarray as xr
from django.test import TestCase

from aquaculture.models import LocalRecife, MedicaoAmbiental
from ingestao.conectores.copernicus import (
    SERIES,
    ConectorCopernicus,
    ultimo_dia_permitido,
)
from ingestao.registro import ingerir


def dataset_falso(variavel, inicio, fim, valor=35.0):
    """Grade diaria com 2x2 pixels e um nivel de profundidade."""
    tempos = pd.date_range(inicio, fim, freq='D')
    dados = np.full((len(tempos), 1, 2, 2), valor, dtype='float32')
    return xr.Dataset(
        {variavel: (('time', 'depth', 'latitude', 'longitude'), dados)},
        coords={
            'time': tempos,
            'depth': [0.494],
            'latitude': [-18.0, -17.9],
            'longitude': [-38.9, -38.8],
        },
    )


class AberturaFalsa:
    """Devolve cobertura diferente por dataset, como no CMEMS real."""

    def __init__(self, coberturas, valores=None):
        self.coberturas = coberturas
        self.valores = valores or {}
        self.pedidos = []

    def __call__(self, fonte, bbox):
        self.pedidos.append(fonte.dataset_id)
        inicio, fim = self.coberturas[fonte.dataset_id]
        return dataset_falso(
            fonte.variavel,
            inicio,
            fim,
            self.valores.get(fonte.dataset_id, 35.0),
        )


# Cobertura medida no catalogo real em 25/07/2026.
REANALISE_SAL = 'cmems_mod_glo_phy_my_0.083deg_P1D-m'
ANALISE_SAL = 'cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m'

COBERTURA_REALISTA = {
    REANALISE_SAL: (date(2020, 1, 1), date(2026, 6, 23)),
    ANALISE_SAL: (date(2022, 6, 1), date(2026, 8, 4)),  # publica futuro
}


class LimiteDeFuturoTests(TestCase):
    """Previsao nao pode entrar no banco como medicao."""

    def test_ultimo_dia_permitido_e_ontem(self):
        hoje = date(2026, 7, 25)

        self.assertEqual(ultimo_dia_permitido(hoje), date(2026, 7, 24))

    def test_periodo_e_cortado_em_ontem(self):
        local = LocalRecife.objects.create(
            slug='local-futuro', nome='Futuro', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )
        abrir = AberturaFalsa(COBERTURA_REALISTA)
        conector = ConectorCopernicus(series=['salinidade'], abrir=abrir)

        resultado = conector.coletar(
            local, date(2026, 6, 1), date.today() + timedelta(days=10)
        )

        self.assertFalse(resultado.houve_falha)
        self.assertIn('previsao nao entra como medicao', resultado.nota)
        if resultado.observacoes:
            self.assertLessEqual(
                max(o.data for o in resultado.observacoes),
                ultimo_dia_permitido(),
            )


class EmendaDeProdutosTests(TestCase):
    """Reanalise no historico, analise no periodo recente."""

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-cmems', nome='CMEMS', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )

    def _coletar(self, inicio, fim, valores=None):
        abrir = AberturaFalsa(COBERTURA_REALISTA, valores)
        conector = ConectorCopernicus(series=['salinidade'], abrir=abrir)
        return conector.coletar(self.local, inicio, fim), abrir

    def test_periodo_antigo_usa_so_a_reanalise(self):
        resultado, abrir = self._coletar(date(2021, 1, 1), date(2021, 3, 1))

        self.assertEqual(abrir.pedidos[0], REANALISE_SAL)
        origens = {o.dataset_id for o in resultado.observacoes}
        self.assertEqual(origens, {REANALISE_SAL})

    def test_periodo_recente_emenda_os_dois(self):
        """O trecho apos o fim da reanalise vem da analise."""
        resultado, _ = self._coletar(date(2026, 6, 1), date(2026, 7, 10))

        por_origem = {}
        for o in resultado.observacoes:
            por_origem.setdefault(o.dataset_id, []).append(o.data)

        self.assertEqual(set(por_origem), {REANALISE_SAL, ANALISE_SAL})
        self.assertEqual(max(por_origem[REANALISE_SAL]), date(2026, 6, 23))
        self.assertEqual(min(por_origem[ANALISE_SAL]), date(2026, 6, 24))

    def test_emenda_nao_duplica_datas(self):
        """Os dois produtos se sobrepoem de 2022 a 2026 - so um pode valer."""
        resultado, _ = self._coletar(date(2026, 6, 1), date(2026, 7, 10))

        datas = [o.data for o in resultado.observacoes]

        self.assertEqual(len(datas), len(set(datas)))

    def test_reanalise_tem_precedencia_na_sobreposicao(self):
        """No periodo em que os dois existem, vale o produto reprocessado."""
        resultado, _ = self._coletar(
            date(2023, 1, 1), date(2023, 1, 5),
            valores={REANALISE_SAL: 35.0, ANALISE_SAL: 99.0},
        )

        origens = {o.dataset_id for o in resultado.observacoes}
        self.assertEqual(origens, {REANALISE_SAL})

    def test_proveniencia_chega_ao_banco_por_valor(self):
        abrir = AberturaFalsa(COBERTURA_REALISTA)
        conector = ConectorCopernicus(series=['salinidade'], abrir=abrir)

        ingerir(self.local, date(2026, 6, 1), date(2026, 7, 10), conector)

        datasets = set(
            MedicaoAmbiental.objects.filter(fonte='copernicus')
            .values_list('dataset_id', flat=True)
        )
        self.assertEqual(datasets, {REANALISE_SAL, ANALISE_SAL})

    def test_variavel_vira_nome_canonico(self):
        abrir = AberturaFalsa(COBERTURA_REALISTA)
        conector = ConectorCopernicus(series=['salinidade'], abrir=abrir)

        ingerir(self.local, date(2021, 1, 1), date(2021, 1, 5), conector)

        medicao = MedicaoAmbiental.objects.filter(fonte='copernicus').first()
        self.assertEqual(medicao.variavel, 'salinidade')


class ConfiguracaoDeSeriesTests(TestCase):
    def test_kd490_fica_fora_do_padrao(self):
        """Decisao de 25/07/2026: so ha dado de 2023-11 e sem reanalise."""
        self.assertNotIn('kd490', ConectorCopernicus().series)

    def test_kd490_continua_disponivel_para_o_experimento(self):
        conector = ConectorCopernicus(series=['kd490'])

        self.assertEqual(conector.series, ('kd490',))

    def test_serie_desconhecida_e_recusada_na_construcao(self):
        with self.assertRaises(ValueError) as ctx:
            ConectorCopernicus(series=['clorofila'])

        self.assertIn('clorofila', str(ctx.exception))

    def test_kd490_nao_tem_reanalise(self):
        """Trava a razao pela qual ele saiu do baseline."""
        tipos = {f.tipo for f in SERIES['kd490']}

        self.assertEqual(tipos, {'analise'})

    def test_series_do_baseline_tem_reanalise(self):
        for nome in ('salinidade', 'oxigenio'):
            tipos = {f.tipo for f in SERIES[nome]}
            self.assertIn('reanalise', tipos, f'{nome} precisa cobrir 2020')


class FalhaDoCopernicusTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-cmems-falha', nome='Falha', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )

    def test_falha_de_rede_nao_derruba_o_pipeline(self):
        def explodir(fonte, bbox):
            raise ConnectionError('sem rede')

        conector = ConectorCopernicus(
            series=['salinidade'], abrir=explodir, dormir=lambda _s: None
        )

        resultado = conector.coletar(
            self.local, date(2021, 1, 1), date(2021, 1, 5)
        )

        self.assertTrue(resultado.houve_falha)
        self.assertIn('sem rede', resultado.erro)

    def test_credencial_recusada_nao_gasta_retentativa(self):
        esperas = []

        def negar(fonte, bbox):
            raise PermissionError('401 Unauthorized: invalid credentials')

        conector = ConectorCopernicus(
            series=['salinidade'], abrir=negar, dormir=esperas.append
        )

        conector.coletar(self.local, date(2021, 1, 1), date(2021, 1, 5))

        self.assertEqual(esperas, [])

    def test_local_sem_coordenadas_e_recusado(self):
        sem_geo = LocalRecife.objects.create(
            slug='sem-geo-cmems', nome='Sem Geo', estado='Bahia',
            cidade='Caravelas',
        )
        conector = ConectorCopernicus(series=['salinidade'])

        resultado = conector.coletar(
            sem_geo, date(2021, 1, 1), date(2021, 1, 5)
        )

        self.assertTrue(resultado.houve_falha)
        self.assertIn('coordenadas', resultado.erro)
