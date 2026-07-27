"""Testes do conversor Markdown -> docx.

O que protegem, em ordem de gravidade: que **nenhum texto se perca** na
conversao, que as tabelas saiam com as dimensoes certas (sao a construcao mais
frequente da documentacao, e carregam os resultados), e que marcador nenhum
vaze cru para o documento final.
"""

from django.test import SimpleTestCase

from documentacao.markdown_docx import Trecho, analisar, formatar_inline


def texto_de(trechos):
    return ''.join(t.texto for t in trechos)


class InlineTests(SimpleTestCase):
    def test_negrito(self):
        trechos = formatar_inline('isto e **importante** mesmo')

        self.assertEqual(texto_de(trechos), 'isto e importante mesmo')
        self.assertTrue(any(t.negrito and t.texto == 'importante' for t in trechos))

    def test_codigo_perde_as_crases(self):
        trechos = formatar_inline('use `manage.py migrate` agora')

        self.assertEqual(texto_de(trechos), 'use manage.py migrate agora')
        self.assertTrue(any(t.codigo for t in trechos))

    def test_link_guarda_a_url_e_mostra_so_o_texto(self):
        trechos = formatar_inline('veja [o documento](docs/X.md) ali')

        self.assertEqual(texto_de(trechos), 'veja o documento ali')
        self.assertEqual([t.url for t in trechos if t.url], ['docs/X.md'])

    def test_negrito_contendo_link_nao_vaza_sintaxe(self):
        """A regressao real: era o unico defeito nos 11 documentos."""
        trechos = formatar_inline('📖 **Leia [GCBD.md](GCBD.md) antes**')

        resultado = texto_de(trechos)
        self.assertNotIn('](', resultado)
        self.assertNotIn('**', resultado)
        self.assertIn('Leia GCBD.md antes', resultado)
        self.assertTrue(all(t.negrito for t in trechos if t.texto.strip()
                            and t.texto.strip() != '📖'))

    def test_link_cujo_texto_e_codigo(self):
        trechos = formatar_inline('em [`ingestao/base.py`](../backend/base.py)')

        self.assertNotIn('`', texto_de(trechos))
        alvo = [t for t in trechos if t.url]
        self.assertEqual(alvo[0].texto, 'ingestao/base.py')
        self.assertTrue(alvo[0].codigo)

    def test_negrito_com_codigo_dentro(self):
        trechos = formatar_inline('**o campo `dhw` importa**')

        self.assertEqual(texto_de(trechos), 'o campo dhw importa')
        self.assertTrue(all(t.negrito for t in trechos))
        self.assertTrue(any(t.codigo for t in trechos))

    def test_texto_sem_marcador_atravessa_intacto(self):
        original = 'uma frase comum, com virgula e acento: coracao'

        self.assertEqual(texto_de(formatar_inline(original)), original)

    def test_asterisco_solto_nao_quebra(self):
        trechos = formatar_inline('multiplicacao 3 * 4 = 12')

        self.assertEqual(texto_de(trechos), 'multiplicacao 3 * 4 = 12')


