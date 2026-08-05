"""Testes da escala de aviso.

🚨 **O defeito que estes testes existem para impedir e silencioso.** Uma escala
com os cortes fora de ordem nao levanta erro: ela classifica, e classifica
errado, porque `classificar` devolve o primeiro corte alcancado. Uma
probabilidade de 0,9 numa escala embaralhada pode sair como "observacao" e
ninguem descobre — o site continua respondendo, com o nome errado.

E o mesmo formato de erro que o projeto ja pagou duas vezes: cobertura gravada
que envelhecia em silencio (27/07) e a tabela de episodios com duas linhas
trocadas, que decidiu o limiar errado por tres dias (27–30/07). Em todos, o
dado estava certo e a **leitura** estava errada.
"""

from django.test import SimpleTestCase

from ml import niveis


class ClassificarTests(SimpleTestCase):
    def test_probabilidade_alta_cai_no_degrau_alto(self):
        self.assertEqual(niveis.classificar(0.9).slug, 'alerta_alto')

    def test_probabilidade_media_cai_em_alerta(self):
        self.assertEqual(niveis.classificar(0.30).slug, 'alerta')

    def test_probabilidade_baixa_cai_em_observacao(self):
        self.assertEqual(niveis.classificar(0.08).slug, 'observacao')

    def test_probabilidade_muito_baixa_nao_avisa(self):
        self.assertEqual(niveis.classificar(0.01).slug, 'sem_aviso')

    def test_zero_tem_nivel(self):
        """🚨 A isotonica devolve 0,000 exato em 12,2% das amostras de treino.

        Sem um degrau de corte 0.0 no fim da escala, essas probabilidades
        ficariam sem nivel nenhum.
        """
        self.assertEqual(niveis.classificar(0.0).slug, 'sem_aviso')

    def test_um_tem_nivel(self):
        """E a isotonica devolve 1,000 exato tambem."""
        self.assertEqual(niveis.classificar(1.0).slug, 'alerta_alto')

    def test_o_corte_entra_no_nivel_que_ele_nomeia(self):
        """⚠️ `>=`, e nao `>`.

        O corte e promessa publica: "avisamos a partir de 20%". Com `>` a
        promessa falharia exatamente no ponto que ela nomeia, e o site diria
        "sem aviso" para uma probabilidade de exatamente 20%.
        """
        for nivel in niveis.ESCALA:
            with self.subTest(nivel=nivel.slug):
                self.assertEqual(
                    niveis.classificar(nivel.corte).slug, nivel.slug,
                )


class EscalaCanonicaTests(SimpleTestCase):
    def test_os_cortes_estao_em_ordem_decrescente(self):
        cortes = [n.corte for n in niveis.ESCALA]

        self.assertEqual(cortes, sorted(cortes, reverse=True))

    def test_o_ultimo_degrau_recebe_tudo(self):
        self.assertEqual(niveis.ESCALA[-1].corte, 0.0)

    def test_o_piso_e_o_teto_do_modelo(self):
        """🚨 O corte mais baixo e 0,05 porque nenhum outro cobre mais.

        Medido em 30/07/2026: 0,05 detecta 18 dos 19 episodios, e nenhum corte
        varrido detecta mais. Subir este piso seria descartar cobertura que
        existe — foi exatamente o que a decisao de 27/07 fez sem saber.
        """
        cortes_que_avisam = [n.corte for n in niveis.ESCALA if n.corte > 0]

        self.assertEqual(min(cortes_que_avisam), 0.05)

    def test_todo_nivel_diz_o_que_fazer(self):
        """Nivel sem acao associada e nivel que cada um interpreta a seu modo."""
        for nivel in niveis.ESCALA:
            with self.subTest(nivel=nivel.slug):
                self.assertTrue(nivel.acao.strip())

    def test_so_os_degraus_de_cima_exigem_acao(self):
        """A observacao existe para cobrir sem mobilizar.

        Se ela exigisse acao, a escala inteira perderia o sentido: seria de
        novo um corte unico em 0,05, com metade dos avisos falsos.
        """
        por_slug = {n.slug: n for n in niveis.ESCALA}

        self.assertFalse(por_slug['sem_aviso'].exige_acao)
        self.assertFalse(por_slug['observacao'].exige_acao)
        self.assertTrue(por_slug['alerta'].exige_acao)
        self.assertTrue(por_slug['alerta_alto'].exige_acao)

    def test_os_slugs_sao_unicos(self):
        slugs = [n.slug for n in niveis.ESCALA]

        self.assertEqual(len(set(slugs)), len(slugs))


