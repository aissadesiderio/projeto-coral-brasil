"""Auditoria: a cadeia da aquisicao ao resultado, montada a partir do que existe.

| Modulo | Papel |
|---|---|
| `codigo` | qual commit produziu isto, e se a arvore estava limpa |
| `procedencia` | fontes, locais, execucoes, retomada, modelos e **lacunas** |

Entrada pela linha de comando: `manage.py auditar`.

🚨 **Nada aqui e lido de agregado gravado.** Todo numero sai de um `COUNT` sobre
a tabela real, na hora. O projeto ja perdeu uma decisao para o defeito oposto:
uma cobertura gravada envelheceu em silencio e a tabela montada a partir dela
trocou dois episodios de lugar, decidindo o limiar de alerta. Auditoria que le
agregado audita o agregado.

⚠️ **O relatorio declara o que nao consegue afirmar.** `lacunas` nao e apendice:
sem ela, o retrato descreveria um projeto sem lacuna nenhuma.

⚠️ **`procedencia` NAO e importado aqui, e isso e deliberado.** Ele depende de
`aquaculture.models`, que exige o registro de apps do Django carregado. Como
`ml.persistencia` importa `auditoria.codigo` para carimbar o artefato, um
import ansioso de `procedencia` no pacote faria qualquer import de
`ml.persistencia` exigir Django pronto — inclusive nos caminhos que hoje
funcionam sem ele. Quem precisa do outro modulo pede por nome:

    from auditoria import procedencia   # funciona, mesmo sem estar no __init__

`codigo` fica aqui porque so usa a biblioteca padrao.
"""

from . import codigo

__all__ = ['codigo']
