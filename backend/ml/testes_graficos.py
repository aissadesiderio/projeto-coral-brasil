"""Testes das figuras de interpretacao do modelo.

⚠️ **Um teste nao consegue olhar para um grafico.** Ele nao sabe dizer se o
eixo ficou legivel, se uma curva sumiu atras da outra, ou se a cor escolhida
distingue as quatro variaveis — e as tres primeiras versoes destas figuras
falharam exatamente nisso, com o codigo correto: o oxigenio varia numa
amplitude cinco vezes maior que a temperatura e, num eixo comum, apagava as
outras tres curvas. Isso so foi visto abrindo o PNG.

Entao o que se protege aqui e o que **sobrevive a mudanca de escala**:

1. **Nenhum numero e recalculado.** As figuras leem `Importancia` e o quadro
   pronto; se alguem passar a computar a metrica dentro do desenho, ela vira
   uma segunda implementacao livre para divergir da primeira.
2. **A distincao entre media e serie por ano.** Um coeficiente que troca de
   sinal tem media perto de zero, e a figura precisa marcar isso — e a unica
   informacao que a media destroi.
3. **A figura recusa em vez de sair vazia.** Eixo em branco parece resultado.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from ml import graficos
from ml.importancia import Importancia


def _fechar(figura):
    import matplotlib.pyplot as plt

    plt.close(figura.figura)


class OQueEPrevistoTests(SimpleTestCase):
    """🚨 O esquema que precisa ser lido antes das outras quatro figuras.

    "Prever branqueamento" e "prever alerta de estresse termico" soam iguais e
    nao sao. A diferenca esta medida em RESULTADOS.md secao 11.2, e e enorme:
    a regra da NOAA acerta 10 de 10 quando dispara, e deixa passar 78 dos 88
    branqueamentos brasileiros registrados.
    """

    def test_a_legenda_traz_os_dois_numeros_que_definem_a_diferenca(self):
        figura = graficos.o_que_e_previsto()

        self.assertIn('10 de 10', figura.legenda)
        self.assertIn('78 dos 88', figura.legenda)
        _fechar(figura)

    def test_a_legenda_declara_a_procedencia_dos_numeros(self):
        """Numero sem origem num TCC e numero que a banca pergunta de onde veio."""
        figura = graficos.o_que_e_previsto()

        self.assertIn('166 visitas', figura.legenda)
        self.assertIn('GCBD', figura.legenda)
        _fechar(figura)

    def test_diz_que_o_alerta_nao_e_necessario_para_o_branqueamento(self):
        """A assimetria e a frase mais importante que o projeto produziu."""
        figura = graficos.o_que_e_previsto()

        self.assertIn('suficiente', figura.legenda)
        self.assertIn('necessário', figura.legenda)
        _fechar(figura)

    def test_nao_manda_ver_a_si_mesma(self):
        """Rodape apontando para a figura que ele rodapeia manda procurar onde
        o leitor ja esta."""
        figura = graficos.o_que_e_previsto()

        rodapes = [
            t.get_text() for t in figura.figura.texts
            if graficos.AVISO_CURTO in t.get_text()
        ]
        self.assertEqual(len(rodapes), 1)
        self.assertNotIn('Ver a figura', rodapes[0])
        _fechar(figura)

    def test_nao_toca_no_banco(self):
        """E esquema, nao grafico de dados: precisa sair num clone vazio."""
        figura = graficos.o_que_e_previsto()

        self.assertEqual(figura.nome, 'o_que_e_previsto')
        _fechar(figura)


class SeloDoAlvoTests(SimpleTestCase):
    """🚨 O carimbo que impede a leitura errada, em TODAS as figuras.

    Nao adianta escrever "alerta termico" com cuidado numa figura e esquecer na
    seguinte: quem ve a esquecida conclui que o site preve branqueamento. Por
    isso o aviso e aplicado por `_selar`, e este teste percorre cada funcao
    publica exigindo o carimbo — inclusive nas que forem escritas depois desta.
    """

    def _todas(self):
        medida = Importancia(
            modelo='logistica', anos=[2020, 2022],
            coeficientes={'dhw_variacao_7d': 4.0},
            coeficientes_por_ano={'dhw_variacao_7d': [4.0, 5.0]},
            por_coluna_por_ano={'dhw_variacao_7d': [0.8, 0.3]},
        )
        base = date(2026, 1, 1)
        quadro = pd.DataFrame({
            'local': ['r'] * 40,
            'data': [base + timedelta(days=n) for n in range(40)],
            'sst_variacao_7d': np.linspace(-1, 1, 40),
            'dhw_variacao_7d': np.linspace(0, 2, 40),
            'probabilidade': np.linspace(0, 1, 40),
            'alvo_binario': [0] * 40,
        })
        colunas = ['sst_variacao_7d', 'dhw_variacao_7d']

        class _Ajuste:
            colunas = ('sst_variacao_7d', 'dhw_variacao_7d')

            def prever_probabilidade(self, q):
                return np.full(len(q), 0.2)

        yield graficos.o_que_e_previsto()
        yield graficos.coeficientes_por_ano(medida)
        yield graficos.importancia_por_ano(medida)
        yield graficos.linha_do_tempo(quadro, 'probabilidade', 0.1, 'r', colunas)
        yield graficos.resposta_a_variavel(_Ajuste(), quadro, colunas, 0.1, pontos=10)

    def test_toda_figura_carrega_o_aviso_na_legenda(self):
        for figura in self._todas():
            with self.subTest(figura=figura.nome):
                self.assertTrue(
                    figura.legenda.startswith(graficos.AVISO_DO_ALVO),
                    f'{figura.nome} nao passou por _selar',
                )
            _fechar(figura)

    def test_toda_figura_carrega_o_aviso_desenhado(self):
        """Na legenda nao basta: o PNG viaja sozinho para dentro de slides."""
        for figura in self._todas():
            with self.subTest(figura=figura.nome):
                textos = [t.get_text() for t in figura.figura.texts]
                self.assertTrue(
                    any(graficos.AVISO_CURTO in t for t in textos),
                    f'{figura.nome} saiu sem o carimbo no rodape',
                )
            _fechar(figura)

    def test_o_aviso_nomeia_as_duas_coisas_que_nao_devem_ser_confundidas(self):
        self.assertIn('ALERTA DE ESTRESSE TÉRMICO', graficos.AVISO_DO_ALVO)
        self.assertIn('branqueamento observado', graficos.AVISO_DO_ALVO)


class RotulosTests(SimpleTestCase):
    """🚨 O rotulo carrega uma afirmacao cientifica, nao so estetica."""

    def test_todo_rotulo_diz_que_a_feature_e_uma_variacao(self):
        """Sem isso a figura afirma algo que o modelo nao testou.

        `sst_variacao_7d` mede **aquecer**, nao **estar quente**. Um eixo
        escrito so "Temperatura" troca a segunda afirmacao pela primeira, e ela
        e mais forte do que o experimento sustenta.
        """
        for coluna in graficos.ROTULOS:
            with self.subTest(coluna=coluna):
                self.assertIn('variação', graficos.ROTULOS[coluna])

    def test_toda_variavel_rotulada_tem_unidade(self):
        self.assertEqual(set(graficos.ROTULOS), set(graficos.UNIDADES))

    def test_toda_variavel_rotulada_tem_cor_propria(self):
        cores = [graficos.CORES[c] for c in graficos.ROTULOS]

        self.assertEqual(len(set(cores)), len(cores), 'Duas variaveis com a mesma cor')

    def test_coluna_desconhecida_nao_quebra(self):
        self.assertEqual(graficos.rotulo('coisa_nova_7d'), 'coisa_nova_7d')


class CoeficientesPorAnoTests(SimpleTestCase):
    def _importancia(self, por_ano):
        return Importancia(
            modelo='logistica',
            anos=[2020, 2022, 2024],
            coeficientes={c: sum(v) / len(v) for c, v in por_ano.items()},
            coeficientes_por_ano=por_ano,
        )

    def test_desenha_um_painel_por_variavel(self):
        figura = graficos.coeficientes_por_ano(
            self._importancia({
                'sst_variacao_7d': [0.1, 0.2, 0.15],
                'dhw_variacao_7d': [4.0, 5.0, 3.5],
            })
        )

        self.assertEqual(len(figura.figura.axes), 2)
        _fechar(figura)

    def test_a_legenda_denuncia_troca_de_sinal(self):
        """🚨 A unica coisa que a media destroi, e a que muda a conclusao.

        Media +0,03 le-se "quase sem efeito". Mas se os anos foram +0,5 e
        -0,44, o modelo nao teve pouco efeito: ele **discordou de si mesmo**
        sobre a direcao.
        """
        figura = graficos.coeficientes_por_ano(
            self._importancia({'oxigenio_variacao_7d': [0.5, -0.44, 0.03]})
        )

        self.assertIn('Mudaram de direção', figura.legenda)
        self.assertIn('Oxigênio', figura.legenda)
        _fechar(figura)

    def test_sem_troca_de_sinal_a_legenda_diz_isso_explicitamente(self):
        """Silencio nao serve: quem le precisa saber que foi conferido."""
        figura = graficos.coeficientes_por_ano(
            self._importancia({'dhw_variacao_7d': [4.0, 5.0, 3.5]})
        )

        self.assertIn('Nenhuma variável mudou de direção', figura.legenda)
        _fechar(figura)

    def test_a_legenda_registra_os_anos_medidos(self):
        """Figura sem procedencia e figura que a banca pergunta de onde veio."""
        figura = graficos.coeficientes_por_ano(
            self._importancia({'dhw_variacao_7d': [4.0, 5.0, 3.5]})
        )

        self.assertIn('2020', figura.legenda)
        self.assertIn('treinado sem enxergar', figura.legenda)
        _fechar(figura)

    def test_modelo_sem_coeficiente_recusa_em_vez_de_desenhar_vazio(self):
        """Arvore e boosting nao tem `coef_`. Eixo em branco parece resultado."""
        vazia = Importancia(modelo='arvore', anos=[2020], coeficientes_por_ano={})

        with self.assertRaises(ValueError) as capturado:
            graficos.coeficientes_por_ano(vazia)

        self.assertIn('logistica', str(capturado.exception))


class ImportanciaPorAnoTests(SimpleTestCase):
    def test_desenha_uma_curva_por_variavel(self):
        medida = Importancia(
            modelo='logistica',
            anos=[2020, 2022],
            por_coluna_por_ano={
                'sst_variacao_7d': [0.01, 0.00],
                'dhw_variacao_7d': [0.84, 0.30],
            },
        )

        figura = graficos.importancia_por_ano(medida)

        eixo = figura.figura.axes[0]
        self.assertEqual(len(eixo.get_lines()), 3)  # duas curvas + a linha do zero
        _fechar(figura)

    def test_a_legenda_explica_queda_negativa(self):
        """Ela aparece de verdade, e sem explicacao le-se como defeito."""
        medida = Importancia(
            modelo='logistica', anos=[2020],
            por_coluna_por_ano={'sst_variacao_7d': [-0.002]},
        )

        figura = graficos.importancia_por_ano(medida)

        self.assertIn('negativa não é erro', figura.legenda)
        _fechar(figura)

    def test_sem_medicao_recusa(self):
        with self.assertRaises(ValueError):
            graficos.importancia_por_ano(Importancia(modelo='logistica'))


class LinhaDoTempoTests(SimpleTestCase):
    COLUNAS = ('sst_variacao_7d', 'dhw_variacao_7d')

    def _quadro(self, alvo=None, local='recife-teste', dias=40):
        base = date(2026, 1, 1)
        alvo = alvo if alvo is not None else [0] * dias
        return pd.DataFrame({
            'local': [local] * dias,
            'data': [base + timedelta(days=n) for n in range(dias)],
            'sst_variacao_7d': np.linspace(-1, 1, dias),
            'dhw_variacao_7d': np.linspace(0, 2, dias),
            'probabilidade': np.linspace(0, 1, dias),
            'alvo_binario': alvo,
        })

    def test_um_painel_por_variavel_mais_o_da_probabilidade(self):
        """🚨 Painel separado, e nao curvas sobrepostas.

        Num eixo comum o oxigenio (+-5 mmol/m3) achata a temperatura (+-1 C):
        a figura fica correta e ilegivel, que para uma figura e o mesmo que
        errada.
        """
        figura = graficos.linha_do_tempo(
            self._quadro(), 'probabilidade', 0.10, 'recife-teste', self.COLUNAS,
        )

        self.assertEqual(len(figura.figura.axes), len(self.COLUNAS) + 1)
        _fechar(figura)

    def test_conta_os_episodios_reais_na_legenda(self):
        alvo = [0] * 10 + [1] * 5 + [0] * 10 + [1] * 3 + [0] * 12

        figura = graficos.linha_do_tempo(
            self._quadro(alvo), 'probabilidade', 0.10, 'recife-teste', self.COLUNAS,
        )

        self.assertIn('2 períodos', figura.legenda)
        _fechar(figura)

    def test_local_sem_linha_recusa(self):
        with self.assertRaises(ValueError):
            graficos.linha_do_tempo(
                self._quadro(), 'probabilidade', 0.10, 'outro-recife', self.COLUNAS,
            )

    def test_o_nome_do_arquivo_carrega_o_recife(self):
        """Tres PNGs numa pasta precisam se distinguir sem abrir."""
        figura = graficos.linha_do_tempo(
            self._quadro(), 'probabilidade', 0.10, 'recife-teste', self.COLUNAS,
        )

        self.assertEqual(figura.nome, 'linha_do_tempo_recife-teste')
        _fechar(figura)


class IntervalosTests(SimpleTestCase):
    """As faixas dos episodios reais. Errar aqui desloca o que aconteceu."""

    def _datas(self, n):
        return [date(2026, 1, 1) + timedelta(days=i) for i in range(n)]

    def test_um_trecho_continuo_vira_um_intervalo(self):
        datas = self._datas(6)

        achados = list(graficos._intervalos(datas, [0, 1, 1, 1, 0, 0]))

        self.assertEqual(achados, [(datas[1], datas[3])])

    def test_dois_trechos_separados_viram_dois(self):
        datas = self._datas(7)

        achados = list(graficos._intervalos(datas, [1, 1, 0, 0, 1, 0, 0]))

        self.assertEqual(achados, [(datas[0], datas[1]), (datas[4], datas[4])])

    def test_trecho_que_vai_ate_o_fim_e_fechado(self):
        """Sem isto o ultimo episodio da serie sumiria do grafico."""
        datas = self._datas(4)

        achados = list(graficos._intervalos(datas, [0, 0, 1, 1]))

        self.assertEqual(achados, [(datas[2], datas[3])])

    def test_serie_sem_episodio_nao_produz_faixa(self):
        self.assertEqual(list(graficos._intervalos(self._datas(3), [0, 0, 0])), [])


class RespostaAVariavelTests(SimpleTestCase):
    COLUNAS = ('sst_variacao_7d', 'dhw_variacao_7d')

    class _AjusteFalso:
        """Responde pelo dobro do DHW, para a curva ter forma conhecida."""

        def __init__(self, colunas):
            self.colunas = colunas
            self.vistos = []

        def prever_probabilidade(self, quadro):
            self.vistos.append(quadro.copy())
            return np.clip(quadro['dhw_variacao_7d'] * 0.5 + 0.1, 0, 1).to_numpy()

    def _quadro(self, n=200):
        gerador = np.random.default_rng(42)
        return pd.DataFrame({
            'sst_variacao_7d': gerador.normal(0, 0.4, n),
            'dhw_variacao_7d': gerador.normal(0.5, 0.6, n),
        })

    def test_desenha_um_painel_por_variavel(self):
        ajuste = self._AjusteFalso(self.COLUNAS)

        figura = graficos.resposta_a_variavel(
            ajuste, self._quadro(), list(self.COLUNAS), 0.10,
        )

        self.assertEqual(len(figura.figura.axes), 2)
        _fechar(figura)

    def test_as_outras_variaveis_ficam_paradas_na_mediana(self):
        """🚨 O que torna a curva interpretavel: so uma coisa muda por vez."""
        ajuste = self._AjusteFalso(self.COLUNAS)
        quadro = self._quadro()

        figura = graficos.resposta_a_variavel(
            ajuste, quadro, list(self.COLUNAS), 0.10, pontos=20,
        )

        # No painel que varre a SST, o DHW tem de estar constante na mediana.
        cenario_sst = ajuste.vistos[0]
        self.assertEqual(cenario_sst['dhw_variacao_7d'].nunique(), 1)
        self.assertAlmostEqual(
            cenario_sst['dhw_variacao_7d'].iloc[0],
            quadro['dhw_variacao_7d'].median(),
        )
        _fechar(figura)

    def test_a_varredura_fica_dentro_do_observado(self):
        """Percentil 1 a 99: fora dali a curva seria extrapolacao pura."""
        ajuste = self._AjusteFalso(self.COLUNAS)
        quadro = self._quadro()

        figura = graficos.resposta_a_variavel(
            ajuste, quadro, list(self.COLUNAS), 0.10, pontos=20,
        )

        varrido = ajuste.vistos[0]['sst_variacao_7d']
        self.assertGreaterEqual(varrido.min(), quadro['sst_variacao_7d'].min())
        self.assertLessEqual(varrido.max(), quadro['sst_variacao_7d'].max())
        _fechar(figura)

    def test_a_legenda_avisa_que_a_curva_descreve_o_modelo_e_nao_o_oceano(self):
        """No mar as variaveis nao se movem sozinhas; aquecer muda o oxigenio."""
        ajuste = self._AjusteFalso(self.COLUNAS)

        figura = graficos.resposta_a_variavel(
            ajuste, self._quadro(), list(self.COLUNAS), 0.10, pontos=20,
        )

        self.assertIn('descreve o MODELO, não o mar', figura.legenda)
        self.assertIn('nenhuma linha aqui é uma previsão', figura.legenda)
        _fechar(figura)


class SalvarTests(SimpleTestCase):
    def test_salva_a_legenda_ao_lado_da_figura(self):
        """PNG solto numa pasta perde a procedencia em uma semana."""
        import tempfile
        from pathlib import Path

        medida = Importancia(
            modelo='logistica', anos=[2020],
            coeficientes={'dhw_variacao_7d': 4.0},
            coeficientes_por_ano={'dhw_variacao_7d': [4.0]},
        )
        figura = graficos.coeficientes_por_ano(medida)

        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            caminhos = figura.salvar(pasta)

            self.assertTrue(caminhos[0].exists())
            legenda = pasta / f'{figura.nome}.txt'
            self.assertTrue(legenda.exists())
            self.assertIn('Peso que o modelo deu', legenda.read_text(encoding='utf-8'))

        _fechar(figura)
