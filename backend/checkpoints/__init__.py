"""Retomada de trabalho interrompido, e o mapeamento do que ja foi adquirido.

Duas metades, que servem a coisas diferentes e nao devem ser confundidas:

| | Onde | Para que |
|---|---|---|
| `Checkpoint` (banco) | `aquaculture.models` | retomar de onde parou, sem reprocessar |
| manifesto (JSON) | `manifesto.py` | auditar depois o que entrou em cada resultado |

🚨 **O checkpoint e a fonte da verdade sobre o que foi TENTADO, nunca sobre o
que EXISTE.** Quem responde o que existe e o dado. Confundir os dois e o unico
jeito de esta funcionalidade causar dano: bastaria alguem apagar uma tabela
para a retomada passar a pular blocos reais para sempre. `conferir()` existe
por isso — ver a docstring de `aquaculture.models.Checkpoint`.

Uso tipico:

    from checkpoints import pendentes, registrar

    for bloco in pendentes('ingestao.noaa-crw', blocos):
        with registrar('ingestao.noaa-crw', bloco) as ponto:
            ponto.evidencia['gravadas'] = processar(bloco)
"""

from .manifesto import como_json, gravar, montar
from .nucleo import (
    TENTATIVAS_ATE_DESISTIR,
    Ponto,
    conferir,
    esgotadas,
    falhas,
    ja_concluido,
    limpar,
    marcar_falha,
    pendentes,
    registrar,
)

__all__ = [
    'TENTATIVAS_ATE_DESISTIR',
    'Ponto',
    'como_json',
    'conferir',
    'esgotadas',
    'falhas',
    'gravar',
    'ja_concluido',
    'limpar',
    'marcar_falha',
    'montar',
    'pendentes',
    'registrar',
]
