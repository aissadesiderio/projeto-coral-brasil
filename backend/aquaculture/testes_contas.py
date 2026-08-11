"""Conta, aprovacao e a fronteira entre "consegue logar" e "pode contribuir".

🚨 O que estes testes protegem: que `aprovado_para_contribuir` nunca vire
heuristica frouxa (por exemplo, `is_active`), e que a barreira exista de
verdade na API - nao so escondida atras de um botao na tela.
"""

from django.contrib.auth.models import AnonymousUser, User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import PerfilUsuario, aprovado_para_contribuir

SENHA_FORTE = 'uma-senha-bem-forte-2026'


class SinalCriaPerfilTests(TestCase):
    def test_todo_usuario_novo_ganha_perfil_nao_aprovado(self):
        usuario = User.objects.create_user(username='novo', password=SENHA_FORTE)

        self.assertTrue(PerfilUsuario.objects.filter(usuario=usuario).exists())
        self.assertFalse(usuario.perfil.aprovado)

    def test_superusuario_tambem_ganha_perfil(self):
        """⚠️ O perfil existe, mas `aprovado_para_contribuir` nao depende dele
        para master — ver `AprovadoParaContribuirTests`."""
        master = User.objects.create_superuser(
            username='master', email='m@example.com', password=SENHA_FORTE,
        )

        self.assertTrue(PerfilUsuario.objects.filter(usuario=master).exists())


class AprovadoParaContribuirTests(TestCase):
    def test_anonimo_nunca_pode(self):
        self.assertFalse(aprovado_para_contribuir(AnonymousUser()))

    def test_none_nunca_pode(self):
        self.assertFalse(aprovado_para_contribuir(None))

    def test_autenticado_sem_aprovacao_nao_pode(self):
        usuario = User.objects.create_user(username='pendente', password=SENHA_FORTE)
        self.assertFalse(aprovado_para_contribuir(usuario))

    def test_autenticado_aprovado_pode(self):
        usuario = User.objects.create_user(username='aprovado', password=SENHA_FORTE)
        usuario.perfil.aprovado = True
        usuario.perfil.save()

        self.assertTrue(aprovado_para_contribuir(usuario))

    def test_master_pode_mesmo_sem_marcar_aprovado(self):
        """🚨 Master nunca depende do proprio perfil estar aprovado."""
        master = User.objects.create_superuser(
            username='master', email='m@example.com', password=SENHA_FORTE,
        )

        self.assertFalse(master.perfil.aprovado)
        self.assertTrue(aprovado_para_contribuir(master))


@override_settings(OFFLINE_MODE=False)
class CadastroTests(TestCase):
    def test_cria_conta_nao_aprovada_e_ja_loga(self):
        resposta = self.client.post(reverse('auth_cadastro'), {
            'username': 'visitante',
            'email': 'v@example.com',
            'password': SENHA_FORTE,
        })

        self.assertEqual(resposta.status_code, 201)
        dados = resposta.json()
        self.assertEqual(dados['autenticado'], True)
        self.assertEqual(dados['aprovado'], False)
        self.assertEqual(dados['master'], False)
        self.assertTrue(User.objects.filter(username='visitante').exists())

    def test_nao_deixa_repetir_nome_de_usuario(self):
        User.objects.create_user(username='ja-existe', password=SENHA_FORTE)

        resposta = self.client.post(reverse('auth_cadastro'), {
            'username': 'ja-existe', 'password': SENHA_FORTE,
        })

        self.assertEqual(resposta.status_code, 400)

    def test_recusa_senha_fraca(self):
        resposta = self.client.post(reverse('auth_cadastro'), {
            'username': 'fraco', 'password': '123',
        })

        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(User.objects.filter(username='fraco').exists())

    def test_exige_usuario_e_senha(self):
        resposta = self.client.post(reverse('auth_cadastro'), {'username': 'sozinho'})

        self.assertEqual(resposta.status_code, 400)


