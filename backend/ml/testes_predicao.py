"""Testes da aplicacao do modelo a serie atual.

O que protegem, em ordem de gravidade:

1. 🚨 **A janela da predicao e a mesma do treino.** E o defeito silencioso
   deste modulo: uma coluna com o nome certo e o conteudo errado passa pelo
   `Pipeline` sem erro nenhum. Os testes de `_janela_do_nome` e o de
   equivalencia com `dataset.montar` sao a defesa.
2. **Lacuna vira recusa, nunca zero.** Zero e valor legitimo para uma
   variacao, entao preencher devolveria "nada mudou" onde o dado sumiu.
3. **A data-base e a mais recente da serie**, e nao a mais recente que
   funciona — senao ingestao parada ha semanas passa por operacao normal.
"""

from datetime import date, timedelta

from django.test import TestCase

from aquaculture.models import LocalRecife, MedicaoAmbiental
from ml import dataset, predicao


class TraducaoDoNomeDaColunaTests(TestCase):
    """A ponte entre o metadado do artefato e o codigo que calcula."""

    def test_traduz_a_coluna_padrao(self):
        janela = predicao._janela_do_nome('sst_variacao_7d')

        self.assertEqual(janela.variavel, 'sst')
        self.assertEqual(janela.operacao, 'variacao')
        self.assertEqual(janela.dias, 7)

    def test_a_volta_reproduz_o_nome(self):
        """🚨 O invariante que impede calcular uma coisa e chamar de outra."""
        for nome in ('sst_variacao_7d', 'dhw_media_14d', 'oxigenio_maximo_30d'):
            self.assertEqual(predicao._janela_do_nome(nome).nome, nome)

    def test_variavel_com_underscore_sobrevive(self):
        janela = predicao._janela_do_nome('baa_area_alerta_variacao_7d')

        self.assertEqual(janela.variavel, 'baa_area_alerta')

    def test_coluna_sem_formato_de_janela_e_recusada(self):
        """Melhor parar do que inventar uma janela para uma coluna de nivel."""
        with self.assertRaises(predicao.ColunaNaoTraduzivel):
            predicao._janela_do_nome('sst')

    def test_coluna_sem_numero_de_dias_e_recusada(self):
        with self.assertRaises(predicao.ColunaNaoTraduzivel):
            predicao._janela_do_nome('sst_variacao_semana')

    def test_janelas_do_modelo_preserva_a_ordem(self):
        colunas = ('dhw_variacao_7d', 'sst_variacao_7d')

        nomes = tuple(j.nome for j in predicao.janelas_do_modelo(colunas))

        self.assertEqual(nomes, colunas)


class BaseComSerie(TestCase):
    """Uma serie sintetica de dias corridos, para controlar as lacunas."""

    VARIAVEIS = ('sst', 'dhw')
    COLUNAS = ('sst_variacao_7d', 'dhw_variacao_7d')

    def setUp(self):
        MedicaoAmbiental.objects.all().delete()
        LocalRecife.objects.all().delete()

        self.local = LocalRecife.objects.create(
            slug='teste-recife', nome='Recife de Teste', estado='BA',
            cidade='Caravelas', latitude=-17.9, longitude=-38.6,
        )
        self.fim = date(2026, 7, 24)
        self.gravar_serie()

    def gravar_serie(self, dias=30, pular=()):
        inicio = self.fim - timedelta(days=dias - 1)
        for n in range(dias):
            dia = inicio + timedelta(days=n)
            if dia in pular:
                continue
            for i, variavel in enumerate(self.VARIAVEIS):
                MedicaoAmbiental.objects.create(
                    local_recife=self.local, data=dia, variavel=variavel,
                    valor=20.0 + i + n * 0.1, unidade='°C',
                    fonte='noaa_crw', dataset_id='dhw_5km',
                )
            # O alvo entra so para `dataset.montar` conseguir montar linha —
            # a predicao nao le `baa`, porque em `t` ele ainda nao existe.
            MedicaoAmbiental.objects.create(
                local_recife=self.local, data=dia, variavel='baa',
                valor=0.0, unidade='nivel', fonte='noaa_crw',
                dataset_id='dhw_5km',
            )

    def adiantar(self, variavel, dias):
        """Estende **uma** variavel alem do fim, produzindo borda irregular.

        E o formato real de uma serie multi-fonte: o Copernicus publica ate
        ontem e o CoralTemp da NOAA leva de 1 a 3 dias. Nenhuma lacuna e
        criada — os dias novos simplesmente so existem para uma variavel.
        """
        for n in range(1, dias + 1):
            MedicaoAmbiental.objects.create(
                local_recife=self.local, data=self.fim + timedelta(days=n),
                variavel=variavel, valor=30.0 + n, unidade='°C',
                fonte='copernicus', dataset_id='cmems_anfc',
            )


