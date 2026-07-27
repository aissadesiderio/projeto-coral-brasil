"""A probabilidade que o modelo devolve quer dizer alguma coisa?

O painel vai exibir **"risco 37%"**. Para esse numero nao ser decorativo, ele
precisa cumprir uma promessa verificavel:

> **Entre os dias em que o modelo disse 37%, o alerta aconteceu em cerca de 37%
> deles.** Nem mais, nem menos.

Um modelo pode ordenar os casos perfeitamente - sempre dando probabilidade maior
ao dia que vai virar alerta - e ainda assim mentir no numero. Ordenar e calibrar
sao propriedades diferentes, e so a primeira aparece no PR-AUC.

**Por que o Brier bom nao basta.** O Brier da entrega 1 e 0,043, que parece
otimo. Mas 92% dos dias nao tem alerta: um modelo que respondesse 0,00 sempre
teria Brier 0,08 sem prever nada. O Brier mistura tres coisas, e a decomposicao
de Murphy separa:

    Brier = confiabilidade − resolucao + incerteza

- **confiabilidade** (quanto menor, melhor) e a calibracao propriamente dita:
  o quanto a probabilidade prometida difere da frequencia observada;
- **resolucao** (quanto maior, melhor) e o quanto o modelo separa os casos;
- **incerteza** e a dificuldade do problema, e nao depende do modelo.

Um Brier baixo pode vir de incerteza baixa, e nao de acerto. Ver `decompor`.

🚨 **E ha um motivo especifico para suspeitar deste modelo.** Ele e treinado com
`class_weight='balanced'` (ver `ml/modelo.py`), que instrui o estimador a tratar
as classes como se fossem do mesmo tamanho. Isso e correto para *decidir* com
8% de positivos - sem isso o modelo aprende que nunca avisar quase sempre
acerta - e **destroi a calibracao por construcao**: as probabilidades saem
infladas em relacao a taxa real.

Ou seja: nao e um defeito a descobrir, e uma consequencia conhecida a **medir**.

⚠️ **Tudo aqui usa predicao fora-da-dobra.** Calibracao medida sobre o proprio
treino mede memoria: o modelo ja viu a resposta, e a curva sai perfeita sem
querer dizer nada.
"""

from dataclasses import dataclass, field

# Faixas por quantil, e nao por largura igual.
#
# Com 8% de positivos, faixas de largura igual (0-10%, 10-20%, ...) jogam quase
# todos os dias na primeira e deixam as outras com dois ou tres pontos. A curva
# resultante e ruido em nove faixas e um numero na primeira.
#
# Quantil poe o mesmo numero de dias em cada faixa. As faixas ficam de larguras
# diferentes - e e isso que se quer, porque cada ponto passa a ter n parecido.
ESTRATEGIAS = ('quantil', 'largura')
FAIXAS_PADRAO = 10


@dataclass(frozen=True)
class Faixa:
    """Um pedaço da curva: o que foi prometido contra o que aconteceu."""

    inicio: float
    fim: float
    n: int
    probabilidade_media: float   # o que o modelo prometeu
    frequencia_observada: float  # o que de fato aconteceu
    positivos: int

    @property
    def desvio(self):
        """Positivo = o modelo prometeu mais evento do que houve."""
        return self.probabilidade_media - self.frequencia_observada

    def __str__(self):
        return (
            f'[{self.inicio:.3f}, {self.fim:.3f}]  n={self.n:5d}  '
            f'prometido={self.probabilidade_media:.3f}  '
            f'observado={self.frequencia_observada:.3f}  '
            f'desvio={self.desvio:+.3f}'
        )