@override_settings(OFFLINE_MODE=False)
class LoginELogoutTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='alguem', password=SENHA_FORTE)

    def test_login_com_credenciais_certas(self):
        resposta = self.client.post(reverse('auth_login'), {
            'username': 'alguem', 'password': SENHA_FORTE,
        })

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['autenticado'])

    def test_login_com_senha_errada(self):
        resposta = self.client.post(reverse('auth_login'), {
            'username': 'alguem', 'password': 'senha-errada',
        })

        self.assertEqual(resposta.status_code, 401)

    def test_logout_encerra_a_sessao(self):
        self.client.login(username='alguem', password=SENHA_FORTE)

        self.client.post(reverse('auth_logout'))

        self.assertFalse(self.client.get(reverse('auth_eu')).json()['autenticado'])


@override_settings(OFFLINE_MODE=False)
class EuViewTests(TestCase):
    def test_deslogado(self):
        dados = self.client.get(reverse('auth_eu')).json()

        self.assertEqual(
            dados,
            {'autenticado': False, 'username': None, 'master': False, 'aprovado': False},
        )

    def test_logado_nao_aprovado(self):
        User.objects.create_user(username='pendente', password=SENHA_FORTE)
        self.client.login(username='pendente', password=SENHA_FORTE)

        dados = self.client.get(reverse('auth_eu')).json()

        self.assertEqual(dados['autenticado'], True)
        self.assertEqual(dados['aprovado'], False)
        self.assertEqual(dados['master'], False)

    def test_logado_aprovado(self):
        usuario = User.objects.create_user(username='aprovado', password=SENHA_FORTE)
        usuario.perfil.aprovado = True
        usuario.perfil.save()
        self.client.login(username='aprovado', password=SENHA_FORTE)

        self.assertTrue(self.client.get(reverse('auth_eu')).json()['aprovado'])

    def test_master(self):
        User.objects.create_superuser(
            username='master', email='m@example.com', password=SENHA_FORTE,
        )
        self.client.login(username='master', password=SENHA_FORTE)

        dados = self.client.get(reverse('auth_eu')).json()

        self.assertTrue(dados['master'])
        self.assertTrue(dados['aprovado'])


@override_settings(OFFLINE_MODE=False)
class CsrfTests(TestCase):
    """🚨 So escrita **autenticada** exige o token — login e cadastro nao.

    `Client(enforce_csrf_checks=True)` e necessario porque o cliente de
    teste do Django, por padrao, desliga a checagem de CSRF inteira — o que
    esconderia exatamente o comportamento que este teste existe para provar.
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_cadastro_anonimo_nao_exige_csrf(self):
        resposta = self.client.post(reverse('auth_cadastro'), {
            'username': 'sem-csrf', 'password': SENHA_FORTE,
        })

        self.assertEqual(resposta.status_code, 201)

    def test_login_anonimo_nao_exige_csrf(self):
        User.objects.create_user(username='alguem', password=SENHA_FORTE)

        resposta = self.client.post(reverse('auth_login'), {
            'username': 'alguem', 'password': SENHA_FORTE,
        })

        self.assertEqual(resposta.status_code, 200)

    def test_escrita_autenticada_sem_token_falha(self):
        usuario = User.objects.create_user(username='aprovado', password=SENHA_FORTE)
        usuario.perfil.aprovado = True
        usuario.perfil.save()
        self.client.login(username='aprovado', password=SENHA_FORTE)

        resposta = self.client.post(reverse('especie_list'), {
            'nome_cientifico': 'Testus csrfus', 'tipo': 'CORAL',
        })

        self.assertEqual(resposta.status_code, 403)

    def test_escrita_autenticada_com_token_funciona(self):
        usuario = User.objects.create_user(username='aprovado', password=SENHA_FORTE)
        usuario.perfil.aprovado = True
        usuario.perfil.save()
        self.client.login(username='aprovado', password=SENHA_FORTE)
        self.client.get(reverse('auth_eu'))  # primer do cookie csrftoken
        token = self.client.cookies['csrftoken'].value

        resposta = self.client.post(
            reverse('especie_list'),
            {'nome_cientifico': 'Testus csrfus', 'tipo': 'CORAL'},
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(resposta.status_code, 202)