class MontarEntradasTests(BaseComSerie):
    def test_usa_a_data_mais_recente_da_serie(self):
        lidas = predicao.montar_entradas(self.local, self.COLUNAS)

        self.assertEqual(lidas.data_base, self.fim)
        self.assertEqual(lidas.limitado_por, ())

    def test_devolve_uma_entrada_por_coluna(self):
        valores = predicao.montar_entradas(self.local, self.COLUNAS).valores

        self.assertEqual(sorted(valores), sorted(self.COLUNAS))

    def test_a_variacao_e_a_diferenca_de_sete_dias(self):
        """Serie sobe 0,1 por dia, entao sete dias valem 0,7."""
        valores = predicao.montar_entradas(self.local, self.COLUNAS).valores

        self.assertAlmostEqual(valores['sst_variacao_7d'], 0.7, places=6)

    def test_serie_vazia_recusa(self):
        MedicaoAmbiental.objects.all().delete()

        with self.assertRaises(predicao.SemDadoSuficiente):
            predicao.montar_entradas(self.local, self.COLUNAS)

    def test_lacuna_na_ponta_da_janela_recusa(self):
        """🚨 Sem isto o valor viria zero, dizendo "nada mudou"."""
        MedicaoAmbiental.objects.all().delete()
        self.gravar_serie(pular={self.fim - timedelta(days=7)})

        with self.assertRaises(predicao.SemDadoSuficiente):
            predicao.montar_entradas(self.local, self.COLUNAS)

    def test_a_recusa_diz_qual_dia_faltou(self):
        """"Sem dado" nao distingue ingestao de ontem de lacuna de tres semanas."""
        ausente = self.fim - timedelta(days=7)
        MedicaoAmbiental.objects.all().delete()
        self.gravar_serie(pular={ausente})

        with self.assertRaises(predicao.SemDadoSuficiente) as capturado:
            predicao.montar_entradas(self.local, self.COLUNAS)

        self.assertIn(ausente.isoformat(), str(capturado.exception))
        self.assertIn(('sst', ausente), capturado.exception.faltando)

    def test_lacuna_no_meio_nao_atrapalha_a_variacao(self):
        """Variacao compara dois instantes; o meio nao entra na conta.

        Distincao registrada em `dataset.aplicar_janela` — repetida aqui
        porque e ela que decide se a recusa e correta ou excesso de zelo.
        """
        MedicaoAmbiental.objects.all().delete()
        self.gravar_serie(pular={self.fim - timedelta(days=3)})

        valores = predicao.montar_entradas(self.local, self.COLUNAS).valores

        self.assertAlmostEqual(valores['sst_variacao_7d'], 0.7, places=6)

    def test_serie_curta_demais_recusa(self):
        MedicaoAmbiental.objects.all().delete()
        self.gravar_serie(dias=4)

        with self.assertRaises(predicao.SemDadoSuficiente):
            predicao.montar_entradas(self.local, self.COLUNAS)

    def test_nao_anda_para_tras_ate_achar_dia_que_funciona(self):
        """🚨 Andar para tras mascararia ingestao parada como operacao normal."""
        MedicaoAmbiental.objects.all().delete()
        self.gravar_serie(pular={self.fim - timedelta(days=7)})

        with self.assertRaises(predicao.SemDadoSuficiente):
            predicao.montar_entradas(self.local, self.COLUNAS)


