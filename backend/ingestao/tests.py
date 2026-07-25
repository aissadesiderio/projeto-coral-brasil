"""Testes do pipeline de ingestao.

Sem rede: o cliente ERDDAP e substituido por um duble que devolve um
DataFrame conhecido. Isso cobre normalizacao, validacao fisica, upsert
idempotente e tratamento de falha - tudo menos a chamada HTTP em si, que
precisa ser verificada na maquina do usuario.
"""

import os
from datetime import date, datetime, timedelta, timezone

import pandas as pd
from django.test import TestCase

from aquaculture.models import ExecucaoIngestao, LocalRecife, MedicaoAmbiental
from ingestao.certificados import (
    contexto_do_sistema,
    garantir_bundle_ca,
    interpretar,
)
from ingestao.base import PeriodoIndisponivel, ResultadoColeta
from ingestao.conectores.noaa_crw import (
    ConectorNoaaCrw,
    limitar_periodo,
    montar_constraints,
)
from ingestao.erros import parece_documento_html, resumir_erro
from ingestao.normalizacao import ColunaRecusada, normalizar, resolver_variavel
from ingestao.persistencia import preparar_medicoes, ultima_data_ingerida
from ingestao.qualidade import detectar_saltos, validar
from ingestao.registro import dividir_periodo, ingerir
from ingestao.retentativa import e_transitorio, executar_com_retentativa

# Mensagem literal devolvida pelo ERDDAP do pfeg em 25/07/2026.
ERRO_503_ERDDAP = (
    'Error { code=503; message="Service Unavailable: There was a (temporary?) '
    'problem. Wait a minute, then try again. (In a browser, click the Reload '
    'button.)"; }'
)


class Relogio:
    """Duble de `time.sleep`: registra as esperas sem gastar tempo real."""

    def __init__(self):
        self.esperas = []

    def __call__(self, segundos):
        self.esperas.append(segundos)


class ClienteErddapFalso:
    """Duble do cliente ERDDAP.

    Com `falhas_iniciais`, simula um servidor que se recupera: falha as N
    primeiras chamadas e responde na seguinte.
    """

    def __init__(self, df=None, excecao=None, falhas_iniciais=0):
        self._df = df
        self._excecao = excecao
        self._falhas_iniciais = falhas_iniciais
        self.chamadas = 0

    def to_pandas(self):
        self.chamadas += 1
        if self._falhas_iniciais:
            if self.chamadas <= self._falhas_iniciais:
                raise self._excecao or ConnectionError('falha passageira')
        elif self._excecao:
            raise self._excecao
        return self._df


def df_crw(dias=3, sst=28.0, dhw=2.0, baa=1.0):
    """Resposta tipica do ERDDAP: grade com 2 pixels por data."""
    linhas = []
    for i in range(dias):
        d = f'2026-01-{i + 1:02d}T12:00:00Z'
        for offset in (-0.01, 0.01):
            linhas.append(
                {
                    'time (UTC)': d,
                    'CRW_SST (degree_C)': sst + offset,
                    'CRW_DHW (C week)': dhw,
                    'CRW_BAA (1)': baa,
                    'CRW_HOTSPOT (degree_C)': 1.2,
                    'CRW_SSTANOMALY (degree_C)': 0.8,
                }
            )
    return pd.DataFrame(linhas)


# Grade real de Abrolhos em 17/05/2024, medida no ERDDAP: 121 pixels, nenhum
# NaN. E o caso que motivou trocar a media pelo maximo - ver FONTES.md 6.16.
ABROLHOS_2024_05_17 = [3] * 70 + [4] * 45 + [2] * 6


def df_grade_baa(baa_por_pixel, data='2026-03-17'):
    """Uma data, um pixel por valor de BAA em `baa_por_pixel`.

    Serve para montar o caso que motivou a mudanca: uma grade heterogenea, em
    que media e maximo dao respostas diferentes.
    """
    return pd.DataFrame(
        [
            {
                'time (UTC)': f'{data}T12:00:00Z',
                'CRW_SST (degree_C)': 29.0,
                'CRW_BAA (1)': valor,
            }
            for valor in baa_por_pixel
        ]
    )


class NormalizacaoTests(TestCase):
    def test_traduz_nomes_de_fonte_para_canonicos(self):
        self.assertEqual(resolver_variavel('CRW_SST'), 'sst')
        self.assertEqual(resolver_variavel('crw_dhw'), 'dhw')
        self.assertEqual(resolver_variavel('thetao'), 'sst')
        self.assertEqual(resolver_variavel('so'), 'salinidade')
        self.assertEqual(resolver_variavel('kd'), 'kd490')

    def test_coluna_desconhecida_e_ignorada_e_nao_quebra(self):
        self.assertIsNone(resolver_variavel('coluna_qualquer'))

    def test_alcalinidade_e_recusada_como_ph(self):
        """O contrato canonico proibe usar talk como pH.

        Esse e o bug ativo do carregar_historico.py: dados/ph.csv contem talk,
        e o mapa de colunas antigo aceitava 'talk' para o campo ph.
        """
        with self.assertRaises(ColunaRecusada) as ctx:
            resolver_variavel('talk')

        self.assertIn('Alcalinidade', str(ctx.exception))

    def test_salinidade_de_fundo_e_recusada(self):
        with self.assertRaises(ColunaRecusada):
            resolver_variavel('sob')

    def test_converte_kelvin_para_celsius(self):
        resultado = normalizar('CRW_SST', 301.15)

        self.assertEqual(resultado.variavel, 'sst')
        self.assertAlmostEqual(resultado.valor, 28.0, places=2)
        self.assertIn('Kelvin', resultado.observacao)

    def test_par_error_entra_como_degradado(self):
        resultado = normalizar('par_error', 200.0)

        self.assertEqual(resultado.variavel, 'par')
        self.assertEqual(resultado.quality_flag, 'degradado')