def curva(verdadeiro, probabilidade, n_faixas=FAIXAS_PADRAO,
          estrategia='quantil'):
    """Agrupa as predições em faixas e compara promessa com realidade."""
    import numpy as np
    import pandas as pd

    if estrategia not in ESTRATEGIAS:
        raise ValueError(
            f'Estrategia "{estrategia}" desconhecida. Use {list(ESTRATEGIAS)}.'
        )

    y = np.asarray(verdadeiro, dtype=float)
    p = np.asarray(probabilidade, dtype=float)
    if len(y) != len(p):
        raise ValueError(f'Tamanhos diferentes: {len(y)} e {len(p)}.')
    if len(y) == 0:
        return []

    if estrategia == 'quantil':
        # `duplicates='drop'` porque muitas predicoes iguais colapsam bordas -
        # acontece quando o modelo satura perto de 0.
        cortes = pd.qcut(p, n_faixas, duplicates='drop', retbins=True)[1]
    else:
        cortes = np.linspace(0.0, 1.0, n_faixas + 1)

    # 🚨 Guarda descoberta por teste em 27/07/2026.
    #
    # Se a predicao for constante - ou quase -, `qcut` colapsa todas as bordas
    # e devolve **menos de duas**. O laco abaixo entao nao forma faixa nenhuma,
    # a curva sai vazia e o ECE da **0,0**: exatamente a leitura de "calibracao
    # perfeita", quando o caso e o oposto. Um modelo que responde sempre 30%
    # sobre 8% de eventos e o pior calibrado possivel, e estava passando como o
    # melhor.
    #
    # Nesse caso agrupa-se pelos proprios valores distintos, que e o que da
    # sentido a comparacao promessa-x-realidade quando ha poucos valores.
    if len(cortes) < 2:
        distintos = np.unique(p)
        cortes = np.append(distintos, distintos[-1] + 1e-9)

    faixas = []
    for i in range(len(cortes) - 1):
        inicio, fim = float(cortes[i]), float(cortes[i + 1])
        dentro = (p >= inicio) & (p <= fim if i == len(cortes) - 2 else p < fim)
        if not dentro.any():
            continue
        faixas.append(Faixa(
            inicio=inicio,
            fim=fim,
            n=int(dentro.sum()),
            probabilidade_media=float(p[dentro].mean()),
            frequencia_observada=float(y[dentro].mean()),
            positivos=int(y[dentro].sum()),
        ))
    return faixas


def erro_esperado(faixas):
    """ECE — desvio médio, ponderado pelo tamanho de cada faixa.

    Zero é calibração perfeita. Lê-se como "em média, a probabilidade
    prometida erra a frequência real em X pontos".
    """
    total = sum(f.n for f in faixas)
    if not total:
        return 0.0
    return sum(f.n * abs(f.desvio) for f in faixas) / total


def erro_maximo(faixas):
    """MCE — o pior desvio entre as faixas. Denuncia falha localizada."""
    return max((abs(f.desvio) for f in faixas), default=0.0)


@dataclass(frozen=True)
class Decomposicao:
    """Brier separado nas três partes de Murphy."""

    brier: float
    confiabilidade: float  # menor = melhor. É a calibração.
    resolucao: float       # maior = melhor. É a capacidade de separar.
    incerteza: float       # do problema, não do modelo.

    @property
    def residuo(self):
        """Deve ser ~0: confiabilidade − resolução + incerteza = Brier."""
        return self.brier - (self.confiabilidade - self.resolucao + self.incerteza)

    def __str__(self):
        return (
            f'Brier={self.brier:.4f} = confiabilidade({self.confiabilidade:.4f}) '
            f'− resolucao({self.resolucao:.4f}) + incerteza({self.incerteza:.4f})'
        )


def decompor(verdadeiro, probabilidade, faixas=None, n_faixas=FAIXAS_PADRAO,
             estrategia='quantil'):
    """Decomposição de Murphy do Brier score.

    É o que responde "o Brier está bom porque o modelo acerta, ou porque o
    problema é fácil?". Um Brier de 0,043 sobre 8% de positivos pode ser
    quase todo *incerteza*.
    """
    import numpy as np

    y = np.asarray(verdadeiro, dtype=float)
    p = np.asarray(probabilidade, dtype=float)
    if len(y) == 0:
        return Decomposicao(0.0, 0.0, 0.0, 0.0)

    if faixas is None:
        faixas = curva(y, p, n_faixas, estrategia)

    base = float(y.mean())
    n = len(y)

    confiabilidade = sum(
        f.n * (f.probabilidade_media - f.frequencia_observada) ** 2 for f in faixas
    ) / n
    resolucao = sum(
        f.n * (f.frequencia_observada - base) ** 2 for f in faixas
    ) / n

    return Decomposicao(
        brier=float(((p - y) ** 2).mean()),
        confiabilidade=confiabilidade,
        resolucao=resolucao,
        incerteza=base * (1 - base),
    )


