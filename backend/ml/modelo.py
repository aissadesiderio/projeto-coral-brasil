"""Modelo da entrega 1: prever alerta de branqueamento em `t + N`.

**A pergunta e binaria de proposito.** O alvo do banco e ordinal (BAA 0-4), mas
o que o site decide e "avisar ou nao". Prever `BAA >= 3` em `t+N`:

- e a decisao que existe na pratica;
- devolve **probabilidade**, o que permite medir calibracao - um painel que
  diz "risco 37%" precisa que 37% queira dizer alguma coisa;
- e comparavel com a linha de base de persistencia na mesma metrica.

O nivel ordinal continua no conjunto e pode virar alvo depois; o que nao pode e
relatar acuracia multiclasse sobre 92% de dias sem alerta e chamar de resultado.

**Por que PR-AUC e nao ROC-AUC.** Sao ~8% de positivos. O ROC-AUC premia
acerto na classe majoritaria e fica otimista por construcao; a curva
precisao-revocacao mede o que interessa quando o evento e raro.

**Por que Pipeline com nomes de coluna.** O modelo antigo do projeto predizia
0.0 para tudo porque a ordem das features na predicao diferia da do treino e um
`except` nu engolia o erro. Aqui a ordem deixa de ser contrato implicito: o
`ColumnTransformer` seleciona por nome, e `prever` recusa quadro sem as colunas
que o modelo viu no treino.

**Limite conhecido.** Sao ~4 anos-evento de amostra efetiva
(docs/VARIAVEIS.md secao 7.2). Toda dobra de leave-year-out remove perto de um
quarto do sinal, e nenhum ajuste fino de hiperparametro se sustenta nessa base.
Por isso os dois modelos disponiveis sao simples e ficam nos padroes.
"""

from dataclasses import dataclass, field

from ingestao.conectores.noaa_crw import LIMIAR_ALERTA

from .baseline import avaliar, avaliar_episodios, prever_persistencia

# Modelos oferecidos. Deliberadamente dois, e ambos simples:
#
# - `logistica` e o honesto para esta base. Linear, poucos parametros,
#   coeficiente legivel - da para dizer quais variaveis pesaram e em que
#   direcao, que e o que um TCC precisa defender.
# - `boosting` existe para responder "e se um modelo mais forte ganhasse?".
#   Se ele nao superar a logistica, isso e resultado: a relacao e simples ou a
#   amostra e pequena demais para sustentar algo maior.
MODELOS = ('logistica', 'boosting')

# Metodos de recalibracao da probabilidade. `None` = crua, como o estimador
# devolve.
#
# 🚨 **Por que isso e necessario aqui.** `class_weight='balanced'` trata as
# classes como se fossem do mesmo tamanho. Isso e correto para DECIDIR com 8%
# de positivos - sem ele o modelo aprende que nunca avisar quase sempre acerta -
# e **destroi a probabilidade por construcao**. Medido em 27/07/2026: a
# logistica promete 0,165 quando a taxa real e 0,084, com ECE de **0,081**,
# praticamente do tamanho do proprio fenomeno.
#
# Recalibrar conserta o numero sem desmontar a decisao:
#
#   versao                ECE      PR-AUC   R@0.5
#   log_balanced        0,0811     0,885    0,909   <- o que estava no ar
#   log_bal_platt       0,0163     0,878    0,721
#   log_bal_isotonic    0,0039     0,871    0,775
#
# ⚠️ O calibrador e ajustado **dentro** da dobra de treino (`cv=3` interno).
# Ajusta-lo sobre as predicoes que serao avaliadas seria vazamento, e a curva
# sairia perfeita por construcao.
#
# Ver docs/RESULTADOS.md secao 23 e ml/calibracao.py.
CALIBRACOES = (None, 'isotonic', 'sigmoid')


class ColunaAusente(ValueError):
    """O quadro nao tem uma coluna que o modelo viu no treino."""


