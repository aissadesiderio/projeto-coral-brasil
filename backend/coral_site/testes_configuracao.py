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


class TodoTesteEDescobertoTests(SimpleTestCase):
    """🚨 Um arquivo de teste com o nome errado nunca roda, e nao reclama.

    O `manage.py test` usa o discovery do unittest, cujo padrao e `test*.py`.
    Um arquivo cheio de `TestCase` chamado `verificacoes_x.py` simplesmente
    nao e encontrado: a suite passa, o numero total sobe zero, e nada na saida
    diz que faltou alguem. E o mesmo formato de falha silenciosa que ja custou
    caro tres vezes aqui — inclusive o `NO TESTS RAN` de 29/07, em que a suite
    inteira ficou invisivel e **saiu com sucesso**.

    Este teste percorre o codigo com AST — sem importar nada — e exige que todo
    arquivo que defina um `TestCase` tenha nome descobrivel.

    ⚠️ A direcao contraria nao e verificada de proposito: `testar_fontes.py`
    casa com `test*.py` sem conter teste nenhum, e isso e inofensivo. O
    discovery importa o modulo, nao encontra `TestCase` e segue.
    """

    PADRAO_DO_DISCOVERY = 'test*.py'
    BASES_DE_TESTE = ('TestCase', 'SimpleTestCase', 'TransactionTestCase')

    def _define_teste(self, caminho):
        import ast

        try:
            arvore = ast.parse(caminho.read_text(encoding='utf-8'))
        except SyntaxError:  # pragma: no cover - arquivo quebrado ja falha antes
            return False

        for no in ast.walk(arvore):
            if not isinstance(no, ast.ClassDef):
                continue
            for base in no.bases:
                nome = base.attr if isinstance(base, ast.Attribute) else getattr(base, 'id', '')
                if nome.endswith(self.BASES_DE_TESTE):
                    return True
        return False

    def test_todo_arquivo_com_testcase_tem_nome_descobrivel(self):
        import fnmatch

        raiz = Path(settings.BASE_DIR)
        escondidos = []

        for caminho in sorted(raiz.rglob('*.py')):
            if '__pycache__' in caminho.parts or 'migrations' in caminho.parts:
                continue
            if fnmatch.fnmatch(caminho.name, self.PADRAO_DO_DISCOVERY):
                continue
            if self._define_teste(caminho):
                escondidos.append(str(caminho.relative_to(raiz)))

        self.assertEqual(
            escondidos, [],
            f'Estes arquivos definem TestCase e NAO casam com '
            f'"{self.PADRAO_DO_DISCOVERY}", entao o "manage.py test" nunca os '
            f'roda — e nao avisa: {escondidos}',
        )

    def test_o_proprio_guarda_pegaria_um_arquivo_mal_nomeado(self):
        """Um teste que nunca falha nao protege nada. Este confere a si mesmo."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            impostor = Path(tmp) / 'verificacoes_do_recife.py'
            impostor.write_text(
                'from django.test import TestCase\n'
                'class Alguma(TestCase):\n    pass\n',
                encoding='utf-8',
            )

            self.assertTrue(self._define_teste(impostor))

    def test_arquivo_sem_testcase_nao_e_acusado(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            comum = Path(tmp) / 'modulo.py'
            comum.write_text('class Coisa:\n    pass\n', encoding='utf-8')

            self.assertFalse(self._define_teste(comum))


class SemConfiguracaoDePytestTests(SimpleTestCase):
    """⚠️ A seção `[tool.pytest.ini_options]` foi removida em 30/07/2026.

    Ela declarava `python_files = ["test_*.py", "tests.py"]`, que não casa com
    os `testes_*.py` deste projeto — 20 dos 24 arquivos ficavam invisíveis. E
    nem corrigindo o padrão funcionaria: `pytest` e `pytest-django` não são
    dependências. Uma IDE que detectasse a seção ligaria o pytest sozinha e
    exibiria "4 testes" num projeto com mais de 600.

    Este teste existe para que ela não volte por reflexo. Se alguém quiser
    pytest de verdade, o caminho é declarar as duas dependências primeiro — e
    aí este teste é o lugar certo para registrar essa decisão.
    """

    @staticmethod
    def _sem_comentarios(caminho):
        """O TOML sem as linhas de comentário.

        ⚠️ Necessário, e a primeira versão deste teste falhou por não ter:
        o comentário que explica a remoção da seção **cita a seção**, e uma
        busca por substring no arquivo inteiro encontra a citação. Ler texto
        sem respeitar a estrutura dele é o mesmo erro que a tabela de
        episódios trocada — só que aqui ele falha alto, em vez de calado.
        """
        texto = caminho.read_text(encoding='utf-8')
        return '\n'.join(
            linha for linha in texto.splitlines()
            if not linha.lstrip().startswith('#')
        )

    def test_pyproject_nao_declara_pytest_sem_a_dependencia(self):
        pyproject = self._sem_comentarios(RAIZ / 'pyproject.toml')
        requirements = (RAIZ / 'requirements.txt').read_text(encoding='utf-8')

        declara_pytest = '[tool.pytest.ini_options]' in pyproject
        instala_pytest = 'pytest' in requirements.lower()

        if declara_pytest and not instala_pytest:
            self.fail(
                'pyproject.toml configura o pytest, mas ele não está no '
                'requirements.txt. Configuração de uma ferramenta ausente não '
                'falha — ela faz uma IDE mostrar uma contagem parcial de '
                'testes, que se lê como baixa cobertura.'
            )

    def test_o_padrao_de_arquivo_do_pytest_cobriria_os_testes_daqui(self):
        """Se a seção voltar, que volte com o padrão certo.

        `test_*.py` exige o sublinhado logo após "test"; os arquivos daqui são
        `testes_*.py`, em português. O discovery do Django usa `test*.py`, sem
        sublinhado, e por isso enxerga os dois.
        """
        import fnmatch
        import re

        pyproject = self._sem_comentarios(RAIZ / 'pyproject.toml')
        casa = re.search(r'python_files\s*=\s*\[([^\]]*)\]', pyproject)
        if not casa:
            return  # sem seção de pytest: nada a conferir

        padroes = re.findall(r'"([^"]+)"', casa.group(1))
        exemplo = 'testes_predicao.py'

        self.assertTrue(
            any(fnmatch.fnmatch(exemplo, p) for p in padroes),
            f'Nenhum de {padroes} casa com "{exemplo}". Os arquivos de teste '
            f'deste projeto começam com "testes_", em português.',
        )


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


class DocumentacaoNaoMandaRodarComandoInexistenteTests(SimpleTestCase):
    """🚨 Um bloco de codigo num documento e uma instrucao para executar.

    O `README_neo4j.md` passou dias mandando rodar `manage.py neo4j_seed`,
    removido em 28/07/2026, e o `arquitetura.md` o listava como "comando
    oficial" — os dois descobertos so em 31/07, na varredura manual.

    ⚠️ **Isto e pior que documentacao ausente.** Quem segue um comando que nao
    existe recebe `Unknown command` e nao tem como saber se digitou errado, se
    esqueceu de ativar o venv, ou se o projeto esta quebrado. Documento em
    branco pelo menos manda a pessoa perguntar.

    A regra e deliberadamente estreita: **so blocos de codigo**. Prosa pode e
    deve citar comandos removidos — as tabelas de "o que saiu, e por que"
    existem justamente para isso, e sao o oposto do defeito.
    """

    BLOCO = re.compile(r'```(?:bash|powershell|sh|console)?\n(.*?)```', re.DOTALL)
    COMANDO = re.compile(r'manage\.py\s+([a-z_][a-z0-9_]*)')
    IGNORADAS = ('node_modules', 'venv', '.git', 'exportado', 'build')

    def documentos(self):
        for caminho in sorted(RAIZ.rglob('*.md')):
            if not any(p in caminho.parts for p in self.IGNORADAS):
                yield caminho

    def comandos_em_blocos(self, texto):
        for bloco in self.BLOCO.findall(texto):
            yield from self.COMANDO.findall(bloco)

    def test_todo_comando_citado_em_bloco_de_codigo_existe(self):
        from django.core.management import get_commands

        disponiveis = set(get_commands())
        self.assertIn('migrate', disponiveis, 'sanidade: o registro carregou')

        inexistentes = []
        for documento in self.documentos():
            texto = documento.read_text(encoding='utf-8')
            for nome in self.comandos_em_blocos(texto):
                if nome not in disponiveis:
                    inexistentes.append(
                        f'{documento.relative_to(RAIZ).as_posix()}: '
                        f'manage.py {nome}'
                    )

        self.assertEqual(
            inexistentes, [],
            'Documento manda rodar comando que nao existe. Corrija o bloco, '
            'ou mova a mencao para fora do bloco de codigo se ela for '
            'historica:\n  ' + '\n  '.join(inexistentes),
        )

    def test_o_proprio_guarda_pegaria_um_comando_removido(self):
        """Sem isto, um erro no regex viraria um teste que nunca falha."""
        from django.core.management import get_commands

        texto = '```bash\npython backend/manage.py neo4j_seed\n```'
        encontrados = list(self.comandos_em_blocos(texto))

        self.assertEqual(encontrados, ['neo4j_seed'])
        self.assertNotIn('neo4j_seed', get_commands())

    def test_mencao_em_prosa_nao_e_flagrada(self):
        """A tabela de "o que foi removido" e o oposto do defeito."""
        texto = 'O `manage.py neo4j_seed` foi removido em 28/07/2026.'

        self.assertEqual(list(self.comandos_em_blocos(texto)), [])


def _pasta_temporaria():
    import tempfile

    return tempfile.TemporaryDirectory()