class QualidadeTests(TestCase):
    def test_valor_fora_da_faixa_fisica_vira_nulo_e_nao_zero(self):
        """A regressao central: o pipeline antigo fazia fillna(0)."""
        resultado = validar('salinidade', -5.0)

        self.assertFalse(resultado.aprovado)
        self.assertIsNone(resultado.valor)
        self.assertNotEqual(resultado.valor, 0)
        self.assertIn('nao como zero', resultado.observacao)

    def test_ph_zero_seria_reprovado(self):
        """pH 0 era gravado pelo pipeline antigo em toda lacuna > 14 dias."""
        resultado = validar('sst', -100.0)

        self.assertFalse(resultado.aprovado)
        self.assertIsNone(resultado.valor)

    def test_valor_plausivel_mas_atipico_e_preservado_como_degradado(self):
        resultado = validar('salinidade', 42.0)

        self.assertTrue(resultado.aprovado)
        self.assertEqual(resultado.valor, 42.0)
        self.assertEqual(resultado.quality_flag, 'degradado')

    def test_valor_normal_passa_limpo(self):
        resultado = validar('sst', 28.0)

        self.assertEqual(resultado.quality_flag, 'ok')
        self.assertEqual(resultado.valor, 28.0)

    def test_detecta_salto_diario_implausivel(self):
        serie = [
            (date(2026, 1, 1), 28.0),
            (date(2026, 1, 2), 28.3),
            (date(2026, 1, 3), 40.0),
        ]

        suspeitas = detectar_saltos(serie, 'sst')

        self.assertIn(date(2026, 1, 3), suspeitas)
        self.assertNotIn(date(2026, 1, 2), suspeitas)


class ConectorNoaaCrwTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-ingestao-teste',
            nome='Local de Teste',
            estado='Bahia',
            cidade='Caravelas',
            latitude=-17.972,
            longitude=-38.688,
        )

    def test_agrega_a_grade_por_data(self):
        conector = ConectorNoaaCrw(cliente=ClienteErddapFalso(df_crw(dias=3)))

        resultado = conector.coletar(self.local, date(2026, 1, 1), date(2026, 1, 3))

        self.assertFalse(resultado.houve_falha)
        datas = {o.data for o in resultado.observacoes}
        self.assertEqual(len(datas), 3, 'Os 2 pixels por data deviam virar 1 valor')
        colunas = {o.coluna for o in resultado.observacoes}
        self.assertEqual(
            colunas,
            {
                'CRW_SST', 'CRW_DHW', 'CRW_BAA',
                'CRW_HOTSPOT', 'CRW_SSTANOMALY',
                # Derivada do BAA pelo proprio conector.
                'CRW_BAA_FRACAO_ALERTA',
            },
        )

    def test_falha_de_rede_nao_levanta_excecao(self):
        """Uma fonte fora do ar nao pode derrubar o pipeline."""
        conector = ConectorNoaaCrw(
            cliente=ClienteErddapFalso(excecao=ConnectionError('timeout')),
            dormir=Relogio(),
        )

        resultado = conector.coletar(self.local, date(2026, 1, 1), date(2026, 1, 3))

        self.assertTrue(resultado.houve_falha)
        self.assertIn('ConnectionError', resultado.erro)

    def test_local_sem_coordenadas_e_recusado_sem_inventar_bbox(self):
        sem_geo = LocalRecife.objects.create(
            slug='sem-coordenadas',
            nome='Sem Coordenadas',
            estado='Bahia',
            cidade='Caravelas',
        )
        conector = ConectorNoaaCrw(cliente=ClienteErddapFalso(df_crw()))

        resultado = conector.coletar(sem_geo, date(2026, 1, 1), date(2026, 1, 3))

        self.assertTrue(resultado.houve_falha)
        self.assertIn('coordenadas', resultado.erro)

    def test_resposta_vazia_nao_quebra(self):
        conector = ConectorNoaaCrw(cliente=ClienteErddapFalso(pd.DataFrame()))

        resultado = conector.coletar(self.local, date(2026, 1, 1), date(2026, 1, 3))

        self.assertEqual(resultado.observacoes, [])


