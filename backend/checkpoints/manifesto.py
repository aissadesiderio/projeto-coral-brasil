"""O mapeamento em JSON do que foi adquirido — a metade legivel por maquina.

O checkpoint no banco serve a retomada. O manifesto serve a **auditoria**: e o
arquivo que acompanha um resultado publicado e responde, sem acesso ao banco,
"de onde veio cada pedaco disto".

⚠️ **Nao e um segundo lugar onde a verdade mora.** O manifesto e sempre gerado
a partir dos checkpoints, nunca editado a mao e nunca lido de volta pelo
sistema — se fosse, seria mais um estado para divergir do banco, e este projeto
ja tem a licao gravada: um valor calculado na leitura vira indistinguivel de
dado real depois de escrito em arquivo (FONTES.md secao 2.1).

Ele e saida. Sempre.
"""

import json
from collections import Counter

from django.utils import timezone

from aquaculture.models import Checkpoint

# Versao do formato. Um manifesto guardado ao lado de um resultado de 2026
# precisa continuar interpretavel quando o formato mudar — sem o campo, a
# unica saida seria adivinhar pelo conteudo.
VERSAO_FORMATO = 1


def montar(tarefa=None):
    """O manifesto como dicionario.

    Sem `tarefa`, cobre todas — util para o retrato geral; com `tarefa`, so
    aquela, que e o caso de anexar a um resultado especifico.
    """
    consulta = Checkpoint.objects.all()
    if tarefa:
        consulta = consulta.filter(tarefa=tarefa)

    registros = list(consulta.order_by('tarefa', 'unidade'))

    por_status = Counter(registro.status for registro in registros)

    # A soma da evidencia so faz sentido sobre o que concluiu: somar a
    # evidencia parcial de uma unidade que falhou no meio produziria um total
    # que nao corresponde a nada.
    totais = Counter()
    for registro in registros:
        if registro.status != Checkpoint.CONCLUIDO:
            continue
        for chave, valor in (registro.evidencia or {}).items():
            if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                totais[chave] += valor

    return {
        'versao_formato': VERSAO_FORMATO,
        'gerado_em': timezone.now().isoformat(),
        'tarefa': tarefa or '(todas)',
        'resumo': {
            'unidades': len(registros),
            'por_status': dict(sorted(por_status.items())),
            'totais_da_evidencia': dict(sorted(totais.items())),
        },
        'unidades': [
            {
                'tarefa': registro.tarefa,
                'unidade': registro.unidade,
                'status': registro.status,
                'tentativas': registro.tentativas,
                'evidencia': registro.evidencia or {},
                'correlacao': registro.correlacao or None,
                'concluido_em': (
                    registro.concluido_em.isoformat()
                    if registro.concluido_em else None
                ),
                # 🚨 O erro entra no manifesto de proposito. Um manifesto que
                # lista so o que deu certo descreve um pipeline que nunca
                # falhou — e nenhum pipeline e assim. O que se audita e o
                # conjunto, incluindo o que ficou de fora e por que.
                'erro': registro.erro or None,
            }
            for registro in registros
        ],
    }


def como_json(tarefa=None, indentado=True):
    return json.dumps(
        montar(tarefa),
        ensure_ascii=False,
        indent=2 if indentado else None,
        default=str,
    )


def gravar(caminho, tarefa=None):
    """Escreve o manifesto em disco e devolve o caminho."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(como_json(tarefa), encoding='utf-8')
    return caminho
