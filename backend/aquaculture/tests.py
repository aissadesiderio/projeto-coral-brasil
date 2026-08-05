from contextlib import contextmanager
from datetime import date
from io import StringIO
import json
from pathlib import Path
import re
import shutil
import tempfile
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin import LocalRecifeAdmin
from .management.commands.testar_fontes import _origem_das_credenciais
from .management.utils import exigir_migrations_aplicadas, migrations_pendentes
from .code_sync import (
    BACKEND_SYNC_PATH,
    FRONTEND_SYNC_PATH,
    sync_project_code_from_db,
)
from .inventario_datasets import (
    DATASETS_REAIS,
    EXCLUIDOS,
    construir_inventario,
)
from .models import DatasetCatalogo, Especie, LocalRecife
from .neo4j_schema import SCHEMA_QUERIES
from .neo4j_service import Neo4jServiceError, listar_localizacoes_grafo, obter_localizacao_grafo


@override_settings(OFFLINE_MODE=False)
class LocalRecifeApiTests(TestCase):
    def setUp(self):
        self.local, _ = LocalRecife.objects.update_or_create(
            slug='abrolhos-ba',
            defaults={
                'nome': 'Parque Nacional Marinho de Abrolhos',
                'estado': 'Bahia',
                'cidade': 'Caravelas',
                'descricao': 'Local de teste para API.',
            },
        )
        self.especie, _ = Especie.objects.update_or_create(
            nome_cientifico='Mussismilia braziliensis',
            defaults={
                'nome_comum': 'Coral-cerebro brasileiro',
                'tipo': 'CORAL',
            },
        )
        self.especie.locais.add(self.local)

    def test_local_detail_returns_species(self):
        response = self.client.get(reverse('local_recife_detail', kwargs={'slug': self.local.slug}))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['slug'], self.local.slug)
        nomes = [item['nome_cientifico'] for item in payload['especies']]
        self.assertIn('Mussismilia braziliensis', nomes)

    def test_a_api_nao_serve_mais_o_caminho_legado(self):
        """🚨 `monitoramento_recente` era `StatusPredicao`, removido em 30/07.

        Ele publicava `risco_integrado` e `nivel_alerta` — dois campos com
        nome de resultado e nenhuma conta por tras — para qualquer cliente da
        API, muito depois de o site ter parado de exibi-los.
        """
        for rota in (
            reverse('local_recife_detail', kwargs={'slug': self.local.slug}),
            reverse('local_recife_list'),
        ):
            with self.subTest(rota=rota):
                corpo = self.client.get(rota).json()
                texto = json.dumps(corpo)

                for campo in (
                    'monitoramento_recente', 'risco_integrado',
                    'nivel_alerta', 'nivel_alerta_atual', 'risco_atual',
                ):
                    self.assertNotIn(campo, texto)

    def test_possui_painel_risco_sai_do_artefato_e_nao_de_registro_legado(self):
        """A resposta precisa concordar com quem devolve 404 no painel.

        Antes de 30/07/2026 este campo era `bool(StatusPredicao)`, com queda
        para o registro global — e por isso dizia `true` para **todo** recife
        cadastrado, inclusive um que o modelo nunca viu.
        """
        fora_do_treino = LocalRecife.objects.create(
            slug='recife-fora-do-treino', nome='Fora do Treino',
            estado='Bahia', cidade='Caravelas',
        )

        with patch(
            'ml.persistencia.ler_metadados',
            return_value={'locais': [self.local.slug]},
        ):
            por_slug = {
                item['slug']: item
                for item in self.client.get(reverse('local_recife_list')).json()
            }

        self.assertTrue(por_slug[self.local.slug]['possui_painel_risco'])
        self.assertFalse(por_slug[fora_do_treino.slug]['possui_painel_risco'])

    def test_sem_artefato_nenhum_recife_anuncia_painel(self):
        """⚠️ O catalogo nao pode cair porque `treinar_final` nao rodou."""
        from ml import persistencia

        with patch(
            'ml.persistencia.ler_metadados',
            side_effect=persistencia.ArtefatoAusente('sem artefato'),
        ):
            response = self.client.get(reverse('local_recife_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            all(item['possui_painel_risco'] is False for item in response.json())
        )

    def test_especie_list_can_filter_by_local(self):
        response = self.client.get(f"{reverse('especie_list')}?local={self.local.slug}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        nomes = [item['nome_cientifico'] for item in payload]
        self.assertIn('Mussismilia braziliensis', nomes)


@override_settings(OFFLINE_MODE=True)
class OfflineModeTests(TestCase):
    """O portao de manutencao precisa devolver 503, nao estourar 500.

    Regressao: `OfflineModeMixin.dispatch` devolvia um `Response` do DRF sem
    renderizador, o que levantava AssertionError antes de chegar ao cliente.
    """

    def setUp(self):
        # Slug e nome proprios para nao colidir com os seeds das migrations.
        self.local = LocalRecife.objects.create(
            slug='recife-offline-teste',
            nome='Recife de Teste Offline',
            estado='Bahia',
            cidade='Caravelas',
        )
        self.especie = Especie.objects.create(
            nome_cientifico='Testus offlinus',
            nome_comum='Especie de teste offline',
        )

    def test_todas_as_rotas_publicas_respondem_503(self):
        rotas = [
            reverse('local_recife_list'),
            reverse('local_recife_detail', kwargs={'slug': self.local.slug}),
            reverse('especie_list'),
            reverse('especie_detail', kwargs={'pk': self.especie.pk}),
            reverse('medicao_list'),
        ]

        for rota in rotas:
            with self.subTest(rota=rota):
                response = self.client.get(rota)

                self.assertEqual(response.status_code, 503)
                self.assertIn('offline', response.json()['detail'].lower())

    def test_endpoint_de_status_continua_acessivel(self):
        """O frontend precisa conseguir detectar o modo offline."""
        response = self.client.get(reverse('api_status'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['offline_mode'])


@override_settings(OFFLINE_MODE=False)
class DatasetCatalogoApiTests(TestCase):
    def setUp(self):
        self.local, _ = LocalRecife.objects.update_or_create(
            slug='recife-datasets-teste-ba',
            defaults={
                'nome': 'Recife de Datasets Teste',
                'estado': 'Bahia',
                'cidade': 'Ilheus',
                'descricao': 'Local de teste para datasets relacionados.',
                'ativo': True,
            },
        )
        DatasetCatalogo.objects.update_or_create(
            id='dataset_teste_slug_canonico',
            defaults={
                'titulo': 'Temperatura da superficie do mar - Recife de Datasets Teste',
                'resumo': 'Serie mensal de temperatura da superficie do mar.',
                'fonte': 'Copernicus',
                'tipo_dado': 'Climatico',
                'localizacao': 'Recife de Datasets Teste',
                'local_slug': 'recife-datasets-teste-ba',
                'estado': 'Bahia',
                'cidade': 'Ilheus',
                'formato': 'CSV',
                'recorte_temporal': 'intervalo',
                'data_inicio': date(2026, 3, 1),
                'data_fim': date(2026, 3, 31),
                'periodo_rotulo': 'Mar/2026',
                'tamanho_mb': 1843.2,
                'url_download': '/dados/sst.csv',
                'ordem_exibicao': 1,
                'ativo': True,
            },
        )
        DatasetCatalogo.objects.update_or_create(
            id='relatorio_abrolhos_sem_slug',
            defaults={
                'titulo': 'Relatorio de campo de Abrolhos',
                'resumo': 'Dataset relacionado por cidade e estado sem local_slug canonico.',
                'fonte': 'Projeto Coral Brasil',
                'tipo_dado': 'Relatorio',
                'localizacao': 'Recife de Datasets Teste',
                'local_slug': '',
                'estado': 'Bahia',
                'cidade': 'Ilheus',
                'formato': 'PDF',
                'recorte_temporal': 'publicacao',
                'data_publicacao': date(2026, 4, 18),
                'periodo_rotulo': 'Abr/2026',
                'tamanho_mb': 24.5,
                'url_download': '/dados/relatorio-abrolhos.pdf',
                'ordem_exibicao': 2,
                'ativo': True,
            },
        )
        DatasetCatalogo.objects.update_or_create(
            id='dataset_inativo',
            defaults={
                'titulo': 'Dataset inativo',
                'resumo': 'Nao deve aparecer na API.',
                'fonte': 'Interno',
                'tipo_dado': 'Relatorio',
                'localizacao': 'Costa Nordeste',
                'estado': 'Regional',
                'cidade': 'Costa Nordeste',
                'formato': 'PDF',
                'recorte_temporal': 'publicacao',
                'data_publicacao': date(2026, 4, 22),
                'periodo_rotulo': 'Abr/2026',
                'tamanho_mb': 12,
                'ordem_exibicao': 99,
                'ativo': False,
            },
        )
        DatasetCatalogo.objects.update_or_create(
            id='dataset_picaozinho',
            defaults={
                'titulo': 'Microbioma de Picaozinho',
                'resumo': 'Nao deve aparecer para Abrolhos.',
                'fonte': 'NCBI',
                'tipo_dado': 'Microbioma',
                'localizacao': 'Recife de Picaozinho',
                'local_slug': 'picaozinho-pb',
                'estado': 'Paraiba',
                'cidade': 'Joao Pessoa',
                'formato': 'FASTQ',
                'recorte_temporal': 'intervalo',
                'data_inicio': date(2026, 3, 10),
                'data_fim': date(2026, 3, 24),
                'periodo_rotulo': 'Mar/2026',
                'tamanho_mb': 3174.4,
                'url_download': '',
                'ordem_exibicao': 3,
                'ativo': True,
            },
        )

    def test_dataset_catalog_list_returns_public_shape(self):
        response = self.client.get(reverse('dataset_catalogo_list'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        ids = [item['id'] for item in payload]
        self.assertIn('dataset_teste_slug_canonico', ids)
        self.assertNotIn('dataset_inativo', ids)

        dataset = next(item for item in payload if item['id'] == 'dataset_teste_slug_canonico')
        self.assertEqual(dataset['tipo_dado'], 'Climatico')
        self.assertEqual(dataset['periodo_rotulo'], 'Mar/2026')
        self.assertEqual(dataset['tamanho_mb'], 1843.2)
        self.assertEqual(dataset['url_download'], '/dados/sst.csv')

    def test_local_related_dataset_endpoint_prioritizes_real_matches_and_transition_fields(self):
        response = self.client.get(
            reverse('local_recife_datasets_list', kwargs={'slug': self.local.slug})
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        ids = [item['id'] for item in payload]

        self.assertEqual(
            ids,
            ['dataset_teste_slug_canonico', 'relatorio_abrolhos_sem_slug'],
        )
        self.assertNotIn('dataset_picaozinho', ids)
        self.assertTrue(all(item['localizacao'] for item in payload))

    def test_local_related_dataset_endpoint_returns_404_for_unknown_local(self):
        response = self.client.get(
            reverse('local_recife_datasets_list', kwargs={'slug': 'local-inexistente'})
        )

        self.assertEqual(response.status_code, 404)


@override_settings(OFFLINE_MODE=False)
class GrafoLocalizacaoApiTests(TestCase):
    @patch('aquaculture.views.listar_localizacoes_grafo')
    def test_grafo_localizacao_list_returns_neo4j_payload(self, listar_mock):
        listar_mock.return_value = [
            {
                'slug': 'abrolhos-ba',
                'nome': 'Parque Nacional Marinho de Abrolhos',
                'estado': 'Bahia',
                'cidade': 'Caravelas',
                'descricao': 'Local de teste para o grafo.',
                'ultima_atualizacao': '2026-04-16',
                'quantidade_especies': 1,
                'quantidade_predicoes': 2,
                'risco_atual': 78.0,
                'nivel_alerta_atual': 'ALERTA_1',
                'ultima_predicao_data': '2026-04-16',
            }
        ]

        response = self.client.get(reverse('grafo_localizacoes'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload[0]['slug'], 'abrolhos-ba')
        self.assertEqual(payload[0]['quantidade_predicoes'], 2)
        self.assertEqual(payload[0]['nivel_alerta_atual'], 'ALERTA_1')

    @patch('aquaculture.views.obter_localizacao_grafo')
    def test_grafo_localizacao_detail_returns_404_when_slug_is_missing(self, obter_mock):
        obter_mock.return_value = None

        response = self.client.get(
            reverse('grafo_localizacao_detail', kwargs={'slug': 'inexistente'})
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Localizacao nao encontrada no grafo.')

    @patch('aquaculture.views.obter_localizacao_grafo')
    def test_grafo_localizacao_detail_returns_503_when_neo4j_is_unavailable(self, obter_mock):
        obter_mock.side_effect = Neo4jServiceError('Falha de conexao')

        response = self.client.get(
            reverse('grafo_localizacao_detail', kwargs={'slug': 'abrolhos-ba'})
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['detail'], 'Neo4j indisponivel no momento.')


class Neo4jServiceReadTests(TestCase):
    @patch('aquaculture.neo4j_service.executar_read')
    def test_listar_localizacoes_grafo_returns_current_alert_level(self, executar_read_mock):
        executar_read_mock.return_value = [
            {
                'slug': 'abrolhos-ba',
                'nome': 'Parque Nacional Marinho de Abrolhos',
                'estado': 'Bahia',
                'cidade': 'Caravelas',
                'descricao': 'Local de teste para o grafo.',
                'ultima_atualizacao': '2026-04-16',
                'quantidade_especies': 1,
                'quantidade_predicoes': 2,
                'risco_atual': 78.0,
                'nivel_alerta_atual': 'ALERTA_1',
                'ultima_predicao_data': '2026-04-16',
            }
        ]

        payload = listar_localizacoes_grafo()

        self.assertEqual(payload[0]['risco_atual'], 78.0)
        self.assertEqual(payload[0]['nivel_alerta_atual'], 'ALERTA_1')
        self.assertEqual(payload[0]['ultima_predicao_data'], '2026-04-16')

    @patch('aquaculture.neo4j_service.executar_read')
    def test_obter_localizacao_grafo_returns_local_with_species_and_predictions(self, executar_read_mock):
        executar_read_mock.side_effect = [
            [
                {
                    'slug': 'abrolhos-ba',
                    'nome': 'Parque Nacional Marinho de Abrolhos',
                    'estado': 'Bahia',
                    'cidade': 'Caravelas',
                    'descricao': 'Local de teste para o grafo.',
                    'ultima_atualizacao': '2026-04-16',
                    'ativo': True,
                }
            ],
            [
                {
                    'nome_cientifico': 'Mussismilia braziliensis',
                    'nome_comum': 'Coral-cerebro brasileiro',
                    'tipo': 'CORAL',
                    'descricao': 'Especie formadora de recife.',
                    'iucn_categoria': 'VU',
                    'credito_imagem': 'Equipe local',
                    'fonte_imagem_url': 'https://exemplo.org/imagem',
                    'fonte_url': 'https://exemplo.org/especie',
                }
            ],
            [
                {
                    'local_slug': 'abrolhos-ba',
                    'data': '2026-04-16',
                    'sst_atual': 29.1,
                    'limite_termico': 27.0,
                    'anomalia': 2.1,
                    'dhw_calculado': 6.4,
                    'irradiancia': 32.5,
                    'turbidez': 0.18,
                    'salinidade': 36.0,
                    'ph': 8.1,
                    'oxigenio': 6.5,
                    'nitrato': 0.4,
                    'clorofila': 0.7,
                    'risco_integrado': 78.0,
                    'nivel_alerta': 'ALERTA_1',
                }
            ],
        ]

        payload = obter_localizacao_grafo('abrolhos-ba')

        self.assertIsNotNone(payload)
        self.assertEqual(payload['slug'], 'abrolhos-ba')
        self.assertEqual(payload['especies'][0]['nome_cientifico'], 'Mussismilia braziliensis')
        self.assertEqual(payload['predicoes'][0]['nivel_alerta'], 'ALERTA_1')
        expected_parameters = {'localizacao_id': 'abrolhos-ba'}
        self.assertEqual(executar_read_mock.call_args_list[0].args[1], expected_parameters)
        self.assertEqual(executar_read_mock.call_args_list[1].args[1], expected_parameters)
        self.assertEqual(executar_read_mock.call_args_list[2].args[1], expected_parameters)


class Neo4jCommandWiringTests(TestCase):
    @patch('aquaculture.management.commands.neo4j_init.executar_queries_schema')
    @patch('aquaculture.management.commands.neo4j_init.verificar_conexao_neo4j')
    def test_neo4j_init_uses_canonical_schema_queries(self, verificar_mock, executar_mock):
        executar_mock.return_value = len(SCHEMA_QUERIES)

        call_command('neo4j_init', stdout=StringIO())

        verificar_mock.assert_called_once_with()
        executar_mock.assert_called_once_with(SCHEMA_QUERIES)

    def test_neo4j_seed_e_setup_graph_nao_existem_mais(self):
        """O bootstrap legado do grafo foi removido em 28/07/2026.

        `neo4j_seed` derivava os nos de `StatusPredicao` — os 3 registros do
        caminho legado — e `db/setup_graph.py` so delegava para ele. Quem
        reconstroi o grafo hoje e `neo4j_projetar`, a partir do PostgreSQL.

        Este teste existe para o par nao voltar por copia de um tutorial
        antigo: sao dois caminhos de escrita no mesmo grafo, e o legado
        sobrescreveria a projecao com dado de 2026-04.
        """
        from django.core.management import get_commands

        self.assertNotIn('neo4j_seed', get_commands())

        with self.assertRaises(ImportError):
            from db import setup_graph  # noqa: F401


@override_settings(OFFLINE_MODE=False)
class DjangoAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='senha-forte-123',
        )

    def test_admin_login_and_changelist_work(self):
        self.client.login(username='admin', password='senha-forte-123')

        admin_index = self.client.get('/admin/')
        local_changelist = self.client.get('/admin/aquaculture/localrecife/')

        self.assertEqual(admin_index.status_code, 200)
        self.assertEqual(local_changelist.status_code, 200)

    def test_salvar_no_admin_nao_reescreve_arquivos_de_codigo(self):
        """Regressao: editar dados nao pode sujar a arvore do git.

        `SyncToCodeAdminMixin` disparava `sync_project_code_from_db()` em
        `save_related`, entao qualquer save no admin reescrevia
        `frontend/src/recifeData.js`. Agora isso so acontece pela acao
        explicita ou por `manage.py sync_admin_code`.
        """
        antes_frontend = (
            FRONTEND_SYNC_PATH.read_text(encoding='utf-8')
            if FRONTEND_SYNC_PATH.exists()
            else None
        )
        antes_backend = (
            BACKEND_SYNC_PATH.read_text(encoding='utf-8')
            if BACKEND_SYNC_PATH.exists()
            else None
        )

        self.client.login(username='admin', password='senha-forte-123')
        local = LocalRecife.objects.create(
            slug='recife-admin-teste',
            nome='Recife Admin Teste',
            estado='Bahia',
            cidade='Caravelas',
        )
        url = f'/admin/aquaculture/localrecife/{local.pk}/change/'

        # Os prefixos dos inlines sao lidos do formulario renderizado para o
        # teste nao quebrar caso os inlines mudem.
        html = self.client.get(url).content.decode()
        dados = {
            'slug': local.slug,
            'nome': 'Recife Admin Teste Editado',
            'estado': 'Bahia',
            'cidade': 'Caravelas',
            'descricao': 'Alteracao feita pelo teste.',
            'ativo': 'on',
        }
        for prefixo in set(re.findall(r'name="([\w\-]+)-TOTAL_FORMS"', html)):
            dados[f'{prefixo}-TOTAL_FORMS'] = '0'
            dados[f'{prefixo}-INITIAL_FORMS'] = '0'
            dados[f'{prefixo}-MIN_NUM_FORMS'] = '0'
            dados[f'{prefixo}-MAX_NUM_FORMS'] = '1000'

        response = self.client.post(url, dados, follow=True)

        self.assertEqual(response.status_code, 200)
        local.refresh_from_db()
        self.assertEqual(
            local.nome,
            'Recife Admin Teste Editado',
            'O formulario do admin nao salvou - o teste nao chegou a exercitar o sync.',
        )

        depois_frontend = (
            FRONTEND_SYNC_PATH.read_text(encoding='utf-8')
            if FRONTEND_SYNC_PATH.exists()
            else None
        )
        depois_backend = (
            BACKEND_SYNC_PATH.read_text(encoding='utf-8')
            if BACKEND_SYNC_PATH.exists()
            else None
        )
        self.assertEqual(antes_frontend, depois_frontend, 'recifeData.js foi reescrito')
        self.assertEqual(antes_backend, depois_backend, 'generated_admin_sync.py foi reescrito')


@override_settings(OFFLINE_MODE=False)
class SyncCodeTests(TestCase):
    def test_sync_project_code_from_db_writes_expected_files(self):
        local = LocalRecife.objects.create(
            slug='recife-teste-rj',
            nome='Recife Teste',
            estado='Rio de Janeiro',
            cidade='Arraial do Cabo',
            descricao='Local criado para validar sincronizacao em codigo.',
        )
        especie = Especie.objects.create(
            nome_cientifico='Especie testus',
            nome_comum='Especie de teste',
            tipo='CORAL',
            credito_imagem='Equipe local',
            fonte_imagem_url='https://exemplo.org/imagem',
        )
        especie.locais.add(local)

        output_dir = Path(__file__).resolve().parent / '_sync_test_output'
        output_dir.mkdir(exist_ok=True)
        try:
            backend_out = output_dir / 'generated_sync.py'
            frontend_out = output_dir / 'generated_sync.js'
            result = sync_project_code_from_db(
                backend_output_path=backend_out,
                frontend_output_path=frontend_out,
            )

            backend_text = backend_out.read_text(encoding='utf-8')
            frontend_text = frontend_out.read_text(encoding='utf-8')
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

        self.assertTrue(result['backend_changed'])
        self.assertTrue(result['frontend_changed'])
        self.assertIn('Recife Teste', backend_text)
        self.assertIn('Especie de teste', backend_text)
        self.assertIn('https://exemplo.org/imagem', frontend_text)

    def test_o_codigo_exportado_nao_carrega_mais_numero_de_risco(self):
        """🚨 O fallback do frontend guardava risco e nivel de alerta.

        Eram os campos do `StatusPredicao`, gravados dentro de um arquivo `.js`
        versionado — o pior lugar possivel para um numero de demonstracao,
        porque ele sobrevive a qualquer limpeza do banco e reaparece quando a
        API cai.
        """
        LocalRecife.objects.create(
            slug='recife-sem-risco-rj', nome='Recife Sem Risco',
            estado='Rio de Janeiro', cidade='Arraial do Cabo',
        )

        output_dir = Path(__file__).resolve().parent / '_sync_test_sem_risco'
        output_dir.mkdir(exist_ok=True)
        try:
            frontend_out = output_dir / 'generated_sync.js'
            sync_project_code_from_db(
                backend_output_path=output_dir / 'generated_sync.py',
                frontend_output_path=frontend_out,
            )
            texto = frontend_out.read_text(encoding='utf-8')
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

        for campo in (
            'monitoramento_recente', 'risco_integrado', 'nivel_alerta',
            'risco_atual', 'possui_painel_risco',
        ):
            self.assertNotIn(campo, texto)


class AdminCodeSyncFlagTests(TestCase):
    """A sincronizacao respeita ENABLE_CODE_SYNC e so roda sob demanda.

    A exportacao deixou de acontecer em `save_related`/`delete_*` e virou a
    acao `sincronizar_codigo`. Como agora e o usuario que dispara, a acao
    avisa quando a flag esta desligada em vez de falhar em silencio - com os
    hooks automaticos o silencio era correto, com uma acao explicita nao e.
    """

    def setUp(self):
        self.admin = LocalRecifeAdmin(LocalRecife, AdminSite())

    @override_settings(ENABLE_CODE_SYNC=False)
    @patch('aquaculture.admin.sync_project_code_from_db')
    def test_sync_is_skipped_when_flag_is_disabled(self, sync_mock):
        with patch.object(self.admin, 'message_user') as message_user_mock:
            self.admin.sincronizar_codigo(object(), LocalRecife.objects.none())

        sync_mock.assert_not_called()
        message_user_mock.assert_called_once()
        self.assertIn('desativada', message_user_mock.call_args.args[1].lower())

    @override_settings(ENABLE_CODE_SYNC=True)
    @patch('aquaculture.admin.sync_project_code_from_db')
    def test_sync_runs_when_flag_is_enabled(self, sync_mock):
        sync_mock.return_value = {
            'backend_changed': True,
            'frontend_changed': False,
        }

        with patch.object(self.admin, 'message_user') as message_user_mock:
            self.admin.sincronizar_codigo(object(), LocalRecife.objects.none())

        sync_mock.assert_called_once_with()
        message_user_mock.assert_called_once()

    @override_settings(ENABLE_CODE_SYNC=True)
    @patch('aquaculture.admin.sync_project_code_from_db')
    def test_nao_existem_mais_hooks_automaticos(self, sync_mock):
        """Mesmo com a flag ligada, salvar nao pode exportar sozinho."""
        for hook in ('save_related', 'delete_model', 'delete_queryset'):
            metodo = getattr(type(self.admin), hook)
            self.assertIs(
                metodo,
                getattr(admin.ModelAdmin, hook),
                f'{hook} foi sobrescrito - risco de reintroduzir a escrita automatica',
            )
        sync_mock.assert_not_called()


class InventarioDatasetsTests(TestCase):
    """O catalogo publico so pode conter dados que existem de fato.

    Contexto: a migration 0014 semeava 8 datasets inventados - dois atribuidos
    ao NCBI, do qual o projeto nao tem nenhum dado - e o commit 34879bf passou
    a servi-los por uma API real. A 0016 removeu o seed e o catalogo agora e
    construido a partir dos arquivos reais. Ver docs/FONTES.md secao 6.14.
    """

    IDS_FICTICIOS = [
        'copernicus_sst_abrolhos_2026_03',
        'noaa_dhw_abrolhos_2026_03',
        'inventario_biodiversidade_abrolhos_2026_q1',
        'microbioma_picaozinho_2026_03',
        'genetico_abrolhos_2026_q1',
        'imagem_porto_2026_04',
        'relatorio_picaozinho_2026_04',
        'modelo_branqueamento_nordeste_2026_q2',
    ]

    def test_seed_ficticio_nao_sobrevive_as_migrations(self):
        encontrados = list(
            DatasetCatalogo.objects.filter(id__in=self.IDS_FICTICIOS).values_list(
                'id', flat=True
            )
        )

        self.assertEqual(encontrados, [], f'Datasets ficticios ainda no banco: {encontrados}')

    def test_nenhuma_fonte_declarada_e_o_ncbi(self):
        """O projeto nao possui nenhum dado do NCBI."""
        fontes = set(DatasetCatalogo.objects.values_list('fonte', flat=True))

        self.assertNotIn('NCBI', fontes)

    @contextmanager
    def _dados_no_disco(self):
        """Uma pasta `dados/` com um CSV minimo para cada dataset catalogado.

        🚨 **Ate 30/07/2026 estes testes liam a pasta `backend/dados/` de
        verdade**, e por isso so passavam em maquina que ja tinha rodado a
        ingestao. Os CSVs sao 78 MB e nao sao versionados — entao o CI, que
        parte de um clone limpo, falhava desde a primeira execucao, e um clone
        novo tambem falharia.

        O que se quer medir aqui e o comportamento: o inventario le tamanho e
        periodo **do disco** em vez de repetir numero gravado. Isso um arquivo
        de tres linhas verifica igual — e verifica em qualquer maquina.

        O caso oposto (pasta vazia) continua coberto por
        `test_arquivo_ausente_vira_registro_desativado_e_nao_dado_inventado`.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            pasta = base / 'dados'
            pasta.mkdir()
            # A coluna `time` e a unica que `ler_metadados_arquivo` procura. O
            # recheio existe so para o arquivo passar de 5 KB: `tamanho_mb` e
            # arredondado em duas casas, e tres linhas dariam 0,0 MB — que
            # falharia a assercao de tamanho por ser pequeno, e nao por estar
            # errado.
            conteudo = (
                'time,valor\n'
                '2020-01-01T12:00:00Z,1.0\n'
                + '2021-06-01T12:00:00Z,1.5\n' * 300
                + '2026-07-24T12:00:00Z,2.0\n'
            )
            for fonte in DATASETS_REAIS:
                (pasta / fonte.arquivo).write_text(conteudo, encoding='utf-8')
            with override_settings(BASE_DIR=base):
                yield pasta

    def test_inventario_le_tamanho_e_periodo_do_arquivo(self):
        with self._dados_no_disco():
            registros, ausentes = construir_inventario()

        self.assertEqual(ausentes, [], 'Arquivos de dados esperados nao encontrados')
        for registro in registros:
            with self.subTest(dataset=registro['id']):
                d = registro['defaults']
                self.assertTrue(d['ativo'])
                self.assertGreater(d['tamanho_mb'], 0)
                self.assertIsNotNone(d['data_inicio'])
                self.assertIsNotNone(d['data_fim'])
                self.assertLessEqual(d['data_inicio'], d['data_fim'])

    def test_o_periodo_vem_do_conteudo_e_nao_de_valor_gravado(self):
        """O ponto do teste acima, isolado: as datas saem do arquivo.

        Sem isto, trocar a leitura do disco por uma constante passaria — e foi
        exatamente esse o defeito que o catalogo ja teve (cobertura gravada
        envelhecendo em silencio, PLANEJAMENTO 27/07).
        """
        with self._dados_no_disco():
            registros, _ = construir_inventario()

        primeiro = registros[0]['defaults']
        self.assertEqual(primeiro['data_inicio'], date(2020, 1, 1))
        self.assertEqual(primeiro['data_fim'], date(2026, 7, 24))

    def test_nenhum_registro_promete_download_inexistente(self):
        registros, _ = construir_inventario()

        for registro in registros:
            with self.subTest(dataset=registro['id']):
                self.assertEqual(
                    registro['defaults']['url_download'],
                    '',
                    'O projeto nao serve esses arquivos - nao pode oferecer download',
                )

    def test_arquivo_ausente_vira_registro_desativado_e_nao_dado_inventado(self):
        with tempfile.TemporaryDirectory() as tmp:
            vazio = Path(tmp)
            (vazio / 'dados').mkdir()
            with override_settings(BASE_DIR=vazio):
                registros, ausentes = construir_inventario()

        self.assertEqual(len(ausentes), len(DATASETS_REAIS))
        for registro in registros:
            with self.subTest(dataset=registro['id']):
                d = registro['defaults']
                self.assertFalse(d['ativo'])
                self.assertIsNone(d['tamanho_mb'])
                self.assertIsNone(d['data_inicio'])
                self.assertIn('AUSENTE', d['resumo'])

    def test_arquivos_com_problema_de_integridade_ficam_fora(self):
        """Arquivos que existem no disco mas nao sao publicaveis."""
        inventariados = {f.arquivo for f in DATASETS_REAIS}

        for arquivo, motivo in EXCLUIDOS.items():
            with self.subTest(arquivo=arquivo):
                self.assertNotIn(arquivo, inventariados)
                self.assertTrue(motivo, 'Toda exclusao precisa de um motivo registrado')

        # ph.csv contem alcalinidade; o pH real vem de outro arquivo.
        self.assertIn('ph.csv', EXCLUIDOS)
        ph = next(f for f in DATASETS_REAIS if f.id == 'cmems_ph_abrolhos')
        self.assertNotEqual(ph.arquivo, 'ph.csv')
        self.assertEqual(ph.variavel, 'ph')

    def test_comando_popula_o_catalogo_a_partir_dos_arquivos(self):
        DatasetCatalogo.objects.all().delete()
        saida = StringIO()

        with self._dados_no_disco():
            call_command('inventariar_datasets', stdout=saida)

        self.assertEqual(DatasetCatalogo.objects.count(), len(DATASETS_REAIS))
        self.assertTrue(DatasetCatalogo.objects.filter(ativo=True).exists())
        self.assertIn('Catalogo atualizado', saida.getvalue())

    def test_sem_arquivo_nenhum_o_comando_roda_e_nao_ativa_nada(self):
        """O estado de um clone novo: catalogo montado, tudo desativado.

        Nao e erro — e o que a pagina "Banco de Dados" deve mostrar antes de a
        ingestao rodar. O que seria erro e o comando quebrar, ou marcar como
        disponivel um arquivo que ninguem tem.
        """
        DatasetCatalogo.objects.all().delete()

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'dados').mkdir()
            with override_settings(BASE_DIR=base):
                call_command('inventariar_datasets', stdout=StringIO())

        self.assertEqual(DatasetCatalogo.objects.count(), len(DATASETS_REAIS))
        self.assertFalse(DatasetCatalogo.objects.filter(ativo=True).exists())

    def test_comando_remove_registros_ficticios_remanescentes(self):
        DatasetCatalogo.objects.create(
            id='dataset_inventado_qualquer',
            titulo='Dataset que nao existe',
            fonte='NCBI',
            tipo_dado='Genetico',
        )

        call_command('inventariar_datasets', stdout=StringIO())

        self.assertFalse(
            DatasetCatalogo.objects.filter(id='dataset_inventado_qualquer').exists()
        )


class GuardaDeMigrationsTests(TestCase):
    """Comandos precisam avisar sobre banco desatualizado, nao estourar SQL cru.

    Regressao: rodar `ingerir` numa maquina que puxou codigo novo sem migrar
    produzia `OperationalError: no such column: aquaculture_localrecife.latitude`
    com dezenas de linhas de traceback. O banco e local e nao vem no
    repositorio, entao isso acontece em toda maquina nova.
    """

    def test_banco_em_dia_nao_bloqueia(self):
        self.assertEqual(migrations_pendentes(), [])
        exigir_migrations_aplicadas()  # nao deve levantar

    def test_migrations_pendentes_viram_erro_acionavel(self):
        pendentes = ['aquaculture.0013_alguma', 'aquaculture.0014_outra']

        with patch(
            'aquaculture.management.utils.migrations_pendentes',
            return_value=pendentes,
        ):
            with self.assertRaises(CommandError) as ctx:
                exigir_migrations_aplicadas()

        mensagem = str(ctx.exception)
        self.assertIn('2 migration(s) pendente(s)', mensagem)
        self.assertIn('manage.py migrate', mensagem)
        self.assertIn('aquaculture.0013_alguma', mensagem)

    def test_lista_longa_de_pendentes_e_resumida(self):
        pendentes = [f'app.{i:04d}_migration' for i in range(37)]

        with patch(
            'aquaculture.management.utils.migrations_pendentes',
            return_value=pendentes,
        ):
            with self.assertRaises(CommandError) as ctx:
                exigir_migrations_aplicadas()

        mensagem = str(ctx.exception)
        self.assertIn('37 migration(s)', mensagem)
        self.assertIn('e mais 32', mensagem)

    def test_comandos_de_dados_usam_a_guarda(self):
        for comando in ('ingerir', 'inventariar_datasets'):
            with self.subTest(comando=comando):
                with patch(
                    'aquaculture.management.utils.migrations_pendentes',
                    return_value=['aquaculture.9999_falsa'],
                ):
                    with self.assertRaises(CommandError) as ctx:
                        call_command(comando, stdout=StringIO())

                self.assertIn('migrate', str(ctx.exception))


class CredenciaisCopernicusTests(TestCase):
    """De onde o `testar_fontes` diz que as credenciais vem.

    O caminho recomendado e `copernicusmarine login`, que grava fora do
    projeto. Checar so o .env faria o diagnostico dizer "sem credenciais" a
    quem seguiu a recomendacao - empurrando de volta para guardar senha dentro
    do repositorio.
    """

    def _com_arquivo(self, existe):
        arquivo = Path(tempfile.gettempdir()) / '.copernicusmarine-credentials-teste'
        if existe:
            arquivo.touch()
        elif arquivo.exists():
            arquivo.unlink()
        return patch(
            'aquaculture.management.commands.testar_fontes.'
            'ARQUIVO_CREDENCIAIS_COPERNICUS',
            arquivo,
        )

    @override_settings(COPERNICUSMARINE_SERVICE_USERNAME='alguem@exemplo.org')
    def test_variavel_no_env_e_reconhecida(self):
        with self._com_arquivo(existe=False):
            self.assertIn('.env', _origem_das_credenciais())

    @override_settings(COPERNICUSMARINE_SERVICE_USERNAME='')
    def test_arquivo_do_login_e_reconhecido(self):
        with self._com_arquivo(existe=True):
            origem = _origem_das_credenciais()

        self.assertIsNotNone(origem, 'quem rodou "copernicusmarine login" tem credencial')
        self.assertIn('copernicusmarine-credentials', origem)

    @override_settings(COPERNICUSMARINE_SERVICE_USERNAME='')
    def test_sem_nenhum_dos_dois_devolve_none(self):
        with self._com_arquivo(existe=False):
            self.assertIsNone(_origem_das_credenciais())

    @override_settings(COPERNICUSMARINE_SERVICE_USERNAME='alguem@exemplo.org')
    def test_nenhuma_credencial_e_lida_ou_exposta(self):
        """O diagnostico diz a origem, nunca o valor."""
        with self._com_arquivo(existe=False):
            origem = _origem_das_credenciais()

        self.assertNotIn('alguem@exemplo.org', origem)
