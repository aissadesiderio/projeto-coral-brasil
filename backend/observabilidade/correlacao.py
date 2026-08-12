"""O fio que liga as linhas de log de um mesmo fluxo.

🚨 **Sem isto, "log ponta a ponta" nao existe — existe log embaralhado.** Uma
unica execucao de `manage.py atualizar` percorre 2 fontes x 10 locais x N
blocos de 180 dias, e cada camada (conector, normalizacao, qualidade,
persistencia) escreve suas proprias linhas. Num arquivo unico, isso sai
intercalado: a linha que diz "406 medicoes rejeitadas" nao tem como ser ligada
ao bloco que a produziu, e o diagnostico vira arqueologia por horario.

O `correlacao` resolve isso com um identificador que **acompanha o fluxo em vez
de ser repetido a mao em cada mensagem**. Quem abre o fluxo carimba uma vez; as
camadas de baixo nao sabem que ele existe e mesmo assim aparecem com ele.

⚠️ **`contextvars`, e nao variavel de modulo, por um motivo concreto.** Uma
variavel global vaza entre execucoes: dois `ingerir` em paralelo (ou dois testes
seguidos) veriam o contexto um do outro. `ContextVar` isola por contexto de
execucao e por thread, e o `token` devolvido no `set` garante que sair do
`with` restaura exatamente o que havia antes — inclusive em aninhamento.

Exemplo trabalhado, que e o caso real de `registro.ingerir`:

    with contexto(fluxo='ingestao', fonte='noaa-crw', local='abrolhos-ba'):
        # id gerado aqui, ex.: 'a3f9c1d20b74'
        with contexto(bloco='2020-01-01 a 2020-06-28'):
            logger.warning('ERDDAP respondeu 408')
            # sai com correlacao=a3f9c1d20b74 e o bloco junto

A linha gravada carrega os quatro campos sem que `qualidade.py` — que nem
importa este modulo — precise saber de nenhum deles.
"""

import contextlib
import contextvars
import uuid

# 🚨 `default` precisa ser imutavel. Um dicionario como default seria
# compartilhado por todos os contextos que nunca chamaram `set`, e uma escrita
# nele vazaria para todo o processo. `None` forca a copia explicita em
# `contexto()`.
_CONTEXTO = contextvars.ContextVar('coral_contexto', default=None)

# Quantos caracteres do uuid4. 12 hex = 48 bits: colisao so importaria se dois
# fluxos concorrentes caissem no mesmo id dentro da mesma janela de log, e a
# probabilidade disso e desprezivel para a escala deste projeto. O que 12
# ganha e caber na linha do console sem quebrar a leitura.
TAMANHO_ID = 12

# Campos que nunca entram no log, venham de onde vierem. A lista e por
# **substring** e sem diferenciar maiuscula: `DATABASE_URL` carrega a senha do
# Postgres embutida, e `NEO4J_PASSWORD` viria mascarado so se o nome fosse
# comparado exatamente.
#
# ⚠️ Isto e uma rede de seguranca, nao uma licenca. O lugar certo de nao vazar
# credencial e nao passa-la ao log; esta lista existe porque "ninguem vai
# logar senha" e uma afirmacao sobre pessoas, e o log e escrito por codigo que
# vai ser alterado por outras pessoas depois.
TERMOS_SENSIVEIS = (
    'senha', 'password', 'secret', 'token', 'chave', 'key',
    'credential', 'credencial', 'authorization', 'database_url',
)

MASCARA = '***'


def novo_id():
    """Um identificador curto para um fluxo."""
    return uuid.uuid4().hex[:TAMANHO_ID]


def contexto_atual():
    """O contexto vigente, sempre como dicionario novo.

    ⚠️ Devolve **copia**. Quem chama nao pode alterar o contexto de quem esta
    acima na pilha por acidente — que e exatamente o tipo de defeito que so
    aparece com concorrencia e nunca no teste.
    """
    atual = _CONTEXTO.get()
    return dict(atual) if atual else {}


def correlacao_atual():
    """O id do fluxo em curso, ou `None` fora de qualquer fluxo."""
    return contexto_atual().get('correlacao')


def _e_sensivel(nome):
    minusculo = str(nome).lower()
    return any(termo in minusculo for termo in TERMOS_SENSIVEIS)


def mascarar(campos):
    """Substitui por `***` o valor de toda chave de nome suspeito."""
    return {
        chave: (MASCARA if _e_sensivel(chave) else valor)
        for chave, valor in campos.items()
    }


@contextlib.contextmanager
def contexto(**campos):
    """Abre um escopo de log com os campos dados.

    Gera `correlacao` se ainda nao houver uma — o fluxo mais externo carimba,
    os de dentro herdam. Passar `correlacao=` explicitamente permite continuar
    um fluxo que comecou em outro processo (o caso de uma rotina do cron que
    quer ser ligada a execucao anterior).

    ⚠️ **Campo com valor `None` e descartado**, e nao gravado como nulo. Um
    `local=None` na linha do log se le como "houve um local e ele era vazio",
    quando o que houve foi uma coleta global sem local nenhum. Ausencia e
    ausencia.
    """
    herdado = contexto_atual()
    novo = dict(herdado)
    novo.update(
        {chave: valor for chave, valor in campos.items() if valor is not None}
    )
    novo.setdefault('correlacao', novo_id())

    token = _CONTEXTO.set(mascarar(novo))
    try:
        yield novo['correlacao']
    finally:
        _CONTEXTO.reset(token)


class FiltroCorrelacao:
    """Injeta o contexto vigente em cada `LogRecord`.

    🚨 **E um filtro, e nao um adapter ou um logger proprio, de proposito.**
    Filtro ligado ao *handler* alcanca toda linha que passa por ele — inclusive
    as do Django, do `urllib3` e de qualquer biblioteca de terceiros. Um
    `LoggerAdapter` alcancaria so quem se lembrasse de usa-lo, e "ponta a
    ponta" cairia justamente nas pontas que nao sao nossas.

    Nao filtra nada: devolve sempre `True`. O nome vem da API do `logging`, que
    usa o mesmo gancho para enriquecer e para descartar.
    """

    def filter(self, record):  # noqa: A003 - nome exigido pela API do logging
        atual = contexto_atual()
        record.correlacao = atual.get('correlacao', '-')
        record.contexto = {
            chave: valor for chave, valor in atual.items()
            if chave != 'correlacao'
        }
        return True
