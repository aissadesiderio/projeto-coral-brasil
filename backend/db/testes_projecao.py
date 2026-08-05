"""Testes da projecao PostgreSQL -> Neo4j.

O que protegem, em ordem de gravidade:

1. **O id canonico da medicao inclui variavel e fonte.** Sem isso o `MERGE`
   sobrescreveria oito variaveis por dia em silencio, deixando uma — e o grafo
   pareceria completo.
2. **`limpar` so apaga o que a projecao criou.** Um `DETACH DELETE` cego levaria
   junto qualquer no criado a mao.
3. **`conferir` denuncia divergencia.** Uma projecao que falha no meio deixa o
   grafo parcial e silencioso; a conferencia e o que transforma "rodou" em
   "esta certo".
4. **Toda medicao tem proveniencia.** E a razao de o grafo existir.

Nao tocam no Neo4j: injetam uma conexao falsa que registra o Cypher.
"""

from datetime import date

from django.test import TestCase

from aquaculture.models import Especie, LocalRecife, MedicaoAmbiental
from db import projecao


class ConexaoFalsa:
    """Registra as chamadas e devolve o que for combinado."""

    def __init__(self, respostas=None):
        self.chamadas = []
        self.respostas = respostas or {}

    def run(self, cypher, parametros=None):
        self.chamadas.append((cypher, parametros or {}))
        for trecho, resposta in self.respostas.items():
            if trecho in cypher:
                return resposta
        return [{'n': 0}]

    def linhas_de(self, trecho):
        """As linhas passadas ao Cypher que contem `trecho`."""
        for cypher, parametros in self.chamadas:
            if trecho in cypher and 'linhas' in parametros:
                return parametros['linhas']
        return []


