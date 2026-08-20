"""O mecanismo. A decisao de onde aplicar esta no `__init__` do pacote."""

import hashlib
import json
import logging

from django.core.cache import cache as cache_padrao
from django.db.models import Count, Max

logger = logging.getLogger(__name__)

# Prefixo de toda chave deste projeto. Existe para que um Redis compartilhado
# com outra aplicacao nao produza colisao silenciosa - o modo de falha seria
# servir o painel de outro sistema, que e absurdo o suficiente para valer os
# oito caracteres.
PREFIXO = 'coral'

# ⚠️ 24 horas, e nao "para sempre". O TTL **nao** e o mecanismo de invalidacao
# (isso e a chave), e sim um teto de memoria: cada ingestao diaria gera chaves
# novas, e sem teto as antigas ficariam ocupando o cache para sempre, ja que
# nada volta para apaga-las por nome.
SEGUNDOS_DE_VIDA = 24 * 60 * 60


def chave(*partes):
    """Uma chave estavel a partir de qualquer combinacao de valores.

    Passa por hash em vez de concatenar: `data_base`, listas de colunas e
    dicionarios de escala entrariam com espaco, dois-pontos e virgula, e o
    memcached recusa chave com espaco. O prefixo legivel fica na frente para
    que um `KEYS coral:painel:*` no Redis continue servindo para inspecao.
    """
    material = json.dumps(partes, sort_keys=True, default=str)
    digest = hashlib.sha256(material.encode('utf-8')).hexdigest()[:32]
    rotulo = str(partes[0]) if partes else 'sem-rotulo'
    return f'{PREFIXO}:{rotulo}:{digest}'


def assinatura_das_series(slugs):
    """Por local, o par (ultima data, quantas medicoes) da serie.

    🚨 **Uma consulta so para todos os locais, e nao uma por local.** A versao
    ingenua trocaria 30 ms de pandas por 8 consultas de agregacao — mais barato,
    mas ainda linear no numero de recifes, e o catalogo cresce. Aqui e uma
    agregacao agrupada, coberta pelo indice `['local_recife', 'data']`.

    ⚠️ **`COUNT` acompanha `MAX` de proposito.** Um backfill que preenche
    buraco antigo nao mexe na data maxima; sem a contagem, o painel continuaria
    servindo o resultado calculado antes do buraco ser preenchido.
    """
    from aquaculture.models import MedicaoAmbiental

    linhas = (
        MedicaoAmbiental.objects
        .filter(local_recife__slug__in=list(slugs))
        .values('local_recife__slug')
        .annotate(ultima=Max('data'), quantas=Count('id'))
    )
    return {
        linha['local_recife__slug']: (
            linha['ultima'].isoformat() if linha['ultima'] else None,
            linha['quantas'],
        )
        for linha in linhas
    }


def lembrar(nome_da_chave, calcular, backend=None):
    """Devolve o valor guardado, ou calcula e guarda.

    ⚠️ **Falha do cache nao derruba a requisicao.** Um Redis fora do ar faria
    `cache.get` levantar, e o painel — que funcionava perfeitamente sem cache
    ate ontem — passaria a responder 500 por causa de uma otimizacao. O cache
    e um atalho; quando ele quebra, o caminho longo continua valendo.
    """
    backend = backend or cache_padrao

    try:
        guardado = backend.get(nome_da_chave)
    except Exception as exc:  # pragma: no cover - depende do backend externo
        logger.warning('Cache indisponivel na leitura', extra={'erro': str(exc)})
        return calcular()

    if guardado is not None:
        return guardado

    valor = calcular()

    try:
        backend.set(nome_da_chave, valor, SEGUNDOS_DE_VIDA)
    except Exception as exc:  # pragma: no cover - depende do backend externo
        logger.warning('Cache indisponivel na escrita', extra={'erro': str(exc)})

    return valor


def esquecer(backend=None):
    """Limpa tudo. Para teste e para o operador que precisa forcar recalculo."""
    (backend or cache_padrao).clear()
