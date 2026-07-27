"""Testes do endpoint que faz conta.

O que protegem, em ordem de gravidade:

1. 🚨 **Local fora do treino nao recebe numero.** O modelo viu tres recifes;
   responder sobre um quarto seria extrapolacao servida como medicao.
2. **Artefato ausente vira 503, nunca predicao improvisada.** O `.joblib` e
   derivado e nao versionado — em maquina nova ele simplesmente nao existe.
3. **Janela incompleta vira `disponivel: false` no item**, e nao erro da
   requisicao inteira: um recife sem dado nao pode derrubar os outros dois.
4. **O limiar e a calibracao viajam no payload.** Sem eles a probabilidade e
   um numero sem regra de leitura.

O modelo destes testes e falso de proposito. Carregar o artefato real tornaria
a suite dependente de `treinar_final` ter rodado, e o que se mede aqui e o
contrato da resposta — nao a qualidade da predicao, que tem suite propria.
"""

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.urls import reverse

from aquaculture.models import LocalRecife, MedicaoAmbiental
from ml import predicao


class BasePainel(TestCase):
    COLUNAS = ['sst_variacao_7d', 'dhw_variacao_7d']
    FIM = date(2026, 7, 24)

    def setUp(self):
        MedicaoAmbiental.objects.all().delete()
        LocalRecife.objects.all().delete()

        self.abrolhos = LocalRecife.objects.create(
            slug='teste-abrolhos', nome='Abrolhos', estado='BA',
            cidade='Caravelas', latitude=-17.9, longitude=-38.6,
        )
        self.picao = LocalRecife.objects.create(
            slug='teste-picao', nome='Picaozinho', estado='PB',
            cidade='Joao Pessoa', latitude=-7.1, longitude=-34.8,
        )
        self.serie(self.abrolhos)

        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        predicao.esquecer_modelos()
        self.addCleanup(predicao.esquecer_modelos)

    def serie(self, local, dias=20, pular=()):
        inicio = self.FIM - timedelta(days=dias - 1)
        for n in range(dias):
            dia = inicio + timedelta(days=n)
            if dia in pular:
                continue
            for i, variavel in enumerate(('sst', 'dhw')):
                MedicaoAmbiental.objects.create(
                    local_recife=local, data=dia, variavel=variavel,
                    valor=25.0 + i + n * 0.1, unidade='°C',
                    fonte='noaa_crw', dataset_id='dhw_5km',
                )

    def gravar_modelo(self, locais=None, calibracao='isotonic', escala=0.1):
        """Escreve o par .joblib/.json que o endpoint carrega.

        `escala` controla onde a probabilidade falsa cai: o padrao deixa no
        meio da faixa, para o limiar poder ser testado nos dois sentidos;
        `escala=1` satura em 1,0, que e o caso do extremo.
        """
        import joblib

        from ml import persistencia

        pasta = Path(self.pasta.name)
        pasta.mkdir(parents=True, exist_ok=True)
        joblib.dump(ModeloFalso(escala), pasta / 'painel.joblib')

        import sklearn

        (pasta / 'painel.json').write_text(json.dumps({
            'assinatura': persistencia.ASSINATURA,
            'formato': persistencia.FORMATO,
            'nome': 'painel',
            'gerado_em': '2026-07-27',
            'sklearn': sklearn.__version__,
            'modelo': 'logistica',
            'colunas': self.COLUNAS,
            'horizonte_dias': 7,
            'alvo': 'baa >= 3.0 em t+7',
            'n_treino': 7095,
            'positivos_treino': 596,
            'calibracao': calibracao,
            'locais': locais if locais is not None else ['teste-abrolhos'],
        }), encoding='utf-8')
        return pasta

    def buscar(self, caminho='', **extras):
        pasta = extras.pop('pasta', Path(self.pasta.name))
        ajustes = {
            'OFFLINE_MODE': False,
            'PAINEL_MODELO': 'painel',
            'PAINEL_LIMIAR': 0.20,
            **extras,
        }
        with override_settings(**ajustes):
            with _pasta_de_modelos(pasta):
                return self.client.get(caminho or reverse('painel_risco_list'))


