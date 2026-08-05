"""Mede se a probabilidade que o modelo devolve quer dizer alguma coisa.

O painel vai exibir "risco 37%". Este comando responde se, entre os dias em que
o modelo disse 37%, o alerta aconteceu em cerca de 37% deles.

(!) Tudo com predicao **fora da dobra**: cada amostra e prevista pelo modelo que
nao a viu. Medir calibracao sobre o proprio treino mede memoria.
"""

from django.core.management.base import BaseCommand

from aquaculture.models import LocalRecife
from ml import calibracao, dataset, modelo


class Command(BaseCommand):
    help = 'Mede a calibracao da probabilidade prevista (curva de confiabilidade).'

    def add_arguments(self, parser):
        parser.add_argument('--horizonte', type=int, default=7)
        parser.add_argument(
            '--modelo', action='append', choices=list(modelo.MODELOS),
            help='Pode repetir. Padrao: os dois.',
        )
        parser.add_argument('--faixas', type=int, default=calibracao.FAIXAS_PADRAO)
        parser.add_argument(
            '--estrategia', default='quantil',
            choices=list(calibracao.ESTRATEGIAS),
        )
        parser.add_argument(
            '--calibrar', action='append',
            choices=['nenhuma', 'isotonic', 'sigmoid'],
            help='Pode repetir. Padrao: compara as tres.',
        )
        parser.add_argument('--semente', type=int, default=42)

    def handle(self, *args, **opcoes):
        locais = list(LocalRecife.objects.filter(latitude__isnull=False))
        if not locais:
            self.stderr.write(self.style.ERROR('Nenhum local com coordenadas.'))
            return

        conjunto = dataset.montar_todos(locais, horizonte=opcoes['horizonte'])
        if conjunto.n == 0:
            self.stderr.write(self.style.ERROR('Conjunto vazio.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING('=== CONJUNTO ==='))
        self.stdout.write(f'  {conjunto.resumo()}')
        self.stdout.write(f'  colunas: {", ".join(conjunto.colunas_de_entrada)}')

        self.stdout.write(self.style.WARNING(
            '\n  (!) O modelo usa class_weight="balanced", que trata as classes\n'
            '     como se fossem do mesmo tamanho. Isso e correto para DECIDIR\n'
            '     com 8% de positivos, e distorce a PROBABILIDADE por\n'
            '     construcao. O vies abaixo e esperado, nao surpresa.'
        ))

        metodos = opcoes['calibrar'] or ['nenhuma', 'sigmoid', 'isotonic']
        resumo = []

        for nome in (opcoes['modelo'] or list(modelo.MODELOS)):
            for metodo in metodos:
                calibrar = None if metodo == 'nenhuma' else metodo
                self.stdout.write(self.style.MIGRATE_HEADING(
                    f'\n=== {nome.upper()} / recalibracao: {metodo} ==='
                ))
                relatorio = calibracao.avaliar(
                    conjunto, nome=nome, n_faixas=opcoes['faixas'],
                    estrategia=opcoes['estrategia'], semente=opcoes['semente'],
                    calibrar=calibrar,
                )
                self.stdout.write(relatorio.resumo())
                self.stdout.write('\n  ' + self._veredito(relatorio))
                resumo.append((nome, metodo, relatorio))

        if len(resumo) > 1:
            self.stdout.write(self.style.MIGRATE_HEADING('\n=== COMPARACAO ==='))
            self.stdout.write(
                f'  {"modelo":11s} {"recalib":9s} {"ECE":>7s} {"MCE":>7s} '
                f'{"vies":>7s} {"confiab":>8s}'
            )
            for nome, metodo, r in resumo:
                self.stdout.write(
                    f'  {nome:11s} {metodo:9s} {r.erro_esperado:7.4f} '
                    f'{r.erro_maximo:7.4f} {r.vies_global:+7.4f} '
                    f'{r.decomposicao.confiabilidade:8.4f}'
                )

        self.stdout.write(self.style.SUCCESS('\nPronto.'))

    def _veredito(self, relatorio):
        ece = relatorio.erro_esperado
        if ece < 0.02:
            return (
                '[ok] Calibrado o suficiente para exibir porcentagem '
                f'(ECE {ece:.3f}).'
            )
        if ece < 0.05:
            return (
                f'(!) Calibracao sofrivel (ECE {ece:.3f}). Da para exibir '
                'faixa qualitativa, nao numero.'
            )
        return (
            f'(!) NAO calibrado (ECE {ece:.3f}). Exibir esta probabilidade como '
            'porcentagem seria mentir para quem le.'
        )