class BordaIrregularTests(BaseComSerie):
    """🚨 O estado que deixava o painel escuro na maior parte dos dias.

    As duas fontes nunca terminam no mesmo dia: o CoralTemp da NOAA publica
    com 1 a 3 dias de atraso e a analise do Copernicus vai ate ontem. Ate
    30/07/2026 a data-base caia na ponta mais adiantada, a janela nunca
    fechava, e os tres recifes respondiam `disponivel: false` esperando um dado
    que nem entrava na conta daquele dia.

    O que **nao** pode voltar junto: buraco no meio da janela continua sendo
    recusa. A diferenca e onde a borda direita cai, nao varrer para tras.
    """

    def test_borda_irregular_responde_no_ultimo_dia_completo(self):
        self.adiantar('dhw', dias=3)

        lidas = predicao.montar_entradas(self.local, self.COLUNAS)

        self.assertEqual(lidas.data_base, self.fim)

    def test_diz_qual_variavel_segura_a_borda(self):
        """Sem isto, uma fonte quebrada vira so "dado um pouco mais velho"."""
        self.adiantar('dhw', dias=3)

        lidas = predicao.montar_entradas(self.local, self.COLUNAS)

        self.assertEqual(lidas.limitado_por, ('sst',))

    def test_borda_reta_nao_aponta_ninguem(self):
        lidas = predicao.montar_entradas(self.local, self.COLUNAS)

        self.assertEqual(lidas.limitado_por, ())

    def test_o_valor_e_o_do_dia_completo_e_nao_o_do_dia_adiantado(self):
        """A conta tem de sair igualzinha a de antes de a outra fonte chegar."""
        esperado = predicao.montar_entradas(self.local, self.COLUNAS).valores

        self.adiantar('dhw', dias=3)
        obtido = predicao.montar_entradas(self.local, self.COLUNAS).valores

        self.assertEqual(obtido, esperado)

    def test_buraco_no_meio_continua_recusando_mesmo_com_borda_irregular(self):
        """🚨 A recusa que a mudanca nao pode ter comprado de volta."""
        MedicaoAmbiental.objects.all().delete()
        self.gravar_serie(pular={self.fim - timedelta(days=7)})
        self.adiantar('dhw', dias=3)

        with self.assertRaises(predicao.SemDadoSuficiente):
            predicao.montar_entradas(self.local, self.COLUNAS)

    def test_atraso_declara_a_idade_do_dia_completo(self):
        """O atraso conta da data-base, e nao da ponta adiantada da serie."""
        self.adiantar('dhw', dias=3)
        ajuste = _AjusteFalso(self.COLUNAS)

        risco = predicao.calcular(
            self.local, ajuste, limiar=0.5, hoje=self.fim + timedelta(days=4),
        )

        self.assertEqual(risco.data_base, self.fim)
        self.assertEqual(risco.dias_de_atraso, 4)
        self.assertEqual(risco.limitado_por, ('sst',))

    def test_nenhum_dia_completo_recusa_dizendo_o_que_falta(self):
        """Uma fonte que nunca foi ingerida nao vira atraso: vira recusa."""
        MedicaoAmbiental.objects.filter(variavel='sst').delete()

        with self.assertRaises(predicao.SemDadoSuficiente) as capturado:
            predicao.montar_entradas(self.local, self.COLUNAS)

        self.assertIn('sst', str(capturado.exception))


class _AjusteFalso:
    """Um modelo de mentira: devolve probabilidade fixa sem tocar em sklearn."""

    horizonte = 7

    def __init__(self, colunas):
        self.colunas = colunas

    def prever_probabilidade(self, quadro):
        return [0.25] * len(quadro)


class MesmaContaDoTreinoTests(BaseComSerie):
    """🚨 O teste que fecha o buraco silencioso deste modulo."""

    def test_a_entrada_bate_com_a_linha_montada_pelo_dataset(self):
        """A predicao e o treino tem de produzir o mesmo numero para o mesmo dia.

        Se divergirem, o modelo recebe colunas com o nome certo e o conteudo
        errado — e responde normalmente, sem erro nenhum.
        """
        janelas = dataset.janelas_para(self.VARIAVEIS)
        conjunto = dataset.montar(self.local, horizonte=1, janelas=janelas)
        # A ultima linha que o dataset consegue montar fica um dia antes do fim
        # da serie, porque ele precisa do alvo em t+1.
        linha = conjunto.quadro.iloc[-1]

        largo, _ = dataset.carregar_largo(self.local, self.VARIAVEIS)
        esperado = {
            j.nome: float(dataset.aplicar_janela(largo[j.variavel], j)[linha['data']])
            for j in janelas
        }

        valores = predicao.montar_entradas(self.local, self.COLUNAS).valores
        _, valores_naquele_dia = (
            linha['data'],
            {c: float(linha[c]) for c in self.COLUNAS},
        )

        self.assertEqual(valores_naquele_dia, esperado)
        # E a conta da predicao no dia dela usa a mesma funcao.
        self.assertAlmostEqual(
            valores['sst_variacao_7d'],
            float(dataset.aplicar_janela(largo['sst'], janelas[0])[self.fim]),
            places=9,
        )


