"""Quais variaveis o modelo usou, e em que direcao.

Responde a pergunta que a docs/VARIAVEIS.md secao 3.6 deixou em aberto: medimos
que a **trajetoria do oxigenio** distingue inicio de fim de episodio melhor que
a do DHW, e registramos que isso "precisa ser confirmado no modelo treinado".
E o que este modulo faz.

**Duas medidas, porque uma sozinha engana.**

*Coeficiente* (so na logistica) diz **direcao e magnitude**: "oxigenio caindo
aumenta o risco, nesta escala". E o que se defende numa banca. Mas coeficiente
grande numa variavel que quase nao varia nao muda predicao nenhuma.

*Permutacao* embaralha uma coluna e mede **quanto o modelo piora**. Funciona
nos dois modelos e mede contribuicao real para prever, nao ajuste. Mas nao diz
direcao.

**As duas sao medidas no ano deixado de fora**, nunca no treino. Importancia
calculada onde o modelo ja viu a resposta mede memoria, nao uso.

⚠️ **Correlacao divide credito.** `sst` e `sst_variacao_7d` andam juntas: ao
embaralhar so uma, a outra ainda carrega parte da informacao, e a queda medida
subestima as duas. Por isso ha tambem a medida **por grupo** - a variavel e
suas trajetorias embaralhadas de uma vez. Se o grupo cai muito e cada coluna
sozinha cai pouco, a informacao esta na variavel, repartida entre as colunas.
"""

from dataclasses import dataclass, field

from .baseline import anos_disponiveis, dividir_deixando_um_ano_de_fora
from .modelo import alvo_binario, treinar

# Metrica usada para medir a queda. E a mesma do experimento: com 8% de
# positivos, acuracia nao serve de criterio nem aqui.
REPETICOES_PADRAO = 10


def grupos_de_variavel(colunas):
    """Agrupa cada variavel com as janelas derivadas dela.

    `sst`, `sst_variacao_7d` e `sst_variacao_14d` viram um grupo `sst`. E o
    conjunto que precisa ser embaralhado junto para medir o que a variavel
    inteira contribui.
    """
    grupos = {}
    for coluna in colunas:
        base = coluna.split('_variacao_')[0].split('_media_')[0].split('_maximo_')[0]
        grupos.setdefault(base, []).append(coluna)
    return grupos


def _pontuar(ajuste, quadro, y):
    from sklearn.metrics import average_precision_score

    return float(average_precision_score(y, ajuste.prever_probabilidade(quadro)))


def queda_por_permutacao(ajuste, quadro, colunas_do_grupo,
                         repeticoes=REPETICOES_PADRAO, semente=42):
    """Quanto o PR-AUC cai ao embaralhar as colunas do grupo.

    As colunas do grupo recebem **a mesma permutacao**, de proposito: isso
    preserva a correlacao entre elas e quebra apenas a ligacao com o alvo. Usar
    permutacoes independentes destruiria tambem a estrutura interna do grupo e
    mediria outra coisa.
    """
    import numpy as np

    y = alvo_binario(quadro['alvo'])
    base = _pontuar(ajuste, quadro, y)

    gerador = np.random.default_rng(semente)
    quedas = []
    for _ in range(repeticoes):
        embaralhado = quadro.copy()
        ordem = gerador.permutation(len(quadro))
        for coluna in colunas_do_grupo:
            embaralhado[coluna] = quadro[coluna].to_numpy()[ordem]
        quedas.append(base - _pontuar(ajuste, embaralhado, y))

    return float(np.mean(quedas)), float(np.std(quedas))


def coeficientes(ajuste):
    """Coeficientes da logistica, na escala padronizada.

    O Pipeline aplica `StandardScaler` antes do estimador, entao os
    coeficientes ja estao em unidades de desvio-padrao e sao **comparaveis
    entre si** - o que nao seria verdade nas unidades originais, onde oxigenio
    (centenas) e salinidade (dezenas) nao se comparam.

    Retorna None para modelos sem coeficiente (arvore).
    """
    estimador = ajuste.pipeline.named_steps['estimador']
    if not hasattr(estimador, 'coef_'):
        return None
    return dict(zip(ajuste.colunas, estimador.coef_[0]))