class ModeloFalso:
    """Devolve a soma das entradas vezes `escala`, cortada em [0, 1]."""

    def __init__(self, escala=0.1):
        self.escala = escala

    def predict_proba(self, quadro):
        import numpy as np

        soma = np.clip(
            np.asarray(quadro).sum(axis=1) * self.escala, 0.0, 1.0
        )
        return np.column_stack([1 - soma, soma])


class _pasta_de_modelos:
    """Aponta `persistencia.PASTA_PADRAO` para um diretorio temporario."""

    def __init__(self, pasta):
        self.pasta = pasta

    def __enter__(self):
        from ml import persistencia

        self.anterior = persistencia.PASTA_PADRAO
        persistencia.PASTA_PADRAO = self.pasta
        predicao.esquecer_modelos()

    def __exit__(self, *erro):
        from ml import persistencia

        persistencia.PASTA_PADRAO = self.anterior
        predicao.esquecer_modelos()


class PainelListaTests(BasePainel):
    def test_responde_com_o_bloco_do_modelo_e_os_resultados(self):
        self.gravar_modelo()

        corpo = self.buscar().json()

        self.assertIn('modelo', corpo)
        self.assertIn('results', corpo)

    def test_o_bloco_do_modelo_diz_o_que_a_probabilidade_significa(self):
        """Alvo, horizonte e calibracao nao sao metadado decorativo."""
        self.gravar_modelo()

        bloco = self.buscar().json()['modelo']

        self.assertEqual(bloco['alvo'], 'baa >= 3.0 em t+7')
        self.assertEqual(bloco['horizonte_dias'], 7)
        self.assertEqual(bloco['calibracao'], 'isotonic')
        self.assertEqual(bloco['colunas'], self.COLUNAS)

    def test_o_limiar_vem_no_payload(self):
        """🚨 Nao existe corte natural: 0,50 e 0,20 sao decisoes diferentes."""
        self.gravar_modelo()

        corpo = self.buscar().json()

        self.assertEqual(corpo['modelo']['limiar'], 0.20)
        self.assertEqual(corpo['results'][0]['limiar'], 0.20)

    def test_a_ordem_segue_os_metadados_e_nao_o_banco(self):
        self.serie(self.picao)
        self.gravar_modelo(locais=['teste-picao', 'teste-abrolhos'])

        slugs = [x['local'] for x in self.buscar().json()['results']]

        self.assertEqual(slugs, ['teste-picao', 'teste-abrolhos'])

    def test_so_devolve_os_locais_que_o_modelo_viu(self):
        self.serie(self.picao)
        self.gravar_modelo(locais=['teste-abrolhos'])

        slugs = [x['local'] for x in self.buscar().json()['results']]

        self.assertEqual(slugs, ['teste-abrolhos'])

    def test_a_data_base_e_a_data_alvo_acompanham(self):
        """Risco sem data e lido como "agora", que e o que ele nao e."""
        self.gravar_modelo()

        item = self.buscar().json()['results'][0]

        self.assertEqual(item['data_base'], '2026-07-24')
        self.assertEqual(item['data_alvo'], '2026-07-31')

    def test_o_atraso_da_serie_vem_no_payload(self):
        self.gravar_modelo()

        item = self.buscar().json()['results'][0]

        self.assertIn('dias_de_atraso', item)
        self.assertGreaterEqual(item['dias_de_atraso'], 0)

    def test_as_entradas_acompanham_a_probabilidade(self):
        self.gravar_modelo()

        item = self.buscar().json()['results'][0]

        self.assertEqual(sorted(item['entradas']), sorted(self.COLUNAS))

    def test_o_alerta_sai_do_limiar(self):
        self.gravar_modelo()

        item = self.buscar().json()['results'][0]

        self.assertEqual(item['alerta'], item['probabilidade'] >= item['limiar'])

    def test_limiar_configuravel_muda_o_alerta(self):
        """Trocar alarme falso por evento perdido e decisao de quem opera."""
        self.gravar_modelo()

        frouxo = self.buscar(PAINEL_LIMIAR=0.0).json()['results'][0]
        apertado = self.buscar(PAINEL_LIMIAR=0.99).json()['results'][0]

        self.assertTrue(frouxo['alerta'])
        self.assertFalse(apertado['alerta'])