def construir(nome='logistica', semente=42, calibrar=None):
    """Monta o Pipeline. A selecao por nome acontece em `Ajuste.colunas`.

    `calibrar` envolve o estimador num recalibrador de probabilidade. Ver
    `CALIBRACOES`.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    if calibrar not in CALIBRACOES:
        raise ValueError(
            f'Calibracao "{calibrar}" desconhecida. '
            f'Disponiveis: {list(CALIBRACOES)}.'
        )

    if nome == 'logistica':
        # `class_weight='balanced'` porque 8% de positivos: sem isso o modelo
        # aprende que nunca avisar quase sempre acerta. Ver docs/VARIAVEIS.md
        # secao 7.2.
        estimador = LogisticRegression(
            class_weight='balanced', max_iter=2000, random_state=semente
        )
        escala = StandardScaler()
    elif nome == 'boosting':
        estimador = HistGradientBoostingClassifier(
            class_weight='balanced', random_state=semente
        )
        # Arvore nao precisa de escala; manter a etapa deixaria o Pipeline
        # simetrico ao custo de sugerir que a escala importa aqui.
        escala = 'passthrough'
    else:
        raise ValueError(f'Modelo "{nome}" desconhecido. Disponiveis: {list(MODELOS)}.')

    pipeline = Pipeline([('escala', escala), ('estimador', estimador)])
    if calibrar is None:
        return pipeline

    from sklearn.calibration import CalibratedClassifierCV

    # O `cv=3` e interno ao treino: o calibrador so ve dados que o estimador
    # tambem viu, nunca a dobra de teste de fora.
    return CalibratedClassifierCV(pipeline, method=calibrar, cv=3)


def alvo_binario(serie):
    """BAA ordinal -> "houve alerta". O evento que o site comunica."""
    return (serie >= LIMIAR_ALERTA).astype(int)


@dataclass
class Ajuste:
    """Um modelo treinado, junto com o que ele viu.

    As colunas viajam com o modelo de proposito: e o que permite `prever`
    recusar um quadro diferente em vez de silenciosamente reordenar features.
    """

    pipeline: object
    nome: str
    colunas: tuple
    horizonte: int
    n_treino: int = 0
    positivos_treino: int = 0
    calibracao: object = None

    def prever_probabilidade(self, quadro):
        faltando = [c for c in self.colunas if c not in quadro.columns]
        if faltando:
            raise ColunaAusente(
                f'O quadro nao tem {faltando}. O modelo "{self.nome}" foi '
                f'treinado com {list(self.colunas)}.'
            )
        # Seleciona por nome e na ordem do treino - a ordem do quadro que
        # chega e irrelevante, que e exatamente o ponto.
        return self.pipeline.predict_proba(quadro[list(self.colunas)])[:, 1]

    def prever(self, quadro, limiar=0.5):
        import pandas as pd

        probabilidade = self.prever_probabilidade(quadro)
        return pd.Series(probabilidade >= limiar, index=quadro.index).astype(int)

    def metadados(self):
        """O que precisa acompanhar o artefato para ele ser reproduzivel."""
        return {
            'modelo': self.nome,
            'colunas': list(self.colunas),
            'horizonte_dias': self.horizonte,
            'alvo': f'baa >= {LIMIAR_ALERTA} em t+{self.horizonte}',
            'n_treino': self.n_treino,
            'positivos_treino': self.positivos_treino,
            # Sem isto ninguem sabe se a probabilidade gravada e crua ou
            # recalibrada - e a diferenca vale 0,081 de ECE.
            'calibracao': self.calibracao,
        }


def treinar(quadro, colunas, nome='logistica', horizonte=7, semente=42,
            calibrar=None):
    """Treina sobre um quadro ja montado por `ml.dataset`."""
    pipeline = construir(nome, semente, calibrar)
    y = alvo_binario(quadro['alvo'])

    pipeline.fit(quadro[list(colunas)], y)

    return Ajuste(
        pipeline=pipeline,
        nome=nome,
        colunas=tuple(colunas),
        horizonte=horizonte,
        n_treino=len(quadro),
        positivos_treino=int(y.sum()),
        calibracao=calibrar,
    )


def como_baa(binario):
    """Converte predicao binaria em serie comparavel com o BAA ordinal.

    Permite reusar `avaliar` e `avaliar_episodios`, que trabalham no nivel.
    Nao inventa nivel: usa o limiar, o unico ponto que o binario determina.
    """
    return binario * LIMIAR_ALERTA


@dataclass
class ResultadoAno:
    ano: int
    n_teste: int
    positivos_teste: int
    pr_auc: float = 0.0
    brier: float = 0.0
    desempenho_modelo: object = None
    desempenho_persistencia: object = None
    episodios_modelo: object = None
    episodios_persistencia: object = None

    @property
    def teve_evento(self):
        return self.positivos_teste > 0

    def __str__(self):
        if not self.teve_evento:
            return f'  {self.ano}: n={self.n_teste:5d}  sem evento no ano - nada a detectar'
        return (
            f'  {self.ano}: n={self.n_teste:5d}  PR-AUC={self.pr_auc:.3f}  '
            f'Brier={self.brier:.3f}  '
            f'F1 modelo={self.desempenho_modelo.f1_alerta:.3f} vs '
            f'persistencia={self.desempenho_persistencia.f1_alerta:.3f}  |  '
            f'episodios {self.episodios_modelo.episodios_detectados}/'
            f'{self.episodios_modelo.episodios_reais} vs '
            f'{self.episodios_persistencia.episodios_detectados}/'
            f'{self.episodios_persistencia.episodios_reais}'
        )


@dataclass
class Comparacao:
    """Resultado do leave-year-out inteiro."""

    modelo: str
    anos: list = field(default_factory=list)

    @property
    def anos_com_evento(self):
        return [r for r in self.anos if r.teve_evento]

    def media(self, atributo):
        """Media so sobre anos com evento.

        Incluir ano sem evento inflaria qualquer metrica de alerta: F1 = 0 num
        ano em que nao havia nada a detectar nao mede o modelo, mede o clima.
        """
        avaliados = self.anos_com_evento
        if not avaliados:
            return 0.0
        return sum(getattr(r, atributo) for r in avaliados) / len(avaliados)

    def resumo(self):
        linhas = [f'Modelo "{self.modelo}" - leave-year-out', '']
        linhas += [str(r) for r in self.anos]
        avaliados = self.anos_com_evento
        if avaliados:
            f1_m = sum(r.desempenho_modelo.f1_alerta for r in avaliados) / len(avaliados)
            f1_p = sum(
                r.desempenho_persistencia.f1_alerta for r in avaliados
            ) / len(avaliados)
            linhas += [
                '',
                f'  media sobre os {len(avaliados)} anos COM evento:',
                f'    PR-AUC = {self.media("pr_auc"):.3f}   '
                f'Brier = {self.media("brier"):.3f}',
                f'    F1 alerta: modelo = {f1_m:.3f}  |  persistencia = {f1_p:.3f}'
                f'   ({"modelo ganha" if f1_m > f1_p else "persistencia ganha"})',
            ]
        return '\n'.join(linhas)


def comparar_com_persistencia(conjunto, nome='logistica', limiar=0.5, semente=42):
    """Leave-year-out: treina sem um ano, testa nele, compara com persistencia.

    A divisao e por ano da **data do alvo** - o dia sobre o qual a previsao
    fala. Divisao aleatoria seria vazamento puro: dias vizinhos do mesmo
    episodio cairiam dos dois lados.
    """
    from sklearn.metrics import average_precision_score, brier_score_loss

    from .baseline import anos_disponiveis, dividir_deixando_um_ano_de_fora

    quadro = conjunto.quadro
    colunas = conjunto.colunas_de_entrada
    comparacao = Comparacao(modelo=nome)

    for ano in anos_disponiveis(quadro):
        treino, teste = dividir_deixando_um_ano_de_fora(quadro, ano)
        if teste.empty or treino.empty:
            continue

        y_teste = alvo_binario(teste['alvo'])
        resultado = ResultadoAno(
            ano=ano, n_teste=len(teste), positivos_teste=int(y_teste.sum())
        )

        if not resultado.teve_evento:
            comparacao.anos.append(resultado)
            continue

        ajuste = treinar(treino, colunas, nome, conjunto.horizonte, semente)
        probabilidade = ajuste.prever_probabilidade(teste)
        previsto = ajuste.prever(teste, limiar)

        resultado.pr_auc = float(average_precision_score(y_teste, probabilidade))
        resultado.brier = float(brier_score_loss(y_teste, probabilidade))

        previsto_baa = como_baa(previsto)
        persistencia = prever_persistencia(teste)

        resultado.desempenho_modelo = avaliar(teste['alvo'], previsto_baa)
        resultado.desempenho_persistencia = avaliar(teste['alvo'], persistencia)
        resultado.episodios_modelo = avaliar_episodios(teste, previsto_baa)
        resultado.episodios_persistencia = avaliar_episodios(teste, persistencia)

        comparacao.anos.append(resultado)

    return comparacao
