"""O que estes testes travam.

⚠️ **Checkpoint e a funcionalidade com o maior potencial de dano silencioso do
projeto**, porque o defeito dele nao aparece como erro: aparece como trabalho
que deixou de ser feito. Um bloco pulado indevidamente vira buraco na serie, e
buraco na serie e exatamente o que ninguem percebe ate alguem plotar o ano
inteiro.

Os testes cobrem as tres formas de esse dano acontecer:

1. pular o que nao foi feito (`pendentes`, `--completo`);
2. refazer o que ja foi feito (o proposito, invertido);
3. afirmar como feito o que o banco nao tem (`conferir`).
"""

import json
from datetime import date

from django.test import TestCase

import checkpoints
from aquaculture.models import Checkpoint, LocalRecife
from ingestao.registro import tarefa_de
from observabilidade import contexto

TAREFA = 'teste.tarefa'


class RegistrarTests(TestCase):
    def test_saida_limpa_marca_concluido_com_a_evidencia(self):
        with checkpoints.registrar(TAREFA, 'bloco-1') as ponto:
            ponto.evidencia['gravadas'] = 406

        registro = Checkpoint.objects.get(tarefa=TAREFA, unidade='bloco-1')
        self.assertEqual(registro.status, Checkpoint.CONCLUIDO)
        self.assertEqual(registro.evidencia, {'gravadas': 406})
        self.assertIsNotNone(registro.concluido_em)
        self.assertEqual(registro.tentativas, 1)

    def test_excecao_marca_falhou_e_relanca(self):
        """Registrar a falha nao e trata-la.

        Se o gerenciador engolisse a excecao, um bloco que quebrou no meio
        pareceria ter passado — e o laco seguiria como se nada.
        """
        with self.assertRaises(ValueError):
            with checkpoints.registrar(TAREFA, 'bloco-1'):
                raise ValueError('erddap 408')

        registro = Checkpoint.objects.get(tarefa=TAREFA, unidade='bloco-1')
        self.assertEqual(registro.status, Checkpoint.FALHOU)
        self.assertIn('erddap 408', registro.erro)

    def test_tentativa_e_contada_na_entrada(self):
        """🚨 Contar na saida perderia a queda dura.

        Um `kill` no meio nao executa nenhum bloco de saida. Se a tentativa so
        fosse contada ao falhar, a unidade que derruba o processo toda vez
        seria tentada para sempre — o caso exato em que desistir importa.
        """
        try:
            with checkpoints.registrar(TAREFA, 'bloco-1'):
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            pass

        registro = Checkpoint.objects.get(tarefa=TAREFA, unidade='bloco-1')
        self.assertEqual(registro.tentativas, 1)

    def test_repetir_a_mesma_unidade_nao_cria_segunda_linha(self):
        for _ in range(3):
            with checkpoints.registrar(TAREFA, 'bloco-1'):
                pass

        self.assertEqual(
            Checkpoint.objects.filter(tarefa=TAREFA, unidade='bloco-1').count(), 1
        )
        registro = Checkpoint.objects.get(tarefa=TAREFA, unidade='bloco-1')
        self.assertEqual(registro.tentativas, 3)

    def test_guarda_a_correlacao_do_fluxo(self):
        with contexto(fluxo='ingestao') as identificador:
            with checkpoints.registrar(TAREFA, 'bloco-1'):
                pass

        registro = Checkpoint.objects.get(tarefa=TAREFA, unidade='bloco-1')
        self.assertEqual(registro.correlacao, identificador)


