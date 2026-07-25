"""Testes do pipeline de ingestao.

Sem rede: o cliente ERDDAP e substituido por um duble que devolve um
DataFrame conhecido. Isso cobre normalizacao, validacao fisica, upsert
idempotente e tratamento de falha - tudo menos a chamada HTTP em si, que
precisa ser verificada na maquina do usuario.
"""

from datetime import date, timedelta

import pandas as pd
from django.test import TestCase

from aquaculture.models import ExecucaoIngestao, LocalRecife, MedicaoAmbiental
from ingestao.conectores.noaa_crw import ConectorNoaaCrw
from ingestao.erros import resumir_erro
from ingestao.normalizacao import ColunaRecusada, normalizar, resolver_variavel
from ingestao.persistencia import preparar_medicoes, ultima_data_ingerida
from ingestao.qualidade import detectar_saltos, validar
from ingestao.registro import ingerir


class ClienteErddapFalso:
    """Duble do cliente ERDDAP."""

    def __init__(self, df=None, excecao=None):
        self._df = df
        self._excecao = excecao
        self.chamadas = 0

    def to_pandas(self):
        self.chamadas += 1
        if self._excecao:
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
        self.assertEqual(len(datas), 3, 'Os 2 pixels por data deviam virar 1 media')
        colunas = {o.coluna for o in resultado.observacoes}
        self.assertEqual(colunas, set(ConectorNoaaCrw.variaveis and
                                      ['CRW_SST', 'CRW_DHW', 'CRW_BAA',
                                       'CRW_HOTSPOT', 'CRW_SSTANOMALY']))

    def test_falha_de_rede_nao_levanta_excecao(self):
        """Uma fonte fora do ar nao pode derrubar o pipeline."""
        conector = ConectorNoaaCrw(
            cliente=ClienteErddapFalso(excecao=ConnectionError('timeout'))
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
            cliente=ClienteErddapFalso(df if df is not None else df_crw(), excecao)
        )

    def test_grava_medicoes_com_proveniencia(self):
        execucao = ingerir(
            self.local, date(2026, 1, 1), date(2026, 1, 3), self._conector()
        )

        self.assertEqual(execucao.status, 'sucesso')
        self.assertEqual(MedicaoAmbiental.objects.count(), 15)  # 3 datas x 5 variaveis

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

        resultado = ConectorQueFalhaNoConstrutor().coletar(
            self.local, date(2026, 1, 1), date(2026, 1, 3)
        )

        self.assertTrue(resultado.houve_falha)
        self.assertIn('403', resultado.erro)

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
            self.local, date(2026, 1, 1), date(2026, 1, 3), ConectorComHtml()
        )

        self.assertEqual(execucao.status, 'falha')
        self.assertLess(len(execucao.mensagem_erro), 500)
        self.assertNotIn('<html', execucao.mensagem_erro)
        self.assertNotIn('<p>', execucao.mensagem_erro)
        self.assertIn('OSError', execucao.mensagem_erro)
        self.assertIn('Forbidden', execucao.mensagem_erro)

    def test_resumir_erro_preserva_tipo_quando_mensagem_vazia(self):
        self.assertEqual(resumir_erro(ValueError('')), 'ValueError')
