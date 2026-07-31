"""Linhas de base e as metricas que fazem sentido aqui.

**A persistencia e o piso.** Ela responde "o BAA daqui a N dias e igual ao de
hoje" e nao usa feature nenhuma. Um modelo que nao a supere nao se justifica -
e, com episodios que duram semanas (docs/VARIAVEIS.md secao 7.2), ela tende a
ser forte. Melhor descobrir isso antes de treinar do que depois.

**A regra da NOAA e o segundo piso, e ele e mais alto.** A persistencia copia o
BAA de hoje, que e categoria de 0 a 4 e nao tem meio-termo: ou ela avisa, ou
nao. A regra publicada da NOAA trabalha sobre o DHW, que e continuo - e por
isso pode ter o corte movido para trocar revocacao por precisao, coisa que a
persistencia nao permite. Comparar so com a persistencia responde "o modelo
bate uma copia?"; comparar tambem com a regra responde **"o modelo bate o que
a NOAA ja publica de graca?"**, que e a pergunta de quem opera. Ver
`prever_regra_noaa` e docs/RESULTADOS.md secao 24.

**Por que as metricas daqui nao sao acuracia.** 92% dos dias nao tem alerta.
Um modelo que sempre responde "sem alerta" acerta 92% e nao serve para nada.
`taxa_da_classe_majoritaria` existe justamente para deixar esse numero a vista,
ao lado de qualquer acuracia relatada.

**Por que ha metrica por episodio.** A amostra efetiva sao ~19 episodios em
~4 anos-evento, nao 7.173 dias: os dias dentro de um mesmo episodio sao
fortemente autocorrelacionados. Contar acerto dia a dia infla a impressao de
evidencia. `avaliar_episodios` conta o que interessa a quem le um aviso: o
evento foi detectado, e quantos alarmes falsos houve.
"""

from dataclasses import dataclass
from datetime import timedelta

from ingestao.conectores.noaa_crw import LIMIAR_ALERTA

# Folga tolerada ao agrupar dias em episodio. Uma lacuna do produto (ha 6, tres
# consecutivas) ou uma oscilacao de um dia nao deveriam partir um mesmo evento
# em dois. Mesmo criterio usado na medicao de docs/VARIAVEIS.md secao 7.2.
FOLGA_EPISODIO_DIAS = 3


def prever_persistencia(quadro):
    """A predicao da linha de base: o alvo de hoje vale para t+N."""
    return quadro['alvo_atual']


# Os dois cortes da regra publicada da NOAA para "Alerta Nivel 1", o mesmo
# patamar que `LIMIAR_ALERTA` marca no BAA:
#
#     BAA >= 3  <=>  HotSpot >= 1 °C  E  DHW >= 4 °C-semana
#
# https://coralreefwatch.noaa.gov/product/5km/  (ver docs/FONTES.md secao 6.16)
CORTE_DHW_ALERTA_1 = 4.0
CORTE_HOTSPOT_ALERTA_1 = 1.0

# Cortes de DHW varridos ao escolher o ponto de operacao da regra.
#
# ⚠️ O piso e 0,5 **para que a varredura contenha o otimo em vez de encostar
# nele**. A primeira versao comecava em 1,0 e escolhia 1,0 em todas as cinco
# dobras - um otimo na borda nao e otimo, e um sinal de que a varredura acabou
# cedo demais. Medido em 30/07/2026 sobre os 7.095 dias, com o HotSpot junto:
#
#   corte    0,00    0,25    0,50    1,00    2,00    4,00
#   F1      0,812   0,817   0,827   0,837   0,783   0,654
#
# O maximo esta mesmo em 1,0, e agora ha ponto medido dos dois lados dele.
# Ver docs/RESULTADOS.md secao 24.
CORTES_DHW = (0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0)


def prever_regra_noaa(quadro, corte_dhw=CORTE_DHW_ALERTA_1, usar_hotspot=True):
    """A regra publicada da NOAA aplicada em `t`, lida como previsao para t+N.

    Devolve serie no nivel do BAA (0 ou `LIMIAR_ALERTA`), para poder passar por
    `avaliar` e `avaliar_episodios` sem tratamento especial - o mesmo truque de
    `modelo.como_baa`.

    🚨 **Ela nao preve nada, e esse e o ponto.** A regra descreve o estado de
    hoje; usa-la como previsao de daqui a N dias e apostar que o estado nao
    muda. Se o modelo nao vencer isso, o que ele tem nao e capacidade de
    previsao - e a inercia termica do oceano, que a regra tambem tem de graca.

    ⚠️ **Ela nao reproduz o BAA do banco, e o desvio nao e defeito.** Medido em
    30/07/2026 sobre os 7.173 dias das tres series: concordancia de 0,964, com
    **0 dias** em que a regra avisa e o BAA nao, e **261 dias** em que o BAA
    avisa e a regra nao. A causa e a agregacao, decidida em
    `ingestao/conectores/noaa_crw.py`: o BAA e reduzido dos ~121 pixels da bbox
    por **maximo** (categoria ordinal), enquanto DHW e HotSpot vao por
    **media**. Um pixel quente sozinho levanta o BAA do recife sem levantar a
    media de nenhum dos dois. A regra so erra para menos, nunca para mais.

    `usar_hotspot=False` deixa so `DHW >= corte`. E a versao mais fraca, e
    existe para separar as duas metades da regra: sem o HotSpot ela dispara nos
    dias em que a agua ja esfriou mas o calor acumulado ainda nao decaiu - 479
    dias na serie, todos com HotSpot abaixo de 1.
    """
    quente = quadro['dhw_atual'] >= corte_dhw
    if usar_hotspot:
        quente = quente & (quadro['hotspot_atual'] >= CORTE_HOTSPOT_ALERTA_1)
    # `fillna(False)`: dia sem a variavel e dia em que a regra nao tem o que
    # dizer, e "nao avisar" e a resposta honesta - nao um alerta a esmo.
    return quente.fillna(False).astype(float) * LIMIAR_ALERTA