@dataclass
class Relatorio:
    """O resultado completo, pronto para imprimir."""

    modelo: str
    n: int
    taxa_base: float
    probabilidade_media: float
    faixas: list = field(default_factory=list)
    decomposicao: object = None

    @property
    def erro_esperado(self):
        return erro_esperado(self.faixas)

    @property
    def erro_maximo(self):
        return erro_maximo(self.faixas)

    @property
    def vies_global(self):
        """Positivo = o modelo promete mais evento do que existe."""
        return self.probabilidade_media - self.taxa_base

    def resumo(self):
        linhas = [
            f'Calibracao — modelo "{self.modelo}", {self.n} amostras '
            f'(fora da dobra)',
            '',
            f'  taxa real de evento     : {self.taxa_base:.3f}',
            f'  probabilidade media dita: {self.probabilidade_media:.3f}',
            f'  vies global             : {self.vies_global:+.3f}'
            f'   ({"promete demais" if self.vies_global > 0 else "promete de menos"})',
            '',
            f'  erro esperado (ECE)     : {self.erro_esperado:.3f}',
            f'  erro maximo   (MCE)     : {self.erro_maximo:.3f}',
        ]
        if self.decomposicao:
            linhas += ['', f'  {self.decomposicao}']
        linhas += ['', '  FAIXAS (prometido x observado):']
        for f in self.faixas:
            marca = '#' * min(40, round(f.frequencia_observada * 40))
            linhas.append(f'    {f}  {marca}')
        return '\n'.join(linhas)


def predicoes_fora_da_dobra(conjunto, nome='logistica', semente=42,
                            calibrar=None):
    """Reúne a predição de cada amostra feita pelo modelo que **não a viu**.

    É a única forma honesta de medir calibração: sobre o próprio treino, o
    modelo já viu a resposta e a curva sai perfeita sem querer dizer nada.

    Usa a mesma divisão do experimento — um ano inteiro de fora por vez.
    """
    import numpy as np
    import pandas as pd

    from .baseline import anos_disponiveis, dividir_deixando_um_ano_de_fora
    from .modelo import alvo_binario, treinar

    quadro = conjunto.quadro
    colunas = conjunto.colunas_de_entrada
    probabilidade = pd.Series(np.nan, index=quadro.index, dtype=float)

    for ano in anos_disponiveis(quadro):
        treino, teste = dividir_deixando_um_ano_de_fora(quadro, ano)
        if teste.empty or treino.empty:
            continue
        if alvo_binario(treino['alvo']).nunique() < 2:
            # Sem as duas classes no treino o `fit` nem aceita.
            continue
        ajuste = treinar(treino, colunas, nome, conjunto.horizonte, semente,
                         calibrar=calibrar)
        probabilidade.loc[teste.index] = ajuste.prever_probabilidade(teste)

    avaliadas = probabilidade.notna()
    return alvo_binario(quadro.loc[avaliadas, 'alvo']), probabilidade[avaliadas]


def avaliar(conjunto, nome='logistica', n_faixas=FAIXAS_PADRAO,
            estrategia='quantil', semente=42, calibrar=None):
    """Mede a calibração do modelo sobre o conjunto inteiro, fora da dobra."""
    y, p = predicoes_fora_da_dobra(conjunto, nome, semente, calibrar)
    faixas = curva(y, p, n_faixas, estrategia)

    return Relatorio(
        modelo=f'{nome}+{calibrar}' if calibrar else nome,
        n=len(y),
        taxa_base=float(y.mean()) if len(y) else 0.0,
        probabilidade_media=float(p.mean()) if len(p) else 0.0,
        faixas=faixas,
        decomposicao=decompor(y, p, faixas),
    )