class PendentesTests(TestCase):
    def test_remove_o_que_ja_concluiu_e_preserva_a_ordem(self):
        """🚨 Ordem importa e nao e detalhe estetico.

        A ingestao pede blocos em ordem cronologica porque
        `ultima_data_ingerida` depende de a serie crescer pela ponta. Devolver
        um `set` quebraria isso de um jeito que so apareceria como buraco na
        serie, semanas depois.
        """
        with checkpoints.registrar(TAREFA, 'b'):
            pass

        self.assertEqual(
            checkpoints.pendentes(TAREFA, ['a', 'b', 'c', 'd']),
            ['a', 'c', 'd'],
        )

    def test_falha_continua_pendente(self):
        with self.assertRaises(ValueError):
            with checkpoints.registrar(TAREFA, 'a'):
                raise ValueError('x')

        self.assertEqual(checkpoints.pendentes(TAREFA, ['a']), ['a'])

    def test_interrompido_continua_pendente(self):
        """Um `em_andamento` que sobreviveu ao processo e rastro de queda."""
        Checkpoint.objects.create(
            tarefa=TAREFA, unidade='a', status=Checkpoint.EM_ANDAMENTO,
        )
        self.assertEqual(checkpoints.pendentes(TAREFA, ['a']), ['a'])

    def test_para_de_tentar_depois_do_limite(self):
        """O "tratar somente estas excecoes" do pedido.

        Cinco tentativas contra a mesma parede nao sao retomada: sao
        desperdicio com aparencia de esforco.
        """
        Checkpoint.objects.create(
            tarefa=TAREFA, unidade='a', status=Checkpoint.FALHOU,
            tentativas=checkpoints.TENTATIVAS_ATE_DESISTIR,
        )
        self.assertEqual(checkpoints.pendentes(TAREFA, ['a']), [])
        self.assertEqual(
            checkpoints.pendentes(TAREFA, ['a'], incluir_esgotadas=True), ['a']
        )
        self.assertEqual(
            list(checkpoints.esgotadas(TAREFA).values_list('unidade', flat=True)),
            ['a'],
        )

    def test_tarefas_diferentes_nao_se_misturam(self):
        with checkpoints.registrar('tarefa.a', 'bloco-1'):
            pass
        self.assertEqual(checkpoints.pendentes('tarefa.b', ['bloco-1']), ['bloco-1'])

    def test_limpar_devolve_a_unidade_para_a_fila(self):
        """Sem isto, corrigir um defeito no tratamento de um bloco nao teria
        efeito: o bloco seguiria marcado como concluido para sempre."""
        with checkpoints.registrar(TAREFA, 'a'):
            pass
        checkpoints.limpar(TAREFA)
        self.assertEqual(checkpoints.pendentes(TAREFA, ['a']), ['a'])


class ConferirTests(TestCase):
    """🚨 A defesa contra o checkpoint virar mentira duravel."""

    def test_sem_divergencia_devolve_lista_vazia(self):
        with checkpoints.registrar(TAREFA, 'a') as ponto:
            ponto.evidencia['gravadas'] = 406

        divergencias = checkpoints.conferir(
            TAREFA, lambda registro: {'gravadas': 406}
        )
        self.assertEqual(divergencias, [])

    def test_banco_esvaziado_aparece_como_divergencia(self):
        """O cenario concreto: alguem restaura um backup antigo.

        O checkpoint continua afirmando 406 medicoes, e sem `conferir` a
        proxima execucao pularia o bloco para sempre — buraco permanente e
        invisivel, porque o mecanismo criado para nao reprocessar e o mesmo que
        impede de notar.
        """
        with checkpoints.registrar(TAREFA, 'a') as ponto:
            ponto.evidencia['gravadas'] = 406

        divergencias = checkpoints.conferir(
            TAREFA, lambda registro: {'gravadas': 0}
        )
        self.assertEqual(len(divergencias), 1)
        _, esperado, encontrado = divergencias[0]
        self.assertEqual(esperado, {'gravadas': 406})
        self.assertEqual(encontrado, {'gravadas': 0})

    def test_verificador_que_devolve_none_e_pulado(self):
        """Nem toda unidade e conferivel, e fingir que e produziria alarme falso."""
        with checkpoints.registrar(TAREFA, 'a') as ponto:
            ponto.evidencia['gravadas'] = 406
        self.assertEqual(checkpoints.conferir(TAREFA, lambda r: None), [])

    def test_so_confere_o_que_concluiu(self):
        with self.assertRaises(ValueError):
            with checkpoints.registrar(TAREFA, 'a'):
                raise ValueError('x')
        self.assertEqual(checkpoints.conferir(TAREFA, lambda r: {'x': 1}), [])


