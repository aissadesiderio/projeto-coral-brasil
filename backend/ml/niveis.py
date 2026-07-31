"""A escala de aviso do painel: de quanto em quanto a resposta muda de nome.

🚨 **Isto substitui o corte unico, e a substituicao resolve um dilema que o
corte unico nao tinha como resolver.** Ate 30/07/2026 havia um numero so —
`PAINEL_LIMIAR` — e escolhe-lo era escolher entre duas coisas incompativeis:

- **cobrir tudo**: o modelo detecta no maximo 18 dos 19 episodios, e so o corte
  0,05 alcanca esse teto. Qualquer valor acima abre mao, de proposito, de um
  episodio que o modelo consegue pegar — inclusive o de **nove dias** de
  Picaozinho em 2022;
- **ser levado a serio**: em 0,05, metade dos avisos e falsa e o site fica
  aceso 15,9% do tempo. Aviso que acende um dia em cada seis para de
  significar alguma coisa, e o proprio projeto ja tinha escrito isso ao decidir
  que a rotina diaria **nao fala em dia normal** (PLANEJAMENTO, 28/07).

Com uma escala, os dois objetivos deixam de competir: o degrau mais baixo
garante que nada que o modelo alcanca escape, e o mais alto carrega a
exigencia de acao. O que era um numero passa a ser **o que se espera de quem
le**.

⚠️ **Nao e o retorno do `RISCO_STATUS` legado.** Aquele tinha quatro niveis
herdados do `StatusPredicao` e **nenhum numero por tras** — foi removido em
28/07/2026. Estes tres saem da varredura de `ml/limiar.py`, e cada corte tem
precisao, cobertura e custo medidos. A diferenca entre os dois nao e de forma,
e de procedencia.

## Os cortes, e por que sao estes

Medido em 30/07/2026 sobre as predicoes fora da dobra (7.095 amostras, 3
recifes, 7 anos), com o modelo calibrado que o painel serve:

| Corte | Precisao | Episodios | 1o dia | Atraso | Falsos/ano/recife | Dias/ano aceso |
|---|---|---|---|---|---|---|
| 0,05 | 0,498 | **18/19** | 19 | 0,45 d | 27,0 | 53,7 |
| 0,20 | 0,719 | 16/19 | 16 | 1,50 d | 10,0 | 35,5 |
| 0,50 | 0,826 | 14/19 | 10 | 4,94 d | 4,5 | 25,7 |

**0,05 e o piso porque e o teto do modelo.** Nenhum corte detecta mais que 18
de 19 episodios; o unico que escapa de todos (Picaozinho, 21–23/04/2026) e
limitacao do modelo, nao da escala. Colocar o primeiro degrau acima de 0,05
seria descartar cobertura que existe.

**0,20 e o degrau de acao porque e onde a maioria dos avisos passa a ser
verdadeira** (7 em cada 10). Abaixo dali, mobilizar equipe erra quase metade
das vezes.

**0,50 e o degrau alto porque 8 em cada 10 acertam e o custo cai para 4,5 dias
de alarme falso por ano.** Em compensacao ele chega tarde — atraso medio de
quase 5 dias —, e e por isso que ele **nao** substitui os anteriores: e um
qualificador de gravidade, nao um filtro.

⚠️ **Os tres numeros vem da mesma varredura que os avalia.** Serve para
escolher entre cortes, nao como estimativa do que acontecera no ano que vem.
Mesma ressalva de docs/RESULTADOS.md secao 22.9.

## Para quem isto e escrito

O publico do alerta esta declarado em docs/VISAO_GERAL.md secao 2.1: **quem
age sobre ele** — gestao de unidade de conservacao, pesquisa de campo,
monitoramento acionavel. A escala existe porque esse publico precisa dos dois
extremos: nao perder evento **e** poder confiar no aviso que o faz sair de
casa.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Nivel:
    """Um degrau da escala: o corte, o nome, e o que se espera de quem le.

    `acao` nao e enfeite de interface. Um nivel sem acao associada e um nivel
    que cada leitor interpreta a seu modo — e a diferenca entre "observacao" e
    "alerta" so existe se ela disser coisas diferentes sobre o que fazer.
    """

    slug: str
    rotulo: str
    corte: float
    acao: str
    ordem: int

    @property
    def exige_acao(self):
        """Deste degrau para cima se espera que alguem faca alguma coisa."""
        return self.ordem >= 2


# A escala canonica. A ordem importa: `classificar` percorre de cima para
# baixo e devolve o primeiro cujo corte a probabilidade alcanca.
ESCALA = (
    Nivel(
        slug='alerta_alto',
        rotulo='Alerta alto',
        corte=0.50,
        acao='Acionar monitoramento com prioridade. Oito em cada dez avisos '
             'neste nível se confirmam.',
        ordem=3,
    ),
    Nivel(
        slug='alerta',
        rotulo='Alerta',
        corte=0.20,
        acao='Acionar monitoramento. Sete em cada dez avisos neste nível se '
             'confirmam.',
        ordem=2,
    ),
    Nivel(
        slug='observacao',
        rotulo='Observação',
        corte=0.05,
        acao='Acompanhar, sem mobilizar. Metade dos avisos neste nível não se '
             'confirma — ele existe para que nada que o modelo alcança passe '
             'despercebido.',
        ordem=1,
    ),
    Nivel(
        slug='sem_aviso',
        rotulo='Sem aviso',
        corte=0.0,
        acao='Nada a fazer.',
        ordem=0,
    ),
)


class EscalaInvalida(ValueError):
    """A escala configurada nao pode ser usada para classificar."""


def validar(escala):
    """Recusa escala malformada antes que ela classifique alguma coisa.

    🚨 Uma escala fora de ordem **nao levanta erro sozinha** — ela classifica,
    e classifica errado: `classificar` devolve o primeiro corte alcancado, e
    com os cortes embaralhados isso vira o degrau errado, em silencio, para
    sempre. E o mesmo defeito que o projeto ja pagou com cobertura gravada e
    com a tabela de episodios trocada: o dado certo, lido na ordem errada.
    """
    if not escala:
        raise EscalaInvalida('A escala esta vazia: nao ha nivel para atribuir.')

    cortes = [n.corte for n in escala]
    if cortes != sorted(cortes, reverse=True):
        raise EscalaInvalida(
            f'Os cortes precisam estar em ordem decrescente. Recebido: {cortes}. '
            f'Fora de ordem a classificacao nao falha - ela devolve o nivel '
            f'errado sem avisar.'
        )
    if len(set(cortes)) != len(cortes):
        raise EscalaInvalida(f'Ha cortes repetidos: {cortes}.')
    if escala[-1].corte > 0.0:
        raise EscalaInvalida(
            f'O ultimo nivel precisa ter corte 0.0 para receber tudo o que '
            f'ficou abaixo dos outros. Recebido: {escala[-1].corte}. Sem isso '
            f'uma probabilidade baixa nao teria nivel nenhum.'
        )
    return escala


def classificar(probabilidade, escala=None):
    """O degrau em que esta probabilidade cai.

    ⚠️ A comparacao e `>=`, e isso importa: uma probabilidade exatamente igual
    ao corte **entra** no nivel. Cortes sao promessas publicas ("avisamos a
    partir de 20%"), e um `>` faria a promessa falhar exatamente no ponto que
    ela nomeia.
    """
    escala = validar(escala or ESCALA)
    for nivel in escala:
        if probabilidade >= nivel.corte:
            return nivel
    return escala[-1]


def de_configuracao(bruto):
    """Monta uma escala a partir de uma lista de dicionarios do `settings`.

    Existe para que os cortes sejam ajustaveis sem editar codigo — eles sao
    **decisao de quem opera**, como o limiar unico era. O formato de cada item
    e `{'slug', 'rotulo', 'corte', 'acao'}`; a `ordem` sai da posicao.
    """
    if not bruto:
        return ESCALA

    niveis = []
    total = len(bruto)
    for posicao, item in enumerate(bruto):
        faltando = {'slug', 'rotulo', 'corte'} - set(item)
        if faltando:
            raise EscalaInvalida(
                f'Nivel na posicao {posicao} sem {sorted(faltando)}: {item}'
            )
        niveis.append(Nivel(
            slug=item['slug'],
            rotulo=item['rotulo'],
            corte=float(item['corte']),
            acao=item.get('acao', ''),
            ordem=total - 1 - posicao,
        ))
    return validar(tuple(niveis))


def como_payload(escala=None):
    """A escala inteira, para viajar na resposta da API.

    🚨 **Vai junto da probabilidade de proposito.** Sem a escala no payload,
    quem consome ve o nome do nivel e nao tem como saber de que corte ele veio
    — e a mesma razao pela qual o `limiar` ja viajava ao lado da
    `probabilidade` desde 27/07: quem consome precisa poder discordar do corte
    sem refazer a conta.
    """
    return [
        {
            'slug': n.slug,
            'rotulo': n.rotulo,
            'corte': n.corte,
            'acao': n.acao,
            'exige_acao': n.exige_acao,
        }
        for n in validar(escala or ESCALA)
    ]
