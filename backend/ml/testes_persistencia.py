"""Testes da gravacao do modelo.

O que protegem, em ordem de gravidade: que **carregar nao execute pickle de
origem desconhecida** (joblib.load executa codigo), que o artefato **volte
identico** ao que foi gravado, que uma **troca de versao do scikit-learn** nao
passe em silencio, e que os metadados sejam legiveis **sem** abrir o pickle.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pandas as pd
from django.test import SimpleTestCase

from ml import modelo, persistencia
from ml.persistencia import ArtefatoAusente, ArtefatoIncompativel


def quadro_de_treino(n=60):
    """Alvo simples e aprendivel: alerta quando o DHW subiu."""
    metade = n // 2
    return pd.DataFrame({
        'sst_variacao_7d': [0.1] * metade + [1.2] * (n - metade),
        'dhw_variacao_7d': [0.0] * metade + [3.0] * (n - metade),
        'alvo': [0.0] * metade + [4.0] * (n - metade),
    })


class PersistenciaTests(SimpleTestCase):
    COLUNAS = ('sst_variacao_7d', 'dhw_variacao_7d')

    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)
        self.quadro = quadro_de_treino()
        self.ajuste = modelo.treinar(
            self.quadro, self.COLUNAS, nome='logistica', horizonte=7
        )

    def _salvar(self, nome='teste'):
        return persistencia.salvar(self.ajuste, nome, pasta=self.pasta)

    # --- ida e volta ---------------------------------------------------------

    def test_o_artefato_volta_com_as_mesmas_colunas(self):
        self._salvar()

        recarregado = persistencia.carregar('teste', pasta=self.pasta)

        self.assertEqual(recarregado.colunas, self.ajuste.colunas)
        self.assertEqual(recarregado.horizonte, 7)
        self.assertEqual(recarregado.nome, 'logistica')

    def test_o_artefato_preve_igual_ao_original(self):
        """A garantia que importa: gravar e carregar nao muda a predicao."""
        self._salvar()

        recarregado = persistencia.carregar('teste', pasta=self.pasta)
        antes = self.ajuste.prever_probabilidade(self.quadro)
        depois = recarregado.prever_probabilidade(self.quadro)

        self.assertEqual(list(antes), list(depois))

    def test_grava_os_dois_arquivos(self):
        caminho_modelo, caminho_json = self._salvar()

        self.assertTrue(caminho_modelo.exists())
        self.assertTrue(caminho_json.exists())
        self.assertEqual(caminho_modelo.suffix, '.joblib')

    # --- metadados -----------------------------------------------------------

    def test_metadados_sao_legiveis_sem_abrir_o_pickle(self):
        """Precisa dar para saber o que e o arquivo antes de executa-lo."""
        _, caminho_json = self._salvar()

        crus = json.loads(caminho_json.read_text(encoding='utf-8'))

        self.assertEqual(crus['colunas'], list(self.COLUNAS))
        self.assertEqual(crus['horizonte_dias'], 7)
        self.assertIn('alvo', crus)
        self.assertIn('sklearn', crus)
        self.assertIn('gerado_em', crus)

    def test_extras_entram_nos_metadados(self):
        persistencia.salvar(
            self.ajuste, 'teste', pasta=self.pasta, extras={'locais': ['x']}
        )

        self.assertEqual(
            persistencia.ler_metadados('teste', self.pasta)['locais'], ['x']
        )

    def test_ler_metadados_nao_precisa_do_joblib(self):
        _, _ = self._salvar()
        (self.pasta / 'teste.joblib').unlink()

        # O JSON continua legivel; so `carregar` e que deve reclamar.
        self.assertEqual(
            persistencia.ler_metadados('teste', self.pasta)['nome'], 'teste'
        )
        with self.assertRaises(ArtefatoAusente):
            persistencia.carregar('teste', pasta=self.pasta)

    # --- recusas -------------------------------------------------------------

    def test_recusa_artefato_sem_a_assinatura_do_projeto(self):
        """🚨 joblib.load executa codigo. Arquivo de origem desconhecida, nao."""
        caminho_modelo, caminho_json = self._salvar()
        caminho_json.write_text(
            json.dumps({'formato': 1, 'modelo': 'logistica', 'colunas': []}),
            encoding='utf-8',
        )

        with self.assertRaises(ArtefatoIncompativel) as contexto:
            persistencia.carregar('teste', pasta=self.pasta)

        self.assertIn('executa codigo', str(contexto.exception))

    def test_recusa_formato_desconhecido(self):
        _, caminho_json = self._salvar()
        dados = json.loads(caminho_json.read_text(encoding='utf-8'))
        dados['formato'] = 99
        caminho_json.write_text(json.dumps(dados), encoding='utf-8')

        with self.assertRaises(ArtefatoIncompativel):
            persistencia.carregar('teste', pasta=self.pasta)

    def test_recusa_versao_diferente_do_sklearn(self):
        """O pickle de um Pipeline nao e compativel entre versoes.

        E a falha e silenciosa: o objeto carrega e preve errado. Melhor recusar.
        """
        _, caminho_json = self._salvar()
        dados = json.loads(caminho_json.read_text(encoding='utf-8'))
        dados['sklearn'] = '0.1.0'
        caminho_json.write_text(json.dumps(dados), encoding='utf-8')

        with self.assertRaises(ArtefatoIncompativel) as contexto:
            persistencia.carregar('teste', pasta=self.pasta)

        self.assertIn('scikit-learn', str(contexto.exception))

    def test_versao_diferente_pode_ser_tolerada_explicitamente(self):
        _, caminho_json = self._salvar()
        dados = json.loads(caminho_json.read_text(encoding='utf-8'))
        dados['sklearn'] = '0.1.0'
        caminho_json.write_text(json.dumps(dados), encoding='utf-8')

        recarregado = persistencia.carregar(
            'teste', pasta=self.pasta, exigir_mesma_versao=False
        )

        self.assertEqual(recarregado.colunas, self.ajuste.colunas)

    def test_artefato_inexistente_diz_como_gerar(self):
        with self.assertRaises(ArtefatoAusente) as contexto:
            persistencia.carregar('nao_existe', pasta=self.pasta)

        self.assertIn('treinar_final', str(contexto.exception))

    # --- o contrato de colunas continua valendo ------------------------------

    def test_o_modelo_carregado_recusa_quadro_sem_as_colunas(self):
        """A guarda de `Ajuste` tem que sobreviver a ida e volta."""
        self._salvar()
        recarregado = persistencia.carregar('teste', pasta=self.pasta)

        with self.assertRaises(modelo.ColunaAusente):
            recarregado.prever_probabilidade(
                pd.DataFrame({'sst_variacao_7d': [0.1]})
            )

    def test_ordem_das_colunas_do_quadro_nao_importa(self):
        self._salvar()
        recarregado = persistencia.carregar('teste', pasta=self.pasta)
        invertido = self.quadro[list(reversed(self.quadro.columns))]

        self.assertEqual(
            list(recarregado.prever_probabilidade(self.quadro)),
            list(recarregado.prever_probabilidade(invertido)),
        )

    # --- listagem ------------------------------------------------------------

    def test_listar_pasta_vazia(self):
        self.assertEqual(persistencia.listar(self.pasta / 'vazia'), [])

    def test_listar_traz_os_gravados(self):
        self._salvar('um')
        self._salvar('dois')

        nomes = {m['nome'] for m in persistencia.listar(self.pasta)}

        self.assertEqual(nomes, {'um', 'dois'})

    def test_listar_nao_quebra_com_artefato_invalido(self):
        self._salvar('bom')
        (self.pasta / 'ruim.json').write_text('{"assinatura": "outro"}',
                                              encoding='utf-8')

        modelos = {m['nome']: m for m in persistencia.listar(self.pasta)}

        self.assertIn('erro', modelos['ruim'])
        self.assertNotIn('erro', modelos['bom'])
