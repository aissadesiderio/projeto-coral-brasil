# Metodologia — Como o modelo é avaliado

Este documento explica **o desenho do experimento**: o que estamos tentando
responder, contra o que o modelo é comparado, e como o teste é feito sem
trapaça. É o documento que vira o capítulo de metodologia do TCC.

📖 **Existe uma versão sem jargão deste documento**, com o mesmo conteúdo e
analogias no lugar dos termos técnicos:
[METODOLOGIA_SIMPLES.md](METODOLOGIA_SIMPLES.md). Use aquela para explicar a
alguém ou apresentar; esta para implementar e auditar.

Os outros documentos respondem outras perguntas:
[FONTES.md](FONTES.md) diz de onde vêm os dados,
[VARIAVEIS.md](VARIAVEIS.md) diz por que cada variável entra,
[arquitetura.md](arquitetura.md) diz onde tudo isso mora.

---

## 1. A pergunta

Uma só:

> **Olhando o mar hoje, dá para saber se daqui a N dias o recife estará em
> alerta de branqueamento?**

Se a resposta for sim, o site vira um sistema de aviso — dá tempo de agir. Se
for não, **isso também é um resultado válido**, e é melhor descobrir cedo do
que depois de meses construindo em cima de uma premissa falsa.

`N` é parâmetro do experimento, não constante escondida no código. Valores
testados: 7, 14 e 30 dias.

A escolha desse alvo — e por que ele não é circular — está em
[VARIAVEIS.md](VARIAVEIS.md) §4.

---

## 2. A régua: persistência

Antes de construir qualquer modelo, é preciso saber **o que seria fácil**.

Existe uma previsão burra que funciona surpreendentemente bem:

> *"Daqui a N dias vai estar igual a hoje."*

É como prever o tempo dizendo "amanhã vai ser igual a hoje". Não é inteligente,
mas acerta muito — porque o clima não muda de uma hora para outra.

**É o piso, e ele é alto.** Medido em 25/07/2026, para N = 7 dias:

| | Persistência |
|---|---|
| Dos alertas que ela dá, quantos acontecem | **84%** |
| Dos eventos reais, quantos ela avisa | **84%** |
| Episódios detectados | 15 de 19 |

Ela funciona porque **um evento de branqueamento dura semanas**: o maior da
série durou 117 dias. Se hoje está em alerta, daqui a uma semana provavelmente
ainda está.

### O que isso obriga

**Um modelo que acerte 80% é pior que não fazer nada.** Ele só se justifica se
superar a persistência — e a comparação precisa ser feita **nas mesmas
linhas**, senão não diz nada.

Também já sabemos **onde a persistência erra**: no começo e no fim dos
episódios. Ela não vê o evento chegar nem acabar. Em 2026, que teve episódios
curtos, ela caiu para 47%. **É nessas transições que um modelo pode ganhar** —
e é por isso que existem as features de trajetória ([VARIAVEIS.md](VARIAVEIS.md)
§3.6).

---

## 3. Como testar sem trapacear

Esta é a parte que mais confunde, e a mais importante.

Imagine estudar para uma prova **usando exatamente as questões que vão cair**.
Você tira 10, e isso não significa nada.

Com dados é igual: se o modelo treinar nos mesmos dias em que for testado, ele
decora em vez de aprender.

### A armadilha sutil

**Não basta separar dias aleatoriamente.**

Se o modelo treinar no dia 15 de março e for testado no dia 16, ele já sabe a
resposta — o recife não muda de um dia para o outro, e os dois dias pertencem
ao mesmo episódio. É colar sem perceber.

Esse é o defeito do `train_test_split` aleatório do modelo antigo do projeto.
Em série temporal, ele é vazamento puro.

### A solução: esconder um ano inteiro

| Treina em | Testa em |
|---|---|
| 2021, 2022, 2023, 2024, 2025, 2026 | **2020** |
| 2020, 2021, 2023, 2024, 2025, 2026 | **2022** |
| 2020, 2021, 2022, 2023, 2025, 2026 | **2024** |
| … | … |

O modelo nunca viu aquele ano. Se acerta ali, aprendeu de verdade.

⚠️ **A divisão é pelo ano da data do alvo**, não da data das features. O que
define a dobra é *o dia sobre o qual a previsão fala*. Uma amostra com features
de 28/12/2023 prevendo 04/01/2024 pertence a 2024.

---

## 4. Por que não medimos "quantos por cento acertou"

**92% dos dias não têm alerta.**

Então um modelo que responde sempre *"sem alerta, pode ficar tranquilo"* acerta
92% — e é inútil, porque nunca avisa ninguém.

**Acurácia aqui é um número bonito e vazio.** Qualquer acurácia relatada precisa
vir ao lado da taxa da classe majoritária, senão engana. O código calcula as
duas juntas de propósito (`baseline.taxa_da_classe_majoritaria`).