class AgregacaoEspacialTests(TestCase):
    """A regra de agregacao e por variavel - ver docs/FONTES.md secao 6.16.

    Media de categoria ordinal nao e categoria, e subestima o alerta. Estes
    testes travam o maximo para o BAA e a media para o resto.
    """

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-agregacao', nome='Agregacao', estado='Bahia',
            cidade='Caravelas', latitude=-17.972, longitude=-38.688,
        )

    def _coletar(self, df):
        conector = ConectorNoaaCrw(cliente=ClienteErddapFalso(df))
        return conector.coletar(self.local, date(2026, 3, 17), date(2026, 3, 17))

    def _valor(self, resultado, coluna):
        return next(o.valor for o in resultado.observacoes if o.coluna == coluna)

    def test_baa_usa_o_maximo_e_nao_a_media(self):
        """Reproduz a grade medida em Abrolhos, 17/05/2024.

        A media dava 3,32 -> arredondada para 3 (Alerta Nivel 1), enquanto 45
        dos 121 pixels estavam em Alerta Nivel 2.
        """
        resultado = self._coletar(df_grade_baa(ABROLHOS_2024_05_17))

        self.assertEqual(self._valor(resultado, 'CRW_BAA'), 4)

    def test_media_desta_grade_daria_um_nivel_a_menos(self):
        """Guarda a premissa do teste acima: sem isso ele passaria a toa."""
        media = sum(ABROLHOS_2024_05_17) / len(ABROLHOS_2024_05_17)

        self.assertAlmostEqual(media, 3.3223, places=4)
        self.assertEqual(round(media), 3)
        self.assertEqual(max(ABROLHOS_2024_05_17), 4)

    def test_sst_continua_por_media(self):
        """Grandeza continua nao muda de regra."""
        conector = ConectorNoaaCrw(cliente=ClienteErddapFalso(df_crw(dias=1, sst=28.0)))

        resultado = conector.coletar(self.local, date(2026, 1, 1), date(2026, 1, 1))

        # Os dois pixels sao 27,99 e 28,01.
        self.assertAlmostEqual(self._valor(resultado, 'CRW_SST'), 28.0, places=6)

    def test_fracao_de_area_mede_a_extensao_do_alerta(self):
        """Em 17/05/2024, 115 dos 121 pixels estavam em Alerta Nivel 1+."""
        resultado = self._coletar(df_grade_baa(ABROLHOS_2024_05_17))

        self.assertAlmostEqual(
            self._valor(resultado, 'CRW_BAA_FRACAO_ALERTA'), 115 / 121, places=6
        )

    def test_fracao_distingue_pixel_isolado_de_recife_inteiro(self):
        """O maximo sozinho nao faz essa distincao - e por isso ela existe."""
        um_pixel = self._coletar(df_grade_baa([4] + [0] * 120))
        recife_todo = self._coletar(df_grade_baa([4] * 121))

        self.assertEqual(
            self._valor(um_pixel, 'CRW_BAA'),
            self._valor(recife_todo, 'CRW_BAA'),
        )
        self.assertAlmostEqual(
            self._valor(um_pixel, 'CRW_BAA_FRACAO_ALERTA'), 1 / 121, places=6
        )
        self.assertEqual(self._valor(recife_todo, 'CRW_BAA_FRACAO_ALERTA'), 1.0)

    def test_fracao_conta_do_alerta_nivel_1_para_cima(self):
        """BAA 2 e "Aviso", ainda nao e alerta: nao entra na fracao."""
        resultado = self._coletar(df_grade_baa([2] * 60 + [3] * 40 + [0] * 21))

        self.assertAlmostEqual(
            self._valor(resultado, 'CRW_BAA_FRACAO_ALERTA'), 40 / 121, places=6
        )

    def test_fracao_ignora_pixel_sem_dado_em_vez_de_conta_lo_como_calmo(self):
        """Dividir pelo total da grade diluiria o alerta no dia de pior
        cobertura, que e justamente quando ele mais importa."""
        resultado = self._coletar(df_grade_baa([4] * 10 + [None] * 90 + [0] * 10))

        self.assertAlmostEqual(
            self._valor(resultado, 'CRW_BAA_FRACAO_ALERTA'), 10 / 20, places=6
        )

    def test_fracao_chega_ao_banco_como_variavel_propria(self):
        conector = ConectorNoaaCrw(
            cliente=ClienteErddapFalso(df_grade_baa(ABROLHOS_2024_05_17))
        )

        ingerir(self.local, date(2026, 3, 17), date(2026, 3, 17), conector)

        medicao = MedicaoAmbiental.objects.get(
            local_recife=self.local, variavel='baa_area_alerta'
        )
        self.assertAlmostEqual(medicao.valor, 115 / 121, places=6)
        self.assertEqual(medicao.unidade, 'fração')
        self.assertEqual(medicao.quality_flag, 'ok')

    def test_fracao_nao_e_arredondada_como_o_baa(self):
        """`normalizar` arredonda o BAA por ser ordinal. A fracao e continua."""
        normalizado = normalizar('CRW_BAA_FRACAO_ALERTA', 45 / 121)

        self.assertEqual(normalizado.variavel, 'baa_area_alerta')
        self.assertNotEqual(normalizado.valor, 0.0, 'arredondar zeraria a fracao')
        self.assertEqual(normalizado.valor, 45 / 121)

    def test_fracao_fora_de_zero_a_um_e_reprovada(self):
        self.assertFalse(validar('baa_area_alerta', 1.4).aprovado)
        self.assertTrue(validar('baa_area_alerta', 1.0).aprovado)
        self.assertTrue(validar('baa_area_alerta', 0.0).aprovado)

    def test_dia_sem_baa_valido_nao_inventa_fracao(self):
        resultado = self._coletar(df_grade_baa([None] * 5))

        fracoes = [
            o for o in resultado.observacoes if o.coluna == 'CRW_BAA_FRACAO_ALERTA'
        ]
        self.assertTrue(all(o.valor is None for o in fracoes))

    def test_dataset_sem_baa_nao_gera_fracao(self):
        """Um espelho que nao publique CRW_BAA nao pode quebrar a extracao."""
        df = pd.DataFrame(
            [{'time (UTC)': '2026-03-17T12:00:00Z', 'CRW_SST (degree_C)': 29.0}]
        )

        resultado = self._coletar(df)

        colunas = {o.coluna for o in resultado.observacoes}
        self.assertEqual(colunas, {'CRW_SST'})


class IngestaoTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-ingestao-teste',
            nome='Local de Teste',
            estado='Bahia',
            cidade='Caravelas',
            latitude=-17.972,
            longitude=-38.688,
        )

    def _conector(self, df=None, excecao=None):
        return ConectorNoaaCrw(
            cliente=ClienteErddapFalso(df if df is not None else df_crw(), excecao),
            dormir=Relogio(),
        )

    def test_grava_medicoes_com_proveniencia(self):
        execucao = ingerir(
            self.local, date(2026, 1, 1), date(2026, 1, 3), self._conector()
        )

        self.assertEqual(execucao.status, 'sucesso')
        # 3 datas x 6 variaveis: as 5 do ERDDAP mais a fracao de area derivada.
        self.assertEqual(MedicaoAmbiental.objects.count(), 18)

        sst = MedicaoAmbiental.objects.get(data=date(2026, 1, 1), variavel='sst')
        self.assertEqual(sst.fonte, 'noaa_crw')
        self.assertEqual(sst.unidade, '°C')
        self.assertEqual(sst.quality_flag, 'ok')
        self.assertTrue(sst.dataset_id)

    def test_rodar_duas_vezes_nao_duplica_nem_apaga(self):
        """O pipeline antigo fazia delete_all() antes de cada carga."""
        ingerir(self.local, date(2026, 1, 1), date(2026, 1, 3), self._conector())
        primeira = MedicaoAmbiental.objects.count()

        ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 1, 3),
            self._conector(),
            incremental=False,
        )

        self.assertEqual(MedicaoAmbiental.objects.count(), primeira)
        self.assertGreater(primeira, 0)

    def test_upsert_atualiza_valor_em_vez_de_criar_linha(self):
        ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 1, 3),
            self._conector(df_crw(dias=1, sst=28.0)),
            incremental=False,
        )
        ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 1, 3),
            self._conector(df_crw(dias=1, sst=30.0)),
            incremental=False,
        )

        sst = MedicaoAmbiental.objects.filter(variavel='sst')
        self.assertEqual(sst.count(), 1)
        self.assertAlmostEqual(sst.first().valor, 30.0, places=2)

    def test_modo_incremental_busca_apenas_o_delta(self):
        ingerir(self.local, date(2026, 1, 1), date(2026, 1, 3), self._conector())

        self.assertEqual(
            ultima_data_ingerida(self.local, 'noaa_crw'), date(2026, 1, 3)
        )

        execucao = ingerir(
            self.local, date(2026, 1, 1), date(2026, 1, 3), self._conector()
        )

        self.assertEqual(execucao.status, 'sucesso')
        self.assertIn('ja ingerido', execucao.mensagem_erro)

    def test_falha_e_registrada_em_execucaoingestao(self):
        execucao = ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 1, 3),
            self._conector(excecao=ConnectionError('sem rede')),
        )

        self.assertEqual(execucao.status, 'falha')
        self.assertIn('sem rede', execucao.mensagem_erro)
        self.assertEqual(MedicaoAmbiental.objects.count(), 0)
        self.assertEqual(ExecucaoIngestao.objects.filter(status='falha').count(), 1)

    def test_valor_impossivel_vira_nulo_rastreavel_e_nao_zero(self):
        execucao = ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 1, 3),
            self._conector(df_crw(dias=1, sst=999.0)),
        )

        self.assertEqual(execucao.status, 'parcial')
        self.assertGreater(execucao.registros_rejeitados, 0)

        sst = MedicaoAmbiental.objects.get(variavel='sst')
        self.assertIsNone(sst.valor)
        self.assertEqual(sst.quality_flag, 'invalido')
        self.assertIn('nao como zero', sst.observacao)

    def test_baa_e_gravado_como_target(self):
        """O BAA precisa chegar ao banco - e a variavel resposta da entrega 1."""
        ingerir(self.local, date(2026, 1, 1), date(2026, 1, 3), self._conector())

        baa = MedicaoAmbiental.objects.filter(variavel='baa')
        self.assertEqual(baa.count(), 3)
        self.assertTrue(all(b.valor == 1.0 for b in baa))


class PreparacaoMedicoesTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-prep-teste',
            nome='Local Prep',
            estado='Bahia',
            cidade='Caravelas',
            latitude=-17.972,
            longitude=-38.688,
        )

    def test_coluna_recusada_e_reportada_e_nao_gravada(self):
        from ingestao.base import Observacao, ResultadoColeta

        resultado = ResultadoColeta(
            observacoes=[Observacao(date(2026, 1, 1), 'talk', 2.5)],
            dataset_id='teste',
        )

        medicoes, rejeitadas, recusas = preparar_medicoes(
            self.local, resultado, 'fonte_teste'
        )

        self.assertEqual(medicoes, [])
        self.assertEqual(len(recusas), 1)
        self.assertIn('Alcalinidade', recusas[0])


class TratamentoDeErroTests(TestCase):
    """Regressoes de duas falhas encontradas ao rodar contra o NOAA real.

    1. O erddapy em modo griddap faz HTTP ja no construtor. Montar o cliente
       fora do try deixava a excecao escapar, e a ExecucaoIngestao ficava com
       status 'falha' e mensagem vazia.
    2. Servidores ERDDAP respondem erro com uma pagina HTML inteira, que ia
       parar no banco literalmente.
    """

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-erro-teste',
            nome='Local Erro',
            estado='Bahia',
            cidade='Caravelas',
            latitude=-17.972,
            longitude=-38.688,
        )

    def test_falha_ao_montar_cliente_vira_resultado_e_nao_excecao(self):
        class ConectorQueFalhaNoConstrutor(ConectorNoaaCrw):
            def _montar_cliente(self, bbox, inicio, fim):
                raise ConnectionError('403 Forbidden no .dds')

        relogio = Relogio()
        resultado = ConectorQueFalhaNoConstrutor(dormir=relogio).coletar(
            self.local, date(2026, 1, 1), date(2026, 1, 3)
        )

        self.assertTrue(resultado.houve_falha)
        self.assertIn('403', resultado.erro)
        self.assertEqual(
            relogio.esperas, [], 'Um 403 nao melhora esperando - nao deve repetir'
        )

    def test_execucao_registra_motivo_mesmo_com_excecao_nao_tratada(self):
        class ConectorQuebrado(ConectorNoaaCrw):
            def coletar(self, local, inicio, fim):
                raise RuntimeError('conector mal comportado')

        execucao = ingerir(
            self.local, date(2026, 1, 1), date(2026, 1, 3), ConectorQuebrado()
        )

        self.assertEqual(execucao.status, 'falha')
        self.assertNotEqual(execucao.mensagem_erro, '')
        self.assertIn('mal comportado', execucao.mensagem_erro)

    def test_pagina_html_de_erro_nao_vai_inteira_para_o_banco(self):
        html = (
            '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">\n<html>\n'
            '<head><title>403 Forbidden</title></head>\n<body>\n'
            "<h1>Forbidden</h1>\n<p>You don't have permission to access "
            '/erddap/griddap/NOAA_DHW.dds on this server.</p>\n'
            '</body></html>\n' + ('<p>ruido</p>\n' * 200)
        )

        class ConectorComHtml(ConectorNoaaCrw):
            def _montar_cliente(self, bbox, inicio, fim):
                raise OSError(html)

        execucao = ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 1, 3),
            ConectorComHtml(dormir=Relogio()),
        )

        self.assertEqual(execucao.status, 'falha')
        self.assertLess(len(execucao.mensagem_erro), 500)
        self.assertNotIn('<html', execucao.mensagem_erro)
        self.assertNotIn('<p>', execucao.mensagem_erro)
        self.assertIn('OSError', execucao.mensagem_erro)
        self.assertIn('Forbidden', execucao.mensagem_erro)

    def test_resumir_erro_preserva_tipo_quando_mensagem_vazia(self):
        self.assertEqual(resumir_erro(ValueError('')), 'ValueError')