class ManifestoTests(TestCase):
    def test_soma_a_evidencia_so_do_que_concluiu(self):
        with checkpoints.registrar(TAREFA, 'a') as ponto:
            ponto.evidencia['gravadas'] = 400
        with checkpoints.registrar(TAREFA, 'b') as ponto:
            ponto.evidencia['gravadas'] = 6
        with self.assertRaises(ValueError):
            with checkpoints.registrar(TAREFA, 'c') as ponto:
                ponto.evidencia['gravadas'] = 99
                raise ValueError('x')

        manifesto = checkpoints.montar(TAREFA)
        self.assertEqual(
            manifesto['resumo']['totais_da_evidencia'], {'gravadas': 406}
        )
        self.assertEqual(manifesto['resumo']['por_status']['concluido'], 2)
        self.assertEqual(manifesto['resumo']['por_status']['falhou'], 1)

    def test_lista_tambem_o_que_falhou(self):
        """Um manifesto que lista so o sucesso descreve um pipeline que nunca
        falhou — e nenhum pipeline e assim."""
        with self.assertRaises(ValueError):
            with checkpoints.registrar(TAREFA, 'c'):
                raise ValueError('erddap 408')

        unidades = checkpoints.montar(TAREFA)['unidades']
        self.assertEqual(len(unidades), 1)
        self.assertIn('erddap 408', unidades[0]['erro'])

    def test_json_e_parseavel_e_traz_versao_de_formato(self):
        with checkpoints.registrar(TAREFA, 'a'):
            pass
        dados = json.loads(checkpoints.como_json(TAREFA))
        self.assertEqual(dados['versao_formato'], 1)
        self.assertEqual(dados['tarefa'], TAREFA)


class NomeDaTarefaTests(TestCase):
    def test_locais_diferentes_nao_compartilham_checkpoint(self):
        """🚨 O defeito que uma tarefa unica causaria.

        Os rotulos de bloco sao os mesmos em todo local ("2020-01-01 a
        2020-06-28"). Com uma tarefa so, o bloco de Abrolhos marcaria como
        concluido o bloco homonimo de Picaozinho, e a serie do segundo ficaria
        vazia sem nenhum erro em lugar nenhum.
        """
        self.assertNotEqual(
            tarefa_de('noaa-crw', 'abrolhos-ba'),
            tarefa_de('noaa-crw', 'picaozinho-pb'),
        )
        self.assertNotEqual(
            tarefa_de('noaa-crw', 'abrolhos-ba'),
            tarefa_de('copernicus', 'abrolhos-ba'),
        )


class VerificadorDeIngestaoTests(TestCase):
    """O parsing do rotulo da unidade - a parte que mais facilmente erra calado."""

    def setUp(self):
        from aquaculture.models import MedicaoAmbiental

        self.local, _ = LocalRecife.objects.get_or_create(
            slug='abrolhos-ba',
            defaults={
                'nome': 'Abrolhos', 'estado': 'BA', 'cidade': 'Caravelas',
                'latitude': -17.972, 'longitude': -38.688, 'ativo': True,
            },
        )
        MedicaoAmbiental.objects.filter(local_recife=self.local).delete()
        for dia in (date(2020, 1, 2), date(2020, 1, 3)):
            MedicaoAmbiental.objects.create(
                local_recife=self.local, data=dia, variavel='sst',
                valor=27.0, unidade='degree_C', fonte='noaa-crw',
            )

    def _verificar(self, tarefa, unidade):
        from aquaculture.management.commands.checkpoints import (
            _verificador_de_ingestao,
        )
        return _verificador_de_ingestao(
            Checkpoint(tarefa=tarefa, unidade=unidade, evidencia={})
        )

    def test_conta_as_medicoes_do_periodo_da_unidade(self):
        self.assertEqual(
            self._verificar('ingestao.noaa-crw.abrolhos-ba', '2020-01-01 a 2020-01-05'),
            {'gravadas': 2},
        )

    def test_periodo_fora_da_janela_nao_conta(self):
        self.assertEqual(
            self._verificar('ingestao.noaa-crw.abrolhos-ba', '2021-01-01 a 2021-01-05'),
            {'gravadas': 0},
        )

    def test_outra_fonte_nao_conta(self):
        """As duas fontes convivem no mesmo dia; contar as duas juntas faria
        todo bloco parecer ter o dobro do que gravou."""
        self.assertEqual(
            self._verificar('ingestao.copernicus.abrolhos-ba', '2020-01-01 a 2020-01-05'),
            {'gravadas': 0},
        )

    def test_tarefa_que_nao_e_ingestao_devolve_none(self):
        """🚨 Conferir o que nao se sabe conferir produz alarme falso.

        E alarme falso e pior que nao conferir: treina quem le a ignorar a
        saida, e ai a divergencia real passa junto.
        """
        self.assertIsNone(self._verificar('treino.leave-year-out', '2020'))
        self.assertIsNone(self._verificar('ingestao.noaa-crw', '2020-01-01 a 2020-01-05'))

    def test_unidade_em_formato_inesperado_devolve_none(self):
        self.assertIsNone(
            self._verificar('ingestao.noaa-crw.abrolhos-ba', 'bloco-1')
        )