class ProjecaoTests(TestCase):
    def setUp(self):
        # ⚠️ As migracoes semeiam os tres recifes e nove especies. Como estes
        # testes conferem CONTAGENS, o dado semeado entraria no total e as
        # asercoes passariam ou falhariam por motivo errado. Zera-se primeiro.
        MedicaoAmbiental.objects.all().delete()
        Especie.objects.all().delete()
        LocalRecife.objects.all().delete()

        self.local = LocalRecife.objects.create(
            slug='teste-recife', nome='Recife de teste', estado='BA',
            cidade='Caravelas', latitude=-17.97, longitude=-38.69,
        )
        self.especie = Especie.objects.create(
            nome_cientifico='Mussismilia braziliensis', nome_comum='Coral-cerebro',
        )
        self.especie.locais.add(self.local)

        for variavel, fonte, dataset in (
            ('sst', 'noaa_crw', 'dhw_5km'),
            ('dhw', 'noaa_crw', 'dhw_5km'),
            ('salinidade', 'copernicus', 'cmems_phy_my'),
        ):
            MedicaoAmbiental.objects.create(
                local_recife=self.local, data=date(2026, 7, 24),
                variavel=variavel, valor=1.0, fonte=fonte, dataset_id=dataset,
            )

    # --- o id canonico ------------------------------------------------------

    def test_o_id_da_medicao_distingue_variavel_e_fonte(self):
        """🚨 A regressao mais grave possivel aqui.

        O schema antigo usava `slug:data`, herdado de `StatusPredicao`, onde uma
        linha era um dia. Agora uma linha e uma VARIAVEL de uma FONTE num dia —
        oito por local por dia. Com o id antigo, o `MERGE` casaria as oito no
        mesmo no e sobrescreveria sete, **sem erro nenhum**.
        """
        conexao = ConexaoFalsa()

        projecao.projetar_medicoes(conexao)

        ids = {linha['id'] for linha in conexao.linhas_de('MERGE (m:MedicaoAmbiental')}
        self.assertEqual(len(ids), 3, 'ids colidiram entre variaveis')
        self.assertIn('teste-recife:2026-07-24:sst:noaa_crw', ids)

    def test_a_mesma_variavel_de_fontes_diferentes_nao_colide(self):
        """SST existe no CRW e no Copernicus; as duas podem conviver."""
        MedicaoAmbiental.objects.create(
            local_recife=self.local, data=date(2026, 7, 24), variavel='sst',
            valor=25.0, fonte='copernicus', dataset_id='cmems_phy_my',
        )
        conexao = ConexaoFalsa()

        projecao.projetar_medicoes(conexao)

        ids = {linha['id'] for linha in conexao.linhas_de('MERGE (m:MedicaoAmbiental')}
        self.assertEqual(len(ids), 4)

    def test_a_fonte_junta_publicador_e_dataset(self):
        """A emenda reanalise->analise so e auditavel se o dataset entrar no id."""
        self.assertEqual(
            projecao._slug_fonte('copernicus', 'cmems_phy_my'),
            'copernicus:cmems_phy_my',
        )

    def test_fonte_sem_dataset_nao_vira_id_com_dois_pontos_solto(self):
        self.assertEqual(projecao._slug_fonte('noaa_crw', ''), 'noaa_crw')

    # --- proveniencia -------------------------------------------------------

    def test_toda_medicao_aponta_para_uma_fonte(self):
        conexao = ConexaoFalsa()

        projecao.projetar_medicoes(conexao)

        linhas = conexao.linhas_de('MERGE (m:MedicaoAmbiental')
        self.assertTrue(all(linha['fonte_id'] for linha in linhas))

    def test_as_fontes_saem_do_dado_e_nao_de_lista_fixa(self):
        """Se a ingestao passar a usar outro produto, a fonte aparece sozinha."""
        conexao = ConexaoFalsa()

        total = projecao.projetar_fontes(conexao)

        ids = {linha['id'] for linha in conexao.linhas_de('MERGE (n:FonteDados')}
        self.assertEqual(total, 2)
        self.assertEqual(ids, {'noaa_crw:dhw_5km', 'copernicus:cmems_phy_my'})

    def test_o_cypher_da_medicao_cria_as_duas_relacoes(self):
        conexao = ConexaoFalsa()

        projecao.projetar_medicoes(conexao)

        cypher = next(c for c, _ in conexao.chamadas if 'MERGE (m:MedicaoAmbiental' in c)
        self.assertIn('TEM_MEDICAO', cypher)
        self.assertIn('PROVENIENTE_DE', cypher)

    # --- limpeza ------------------------------------------------------------

    def test_limpar_filtra_pela_origem(self):
        """Nao tem autoridade sobre no que nao produziu."""
        conexao = ConexaoFalsa({'DETACH DELETE': [{'n': 0}]})

        projecao.limpar(conexao)

        cypher, parametros = conexao.chamadas[0]
        self.assertIn('origem_registro', cypher)
        self.assertEqual(parametros['origem'], projecao.ORIGEM)

    def test_limpar_vai_em_lotes(self):
        """Uma transacao com 172 mil elementos estoura a memoria da instancia."""
        respostas = iter([[{'n': projecao.LOTE}], [{'n': 7}]])

        class EmDoisPassos(ConexaoFalsa):
            def run(self, cypher, parametros=None):
                self.chamadas.append((cypher, parametros or {}))
                return next(respostas)

        conexao = EmDoisPassos()

        total = projecao.limpar(conexao)

        self.assertEqual(total, projecao.LOTE + 7)
        self.assertEqual(len(conexao.chamadas), 2)

    def test_tudo_projetado_carrega_a_marca_de_origem(self):
        conexao = ConexaoFalsa()

        projecao.projetar_localizacoes(conexao)
        projecao.projetar_especies(conexao)
        projecao.projetar_fontes(conexao)
        projecao.projetar_medicoes(conexao)

        for trecho in ('MERGE (n:Localizacao', 'MERGE (n:Especie',
                       'MERGE (n:FonteDados'):
            for linha in conexao.linhas_de(trecho):
                self.assertEqual(linha['origem_registro'], projecao.ORIGEM)
        for linha in conexao.linhas_de('MERGE (m:MedicaoAmbiental'):
            self.assertEqual(linha['props']['origem_registro'], projecao.ORIGEM)

    # --- constraints --------------------------------------------------------

    def test_as_constraints_sao_idempotentes(self):
        """Sem constraint o MERGE casa por varredura e pode duplicar."""
        conexao = ConexaoFalsa()

        projecao.garantir_constraints(conexao)

        for cypher, _ in conexao.chamadas:
            self.assertIn('IF NOT EXISTS', cypher)

    # --- lotes --------------------------------------------------------------

    def test_o_lote_parte_a_escrita(self):
        for i in range(20):
            MedicaoAmbiental.objects.create(
                local_recife=self.local, data=date(2026, 6, 1),
                variavel='sst', valor=float(i), fonte=f'fonte{i}',
                dataset_id='x',
            )
        conexao = ConexaoFalsa()

        projecao.projetar_medicoes(conexao, lote=5)

        escritas = [c for c, _ in conexao.chamadas if 'MERGE (m:MedicaoAmbiental' in c]
        self.assertGreaterEqual(len(escritas), 4)

    def test_devolve_quantas_medicoes_escreveu(self):
        conexao = ConexaoFalsa()

        self.assertEqual(projecao.projetar_medicoes(conexao), 3)

    # --- conferencia --------------------------------------------------------

    def test_conferir_aprova_quando_bate(self):
        conexao = ConexaoFalsa({
            '(n:Localizacao)': [{'n': 1}],
            '(n:Especie)': [{'n': 1}],
            '(n:FonteDados)': [{'n': 2}],
            '(n:MedicaoAmbiental)': [{'n': 3}],
            '[r:TEM_MEDICAO]': [{'n': 3}],
            '[r:PROVENIENTE_DE]': [{'n': 3}],
            'NOT (m)-[:PROVENIENTE_DE]': [{'n': 0}],
        })

        conferencias, orfas = projecao.conferir(conexao)

        self.assertEqual(orfas, 0)
        self.assertTrue(all(esperado == obtido for _, esperado, obtido in conferencias))

    def test_conferir_denuncia_projecao_parcial(self):
        """O caso perigoso: falhou no meio e o grafo responde incompleto."""
        conexao = ConexaoFalsa({
            '(n:Localizacao)': [{'n': 1}],
            '(n:Especie)': [{'n': 1}],
            '(n:FonteDados)': [{'n': 2}],
            '(n:MedicaoAmbiental)': [{'n': 2}],   # falta uma
            '[r:TEM_MEDICAO]': [{'n': 2}],
            '[r:PROVENIENTE_DE]': [{'n': 2}],
            'NOT (m)-[:PROVENIENTE_DE]': [{'n': 0}],
        })

        conferencias, _ = projecao.conferir(conexao)

        divergentes = [n for n, e, o in conferencias if e != o]
        self.assertIn('MedicaoAmbiental', divergentes)

    def test_conferir_denuncia_medicao_sem_proveniencia(self):
        conexao = ConexaoFalsa({'NOT (m)-[:PROVENIENTE_DE]': [{'n': 4}]})

        _, orfas = projecao.conferir(conexao)

        self.assertEqual(orfas, 4)

    # --- projecao completa --------------------------------------------------

    def test_projetar_conta_as_relacoes_derivadas(self):
        conexao = ConexaoFalsa()

        resultado = projecao.projetar(conexao, limpar_antes=False)

        self.assertEqual(resultado.medicoes, 3)
        self.assertEqual(resultado.rel_tem_medicao, 3)
        self.assertEqual(resultado.rel_proveniente, 3)
        self.assertEqual(resultado.localizacoes, 1)
        self.assertEqual(resultado.rel_abriga, 1)

    def test_sem_localizacao_as_medicoes_nao_ficam_orfas(self):
        """Sem o no de local, o MATCH nao casa e a medicao sumiria em silencio."""
        MedicaoAmbiental.objects.all().delete()
        Especie.objects.all().delete()
        LocalRecife.objects.all().delete()
        conexao = ConexaoFalsa()

        resultado = projecao.projetar(conexao, limpar_antes=False)

        self.assertEqual(resultado.medicoes, 0)
        self.assertTrue(resultado.avisos)
