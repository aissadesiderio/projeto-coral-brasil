"""Passo 1 da entrega 2: branqueamento observado com as termicas do GCBD.

Nao toca no banco nem na rede - le so o CSV do GCBD. E o experimento que
docs/GCBD.md registrou como gratuito: mede quanto do branqueamento observado
nos sitios brasileiros o sinal termico sozinho explica, antes de decidir se
vale ingerir salinidade e oxigenio.
"""

from django.core.management.base import BaseCommand

from ml import gcbd


class Command(BaseCommand):
    help = 'Treina e valida o modelo de branqueamento observado (GCBD).'

    def add_arguments(self, parser):
        parser.add_argument('--csv', help='Caminho do CSV do GCBD.')
        parser.add_argument('--pais', default=gcbd.PAIS_PADRAO)
        parser.add_argument(
            '--limiar', type=float, default=gcbd.LIMIAR_BRANQUEAMENTO,
            help='Percent_Bleaching acima do qual conta como branqueamento.',
        )
        parser.add_argument(
            '--modelo', default='logistica', choices=['logistica', 'boosting'],
        )
        parser.add_argument('--dobras', type=int, default=5)
        parser.add_argument(
            '--com-climatologia', action='store_true',
            help='Inclui as colunas constantes do sitio, alem das do dia.',
        )
        parser.add_argument(
            '--com-contexto', action='store_true',
            help='Inclui profundidade, distancia da costa, turbidez e ciclones.',
        )
        parser.add_argument(
            '--importancia', action='store_true',
            help='Mede a queda do PR-AUC ao embaralhar cada variavel.',
        )
        parser.add_argument(
            '--interpretavel', action='store_true',
            help='Usa so as 3 variaveis sem coeficiente invertido '
                 f'({", ".join(gcbd.FEATURES_INTERPRETAVEIS)}).',
        )

    def handle(self, *args, **opcoes):
        if opcoes['interpretavel']:
            features = list(gcbd.FEATURES_INTERPRETAVEIS)
        else:
            features = list(gcbd.TERMICAS_DO_DIA)
        if opcoes['com_climatologia']:
            features += list(gcbd.CLIMATOLOGIA_DO_SITIO)
        if opcoes['com_contexto']:
            features += list(gcbd.CONTEXTO_DO_SITIO)

        try:
            conjunto = gcbd.montar(
                caminho=opcoes['csv'], pais=opcoes['pais'],
                features=features, limiar=opcoes['limiar'],
            )
        except gcbd.ArquivoAusente as erro:
            self.stderr.write(self.style.ERROR(str(erro)))
            return

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== CONJUNTO ==='))
        self.stdout.write(f'  {conjunto.resumo()}')
        self.stdout.write(f'  alvo: Percent_Bleaching > {conjunto.limiar}%')
        self.stdout.write(f'  {len(features)} features: {", ".join(features)}')

        if conjunto.n < 20:
            self.stderr.write(
                self.style.ERROR(f'\nSo {conjunto.n} visitas - amostra insuficiente.')
            )
            return

        # A regra da NOAA sobre o conjunto inteiro: e a referencia publicada, e
        # nao precisa de treino nenhum para ser calculada.
        previsto = gcbd.prever_regra_noaa(conjunto.quadro)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n=== LINHA DE BASE: regra da NOAA (DHW >= {gcbd.LIMIAR_DHW_NOAA}) ==='
        ))
        self.stdout.write(f'  {gcbd.avaliar(conjunto.quadro["alvo"], previsto)}')
        zerados = (conjunto.quadro[gcbd.COLUNA_DHW] == 0).mean()
        self.stdout.write(
            f'  {gcbd.COLUNA_DHW} = 0 em {zerados:.1%} das visitas'
        )

        for agrupamento in ('sitio', 'ano'):
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'\n=== VALIDACAO AGRUPADA POR {agrupamento.upper()} ==='
            ))
            try:
                resultado = gcbd.validar(
                    conjunto, nome=opcoes['modelo'],
                    agrupar_por=agrupamento, n_dobras=opcoes['dobras'],
                )
            except ValueError as erro:
                self.stderr.write(f'  {erro}')
                continue
            self.stdout.write(resultado.resumo())

        if opcoes['importancia']:
            for agrupamento in ('sitio', 'ano'):
                self.stdout.write(self.style.MIGRATE_HEADING(
                    f'\n=== IMPORTANCIA (agrupado por {agrupamento}) ==='
                ))
                self.stdout.write(
                    gcbd.medir_importancia(
                        conjunto, nome=opcoes['modelo'],
                        agrupar_por=agrupamento, n_dobras=opcoes['dobras'],
                    ).resumo()
                )

        self.stdout.write(self.style.SUCCESS('\nPronto.'))
