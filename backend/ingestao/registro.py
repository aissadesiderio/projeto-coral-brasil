"""Resolucao de conectores por slug e execucao da ingestao.

Cada par (fonte, local) e uma unidade independente: se uma fonte falhar, as
outras continuam e a falha fica registrada em `ExecucaoIngestao`.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from aquaculture.models import ExecucaoIngestao

from .conectores.noaa_crw import ConectorNoaaCrw
from .erros import resumir_erro
from .persistencia import gravar, preparar_medicoes, ultima_data_ingerida

logger = logging.getLogger(__name__)

CONECTORES = {
    ConectorNoaaCrw.slug: ConectorNoaaCrw,
}


def obter_conector(slug):
    if slug not in CONECTORES:
        disponiveis = ', '.join(sorted(CONECTORES))
        raise KeyError(f'Conector "{slug}" nao existe. Disponiveis: {disponiveis}')
    return CONECTORES[slug]()


def ingerir(local, inicio, fim, conector, incremental=True):
    """Executa a ingestao de uma fonte para um local e registra o resultado.

    Com `incremental`, retoma da ultima data ja gravada em vez de rebaixar a
    serie inteira. Retorna o `ExecucaoIngestao` correspondente.
    """
    if incremental:
        ultima = ultima_data_ingerida(local, conector.slug)
        if ultima and ultima >= inicio:
            inicio = ultima + timedelta(days=1)

    execucao = ExecucaoIngestao.objects.create(
        fonte=conector.slug,
        local_recife=local,
        inicio_periodo=inicio,
        fim_periodo=fim,
        status='falha',
    )

    if inicio > fim:
        execucao.status = 'sucesso'
        execucao.concluido_em = timezone.now()
        execucao.mensagem_erro = 'Nada a fazer: periodo ja ingerido.'
        execucao.save()
        return execucao

    # Rede de seguranca: o contrato manda o conector devolver
    # ResultadoColeta(erro=...) em vez de levantar, mas se algum deixar uma
    # excecao escapar, a execucao ainda precisa ficar registrada com o motivo
    # - um registro com status "falha" e mensagem vazia nao serve para nada.
    try:
        resultado = conector.coletar(local, inicio, fim)
    except Exception as exc:
        logger.warning(
            'Conector %s levantou excecao nao tratada: %s',
            conector.slug,
            resumir_erro(exc),
        )
        logger.debug('Detalhe completo', exc_info=exc)
        execucao.status = 'falha'
        execucao.mensagem_erro = (
            f'Excecao nao tratada pelo conector - {resumir_erro(exc)}'
        )
        execucao.concluido_em = timezone.now()
        execucao.save()
        return execucao

    if resultado.houve_falha:
        execucao.status = 'falha'
        execucao.mensagem_erro = resultado.erro
        execucao.concluido_em = timezone.now()
        execucao.save()
        logger.warning(
            'Ingestao %s/%s falhou: %s', conector.slug, local.slug, resultado.erro
        )
        return execucao

    medicoes, rejeitadas, recusas = preparar_medicoes(local, resultado, conector.slug)
    gravadas = gravar(medicoes)

    # A nota nao e falha - registra algo que o operador precisa saber, como o
    # periodo ter sido encolhido ate onde a fonte publica. Vai junto das
    # recusas, mas sem rebaixar o status.
    anotacoes = ([resultado.nota] if resultado.nota else []) + list(recusas)

    execucao.registros_gravados = gravadas
    execucao.registros_rejeitados = rejeitadas
    execucao.status = 'parcial' if (rejeitadas or recusas) else 'sucesso'
    execucao.mensagem_erro = '\n'.join(anotacoes)
    execucao.concluido_em = timezone.now()
    execucao.save()

    return execucao