class ResumoDeErroTests(TestCase):
    """Resumir nao pode custar a causa do erro.

    Regressao: a deteccao de HTML era "tem < e tem >", e o URLError do Python
    formata a mensagem como "<urlopen error [SSL: ...]>". O resumo apagava a
    mensagem inteira e gravava so "URLError" - pior do que nao resumir.
    """

    def test_urlerror_preserva_a_causa(self):
        import ssl
        import urllib.error

        exc = urllib.error.URLError(
            ssl.SSLCertVerificationError(
                '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed'
            )
        )

        resumo = resumir_erro(exc)

        self.assertIn('URLError', resumo)
        self.assertIn('CERTIFICATE_VERIFY_FAILED', resumo)

    def test_mensagem_com_angulares_nao_e_confundida_com_html(self):
        resumo = resumir_erro(ValueError('valor <esperado> nao encontrado'))

        self.assertIn('esperado', resumo)

    def test_pagina_html_continua_sendo_resumida(self):
        html = (
            '<!DOCTYPE HTML><html><head><title>403</title></head>'
            '<body><h1>Forbidden</h1><p>No permission.</p></body></html>'
        )

        resumo = resumir_erro(OSError(html))

        self.assertNotIn('<html', resumo)
        self.assertNotIn('<p>', resumo)
        self.assertIn('Forbidden', resumo)

    def test_parece_documento_html_distingue_os_dois_casos(self):
        self.assertTrue(parece_documento_html('<!DOCTYPE html><html>...'))
        self.assertTrue(parece_documento_html('<body>erro</body>'))
        self.assertFalse(parece_documento_html('<urlopen error timed out>'))
        self.assertFalse(parece_documento_html('a < b and b > c'))


class ConstraintsGriddapTests(TestCase):
    """Traducao da bbox para o vocabulario do griddap.

    Regressao de 25/07/2026: o conector substituia `e.constraints` por um
    dicionario proprio, e o erddapy recusava com "keys in e.constraints have
    changed" - ele exige exatamente as chaves que `griddap_initialize()` criou,
    inclusive as `*_step`, que o codigo nao conhecia.
    """

    BBOX = (-38.94, -18.22, -38.44, -17.72)  # lon_min, lat_min, lon_max, lat_max

    def _dataset(self, lat=(-89.975, 89.975), lon=(-179.975, 179.975), passo=1):
        """Constraints como o erddapy as monta apos griddap_initialize()."""
        return {
            'time>=': '2026-07-24T12:00:00Z',
            'time<=': '2026-07-24T12:00:00Z',
            'time_step': passo,
            'latitude>=': lat[0],
            'latitude<=': lat[1],
            'latitude_step': passo,
            'longitude>=': lon[0],
            'longitude<=': lon[1],
            'longitude_step': passo,
        }

    def _dims(self):
        return ['time', 'latitude', 'longitude']

    def test_atualizar_preserva_o_conjunto_de_chaves(self):
        """A regressao em si: o erddapy compara `keys()`, nao valores."""
        original = self._dataset()
        antes = set(original.keys())

        atualizacao = montar_constraints(
            original, self._dims(), self.BBOX, date(2026, 7, 1), date(2026, 7, 25)
        )
        original.update(atualizacao)

        self.assertEqual(set(original.keys()), antes)
        self.assertEqual(original['latitude_step'], 1, 'o passo nao pode sumir')

    def test_periodo_vira_texto_iso(self):
        constraints = montar_constraints(
            self._dataset(),
            self._dims(),
            self.BBOX,
            date(2026, 7, 1),
            date(2026, 7, 25),
        )

        self.assertEqual(constraints['time>='], '2026-07-01')
        self.assertEqual(constraints['time<='], '2026-07-25')

    def test_eixo_crescente_mantem_a_ordem_numerica(self):
        constraints = montar_constraints(
            self._dataset(),
            self._dims(),
            self.BBOX,
            date(2026, 7, 1),
            date(2026, 7, 25),
        )

        self.assertAlmostEqual(constraints['latitude>='], -18.22)
        self.assertAlmostEqual(constraints['latitude<='], -17.72)

    def test_eixo_descendente_inverte_a_faixa(self):
        """Latitude gravada de 90 para -90: pedir na ordem numerica da vazio."""
        constraints = montar_constraints(
            self._dataset(lat=(89.975, -89.975)),
            self._dims(),
            self.BBOX,
            date(2026, 7, 1),
            date(2026, 7, 25),
        )

        self.assertAlmostEqual(constraints['latitude>='], -17.72)
        self.assertAlmostEqual(constraints['latitude<='], -18.22)

    def test_dataset_em_0_360_converte_a_longitude(self):
        """Pedir -38,7 num dataset 0..360 nao da erro - devolve vazio."""
        constraints = montar_constraints(
            self._dataset(lon=(0.025, 359.975)),
            self._dims(),
            self.BBOX,
            date(2026, 7, 1),
            date(2026, 7, 25),
        )

        self.assertAlmostEqual(constraints['longitude>='], 321.06)
        self.assertAlmostEqual(constraints['longitude<='], 321.56)

    def test_dataset_em_menos180_180_nao_mexe_na_longitude(self):
        constraints = montar_constraints(
            self._dataset(),
            self._dims(),
            self.BBOX,
            date(2026, 7, 1),
            date(2026, 7, 25),
        )

        self.assertAlmostEqual(constraints['longitude>='], -38.94)

    def test_dimensoes_com_nome_curto_sao_reconhecidas(self):
        dataset = {
            'time>=': 'x', 'time<=': 'x', 'time_step': 1,
            'lat>=': -89.9, 'lat<=': 89.9, 'lat_step': 1,
            'lon>=': -179.9, 'lon<=': 179.9, 'lon_step': 1,
        }

        constraints = montar_constraints(
            dataset,
            ['time', 'lat', 'lon'],
            self.BBOX,
            date(2026, 7, 1),
            date(2026, 7, 25),
        )

        self.assertIn('lat>=', constraints)
        self.assertNotIn('latitude>=', constraints)

    def test_dimensao_ausente_diz_o_que_o_dataset_publica(self):
        with self.assertRaises(ValueError) as ctx:
            montar_constraints(
                {'time>=': 'x', 'time<=': 'x', 'time_step': 1},
                ['time', 'depth'],
                self.BBOX,
                date(2026, 7, 1),
                date(2026, 7, 25),
            )

        self.assertIn('latitude', str(ctx.exception))
        self.assertIn('depth', str(ctx.exception))