class DadoInsuficienteTests(BasePainel):
    def test_janela_incompleta_marca_o_item_como_indisponivel(self):
        """🚨 E o item que fica indisponivel, nao a requisicao que falha."""
        MedicaoAmbiental.objects.all().delete()
        self.serie(self.abrolhos, pular={self.FIM - timedelta(days=7)})
        self.gravar_modelo()

        resposta = self.buscar()
        item = resposta.json()['results'][0]

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(item['disponivel'])
        self.assertNotIn('probabilidade', item)

    def test_o_motivo_diz_qual_dia_faltou(self):
        ausente = self.FIM - timedelta(days=7)
        MedicaoAmbiental.objects.all().delete()
        self.serie(self.abrolhos, pular={ausente})
        self.gravar_modelo()

        item = self.buscar().json()['results'][0]

        self.assertIn(ausente.isoformat(), item['motivo'])
        self.assertIn(
            {'variavel': 'sst', 'data': ausente.isoformat()}, item['faltando']
        )

    def test_um_recife_sem_dado_nao_derruba_os_outros(self):
        self.serie(self.picao)
        MedicaoAmbiental.objects.filter(
            local_recife=self.abrolhos, data=self.FIM - timedelta(days=7)
        ).delete()
        self.gravar_modelo(locais=['teste-abrolhos', 'teste-picao'])

        itens = {x['local']: x for x in self.buscar().json()['results']}

        self.assertFalse(itens['teste-abrolhos']['disponivel'])
        self.assertTrue(itens['teste-picao']['disponivel'])

    def test_serie_que_termina_antes_atrasa_a_data_base_em_vez_de_recusar(self):
        """A distincao que separa "ingestao atrasada" de "serie furada".

        Apagar o ultimo dia **nao** e lacuna: e a serie terminando um dia mais
        cedo, indistinguivel de uma ingestao que ainda nao rodou hoje. Nesse
        caso a resposta sai, com a data-base recuada e `dias_de_atraso` maior —
        o atraso fica declarado em vez de virar recusa.

        Recusa fica para o outro caso: o dia existe na serie mas a ponta da
        janela nao.
        """
        MedicaoAmbiental.objects.filter(
            local_recife=self.abrolhos, data=self.FIM
        ).delete()
        self.gravar_modelo()

        item = self.buscar().json()['results'][0]

        self.assertTrue(item['disponivel'])
        self.assertEqual(item['data_base'], (self.FIM - timedelta(days=1)).isoformat())

    def test_local_sem_medicao_nenhuma_e_indisponivel_e_nao_erro(self):
        self.gravar_modelo(locais=['teste-abrolhos', 'teste-picao'])

        itens = {x['local']: x for x in self.buscar().json()['results']}

        self.assertFalse(itens['teste-picao']['disponivel'])

    def test_a_probabilidade_nunca_vem_zero_por_falta_de_dado(self):
        """🚨 O defeito que este endpoint existe para nao repetir.

        Preencher lacuna com zero devolveria `variacao = 0`, ou seja "nada
        mudou" — a afirmacao mais tranquilizadora possivel, justamente onde o
        dado sumiu.
        """
        MedicaoAmbiental.objects.all().delete()
        self.serie(self.abrolhos, pular={self.FIM - timedelta(days=7)})
        self.gravar_modelo()

        item = self.buscar().json()['results'][0]

        self.assertNotIn('probabilidade', item)
        self.assertNotIn('entradas', item)


