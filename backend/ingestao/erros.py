"""Resumo de erros de fontes externas para gravacao em banco.

Servidores ERDDAP respondem a falhas com uma pagina HTML inteira, e o erddapy
repassa esse HTML como mensagem da excecao. Gravar isso em
`ExecucaoIngestao.mensagem_erro` polui o banco e torna o log ilegivel - o que
importa e o tipo do erro e a primeira linha util.
"""

import re

LIMITE_CARACTERES = 400

_TAGS_HTML = re.compile(r'<[^>]+>')
_ESPACOS = re.compile(r'\s+')

# Marcadores que identificam um documento HTML de verdade.
#
# Nao basta procurar "<" e ">": o URLError do Python formata a mensagem como
# "<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] ...>", e tratar isso como
# tag apagava a causa inteira do erro, deixando so "URLError" no log - que e
# pior do que nao resumir nada.
_MARCADORES_HTML = re.compile(r'<!doctype\s+html|<html[\s>]|<body[\s>]|<head[\s>]', re.IGNORECASE)

# Linhas de boilerplate de pagina de erro que nao acrescentam informacao.
_RUIDO = re.compile(
    r'^(doctype|html|head|title|body|hr|address|meta|link)\b',
    re.IGNORECASE,
)


def parece_documento_html(texto):
    """Distingue uma pagina HTML de uma mensagem que apenas usa < e >."""
    return bool(_MARCADORES_HTML.search(texto))


def limpar_html(texto):
    """Extrai o texto util de uma resposta HTML de erro."""
    sem_tags = _TAGS_HTML.sub(' ', texto)
    linhas = [
        linha.strip()
        for linha in sem_tags.splitlines()
        if linha.strip() and not _RUIDO.match(linha.strip())
    ]
    return _ESPACOS.sub(' ', ' '.join(linhas)).strip()


def resumir_erro(exc, limite=LIMITE_CARACTERES):
    """Transforma uma excecao em uma mensagem curta e legivel.

    Preserva sempre o tipo da excecao, que costuma ser o dado mais util para
    diagnosticar (HTTPError, ConnectionError, TimeoutException...).
    """
    tipo = type(exc).__name__
    mensagem = str(exc)

    if parece_documento_html(mensagem):
        mensagem = limpar_html(mensagem)

    mensagem = _ESPACOS.sub(' ', mensagem).strip()

    if not mensagem:
        return tipo

    if len(mensagem) > limite:
        mensagem = mensagem[:limite].rstrip() + '...'

    return f'{tipo}: {mensagem}'
