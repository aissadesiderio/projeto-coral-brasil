"""Log, correlacao e auditoria — o rastro de ponta a ponta do projeto.

O que cada modulo resolve:

| Modulo | Papel |
|---|---|
| `correlacao` | o id que liga as linhas de um mesmo fluxo, e o mascaramento de credencial |
| `formatadores` | a mesma linha em texto (console) e em JSON Lines (arquivo) |
| `config` | monta o `LOGGING` do Django a partir do ambiente |
| `middleware` | abre um fluxo por requisicao HTTP e devolve o id no cabecalho |

Uso normal, em qualquer modulo do backend:

    import logging
    from observabilidade import contexto

    logger = logging.getLogger(__name__)

    with contexto(fluxo='ingestao', fonte='noaa-crw', local=local.slug):
        logger.info('Coleta iniciada', extra={'bloco': rotulo})

⚠️ **`extra=` e o que torna a linha auditavel.** Numero embutido na frase
(`f'{n} medicoes'`) so volta a ser numero por regex; em `extra={'medicoes': n}`
ele vira campo no JSON e pode ser somado depois sem ninguem reprocessar prosa.
"""

from .correlacao import (
    contexto,
    contexto_atual,
    correlacao_atual,
    mascarar,
    novo_id,
)

__all__ = [
    'contexto',
    'contexto_atual',
    'correlacao_atual',
    'mascarar',
    'novo_id',
]