class CalcularTests(BaseComSerie):
    class AjusteFalso:
        """Um `Ajuste` de mentira: devolve a soma das entradas, cortada em 1.

        Deliberadamente nao usa sklearn — o que se mede aqui e a montagem do
        `Risco`, e um modelo real traria variancia que nao interessa ao teste.
        """

        colunas = ('sst_variacao_7d', 'dhw_variacao_7d')
        horizonte = 7
        nome = 'falso'

        def __init__(self, fixa=None):
            self.fixa = fixa

        def prever_probabilidade(self, quadro):
            if self.fixa is not None:
                return [self.fixa]
            return [min(1.0, float(quadro[list(self.colunas)].sum(axis=1).iloc[0]))]

    def test_a_data_alvo_e_a_base_mais_o_horizonte(self):
        risco = predicao.calcular(self.local, self.AjusteFalso(), 0.2)

        self.assertEqual(risco.data_alvo, self.fim + timedelta(days=7))

    def test_o_atraso_e_medido_contra_hoje(self):
        risco = predicao.calcular(
            self.local, self.AjusteFalso(), 0.2, hoje=self.fim + timedelta(days=5)
        )

        self.assertEqual(risco.dias_de_atraso, 5)

    def test_o_limiar_decide_o_alerta_e_viaja_junto(self):
        acima = predicao.calcular(self.local, self.AjusteFalso(fixa=0.5), 0.2)
        abaixo = predicao.calcular(self.local, self.AjusteFalso(fixa=0.1), 0.2)

        self.assertTrue(acima.alerta)
        self.assertFalse(abaixo.alerta)
        self.assertEqual(acima.limiar, 0.2)

    def test_o_limiar_no_ponto_exato_alerta(self):
        risco = predicao.calcular(self.local, self.AjusteFalso(fixa=0.2), 0.2)

        self.assertTrue(risco.alerta)

    def test_as_entradas_acompanham_a_resposta(self):
        """Sem elas ninguem consegue conferir de onde saiu o numero."""
        risco = predicao.calcular(self.local, self.AjusteFalso(), 0.2)

        self.assertEqual(sorted(risco.entradas), sorted(self.COLUNAS))

    def test_probabilidade_zero_exata_e_marcada_como_extremo(self):
        """🚨 A isotonica devolve 0 exato em 12,2% das amostras de treino."""
        risco = predicao.calcular(self.local, self.AjusteFalso(fixa=0.0), 0.2)

        self.assertTrue(risco.no_extremo)

    def test_probabilidade_um_exata_e_marcada_como_extremo(self):
        risco = predicao.calcular(self.local, self.AjusteFalso(fixa=1.0), 0.2)

        self.assertTrue(risco.no_extremo)

    def test_probabilidade_intermediaria_nao_e_extremo(self):
        risco = predicao.calcular(self.local, self.AjusteFalso(fixa=0.37), 0.2)

        self.assertFalse(risco.no_extremo)


class CacheDoModeloTests(TestCase):
    """O cache existe para nao desserializar o pickle a cada visita."""

    def setUp(self):
        predicao.esquecer_modelos()

    def tearDown(self):
        predicao.esquecer_modelos()

    def _gravar(self, pasta, calibracao='isotonic'):
        from ml import modelo, persistencia

        ajuste = modelo.Ajuste(
            pipeline=None, nome='logistica', colunas=('sst_variacao_7d',),
            horizonte=7, n_treino=10, positivos_treino=2, calibracao=calibracao,
        )
        import joblib

        caminho_modelo, _ = persistencia._caminhos('teste', pasta)
        caminho_modelo.parent.mkdir(parents=True, exist_ok=True)
        persistencia.salvar(ajuste, 'teste', pasta)
        joblib.dump({'marcador': calibracao}, caminho_modelo)
        return caminho_modelo

    def test_le_o_artefato_uma_vez_so(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            self._gravar(pasta)

            primeiro, _ = predicao.carregar_modelo('teste', pasta)
            segundo, _ = predicao.carregar_modelo('teste', pasta)

            self.assertIs(primeiro, segundo)

    def test_regerar_o_artefato_invalida_o_cache(self):
        """🚨 Cache por TTL serviria o modelo antigo depois de retreinar."""
        import os
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            caminho = self._gravar(pasta, 'isotonic')
            primeiro, _ = predicao.carregar_modelo('teste', pasta)

            caminho_novo = self._gravar(pasta, 'sigmoid')
            # mtime em nanossegundos pode nao mudar em disco rapido: forcado.
            marca = os.stat(caminho_novo).st_mtime + 10
            os.utime(caminho_novo, (marca, marca))

            segundo, metadados = predicao.carregar_modelo('teste', pasta)

            self.assertIsNot(primeiro, segundo)
            self.assertEqual(metadados['calibracao'], 'sigmoid')
            self.assertEqual(caminho, caminho_novo)
