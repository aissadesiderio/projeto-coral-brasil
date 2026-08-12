"""Abre um fluxo de log por requisicao HTTP.

A ingestao e o treino comecam num comando, e ali quem abre o `contexto` e o
proprio comando. A API nao tem esse ponto: cada requisicao entra pelo Django, e
sem um gancho aqui as linhas gravadas durante um `GET /api/painel-risco/`
sairiam sem correlacao nenhuma — o unico fluxo do sistema fora do rastro.

⚠️ **O identificador volta no cabecalho `X-Correlacao`.** E o que torna o log
util para quem esta do lado de fora: um erro relatado por quem usa o site vem
com o id, e o id encontra a linha. Sem devolver, a unica ancora seria o
horario aproximado informado por quem viu a tela.
"""

import logging
import time

from .correlacao import contexto

logger = logging.getLogger(__name__)

CABECALHO = 'X-Correlacao'

# Cabecalho aceito na entrada, para que um proxy ou o proprio frontend possam
# propagar um id ja existente em vez de comecar outro.
CABECALHO_ENTRADA = 'HTTP_X_CORRELACAO'

# Rotas que nao geram linha de log. `/admin/jsi18n/` e os estaticos sao ruido
# de alto volume e valor nulo para auditoria de dado.
IGNORADAS = ('/static/', '/media/', '/admin/jsi18n/')

# A partir de quantos milissegundos a requisicao vira WARNING em vez de INFO.
# 🚨 Nao e um alarme de performance: e o gancho de "gargalo" pedido junto com o
# cache. Sem medir onde demora, cachear e adivinhar.
LIMITE_LENTA_MS = 1000


class CorrelacaoMiddleware:
    """Envolve a requisicao num contexto de log e mede quanto ela levou."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, requisicao):
        if requisicao.path.startswith(IGNORADAS):
            return self.get_response(requisicao)

        recebido = requisicao.META.get(CABECALHO_ENTRADA) or None

        with contexto(
            fluxo='http',
            metodo=requisicao.method,
            rota=requisicao.path,
            correlacao=recebido,
        ) as identificador:
            comeco = time.perf_counter()
            try:
                resposta = self.get_response(requisicao)
            except Exception:
                # ⚠️ Registra e **relanca**. Engolir aqui transformaria um 500
                # com traceback num 200 vazio; o papel deste bloco e garantir
                # que a falha entre no arquivo com a mesma correlacao da
                # requisicao, nao tratar a falha.
                decorrido = (time.perf_counter() - comeco) * 1000
                logger.exception(
                    'Requisicao levantou excecao',
                    extra={'duracao_ms': round(decorrido, 1)},
                )
                raise

            decorrido = (time.perf_counter() - comeco) * 1000
            resposta[CABECALHO] = identificador

            nivel = logging.INFO
            if resposta.status_code >= 500 or decorrido >= LIMITE_LENTA_MS:
                nivel = logging.WARNING

            logger.log(
                nivel,
                'Requisicao concluida',
                extra={
                    'status': resposta.status_code,
                    'duracao_ms': round(decorrido, 1),
                },
            )
            return resposta