### O que medimos no lugar

| Métrica | A pergunta que ela responde |
|---|---|
| **Precisão** | Quando ele avisa, tem razão? |
| **Revocação** | Dos eventos reais, quantos ele avisou? |
| **F1** | As duas juntas, num número |
| **PR-AUC** | O mesmo, sem depender de onde se corta o "avisar ou não" |
| **Brier score** | A probabilidade é honesta? |

**Por que PR-AUC e não ROC-AUC.** Com 8% de positivos, o ROC-AUC premia acerto
na classe majoritária e fica otimista por construção. A curva
precisão-revocação mede o que interessa quando o evento é raro.

**Por que Brier importa.** O painel vai exibir algo como "risco: 37%". Esse
número precisa querer dizer alguma coisa — que em 100 dias parecidos, o evento
aconteceu em cerca de 37. Um modelo pode ordenar bem os dias e ainda assim
estar sistematicamente errado na escala. Calibração é o que separa "37%" de
"um número que sobe quando piora".

---

## 5. Quais modelos, e por que dois

O projeto roda **dois modelos lado a lado**, em toda avaliação:

| Nome no código | O que é | É árvore de decisão? |
|---|---|---|
| `logistica` | Regressão logística | ❌ não — é linear |
| `boosting` | `HistGradientBoostingClassifier` | ✅ **sim** — centenas de árvores |

O *gradient boosting* constrói muitas árvores pequenas em sequência, cada uma
corrigindo os erros da anterior. É uma família de árvores, não uma só, mas o
bloco de construção é a árvore de decisão.

*(O modelo antigo do projeto, descartado, era uma Random Forest — também
árvore. Ver [VISAO_GERAL.md](VISAO_GERAL.md) §11 para por que foi descartado.)*

### O que cada família consegue representar

Esta parte costuma ser entendida ao contrário, então vale o exemplo.

Suponha que a salinidade estresse o coral **nos dois extremos** — muito baixa
(chuva, água doce) e muito alta (evaporação). Uma relação em U.

**A regressão logística só sabe dizer uma direção.** Ela é obrigada a escolher
entre *"mais sal = mais risco"* ou *"menos sal = mais risco"*. Diante de um U,
ela responde uma reta, e erra nas duas pontas.

**A árvore não assume direção nenhuma** — ela corta o espaço em pedaços:

```
salinidade < 34?   →  risco alto
salinidade 34–38?  →  risco baixo
salinidade > 38?   →  risco alto
```

| | Relação sempre na mesma direção | Relação que muda de direção |
|---|---|---|
| Regressão logística | ✅ boa | ❌ ruim |
| Árvore / boosting | ✅ boa | ✅ **boa** |

⚠️ **Portanto: variável que influencia "para mais e para menos" é argumento a
favor de árvore, não contra.** Quem tem dificuldade com isso é o modelo linear.

### Por que os dois ficam, em vez de escolher um

Não é indecisão — cada um responde uma pergunta diferente.

**A logística é interpretável** — *sob uma condição que este projeto não
cumpre*. Ela dá um coeficiente por variável, o que em princípio permite
afirmar *"o oxigênio caindo aumenta o risco, nesta magnitude"*.

🚨 **Medido em 25/07/2026: com o conjunto atual de features, os coeficientes
não são interpretáveis.** O do `dhw` saiu **negativo** — lido como mecanismo,
diria que calor acumulado protege o coral. É artefato de colinearidade.

**A causa medida não é a que se supunha.** Nível e trajetória quase não se
correlacionam (r ≈ 0,10). A colinearidade está entre as **duas janelas da mesma
variável**: `dhw_variacao_7d` e `dhw_variacao_14d` têm **r = 0,976**.

✅ **E há solução medida:** usar **uma janela por variável** elimina o problema
sem custo de desempenho — 4 entradas em vez de 10, F1 0,728 contra 0,707, o
melhor PR-AUC de todas as versões testadas, e **nenhum coeficiente térmico
invertido**. Ver [RESULTADOS.md](RESULTADOS.md) §8 para as cinco versões
comparadas.

Enquanto essa mudança não for aplicada ao código, **a leitura defensável é a
importância por grupo**, que dá magnitude mas não direção.

**O boosting responde "e se um modelo mais expressivo ganhasse?"**. Se ele
**não** superar a logística, isso é resultado publicável: ou a relação é
simples, ou a amostra é pequena demais para sustentar algo maior.

Na primeira rodada foi o segundo caso — nenhum dominou:

| | Acerto diário (F1) | Episódios detectados |
|---|---|---|
| Logística | 0,707 | **18/19** |
| Boosting | **0,741** | 17/19 |

