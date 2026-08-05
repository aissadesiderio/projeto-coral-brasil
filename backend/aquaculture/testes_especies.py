"""Proveniencia das especies — a metade do projeto que nao tinha nenhuma.

🚨 O que estes testes protegem: **que o site nunca exiba uma categoria de
conservacao que nao consiga datar.**

Categoria da IUCN tem prazo de validade invisivel. `Dendrogyra cylindrus`, que
esta neste acervo, foi *Vulneravel* de 2008 a 2022 e hoje e *Criticamente
Ameacada* — as duas afirmacoes corretas, em anos diferentes. Sem o ano, a tela
nao distingue "e CR" de "era VU quando alguem digitou isto".

E e o campo que mais importa acertar: a categoria de conservacao e **o unico do
banco que uma pessoa vai citar**.
"""

import importlib
from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Especie


class ProcedenciaDaCategoriaTests(TestCase):
    """`iucn_tem_procedencia` decide se a categoria pode ser afirmada."""

    def test_categoria_com_ano_tem_procedencia(self):
        especie = Especie(iucn_categoria='CR', iucn_avaliado_em=2022)

        self.assertTrue(especie.iucn_tem_procedencia)

    def test_categoria_sem_ano_nao_tem_procedencia(self):
        """O caso das nove especies herdadas da lista digitada a mao."""
        especie = Especie(iucn_categoria='VU')

        self.assertFalse(especie.iucn_tem_procedencia)

    def test_ano_sem_categoria_tambem_nao(self):
        self.assertFalse(Especie(iucn_avaliado_em=2022).iucn_tem_procedencia)

    def test_especie_sem_nada_nao_tem_procedencia(self):
        self.assertFalse(Especie().iucn_tem_procedencia)

    def test_a_url_da_ficha_nao_substitui_o_ano(self):
        """⚠️ O link ajuda o leitor a conferir; o ano e o que torna datavel.

        Uma ficha da IUCN mostra a avaliacao **atual**. Guardar o link sem o
        ano nao registra qual avaliacao foi lida — so onde procurar outra.
        """
        especie = Especie(
            iucn_categoria='VU',
            fonte_iucn_url='https://www.iucnredlist.org/species/133012/54172206',
        )

        self.assertFalse(especie.iucn_tem_procedencia)


@override_settings(OFFLINE_MODE=False)
class ApiDeEspeciesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Especie.objects.all().delete()
        cls.datada = Especie.objects.create(
            nome_cientifico='Dendrogyra cylindrus',
            nome_comum='Coral-pilar',
            iucn_categoria='CR',
            iucn_avaliado_em=2022,
            iucn_versao='2024-1',
            fonte_iucn_url='https://www.iucnredlist.org/species/133184/16576167',
        )
        cls.sem_ano = Especie.objects.create(
            nome_cientifico='Mussismilia braziliensis',
            nome_comum='Coral-cerebro brasileiro',
            iucn_categoria='VU',
        )

    def buscar(self):
        return {
            item['nome_cientifico']: item
            for item in self.client.get(reverse('especie_list')).json()
        }

    def test_a_api_declara_se_a_categoria_pode_ser_afirmada(self):
        """🚨 A regra viaja no payload, e nao e reinventada por cada cliente.

        Mesmo motivo do `limiar` acompanhar a `probabilidade`: dois lugares
        decidindo a mesma coisa divergem em silencio.
        """
        por_nome = self.buscar()

        self.assertTrue(por_nome['Dendrogyra cylindrus']['iucn_tem_procedencia'])
        self.assertFalse(por_nome['Mussismilia braziliensis']['iucn_tem_procedencia'])

    def test_a_procedencia_completa_vem_junto(self):
        item = self.buscar()['Dendrogyra cylindrus']

        self.assertEqual(item['iucn_categoria'], 'CR')
        self.assertEqual(item['iucn_categoria_rotulo'], 'Criticamente ameacada')
        self.assertEqual(item['iucn_avaliado_em'], 2022)
        self.assertEqual(item['iucn_versao'], '2024-1')
        self.assertIn('iucnredlist.org', item['fonte_iucn_url'])

    def test_os_identificadores_taxonomicos_estao_no_contrato(self):
        """Sem eles, GBIF e OBIS nao tem por onde entrar (fase 3 do plano)."""
        item = self.buscar()['Dendrogyra cylindrus']

        for campo in ('aphia_id', 'gbif_key', 'status_taxonomico', 'nome_aceito'):
            self.assertIn(campo, item)

    def test_o_campo_de_texto_livre_nao_existe_mais(self):
        """`status_conservacao` guardava categoria sem id, sem ano e sem fonte."""
        item = self.buscar()['Dendrogyra cylindrus']

        self.assertNotIn('status_conservacao', item)


class ConferenciaVencidaTests(TestCase):
    """🚨 A condicao que teria pego o erro do `Mussismilia braziliensis`.

    Ter categoria e ano nao basta. A categoria envelhece porque a IUCN publica
    **outra** avaliacao, e o registro local continua apontando para a antiga —
    sem nada mudar nele, e portanto sem nada indicando que parou no tempo.
    """

    def test_conferencia_recente_nao_vence(self):
        especie = Especie(
            iucn_categoria='CR', iucn_avaliado_em=2022,
            iucn_consultado_em=date.today() - timedelta(days=30),
        )

        self.assertFalse(especie.iucn_conferencia_vencida)

    def test_conferencia_antiga_vence(self):
        especie = Especie(
            iucn_categoria='VU', iucn_avaliado_em=2008,
            iucn_consultado_em=date.today() - timedelta(days=1200),
        )

        self.assertTrue(especie.iucn_conferencia_vencida)

    def test_nunca_conferida_nao_conta_como_vencida(self):
        """São duas faltas diferentes, e misturá-las esconde uma delas.

        "Sem procedência" já é contado em outro lugar. Marcar também como
        vencida faria o mesmo problema aparecer duas vezes e o outro, nenhuma.
        """
        especie = Especie(iucn_categoria='VU')

        self.assertFalse(especie.iucn_conferencia_vencida)
        self.assertFalse(especie.iucn_tem_procedencia)