class DividirPeriodoTests(TestCase):
    """Fatiamento do periodo em blocos.

    Regressao de 25/07/2026: pedir 2020-2026 de uma vez fez o ERDDAP responder
    ReadTimeout e HTTP 408 nos tres locais, e o backfill inteiro terminou com
    zero medicoes.
    """

    def test_periodo_curto_vira_um_bloco_so(self):
        blocos = list(dividir_periodo(date(2026, 7, 1), date(2026, 7, 25), 180))

        self.assertEqual(blocos, [(date(2026, 7, 1), date(2026, 7, 25))])

    def test_blocos_sao_contiguos_e_sem_sobreposicao(self):
        blocos = list(dividir_periodo(date(2020, 1, 1), date(2026, 7, 23), 180))

        self.assertEqual(blocos[0][0], date(2020, 1, 1))
        self.assertEqual(blocos[-1][1], date(2026, 7, 23))
        for (_, fim_anterior), (inicio, _) in zip(blocos, blocos[1:]):
            self.assertEqual(inicio - fim_anterior, timedelta(days=1))

    def test_nenhum_bloco_passa_da_janela(self):
        blocos = list(dividir_periodo(date(2020, 1, 1), date(2026, 7, 23), 180))

        for inicio, fim in blocos:
            self.assertLessEqual((fim - inicio).days + 1, 180)

    def test_seis_anos_viram_poucos_blocos(self):
        blocos = list(dividir_periodo(date(2020, 1, 1), date(2026, 7, 23), 180))

        self.assertEqual(len(blocos), 14)

    def test_um_unico_dia(self):
        blocos = list(dividir_periodo(date(2026, 7, 1), date(2026, 7, 1), 180))

        self.assertEqual(blocos, [(date(2026, 7, 1), date(2026, 7, 1))])

    def test_janela_invalida_e_recusada(self):
        with self.assertRaises(ValueError):
            list(dividir_periodo(date(2026, 7, 1), date(2026, 7, 25), 0))


class IngestaoPorBlocosTests(TestCase):
    """Um bloco que falha nao pode levar junto os que deram certo."""

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-blocos-teste',
            nome='Local Blocos',
            estado='Bahia',
            cidade='Caravelas',
            latitude=-17.972,
            longitude=-38.688,
        )

    class ConectorPorBloco(ConectorNoaaCrw):
        """Devolve um dia de dado por bloco; falha nos blocos escolhidos."""

        def __init__(self, blocos_que_falham=(), **kw):
            super().__init__(**kw)
            self.blocos_que_falham = set(blocos_que_falham)
            self.chamadas = []

        def coletar(self, local, inicio, fim):
            numero = len(self.chamadas) + 1
            self.chamadas.append((inicio, fim))
            if numero in self.blocos_que_falham:
                return ResultadoColeta(erro=f'falha simulada no bloco {numero}')
            return self._extrair(df_crw(dias=1))

    def test_periodo_longo_e_dividido_em_varias_chamadas(self):
        conector = self.ConectorPorBloco(dormir=Relogio())

        ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 12, 31),
            conector,
            janela_dias=90,
        )

        self.assertEqual(len(conector.chamadas), 5)
        self.assertEqual(conector.chamadas[0][0], date(2026, 1, 1))
        self.assertEqual(conector.chamadas[-1][1], date(2026, 12, 31))

    def test_bloco_com_falha_nao_descarta_os_que_deram_certo(self):
        conector = self.ConectorPorBloco(blocos_que_falham=[2], dormir=Relogio())

        execucao = ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 12, 31),
            conector,
            janela_dias=90,
        )

        self.assertEqual(execucao.status, 'parcial')
        self.assertGreater(execucao.registros_gravados, 0)
        self.assertIn('falha simulada no bloco 2', execucao.mensagem_erro)

    def test_todos_os_blocos_falhando_e_falha(self):
        conector = self.ConectorPorBloco(
            blocos_que_falham=range(1, 10), dormir=Relogio()
        )

        execucao = ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 12, 31),
            conector,
            janela_dias=90,
        )

        self.assertEqual(execucao.status, 'falha')
        self.assertEqual(execucao.registros_gravados, 0)

    def test_para_apos_falhas_seguidas_em_vez_de_insistir(self):
        """Fonte fora do ar nao deve gastar o backoff completo em cada bloco."""
        conector = self.ConectorPorBloco(
            blocos_que_falham=range(1, 60), dormir=Relogio()
        )

        execucao = ingerir(
            self.local,
            date(2020, 1, 1),
            date(2026, 7, 23),
            conector,
            janela_dias=30,
        )

        self.assertEqual(len(conector.chamadas), 3)
        self.assertIn('nao foram tentados', execucao.mensagem_erro)

    def test_falhas_isoladas_nao_interrompem_o_backfill(self):
        """Tres falhas espalhadas nao sao tres seguidas."""
        conector = self.ConectorPorBloco(
            blocos_que_falham=[2, 4, 6], dormir=Relogio()
        )

        ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 12, 31),
            conector,
            janela_dias=45,
        )

        self.assertEqual(len(conector.chamadas), 9, 'nenhum bloco pode ser pulado')

    def test_progresso_reporta_cada_bloco(self):
        linhas = []
        conector = self.ConectorPorBloco(dormir=Relogio())

        ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 12, 31),
            conector,
            janela_dias=90,
            progresso=linhas.append,
        )

        self.assertEqual(len(linhas), 5)
        self.assertIn('bloco 1/5', linhas[0])

    def test_nota_repetida_aparece_uma_vez_so(self):
        class ConectorComNota(self.ConectorPorBloco):
            def coletar(self, local, inicio, fim):
                resultado = super().coletar(local, inicio, fim)
                resultado.nota = 'Periodo encolhido.'
                return resultado

        execucao = ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 12, 31),
            ConectorComNota(dormir=Relogio()),
            janela_dias=90,
        )

        self.assertEqual(execucao.mensagem_erro.count('Periodo encolhido.'), 1)


