# Como o modelo funciona — versão sem jargão

Este documento explica **como o modelo é construído e testado**, em linguagem
comum. É a versão para ler, explicar para alguém ou defender numa apresentação.

A versão técnica, com os nomes formais e os detalhes de implementação, está em
[METODOLOGIA.md](METODOLOGIA.md). O conteúdo é o mesmo — muda só a linguagem.

## Índice

1. [O que estamos tentando fazer](#1-o-que-estamos-tentando-fazer)
2. [A régua: a previsão burra](#2-a-régua-a-previsão-burra)
3. [Como testar sem colar](#3-como-testar-sem-colar)
4. [Por que "acertou 92%" não quer dizer nada](#4-por-que-acertou-92-não-quer-dizer-nada)
5. [Por que contamos eventos, e não dias](#5-por-que-contamos-eventos-e-não-dias)
6. [Por que usamos dois modelos](#6-por-que-usamos-dois-modelos)
7. [Por que o modelo precisa saber a direção](#7-por-que-o-modelo-precisa-saber-a-direção)
8. [O que ainda não dá para afirmar](#8-o-que-ainda-não-dá-para-afirmar)

---

## 1. O que estamos tentando fazer

Uma pergunta só:

> **Olhando o mar hoje, dá para saber se daqui a uma semana o recife estará em
> alerta de branqueamento?**

Se der, o site vira um sistema de aviso: dá tempo de agir.

Se não der, **isso também é resposta**. É melhor descobrir agora do que depois
de meses construindo em cima de uma suposição errada.

---

## 2. A régua: a previsão burra

Antes de construir qualquer coisa, é preciso saber **o que seria fácil**.

Existe uma previsão burra que funciona bem demais:

> *"Daqui a uma semana vai estar igual a hoje."*

É como prever o tempo dizendo "amanhã vai ser igual a hoje". Não é inteligente,
mas acerta muito — porque o clima não muda de repente.

**E ela acerta 84%.**

Ela funciona porque **um evento de branqueamento dura semanas** — o maior da
nossa série durou 117 dias. Se hoje o recife está em alerta, daqui a uma semana
provavelmente ainda está.

### O que isso significa

**Um modelo que acerte 80% é pior do que não fazer nada.**

Ele só se justifica se passar de 84%. Essa é a régua, e ela é alta.

Mas já sabemos **onde a previsão burra falha**: ela não vê o evento chegar nem
acabar. Ela só sabe repetir o presente. É aí que um modelo pode ganhar.

---

## 3. Como testar sem colar

Esta é a parte que mais confunde — e a mais importante.

Imagine estudar para uma prova **usando exatamente as questões que vão cair**.
Você tira 10, e a nota não significa nada.

Com dados é igual: se o modelo treinar nos mesmos dias em que for testado, ele
**decora** em vez de aprender.

### A armadilha que quase ninguém vê

Não basta separar os dias aleatoriamente.

Se o modelo treinar no **dia 15 de março** e for testado no **dia 16**, ele já
sabe a resposta — o recife não muda de um dia para o outro. Os dois dias são
praticamente o mesmo dia.

É colar sem perceber. E era exatamente o que o código antigo do projeto fazia.

### A solução: esconder um ano inteiro

| Treina em | Testa em |
|---|---|
| todos os anos, menos 2020 | **2020** |
| todos os anos, menos 2022 | **2022** |
| todos os anos, menos 2024 | **2024** |
| … | … |

O modelo nunca viu aquele ano. Se ele acerta ali, **aprendeu de verdade**.

---

## 4. Por que "acertou 92%" não quer dizer nada

**92% dos dias não têm alerta nenhum.**

Então um modelo que responde sempre *"pode ficar tranquilo"* acerta 92% dos
dias — e é completamente inútil, porque nunca avisa ninguém.

> É como um alarme de incêndio que fica corretamente quieto 364 dias por ano —
> e não toca no dia do incêndio.

Por isso a porcentagem de acerto sozinha é um número bonito e vazio.

### O que olhamos no lugar

| Pergunta | O que ela verifica |
|---|---|
| Quando ele avisa, tem razão? | se ele dá alarme falso demais |
| Dos eventos reais, quantos ele avisou? | se ele deixa evento passar |
| A porcentagem que ele mostra é honesta? | se "risco 37%" quer mesmo dizer 37% |

A última importa porque o site vai exibir um número de risco. Esse número
precisa querer dizer que **em 100 dias parecidos, o evento aconteceu em uns 37**
— e não ser só um número que sobe quando piora.

---

## 5. Por que contamos eventos, e não dias

Imagine um recife com **dois eventos** num ano:

| | Duração |
|---|---|
| Evento A | 60 dias |
| Evento B | 5 dias |

**A previsão burra** olha hoje e repete:

- No **evento A**, depois que o alerta começa, ela acerta quase todos os 60
  dias — enquanto durar, "igual a hoje" está certo.
- No **evento B**, ela **nunca percebe nada**. Acaba antes de ela entrar nele.

> Placar: acertou 60 dias, **perdeu 1 dos 2 eventos**.

**O modelo** tenta antecipar, olhando se a água está esquentando:

- No **evento A**, acerta o começo mas erra alguns dias no meio.
- No **evento B**, **percebe** — porque viu a temperatura subindo antes.

> Placar: acertou 55 dias, **pegou os 2 eventos**.

### Quem ganhou?

| Jeito de contar | Previsão burra | Modelo |
|---|---|---|
| Contando **dias** | 60 ✅ | 55 |
| Contando **eventos** | 1 de 2 | **2 de 2** ✅ |

**Depende de como se conta.** E foi exatamente isso que aconteceu com os dados
reais: empate contando dias, vitória clara contando eventos.

### Qual conta importa

**A de eventos.** Se o recife entrou em alerta e ninguém foi avisado, não
adianta o sistema ter acertado 60 dias tranquilos antes.

Por isso essa forma de contar foi construída **antes** do modelo existir. Se
olhássemos só os dias, teríamos concluído que o modelo não serve — e seria uma
conclusão errada, tirada da conta errada.

---

## 6. Por que usamos dois modelos

Os dois são bem diferentes.

**O primeiro é como uma receita escrita:**

> *"Oxigênio caindo aumenta o risco. Temperatura subindo aumenta mais ainda."*

Você lê, entende e consegue explicar para outra pessoa.

**O segundo é como um cozinheiro experiente:**

> *"Confia em mim, esse aí vai branquear."*

Costuma acertar mais, mas não sabe explicar como chegou lá.

### Rodar os dois é um teste, não indecisão

A pergunta é:

> **O cozinheiro experiente cozinha melhor que a receita escrita?**

E as duas respostas ensinam algo:

| Se o cozinheiro ganhar bastante | Se ele não ganhar |
|---|---|
| A relação é complicada — vale abrir mão da explicação | A relação é simples — **fique com a receita**, que você consegue explicar |

**Não existe resposta ruim.** Nos dois casos você sai sabendo mais.

### O que aconteceu

Empate. Cada um ganhou numa coluna, e por pouco.

**Isso é bom.** Se o modelo complicado tivesse ganhado de longe, seria preciso
escolher entre **acertar mais** e **conseguir explicar**. Como empatou, dá para
ficar com o simples e ainda dizer, com honestidade:

> *"Testamos um modelo mais forte. Não melhorou. Isso indica que a relação é
> simples, ou que ainda temos dados de menos para sustentar algo maior."*

Essa frase é mais forte do que apresentar um modelo só — porque mostra que a
alternativa foi **testada**, não suposta.

### 🚨 Mas descobrimos um problema com a receita

A vantagem da receita escrita seria poder ler cada linha dela. Fomos ler — e
**a receita está borrada**.

Ela diz coisas assim:

> *"Mais calor acumulado **diminui** o risco."*

Isso é obviamente falso. Calor acumulado é justamente o que mata coral.

**O motivo é que medimos a mesma coisa duas vezes.** Cada variável entra na
receita com **duas medidas de mudança**: quanto mudou na **última semana** e
quanto mudou nas **últimas duas semanas**.

É como uma receita que manda:

> - coloque **1 colher a mais de sal que ontem**
> - coloque **2 colheres a mais de sal que na semana passada**

As duas instruções dizem quase a mesma coisa — quem sabe uma já sabe a outra. O
prato pode até sair certo, mas **cada linha sozinha deixa de fazer sentido**, e
uma delas pode virar negativa para compensar a outra.

> ⚠️ **Primeiro achamos que o problema era outro.** Suspeitávamos que a
> sobreposição fosse entre *"quanto está"* e *"quanto mudou"*. Medimos, e essas
> duas quase não se sobrepõem — saber que o calor está em 8 diz pouco sobre ele
> ter subido ou descido. A sobreposição real era entre as **duas medidas de
> mudança**, que se parecem em **97%**.

### Por que isso acontece, com números

O nome técnico é **colinearidade**: duas informações que dizem quase a mesma
coisa.

No nosso caso, cada variável entra duas vezes:

| Coluna | O que ela diz |
|---|---|
| `dhw` | o calor acumulado **é 8** |
| `dhw_variacao_14d` | ele **subiu 3** nas últimas duas semanas |

Elas andam juntas. Sabendo uma, você já sabe muito sobre a outra.

Agora suponha que a verdade seja simples — **risco = 2 × calor acumulado** — e
que, nos nossos dados, a variação seja mais ou menos **metade** do calor
acumulado.

O modelo pode escrever essa mesma verdade de infinitas formas, e **todas dão a
resposta certa**:

| Fórmula que o modelo poderia escolher | Resultado |
|---|---|
| `2 × dhw` + `0 × variação` | ✅ certo |
| `0 × dhw` + `4 × variação` | ✅ certo |
| **`−2 × dhw`** + `8 × variação` | ✅ **também certo** |

Confira a última: se a variação é metade do dhw, então
`−2×dhw + 8×(dhw÷2)` = `−2dhw + 4dhw` = `2×dhw`. Bate.

As três previsões são **idênticas**. O modelo escolhe uma qualquer — e se
escolher a terceira, a explicação dele passa a dizer *"mais calor acumulado =
menos risco"*.

> **A previsão não está errada. A explicação é que não é confiável.**

### O que dá para afirmar mesmo assim

Dá para dizer **quanto cada variável importa** — basta apagá-la e ver o quanto
o modelo piora:

| Variável | O quanto faz falta |
|---|---|
| **Calor acumulado** | muito |
| **Temperatura** | bastante |
| Oxigênio | pouquinho |
| Salinidade | nada |

O que **não** dá é dizer a direção ("subir isso aumenta o risco em tanto") —
não enquanto as medidas repetidas estiverem juntas.

E é bom que isso tenha aparecido agora: se alguém numa banca lesse o
"calor acumulado diminui o risco" antes de nós, seria bem pior.

### E já sabemos como consertar

Testamos uma receita com **uma medida de mudança só** — a da última semana, sem
a de duas semanas. Resultado:

| | Receita atual | Receita enxuta |
|---|---|---|
| Instruções | 10 | **4** |
| Acerto | 0,707 | **0,728** |
| Linhas com sinal invertido | 1 | **nenhuma** |

**A receita enxuta acerta um pouco mais, usa menos da metade das instruções, e
volta a fazer sentido lida linha por linha.** O calor acumulado aparece como o
maior fator, positivo, como a física manda.

O único custo: ela pega **16 dos 19 eventos** em vez de 18 — e essa diferença
está dentro da margem de erro do projeto.

A decisão registrada é adotar a receita enxuta. Um modelo que se explica vale
mais que dois eventos de vantagem dentro da margem de erro.

---

## 7. Por que o modelo precisa saber a direção

Um número sozinho não diz para onde as coisas estão indo:

> **"O calor acumulado é 6."**

Isso descreve tanto um recife que **subiu de 2** na última semana — o evento
está começando, vai piorar — quanto um que **caiu de 10** — o evento está
acabando.

**São situações opostas com o mesmo número.**

Por isso o modelo recebe também *quanto cada coisa mudou nos últimos 7 e 14
dias*. Sem isso, ele fica **pior que a previsão burra**:

| | Sabendo a direção | Sem saber |
|---|---|---|
| Placar | **0,707** | 0,489 |

Essa é a diferença mais clara de todo o experimento.

### Uma surpresa

Esperávamos que a direção do **calor acumulado** fosse a mais útil. Não é.

O calor acumulado soma as últimas 12 semanas, então ele **continua subindo até
no fim do evento** — não serve para dizer se está começando ou acabando.

Quem serve é a direção da **temperatura** e, curiosamente, a do **oxigênio** —
que cai quando o evento começa e sobe quando acaba. Faz sentido: água quente
segura menos oxigênio.

Esse parecia o primeiro sinal de que uma variável **que não é temperatura**
pode ajudar — a pergunta científica do trabalho.

**Mas o sinal não se confirmou.** Quando medimos quanto o oxigênio realmente
ajuda o modelo a prever, a resposta foi: **quase nada**, e a parte de
"direção do oxigênio" foi **puro ruído**.

Por quê? Provavelmente porque **oxigênio depende de temperatura** — água quente
segura menos oxigênio. Então o modelo já sabia daquilo por outro caminho.

> Distinguir dois grupos **não é o mesmo** que ajudar a prever. A primeira
> medida olhou só os momentos de virada; a segunda olhou o ano inteiro.

Ficou registrado assim, e não apagado, de propósito: um indício que não
sobrevive ao teste seguinte faz parte do trabalho.

---

## 8. O que ainda não dá para afirmar

Sendo honesta sobre os limites:

**Temos poucos eventos.** Parecem muitos dias com alerta — quase 600 — mas eles
se agrupam em **19 eventos**, concentrados em **4 anos**. E os três recifes
reagem juntos, porque é o mesmo oceano esquentando. Então não são 19 casos
independentes; são mais ou menos 4.

**O que isso impede:**

1. Diferenças pequenas entre modelos são **sorte**, não resultado.
2. Não dá para ficar ajustando o modelo até ele melhorar — com poucos eventos,
   isso é decorar, não aprender.
3. A pergunta *"salinidade e oxigênio ajudam?"* ainda não tem resposta firme.
   Para respondê-la é preciso mais dados de branqueamento observado de verdade,
   e não classificação feita por satélite.

**E o mais importante:** o modelo prevê **estresse térmico**, não branqueamento
observado. O nome honesto do produto é *previsão de estresse térmico*. Chamar
de "previsão de branqueamento" seria prometer mais do que ele entrega.

---

## Onde ver mais

| Documento | O que tem |
|---|---|
| [VISAO_GERAL.md](VISAO_GERAL.md) | O projeto inteiro: o que é branqueamento, o que cada variável significa |
| [METODOLOGIA.md](METODOLOGIA.md) | Esta mesma explicação, com os nomes técnicos |
| [RESULTADOS.md](RESULTADOS.md) | Os números que saíram |
| [VARIAVEIS.md](VARIAVEIS.md) | Por que cada variável entra ou fica de fora |

---

## Histórico

| Data | Alteração |
|---|---|
| 25/07/2026 | Acrescentado, em §6 e §7, o resultado da medida de importância: a "receita" **não** se explica neste projeto, porque cada variável é medida duas vezes (nível e mudança) e as linhas individuais deixam de fazer sentido — analogia das duas colheres de sal. E o indício do oxigênio, que a §7 anunciava, **não se confirmou**. |
| 25/07/2026 | Documento criado como versão sem jargão da METODOLOGIA.md, para leitura e apresentação. Mesmo conteúdo, com analogias: previsão do tempo, prova com as questões vazadas, alarme de incêndio, receita e cozinheiro. |