class ValidacaoTests(SimpleTestCase):
    """🚨 O que impede a escala errada de classificar em silencio."""

    def _nivel(self, slug, corte, ordem):
        return niveis.Nivel(slug=slug, rotulo=slug, corte=corte, acao='x',
                            ordem=ordem)

    def test_cortes_fora_de_ordem_sao_recusados(self):
        embaralhada = (
            self._nivel('baixo', 0.05, 1),
            self._nivel('alto', 0.50, 2),
            self._nivel('nada', 0.0, 0),
        )

        with self.assertRaises(niveis.EscalaInvalida) as capturado:
            niveis.validar(embaralhada)

        self.assertIn('decrescente', str(capturado.exception))

    def test_a_mensagem_explica_por_que_isso_e_grave(self):
        """Recusar sem dizer o motivo convida a "consertar" invertendo de novo."""
        embaralhada = (
            self._nivel('baixo', 0.05, 1),
            self._nivel('alto', 0.50, 2),
            self._nivel('nada', 0.0, 0),
        )

        with self.assertRaises(niveis.EscalaInvalida) as capturado:
            niveis.validar(embaralhada)

        self.assertIn('sem avisar', str(capturado.exception))

    def test_escala_sem_piso_zero_e_recusada(self):
        sem_piso = (
            self._nivel('alto', 0.50, 1),
            self._nivel('baixo', 0.05, 0),
        )

        with self.assertRaises(niveis.EscalaInvalida) as capturado:
            niveis.validar(sem_piso)

        self.assertIn('0.0', str(capturado.exception))

    def test_cortes_repetidos_sao_recusados(self):
        repetida = (
            self._nivel('a', 0.20, 2),
            self._nivel('b', 0.20, 1),
            self._nivel('nada', 0.0, 0),
        )

        with self.assertRaises(niveis.EscalaInvalida):
            niveis.validar(repetida)

    def test_escala_vazia_e_recusada(self):
        with self.assertRaises(niveis.EscalaInvalida):
            niveis.validar(())

    def test_classificar_valida_antes_de_responder(self):
        """Nao adianta validar so na configuracao: `classificar` e a porta."""
        embaralhada = (
            self._nivel('baixo', 0.05, 1),
            self._nivel('alto', 0.50, 2),
            self._nivel('nada', 0.0, 0),
        )

        with self.assertRaises(niveis.EscalaInvalida):
            niveis.classificar(0.9, embaralhada)


class DeConfiguracaoTests(SimpleTestCase):
    """Os cortes sao decisao de quem opera, e precisam sair do `settings`."""

    def test_lista_vazia_usa_a_escala_canonica(self):
        self.assertIs(niveis.de_configuracao([]), niveis.ESCALA)

    def test_none_usa_a_escala_canonica(self):
        self.assertIs(niveis.de_configuracao(None), niveis.ESCALA)

    def test_monta_a_escala_declarada(self):
        escala = niveis.de_configuracao([
            {'slug': 'grave', 'rotulo': 'Grave', 'corte': 0.6, 'acao': 'agir'},
            {'slug': 'nada', 'rotulo': 'Nada', 'corte': 0.0},
        ])

        self.assertEqual([n.slug for n in escala], ['grave', 'nada'])
        self.assertEqual(niveis.classificar(0.7, escala).slug, 'grave')

    def test_a_ordem_sai_da_posicao(self):
        escala = niveis.de_configuracao([
            {'slug': 'a', 'rotulo': 'A', 'corte': 0.6},
            {'slug': 'b', 'rotulo': 'B', 'corte': 0.2},
            {'slug': 'c', 'rotulo': 'C', 'corte': 0.0},
        ])

        self.assertEqual([n.ordem for n in escala], [2, 1, 0])

    def test_campo_faltando_e_recusado_dizendo_qual(self):
        with self.assertRaises(niveis.EscalaInvalida) as capturado:
            niveis.de_configuracao([{'slug': 'x', 'corte': 0.5}])

        self.assertIn('rotulo', str(capturado.exception))

    def test_configuracao_fora_de_ordem_e_recusada(self):
        with self.assertRaises(niveis.EscalaInvalida):
            niveis.de_configuracao([
                {'slug': 'a', 'rotulo': 'A', 'corte': 0.1},
                {'slug': 'b', 'rotulo': 'B', 'corte': 0.5},
                {'slug': 'c', 'rotulo': 'C', 'corte': 0.0},
            ])


class ComoPayloadTests(SimpleTestCase):
    def test_leva_a_escala_inteira(self):
        payload = niveis.como_payload()

        self.assertEqual(len(payload), len(niveis.ESCALA))

    def test_cada_item_leva_o_corte_de_onde_veio(self):
        """Sem o corte, quem consome ve o nome do nivel e nao sabe de onde saiu."""
        for item in niveis.como_payload():
            with self.subTest(nivel=item['slug']):
                self.assertIn('corte', item)
                self.assertIn('acao', item)
                self.assertIn('exige_acao', item)
