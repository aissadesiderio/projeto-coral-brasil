"""Registrar o que ja foi feito, para nao refazer — e para saber o que falta.

O modelo e a decisao de desenho estao documentados em
`aquaculture.models.Checkpoint`. Aqui esta o uso.

Padrao normal, num laco que percorre unidades:

    from checkpoints import pendentes, registrar

    for bloco in pendentes('ingestao.noaa-crw', todos_os_blocos):
        with registrar('ingestao.noaa-crw', bloco) as ponto:
            gravadas = coletar_e_gravar(bloco)
            ponto.evidencia['gravadas'] = gravadas

Saida limpa do `with` marca `concluido`. Excecao marca `falhou`, guarda o erro
e **relanca** — o checkpoint registra a falha, nao a engole.

⚠️ **`registrar` supõe autocommit, que e o modo em que a ingestao roda.** Dentro
de um `transaction.atomic()` que depois faz rollback, o registro da falha vai
embora junto com o resto — o que e coerente (nada aconteceu, nada foi
registrado), mas nao e o que alguem espera ao ler "o checkpoint grava a falha".
Se um dia uma tarefa precisar registrar falha sobrevivendo ao rollback, isso
exige `transaction.atomic(durable=...)` ou uma conexao separada, e nao esta
feito aqui porque nenhuma tarefa atual precisa.
"""

import contextlib
import logging

from django.db import transaction
from django.utils import timezone

from aquaculture.models import Checkpoint
from observabilidade import contexto, correlacao_atual

logger = logging.getLogger(__name__)

# Depois de tantas tentativas, a unidade para de ser "tenta de novo" e vira
# "olha isto". 🚨 O numero existe para que a retomada nao vire laco infinito
# contra uma fonte que nunca vai responder — o mesmo raciocinio do
# `LIMITE_FALHAS_SEGUIDAS` da ingestao, mas persistido entre execucoes: aquele
# esquece a cada execucao, este lembra.
TENTATIVAS_ATE_DESISTIR = 5


class Ponto:
    """O checkpoint em aberto, entregue ao corpo do `with`.

    `evidencia` e um dicionario para preencher durante o trabalho. Fica no
    objeto, e nao no retorno, porque o corpo do `with` nao tem como devolver
    valor para o gerenciador.
    """

    def __init__(self, registro):
        self.registro = registro
        self.evidencia = dict(registro.evidencia or {})

    @property
    def tentativas(self):
        return self.registro.tentativas

    @property
    def unidade(self):
        return self.registro.unidade


def ja_concluido(tarefa, unidade):
    """Se esta unidade ja foi feita com sucesso alguma vez."""
    return Checkpoint.objects.filter(
        tarefa=tarefa, unidade=str(unidade), status=Checkpoint.CONCLUIDO,
    ).exists()


def pendentes(tarefa, unidades, incluir_esgotadas=False):
    """Filtra a lista, deixando so o que ainda precisa ser processado.

    🚨 **Preserva a ordem recebida.** A ingestao pede blocos em ordem
    cronologica de proposito — `ultima_data_ingerida` depende de a serie
    crescer pela ponta. Devolver um `set` aqui quebraria isso de um jeito que
    so apareceria como buraco na serie, semanas depois.

    Por padrao **exclui** as unidades que ja esgotaram `TENTATIVAS_ATE_DESISTIR`:
    e o "tratar somente estas excecoes" — depois de cinco tentativas contra a
    mesma parede, repetir de novo nao e retomada, e desperdicio com aparencia
    de esforco. Elas continuam listadas em `esgotadas()`.
    """
    chaves = [str(unidade) for unidade in unidades]

    concluidas = set(
        Checkpoint.objects.filter(
            tarefa=tarefa, unidade__in=chaves, status=Checkpoint.CONCLUIDO,
        ).values_list('unidade', flat=True)
    )

    esgotadas = set()
    if not incluir_esgotadas:
        esgotadas = set(
            Checkpoint.objects.filter(
                tarefa=tarefa, unidade__in=chaves,
                tentativas__gte=TENTATIVAS_ATE_DESISTIR,
            )
            .exclude(status=Checkpoint.CONCLUIDO)
            .values_list('unidade', flat=True)
        )

    return [
        unidade for unidade, chave in zip(unidades, chaves)
        if chave not in concluidas and chave not in esgotadas
    ]


def esgotadas(tarefa):
    """As unidades que falharam tantas vezes que pararam de ser tentadas."""
    return Checkpoint.objects.filter(
        tarefa=tarefa, tentativas__gte=TENTATIVAS_ATE_DESISTIR,
    ).exclude(status=Checkpoint.CONCLUIDO)


def falhas(tarefa):
    """Tudo que nao concluiu — inclui o interrompido, nao so o que deu erro."""
    return Checkpoint.objects.filter(tarefa=tarefa).exclude(
        status=Checkpoint.CONCLUIDO
    )


