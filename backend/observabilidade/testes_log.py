"""O que estes testes protegem, e por que cada um existe.

⚠️ **Log e a camada mais facil de quebrar sem ninguem notar**, porque ninguem
le log quando esta tudo bem — e quando alguem le, e durante uma falha, que e o
pior momento para descobrir que o rastro nao existe. Os testes aqui fixam as
tres propriedades das quais a auditoria depende:

1. a correlacao acompanha o fluxo sem ser repetida a mao;
2. credencial nao vaza para o arquivo;
3. o JSON continua sendo uma linha por evento, parseavel.
"""

import io
import json
import logging
import threading

from django.test import SimpleTestCase

from .config import montar, rodando_teste
from .correlacao import (
    FiltroCorrelacao,
    contexto,
    contexto_atual,
    correlacao_atual,
    mascarar,
)
from .formatadores import JsonLinhas, TextoLegivel


def _registro(mensagem='oi', nivel=logging.INFO, **extras):
    """Um LogRecord passado pelo filtro, como o handler o receberia."""
    registro = logging.LogRecord(
        name='ingestao.conectores.noaa_crw', level=nivel,
        pathname='/app/ingestao/conectores/noaa_crw.py', lineno=42,
        msg=mensagem, args=(), exc_info=None, func='coletar',
    )
    for chave, valor in extras.items():
        setattr(registro, chave, valor)
    FiltroCorrelacao().filter(registro)
    return registro


class ContextoTests(SimpleTestCase):
    def test_fora_de_fluxo_nao_ha_correlacao(self):
        self.assertIsNone(correlacao_atual())
        self.assertEqual(contexto_atual(), {})

    def test_o_id_e_gerado_uma_vez_e_herdado_pelos_aninhados(self):
        """🚨 O ponto inteiro da camada.

        `qualidade.py` e `persistencia.py` nao importam `observabilidade` e
        mesmo assim precisam sair com o id do bloco que os chamou. Se o
        aninhamento gerasse id novo, cada camada viraria um fluxo separado e
        "ponta a ponta" deixaria de existir.
        """
        with contexto(fluxo='ingestao', fonte='noaa-crw') as externo:
            with contexto(bloco='2020-01-01 a 2020-06-28') as interno:
                self.assertEqual(interno, externo)
                atual = contexto_atual()
                self.assertEqual(atual['fonte'], 'noaa-crw')
                self.assertEqual(atual['bloco'], '2020-01-01 a 2020-06-28')

    def test_sair_do_bloco_restaura_o_contexto_anterior(self):
        with contexto(fluxo='ingestao'):
            with contexto(bloco='x'):
                pass
            self.assertNotIn('bloco', contexto_atual())
        self.assertEqual(contexto_atual(), {})

    def test_campo_nulo_nao_entra(self):
        """Ausencia e ausencia.

        Uma coleta global nao tem local. Gravar `local=None` se le como "havia
        um local e ele era vazio", que e outra afirmacao.
        """
        with contexto(fluxo='ingestao', local=None):
            self.assertNotIn('local', contexto_atual())

    def test_correlacao_explicita_continua_um_fluxo_de_fora(self):
        with contexto(fluxo='cron', correlacao='abc123') as identificador:
            self.assertEqual(identificador, 'abc123')

    def test_contexto_atual_devolve_copia(self):
        with contexto(fluxo='ingestao'):
            copia = contexto_atual()
            copia['fluxo'] = 'adulterado'
            self.assertEqual(contexto_atual()['fluxo'], 'ingestao')

    def test_threads_nao_veem_o_contexto_uma_da_outra(self):
        """⚠️ A razao de ser `contextvars` e nao variavel de modulo.

        Com uma global, a thread B leria o fluxo da thread A — e o log de uma
        ingestao apareceria carimbado com a correlacao de outra.
        """
        vistos = []

        def sem_contexto():
            vistos.append(correlacao_atual())

        with contexto(fluxo='ingestao'):
            outra = threading.Thread(target=sem_contexto)
            outra.start()
            outra.join()

        self.assertEqual(vistos, [None])


class MascaramentoTests(SimpleTestCase):
    def test_mascara_por_substring_e_sem_diferenciar_maiuscula(self):
        mascarado = mascarar({
            'DATABASE_URL': 'postgres://u:senha@host/db',
            'neo4j_password': 'segredo',
            'API_TOKEN': 'abc',
            'local': 'abrolhos-ba',
        })
        self.assertEqual(mascarado['DATABASE_URL'], '***')
        self.assertEqual(mascarado['neo4j_password'], '***')
        self.assertEqual(mascarado['API_TOKEN'], '***')
        self.assertEqual(mascarado['local'], 'abrolhos-ba')

    def test_credencial_no_contexto_nao_chega_ao_registro(self):
        with contexto(fluxo='ingestao', senha_copernicus='segredo'):
            registro = _registro()
        self.assertEqual(registro.contexto['senha_copernicus'], '***')

    def test_credencial_no_extra_nao_chega_ao_json(self):
        registro = _registro(token='abc123')
        linha = json.loads(JsonLinhas().format(registro))
        self.assertEqual(linha['dados']['token'], '***')