class LimitarPeriodoTests(TestCase):
    """Atraso de publicacao do satelite.

    Regressao de 25/07/2026: o dataset ia ate 23/07, o comando pediu ate hoje
    (25/07) e o ERDDAP respondeu 404 - a coleta inteira caiu por causa de dois
    dias que ainda nao existiam.
    """

    def test_encolhe_ate_o_fim_do_eixo(self):
        inicio, fim, nota = limitar_periodo(
            date(2026, 7, 1), date(2026, 7, 25), '2026-07-23T12:00:00Z'
        )

        self.assertEqual(inicio, date(2026, 7, 1))
        self.assertEqual(fim, date(2026, 7, 23))
        self.assertIn('2026-07-23', nota)

    def test_periodo_dentro_do_eixo_passa_intacto(self):
        inicio, fim, nota = limitar_periodo(
            date(2026, 7, 1), date(2026, 7, 20), '2026-07-23T12:00:00Z'
        )

        self.assertEqual(fim, date(2026, 7, 20))
        self.assertEqual(nota, '')

    def test_janela_inteira_no_futuro_nao_e_falha(self):
        with self.assertRaises(PeriodoIndisponivel) as ctx:
            limitar_periodo(
                date(2026, 7, 24), date(2026, 7, 25), '2026-07-23T12:00:00Z'
            )

        self.assertIn('2026-07-23', str(ctx.exception))

    def test_eixo_em_epoch_tambem_e_lido(self):
        """Alguns servidores ERDDAP publicam o tempo como epoch em segundos."""
        epoch = datetime(2026, 7, 23, 12, tzinfo=timezone.utc).timestamp()

        _inicio, fim, _nota = limitar_periodo(
            date(2026, 7, 1), date(2026, 7, 25), epoch
        )

        self.assertEqual(fim, date(2026, 7, 23))

    def test_eixo_ilegivel_nao_trava_a_coleta(self):
        inicio, fim, nota = limitar_periodo(
            date(2026, 7, 1), date(2026, 7, 25), 'formato inesperado'
        )

        self.assertEqual((inicio, fim), (date(2026, 7, 1), date(2026, 7, 25)))
        self.assertEqual(nota, '')


class NotaDeColetaTests(TestCase):
    """A nota chega ao banco sem rebaixar o status da execucao."""

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-nota-teste',
            nome='Local Nota',
            estado='Bahia',
            cidade='Caravelas',
            latitude=-17.972,
            longitude=-38.688,
        )

    def test_periodo_indisponivel_grava_sucesso_com_explicacao(self):
        class ConectorSemDadoNovo(ConectorNoaaCrw):
            def _montar_cliente(self, bbox, inicio, fim):
                raise PeriodoIndisponivel('O dataset vai ate 2026-07-23.')

        execucao = ingerir(
            self.local,
            date(2026, 7, 24),
            date(2026, 7, 25),
            ConectorSemDadoNovo(dormir=Relogio()),
        )

        self.assertEqual(execucao.status, 'sucesso')
        self.assertEqual(execucao.registros_gravados, 0)
        self.assertIn('2026-07-23', execucao.mensagem_erro)

    def test_periodo_indisponivel_nao_gasta_retentativa(self):
        relogio = Relogio()

        class ConectorSemDadoNovo(ConectorNoaaCrw):
            def _montar_cliente(self, bbox, inicio, fim):
                raise PeriodoIndisponivel('sem dado novo')

        ConectorSemDadoNovo(dormir=relogio).coletar(
            self.local, date(2026, 7, 24), date(2026, 7, 25)
        )

        self.assertEqual(relogio.esperas, [])


class VariaveisPublicadasTests(TestCase):
    """O erddapy recusa a consulta inteira se pedirmos algo que nao existe."""

    def test_pede_apenas_o_que_o_espelho_publica(self):
        conector = ConectorNoaaCrw()

        pedidas = conector._variaveis_publicadas(
            ['CRW_SST', 'CRW_DHW', 'CRW_BAA', 'mask', 'CRW_SEAICE']
        )

        self.assertEqual(pedidas, ['CRW_SST', 'CRW_DHW', 'CRW_BAA'])

    def test_dataset_sem_nenhuma_variavel_esperada_falha_com_orientacao(self):
        conector = ConectorNoaaCrw()

        with self.assertRaises(ValueError) as ctx:
            conector._variaveis_publicadas(['analysed_sst', 'mask'])

        self.assertIn('testar_fontes', str(ctx.exception))


class BundleDeCertificadosTests(TestCase):
    """A cadeia de confianca TLS usada pelas fontes externas.

    Regressao de 25/07/2026: no PC da faculdade a ingestao falhava com
    CERTIFICATE_VERIFY_FAILED porque o `pandas.read_csv(url)` busca pelo
    urllib, que no Windows nao usa o certifi como o `requests` usa.
    """

    def setUp(self):
        self._ambiente = {
            v: os.environ.get(v)
            for v in ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'SSL_CERT_DIR')
        }
        for variavel in self._ambiente:
            os.environ.pop(variavel, None)

    def tearDown(self):
        for variavel, valor in self._ambiente.items():
            if valor is None:
                os.environ.pop(variavel, None)
            else:
                os.environ[variavel] = valor

    def test_define_o_bundle_quando_ninguem_definiu(self):
        caminho = garantir_bundle_ca()

        self.assertIsNotNone(caminho, 'certifi deveria estar instalado')
        self.assertTrue(os.path.exists(caminho))
        self.assertEqual(os.environ['SSL_CERT_FILE'], caminho)
        self.assertEqual(os.environ['REQUESTS_CA_BUNDLE'], caminho)

    def test_respeita_bundle_ja_definido_no_ambiente(self):
        """Um SSL_CERT_FILE existente costuma ser a raiz da instituicao."""
        os.environ['SSL_CERT_FILE'] = 'C:\\ti\\raiz-da-faculdade.pem'

        caminho = garantir_bundle_ca()

        self.assertEqual(caminho, 'C:\\ti\\raiz-da-faculdade.pem')
        self.assertEqual(os.environ['SSL_CERT_FILE'], 'C:\\ti\\raiz-da-faculdade.pem')

    def test_e_idempotente(self):
        primeiro = garantir_bundle_ca()

        self.assertEqual(garantir_bundle_ca(), primeiro)

    def test_contexto_do_sistema_ignora_o_certifi(self):
        """Sem isso o diagnostico compararia o certifi com ele mesmo."""
        garantir_bundle_ca()

        contexto_do_sistema()

        self.assertIn(
            'SSL_CERT_FILE', os.environ, 'a variavel precisa ser restaurada depois'
        )