Com ~4 anos-evento, essa diferença é ruído. **O boosting não comprou nada
claro**, que é exatamente o esperado com esta base. Ver
[RESULTADOS.md](RESULTADOS.md).

### Ambos ficam nos padrões, de propósito

Nenhum hiperparâmetro foi ajustado. Com ~4 anos-evento, ajuste fino é
sobreajuste disfarçado de melhoria — e o *leave-year-out* não tem dobras
suficientes para separar melhora real de sorte na dobra.

A única configuração deliberada é `class_weight='balanced'` nos dois: com 8%
de positivos, sem isso o modelo aprende que **nunca avisar quase sempre
acerta**.

---

## 6. Métrica por episódio

Contar acerto dia a dia infla a impressão de evidência, porque dias dentro do
mesmo episódio são quase o mesmo dia.

Então, além do desempenho diário, medimos por evento:

- **Um episódio conta como detectado se algum dos seus dias foi previsto.**
  Se o evento durou 70 dias e o modelo acertou o início com 3 dias de atraso,
  isso é sucesso, não fracasso — quem lê um aviso quer saber do evento, não da
  data exata.
- **Alarme falso é um episódio previsto que não encosta em nenhum evento real** —
  não um dia isolado a mais dentro de um evento que de fato aconteceu.

⚠️ O agrupamento é **por local**. Num quadro com vários recifes as datas se
repetem, e agrupar só por data funde episódios simultâneos de recifes
diferentes num evento só. Na primeira execução real isso fez 19 episódios
contarem como 7.

---

## 7. Limitações declaradas

**A amostra efetiva são ~4 anos-evento, não 7.134 dias.** Os 598 dias em alerta
se agrupam em 19 episódios, concentrados nos mesmos quatro anos nos três
recifes — é o mesmo forçante oceanográfico atingindo três pontos da mesma
costa. Detalhe e medição em [VARIAVEIS.md](VARIAVEIS.md) §7.2.

Consequências que precisam aparecer no trabalho, não serem descobertas pela
banca:

1. **Cada dobra do leave-year-out remove ~25% do sinal disponível.**
2. **Nenhum ajuste fino de hiperparâmetro se sustenta nessa base.** Por isso os
   modelos usados são simples e ficam nos padrões.
3. **A média de desempenho é calculada só sobre anos com evento.** Incluir 2021
   e 2023, que não tiveram nenhum, mediria o clima e não o modelo.
4. **Dias de um mesmo episódio são autocorrelacionados.** Se houver teste
   estatístico, a unidade amostral é o episódio.

---

## 8. Onde isso está no código

| Arquivo | O que faz |
|---|---|
| [`backend/ml/dataset.py`](../backend/ml/dataset.py) | Monta a tabela: features em `t`, alvo em `t+N`. Todas as guardas contra vazamento |
| [`backend/ml/baseline.py`](../backend/ml/baseline.py) | Persistência, métricas diárias e por episódio, divisão *leave-year-out* |
| [`backend/ml/modelo.py`](../backend/ml/modelo.py) | O modelo e a comparação ano a ano contra a persistência |
| [`backend/ml/tests.py`](../backend/ml/tests.py) | Testes que travam cada regra acima |

O modelo é encapsulado num `Pipeline` do sklearn que **seleciona features por
nome**. Não é preciosismo: o modelo antigo do projeto predizia `0.0` para todos
os registros porque a ordem das features na predição diferia da do treino, e um
`except` sem tipo engolia o erro. Ordem de coluna deixa de ser contrato
implícito.

---

## 9. Histórico

| Data | Alteração |
|---|---|
| 25/07/2026 | **§5 corrigida — os coeficientes não são interpretáveis neste projeto.** O argumento de que "a logística é interpretável" valia sob uma condição que o projeto não cumpre: features não correlacionadas. Cada variável entra junto com a própria trajetória, e a medição mostrou o coeficiente do `dhw` **negativo** — o que lido como mecanismo diria que calor acumulado protege o coral. Enquanto a colinearidade não for resolvida, a leitura defensável é a importância por grupo, que dá magnitude e não direção. Ver [RESULTADOS.md](RESULTADOS.md) §7. |
| 25/07/2026 | **§5 criada — quais modelos e por que dois.** Registra que o `boosting` **é** baseado em árvores de decisão e a `logistica` não, e corrige uma inversão comum: variável que influencia "para mais e para menos" é argumento **a favor** de árvore, não contra — quem tem dificuldade com relação em U é o modelo linear. Também por que os dois convivem (interpretabilidade contra expressividade) e por que ambos ficam nos padrões. |
| 25/07/2026 | Documento criado. Registra o desenho do experimento da entrega 1: alvo binário com horizonte de N dias, persistência como piso, validação *leave-year-out*, métricas de evento raro e por episódio, e as quatro limitações que decorrem de ~4 anos-evento de amostra efetiva. |
