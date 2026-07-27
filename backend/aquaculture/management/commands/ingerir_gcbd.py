"""Passo 2 da entrega 2: baixa a janela ambiental antes de cada visita do GCBD.

Usa a rede e exige credencial do Copernicus (a mesma de `ingerir`, guardada em
`~/.copernicusmarine`). Nao escreve no banco: o resultado vai para um cache em
`dados/`, com proveniencia por valor. O porque esta em `ml/gcbd_ambiental.py`.

Grava a cada visita concluida, entao pode ser interrompido e retomado.
"""

from django.core.management.base import BaseCommand

from ml import gcbd, gcbd_ambiental


class Command(BaseCommand):
    help = 'Baixa salinidade e oxigenio nos 90 dias antes de cada visita do GCBD.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', help='Caminho do CSV do GCBD.')
        parser.add_argument('--cache', help='Onde gravar as janelas.')
        parser.add_argument('--pais', default=gcbd.PAIS_PADRAO)
        parser.add_argument(
            '--dias', type=int, default=gcbd_ambiental.DIAS_DA_JANELA,
            help=f'Tamanho da janela. Padrao: {gcbd_ambiental.DIAS_DA_JANELA}',
        )
        parser.add_argument(
            '--limite', type=int,
            help='Extrai so as N primeiras visitas. Util para testar.',
        )
        parser.add_argument(
            '--variavel', action='append',
            choices=list(gcbd_ambiental.VARIAVEIS_COM_AGUA),
            help='Extrai so esta variavel. Pode repetir.',
        )
        parser.add_argument(
            '--agua', action='store_true',
            help='Acrescenta as variaveis de qualidade da agua '
                 f'({", ".join(gcbd_ambiental.QUALIDADE_DA_AGUA)}). '
                 'Saem do mesmo produto do oxigenio.',
        )

    def handle(self, *args, **opcoes):
        try:
            conjunto = gcbd.montar(caminho=opcoes['csv'], pais=opcoes['pais'])
        except gcbd.ArquivoAusente as erro:
            self.stderr.write(self.style.ERROR(str(erro)))
            return

        if opcoes['variavel']:
            variaveis = tuple(opcoes['variavel'])
        elif opcoes['agua']:
            variaveis = gcbd_ambiental.VARIAVEIS_COM_AGUA
        else:
            variaveis = gcbd_ambiental.VARIAVEIS
        visitas = gcbd_ambiental.visitas_de(conjunto)
        if opcoes['limite']:
            visitas = visitas.head(opcoes['limite'])

        self.stdout.write(self.style.MIGRATE_HEADING('=== O QUE SERA EXTRAIDO ==='))
        self.stdout.write(f'  {len(visitas)} visitas, {visitas["Site_ID"].nunique()} sitios')
        self.stdout.write(f'  janela de {opcoes["dias"]} dias antes de cada uma')
        self.stdout.write(f'  variaveis: {", ".join(variaveis)}')
        self.stdout.write(
            f'  ate {len(visitas) * len(variaveis) * (opcoes["dias"] + 1):,} '
            f'valores diarios'
        )
        self.stdout.write(
            f'  cache: {opcoes["cache"] or gcbd_ambiental.CAMINHO_CACHE}\n'
        )

        def progresso(variavel, indice, total, visita, raio):
            if indice % 10 == 0 or indice == total:
                self.stdout.write(
                    f'  {variavel:11s} {indice:4d}/{total}  '
                    f'sitio {visita.Site_ID} em {visita.Date}  raio {raio}°'
                )

        self.stdout.write(self.style.MIGRATE_HEADING('=== EXTRAINDO ==='))
        resultado = gcbd_ambiental.extrair(
            conjunto,
            caminho=opcoes['cache'],
            variaveis=variaveis,
            dias=opcoes['dias'],
            limite=opcoes['limite'],
            ao_progredir=progresso,
        )

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== RESULTADO ==='))
        self.stdout.write(f'  {resultado.resumo()}')

        if resultado.falhas:
            self.stdout.write(self.style.WARNING('\n  Falhas:'))
            for sitio, data, variavel, erro in resultado.falhas[:20]:
                self.stdout.write(f'    {sitio} {data} {variavel}: {erro}')

        self.stdout.write(self.style.SUCCESS(
            '\nPronto. Rode de novo para retomar o que faltou.'
        ))
