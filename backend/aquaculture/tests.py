from datetime import date
from pathlib import Path
import re
import shutil

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .code_sync import (
    BACKEND_SYNC_PATH,
    FRONTEND_SYNC_PATH,
    sync_project_code_from_db,
)
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
            reverse('monitoramento_list'),
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
