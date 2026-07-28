"""Testes da sequencia de reconstrucao do deploy.

O que protegem, em ordem de gravidade:

1. 🚨 **Falha interrompe.** Um deploy que segue depois de um passo quebrado
   entrega um site meio construido — pior que um que nao sobe, porque parece
   ter funcionado.
2. **Passo obrigatorio nao pode ser pulado.** Pular o `migrate` faria a falha
   aparecer tres passos adiante, com mensagem que nao aponta para a causa.
3. **A ordem e a declarada.** `treinar_final` le o banco; rodar antes do
   `migrate` falharia por motivo errado.
4. 🚨 **A saida cabe no console.** Tres comandos quebraram em producao por
   emoji no `stdout` — o console do Windows usa cp1252. Nao e cosmetica: o
   comando morre no meio, e o deploy para por um caractere.
"""

from django.test import SimpleTestCase

from db import deploy


class SequenciaTests(SimpleTestCase):
    def passos(self):
        return (
            deploy.Passo('um', 'comando_um', 'motivo um'),
            deploy.Passo('dois', 'comando_dois', 'motivo dois'),
            deploy.Passo('tres', 'comando_tres', 'motivo tres', dispensavel=True),
        )

    def executar(self, falhar_em=None, **extras):
        chamados = []

        def falso(comando, *args, **opcoes):
            chamados.append(comando)
            if comando == falhar_em:
                raise RuntimeError('quebrou de proposito')

        import django.core.management as gerencia

        original = gerencia.call_command
        gerencia.call_command = falso
        try:
            resultado = deploy.executar(self.passos(), **extras)
        finally:
            gerencia.call_command = original
        return resultado, chamados

    def test_roda_todos_na_ordem_declarada(self):
        resultado, chamados = self.executar()

        self.assertTrue(resultado.ok)
        self.assertEqual(chamados, ['comando_um', 'comando_dois', 'comando_tres'])

    def test_falha_interrompe_o_restante(self):
        """🚨 Site meio construido parece ter funcionado."""
        resultado, chamados = self.executar(falhar_em='comando_dois')

        self.assertFalse(resultado.ok)
        self.assertEqual(chamados, ['comando_um', 'comando_dois'])
        self.assertNotIn('comando_tres', chamados)

    def test_a_falha_diz_qual_passo_e_por_que_ele_existe(self):
        resultado, _ = self.executar(falhar_em='comando_dois')

        self.assertEqual(resultado.falhou.passo.nome, 'dois')
        self.assertEqual(resultado.falhou.passo.motivo, 'motivo dois')

    def test_passo_dispensavel_pode_ser_pulado(self):
        resultado, chamados = self.executar(pular=['tres'])

        self.assertTrue(resultado.ok)
        self.assertNotIn('comando_tres', chamados)
        self.assertEqual([p.nome for p in resultado.pulados], ['tres'])

    def test_passo_obrigatorio_nao_pode_ser_pulado(self):
        """Pular faria a falha aparecer longe da causa."""
        with self.assertRaises(ValueError) as ctx:
            self.executar(pular=['um'])

        self.assertIn('obrigatorios', str(ctx.exception))

    def test_o_progresso_e_reportado_passo_a_passo(self):
        eventos = []
        self.executar(ao_progredir=lambda p, e: eventos.append((p.nome, e)))

        self.assertIn(('um', 'iniciando'), eventos)
        self.assertIn(('um', 'ok'), eventos)

    def test_o_progresso_avisa_a_falha(self):
        eventos = []
        self.executar(
            falhar_em='comando_dois',
            ao_progredir=lambda p, e: eventos.append((p.nome, e)),
        )

        self.assertIn(('dois', 'falhou'), eventos)


