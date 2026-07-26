"""Entrega 2, passo 1: branqueamento **observado**, com as termicas do proprio GCBD.

A entrega 1 previa o BAA - um rotulo que a propria NOAA calcula a partir de
temperatura. Perguntar ali "variaveis nao termicas ajudam?" era circular: o
alvo era termico por construcao. Aqui o alvo e **coral branqueado contado por
mergulhador**, e a pergunta deixa de ser circular.

Este modulo faz o passo 1 do plano de docs/GCBD.md: usar so as variaveis
termicas que ja vem no arquivo, **sem ingerir nada**, para medir quanto do
branqueamento observado no Brasil o sinal termico sozinho explica.

Tres decisoes aqui nao sao obvias e foram medidas antes de virar codigo:

**1. A unidade amostral e a visita, nao a linha.** O GCBD traz uma linha por
substrato (`Hard Coral`, `Nutrient Indicator Algae`, ...) da mesma visita. As
313 linhas brasileiras utilizaveis sao **166 visitas**, e dentro de cada visita
as termicas e o `Percent_Bleaching` sao **identicos** - conferido: 0 de 166
visitas divergem no alvo. Tratar linha como amostra inflaria n em 1,9x sem
acrescentar informacao, e colocaria copias da mesma visita nos dois lados de
qualquer divisao de validacao. Ver `agregar_por_visita`.

**2. Metade das colunas termicas e climatologia do sitio, nao condicao do dia.**
`TSA_Mean`, `SSTA_Maximum`, `*_Standard_Deviation`, `*Max`, `*Mean` sao
constantes dentro de um sitio: descrevem o lugar, nao a visita. Sao features
legitimas sob validacao agrupada por sitio, mas respondem outra pergunta - "este
recife e termicamente instavel?" em vez de "fez calor antes desta visita?".
Ficam separadas em `CLIMATOLOGIA_DO_SITIO` para que a distincao seja explicita.

**3. `ClimSST` tem sentinela.** Vale exatamente 262,15 K (= -11 C) em **115 dos
313 registros brasileiros**. Nao e climatologia, e ausencia codificada como
numero. docs/GCBD.md recomendava `ClimSST` como uma das tres variaveis do
baseline; a recomendacao nao sobrevive a medicao. Ver `SENTINELAS`.

**Por que a validacao e agrupada.** Sao 166 visitas em 119 sitios, varias delas
no mesmo recife em anos diferentes. Divisao aleatoria poria o mesmo sitio nos
dois lados, e como a climatologia do sitio e constante, o modelo poderia
reconhece-lo em vez de aprender o fenomeno. Ver `validar`.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

# O arquivo nao e versionado (16 MB, reconstruivel pelo DOI - ver docs/GCBD.md).
# A raiz do projeto e tres niveis acima deste arquivo: backend/ml/gcbd.py.
RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_PADRAO = RAIZ / 'dados' / 'global_bleaching_environmental.csv'
VARIAVEL_DE_AMBIENTE = 'GCBD_CSV'

PAIS_PADRAO = 'Brazil'

# ---------------------------------------------------------------------------
# O alvo
# ---------------------------------------------------------------------------

COLUNA_ALVO = 'Percent_Bleaching'

# **O limiar e declarado, nunca implicito.** `Percent_Bleaching` e percentual;
# transforma-lo em sim/nao e uma escolha, e docs/GCBD.md exigia que ela
# aparecesse. Zero e o padrao porque separa "algum branqueamento foi visto" de
# "nenhum", que e a distincao que o mergulhador registrou.
#
# A escolha nao e cosmetica: > 0% da 53% de positivos, > 10% da 15%. Mas
# tambem nao e artificial - dos 88 positivos, so 2 tem menos de 0,1%, e a
# mediana deles e 5%. O equilibrio de classes e real, nao efeito do limiar.
LIMIAR_BRANQUEAMENTO = 0.0

# ---------------------------------------------------------------------------
# As colunas
# ---------------------------------------------------------------------------

# Variam de visita para visita no mesmo sitio: sao a condicao do dia.
TERMICAS_DO_DIA = (
    'Temperature_Kelvin',   # SST na data da observacao
    'SSTA',                 # anomalia de SST
    'SSTA_Frequency',
    'SSTA_DHW',
    'TSA',                  # anomalia de estresse termico
    'TSA_Frequency',
    'TSA_DHW',              # o DHW da NOAA, o acumulador de 12 semanas
    'Windspeed',
)

# Constantes dentro de cada sitio: descrevem o lugar, nao a visita.
CLIMATOLOGIA_DO_SITIO = (
    'Temperature_Mean',
    'Temperature_Minimum',
    'Temperature_Maximum',
    'Temperature_Kelvin_Standard_Deviation',
    'SSTA_Standard_Deviation',
    'SSTA_Minimum',
    'SSTA_Maximum',
    'SSTA_Frequency_Standard_Deviation',
    'SSTA_FrequencyMax',
    'SSTA_FrequencyMean',
    'SSTA_DHW_Standard_Deviation',
    'SSTA_DHWMax',
    'SSTA_DHWMean',
    'TSA_Standard_Deviation',
    'TSA_Minimum',
    'TSA_Maximum',
    'TSA_Mean',
    'TSA_Frequency_Standard_Deviation',
    'TSA_FrequencyMax',
    'TSA_FrequencyMean',
    'TSA_DHW_Standard_Deviation',
    'TSA_DHWMax',
    'TSA_DHWMean',
)

# Contexto do sitio que nao e termico. `Exposure` e texto e fica de fora do
# padrao - codifica-la exigiria decidir uma ordem entre 'Exposed', 'Sheltered'
# e 'Sometimes', e isso e escolha de modelagem, nao de carregamento.
CONTEXTO_DO_SITIO = (
    'Depth_m',
    'Distance_to_Shore',
    'Turbidity',
    'Cyclone_Frequency',
)

# Colunas que o arquivo tem mas que nao servem, com o motivo medido.
COLUNAS_RECUSADAS = {
    'ClimSST': (
        'vale 262,15 K (= -11 C) em 115 dos 313 registros brasileiros: e '
        'ausencia codificada como numero, nao climatologia. Ver SENTINELAS.'
    ),
    'SSTA_Mean': (
        'constante em 0,0 no recorte brasileiro inteiro. Uma coluna sem '
        'variancia nao pode informar nada, e ainda ocupa um grau de liberdade.'
    ),
}

# Valor que o GCBD usa no lugar de "sem dado" - vira NaN no carregamento.
# 262,15 K sao exatamente -11 C, o que denuncia a origem: um -11 em Celsius
# convertido para Kelvin sem que ninguem notasse que -11 era o codigo de falta.
SENTINELAS = {'ClimSST': 262.15}

# **O padrao e o conjunto inteiro, de proposito.** As oito termicas do dia sao
# o que o GCBD oferece, sem escolha nossa - e a versao que pode ser relatada
# sem ressalva de selecao.
FEATURES_PADRAO = TERMICAS_DO_DIA

# O conjunto reduzido, motivado por colinearidade **diagnosticada**, nao por
# procura de metrica:
#
#   SSTA_Frequency x TSA_Frequency   r = 0,881   (VIF 11,7 e 7,9)
#   Temperature_Kelvin x TSA         r = 0,881   (VIF 5,3 e 9,6)
#   SSTA_DHW x TSA_DHW               r = 0,693
#
# Com as oito, quatro coeficientes saem invertidos - `SSTA` em -0,58 diz que
# anomalia quente de SST *protege* o coral, o que e fisicamente falso. Com
# estas tres, nenhum inverte: TSA_DHW +0,95 (estresse acumulado piora), TSA
# +0,21 (anomalia do dia piora), Windspeed -0,36 (vento mistura a coluna
# d'agua e resfria - negativo aqui e o esperado, nao inversao).
#
# ⚠️ **As metricas desta versao sao otimistas.** O conjunto foi escolhido
# olhando a mesma validacao que o avalia; sobre 166 visitas isso e vies real.
# Ver docs/RESULTADOS.md secao 12.
FEATURES_INTERPRETAVEIS = ('TSA_DHW', 'TSA', 'Windspeed')

# Limiar de DHW da propria NOAA para Alerta Nivel 1 - a regra publicada, que e
# a linha de base honesta aqui. Equivale a persistencia da entrega 1: se o
# modelo nao superar a regra que ja existe, ele nao se justifica.
LIMIAR_DHW_NOAA = 4.0
COLUNA_DHW = 'TSA_DHW'


class ArquivoAusente(FileNotFoundError):
    """O CSV do GCBD nao esta onde deveria."""


def caminho_do_csv(caminho=None):
    """Resolve o caminho: argumento, depois `GCBD_CSV`, depois `dados/`."""
    if caminho:
        return Path(caminho)
    do_ambiente = os.environ.get(VARIAVEL_DE_AMBIENTE)
    return Path(do_ambiente) if do_ambiente else CAMINHO_PADRAO


def carregar(caminho=None, pais=PAIS_PADRAO):
    """Le o CSV e devolve o recorte do pais, com o alvo ja numerico.

    Nao agrega nem filtra coluna: devolve as linhas cruas do recorte, para que
    `agregar_por_visita` possa ser testada em separado.
    """
    import pandas as pd

    arquivo = caminho_do_csv(caminho)
    if not arquivo.exists():
        raise ArquivoAusente(
            f'{arquivo} nao existe. O arquivo do GCBD nao e versionado (16 MB). '
            f'Baixe pelo DOI registrado em docs/GCBD.md e coloque em '
            f'{CAMINHO_PADRAO}, ou aponte {VARIAVEL_DE_AMBIENTE} para ele.'
        )

    quadro = pd.read_csv(arquivo, low_memory=False)
    if pais:
        do_pais = quadro['Country_Name'].astype(str).str.strip() == pais
        quadro = quadro[do_pais].copy()

    quadro[COLUNA_ALVO] = pd.to_numeric(quadro[COLUNA_ALVO], errors='coerce')
    return quadro[quadro[COLUNA_ALVO].notna()].copy()


def limpar_sentinelas(quadro):
    """Troca os valores-sentinela por NaN. Devolve (quadro, contagem por coluna)."""
    import numpy as np
    import pandas as pd

    quadro = quadro.copy()
    trocados = {}
    for coluna, sentinela in SENTINELAS.items():
        if coluna not in quadro.columns:
            continue
        valores = pd.to_numeric(quadro[coluna], errors='coerce')
        atingidos = valores == sentinela
        if atingidos.any():
            trocados[coluna] = int(atingidos.sum())
        quadro[coluna] = valores.where(~atingidos, np.nan)
    return quadro, trocados


def agregar_por_visita(quadro):
    """Uma linha por (sitio, data). **A decisao mais importante do modulo.**

    O GCBD traz uma linha por substrato amostrado na visita. Elas repetem as
    mesmas termicas e o mesmo `Percent_Bleaching` - foi conferido no recorte
    brasileiro: **0 de 166 visitas divergem no alvo**.

    A agregacao usa `max` no alvo e `first` no resto. `max` e a escolha certa
    mesmo empatando hoje: se um dia duas linhas divergirem, "houve branqueamento
    nesta visita" e a pergunta, e ela e respondida pelo maior valor observado -
    a media diluiria um branqueamento real de coral duro contra um zero de alga.
    """
    import pandas as pd

    numericas = [
        c for c in (*TERMICAS_DO_DIA, *CLIMATOLOGIA_DO_SITIO, *CONTEXTO_DO_SITIO,
                    'Latitude_Degrees', 'Longitude_Degrees', 'Date_Year')
        if c in quadro.columns
    ]
    quadro = quadro.copy()
    for coluna in numericas:
        quadro[coluna] = pd.to_numeric(quadro[coluna], errors='coerce')

    regras = {COLUNA_ALVO: 'max'}
    regras.update({c: 'first' for c in numericas})
    for texto in ('Site_Name', 'Ecoregion_Name', 'Exposure'):
        if texto in quadro.columns:
            regras[texto] = 'first'

    visitas = quadro.groupby(['Site_ID', 'Date'], as_index=False).agg(regras)
    return visitas.sort_values(['Date', 'Site_ID']).reset_index(drop=True)


@dataclass
class ConjuntoGCBD:
    """A tabela pronta, mais o que precisou ser descartado para chegar nela."""

    quadro: object
    features: tuple
    limiar: float
    linhas_originais: int = 0
    visitas: int = 0
    descartadas_sem_feature: int = 0
    sentinelas_trocadas: dict = field(default_factory=dict)

    @property
    def n(self):
        return len(self.quadro)

    @property
    def positivos(self):
        return int(self.quadro['alvo'].sum())

    @property
    def taxa_positiva(self):
        return self.positivos / self.n if self.n else 0.0

    @property
    def sitios(self):
        return int(self.quadro['Site_ID'].nunique())

    def resumo(self):
        sentinela = (
            f', {sum(self.sentinelas_trocadas.values())} sentinela(s) -> NaN'
            if self.sentinelas_trocadas else ''
        )
        return (
            f'{self.n} visitas de {self.linhas_originais} linhas '
            f'({self.visitas} visitas antes de exigir feature, '
            f'-{self.descartadas_sem_feature} sem feature completa{sentinela})  |  '
            f'{self.positivos} positivos ({self.taxa_positiva:.1%}), '
            f'{self.sitios} sitios'
        )


def montar(caminho=None, pais=PAIS_PADRAO, features=FEATURES_PADRAO,
           limiar=LIMIAR_BRANQUEAMENTO):
    """Conjunto supervisionado do GCBD: features termicas -> branqueou ou nao.

    Diferente de `ml.dataset`, aqui **nao ha horizonte**: a observacao e o
    estado do recife naquele dia, nao uma previsao para daqui a N dias. O
    experimento e transversal, e a validacao agrupa por sitio ou por ano em vez
    de deixar um ano de fora.
    """
    features = tuple(features)
    recusadas = [f for f in features if f in COLUNAS_RECUSADAS]
    if recusadas:
        motivos = '; '.join(f'"{f}": {COLUNAS_RECUSADAS[f]}' for f in recusadas)
        raise ValueError(f'Coluna(s) recusada(s) como feature - {motivos}')

    cru = carregar(caminho, pais)
    linhas = len(cru)

    cru, trocados = limpar_sentinelas(cru)
    visitas = agregar_por_visita(cru)
    n_visitas = len(visitas)

    faltando = [f for f in features if f not in visitas.columns]
    if faltando:
        raise ValueError(f'O arquivo nao tem as colunas {faltando}.')

    antes = len(visitas)
    visitas = visitas.dropna(subset=list(features))
    sem_feature = antes - len(visitas)

    visitas = visitas.copy()
    visitas['alvo'] = (visitas[COLUNA_ALVO] > limiar).astype(int)

    return ConjuntoGCBD(
        quadro=visitas.reset_index(drop=True),
        features=features,
        limiar=limiar,
        linhas_originais=linhas,
        visitas=n_visitas,
        descartadas_sem_feature=sem_feature,
        sentinelas_trocadas=trocados,
    )


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------

def _divisao(numerador, denominador):
    """Zero quando nao ha o que dividir - e nao NaN nem excecao."""
    return float(numerador) / denominador if denominador else 0.0


@dataclass(frozen=True)
class Desempenho:
    """Metricas binarias. Nao reusa `ml.baseline.Desempenho` de proposito.

    Aquele trabalha sobre o BAA ordinal e binariza por `LIMIAR_ALERTA = 3`;
    aqui o alvo ja e 0/1. Passar 0/1 por aquele limiar daria zero em tudo.
    """

    n: int
    positivos: int
    acuracia: float
    taxa_majoritaria: float
    precisao: float
    revocacao: float
    f1: float
    verdadeiros_positivos: int
    falsos_positivos: int
    falsos_negativos: int

    def __str__(self):
        return (
            f'n={self.n}  acc={self.acuracia:.3f} '
            f'(classe majoritaria={self.taxa_majoritaria:.3f})  '
            f'P={self.precisao:.3f} R={self.revocacao:.3f} F1={self.f1:.3f}  '
            f'(VP={self.verdadeiros_positivos} FP={self.falsos_positivos} '
            f'FN={self.falsos_negativos})'
        )


def avaliar(verdadeiro, previsto):
    """Desempenho binario sobre visitas."""
    n = len(verdadeiro)
    if n == 0:
        return Desempenho(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0)

    real = verdadeiro.astype(bool)
    prev = previsto.astype(bool)

    vp = int((real & prev).sum())
    fp = int((~real & prev).sum())
    fn = int((real & ~prev).sum())

    precisao = _divisao(vp, vp + fp)
    revocacao = _divisao(vp, vp + fn)
    positivos = int(real.sum())
    maioria = max(positivos, n - positivos)

    return Desempenho(
        n=n,
        positivos=positivos,
        acuracia=float((real == prev).mean()),
        taxa_majoritaria=_divisao(maioria, n),
        precisao=precisao,
        revocacao=revocacao,
        f1=_divisao(2 * precisao * revocacao, precisao + revocacao),
        verdadeiros_positivos=vp,
        falsos_positivos=fp,
        falsos_negativos=fn,
    )


def prever_regra_noaa(quadro, limiar=LIMIAR_DHW_NOAA, coluna=COLUNA_DHW):
    """A linha de base: a regra publicada da NOAA, `DHW >= 4` -> Alerta Nivel 1.

    E o piso a ser batido. Um modelo que nao supere a regra que ja existe e
    esta documentada nao se justifica - mesmo papel da persistencia na entrega 1
    (ver ml/baseline.py).
    """
    import pandas as pd

    return pd.Series(
        (pd.to_numeric(quadro[coluna], errors='coerce') >= limiar).astype(int),
        index=quadro.index,
    )


# ---------------------------------------------------------------------------
# Validacao
# ---------------------------------------------------------------------------

AGRUPAMENTOS = {
    'sitio': 'Site_ID',
    'ano': 'Date_Year',
}


@dataclass
class ResultadoValidacao:
    """Predicoes fora-da-dobra, reunidas. E o que permite uma PR-AUC unica."""

    modelo: str
    agrupamento: str
    n_dobras: int
    verdadeiro: object = None
    probabilidade: object = None
    previsto: object = None
    pr_auc: float = 0.0
    brier: float = 0.0
    taxa_base: float = 0.0
    desempenho: object = None
    desempenho_noaa: object = None
    por_dobra: list = field(default_factory=list)

    @property
    def ganho_sobre_acaso(self):
        """PR-AUC dividida pela taxa base. 1,0 = nao melhor que sortear.

        Sem isso a PR-AUC nao se le: com 53% de positivos, sortear ja da ~0,53.
        """
        return _divisao(self.pr_auc, self.taxa_base)

    def resumo(self):
        linhas = [
            f'Modelo "{self.modelo}" - validacao agrupada por {self.agrupamento} '
            f'({self.n_dobras} dobras)',
            '',
            f'  PR-AUC = {self.pr_auc:.3f}   (taxa base = {self.taxa_base:.3f}, '
            f'ganho = {self.ganho_sobre_acaso:.2f}x)',
            f'  Brier  = {self.brier:.3f}',
            '',
            f'  modelo:      {self.desempenho}',
            f'  regra NOAA:  {self.desempenho_noaa}',
        ]
        if self.por_dobra:
            linhas += ['', '  por dobra:']
            linhas += [
                f'    dobra {d["dobra"]}: n={d["n"]:3d} pos={d["positivos"]:3d}  '
                f'F1={d["f1"]:.3f}'
                for d in self.por_dobra
            ]
        return '\n'.join(linhas)


def validar(conjunto, nome='logistica', agrupar_por='sitio', n_dobras=5,
            limiar=0.5, semente=42):
    """Validacao cruzada agrupada, com as predicoes fora-da-dobra reunidas.

    ⚠️ **O agrupamento nao e detalhe.** Sao 166 visitas em 119 sitios: varias
    sao o mesmo recife em anos diferentes. Divisao aleatoria poria o mesmo
    sitio nos dois lados e, como a climatologia dele e constante, o modelo
    poderia reconhecer o lugar em vez de aprender o fenomeno.

    `agrupar_por='sitio'` responde "generaliza para um recife novo?".
    `agrupar_por='ano'` responde "generaliza para um evento novo?". Sao
    perguntas diferentes e as duas importam - por isso as duas sao oferecidas.

    **Por que as predicoes sao reunidas em vez de a metrica ser promediada.**
    As dobras aqui sao muito desiguais (1994 tem 1 visita, 2007 tem 33). Uma
    media de PR-AUC por dobra daria o mesmo peso a uma dobra de 1 amostra e a
    uma de 33. Reunir as predicoes fora-da-dobra e calcular uma metrica so trata
    cada visita uma vez, que e o que se quer.
    """
    import numpy as np
    import pandas as pd
    from sklearn.metrics import average_precision_score, brier_score_loss
    from sklearn.model_selection import GroupKFold

    from .modelo import construir

    if agrupar_por not in AGRUPAMENTOS:
        raise ValueError(
            f'Agrupamento "{agrupar_por}" desconhecido. '
            f'Disponiveis: {list(AGRUPAMENTOS)}.'
        )

    quadro = conjunto.quadro
    colunas = list(conjunto.features)
    X = quadro[colunas]
    y = quadro['alvo']
    grupos = quadro[AGRUPAMENTOS[agrupar_por]]

    n_grupos = grupos.nunique()
    dobras = min(n_dobras, n_grupos)
    if dobras < 2:
        raise ValueError(
            f'Ha apenas {n_grupos} grupo(s) de "{agrupar_por}" - nao da para '
            f'validar de forma agrupada.'
        )

    probabilidade = np.full(len(quadro), np.nan)
    por_dobra = []

    for indice, (treino, teste) in enumerate(
        GroupKFold(n_splits=dobras).split(X, y, grupos), start=1
    ):
        # Uma dobra sem as duas classes no treino nao ensina o modelo a
        # distinguir nada - e `fit` nem aceita alvo de uma classe so.
        if y.iloc[treino].nunique() < 2:
            continue

        pipeline = construir(nome, semente)
        pipeline.fit(X.iloc[treino], y.iloc[treino])
        p = pipeline.predict_proba(X.iloc[teste])[:, 1]
        probabilidade[teste] = p

        prev_dobra = (p >= limiar).astype(int)
        desempenho = avaliar(y.iloc[teste], pd.Series(prev_dobra, index=teste))
        por_dobra.append({
            'dobra': indice,
            'n': len(teste),
            'positivos': int(y.iloc[teste].sum()),
            'f1': desempenho.f1,
        })

    avaliadas = ~np.isnan(probabilidade)
    y_avaliado = y[avaliadas]
    p_avaliada = probabilidade[avaliadas]
    previsto = pd.Series((p_avaliada >= limiar).astype(int), index=y_avaliado.index)

    taxa_base = float(y_avaliado.mean()) if len(y_avaliado) else 0.0

    return ResultadoValidacao(
        modelo=nome,
        agrupamento=agrupar_por,
        n_dobras=len(por_dobra),
        verdadeiro=y_avaliado,
        probabilidade=pd.Series(p_avaliada, index=y_avaliado.index),
        previsto=previsto,
        pr_auc=float(average_precision_score(y_avaliado, p_avaliada))
        if y_avaliado.nunique() > 1 else 0.0,
        brier=float(brier_score_loss(y_avaliado, p_avaliada)),
        taxa_base=taxa_base,
        desempenho=avaliar(y_avaliado, previsto),
        desempenho_noaa=avaliar(
            y_avaliado, prever_regra_noaa(quadro.loc[y_avaliado.index])
        ),
        por_dobra=por_dobra,
    )


# ---------------------------------------------------------------------------
# Importancia
# ---------------------------------------------------------------------------

REPETICOES_PADRAO = 10


@dataclass
class ImportanciaGCBD:
    """Quanto cada variavel contribui, medido fora da dobra."""

    modelo: str
    agrupamento: str
    dobras: int = 0
    por_coluna: dict = field(default_factory=dict)
    coeficientes: dict = field(default_factory=dict)

    def resumo(self):
        linhas = [
            f'Importancia - "{self.modelo}", agrupado por {self.agrupamento} '
            f'({self.dobras} dobras)',
            '',
            '  QUEDA DO PR-AUC ao embaralhar a coluna (medida fora da dobra)',
        ]
        for nome, valor in sorted(self.por_coluna.items(), key=lambda p: -p[1]):
            barra = '#' * max(0, round(valor * 200))
            linhas.append(f'    {nome:26s} {valor:+7.4f}  {barra}')

        if self.coeficientes:
            linhas += [
                '',
                '  COEFICIENTES (escala padronizada; positivo = mais risco)',
            ]
            for nome, valor in sorted(
                self.coeficientes.items(), key=lambda p: -abs(p[1])
            ):
                linhas.append(f'    {nome:26s} {valor:+7.3f}')
        return '\n'.join(linhas)


def medir_importancia(conjunto, nome='logistica', agrupar_por='ano',
                      repeticoes=REPETICOES_PADRAO, semente=42, n_dobras=5):
    """Permutacao medida **na dobra deixada de fora**, nunca no treino.

    Importancia calculada onde o modelo ja viu a resposta mede memoria, e nao
    uso - mesma regra de ml/importancia.py. Aqui nao ha grupo de colunas a
    embaralhar junto: cada variavel do GCBD e uma coluna so, sem janelas
    derivadas.
    """
    import numpy as np
    from sklearn.metrics import average_precision_score
    from sklearn.model_selection import GroupKFold

    from .modelo import construir

    if agrupar_por not in AGRUPAMENTOS:
        raise ValueError(f'Agrupamento "{agrupar_por}" desconhecido.')

    quadro = conjunto.quadro
    colunas = list(conjunto.features)
    X, y = quadro[colunas], quadro['alvo']
    grupos = quadro[AGRUPAMENTOS[agrupar_por]]
    dobras = min(n_dobras, grupos.nunique())

    acumulado = {c: [] for c in colunas}
    acumulado_coef = {c: [] for c in colunas}
    medidas = 0

    for treino, teste in GroupKFold(n_splits=dobras).split(X, y, grupos):
        if y.iloc[treino].nunique() < 2 or y.iloc[teste].nunique() < 2:
            # Dobra de uma classe so nao tem PR-AUC definida.
            continue

        pipeline = construir(nome, semente)
        pipeline.fit(X.iloc[treino], y.iloc[treino])

        fora = X.iloc[teste]
        y_fora = y.iloc[teste]
        base = float(average_precision_score(
            y_fora, pipeline.predict_proba(fora)[:, 1]
        ))
        medidas += 1

        gerador = np.random.default_rng(semente)
        for coluna in colunas:
            quedas = []
            for _ in range(repeticoes):
                embaralhado = fora.copy()
                embaralhado[coluna] = fora[coluna].to_numpy()[
                    gerador.permutation(len(fora))
                ]
                quedas.append(base - float(average_precision_score(
                    y_fora, pipeline.predict_proba(embaralhado)[:, 1]
                )))
            acumulado[coluna].append(float(np.mean(quedas)))

        estimador = pipeline.named_steps['estimador']
        if hasattr(estimador, 'coef_'):
            for coluna, valor in zip(colunas, estimador.coef_[0]):
                acumulado_coef[coluna].append(float(valor))

    def media(mapa):
        return {c: sum(v) / len(v) for c, v in mapa.items() if v}

    return ImportanciaGCBD(
        modelo=nome,
        agrupamento=agrupar_por,
        dobras=medidas,
        por_coluna=media(acumulado),
        coeficientes=media(acumulado_coef),
    )
