"""Testes da leitura do `.env` e da composicao dos bancos locais.

Os dois defeitos cobertos aqui tem a mesma forma, e e por isso que estao no
mesmo arquivo: **uma configuracao invalida que o sistema aceita em silencio, e
que reaparece depois como um erro apontando para o lugar errado.**

1. Espaco em branco no fim de um valor do `.env`. O `django-environ` nao apara,
   e `DATABASE_URL=.../coral_brasil<espaco>` vira o banco `"coral_brasil "` —
   cuja mensagem de erro (`database ... does not exist`) manda conferir o
   Docker, que esta certo.
2. `NEO4J_USER` diferente de `neo4j` no `docker-compose.yml`. O Neo4j so aceita
   esse nome para o administrador inicial; qualquer outro derruba o container
   num laco de reinicio cuja causa aparece so no log.
"""

import os
import re
from pathlib import Path

import yaml
from django.test import SimpleTestCase

from coral_site import settings

RAIZ = Path(settings.BASE_DIR).parent


class AparaEspacoDoEnvTests(SimpleTestCase):
    """🚨 Verificado em 29/07/2026, num `.env` montado por copiar-e-colar."""

    def setUp(self):
        self.arquivo = Path(self.enterContext(_pasta_temporaria())) / '.env'
        self.chaves = []

    def tearDown(self):
        for chave in self.chaves:
            os.environ.pop(chave, None)

    def _preparar(self, linhas, ambiente):
        self.arquivo.write_text('\n'.join(linhas), encoding='utf-8')
        for chave, valor in ambiente.items():
            os.environ[chave] = valor
            self.chaves.append(chave)
        return settings._aparar_valores_do_env(self.arquivo)

    def test_apara_o_espaco_no_fim(self):
        self._preparar(
            ['DATABASE_URL=postgres://x/coral_brasil'],
            {'DATABASE_URL': 'postgres://x/coral_brasil '},
        )

        self.assertEqual(os.environ['DATABASE_URL'], 'postgres://x/coral_brasil')

    def test_relata_quais_chaves_foram_aparadas(self):
        aparadas = self._preparar(
            ['NEO4J_PASSWORD=segredo', 'DJANGO_DEBUG=True'],
            {'NEO4J_PASSWORD': 'segredo  ', 'DJANGO_DEBUG': 'True'},
        )

        self.assertEqual(aparadas, ('NEO4J_PASSWORD',))

    def test_valor_sem_espaco_nao_e_tocado(self):
        aparadas = self._preparar(
            ['DATABASE_URL=postgres://x/coral_brasil'],
            {'DATABASE_URL': 'postgres://x/coral_brasil'},
        )

        self.assertEqual(aparadas, ())

    def test_nao_mexe_em_variavel_que_o_env_nao_declara(self):
        """⚠️ Varrer `os.environ` inteiro alteraria variaveis do sistema."""
        self._preparar(
            ['DJANGO_DEBUG=True'],
            {'DJANGO_DEBUG': 'True', 'PATH_DE_TESTE_CORAL': 'valor  '},
        )

        self.assertEqual(os.environ['PATH_DE_TESTE_CORAL'], 'valor  ')

    def test_comentario_e_linha_vazia_nao_quebram(self):
        aparadas = self._preparar(
            ['# comentario', '', 'DJANGO_DEBUG=True'],
            {'DJANGO_DEBUG': 'True '},
        )

        self.assertEqual(aparadas, ('DJANGO_DEBUG',))

    def test_arquivo_ausente_devolve_vazio(self):
        self.assertEqual(
            settings._aparar_valores_do_env(self.arquivo.parent / 'nao-existe'),
            (),
        )


class UsuarioDoNeo4jNoComposeTests(SimpleTestCase):
    """🚨 Derrubou o Neo4j num laco de reinicio em 30/07/2026.

    O `NEO4J_AUTH` do compose precisa fixar `neo4j` como usuario. Deixa-lo sair
    de `${NEO4J_USER}` oferece um botao que o Neo4j nao aceita: com qualquer
    outro valor o entrypoint sai com codigo 1 antes de o banco existir, o
    Docker reinicia para sempre, e `docker compose ps` mostra so
    `Restarting (1)` com a coluna PORTS vazia.
    """

    def setUp(self):
        self.compose = yaml.safe_load(
            (RAIZ / 'docker-compose.yml').read_text(encoding='utf-8')
        )

    def test_o_usuario_administrador_e_literal(self):
        auth = self.compose['services']['neo4j']['environment']['NEO4J_AUTH']

        self.assertTrue(
            auth.startswith('neo4j/'),
            f'NEO4J_AUTH comeca com "{auth.split("/")[0]}". O Neo4j so aceita '
            f'"neo4j" como administrador inicial, e qualquer outro valor '
            f'derruba o container em laco.',
        )

    def test_o_usuario_nao_vem_de_variavel(self):
        auth = self.compose['services']['neo4j']['environment']['NEO4J_AUTH']
        usuario = auth.split('/')[0]

        self.assertNotIn(
            '$', usuario,
            'O usuario do NEO4J_AUTH nao pode vir de variavel: um NEO4J_USER '
            'sobrando no ambiente da maquina reintroduziria a falha.',
        )

    def test_a_senha_continua_configuravel(self):
        """A senha *deve* sair de variavel — e a unica parte que varia."""
        auth = self.compose['services']['neo4j']['environment']['NEO4J_AUTH']

        self.assertIn('${NEO4J_PASSWORD', auth)

    def test_a_senha_padrao_tem_o_minimo_que_o_neo4j_exige(self):
        """Menos de 8 caracteres e a outra causa do mesmo laco de reinicio."""
        auth = self.compose['services']['neo4j']['environment']['NEO4J_AUTH']
        padrao = re.search(r'\$\{NEO4J_PASSWORD:-([^}]+)\}', auth)

        self.assertIsNotNone(padrao, 'NEO4J_PASSWORD precisa ter valor padrao.')
        self.assertGreaterEqual(len(padrao.group(1)), 8)


def _pasta_temporaria():
    import tempfile

    return tempfile.TemporaryDirectory()