class BlocoTests(SimpleTestCase):
    def test_cabecalhos_por_nivel(self):
        blocos = analisar('# Um\n\n## Dois\n\n### Tres')

        self.assertEqual([b.nivel for b in blocos], [1, 2, 3])

    def test_tabela_vira_matriz_sem_a_linha_separadora(self):
        md = '| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |'

        tabela = analisar(md)[0].tabela

        self.assertEqual(len(tabela), 3)          # cabecalho + 2 linhas
        self.assertEqual(len(tabela[0]), 2)       # 2 colunas
        self.assertEqual(texto_de(tabela[2][1]), '4')

    def test_tabela_com_celula_vazia_mantem_a_coluna(self):
        """Perder uma coluna vazia desalinharia a tabela inteira."""
        md = '| a | b |\n|---|---|\n|  | 2 |'

        tabela = analisar(md)[0].tabela

        self.assertEqual(len(tabela[1]), 2)
        self.assertEqual(texto_de(tabela[1][0]), '')

    def test_bloco_de_codigo_nao_interpreta_marcador(self):
        """Um ** dentro de exemplo tem que sair literal."""
        md = '```\n**Instituicao:** algo\n```'

        blocos = analisar(md)

        self.assertEqual(blocos[0].tipo, 'codigo')
        self.assertIn('**Instituicao:**', blocos[0].texto_bruto)

    def test_cabecalho_dentro_de_codigo_nao_vira_titulo(self):
        md = '```\n# isto e um comentario de shell\n```'

        self.assertEqual([b.tipo for b in analisar(md)], ['codigo'])

    def test_lista_e_numerada(self):
        blocos = analisar('- um\n- dois\n\n1. a\n2. b')

        self.assertEqual([b.tipo for b in blocos], ['lista', 'numerada'])
        self.assertEqual(len(blocos[0].linhas), 2)
        self.assertEqual(texto_de(blocos[1].linhas[1]), 'b')

    def test_citacao_junta_linhas_seguidas(self):
        blocos = analisar('> primeira\n> segunda')

        self.assertEqual(blocos[0].tipo, 'citacao')
        self.assertEqual(texto_de(blocos[0].linhas[0]), 'primeira segunda')

    def test_paragrafo_junta_quebras_mas_para_no_proximo_bloco(self):
        blocos = analisar('linha um\nlinha dois\n\n## Titulo')

        self.assertEqual(blocos[0].tipo, 'paragrafo')
        self.assertEqual(texto_de(blocos[0].linhas[0]), 'linha um linha dois')
        self.assertEqual(blocos[1].tipo, 'cabecalho')

    def test_html_de_details_e_ignorado_mas_o_conteudo_fica(self):
        md = '<details>\n<summary>Titulo</summary>\n\ntexto interno\n</details>'

        blocos = analisar(md)

        self.assertEqual([b.tipo for b in blocos], ['paragrafo'])
        self.assertEqual(texto_de(blocos[0].linhas[0]), 'texto interno')

    def test_regua_horizontal(self):
        self.assertEqual([b.tipo for b in analisar('---')], ['regua'])

    def test_documento_vazio_nao_quebra(self):
        self.assertEqual(analisar(''), [])


class NadaSePercleTests(SimpleTestCase):
    """A garantia mais importante: o texto nao pode sumir na conversao."""

    def test_todo_o_texto_visivel_sobrevive(self):
        md = (
            '# Titulo\n\n'
            'Um paragrafo com **negrito** e `codigo`.\n\n'
            '| col | valor |\n|---|---|\n| dhw | 0,728 |\n\n'
            '- item de lista\n\n'
            '> uma citacao\n'
        )

        partes = []
        for bloco in analisar(md):
            for linha in bloco.linhas:
                partes.append(texto_de(linha))
            for linha in bloco.tabela:
                for celula in linha:
                    partes.append(texto_de(celula))
        tudo = ' '.join(partes)

        for esperada in ('Titulo', 'negrito', 'codigo', 'dhw', '0,728',
                         'item de lista', 'uma citacao'):
            self.assertIn(esperada, tudo, f'"{esperada}" sumiu na conversao')

        # E nenhum marcador pode ter sobrado.
        for marcador in ('**', '`', '](' ):
            self.assertNotIn(marcador, tudo, f'marcador {marcador!r} vazou')

    def test_numero_de_resultado_atravessa_a_tabela_intacto(self):
        md = '| Versao | F1 |\n|---|---|\n| **D — so 7d** | **0,728** |'

        tabela = analisar(md)[0].tabela

        self.assertEqual(texto_de(tabela[1][1]), '0,728')
        self.assertEqual(texto_de(tabela[1][0]), 'D — so 7d')