class RelatorioDeEnvelhecimentoTests(TestCase):
    """A procedência entra no `recados()` diário, e não num lembrete humano.

    ⚠️ Com 9 espécies a conferência cabe na memória de quem opera. Se as
    ocorrências passarem a vir do OBIS/GBIF pela bbox do recife, o catálogo vai
    para centenas — e o que não escala não é conferir, é **lembrar**.
    """

    @classmethod
    def setUpTestData(cls):
        from .models import LocalRecife, MedicaoAmbiental

        Especie.objects.all().delete()
        # ⚠️ Precisa haver medicao: `recados()` retorna cedo com "o banco esta
        # vazio", e esse recado domina de proposito — num banco recem-criado,
        # "rode a ingestao" e o unico que importa. Um cenario sem medicao
        # nenhuma nao exercitaria o caminho real.
        local = LocalRecife.objects.create(
            slug='local-recado', nome='Recado', estado='BA', cidade='Caravelas',
        )
        MedicaoAmbiental.objects.create(
            local_recife=local, data=date.today(), variavel='sst',
            valor=26.0, unidade='°C', fonte='noaa_crw',
        )

        Especie.objects.create(
            nome_cientifico='Com procedencia', iucn_categoria='LC',
            iucn_avaliado_em=2022, iucn_consultado_em=date.today(),
        )
        Especie.objects.create(nome_cientifico='Sem ano', iucn_categoria='VU')
        Especie.objects.create(
            nome_cientifico='Vencida', iucn_categoria='CR',
            iucn_avaliado_em=2015,
            iucn_consultado_em=date.today() - timedelta(days=1200),
        )

    def medir(self):
        from db import atualizacao

        return atualizacao.medir()

    def test_conta_as_duas_faltas_em_separado(self):
        estado = self.medir()

        self.assertEqual(estado.especies, 3)
        self.assertEqual(estado.especies_sem_procedencia, 1)
        self.assertEqual(estado.especies_com_conferencia_vencida, 1)
        self.assertEqual(estado.especies_a_conferir, 2)

    def test_o_recado_diario_menciona_as_duas(self):
        from db import atualizacao

        estado = self.medir()
        texto = ' '.join(atualizacao.recados(estado))

        self.assertIn('sem procedencia', texto)
        self.assertIn('conferencia vencida', texto)
        self.assertIn('conferir_especies', texto)

    def test_acervo_em_dia_nao_gera_recado(self):
        """Rotina que sempre avisa treina quem lê a ignorar todos."""
        from db import atualizacao

        Especie.objects.exclude(nome_cientifico='Com procedencia').delete()
        texto = ' '.join(atualizacao.recados(self.medir()))

        self.assertNotIn('especie', texto.lower())


class ComandoConferirEspeciesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Especie.objects.all().delete()
        Especie.objects.create(
            nome_cientifico='Mussismilia braziliensis', iucn_categoria='VU',
        )

    def rodar(self, *args):
        from io import StringIO

        from django.core.management import call_command

        saida = StringIO()
        call_command('conferir_especies', *args, stdout=saida)
        return saida.getvalue()

    def test_lista_a_especie_e_diz_o_que_falta(self):
        texto = self.rodar()

        self.assertIn('Mussismilia braziliensis', texto)
        self.assertIn('SEM ANO', texto)
        self.assertIn('nunca conferida', texto)

    def test_da_o_link_para_conferir(self):
        self.assertIn('iucnredlist.org', self.rodar())

    def test_com_taxon_id_o_link_e_a_ficha_e_nao_a_busca(self):
        """⚠️ Busca pode devolver vários resultados — é sinônimo de novo."""
        Especie.objects.update(iucn_taxon_id=133586)

        texto = self.rodar()

        self.assertIn('iucnredlist.org/species/133586', texto)
        self.assertNotIn('searchType=species', texto)

    def test_avisa_que_terceiro_se_cita_como_terceiro(self):
        self.assertIn('cita-se o terceiro', self.rodar())


class MigracaoDaCategoriaTests(TestCase):
    """A traducao dos rotulos digitados a mao para o codigo oficial."""

    def test_os_rotulos_conhecidos_viram_codigo(self):
        _0022 = importlib.import_module(
            'aquaculture.migrations.0022_proveniencia_das_especies'
        )

        self.assertEqual(_0022.PARA_CODIGO['Vulneravel'], 'VU')
        self.assertEqual(_0022.PARA_CODIGO['Criticamente ameacado'], 'CR')

    def test_nao_avaliado_nao_vira_NE(self):
        """A decisao mais delicada da migracao, travada por teste.

        "Nao avaliado" numa lista digitada e indistinguivel de "ninguem
        consultou" — e `NE` e uma **categoria real** da Lista Vermelha. Mapear
        um no outro afirmaria que a IUCN avaliou, o que e provavelmente **falso**
        para pelo menos duas das cinco especies que tinham esse valor:
        `Holacanthus ciliaris` e `Ocyurus chrysurus` tem avaliacao publicada.

        Inventar afirmacao errada e pior que registrar lacuna.
        """
        _0022 = importlib.import_module(
            'aquaculture.migrations.0022_proveniencia_das_especies'
        )

        self.assertNotIn('Nao avaliado', _0022.PARA_CODIGO)
        self.assertNotIn('NE', _0022.PARA_CODIGO.values())
