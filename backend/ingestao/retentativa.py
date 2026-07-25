"""Retentativa para falhas transitorias de fontes externas.

Nem toda falha merece nova tentativa, e tratar todas igual e errado dos dois
lados: insistir num certificado invalido so gasta tempo, e desistir de um 503
joga fora um dado que estaria disponivel trinta segundos depois.

O caso que motivou o modulo (25/07/2026, rede da faculdade):

    HTTPError: Error { code=503; message="Service Unavailable: There was a
    (temporary?) problem. Wait a minute, then try again." }

O proprio ERDDAP diz o que fazer. Um pipeline que roda por cron nao pode
depender de alguem ler essa frase e reexecutar o comando na mao.
"""

import logging
import re
import time

logger = logging.getLogger(__name__)

TENTATIVAS_PADRAO = 3
ESPERA_INICIAL_S = 10.0
FATOR_BACKOFF = 3.0

# Status HTTP em que o servidor admite que o problema e dele e passageiro.
# 429 e 408 entram porque tambem descrevem "tente de novo", nao "nao pode".
STATUS_TRANSITORIOS = frozenset({408, 425, 429, 500, 502, 503, 504})

# Extrai o status de mensagens de erro de bibliotecas diferentes. Padroes
# fechados de proposito: um `\d{3}` solto casaria com qualquer numero na
# mensagem e faria o modulo decidir por coincidencia.
_CODIGO_HTTP = re.compile(
    r'(?:\bcode\s*=\s*|\bHTTP(?:/[\d.]+)?\s+|\bstatus(?:[ _]code)?[\s=:]+)(\d{3})\b',
    re.IGNORECASE,
)

# Falhas que nao mudam de resposta por esperar: o certificado continua
# invalido, a permissao continua negada, o dataset continua nao existindo.
_DEFINITIVO = re.compile(
    r'certificate|\bssl\b|forbidden|unauthorized|not found|no permission|'
    r'authentication|invalid credential',
    re.IGNORECASE,
)

_TRANSITORIO = re.compile(
    r'timed out|timeout|connection reset|connection aborted|remote end closed|'
    r'temporarily unavailable|service unavailable|bad gateway|'
    r'gateway time-?out|too many requests|try again',
    re.IGNORECASE,
)

_TIPOS_TRANSITORIOS = (ConnectionError, TimeoutError)


def _status_http(exc):
    """Descobre o status HTTP da excecao, se houver."""
    resposta = getattr(exc, 'response', None)
    status = getattr(resposta, 'status_code', None) or getattr(resposta, 'status', None)
    if isinstance(status, int):
        return status

    # urllib.error.HTTPError guarda o status em `code`.
    codigo = getattr(exc, 'code', None)
    if isinstance(codigo, int) and 100 <= codigo < 600:
        return codigo

    encontrado = _CODIGO_HTTP.search(str(exc))
    return int(encontrado.group(1)) if encontrado else None


def e_transitorio(exc):
    """Decide se vale a pena tentar de novo.

    A ordem importa. O status HTTP e a evidencia mais forte e decide sozinho -
    inclusive para *negar* a retentativa, porque um 403 embrulhado em
    `ConnectionError` continua sendo um 403. So quando nao ha status a decisao
    cai no texto e, por ultimo, no tipo da excecao.
    """
    status = _status_http(exc)
    if status is not None:
        return status in STATUS_TRANSITORIOS

    mensagem = str(exc)
    if _DEFINITIVO.search(mensagem):
        return False
    if _TRANSITORIO.search(mensagem):
        return True

    return isinstance(exc, _TIPOS_TRANSITORIOS)


def executar_com_retentativa(
    funcao,
    tentativas=TENTATIVAS_PADRAO,
    espera_inicial=ESPERA_INICIAL_S,
    fator=FATOR_BACKOFF,
    dormir=time.sleep,
    rotulo='fonte externa',
):
    """Executa `funcao`, repetindo enquanto a falha parecer passageira.

    A excecao original sobe intacta quando as tentativas acabam ou quando a
    falha e definitiva - quem chama continua vendo a causa real, nao um erro
    inventado por este modulo.

    `dormir` e injetavel para que os testes nao esperem de verdade.
    """
    if tentativas < 1:
        raise ValueError(f'tentativas deve ser >= 1, recebido {tentativas}')

    for tentativa in range(1, tentativas + 1):
        try:
            return funcao()
        except Exception as exc:
            if tentativa == tentativas or not e_transitorio(exc):
                raise

            espera = espera_inicial * (fator ** (tentativa - 1))
            logger.warning(
                '%s: falha passageira na tentativa %d/%d (%s). '
                'Nova tentativa em %.0fs.',
                rotulo,
                tentativa,
                tentativas,
                type(exc).__name__,
                espera,
            )
            dormir(espera)