class ArtefatoTests(BasePainel):
    def test_sem_artefato_responde_503_com_o_comando(self):
        """O .joblib e derivado: em maquina nova ele nao existe."""
        resposta = self.buscar()

        self.assertEqual(resposta.status_code, 503)
        self.assertIn('treinar_final', resposta.json()['detail'])

    def test_artefato_de_outra_origem_e_recusado(self):
        """🚨 joblib.load executa codigo."""
        self.gravar_modelo()
        caminho = Path(self.pasta.name) / 'painel.json'
        dados = json.loads(caminho.read_text(encoding='utf-8'))
        dados['assinatura'] = 'outro-projeto'
        caminho.write_text(json.dumps(dados), encoding='utf-8')

        resposta = self.buscar()

        self.assertEqual(resposta.status_code, 503)
        self.assertIn('recusado', resposta.json()['detail'].lower())

    def test_a_calibracao_gravada_chega_ao_payload(self):
        """Sem isto o painel nao sabe dizer se o numero e cru ou recalibrado."""
        self.gravar_modelo(calibracao=None)

        bloco = self.buscar().json()['modelo']

        self.assertIsNone(bloco['calibracao'])
        self.assertFalse(bloco['probabilidade_em_degraus'])

    def test_isotonica_avisa_que_a_probabilidade_e_em_degraus(self):
        """Dois recifes diferentes podem sair com o mesmo numero."""
        self.gravar_modelo(calibracao='isotonic')

        self.assertTrue(self.buscar().json()['modelo']['probabilidade_em_degraus'])


class ExtremoTests(BasePainel):
    def test_probabilidade_um_exata_e_sinalizada(self):
        """🚨 121 das 7.095 amostras de treino saem em p = 1,000 exato.

        Isso quer dizer "todas as amostras deste degrau viraram alerta", e nao
        "certeza". A interface nao pode exibir 100%.
        """
        self.gravar_modelo(escala=1.0)

        item = self.buscar().json()['results'][0]

        self.assertEqual(item['probabilidade'], 1.0)
        self.assertTrue(item['no_extremo'])

    def test_probabilidade_no_meio_da_faixa_nao_e_extremo(self):
        self.gravar_modelo()

        item = self.buscar().json()['results'][0]

        self.assertFalse(item['no_extremo'])


class PainelDetalheTests(BasePainel):
    def caminho(self, slug):
        return reverse('painel_risco_detail', args=[slug])

    def test_devolve_o_recife_pedido(self):
        self.gravar_modelo()

        corpo = self.buscar(self.caminho('teste-abrolhos')).json()

        self.assertEqual(corpo['local'], 'teste-abrolhos')
        self.assertIn('modelo', corpo)

    def test_local_fora_do_treino_e_404_com_motivo(self):
        """🚨 Extrapolar seria inventar cobertura que nada sustenta."""
        self.serie(self.picao)
        self.gravar_modelo(locais=['teste-abrolhos'])

        resposta = self.buscar(self.caminho('teste-picao'))

        self.assertEqual(resposta.status_code, 404)
        self.assertIn('nao foi treinado', resposta.json()['detail'])

    def test_o_404_lista_os_locais_disponiveis(self):
        self.gravar_modelo(locais=['teste-abrolhos'])

        detalhe = self.buscar(self.caminho('nao-existe')).json()['detail']

        self.assertIn('teste-abrolhos', detalhe)

    def test_local_inexistente_no_banco_mas_no_modelo_e_404(self):
        self.gravar_modelo(locais=['fantasma'])

        self.assertEqual(self.buscar(self.caminho('fantasma')).status_code, 404)


class ModoOfflineTests(BasePainel):
    def test_a_lista_respeita_o_modo_offline(self):
        self.gravar_modelo()

        with override_settings(OFFLINE_MODE=True):
            resposta = self.client.get(reverse('painel_risco_list'))

        self.assertEqual(resposta.status_code, 503)

    def test_o_detalhe_respeita_o_modo_offline(self):
        self.gravar_modelo()

        with override_settings(OFFLINE_MODE=True):
            resposta = self.client.get(
                reverse('painel_risco_detail', args=['teste-abrolhos'])
            )

        self.assertEqual(resposta.status_code, 503)
