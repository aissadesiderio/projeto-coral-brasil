"""Duas saidas do mesmo registro: uma para pessoa, outra para maquina.

🚨 **A escolha de formato nao e cosmetica aqui — ela decide se a auditoria e
possivel.** O pedido tem duas metades que puxam para lados opostos: alguem
precisa ler o log durante uma falha (e ai coluna alinhada e frase curta ganham)
e alguem precisa **auditar o fluxo depois**, cruzando o que foi adquirido com o
que virou resultado (e ai texto livre e inutil, porque exige regex sobre prosa).

Tentar servir os dois num formato so termina no pior dos dois: um texto quase
estruturado que quebra o parser toda vez que alguem reescreve uma mensagem.

Entao sao dois formatadores sobre **o mesmo `LogRecord`**, e nao duas chamadas
de log. O console recebe `TextoLegivel`; o arquivo recebe `JsonLinhas`. Uma
mensagem nunca existe num e falta no outro.

⚠️ **JSON Lines (um objeto por linha), e nao um array JSON.** Um array precisa
ser fechado para ser valido, e um log e um arquivo que nunca fecha — o processo
pode morrer a qualquer momento. Com JSON Lines, um arquivo truncado no meio
perde a ultima linha e continua legivel; com array, perde o arquivo inteiro.
E permite `grep` antes de `json.loads`, que e como se le log de verdade.
"""

import datetime as dt
import json
import logging

from .correlacao import mascarar

# Atributos que o `logging` poe em todo record. Tudo que sobra foi passado por
# quem chamou (via `extra=`) e entra no JSON como campo proprio - e assim
# `logger.info('...', extra={'medicoes': 406})` vira coluna auditavel sem
# precisar de nenhum registro previo do campo.
_PADRAO_DO_LOGGING = frozenset({
    'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
    'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs',
    'message', 'msg', 'name', 'pathname', 'process', 'processName',
    'relativeCreated', 'stack_info', 'thread', 'threadName', 'taskName',
    'correlacao', 'contexto',
})


class TextoLegivel(logging.Formatter):
    """Uma linha por evento, com o id do fluxo na frente.

    O id vem cedo na linha de proposito: e por ele que se filtra (`findstr
    a3f9c1d2`), e um campo que muda de coluna conforme o tamanho do nome do
    modulo nao serve para isso.
    """

    PADRAO = (
        '%(asctime)s %(levelname)-7s [%(correlacao)s] %(name)s: %(message)s'
    )

    def __init__(self, fmt=None, datefmt='%Y-%m-%d %H:%M:%S'):
        super().__init__(fmt or self.PADRAO, datefmt=datefmt)

    def format(self, record):
        linha = super().format(record)
        extras = _extras(record)
        if extras:
            juntos = ' '.join(f'{c}={v}' for c, v in sorted(extras.items()))
            linha = f'{linha} | {juntos}'
        return linha


class JsonLinhas(logging.Formatter):
    """Um objeto JSON por linha, com o contexto do fluxo achatado dentro.

    ⚠️ **`default=str` no `json.dumps` e deliberado.** Um log que levanta
    excecao ao serializar um `Decimal` ou um `date` derruba o fluxo que estava
    apenas *relatando* — o log passaria a ser fonte de falha em vez de registro
    dela. Perder a fidelidade do tipo e barato; perder a execucao nao e.
    """

    def format(self, record):
        registro = {
            'quando': dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc
            ).isoformat(),
            'nivel': record.levelname,
            'logger': record.name,
            'mensagem': record.getMessage(),
            'correlacao': getattr(record, 'correlacao', '-'),
            'arquivo': f'{record.pathname}:{record.lineno}',
            'funcao': record.funcName,
        }

        contexto = getattr(record, 'contexto', None)
        if contexto:
            registro['contexto'] = contexto

        extras = _extras(record)
        if extras:
            registro['dados'] = extras

        # 🚨 O traceback vai como texto num campo proprio, e nao concatenado na
        # mensagem: no JSON ele precisa ser um valor, senao a linha inteira
        # quebra em N linhas e deixa de ser JSON Lines.
        if record.exc_info:
            registro['erro'] = self.formatException(record.exc_info)
        elif record.exc_text:
            registro['erro'] = record.exc_text

        return json.dumps(registro, ensure_ascii=False, default=str)


def _extras(record):
    """O que quem chamou passou em `extra=`, ja mascarado."""
    achados = {
        chave: valor for chave, valor in record.__dict__.items()
        if chave not in _PADRAO_DO_LOGGING and not chave.startswith('_')
    }
    return mascarar(achados) if achados else {}
