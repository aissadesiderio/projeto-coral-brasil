"""Treina o modelo **uma vez sobre todos os dados** e grava o artefato.

Diferente de `treinar_modelo` e `treinar_gcbd`, que existem para **medir**:
eles treinam um modelo por dobra da validacao e descartam todos, porque cada um
so vale para prever a parte que nao viu.

Aqui e o oposto: um modelo so, sobre tudo, para o painel carregar.

⚠️ **Este comando nao mede nada, e isso e deliberado.** Um numero de desempenho
calculado sobre os mesmos dados do treino mediria memoria, nao previsao — e o
proprio comando de medicao ja existe. Rode `treinar_modelo` para saber se o
modelo presta; rode este para gravar o que sera servido.
"""

from django.core.management.base import BaseCommand

from aquaculture.models import LocalRecife
from ml import dataset, modelo, persistencia

NOME_PADRAO = 'entrega1_baa'


class Command(BaseCommand):
    help = 'Treina sobre todos os dados e grava o modelo para o painel usar.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--nome', default=NOME_PADRAO,
            help=f'Nome do artefato. Padrao: {NOME_PADRAO}',
        )
        parser.add_argument(
            '--horizonte', type=int, default=7,
            help='Dias de antecedencia da previsao. Padrao: 7',
        )
        parser.add_argument(
            '--modelo', default='logistica', choices=list(modelo.MODELOS),
        )
        parser.add_argument(
            '--calibrar', default='isotonic',
            choices=['nenhuma', 'isotonic', 'sigmoid'],
            help='Recalibra a probabilidade. Padrao: isotonic - sem isso o '
                 'numero exibido mente (ECE 0,081). Ver docs/RESULTADOS.md §23.',
        )
        parser.add_argument('--semente', type=int, default=42)
        parser.add_argument('--pasta', help='Onde gravar. Padrao: dados/modelos/')
        parser.add_argument(
            '--listar', action='store_true',
            help='So lista os modelos ja gravados e sai.',
        )

    def handle(self, *args, **opcoes):
        if opcoes['listar']:
            return self._listar(opcoes['pasta'])

        locais = list(LocalRecife.objects.filter(latitude__isnull=False))
        if not locais:
            self.stderr.write(self.style.ERROR(
                'Nenhum local com coordenadas. Sem dados para treinar.'
            ))
            return

        conjunto = dataset.montar_todos(locais, horizonte=opcoes['horizonte'])
        if conjunto.n == 0:
            self.stderr.write(self.style.ERROR(
                f'Conjunto vazio no horizonte {opcoes["horizonte"]}. '
                'Rode a ingestao antes.'
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING('=== CONJUNTO ==='))
        self.stdout.write(f'  {conjunto.resumo()}')
        self.stdout.write(f'  locais: {", ".join(l.slug for l in locais)}')
        self.stdout.write(f'  colunas: {", ".join(conjunto.colunas_de_entrada)}')

        alvo = modelo.alvo_binario(conjunto.quadro['alvo'])
        positivos = int(alvo.sum())
        if positivos == 0:
            self.stderr.write(self.style.ERROR(
                'Nenhuma amostra positiva: o modelo nao teria o que aprender.'
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== TREINO ==='))
        self.stdout.write(
            '  (!) Sobre TODOS os dados, sem dobra. Este comando nao mede\n'
            '      desempenho - para isso existe "treinar_modelo".'
        )

        calibrar = None if opcoes['calibrar'] == 'nenhuma' else opcoes['calibrar']
        if calibrar is None:
            self.stdout.write(self.style.WARNING(
                '  (!) Sem recalibracao: a probabilidade gravada NAO pode ser '
                'exibida como porcentagem. Ver docs/RESULTADOS.md §23.'
            ))
        else:
            self.stdout.write(f'  recalibracao: {calibrar}')

        ajuste = modelo.treinar(
            conjunto.quadro, conjunto.colunas_de_entrada,
            nome=opcoes['modelo'], horizonte=opcoes['horizonte'],
            semente=opcoes['semente'], calibrar=calibrar,
        )

        caminho_modelo, caminho_json = persistencia.salvar(
            ajuste, opcoes['nome'], pasta=opcoes['pasta'],
            extras={
                'semente': opcoes['semente'],
                'locais': sorted(l.slug for l in locais),
                'dias_na_serie': conjunto.dias_na_serie,
                'descartadas_sem_alvo': conjunto.descartadas_sem_alvo,
                'descartadas_sem_janela': conjunto.descartadas_sem_janela,
            },
        )

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== GRAVADO ==='))
        self.stdout.write(f'  modelo    : {caminho_modelo}')
        self.stdout.write(f'  metadados : {caminho_json}')
        self.stdout.write(
            f'  {ajuste.n_treino} amostras, {ajuste.positivos_treino} positivas '
            f'({ajuste.positivos_treino / ajuste.n_treino:.1%})'
        )

        # Confere na hora que o artefato volta igual. Gravar sem conferir seria
        # descobrir o problema so quando o painel pedir a previsao.
        recarregado = persistencia.carregar(opcoes['nome'], pasta=opcoes['pasta'])
        iguais = recarregado.colunas == ajuste.colunas
        self.stdout.write(
            f'  releitura : {"OK" if iguais else "DIVERGIU"} '
            f'({len(recarregado.colunas)} colunas)'
        )

        self.stdout.write(self.style.SUCCESS(
            '\nArtefato derivado: nao versionado, regeravel com este comando.'
        ))

    def _listar(self, pasta):
        modelos = persistencia.listar(pasta)
        if not modelos:
            self.stdout.write('Nenhum modelo gravado ainda.')
            return
        for m in modelos:
            if 'erro' in m:
                self.stdout.write(self.style.WARNING(f'  {m["nome"]}: {m["erro"]}'))
                continue
            self.stdout.write(
                f'  {m["nome"]:20s} {m["modelo"]:10s} '
                f'alvo={m.get("alvo", "?")}  '
                f'n={m.get("n_treino", "?")}  '
                f'gerado em {m.get("gerado_em", "?")}  '
                f'sklearn {m.get("sklearn", "?")}'
            )
