"""Ingestao de dados ambientais das fontes externas.

Uso:
    python backend/manage.py ingerir --desde=2024-01-01
    python backend/manage.py ingerir --local=abrolhos-ba --fonte=noaa_crw
    python backend/manage.py ingerir --desde=ontem --completo

Substitui `coleta_de_dados.py` (que descartava o que buscava) e a parte de
carga do `carregar_historico.py` (que apagava a tabela a cada execucao).
"""

from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from aquaculture.models import LocalRecife
from ingestao.registro import CONECTORES, ingerir, obter_conector


def _parse_data(texto):
    if texto == 'ontem':
        return date.today() - timedelta(days=1)
    if texto == 'hoje':
        return date.today()
    try:
        return datetime.strptime(texto, '%Y-%m-%d').date()
    except ValueError as exc:
        raise CommandError(
            f'Data invalida: "{texto}". Use AAAA-MM-DD, "ontem" ou "hoje".'
        ) from exc


class Command(BaseCommand):
    help = 'Ingere dados ambientais das fontes externas para os locais de recife.'

    def add_arguments(self, parser):
        parser.add_argument('--local', help='Slug do local. Padrao: todos os ativos.')
        parser.add_argument(
            '--fonte',
            help=f'Slug do conector. Padrao: todos. Disponiveis: {", ".join(sorted(CONECTORES))}',
        )
        parser.add_argument('--desde', default='ontem', help='Data inicial (AAAA-MM-DD).')
        parser.add_argument('--ate', default='hoje', help='Data final (AAAA-MM-DD).')
        parser.add_argument(
            '--completo',
            action='store_true',
            help='Rebaixa todo o periodo em vez de retomar da ultima data ingerida.',
        )

    def handle(self, *args, **options):
        inicio = _parse_data(options['desde'])
        fim = _parse_data(options['ate'])

        if inicio > fim:
            raise CommandError(f'Periodo invalido: {inicio} e posterior a {fim}.')

        locais = LocalRecife.objects.filter(ativo=True)
        if options['local']:
            locais = locais.filter(slug=options['local'])
            if not locais.exists():
                raise CommandError(f'Local "{options["local"]}" nao encontrado ou inativo.')

        sem_coordenadas = [l for l in locais if not l.tem_coordenadas]
        locais = [l for l in locais if l.tem_coordenadas]

        for local in sem_coordenadas:
            self.stdout.write(
                self.style.WARNING(
                    f'[pulado] {local.slug}: sem coordenadas - preencha no admin.'
                )
            )

        if not locais:
            raise CommandError('Nenhum local com coordenadas para ingerir.')

        slugs_fonte = [options['fonte']] if options['fonte'] else sorted(CONECTORES)

        # Resolve os conectores antes de anunciar o plano: nao faz sentido
        # imprimir o que sera feito para so entao descobrir que a fonte
        # nao existe.
        conectores = []
        for slug in slugs_fonte:
            try:
                conectores.append(obter_conector(slug))
            except KeyError:
                raise CommandError(
                    f'Conector "{slug}" nao existe. '
                    f'Disponiveis: {", ".join(sorted(CONECTORES))}'
                ) from None

        self.stdout.write(f'Periodo: {inicio} a {fim}')
        self.stdout.write(f'Locais: {", ".join(l.slug for l in locais)}')
        self.stdout.write(f'Fontes: {", ".join(slugs_fonte)}')
        self.stdout.write('')

        total_gravado = 0
        houve_falha = False

        for conector in conectores:
            slug = conector.slug

            for local in locais:
                execucao = ingerir(
                    local,
                    inicio,
                    fim,
                    conector,
                    incremental=not options['completo'],
                )
                total_gravado += execucao.registros_gravados

                if execucao.status == 'falha':
                    houve_falha = True
                    self.stdout.write(
                        self.style.ERROR(
                            f'  [falha]   {slug}/{local.slug}: {execucao.mensagem_erro[:120]}'
                        )
                    )
                elif execucao.status == 'parcial':
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [parcial] {slug}/{local.slug}: '
                            f'{execucao.registros_gravados} gravados, '
                            f'{execucao.registros_rejeitados} reprovados na validacao'
                        )
                    )
                else:
                    self.stdout.write(
                        f'  [ok]      {slug}/{local.slug}: '
                        f'{execucao.registros_gravados} medicoes'
                    )

        self.stdout.write('')
        estilo = self.style.WARNING if houve_falha else self.style.SUCCESS
        self.stdout.write(
            estilo(
                f'Total: {total_gravado} medicoes gravadas.'
                + (' Houve falhas - ver ExecucaoIngestao.' if houve_falha else '')
            )
        )
