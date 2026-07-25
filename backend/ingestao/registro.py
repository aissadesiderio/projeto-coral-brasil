"""Resolucao de conectores por slug e execucao da ingestao.

Cada par (fonte, local) e uma unidade independente: se uma fonte falhar, as
outras continuam e a falha fica registrada em `ExecucaoIngestao`.

O periodo pedido e fatiado em blocos antes de virar requisicao. Motivo medido
em 25/07/2026: pedir 2020-2026 de uma vez (cerca de 2.400 dias x 5 variaveis x
121 pixels) fez o ERDDAP responder `ReadTimeout` e `HTTP 408` nos tres locais,
e a execucao inteira terminou com zero medicoes. Blocos tambem tornam o
backfill retomavel - cada bloco e gravado assim que chega, entao uma
interrupcao no meio nao joga fora o que ja veio.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from aquaculture.models import ExecucaoIngestao

from .base import ResultadoColeta
from .conectores.copernicus import ConectorCopernicus
from .conectores.noaa_crw import ConectorNoaaCrw
from .erros import resumir_erro
from .persistencia import gravar, preparar_medicoes, ultima_data_ingerida

logger = logging.getLogger(__name__)

CONECTORES = {
    ConectorNoaaCrw.slug: ConectorNoaaCrw,
    ConectorCopernicus.slug: ConectorCopernicus,
}

# Tamanho do bloco. 180 dias deixa cada requisicao em torno de 22 mil linhas
# para uma bbox de recife - confortavel para o ERDDAP e ainda poucos blocos
# para uma serie de seis anos.
JANELA_PADRAO_DIAS = 180

# Depois de tantos blocos seguidos falhando, parar. Sem isto, uma fonte fora do
# ar faria o backfill percorrer dezenas de blocos gastando o backoff completo
# em cada um, para no fim gravar nada.
LIMITE_FALHAS_SEGUIDAS = 3

# Quantos erros distintos guardar na mensagem da execucao. O resto vira
# contagem: uma mensagem com dezenas de blocos nao ajuda a diagnosticar.
LIMITE_ERROS_REGISTRADOS = 5


def obter_conector(slug):
    if slug not in CONECTORES:
        disponiveis = ', '.join(sorted(CONECTORES))
        raise KeyError(f'Conector "{slug}" nao existe. Disponiveis: {disponiveis}')
    return CONECTORES[slug]()


def dividir_periodo(inicio, fim, dias):
    """Fatia [inicio, fim] em blocos contiguos de no maximo `dias`."""
    if dias < 1:
        raise ValueError(f'A janela deve ter pelo menos 1 dia, recebido {dias}.')

    atual = inicio
    while atual <= fim:
        ultimo = min(atual + timedelta(days=dias - 1), fim)
        yield atual, ultimo
        atual = ultimo + timedelta(days=1)


def _coletar_bloco(conector, local, inicio, fim):
    """Coleta um bloco, convertendo excecao escapada em ResultadoColeta.

    Rede de seguranca: o contrato manda o conector devolver
    `ResultadoColeta(erro=...)` em vez de levantar, mas se algum deixar uma
    excecao escapar, o bloco ainda precisa virar falha registrada - e nao
    derrubar os outros blocos junto.
    """
    try:
        return conector.coletar(local, inicio, fim)
    except Exception as exc:
        logger.warning(
            'Conector %s levantou excecao nao tratada: %s',
            conector.slug,
            resumir_erro(exc),
        )
        logger.debug('Detalhe completo', exc_info=exc)
        return ResultadoColeta(
            erro=f'Excecao nao tratada pelo conector - {resumir_erro(exc)}'
        )


def _sem_repetir(itens):
    """Remove duplicatas preservando a ordem.

    A mesma observacao ("periodo encolhido") sai de varios blocos; repeti-la
    quatorze vezes na mensagem so atrapalha a leitura.
    """
    vistos = []
    for item in itens:
        if item and item not in vistos:
            vistos.append(item)
    return vistos


def ingerir(local, inicio, fim, conector, incremental=True, janela_dias=None,
            progresso=None):
    """Executa a ingestao de uma fonte para um local e registra o resultado.

    Com `incremental`, retoma da ultima data ja gravada em vez de rebaixar a
    serie inteira. `progresso` e chamado com uma linha de texto ao fim de cada
    bloco - um backfill de anos leva minutos, e silencio nesse tempo parece
    travamento. Retorna o `ExecucaoIngestao` correspondente.
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

    janela = janela_dias or getattr(
        settings, 'INGESTAO_JANELA_DIAS', JANELA_PADRAO_DIAS
    )
    blocos = list(dividir_periodo(inicio, fim, janela))

    total_gravado = 0
    total_rejeitado = 0
    notas, recusas_totais, erros = [], [], []
    falhas_seguidas = 0
    nao_tentados = 0

    for numero, (bloco_inicio, bloco_fim) in enumerate(blocos, start=1):
        rotulo = f'{bloco_inicio} a {bloco_fim}'
        resultado = _coletar_bloco(conector, local, bloco_inicio, bloco_fim)

        if resultado.houve_falha:
            falhas_seguidas += 1
            erros.append(f'[{rotulo}] {resultado.erro}')
            logger.warning(
                'Ingestao %s/%s falhou no bloco %s: %s',
                conector.slug, local.slug, rotulo, resultado.erro,
            )
            if progresso:
                progresso(f'bloco {numero}/{len(blocos)} ({rotulo}): falhou')

            if falhas_seguidas >= LIMITE_FALHAS_SEGUIDAS:
                nao_tentados = len(blocos) - numero
                break
            continue

        falhas_seguidas = 0
        medicoes, rejeitadas, recusas = preparar_medicoes(
            local, resultado, conector.slug
        )
        # Gravar por bloco, e nao no fim: um backfill longo interrompido no
        # meio preserva o que ja chegou, e a proxima execucao incremental
        # retoma dali.
        gravadas = gravar(medicoes)

        total_gravado += gravadas
        total_rejeitado += rejeitadas
        notas.append(resultado.nota)
        recusas_totais.extend(recusas)

        if progresso:
            progresso(
                f'bloco {numero}/{len(blocos)} ({rotulo}): {gravadas} medicoes'
            )

    if nao_tentados:
        erros.append(
            f'Interrompido apos {LIMITE_FALHAS_SEGUIDAS} blocos seguidos com '
            f'falha - {nao_tentados} blocos nao foram tentados. Rode de novo '
            'sem --completo para retomar de onde parou.'
        )

    resumo_erros = _sem_repetir(erros)
    if len(resumo_erros) > LIMITE_ERROS_REGISTRADOS:
        ocultos = len(resumo_erros) - LIMITE_ERROS_REGISTRADOS
        resumo_erros = resumo_erros[:LIMITE_ERROS_REGISTRADOS]
        resumo_erros.append(f'(+{ocultos} outros blocos com falha)')

    if erros and total_gravado == 0:
        execucao.status = 'falha'
    elif erros or total_rejeitado or recusas_totais:
        execucao.status = 'parcial'
    else:
        execucao.status = 'sucesso'

    execucao.registros_gravados = total_gravado
    execucao.registros_rejeitados = total_rejeitado
    execucao.mensagem_erro = '\n'.join(
        _sem_repetir(notas) + _sem_repetir(recusas_totais) + resumo_erros
    )
    execucao.concluido_em = timezone.now()
    execucao.save()

    return execucao