class InterpretacaoSslTests(TestCase):
    """Traducao do diagnostico em conclusao acionavel."""

    def _diagnostico(self, sistema, certifi_):
        return {
            'host': 'exemplo.org',
            'sistema': sistema,
            'certifi': certifi_,
            'bundle_certifi': 'cacert.pem',
            'nomes_no_certificado': [],
        }

    def test_so_o_certifi_funciona_e_o_caso_do_windows(self):
        veredito, _ = interpretar(
            self._diagnostico(
                'SSLCertVerificationError: unable to get local issuer certificate',
                None,
            )
        )

        self.assertEqual(veredito, 'certifi')

    def test_nenhum_dos_dois_verifica_sugere_interceptacao(self):
        veredito, texto = interpretar(
            self._diagnostico(
                'SSLCertVerificationError: self signed certificate in chain',
                'SSLCertVerificationError: self signed certificate in chain',
            )
        )

        self.assertEqual(veredito, 'interceptacao')
        self.assertIn('Nao desligue a verificacao', texto)

    def test_timeout_nao_e_diagnosticado_como_certificado(self):
        """Porta bloqueada tem outro conserto - foi o caso da maquina de casa."""
        veredito, _ = interpretar(
            self._diagnostico('TimeoutError: timed out', 'TimeoutError: timed out')
        )

        self.assertEqual(veredito, 'inalcancavel')

    def test_tudo_verificando_nao_culpa_o_certificado(self):
        veredito, _ = interpretar(self._diagnostico(None, None))

        self.assertEqual(veredito, 'ok')


class ClassificacaoDeFalhaTests(TestCase):
    """Separar o que melhora esperando do que nao melhora nunca."""

    def test_503_do_erddap_e_passageiro(self):
        self.assertTrue(e_transitorio(OSError(ERRO_503_ERDDAP)))

    def test_certificado_invalido_nao_e_passageiro(self):
        import ssl
        import urllib.error

        exc = urllib.error.URLError(
            ssl.SSLCertVerificationError(
                '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed'
            )
        )

        self.assertFalse(e_transitorio(exc))

    def test_403_dentro_de_connectionerror_nao_e_passageiro(self):
        """O tipo da excecao mente; o status manda."""
        self.assertFalse(e_transitorio(ConnectionError('403 Forbidden no .dds')))

    def test_timeout_e_passageiro(self):
        self.assertTrue(e_transitorio(TimeoutError()))
        self.assertTrue(e_transitorio(OSError('<urlopen error timed out>')))

    def test_404_nao_e_passageiro(self):
        self.assertFalse(e_transitorio(OSError('Error { code=404; }')))

    def test_erro_de_programacao_nao_e_passageiro(self):
        self.assertFalse(e_transitorio(KeyError('CRW_SST')))


class RetentativaTests(TestCase):
    def test_repete_ate_o_servidor_se_recuperar(self):
        tentativas = []

        def instavel():
            tentativas.append(1)
            if len(tentativas) < 3:
                raise OSError(ERRO_503_ERDDAP)
            return 'dados'

        relogio = Relogio()
        resultado = executar_com_retentativa(instavel, dormir=relogio)

        self.assertEqual(resultado, 'dados')
        self.assertEqual(len(tentativas), 3)
        self.assertEqual(len(relogio.esperas), 2)

    def test_espera_cresce_entre_as_tentativas(self):
        relogio = Relogio()

        with self.assertRaises(OSError):
            executar_com_retentativa(
                lambda: (_ for _ in ()).throw(OSError(ERRO_503_ERDDAP)),
                dormir=relogio,
            )

        self.assertEqual(relogio.esperas, [10.0, 30.0])

    def test_desiste_preservando_a_excecao_original(self):
        """Quem chama precisa ver a causa real, nao um erro deste modulo."""
        with self.assertRaises(OSError) as ctx:
            executar_com_retentativa(
                lambda: (_ for _ in ()).throw(OSError(ERRO_503_ERDDAP)),
                dormir=Relogio(),
            )

        self.assertIn('503', str(ctx.exception))

    def test_falha_definitiva_falha_de_primeira(self):
        chamadas = []
        relogio = Relogio()

        def negado():
            chamadas.append(1)
            raise PermissionError('403 Forbidden')

        with self.assertRaises(PermissionError):
            executar_com_retentativa(negado, dormir=relogio)

        self.assertEqual(len(chamadas), 1)
        self.assertEqual(relogio.esperas, [])

    def test_sucesso_na_primeira_nao_espera(self):
        relogio = Relogio()

        self.assertEqual(
            executar_com_retentativa(lambda: 'ok', dormir=relogio), 'ok'
        )
        self.assertEqual(relogio.esperas, [])


class RetentativaNoConectorTests(TestCase):
    """O 503 do ERDDAP visto de dentro do conector.

    Caso real de 25/07/2026: a ingestao na rede da faculdade desistiu no
    primeiro 503, apesar de o proprio servidor pedir para tentar de novo.
    """

    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='local-retentativa-teste',
            nome='Local Retentativa',
            estado='Bahia',
            cidade='Caravelas',
            latitude=-17.972,
            longitude=-38.688,
        )

    def test_503_passageiro_nao_perde_a_coleta(self):
        relogio = Relogio()
        cliente = ClienteErddapFalso(
            df_crw(dias=3),
            excecao=OSError(ERRO_503_ERDDAP),
            falhas_iniciais=2,
        )

        execucao = ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 1, 3),
            ConectorNoaaCrw(cliente=cliente, dormir=relogio),
        )

        self.assertEqual(execucao.status, 'sucesso')
        self.assertEqual(cliente.chamadas, 3)
        self.assertEqual(MedicaoAmbiental.objects.count(), 18)

    def test_503_persistente_registra_a_causa_completa(self):
        cliente = ClienteErddapFalso(excecao=OSError(ERRO_503_ERDDAP))

        execucao = ingerir(
            self.local,
            date(2026, 1, 1),
            date(2026, 1, 3),
            ConectorNoaaCrw(cliente=cliente, dormir=Relogio(), tentativas=2),
        )

        self.assertEqual(execucao.status, 'falha')
        self.assertEqual(cliente.chamadas, 2)
        self.assertIn('503', execucao.mensagem_erro)
        self.assertIn('Service Unavailable', execucao.mensagem_erro)
