"""O que a atualizacao diaria precisa saber sobre o proprio envelhecimento.

🚨 **A decisao mais importante deste modulo e o que ele NAO faz: retreinar.**

A tentacao obvia numa rotina diaria e encadear ingestao + retreino + projecao,
deixando tudo sempre fresco. O projeto inteiro diz para nao fazer isso:

> Um modelo que muda toda noite e um modelo que **ninguem mediu**. O
> `treinar_final` grava sem avaliar de proposito — a avaliacao e o
> `treinar_modelo`, que roda leave-year-out. Encadear o primeiro num cron
> substituiria, todo dia, um modelo medido por um modelo nao medido, e o site
> passaria a servir probabilidades de procedencia desconhecida.

E o mesmo raciocinio que fez a calibracao ser medida antes de exibir, e o
limiar ser declarado antes de avisar.

**Entao o modelo envelhece.** A escolha aqui nao e evitar isso — e **tornar
visivel**. A rotina mede a defasagem e a reporta; retreinar continua sendo um
ato deliberado, precedido de medicao.

⚠️ A alternativa honesta seria retreinar **e medir** na mesma rotina, so
promovendo o artefato novo se ele nao piorar. Isso e possivel e nao foi feito:
exige um criterio de promocao que ninguem definiu ainda, e um criterio errado e
pior que nenhum. Fica registrado como caminho, nao como pendencia esquecida.
"""

from dataclasses import dataclass
from datetime import date

# A partir de quantos dias a defasagem do modelo deixa de ser normal.
#
# ⚠️ Nao ha nada de sagrado em 90. O raciocinio: a serie ganha 3 amostras por
# dia sobre uma base de 7.095, entao 90 dias sao ~270 amostras (3,8%) — pouco
# para mover coeficientes. O que 90 dias **podem** trazer e um evento novo, e e
# isso que justifica reavaliar. Ajuste com motivo, e nao por gosto.
DIAS_ATE_MODELO_VELHO = 90

# A partir de quantos dias sem dado novo a ingestao esta claramente parada.
#
# As duas fontes tem latencia propria: o CRW publica com ~1 dia, o Copernicus
# com alguns. Tres dias e o normal observado; sete significa que algo quebrou e
# ninguem percebeu.
DIAS_ATE_INGESTAO_PARADA = 7


@dataclass(frozen=True)
class Estado:
    """Retrato do que envelheceu, e quanto."""

    fim_da_serie: object = None
    dias_desde_ultima_medicao: int = 0
    medicoes: int = 0
    modelo: str = ''
    modelo_treinado_em: object = None
    dias_desde_o_treino: int = 0

    @property
    def ingestao_parada(self):
        return self.dias_desde_ultima_medicao >= DIAS_ATE_INGESTAO_PARADA

    @property
    def modelo_velho(self):
        return self.dias_desde_o_treino >= DIAS_ATE_MODELO_VELHO

    @property
    def saudavel(self):
        return not self.ingestao_parada and not self.modelo_velho


def _dias(inicio, fim):
    if not inicio or not fim:
        return 0
    return max((fim - inicio).days, 0)


def medir(hoje=None, nome_modelo=None):
    """Le o banco e o artefato, e devolve o retrato do envelhecimento.

    ⚠️ Nao levanta quando o modelo nao existe: um servidor recem-provisionado
    esta nesse estado, e a rotina precisa **relatar** isso em vez de morrer —
    a ingestao do dia ainda vale a pena.
    """
    from django.conf import settings
    from django.db.models import Count, Max

    from aquaculture.models import MedicaoAmbiental
    from ml import persistencia

    hoje = hoje or date.today()
    resumo = MedicaoAmbiental.objects.aggregate(
        fim=Max('data'), n=Count('id')
    )
    fim = resumo['fim']

    nome = nome_modelo or getattr(settings, 'PAINEL_MODELO', 'entrega1_baa')
    treinado_em = None
    try:
        metadados = persistencia.ler_metadados(nome)
        bruto = metadados.get('gerado_em')
        if bruto:
            treinado_em = date.fromisoformat(bruto)
    except Exception:  # noqa: BLE001 - ausencia e um estado, nao um erro
        nome = f'{nome} (ausente)'

    return Estado(
        fim_da_serie=fim,
        dias_desde_ultima_medicao=_dias(fim, hoje),
        medicoes=resumo['n'] or 0,
        modelo=nome,
        modelo_treinado_em=treinado_em,
        dias_desde_o_treino=_dias(treinado_em, hoje),
    )


def recados(estado):
    """As frases que quem opera precisa ler, e nenhuma a mais.

    Silencio quando esta tudo bem e deliberado: uma rotina diaria que sempre
    imprime aviso treina quem a le a ignorar todos.
    """
    saida = []

    if estado.medicoes == 0:
        saida.append(
            'O banco esta vazio. Rode "manage.py ingerir --completo" antes de '
            'esperar qualquer coisa do site.'
        )
        return saida

    if estado.ingestao_parada:
        saida.append(
            f'A serie nao recebe dado ha {estado.dias_desde_ultima_medicao} '
            f'dias (ultimo: {estado.fim_da_serie}). O normal observado e ate 3. '
            f'Confira se a fonte respondeu: "manage.py testar_fontes".'
        )

    if estado.modelo_treinado_em is None:
        saida.append(
            'Nao ha modelo utilizavel no disco. O painel de risco responde 503 '
            'ate alguem rodar "manage.py treinar_final".'
        )
    elif estado.modelo_velho:
        saida.append(
            f'O modelo foi treinado ha {estado.dias_desde_o_treino} dias, sobre '
            f'dados ate {estado.modelo_treinado_em}. Isto nao e erro — o '
            f'retreino e deliberado de proposito. Mas vale medir antes de '
            f'decidir: "manage.py treinar_modelo" avalia, "treinar_final" grava.'
        )

    return saida