@contextlib.contextmanager
def registrar(tarefa, unidade, correlacao=None):
    """Abre um checkpoint, fecha como concluido ou falhou.

    ⚠️ **A tentativa e contada na entrada, e nao na saida.** Se fosse contada
    ao falhar, uma queda dura (kill, falta de energia) nao incrementaria nada —
    e a unidade que derruba o processo toda vez seria tentada para sempre, que
    e o caso exato em que desistir importa.
    """
    chave = str(unidade)
    identificador = correlacao or correlacao_atual() or ''

    registro, _ = Checkpoint.objects.get_or_create(
        tarefa=tarefa, unidade=chave,
    )
    Checkpoint.objects.filter(pk=registro.pk).update(
        status=Checkpoint.EM_ANDAMENTO,
        tentativas=registro.tentativas + 1,
        correlacao=identificador,
        erro='',
    )
    registro.refresh_from_db()

    ponto = Ponto(registro)

    with contexto(checkpoint=chave, tentativa=registro.tentativas):
        try:
            yield ponto
        except Exception as exc:
            Checkpoint.objects.filter(pk=registro.pk).update(
                status=Checkpoint.FALHOU,
                erro=f'{type(exc).__name__}: {exc}'[:2000],
                evidencia=ponto.evidencia,
            )
            logger.warning(
                'Checkpoint falhou',
                extra={
                    'tarefa': tarefa,
                    'tentativas': registro.tentativas,
                },
            )
            # Relanca: registrar a falha nao e trata-la. Quem chamou decide se
            # segue para a proxima unidade ou aborta.
            raise
        else:
            Checkpoint.objects.filter(pk=registro.pk).update(
                status=Checkpoint.CONCLUIDO,
                concluido_em=timezone.now(),
                evidencia=ponto.evidencia,
                erro='',
            )
            logger.info(
                'Checkpoint concluido',
                extra={'tarefa': tarefa, **ponto.evidencia},
            )


def marcar_falha(tarefa, unidade, erro, evidencia=None):
    """Registra falha sem levantar excecao.

    Existe para o caso da ingestao, onde o contrato do conector **e** devolver
    `ResultadoColeta(erro=...)` em vez de levantar. Forcar uma excecao ali so
    para alimentar o `registrar` inverteria o desenho: o codigo passaria a
    levantar para poder registrar, que e o rabo abanando o cachorro.
    """
    chave = str(unidade)
    registro, _ = Checkpoint.objects.get_or_create(tarefa=tarefa, unidade=chave)
    Checkpoint.objects.filter(pk=registro.pk).update(
        status=Checkpoint.FALHOU,
        tentativas=registro.tentativas + 1,
        erro=str(erro)[:2000],
        evidencia=evidencia or {},
        correlacao=correlacao_atual() or '',
    )


def limpar(tarefa, unidades=None):
    """Apaga checkpoints para forcar reprocessamento.

    E o `--completo` do lado da retomada: sem isto, corrigir um defeito no
    tratamento de um bloco nao teria efeito nenhum, porque o bloco ja estaria
    marcado como concluido e seria pulado para sempre.
    """
    consulta = Checkpoint.objects.filter(tarefa=tarefa)
    if unidades is not None:
        consulta = consulta.filter(unidade__in=[str(u) for u in unidades])
    with transaction.atomic():
        return consulta.delete()[0]


def conferir(tarefa, verificador):
    """Cruza cada checkpoint concluido com a realidade, e devolve as divergencias.

    🚨 **A funcao que impede o checkpoint de virar mentira durável.**

    Um checkpoint afirma "esta unidade rendeu 406 medicoes". Se alguem apagar a
    tabela, rodar um `limpar` no banco ou restaurar um backup antigo, a
    afirmacao continua gravada e a proxima execucao **pula a unidade**. O
    buraco vira permanente, e invisivel — porque o mecanismo criado para nao
    reprocessar e exatamente o que impede de notar.

    `verificador(checkpoint)` recebe o registro e devolve o que a realidade diz
    (um dicionario), ou `None` se nao souber conferir aquela unidade. A
    comparacao e feita so sobre as chaves que o verificador devolve — ele nao
    precisa conhecer toda a evidencia.

    Devolve uma lista de `(checkpoint, esperado, encontrado)`. Lista vazia
    significa que tudo que os checkpoints afirmam continua verdade.
    """
    divergencias = []
    concluidos = Checkpoint.objects.filter(
        tarefa=tarefa, status=Checkpoint.CONCLUIDO,
    )

    for registro in concluidos:
        real = verificador(registro)
        if real is None:
            continue

        esperado = {
            chave: (registro.evidencia or {}).get(chave) for chave in real
        }
        if esperado != real:
            divergencias.append((registro, esperado, real))
            logger.error(
                'Checkpoint diverge da realidade',
                extra={
                    'tarefa': tarefa,
                    'unidade': registro.unidade,
                    'afirmado': esperado,
                    'encontrado': real,
                },
            )

    return divergencias