def escolher_corte_dhw(treino, cortes=CORTES_DHW, usar_hotspot=True,
                       criterio='f1_alerta'):
    """O corte de DHW que maximiza `criterio` **no conjunto de treino**.

    🚨 Escolher o corte olhando a dobra de teste seria dar a linha de base uma
    vantagem que o modelo nao tem, e o resultado sairia enviesado a favor dela.
    Quem chama precisa passar so o treino da dobra. Ver
    `modelo.comparar_com_linhas_de_base`.

    Empate resolve pelo corte **maior**: entre dois pontos que medem igual no
    treino, o mais conservador e o que produz menos alarme falso fora dele.
    """
    melhor_corte, melhor_valor = None, -1.0
    for corte in sorted(cortes):
        previsto = prever_regra_noaa(treino, corte, usar_hotspot)
        valor = getattr(avaliar(treino['alvo'], previsto), criterio)
        if valor >= melhor_valor:
            melhor_corte, melhor_valor = corte, valor
    return melhor_corte, melhor_valor


def taxa_da_classe_majoritaria(verdadeiro):
    """Acuracia de responder sempre a classe mais frequente.

    Qualquer acuracia relatada precisa vir ao lado deste numero, senao ela nao
    quer dizer nada.
    """
    if len(verdadeiro) == 0:
        return 0.0
    return float(verdadeiro.value_counts(normalize=True).max())


@dataclass(frozen=True)
class Desempenho:
    n: int
    acerto_exato: float
    erro_medio_absoluto: float
    taxa_majoritaria: float
    precisao_alerta: float
    revocacao_alerta: float
    f1_alerta: float
    verdadeiros_positivos: int
    falsos_positivos: int
    falsos_negativos: int

    def __str__(self):
        return (
            f'n={self.n}  exato={self.acerto_exato:.3f} '
            f'(classe majoritaria={self.taxa_majoritaria:.3f})  '
            f'MAE={self.erro_medio_absoluto:.3f}  '
            f'alerta: P={self.precisao_alerta:.3f} R={self.revocacao_alerta:.3f} '
            f'F1={self.f1_alerta:.3f}  (VP={self.verdadeiros_positivos} '
            f'FP={self.falsos_positivos} FN={self.falsos_negativos})'
        )


def _divisao(numerador, denominador):
    """Zero quando nao ha o que dividir - e nao NaN nem excecao.

    Precisao sem nenhum alerta previsto e revocacao sem nenhum alerta real sao
    casos reais aqui: ha anos inteiros sem evento.
    """
    return float(numerador) / denominador if denominador else 0.0


def avaliar(verdadeiro, previsto):
    """Desempenho diario. Use junto com `avaliar_episodios`, nunca sozinho."""
    n = len(verdadeiro)
    if n == 0:
        return Desempenho(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0)

    exato = float((verdadeiro == previsto).mean())
    mae = float((verdadeiro - previsto).abs().mean())

    alerta_real = verdadeiro >= LIMIAR_ALERTA
    alerta_previsto = previsto >= LIMIAR_ALERTA

    vp = int((alerta_real & alerta_previsto).sum())
    fp = int((~alerta_real & alerta_previsto).sum())
    fn = int((alerta_real & ~alerta_previsto).sum())

    precisao = _divisao(vp, vp + fp)
    revocacao = _divisao(vp, vp + fn)
    f1 = _divisao(2 * precisao * revocacao, precisao + revocacao)

    return Desempenho(
        n=n,
        acerto_exato=exato,
        erro_medio_absoluto=mae,
        taxa_majoritaria=taxa_da_classe_majoritaria(verdadeiro),
        precisao_alerta=precisao,
        revocacao_alerta=revocacao,
        f1_alerta=f1,
        verdadeiros_positivos=vp,
        falsos_positivos=fp,
        falsos_negativos=fn,
    )