class PassosDeclaradosTests(SimpleTestCase):
    """A sequencia real, e nao uma inventada para o teste."""

    def nomes(self):
        return [p.nome for p in deploy.PASSOS]

    def test_o_schema_vem_primeiro(self):
        """Sem ele, nenhum passo seguinte tem onde ler."""
        self.assertEqual(self.nomes()[0], 'schema')

    def test_a_conferencia_vem_por_ultimo(self):
        """Ela valida o resultado; validar antes nao mediria nada."""
        self.assertEqual(self.nomes()[-1], 'conferencia')

    def test_o_modelo_vem_depois_do_schema(self):
        nomes = self.nomes()

        self.assertLess(nomes.index('schema'), nomes.index('modelo'))

    def test_os_tres_artefatos_derivados_estao_na_sequencia(self):
        """🚨 O motivo de o comando existir.

        Cada um destes ganhou, quando foi criado, um aviso dizendo "o deploy
        precisa rodar isto". Tres avisos corretos em tres lugares somam zero
        garantia — e era esse o estado ate 28/07/2026.
        """
        for nome in ('modelo', 'grafo', 'documentacao'):
            self.assertIn(nome, self.nomes())

    def test_todo_passo_declara_por_que_existe(self):
        for passo in deploy.PASSOS:
            self.assertGreater(
                len(passo.motivo.strip()), 30, f'{passo.nome} sem motivo real'
            )

    def test_schema_e_conferencia_nao_sao_dispensaveis(self):
        obrigatorios = {p.nome for p in deploy.PASSOS if not p.dispensavel}

        self.assertIn('schema', obrigatorios)
        self.assertIn('conferencia', obrigatorios)
        self.assertIn('modelo', obrigatorios)


class SaidaNoConsoleTests(SimpleTestCase):
    """🚨 A guarda contra o defeito que quebrou o deploy tres vezes hoje.

    O console do Windows usa **cp1252**. Um emoji no `stdout.write` de um
    comando levanta `UnicodeEncodeError` e mata o processo no meio — e o
    sintoma nao lembra a causa: o comando aparece como "falhou" depois de ter
    feito todo o trabalho.

    Aconteceu com `treinar_final` (⚠️), `neo4j_projetar` (✅) e `calibrar`
    (🚨), sempre so ao rodar de verdade, porque a suite de testes captura a
    saida num buffer UTF-8 e nunca toca no console.

    ⚠️ A regra vale so para o que **e impresso**. Docstrings e comentarios
    continuam com emoji: sao lidos em arquivo, e ali o emoji ajuda.
    """

    CODIFICACAO = 'cp1252'

    def strings_de_saida(self):
        """Toda constante de texto de um comando que nao seja docstring."""
        import ast
        import pathlib

        raiz = pathlib.Path(__file__).resolve().parents[1]
        pasta = raiz / 'aquaculture' / 'management' / 'commands'

        for arquivo in sorted(pasta.glob('*.py')):
            arvore = ast.parse(arquivo.read_text(encoding='utf-8'))
            docstrings = {
                id(no.body[0].value)
                for no in ast.walk(arvore)
                if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef))
                and no.body and isinstance(no.body[0], ast.Expr)
                and isinstance(no.body[0].value, ast.Constant)
            }
            for no in ast.walk(arvore):
                if (isinstance(no, ast.Constant)
                        and isinstance(no.value, str)
                        and id(no) not in docstrings):
                    yield arquivo.name, no.lineno, no.value

    def test_nenhum_comando_imprime_o_que_o_console_nao_aceita(self):
        problemas = []
        for arquivo, linha, texto in self.strings_de_saida():
            try:
                texto.encode(self.CODIFICACAO)
            except UnicodeEncodeError as erro:
                trecho = texto[erro.start:erro.end]
                problemas.append(
                    f'{arquivo}:{linha} contem {trecho!a} '
                    f'(U+{ord(trecho[0]):04X})'
                )

        self.assertEqual(
            problemas, [],
            'Strings que o console cp1252 nao imprime — o comando morre no '
            'meio ao rodar de verdade:\n  ' + '\n  '.join(problemas),
        )
