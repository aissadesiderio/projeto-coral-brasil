"""O retrato auditavel do acervo: da aquisicao ao resultado, com as lacunas.

    manage.py auditar                    # o retrato em texto
    manage.py auditar --json auditoria.json
    manage.py auditar --so-lacunas       # so o que nao da para afirmar

🚨 **Existe para ser anexado, nao so lido.** O pedido de rigor cientifico
significa que um resultado publicado precisa vir acompanhado de "de onde veio
cada pedaco disto" — e esse documento nao pode ser escrito a mao no fim do
trabalho. Este projeto ja provou o custo disso duas vezes: uma tabela do
RESULTADOS.md montada a mao trocou dois episodios de lugar e decidiu o limiar
de alerta; e uma cobertura de dataset **gravada** envelheceu em silencio.

⚠️ **Sai com codigo 1 quando ha lacuna que impede citacao.** Nao e alarmismo:
serve para o agendador. Um relatorio que sempre sai com 0 e um relatorio que
nunca e lido — mesma razao pela qual `manage.py atualizar` fica calado em dia
normal e o `neo4j_projetar` virou `CommandError`.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from auditoria import codigo, procedencia

# Lacunas que impedem uma afirmacao de ser publicada como esta, e por isso
# mudam o codigo de saida. As demais (medicao degradada, conferencia vencida)
# sao estado normal de um acervo vivo: aparecem no relatorio sem derrubar nada.
LACUNAS_QUE_BLOQUEIAM = frozenset({
    'checkpoint_esgotado',
    'ingestao_falhou',
    'codigo_nao_reproduzivel',
})


class Command(BaseCommand):
    help = (
        'Retrato auditavel: fontes, cobertura, execucoes, modelos e o que o '
        'acervo ainda nao consegue sustentar.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--json', dest='caminho_json',
            help='Grava o retrato completo em JSON no caminho dado.',
        )
        parser.add_argument(
            '--so-lacunas', action='store_true',
            help='Mostra apenas o que nao pode ser afirmado.',
        )
        parser.add_argument(
            '--sem-modelos', action='store_true',
            help='Nao le os artefatos do disco (mais rapido).',
        )

    def handle(self, *args, **opcoes):
        retrato = procedencia.montar(incluir_modelos=not opcoes['sem_modelos'])

        if opcoes['caminho_json']:
            destino = Path(opcoes['caminho_json'])
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(
                json.dumps(retrato, indent=2, ensure_ascii=False, default=str),
                encoding='utf-8',
            )
            self.stdout.write(self.style.SUCCESS(f'Retrato gravado em {destino}'))

        if not opcoes['so_lacunas']:
            self._codigo(retrato)
            self._fontes(retrato)
            self._locais(retrato)
            self._modelos(retrato)

        bloqueiam = self._lacunas(retrato)
        self._veredito(retrato, bloqueiam)

        if bloqueiam:
            # Codigo 1: o unico canal que um agendador entende.
            raise SystemExit(1)

    def _codigo(self, retrato):
        estado = retrato['codigo']
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Codigo'))
        if estado['commit'] is None:
            self.stdout.write(
                f'  sem git: {estado.get("motivo", "motivo nao registrado")}'
            )
            self.stdout.write(
                '  Nenhum resultado gerado agora e reconstruivel a partir do '
                'repositorio.'
            )
            return

        sujo = ' (ARVORE ALTERADA)' if estado['sujo'] else ''
        self.stdout.write(
            f'  {estado["commit_curto"]} em {estado["ramo"]}{sujo}'
        )
        if estado['sujo']:
            self.stdout.write(
                f'  {estado["arquivos_alterados"]} arquivo(s) fora do commit - '
                'o hash acima nao descreve o que rodou.'
            )

    def _fontes(self, retrato):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Fontes ({len(retrato["fontes"])})'
        ))
        for item in retrato['fontes']:
            dataset = f' / {item["dataset_id"]}' if item['dataset_id'] else ''
            self.stdout.write(f'  {item["fonte"]}{dataset}')
            self.stdout.write(
                f'    {item["medicoes"]:,} medicoes'
                f' | {item["periodo"]["inicio"]} a {item["periodo"]["fim"]}'
                f' | {item["variaveis_distintas"]} variavel(is)'
                f' | {item["locais_cobertos"]} local(is)'
            )
            qualidade = ', '.join(
                f'{flag}: {n:,}' for flag, n in item['por_qualidade'].items()
            )
            self.stdout.write(f'    qualidade: {qualidade}')

    def _locais(self, retrato):
        resumo = retrato['resumo']
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Locais ({resumo["locais_com_serie"]}/'
            f'{resumo["locais_cadastrados"]} com serie)'
        ))
        for item in retrato['locais']:
            if item['medicoes']:
                periodo = item['periodo']
                self.stdout.write(
                    f'  {item["slug"]}: {item["medicoes"]:,} medicoes '
                    f'({periodo["inicio"]} a {periodo["fim"]})'
                )
            else:
                motivo = (
                    'sem coordenadas' if not item['tem_coordenadas']
                    else 'com coordenadas, sem serie'
                )
                self.stdout.write(f'  {item["slug"]}: nenhuma medicao - {motivo}')

    def _modelos(self, retrato):
        modelos = retrato.get('modelos')
        if modelos is None:
            return

        self.stdout.write('')
        if isinstance(modelos, dict) and 'erro' in modelos:
            self.stdout.write(self.style.MIGRATE_HEADING('Modelos'))
            self.stdout.write(f'  nao foi possivel ler: {modelos["erro"]}')
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f'Modelos ({len(modelos)})'))
        for item in modelos:
            self.stdout.write(
                f'  {item.get("nome")} ({item.get("modelo")})'
                f' - gerado em {item.get("gerado_em")}'
            )
            do_codigo = item.get('codigo') or {}
            if do_codigo.get('commit_curto'):
                sujo = ' (arvore alterada)' if do_codigo.get('sujo') else ''
                self.stdout.write(f'    codigo: {do_codigo["commit_curto"]}{sujo}')
            else:
                # 🚨 Artefato anterior a 13/08/2026 nao tem o carimbo. Nao e
                # defeito de leitura: e um artefato que nao da para reproduzir,
                # e dizer isso e melhor que omitir a linha.
                self.stdout.write(
                    '    codigo: nao registrado - artefato anterior ao '
                    'carimbo de versao, nao reproduzivel'
                )
            self.stdout.write(
                f'    treino: {item.get("n_treino")} amostras, '
                f'{item.get("positivos_treino")} positivas'
            )

    def _lacunas(self, retrato):
        lacunas = retrato['lacunas']
        self.stdout.write('')
        if not lacunas:
            self.stdout.write(self.style.SUCCESS(
                'Nenhuma lacuna registrada: tudo que este acervo contem pode '
                'ser citado com procedencia.'
            ))
            return []

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'O que NAO da para afirmar ({len(lacunas)})'
        ))
        bloqueiam = []
        for item in lacunas:
            bloqueia = item['tipo'] in LACUNAS_QUE_BLOQUEIAM
            if bloqueia:
                bloqueiam.append(item)
            marca = 'BLOQUEIA' if bloqueia else 'ressalva'
            self.stdout.write(
                f'  [{marca}] {item["tipo"]}: {item["quantos"]}'
            )
            self.stdout.write(f'    {item["consequencia"]}')
            quais = item.get('quais')
            if quais:
                mostrados = quais[:5]
                self.stdout.write(f'    {", ".join(str(q) for q in mostrados)}')
                if len(quais) > len(mostrados):
                    self.stdout.write(f'    (+{len(quais) - len(mostrados)} outros)')
        return bloqueiam

    def _veredito(self, retrato, bloqueiam):
        resumo = retrato['resumo']
        self.stdout.write('')
        self.stdout.write(
            f'  {resumo["medicoes"]:,} medicoes de {resumo["fontes"]} fonte(s), '
            f'{resumo["locais_com_serie"]}/{resumo["locais_cadastrados"]} '
            f'locais com serie.'
        )

        if not bloqueiam:
            if codigo.reproduzivel():
                self.stdout.write(self.style.SUCCESS(
                    '  Estado publicavel: o retrato acima reconstroi de onde '
                    'veio cada numero.'
                ))
            return

        self.stdout.write(self.style.ERROR(
            f'  {len(bloqueiam)} lacuna(s) impedem citar este estado como '
            'esta. Detalhe acima.'
        ))
