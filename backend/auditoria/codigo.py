"""Qual versao do codigo produziu isto.

🚨 **E o elo que faltava na cadeia, e o mais caro de nao ter.** O artefato do
modelo ja gravava colunas, horizonte, `n_treino` e a versao do scikit-learn —
tudo que descreve *como* ele foi ajustado. Nao gravava **de qual codigo saiu**.
Sem isso, "reproduzir o resultado do TCC" e uma frase sem procedimento: o
mesmo comando, no mesmo banco, um mes depois, roda sobre um `dataset.montar`
que pode ter mudado de regra — e o novo numero e tao defensavel quanto o
antigo, sem nada apontando a diferenca.

Este projeto ja viveu a versao pequena desse problema: em 30/07 uma tabela do
RESULTADOS.md, montada a mao, trocou duas linhas e **decidiu o limiar do
projeto**. O antidoto foi o mesmo dos dois lados — parar de reconstruir a mao o
que o sistema pode carimbar.

⚠️ **`sujo` importa tanto quanto o hash.** Um commit identifica o codigo
versionado; se ha alteracao nao commitada na arvore, o hash sozinho e uma
afirmacao falsa — descreve um estado que nao foi o que rodou. Registrar
`sujo: true` nao conserta a reprodutibilidade, mas impede que alguem confie num
numero que nao da para reconstruir. Mesma regra da categoria da IUCN sem ano:
lacuna declarada vale mais que afirmacao errada.
"""

import functools
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[2]

# Segundos. O `git` local responde em milissegundos; o limite existe para o
# caso de um repositorio em rede ou um lock preso, onde a alternativa seria
# travar a gravacao de um modelo por causa de metadado.
LIMITE_SEGUNDOS = 5


def _git(*argumentos):
    """Roda um comando git na raiz do repositorio. `None` se nao der."""
    try:
        concluido = subprocess.run(
            ['git', *argumentos],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=LIMITE_SEGUNDOS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        # 🚨 Nunca levanta. Metadado de procedencia nao pode derrubar o treino
        # que ele so ia descrever - seria o log virando fonte de falha, o mesmo
        # defeito que `JsonLinhas` evita com `default=str`.
        logger.debug('git indisponivel: %s', exc)
        return None

    if concluido.returncode != 0:
        return None
    return concluido.stdout.strip()


@functools.lru_cache(maxsize=1)
def versao():
    """Um retrato do codigo em execucao.

    ⚠️ **Em cache para o processo inteiro.** Uma execucao nao muda de commit no
    meio; sem o cache, um treino que grava dez artefatos rodaria `git` trinta
    vezes. O cache tambem torna o valor **coerente** dentro da execucao, que
    importa mais: dois artefatos da mesma corrida nao podem sair com hashes
    diferentes so porque alguem commitou no meio.

    Chaves sempre presentes, mesmo sem git — quem le nao precisa checar
    existencia, so valor:

    | Chave | Quando e `None` |
    |---|---|
    | `commit` | fora de um repositorio git, ou git ausente |
    | `ramo` | idem, ou `HEAD` destacado |
    | `sujo` | idem (e `True`/`False` quando se sabe) |
    """
    commit = _git('rev-parse', 'HEAD')

    if commit is None:
        # Sem git nao ha o que afirmar. Devolver zeros ou 'desconhecido' como
        # se fosse valor seria fabricar procedencia - exatamente o defeito do
        # credito de imagem "Acervo local do projeto" (FONTES.md secao 2.1).
        return {
            'commit': None,
            'ramo': None,
            'sujo': None,
            'motivo': 'git indisponivel ou fora de um repositorio',
        }

    # `--porcelain` lista alteracoes nao commitadas; vazio significa arvore
    # limpa. Inclui arquivos nao rastreados de proposito: um modulo novo ainda
    # nao adicionado ao indice **participou** da execucao.
    estado = _git('status', '--porcelain')

    return {
        'commit': commit,
        'commit_curto': commit[:12],
        'ramo': _git('rev-parse', '--abbrev-ref', 'HEAD'),
        'sujo': bool(estado) if estado is not None else None,
        'arquivos_alterados': (
            len(estado.splitlines()) if estado else 0
        ) if estado is not None else None,
    }


def reproduzivel():
    """Se o estado atual permite reconstruir o resultado depois.

    Nao e o mesmo que "esta tudo bem": um resultado gerado com a arvore suja
    continua valido como medicao. So nao e **reconstruivel** a partir do
    repositorio, e quem for cita-lo precisa saber disso.
    """
    atual = versao()
    return atual['commit'] is not None and atual['sujo'] is False