def agrupar_episodios(datas, folga_dias=FOLGA_EPISODIO_DIAS):
    """Agrupa datas em episodios contiguos. Retorna lista de listas de datas."""
    datas = sorted(datas)
    if not datas:
        return []

    episodios, atual = [], [datas[0]]
    for data in datas[1:]:
        if (data - atual[-1]).days <= folga_dias:
            atual.append(data)
        else:
            episodios.append(atual)
            atual = [data]
    episodios.append(atual)
    return episodios


@dataclass(frozen=True)
class DesempenhoEpisodio:
    episodios_reais: int
    episodios_detectados: int
    episodios_falsos: int
    detalhes: list

    @property
    def taxa_deteccao(self):
        return _divisao(self.episodios_detectados, self.episodios_reais)

    def __str__(self):
        return (
            f'{self.episodios_detectados}/{self.episodios_reais} episodios '
            f'detectados ({self.taxa_deteccao:.0%}), '
            f'{self.episodios_falsos} episodio(s) de alarme falso'
        )


def _episodios_de_um_local(quadro, previsto, folga_dias, rotulo):
    alerta_real = quadro['alvo'] >= LIMIAR_ALERTA
    alerta_previsto = previsto >= LIMIAR_ALERTA

    # Indexado pela data do alvo: e o dia sobre o qual a previsao fala.
    datas_reais = list(quadro.loc[alerta_real, 'alvo_data'])
    datas_previstas = list(quadro.loc[alerta_previsto, 'alvo_data'])

    reais = agrupar_episodios(datas_reais, folga_dias)
    previstos = agrupar_episodios(datas_previstas, folga_dias)

    previstas = set(datas_previstas)
    detalhes, detectados = [], 0
    for episodio in reais:
        acertados = sum(1 for d in episodio if d in previstas)
        if acertados:
            detectados += 1
        detalhes.append(
            {
                'local': rotulo,
                'inicio': episodio[0],
                'fim': episodio[-1],
                'dias': len(episodio),
                'dias_previstos': acertados,
                'detectado': bool(acertados),
            }
        )

    reais_por_dia = set(datas_reais)
    falsos = sum(1 for ep in previstos if not any(d in reais_por_dia for d in ep))

    return len(reais), detectados, falsos, detalhes


def avaliar_episodios(quadro, previsto, folga_dias=FOLGA_EPISODIO_DIAS,
                      coluna_grupo='local'):
    """Desempenho por evento, e nao por dia.

    Um episodio real conta como detectado se **algum** dos seus dias foi
    previsto em alerta. E a pergunta certa para um sistema de aviso: errar o
    dia exato de inicio importa menos do que perder o evento inteiro.

    `episodios_falsos` sao episodios previstos que nao encostam em nenhum
    episodio real - alarme falso de verdade, nao um dia isolado a mais dentro
    de um evento que existiu.

    ⚠️ **O agrupamento e por local.** Num quadro com varios recifes as datas se
    repetem, e agrupar so por data funde episodios simultaneos de recifes
    diferentes num evento so - foi o que aconteceu na primeira execucao real,
    onde 19 episodios viraram 7. Se `coluna_grupo` nao existir no quadro, o
    calculo e feito como local unico.
    """
    if coluna_grupo in getattr(quadro, 'columns', []):
        grupos = [
            (rotulo, quadro[quadro[coluna_grupo] == rotulo])
            for rotulo in sorted(quadro[coluna_grupo].unique())
        ]
    else:
        grupos = [('', quadro)]

    reais = detectados = falsos = 0
    detalhes = []
    for rotulo, parte in grupos:
        r, d, f, det = _episodios_de_um_local(
            parte, previsto.loc[parte.index], folga_dias, rotulo
        )
        reais, detectados, falsos = reais + r, detectados + d, falsos + f
        detalhes.extend(det)

    return DesempenhoEpisodio(reais, detectados, falsos, detalhes)


def anos_disponiveis(quadro):
    return sorted({d.year for d in quadro['alvo_data']})


def dividir_deixando_um_ano_de_fora(quadro, ano):
    """Divisao temporal: um ano inteiro fora do treino.

    Divisao aleatoria seria vazamento puro numa serie temporal - dias vizinhos
    de um mesmo episodio cairiam dos dois lados. Ver docs/VARIAVEIS.md secao 4,
    regra 3, e secao 7.2 sobre o custo: com ~4 anos-evento, cada dobra remove
    perto de um quarto do sinal.
    """
    do_ano = quadro['alvo_data'].map(lambda d: d.year) == ano
    return quadro[~do_ano].copy(), quadro[do_ano].copy()


def avaliar_persistencia(conjunto):
    """Roda a linha de base sobre o conjunto inteiro. Retorna (diario, episodio)."""
    quadro = conjunto.quadro
    previsto = prever_persistencia(quadro)
    return avaliar(quadro['alvo'], previsto), avaliar_episodios(quadro, previsto)
