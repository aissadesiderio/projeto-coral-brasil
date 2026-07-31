"""Mede se o modelo presta, escondendo um ano inteiro por vez.

🚨 **Este comando estava descrito em todo lugar e nao existia.** Descoberto em
28/07/2026: o README mostrava como roda-lo, o `treinar_final` mandava usa-lo, e
o aviso de envelhecimento da rotina diaria dizia "manage.py treinar_modelo
avalia". Nenhum deles estava errado sobre o que ele **deveria** fazer — o
codigo da avaliacao ja existia em `ml/modelo.py`, testado. Faltava so o
invólucro, e a confusao veio do arquivo legado `backend/ml_models/
treinar_modelo.py`, que tem o mesmo nome e nao e comando.

A falta importava mais do que parece: a decisao de **nao retreinar na rotina
diaria** se apoia em "retreinar sem medir e errado, e medir e um ato
deliberado". Sem um comando para medir, essa frase nao tinha como ser seguida
por quem nao escreve Python.

**A diferenca para os outros dois comandos de treino:**

| Comando | Treina | Grava | Serve para |
|---|---|---|---|
| `treinar_modelo` | um por ano escondido | nada | **saber se presta** |
| `treinar_final` | um sobre tudo | o artefato | **servir no painel** |
| `treinar_gcbd` | sobre o CSV do GCBD | nada | a entrega 2 |

⚠️ **A divisao e por ano da data do alvo**, e nao aleatoria. Dias vizinhos do
mesmo episodio cairiam dos dois lados numa divisao aleatoria, e o modelo
"acertaria" o que ja viu — foi exatamente o defeito do codigo original do
projeto. Ver docs/METODOLOGIA_SIMPLES.md secao 3.
"""

from django.core.management.base import BaseCommand

from aquaculture.models import LocalRecife
from ml import dataset, modelo


