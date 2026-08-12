"""Mostra o que ja foi adquirido, o que falta e o que desistiu de tentar.

⚠️ **Sem este comando a funcionalidade existiria so para quem abre o `shell`.**
O projeto ja aprendeu isso por outro caminho: a conferencia de especies virou
`manage.py conferir_especies` porque "lembrar de conferir" nao escala como
memoria, so como relatorio. Aqui vale o mesmo — um checkpoint esgotado e
exatamente o tipo de coisa que ninguem procura, porque nao gera erro: gera
silencio.

Tres usos:

    manage.py checkpoints                      # o retrato geral
    manage.py checkpoints --tarefa ingestao.noaa-crw.abrolhos-ba
    manage.py checkpoints --json manifesto.json --tarefa ...

🚨 **`--conferir` cruza a afirmacao com o dado real.** E o unico modo de pegar
o defeito que o checkpoint pode causar: afirmar como feito um bloco cujo dado
nao esta mais no banco. Ver `aquaculture.models.Checkpoint`.
"""

from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

import checkpoints as retomada
from aquaculture.models import Checkpoint, MedicaoAmbiental


class Command(BaseCommand):
    help = (
        'Mostra o progresso das tarefas retomaveis, exporta o manifesto em '
        'JSON e confere os checkpoints contra o dado real.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--tarefa', help='Limita a uma tarefa.')
        parser.add_argument(
            '--json', dest='caminho_json',
            help='Grava o manifesto em JSON no caminho dado.',
        )
        parser.add_argument(
            '--conferir', action='store_true',
            help='Cruza a evidencia gravada com o que existe no banco.',
        )
        parser.add_argument(
            '--limpar', action='store_true',
            help='Apaga os checkpoints da tarefa, forcando reprocessamento.',
        )

    def handle(self, *args, **opcoes):
        tarefa = opcoes['tarefa']

        if opcoes['limpar']:
            if not tarefa:
                # Sem esta trava, um `--limpar` sem argumento apagaria o
                # progresso de todas as tarefas de uma vez - e o proximo
                # backfill recomecaria do zero sem ninguem entender por que.
                raise CommandError(
                    'Use --limpar sempre com --tarefa. Apagar tudo de uma vez '
                    'faria o proximo backfill recomecar do zero.'
                )
            apagados = retomada.limpar(tarefa)
            self.stdout.write(self.style.WARNING(
                f'{apagados} checkpoint(s) apagado(s) de "{tarefa}". '
                'A proxima execucao vai refazer essas unidades.'
            ))
            return

        self._resumo(tarefa)

        if opcoes['conferir']:
            self._conferir(tarefa)

        if opcoes['caminho_json']:
            destino = Path(opcoes['caminho_json'])
            retomada.gravar(destino, tarefa)
            self.stdout.write(self.style.SUCCESS(
                f'Manifesto gravado em {destino}'
            ))

    def _resumo(self, tarefa):
        consulta = Checkpoint.objects.all()
        if tarefa:
            consulta = consulta.filter(tarefa=tarefa)

        registros = list(consulta)
        if not registros:
            alvo = f' para "{tarefa}"' if tarefa else ''
            self.stdout.write(f'Nenhum checkpoint registrado{alvo}.')
            return

        por_tarefa = Counter(registro.tarefa for registro in registros)

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Tarefas ({len(por_tarefa)})'
        ))
        for nome in sorted(por_tarefa):
            do_grupo = [r for r in registros if r.tarefa == nome]
            status = Counter(r.status for r in do_grupo)
            concluidos = status.get(Checkpoint.CONCLUIDO, 0)
            self.stdout.write(f'  {nome}')
            self.stdout.write(
                f'    {concluidos}/{len(do_grupo)} concluidas'
                f' | falhou: {status.get(Checkpoint.FALHOU, 0)}'
                f' | interrompida: {status.get(Checkpoint.EM_ANDAMENTO, 0)}'
            )

        esgotadas = [
            r for r in registros
            if r.tentativas >= retomada.TENTATIVAS_ATE_DESISTIR
            and r.status != Checkpoint.CONCLUIDO
        ]
        if esgotadas:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(
                f'Desistiu de tentar ({len(esgotadas)}) - estas nao serao '
                'retomadas sozinhas:'
            ))
            for registro in esgotadas:
                self.stdout.write(
                    f'  {registro.tarefa} / {registro.unidade}'
                    f' ({registro.tentativas} tentativas)'
                )
                if registro.erro:
                    self.stdout.write(f'    {registro.erro[:200]}')
            self.stdout.write('')
            self.stdout.write(
                '  Para tentar de novo depois de corrigir a causa:\n'
                '    manage.py checkpoints --limpar --tarefa <nome>'
            )

    def _conferir(self, tarefa):
        """Cruza a evidencia dos checkpoints de ingestao com as medicoes reais.

        So sabe conferir tarefas de ingestao - para as demais o verificador
        devolve `None`, e `conferir` as pula em vez de inventar um veredito.
        """
        alvos = [tarefa] if tarefa else sorted(
            Checkpoint.objects.values_list('tarefa', flat=True).distinct()
        )

        total = 0
        for nome in alvos:
            divergencias = retomada.conferir(nome, _verificador_de_ingestao)
            total += len(divergencias)
            for registro, esperado, encontrado in divergencias:
                self.stdout.write(self.style.ERROR(
                    f'  DIVERGE {registro.tarefa} / {registro.unidade}: '
                    f'checkpoint afirma {esperado}, banco tem {encontrado}'
                ))

        self.stdout.write('')
        if total:
            self.stdout.write(self.style.ERROR(
                f'{total} checkpoint(s) afirmam dado que o banco nao tem. '
                'Enquanto isso nao for resolvido, a retomada esta pulando '
                'blocos reais.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                'Conferido: todo checkpoint concluido corresponde ao que esta '
                'no banco.'
            ))


def _verificador_de_ingestao(registro):
    """Conta as medicoes que realmente existem para a unidade do checkpoint.

    A unidade de ingestao e "AAAA-MM-DD a AAAA-MM-DD" e a tarefa e
    "ingestao.<fonte>.<local>". Qualquer coisa fora desse formato devolve
    `None` - conferir o que nao se sabe conferir produziria alarme falso, que
    e pior que nao conferir.
    """
    partes = registro.tarefa.split('.')
    if len(partes) != 3 or partes[0] != 'ingestao':
        return None

    _, fonte, local_slug = partes
    if ' a ' not in registro.unidade:
        return None

    inicio, _, fim = registro.unidade.partition(' a ')
    try:
        existentes = MedicaoAmbiental.objects.filter(
            local_recife__slug=local_slug,
            fonte=fonte,
            data__gte=inicio,
            data__lte=fim,
        ).count()
    except (ValueError, TypeError):
        return None

    # 🚨 Compara so `gravadas`. `rejeitadas` nao vira linha no banco por
    # definicao - exigir que batesse marcaria como divergente todo bloco que
    # teve valor reprovado na validacao fisica, que e comportamento normal.
    return {'gravadas': existentes}