class FormatadoresTests(SimpleTestCase):
    def test_json_e_uma_linha_por_evento(self):
        """🚨 A propriedade que torna o arquivo auditavel.

        Se um valor com quebra de linha vazasse cru, a linha deixaria de ser
        JSON Lines e o arquivo inteiro pararia de ser parseavel a partir dali.
        """
        registro = _registro('primeira\nsegunda', nota='a\nb')
        saida = JsonLinhas().format(registro)
        self.assertNotIn('\n', saida)
        self.assertEqual(json.loads(saida)['mensagem'], 'primeira\nsegunda')

    def test_json_traz_arquivo_linha_e_funcao(self):
        """A granularidade "por classe/arquivo" pedida, sem separar arquivos."""
        linha = json.loads(JsonLinhas().format(_registro()))
        self.assertEqual(linha['arquivo'], '/app/ingestao/conectores/noaa_crw.py:42')
        self.assertEqual(linha['funcao'], 'coletar')
        self.assertEqual(linha['logger'], 'ingestao.conectores.noaa_crw')

    def test_extra_vira_campo_e_nao_texto(self):
        """⚠️ O que separa log auditavel de prosa.

        `medicoes=406` como campo pode ser somado depois; embutido na frase, so
        volta a ser numero por regex sobre texto livre.
        """
        linha = json.loads(JsonLinhas().format(_registro(medicoes=406)))
        self.assertEqual(linha['dados']['medicoes'], 406)

    def test_json_nao_quebra_com_tipo_que_nao_serializa(self):
        """Log que levanta excecao derruba o fluxo que ele so ia relatar."""
        import datetime as dt
        linha = json.loads(
            JsonLinhas().format(_registro(dia=dt.date(2026, 8, 12)))
        )
        self.assertEqual(linha['dados']['dia'], '2026-08-12')

    def test_json_guarda_o_traceback_em_campo_proprio(self):
        try:
            raise ValueError('erddap 408')
        except ValueError:
            import sys
            registro = logging.LogRecord(
                name='ingestao', level=logging.ERROR, pathname='x.py',
                lineno=1, msg='falhou', args=(), exc_info=sys.exc_info(),
            )
            FiltroCorrelacao().filter(registro)
        linha = json.loads(JsonLinhas().format(registro))
        self.assertIn('ValueError: erddap 408', linha['erro'])
        self.assertNotIn('\n', JsonLinhas().format(registro))

    def test_texto_legivel_traz_a_correlacao_no_inicio(self):
        with contexto(fluxo='ingestao', correlacao='a3f9c1d20b74'):
            registro = _registro('Coleta iniciada')
        linha = TextoLegivel().format(registro)
        self.assertIn('[a3f9c1d20b74]', linha)
        self.assertIn('Coleta iniciada', linha)

    def test_texto_legivel_anexa_os_extras(self):
        registro = _registro('Bloco gravado', medicoes=406)
        self.assertIn('medicoes=406', TextoLegivel().format(registro))


class ConfiguracaoTests(SimpleTestCase):
    def test_sem_arquivo_so_ha_console(self):
        config = montar(base_dir=None, em_arquivo=False)
        self.assertEqual(list(config['handlers']), ['console'])

    def test_com_arquivo_ha_unificado_e_so_erros(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as pasta:
            config = montar(base_dir=Path(pasta), pasta=Path(pasta) / 'logs')
        self.assertEqual(
            sorted(config['handlers']), ['arquivo', 'console', 'erros']
        )
        self.assertEqual(config['handlers']['erros']['level'], 'ERROR')

    def test_console_escreve_em_stderr(self):
        """🚨 Os comandos deste projeto escrevem resultado em stdout.

        `conferir_especies`, `limiar` e o CSV de `exportar_docs` sao lidos por
        redirecionamento. Log misturado ali corromperia o arquivo de saida.
        """
        config = montar(base_dir=None, em_arquivo=False)
        self.assertEqual(
            config['handlers']['console']['stream'], 'ext://sys.stderr'
        )

    def test_nunca_desliga_os_loggers_existentes(self):
        """O aviso de credencial expirada do `copernicusmarine` mora ali."""
        config = montar(base_dir=None, em_arquivo=False)
        self.assertIs(config['disable_existing_loggers'], False)

    def test_sql_do_django_fica_em_warning(self):
        config = montar(base_dir=None, em_arquivo=False)
        self.assertEqual(
            config['loggers']['django.db.backends']['level'], 'WARNING'
        )

    def test_nivel_por_dominio(self):
        config = montar(
            base_dir=None, em_arquivo=False, nivel='INFO',
            niveis_por_dominio={'ingestao': 'DEBUG'},
        )
        self.assertEqual(config['loggers']['ingestao']['level'], 'DEBUG')
        self.assertEqual(config['loggers']['ml']['level'], 'INFO')

    def test_rodando_teste_reconhece_manage_py_test(self):
        self.assertTrue(rodando_teste(['manage.py', 'test']))
        self.assertFalse(rodando_teste(['manage.py', 'atualizar']))
        self.assertFalse(rodando_teste(['manage.py', 'ingerir', 'test']))


class PontaAPontaTests(SimpleTestCase):
    """A prova de que as pecas se encaixam: uma linha real, do logger ao JSON."""

    def test_modulo_que_nao_conhece_a_camada_sai_com_a_correlacao(self):
        fluxo = io.StringIO()
        handler = logging.StreamHandler(fluxo)
        handler.setFormatter(JsonLinhas())
        handler.addFilter(FiltroCorrelacao())

        alheio = logging.getLogger('ingestao.qualidade')
        alheio.addHandler(handler)
        alheio.setLevel(logging.INFO)
        alheio.propagate = False
        try:
            with contexto(fluxo='ingestao', fonte='noaa-crw',
                          local='abrolhos-ba') as identificador:
                # Repare: nenhuma mencao a correlacao nesta chamada.
                alheio.info('406 medicoes rejeitadas', extra={'rejeitadas': 406})
        finally:
            alheio.removeHandler(handler)

        linha = json.loads(fluxo.getvalue().strip())
        self.assertEqual(linha['correlacao'], identificador)
        self.assertEqual(linha['contexto']['fonte'], 'noaa-crw')
        self.assertEqual(linha['contexto']['local'], 'abrolhos-ba')
        self.assertEqual(linha['dados']['rejeitadas'], 406)