@dataclass
class Importancia:
    """Resultado agregado sobre as dobras do leave-year-out."""

    modelo: str
    anos: list = field(default_factory=list)
    por_coluna: dict = field(default_factory=dict)
    por_grupo: dict = field(default_factory=dict)
    coeficientes: dict = field(default_factory=dict)

    def ordenado(self, mapa):
        return sorted(mapa.items(), key=lambda par: -par[1])

    def resumo(self):
        linhas = [
            f'Importancia - modelo "{self.modelo}"',
            f'  medida nos {len(self.anos)} anos com evento: {self.anos}',
            '',
            '  POR GRUPO (variavel + suas trajetorias, embaralhadas juntas)',
            '  queda media do PR-AUC ao destruir a informacao:',
        ]
        for nome, valor in self.ordenado(self.por_grupo):
            barra = '#' * max(0, round(valor * 200))
            linhas.append(f'    {nome:16s} {valor:+7.4f}  {barra}')

        linhas += ['', '  POR COLUNA (cada uma isolada)']
        for nome, valor in self.ordenado(self.por_coluna):
            linhas.append(f'    {nome:26s} {valor:+7.4f}')

        if self.coeficientes:
            linhas += [
                '',
                '  COEFICIENTES (escala padronizada; sinal = direcao)',
                '  positivo = aumenta o risco de alerta',
            ]
            for nome, valor in sorted(
                self.coeficientes.items(), key=lambda p: -abs(p[1])
            ):
                linhas.append(f'    {nome:26s} {valor:+7.3f}')

        return '\n'.join(linhas)


def medir(conjunto, nome='logistica', repeticoes=REPETICOES_PADRAO, semente=42):
    """Mede importancia dentro do leave-year-out.

    Para cada ano com evento: treina sem ele, mede a importancia **nele**, e no
    fim tira a media. Medir no proprio treino diria o que o modelo memorizou,
    nao o que ele usa para prever num ano que nunca viu.
    """
    quadro = conjunto.quadro
    colunas = conjunto.colunas_de_entrada
    grupos = grupos_de_variavel(colunas)

    resultado = Importancia(modelo=nome)
    acumulado_coluna = {c: [] for c in colunas}
    acumulado_grupo = {g: [] for g in grupos}
    acumulado_coef = {c: [] for c in colunas}

    for ano in anos_disponiveis(quadro):
        treino, teste = dividir_deixando_um_ano_de_fora(quadro, ano)
        if teste.empty or treino.empty:
            continue
        if int(alvo_binario(teste['alvo']).sum()) == 0:
            # Ano sem evento nao mede importancia: nao ha o que detectar, e o
            # PR-AUC fica indefinido.
            continue

        ajuste = treinar(treino, colunas, nome, conjunto.horizonte, semente)
        resultado.anos.append(ano)

        for coluna in colunas:
            media, _ = queda_por_permutacao(
                ajuste, teste, [coluna], repeticoes, semente
            )
            acumulado_coluna[coluna].append(media)

        for grupo, membros in grupos.items():
            media, _ = queda_por_permutacao(
                ajuste, teste, membros, repeticoes, semente
            )
            acumulado_grupo[grupo].append(media)

        coefs = coeficientes(ajuste)
        if coefs:
            for coluna, valor in coefs.items():
                acumulado_coef[coluna].append(valor)

    def media_de(mapa):
        return {
            chave: sum(valores) / len(valores)
            for chave, valores in mapa.items()
            if valores
        }

    resultado.por_coluna = media_de(acumulado_coluna)
    resultado.por_grupo = media_de(acumulado_grupo)
    resultado.coeficientes = media_de(acumulado_coef)
    return resultado
