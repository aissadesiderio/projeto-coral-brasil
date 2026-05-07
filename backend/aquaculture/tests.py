from datetime import date
from pathlib import Path
import shutil
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin import LocalRecifeAdmin
from .code_sync import sync_project_code_from_db
from .models import Especie, LocalRecife, StatusPredicao


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
