"""Reconstroi os artefatos derivados e valida o resultado.

O passo que faltava para publicar. Sai com codigo 1 na primeira falha.
"""

import sys
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Reconstroi modelo, grafo e documentacao, e confere o resultado.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sem-grafo', action='store_true',
            help='Pula a projecao do Neo4j (ambiente que so serve a API).',
        )
        parser.add_argument(
            '--sem-docs', action='store_true',
            help='Pula a exportacao dos .docx.',
        )

    def handle(self, *args, **opcoes):
        from db import deploy

        pular = []
        if opcoes['sem_grafo']:
            pular.append('grafo')
        if opcoes['sem_docs']:
            pular.append('documentacao')

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Preparando o deploy: reconstruindo o que nao viaja no git'
        ))
        self.stdout.write('')

        inicio = time.monotonic()
        resultado = deploy.executar(pular=pular, ao_progredir=self._progresso)
        duracao = time.monotonic() - inicio

        self.stdout.write('')

        if not resultado.ok:
            self._relatar_falha(resultado)
            sys.exit(1)

        self._conferir_artefatos(deploy)
        self._resumo(resultado, duracao)

    # --- saida ------------------------------------------------------------

    def _progresso(self, passo, estado):
        if estado == 'iniciando':
            self.stdout.write(f'  -> {passo.nome} ({passo.comando})')
        elif estado == 'ok':
            self.stdout.write(self.style.SUCCESS(f'     ok: {passo.nome}'))
        elif estado == 'pulado':
            self.stdout.write(self.style.WARNING(
                f'  -- {passo.nome} pulado a pedido. {passo.motivo}'
            ))
        elif estado == 'falhou':
            self.stdout.write(self.style.ERROR(f'     FALHOU: {passo.nome}'))

    def _relatar_falha(self, resultado):
        falha = resultado.falhou
        self.stdout.write(self.style.ERROR(
            f'Interrompido em "{falha.passo.nome}".'
        ))
        self.stdout.write(f'  comando: manage.py {falha.passo.comando}')
        self.stdout.write(f'  erro:    {type(falha.erro).__name__}: {falha.erro}')
        self.stdout.write('')
        self.stdout.write(f'  Por que este passo existe: {falha.passo.motivo}')

        sugestao = self._sugestao(falha)
        if sugestao:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(sugestao))
        self.stdout.write(self.style.ERROR(
            '\n  Nada foi publicado. Um site meio construido e pior que um '
            'que nao sobe:\n  ele parece ter funcionado.'
        ))

    def _sugestao(self, falha):
        """Sugestao ligada ao **erro**, e nunca so ao passo.

        🚨 A primeira versao disto imprimia "o banco nao tem serie suficiente"
        para qualquer falha nos passos `modelo` e `grafo`. Na primeira execucao
        real o erro foi um `UnicodeEncodeError`, e a mensagem mandou rodar a
        ingestao — que nao tinha nada a ver.

        E a mesma licao que o projeto ja aprendeu com o CDS: **o codigo do erro
        nao e o diagnostico, o texto dele e.** Palpite errado com aparencia de
        certeza custa mais do que palpite nenhum.
        """
        erro = falha.erro
        texto = str(erro).lower()
        nome = type(erro).__name__

        if nome == 'UnicodeEncodeError' or 'charmap' in texto:
            return (
                '  Erro de codificacao ao imprimir, nao de dados. O console do\n'
                '  Windows usa cp1252 e nao aceita emoji nem travessao.\n'
                '  Rode com: set PYTHONIOENCODING=utf-8'
            )

        vazio = any(t in texto for t in (
            'vazio', 'nenhum local', 'sem serie', 'conjunto vazio',
            '0 amostras', 'nao ha medicao',
        ))
        if vazio:
            return (
                '  O banco nao tem serie suficiente. Rode a ingestao antes:\n'
                '    python backend/manage.py ingerir --backfill'
            )

        if nome in ('ServiceUnavailable', 'AuthError') or 'neo4j' in texto:
            return (
                '  O Neo4j nao respondeu. Suba com "docker compose up -d", ou\n'
                '  siga sem grafo com --sem-grafo (o site perde os endpoints\n'
                '  de grafo, e nada mais).'
            )

        # Sem palpite. Melhor silencio que direcao errada.
        return None

    def _conferir_artefatos(self, deploy):
        """O comando terminar sem erro nao prova que o artefato existe."""
        self.stdout.write(self.style.MIGRATE_HEADING('  Artefatos no disco'))
        for nome, ok, detalhe in deploy.conferir_artefatos():
            linha = f'  [{"ok  " if ok else "FALHA"}] {nome} - {detalhe}'
            self.stdout.write(linha if ok else self.style.ERROR(linha))
            if not ok:
                sys.exit(1)

    def _resumo(self, resultado, duracao):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'  {len(resultado.executados)} passo(s) em {duracao:.1f}s. '
            f'Pronto para publicar.'
        ))
        if resultado.pulados:
            nomes = ', '.join(p.nome for p in resultado.pulados)
            self.stdout.write(self.style.WARNING(
                f'  Pulados: {nomes}. O site subira sem eles.'
            ))
        self.stdout.write('')
