"""Material para decidir o limiar de alerta do painel.

Nao escolhe nada: mede a troca e a traduz para alertas e alarmes falsos por
ano, que e a unidade em que a decisao existe.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Mede a troca entre alarme falso e evento perdido, por limiar.'

    def add_arguments(self, parser):
        parser.add_argument('--horizonte', type=int, default=7)
        parser.add_argument('--modelo', default='logistica')
        parser.add_argument('--semente', type=int, default=42)
        parser.add_argument(
            '--calibrar', default='isotonic',
            help='Padrao: isotonic, que e o que o artefato servido usa.',
        )

    def handle(self, *args, **opcoes):
        from aquaculture.models import LocalRecife
        from ml import dataset, limiar as calculo

        locais = list(LocalRecife.objects.filter(ativo=True).order_by('slug'))
        if not locais:
            self.stderr.write('Nenhum local ativo. Rode a ingestao antes.')
            return

        conjunto = dataset.montar_todos(locais, opcoes['horizonte'])
        if conjunto.n == 0:
            self.stderr.write('Conjunto vazio: sem serie suficiente no banco.')
            return

        varredura = calculo.varrer(
            conjunto, opcoes['modelo'], opcoes['semente'], opcoes['calibrar']
        )

        self._contexto(varredura, opcoes)
        self._tabela(varredura)
        self._teto(varredura)
        self._candidatos(varredura)
        self._ressalva()

    # --- saida ------------------------------------------------------------

    def _contexto(self, v, opcoes):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Escolha do limiar de alerta'
        ))
        self.stdout.write(
            f'  modelo {opcoes["modelo"]}+{opcoes["calibrar"]}, '
            f'horizonte {opcoes["horizonte"]}d, predicoes fora da dobra'
        )
        self.stdout.write(
            f'  {v.n} amostras, {v.positivos} positivas '
            f'({v.taxa_base:.1%}), {v.anos} anos, {v.locais} locais'
        )
        self.stdout.write('')

    def _tabela(self, v):
        self.stdout.write(
            '  limiar | precisao revocacao    F1 | episodios | quando avisa  | alarme falso'
        )
        self.stdout.write(
            '         |                          |  peg/tot  | 1o dia atraso | dias/ano/recife'
        )
        self.stdout.write('  ' + '-' * 76)

        for p in v.pontos:
            ano = p.por_ano(v.anos, v.locais)
            self.stdout.write(
                f'  {p.limiar:6.2f} | {p.precisao:8.3f} {p.revocacao:9.3f} '
                f'{p.f1:5.3f} | {p.episodios_detectados:4d}/{p.episodios_reais:<4d} | '
                f'{p.episodios_no_primeiro_dia:6d} {p.atraso_medio_dias:6.2f} | '
                f'{ano["dias_de_alarme_falso"]:11.1f}'
            )

        self.stdout.write('')
        # Sem emoji: o console do Windows usa cp1252 e estoura com eles.
        self.stdout.write(
            '  "quando avisa": episodios avisados ja no 1o dia, e atraso medio\n'
            '  do primeiro aviso em dias. E o que impede ler o plato de\n'
            '  episodios como "apertar o limiar sai de graca" - nao sai: o\n'
            '  evento continua sendo pego, so que mais tarde.'
        )
        self.stdout.write('')

    def _teto(self, v):
        """O que nenhum limiar resolve.

        Existe para a conversa nao virar "e so baixar o corte": um episodio que
        escapa em todos os limiares nao e problema de escolha, e do modelo.
        """
        nunca = v.nunca_detectados()
        if not nunca:
            return

        self.stdout.write(self.style.ERROR(
            f'  Escapam em TODOS os limiares varridos ({len(nunca)}):'
        ))
        for e in nunca:
            self.stdout.write(
                f'    {e["local"]:<22} {e["inicio"]} a {e["fim"]} '
                f'({e["dias"]} dia{"s" if e["dias"] > 1 else ""})'
            )
        self.stdout.write(
            '  Baixar o limiar nao recupera estes. O teto e do modelo.'
        )
        self.stdout.write('')

    def _candidatos(self, v):
        self.stdout.write(self.style.MIGRATE_HEADING('  Candidatos'))

        melhor = v.melhor_f1()
        if melhor:
            self.stdout.write(
                f'  F1 maximo ......... {melhor.limiar:.2f}  '
                f'(F1 {melhor.f1:.3f}, precisao {melhor.precisao:.3f}, '
                f'revocacao {melhor.revocacao:.3f})'
            )

        completo = v.sem_perder_episodio()
        if completo:
            self._candidato('sem perder evento', completo, v)
        else:
            self.stdout.write(
                '  sem perder evento . nao existe: nenhum limiar pega os '
                f'{v.pontos[0].episodios_reais} episodios'
            )
            cobertura = v.melhor_cobertura()
            if cobertura:
                self._candidato('cobertura maxima', cobertura, v)

        # Lido de settings, e nao fixado: o comando existe para reavaliar a
        # decisao, e um numero cravado aqui passaria a mentir no dia seguinte
        # a ela mudar.
        from django.conf import settings

        em_uso = float(getattr(settings, 'PAINEL_LIMIAR', 0.10))
        atual = v.em(em_uso)
        if atual:
            self._candidato(f'em uso hoje ({em_uso:.2f})', atual, v)
        else:
            self.stdout.write(
                f'  em uso hoje ....... {em_uso:.2f}  (fora da varredura)'
            )
        self.stdout.write('')

    def _candidato(self, rotulo, ponto, v):
        ano = ponto.por_ano(v.anos, v.locais)
        self.stdout.write(
            f'  {rotulo:.<18} {ponto.limiar:.2f}  '
            f'({ponto.episodios_detectados}/{ponto.episodios_reais} episodios, '
            f'{ano["dias_de_alarme_falso"]:.1f} dias de alarme falso por ano '
            f'e por recife)'
        )
        for e in ponto.perdidos:
            self.stdout.write(
                f'      perde: {e["local"]} {e["inicio"]} '
                f'({e["dias"]} dia{"s" if e["dias"] > 1 else ""})'
            )

    def _ressalva(self):
        self.stdout.write(self.style.WARNING(
            '  Ressalva: os limiares sao comparados sobre as mesmas predicoes\n'
            '  que os avaliam. Serve para escolher entre eles, nao como\n'
            '  estimativa do desempenho no ano que vem.'
        ))
        self.stdout.write('')
