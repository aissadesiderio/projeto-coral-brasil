from datetime import date
from io import StringIO
from pathlib import Path
import shutil
from unittest.mock import call, patch

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from db import setup_graph
from .admin import LocalRecifeAdmin
from .code_sync import sync_project_code_from_db
from .models import Especie, LocalRecife, StatusPredicao
from .neo4j_schema import (
    DJANGO_STATUS_PREDICAO_MODEL_SLUG,
    SCHEMA_QUERIES,
    build_especie_row,
    build_fonte_dados_seed_payload,
    build_localizacao_row,
    build_status_predicao_row,
)
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
        StatusPredicao.objects.update_or_create(
            local_recife=self.local,
            data=date(2026, 4, 16),
            defaults={
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
            },
        )

    def test_local_detail_returns_species_and_monitoring(self):
        response = self.client.get(reverse('local_recife_detail', kwargs={'slug': self.local.slug}))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['slug'], self.local.slug)
        nomes = [item['nome_cientifico'] for item in payload['especies']]
        self.assertIn('Mussismilia braziliensis', nomes)
        self.assertEqual(payload['monitoramento_recente']['nivel_alerta'], 'ALERTA_1')

    def test_especie_list_can_filter_by_local(self):
        response = self.client.get(f"{reverse('especie_list')}?local={self.local.slug}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        nomes = [item['nome_cientifico'] for item in payload]
        self.assertIn('Mussismilia braziliensis', nomes)


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
                    'status_conservacao': 'Vulneravel',
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


class Neo4jSchemaBuilderTests(TestCase):
    def setUp(self):
        self.local = LocalRecife.objects.create(
            slug='schema-recife-ba',
            nome='Recife de Schema',
            estado='Bahia',
            cidade='Caravelas',
            descricao='Local de teste para schema Neo4j.',
            ultima_atualizacao=date(2026, 4, 16),
        )
        self.especie = Especie.objects.create(
            nome_cientifico='Mussismilia schemaensis',
            nome_comum='Coral de schema',
            tipo='CORAL',
            descricao='Especie de teste.',
            status_conservacao='Vulneravel',
            credito_imagem='Equipe local',
            fonte_imagem_url='https://exemplo.org/imagem',
            fonte_url='https://exemplo.org/especie',
        )
        self.predicao = StatusPredicao.objects.create(
            local_recife=self.local,
            data=date(2026, 4, 16),
            sst_atual=29.1,
            limite_termico=27.0,
            anomalia=2.1,
            dhw_calculado=6.4,
            vento_velocidade=5.2,
            irradiancia=32.5,
            turbidez=0.18,
            salinidade=36.0,
            ph=8.1,
            oxigenio=6.5,
            nitrato=0.4,
            clorofila=0.7,
            risco_integrado=78.0,
            nivel_alerta='ALERTA_1',
        )

    def test_build_localizacao_and_especie_rows_use_canonical_ids(self):
        local_row = build_localizacao_row(self.local)
        especie_row = build_especie_row(self.local, self.especie)

        self.assertEqual(local_row['id'], 'schema-recife-ba')
        self.assertEqual(local_row['props']['slug'], 'schema-recife-ba')
        self.assertEqual(especie_row['id'], 'mussismilia-schemaensis')
        self.assertEqual(especie_row['localizacao_id'], 'schema-recife-ba')
        self.assertEqual(especie_row['props']['nome_cientifico'], 'Mussismilia schemaensis')

    def test_build_status_predicao_row_splits_measurement_and_prediction_nodes(self):
        row = build_status_predicao_row(self.predicao)

        self.assertEqual(row['localizacao_id'], 'schema-recife-ba')
        self.assertEqual(row['medicao']['id'], 'schema-recife-ba:2026-04-16')
        self.assertEqual(
            row['predicao']['id'],
            f'schema-recife-ba:2026-04-16:{DJANGO_STATUS_PREDICAO_MODEL_SLUG}',
        )
        self.assertEqual(row['medicao']['props']['sst'], 29.1)
        self.assertEqual(row['medicao']['props']['par'], 32.5)
        self.assertEqual(row['medicao']['props']['kd490'], 0.18)
        self.assertEqual(row['predicao']['props']['risco_integrado'], 78.0)
        self.assertEqual(row['predicao']['props']['nivel_alerta'], 'ALERTA_1')

    def test_build_fonte_dados_seed_payload_returns_current_transition_source(self):
        payload = build_fonte_dados_seed_payload()

        self.assertEqual(payload['id'], 'django-statuspredicao:v1')
        self.assertEqual(payload['props']['pipeline'], 'neo4j_seed')
        self.assertEqual(payload['props']['status'], 'ativo')


class Neo4jCommandWiringTests(TestCase):
    @patch('aquaculture.management.commands.neo4j_init.executar_queries_schema')
    @patch('aquaculture.management.commands.neo4j_init.verificar_conexao_neo4j')
    def test_neo4j_init_uses_canonical_schema_queries(self, verificar_mock, executar_mock):
        executar_mock.return_value = len(SCHEMA_QUERIES)

        call_command('neo4j_init', stdout=StringIO())

        verificar_mock.assert_called_once_with()
        executar_mock.assert_called_once_with(SCHEMA_QUERIES)

    @patch('db.setup_graph.call_command')
    def test_setup_graph_delegates_to_official_commands(self, call_command_mock):
        setup_graph.setup()

        call_command_mock.assert_has_calls([call('neo4j_init'), call('neo4j_seed')])


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
        StatusPredicao.objects.create(
            local_recife=local,
            data=date(2026, 4, 20),
            sst_atual=28.1,
            limite_termico=27.0,
            anomalia=1.1,
            dhw_calculado=2.8,
            irradiancia=27.0,
            turbidez=0.2,
            salinidade=35.5,
            ph=8.0,
            oxigenio=6.2,
            nitrato=0.3,
            clorofila=0.5,
            risco_integrado=49.0,
            nivel_alerta='OBSERVACAO',
        )

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


class AdminCodeSyncFlagTests(TestCase):
    def setUp(self):
        self.admin = LocalRecifeAdmin(LocalRecife, AdminSite())

    @override_settings(ENABLE_CODE_SYNC=False)
    @patch('aquaculture.admin.sync_project_code_from_db')
    def test_sync_is_skipped_when_flag_is_disabled(self, sync_mock):
        with patch.object(self.admin, 'message_user') as message_user_mock:
            self.admin._sync_code(request=object())

        sync_mock.assert_not_called()
        message_user_mock.assert_not_called()

    @override_settings(ENABLE_CODE_SYNC=True)
    @patch('aquaculture.admin.sync_project_code_from_db')
    def test_sync_runs_when_flag_is_enabled(self, sync_mock):
        sync_mock.return_value = {
            'backend_changed': True,
            'frontend_changed': False,
        }

        with patch.object(self.admin, 'message_user') as message_user_mock:
            self.admin._sync_code(request=object())

        sync_mock.assert_called_once_with()
        message_user_mock.assert_called_once()