class Command(BaseCommand):
    help = (
        'Avalia o modelo com leave-year-out contra as duas linhas de base: '
        'persistencia e a regra publicada da NOAA.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--horizonte', type=int, default=7,
            help='Dias de antecedencia da previsao. Padrao: 7',
        )
        parser.add_argument(
            '--modelo', default='logistica', choices=list(modelo.MODELOS),
        )
        parser.add_argument(
            '--limiar', type=float, default=None,
            help=(
                'Corte para virar alerta. Padrao: o do painel '
                '(settings.PAINEL_LIMIAR), para medir o que esta no ar.'
            ),
        )
        parser.add_argument('--semente', type=int, default=42)
        parser.add_argument(
            '--regra-so-dhw', action='store_true',
            help=(
                'Roda a linha de base da NOAA sem a metade do HotSpot, so com '
                'DHW >= corte. Mede quanto a regra perde quando lhe falta a '
                'informacao de que a agua ainda esta quente hoje.'
            ),
        )

    def handle(self, *args, **opcoes):
        from django.conf import settings

        locais = list(LocalRecife.objects.filter(latitude__isnull=False))
        if not locais:
            self.stderr.write(self.style.ERROR(
                'Nenhum local com coordenadas. Sem dados para avaliar.'
            ))
            return

        conjunto = dataset.montar_todos(locais, horizonte=opcoes['horizonte'])
        if conjunto.n == 0:
            self.stderr.write(self.style.ERROR(
                f'Conjunto vazio no horizonte {opcoes["horizonte"]}. '
                'Rode a ingestao antes.'
            ))
            return

        # O padrao mede **o ponto de operacao que o site usa**. Avaliar em 0,50
        # produziria numeros corretos sobre um modelo que ninguem opera.
        limiar = opcoes['limiar']
        if limiar is None:
            limiar = float(getattr(settings, 'PAINEL_LIMIAR', 0.10))

        self.stdout.write(self.style.MIGRATE_HEADING('=== CONJUNTO ==='))
        self.stdout.write(f'  {conjunto.resumo()}')
        self.stdout.write(f'  locais: {", ".join(l.slug for l in locais)}')
        self.stdout.write(f'  limiar de alerta: {limiar:.2f}')
        self.stdout.write(
            '  (!) Nenhum modelo e gravado aqui. Para gravar: treinar_final.'
        )
        self.stdout.write('')

        comparacao = modelo.comparar_com_linhas_de_base(
            conjunto, opcoes['modelo'], limiar, opcoes['semente'],
            usar_hotspot=not opcoes['regra_so_dhw'],
        )

        self.stdout.write(comparacao.resumo())
        self.stdout.write('')
        self._veredito(comparacao)

    def _veredito(self, comparacao):
        """A pergunta que o comando existe para responder, dita por extenso.

        🚨 **O veredito depende de qual metrica se escolhe, e a primeira versao
        deste metodo escolheu a errada.** Ela comparava F1 e concluia que o
        modelo perdia da persistencia (0,482 contra 0,738) — recomendando, por
        escrito, nao servir o modelo.

        Estava errado por dois motivos que se somam:

        1. **F1 e por dia**, e docs/METODOLOGIA_SIMPLES.md secao 5 ja tinha
           decidido que a unidade e o **episodio**: um evento dura semanas, e
           avisar no dia 3 de nove nao e falha.
        2. **F1 pune alarme falso**, que e exatamente o que a decisao do limiar
           (secao 22.9 de RESULTADOS) escolheu aceitar em troca de
           antecedencia. Julgar por F1 e reprovar o modelo pelo criterio que
           foi deliberadamente descartado ao escolher 0,10.

        Nos mesmos numeros: **18 de 19 episodios contra 15** — o modelo ganha
        com folga na metrica declarada, e perde na que o projeto rejeitou.

        🚨 **E havia um segundo defeito, corrigido em 30/07/2026: o piso era o
        adversario errado.** Ate aqui a unica linha de base era a persistencia,
        que copia o BAA de hoje. Faltava a que qualquer gestor tem de graca —
        **a regra publicada da NOAA**, `HotSpot >= 1 e DHW >= 4`, que sai todo
        dia no site deles. Ganhar de uma copia nao e o mesmo que ganhar do
        produto que ja existe, e enquanto so a copia era medida ninguem
        conseguia saber a diferenca. Agora o veredito julga contra o **maior**
        dos dois pisos.
        """
        avaliados = comparacao.anos_com_evento
        if not avaliados:
            self.stdout.write(self.style.WARNING(
                '  Nenhum ano com evento: nao ha o que detectar, e nenhuma '
                'metrica de alerta significa nada aqui.'
            ))
            return

        modelo_ep, total_ep, modelo_fp = comparacao.episodios('episodios_modelo')
        persist_ep, _, persist_fp = comparacao.episodios('episodios_persistencia')
        regra_ep, _, regra_fp = comparacao.episodios('episodios_regra')

        f1_modelo = sum(
            r.desempenho_modelo.f1_alerta for r in avaliados
        ) / len(avaliados)
        f1_persistencia = sum(
            r.desempenho_persistencia.f1_alerta for r in avaliados
        ) / len(avaliados)

        self.stdout.write(self.style.MIGRATE_HEADING('  Veredito'))
        self.stdout.write(
            '  episodios detectados (alarmes falsos)   <- criterio declarado'
        )
        for rotulo, detectados, falsos in (
            ('modelo      ', modelo_ep, modelo_fp),
            ('persistencia', persist_ep, persist_fp),
            ('regra NOAA  ', regra_ep, regra_fp),
        ):
            self.stdout.write(
                f'    {rotulo} : {detectados}/{total_ep}  ({falsos} falso(s))'
            )
        self.stdout.write(
            f'  F1 por dia           : modelo {f1_modelo:.3f}  |  '
            f'persistencia {f1_persistencia:.3f}'
        )
        self.stdout.write('')

        # 🚨 O piso e o MAIOR dos dois. Comparar so com a persistencia foi o
        # que fez este comando anunciar vitoria sem nunca ter medido a regra
        # que a NOAA ja publica de graca todo dia.
        piso, nome_piso = max(
            (persist_ep, 'a persistencia'), (regra_ep, 'a regra da NOAA')
        )

        if modelo_ep > piso:
            self.stdout.write(self.style.SUCCESS(
                f'  O modelo bate as duas linhas de base: pega '
                f'{modelo_ep - piso} episodio(s) a mais que {nome_piso}, '
                f'que e a mais forte.'
            ))
        elif modelo_ep == piso:
            self.stdout.write(self.style.WARNING(
                f'  Empate com {nome_piso} em episodios ({modelo_ep}/'
                f'{total_ep}). O modelo nao acrescenta deteccao — o que sobra '
                f'a favor dele e alarme falso e antecedencia, e os dois '
                f'precisam ser conferidos acima antes de mante-lo.'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'  (!) O modelo NAO bate a linha de base: '
                f'{modelo_ep}/{total_ep} contra {piso}/{total_ep} de '
                f'{nome_piso}.\n'
                f'      Isto e motivo para nao servir o modelo.'
            ))

        if regra_ep >= modelo_ep:
            self.stdout.write(
                f'\n  (!) A regra da NOAA nao e um adversario qualquer: ela e '
                f'publicada\n      diariamente e nao precisa deste projeto '
                f'para ser lida. Empatar com\n      ela em deteccao significa '
                f'que o que o modelo acrescenta e o numero\n      de '
                f'probabilidade e a antecedencia, e nao o aviso em si.'
            )

        if f1_persistencia > f1_modelo:
            # Nao e contradicao, e o preco declarado. Dizer aqui evita que
            # alguem leia a tabela acima e conclua o contrario do que foi
            # decidido.
            self.stdout.write(
                f'\n  (!) A persistencia ganha no F1 por dia, e isso e '
                f'esperado:\n'
                f'      o limiar em uso foi escolhido para privilegiar '
                f'antecedencia,\n'
                f'      aceitando mais alarme falso - e F1 pune exatamente '
                f'isso.\n'
                f'      Ver docs/RESULTADOS.md secao 22.9.'
            )

        self.stdout.write(
            '\n  (!) Estes numeros valem para o modelo que ESTE comando acabou '
            'de treinar,\n      e nao para o artefato gravado em dados/modelos/. '
            'Os dois coincidem\n      apenas se treinar_final rodou com os '
            'mesmos dados e opcoes.'
        )
