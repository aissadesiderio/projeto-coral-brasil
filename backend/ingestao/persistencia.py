"""Gravacao idempotente das medicoes.

O `carregar_historico.py` fazia `StatusPredicao.objects.all().delete()` antes
de cada carga. Numa ingestao diaria isso e inviavel: uma falha no meio deixa o
banco vazio, e nao ha como ingerir so o delta.

Aqui a gravacao usa upsert sobre a constraint
(local_recife, data, variavel, fonte): rodar duas vezes o mesmo periodo
atualiza os mesmos registros em vez de duplicar ou apagar.
"""

from aquaculture.models import MedicaoAmbiental

from .normalizacao import ColunaRecusada, normalizar
from .qualidade import validar

CAMPOS_ATUALIZAVEIS = [
    'valor',
    'unidade',
    'dataset_id',
    'quality_flag',
    'observacao',
    'data_coleta',
]


def preparar_medicoes(local, resultado, fonte):
    """Normaliza e valida as observacoes brutas de um conector.

    Retorna (medicoes, rejeitadas, recusas). `rejeitadas` sao valores que
    falharam na validacao fisica - eles **ainda sao gravados**, com valor nulo
    e o motivo, para que a lacuna fique rastreavel em vez de silenciosa.
    """
    medicoes = []
    rejeitadas = 0
    recusas = []

    for obs in resultado.observacoes:
        try:
            normalizado = normalizar(obs.coluna, obs.valor)
        except ColunaRecusada as exc:
            recusas.append(str(exc))
            continue

        if normalizado is None:
            continue

        checado = validar(
            normalizado.variavel,
            normalizado.valor,
            normalizado.quality_flag,
            normalizado.observacao,
        )
        if not checado.aprovado:
            rejeitadas += 1

        medicoes.append(
            MedicaoAmbiental(
                local_recife=local,
                data=obs.data,
                variavel=normalizado.variavel,
                valor=checado.valor,
                unidade=normalizado.unidade,
                fonte=fonte,
                dataset_id=resultado.dataset_id,
                quality_flag=checado.quality_flag,
                observacao=checado.observacao,
            )
        )

    return medicoes, rejeitadas, recusas


def gravar(medicoes):
    """Upsert idempotente. Retorna a quantidade de registros processados."""
    if not medicoes:
        return 0

    MedicaoAmbiental.objects.bulk_create(
        medicoes,
        update_conflicts=True,
        unique_fields=['local_recife', 'data', 'variavel', 'fonte'],
        update_fields=CAMPOS_ATUALIZAVEIS,
        batch_size=500,
    )
    return len(medicoes)


def ultima_data_ingerida(local, fonte):
    """Data mais recente ja gravada para (local, fonte).

    Permite buscar so o delta em vez de rebaixar a serie inteira a cada
    execucao. Retorna None se nunca houve ingestao.
    """
    ultima = (
        MedicaoAmbiental.objects.filter(local_recife=local, fonte=fonte)
        .order_by('-data')
        .values_list('data', flat=True)
        .first()
    )
    return ultima
