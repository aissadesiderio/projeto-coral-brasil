"""Gera as figuras sobre o que o modelo aprendeu.

Artefato **derivado**: nao versionado, regeravel por este comando. Mesma
decisao do `.joblib`, do `.docx` e da projecao do Neo4j — figura versionada
envelhece em silencio, e em duas semanas o PNG mostra um modelo e o codigo
produz outro, sem ninguem saber qual vale.

⚠️ **Isto nao e o `gerar_relatorio`, removido em 28/07/2026.** Aquele montava um
documento de aparencia oficial a partir de 3 linhas de demonstracao, com titulo
"2020-2025" sobre dados de abril de 2026. A diferenca nao e de formato: aqui
todo numero desenhado vem de uma funcao que ja o calcula e ja o imprime em
texto, e cada figura sai com um `.txt` ao lado dizendo sobre que dado ela foi
feita.
"""

import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

SAIDA_PADRAO = 'relatorios_gerados/graficos'


class Command(BaseCommand):
    help = 'Gera as figuras de interpretacao do modelo (artefato derivado).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--saida', default=SAIDA_PADRAO,
            help=f'Pasta de destino. Padrao: {SAIDA_PADRAO}',
        )
        parser.add_argument(
            '--modelo', default='logistica',
            help='Modelo das figuras por ano. So a logistica tem coeficiente.',
        )
        parser.add_argument('--horizonte', type=int, default=7)
        parser.add_argument(
            '--repeticoes', type=int, default=5,
            help='Repeticoes da permutacao. Menos = mais rapido, mais ruido.',
        )
        parser.add_argument(
            '--pdf', action='store_true',
            help='Salva tambem em PDF, para inserir no texto sem perder nitidez.',
        )
        parser.add_argument(
            '--so', nargs='+', metavar='FIGURA',
            help='Gera so estas: alvo, coeficientes, importancia, tempo, resposta.',
        )

    def handle(self, *args, **opcoes):
        from aquaculture.models import LocalRecife
        from ml import (
            calibracao, dataset, graficos, importancia, persistencia, predicao,
        )

        raiz = Path(settings.BASE_DIR).parent
        destino = raiz / opcoes['saida']
        destino.mkdir(parents=True, exist_ok=True)

        pedidas = set(opcoes['so'] or (
            'alvo', 'coeficientes', 'importancia', 'tempo', 'resposta',
        ))
        formatos = ('png', 'pdf') if opcoes['pdf'] else ('png',)

        geradas_sem_banco = []
        if 'alvo' in pedidas:
            # 🚨 Primeira, e a unica que nao consulta o banco. E o esquema que
            # separa "alerta de estresse termico" de "branqueamento
            # observado" — sem ele, as outras quatro sao lidas como previsao
            # de branqueamento, que e o que o projeto passou tres secoes de
            # RESULTADOS.md mostrando que elas nao sao.
            geradas_sem_banco.append(graficos.o_que_e_previsto())

        locais = list(LocalRecife.objects.order_by('slug'))
        if not locais:
            raise CommandError(
                'Nao ha local cadastrado. As figuras saem do banco, e um banco '
                'vazio nao produz figura - produziria uma figura vazia, que e '
                'pior. Rode a ingestao antes.'
            )

        self.stdout.write(self.style.MIGRATE_HEADING('=== MONTANDO O CONJUNTO ==='))
        conjunto = dataset.montar_todos(locais, horizonte=opcoes['horizonte'])
        if conjunto.n == 0:
            raise CommandError(
                'O conjunto saiu vazio. Serie curta demais para fechar a '
                'janela de 7 dias, ou sem o alvo `baa`. Rode "manage.py '
                'ingerir --completo --desde=2020-01-01".'
            )
        self.stdout.write(f'  {conjunto.resumo()}')
        self.stdout.write(f'  destino: {destino}\n')

        geradas = list(geradas_sem_banco)
        inicio = time.time()

        if {'coeficientes', 'importancia'} & pedidas:
            self.stdout.write('Medindo importancia (leave-year-out)...')
            medida = importancia.medir(
                conjunto, opcoes['modelo'], opcoes['repeticoes'],
            )
            if not medida.anos:
                raise CommandError(
                    'Nenhum ano com evento no conjunto: nao ha o que medir. '
                    'Com zero positivos o PR-AUC fica indefinido, e uma figura '
                    'sairia com eixo vazio parecendo resultado.'
                )
            self.stdout.write(f'  anos com evento: {medida.anos}')

            if 'coeficientes' in pedidas:
                geradas.append(graficos.coeficientes_por_ano(medida))
            if 'importancia' in pedidas:
                geradas.append(graficos.importancia_por_ano(medida))

        if 'tempo' in pedidas:
            self.stdout.write('Calculando predicoes fora da dobra...')
            from ml.modelo import alvo_binario

            quadro = conjunto.quadro.copy()
            _, probabilidade = calibracao.predicoes_fora_da_dobra(
                conjunto, opcoes['modelo'],
            )
            quadro['probabilidade'] = probabilidade
            quadro['alvo_binario'] = alvo_binario(quadro['alvo'])
            # Dias que nenhuma dobra avaliou (ano sem as duas classes no
            # treino) ficariam como buraco silencioso na curva.
            avaliados = quadro['probabilidade'].notna()
            self.stdout.write(
                f'  {int(avaliados.sum())} de {len(quadro)} dias avaliados '
                f'fora da dobra'
            )
            quadro = quadro[avaliados]

            limiar = float(getattr(settings, 'PAINEL_LIMIAR', 0.10))
            for local in locais:
                if not (quadro['local'] == local.slug).any():
                    self.stdout.write(f'  (sem dados avaliados: {local.slug})')
                    continue
                geradas.append(
                    graficos.linha_do_tempo(
                        quadro, 'probabilidade', limiar, local.slug,
                        conjunto.colunas_de_entrada,
                    )
                )

        if 'resposta' in pedidas:
            self.stdout.write('Carregando o modelo servido...')
            nome = getattr(settings, 'PAINEL_MODELO', 'entrega1_baa')
            try:
                # O mesmo carregador do painel, e nao `persistencia.carregar`
                # direto: e ele que confere assinatura e versao do sklearn
                # antes de despickar. A figura precisa descrever exatamente o
                # objeto que responde no `/api/painel-risco/`.
                ajuste, metadados = predicao.carregar_modelo(nome)
            except (persistencia.ArtefatoAusente,
                    persistencia.ArtefatoIncompativel) as erro:
                raise CommandError(
                    f'{erro}\n\nA figura de resposta descreve o modelo que o '
                    f'painel serve, e ele nao esta no disco. Rode '
                    f'"manage.py treinar_final" antes.'
                ) from erro

            self.stdout.write(
                f'  {metadados.get("nome")}, treinado em '
                f'{metadados.get("gerado_em")}, calibracao '
                f'{metadados.get("calibracao")}'
            )
            limiar = float(getattr(settings, 'PAINEL_LIMIAR', 0.10))
            geradas.append(
                graficos.resposta_a_variavel(
                    ajuste, conjunto.quadro, list(ajuste.colunas), limiar,
                )
            )

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== FIGURAS ==='))
        for figura in geradas:
            caminhos = figura.salvar(destino, formatos)
            tamanho = caminhos[0].stat().st_size / 1024
            self.stdout.write(f'  {figura.nome:34s} {tamanho:7.1f} KB')

        decorrido = time.time() - inicio
        self.stdout.write(self.style.SUCCESS(
            f'\n{len(geradas)} figura(s) em {decorrido:.1f}s.'
        ))
        self.stdout.write(
            'Cada figura tem um .txt ao lado com a legenda e a procedencia.\n'
            'Artefato derivado: nao versionado, regeravel com este comando.'
        )