class IngestaoUsaCheckpointTests(TestCase):
    """A ligacao com o fluxo real - o resto e mecanismo sem uso."""

    def setUp(self):
        # ⚠️ `get_or_create`: as migracoes ja semeiam `abrolhos-ba` (0010) e
        # mais nove locais (0025). Criar aqui esbarra na unicidade do slug.
        self.local, _ = LocalRecife.objects.get_or_create(
            slug='abrolhos-ba',
            defaults={
                'nome': 'Abrolhos', 'estado': 'BA', 'cidade': 'Caravelas',
                'latitude': -17.972, 'longitude': -38.688, 'ativo': True,
            },
        )

    def _conector_falso(self):
        """Um conector que responde com sucesso e **zero observacoes**.

        🚨 E de proposito o caso que motiva o checkpoint existir: a fonte foi
        consultada e nao tinha nada para aquele periodo. Do lado do dado, o
        resultado e indistinguivel de um bloco nunca pedido - `ultima_data_
        ingerida` nao avanca em nenhum dos dois casos. So o checkpoint separa
        "tentei e nao havia" de "nao tentei".
        """
        from ingestao.base import ResultadoColeta

        class Falso:
            slug = 'noaa-crw'
            chamados = []

            def coletar(self, local, inicio, fim):
                Falso.chamados.append((inicio, fim))
                return ResultadoColeta(observacoes=[], dataset_id='dhw_5km')

        Falso.chamados = []
        return Falso()

    def test_segunda_execucao_incremental_pula_o_que_ja_foi_feito(self):
        from ingestao.registro import ingerir

        conector = self._conector_falso()
        ingerir(self.local, date(2020, 1, 1), date(2020, 1, 10), conector,
                incremental=True, janela_dias=5)
        primeira = list(type(conector).chamados)

        conector2 = self._conector_falso()
        ingerir(self.local, date(2020, 1, 1), date(2020, 1, 10), conector2,
                incremental=True, janela_dias=5)

        self.assertEqual(len(primeira), 2)
        self.assertEqual(
            type(conector2).chamados, [],
            'A segunda execucao incremental refez blocos ja marcados como '
            'concluidos - o checkpoint nao esta sendo consultado.',
        )

    def test_completo_ignora_o_checkpoint(self):
        """🚨 Sem isto, `--completo` viraria um sinonimo caro de "nao faz nada".

        A bandeira continuaria existindo e documentada, sem efeito nenhum - o
        pior formato de defeito, porque quem a usa acredita ter refeito tudo.
        """
        from ingestao.registro import ingerir

        conector = self._conector_falso()
        ingerir(self.local, date(2020, 1, 1), date(2020, 1, 10), conector,
                incremental=True, janela_dias=5)

        conector2 = self._conector_falso()
        ingerir(self.local, date(2020, 1, 1), date(2020, 1, 10), conector2,
                incremental=False, janela_dias=5)

        self.assertEqual(
            len(type(conector2).chamados), 2,
            'Com --completo o checkpoint nao pode pular bloco nenhum.',
        )
