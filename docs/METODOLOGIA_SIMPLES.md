# Como o modelo funciona — versão sem jargão

Este documento explica **como o modelo é construído e testado**, em linguagem
comum. É a versão para ler, explicar para alguém ou defender numa apresentação.

A versão técnica, com os nomes formais e os detalhes de implementação, está em
[METODOLOGIA.md](METODOLOGIA.md). O conteúdo é o mesmo — muda só a linguagem.

📖 **Este documento fala só da ciência.** Se a dúvida for sobre o *software* —
o que é um endpoint, onde os dados ficam salvos, por que existem dois bancos —
o documento é o [SISTEMA_SIMPLES.md](SISTEMA_SIMPLES.md), escrito na mesma
linguagem.

## Índice

1. [O que estamos tentando fazer](#1-o-que-estamos-tentando-fazer)
2. [As réguas: a previsão burra, e o aviso que a NOAA já publica](#2-a-régua-a-previsão-burra)
3. [Como testar sem colar](#3-como-testar-sem-colar)
4. [Por que "acertou 92%" não quer dizer nada](#4-por-que-acertou-92-não-quer-dizer-nada)
5. [Por que contamos eventos, e não dias](#5-por-que-contamos-eventos-e-não-dias)
6. [Por que usamos dois modelos](#6-por-que-usamos-dois-modelos)
7. [Por que o modelo precisa saber a direção](#7-por-que-o-modelo-precisa-saber-a-direção)
8. [O que ainda não dá para afirmar](#8-o-que-ainda-não-dá-para-afirmar)
9. [O que descobrimos quando finalmente olhamos branqueamento de verdade](#9-o-que-descobrimos-quando-finalmente-olhamos-branqueamento-de-verdade)
10. [Fomos buscar salinidade e oxigênio. Não era isso.](#10-fomos-buscar-salinidade-e-oxigênio-não-era-isso)
11. [Última tentativa: poluição da água](#11-última-tentativa-poluição-da-água)
12. [O número que o site ia mostrar estava mentindo](#12-o-número-que-o-site-ia-mostrar-estava-mentindo)
13. [A pergunta que sobrou: a partir de quantos por cento o site avisa?](#13-a-pergunta-que-sobrou-a-partir-de-quantos-por-cento-o-site-avisa)

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

### 🚨 A segunda régua, que faltava — e é mais alta

Por muito tempo essa foi a **única** régua do projeto. E ela tem um problema
como adversária: é uma **cópia** do dado de ontem. Ganhar de uma cópia não é o
mesmo que ganhar de algo que já existe.

E já existe. **A própria NOAA publica um aviso todo dia**, com uma regra
simples: se a água está quente agora *e* o calor acumulado passou de certo
ponto, é alerta. Qualquer pessoa pode ler esse aviso de graça, sem este projeto
existir.

Então a pergunta certa nunca foi *"o modelo bate a previsão burra?"*. Era:

> **O modelo bate o aviso que a NOAA já publica?**

Medimos em 30/07/2026. A resposta tem duas metades, e as duas importam:

| | O modelo pega… | E erra o alarme… |
|---|---|---|
| **modelo** | **17 dos 19 episódios** | **11 vezes** |
| previsão burra | 15 dos 19 | 4 vezes |
| **regra da NOAA** | 15 dos 19 | 6 vezes |

**O modelo pega dois episódios a mais. E cobra por isso.** Ele dispara o alarme
cinco a sete vezes mais do que as duas réguas.

Isso não é derrota nem vitória — é o preço, e ele estava escondido enquanto a
única comparação era com a cópia. A frase honesta não é *"o nosso modelo é
melhor que o da NOAA"*. É:

> **O nosso modelo é mais sensível.** Ele avisa mais cedo e avisa mais vezes,
> inclusive quando não precisava.

É exatamente para isso que existe a escala de quatro degraus (§13): quem quiser
só os avisos que quase sempre se confirmam olha o *Alerta alto*; quem preferir
não perder nada olha a *Observação*.

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

### Na segunda parte do projeto, esconder é mais complicado

Na segunda parte do projeto usamos dados diferentes: em vez de medições diárias
de satélite, são **visitas de mergulhadores** a recifes, ao longo de 16 anos.
Cada visita é: fulano foi neste recife, neste dia, e anotou se o coral estava
branqueado.

Aqui não existe "dia seguinte" para colar. Mas existem **duas maneiras
diferentes de duas visitas se parecerem**, e por isso escondemos de dois jeitos:

| Escondemos… | E perguntamos |
|---|---|
| **um recife inteiro** | "O modelo funciona num recife que ele nunca viu?" |
| **um ano inteiro** | "O modelo funciona num ano que ele nunca viu?" |

**E as duas respostas foram diferentes** — muito diferentes. Escondendo recife,
o modelo pareceu bom. Escondendo ano, ele quase empatou com chutar.

### Por que isso acontece — com quatro visitas

Vamos supor quatro visitas só, a dois recifes vizinhos, **A** e **B**:

| Visita | Recife | Ano | Fez quanto calor | Branqueou? |
|---|---|---|---|---|
| 1 | A | 2005 | muito | sim |
| 2 | B | 2005 | muito | sim |
| 3 | A | 2010 | pouco | sim |
| 4 | B | 2010 | pouco | sim |

Repare: em 2005 branqueou com muito calor. Em 2010 branqueou **com pouco** —
porque naquele ano teve outra coisa, digamos uma enxurrada de água doce, que o
modelo não enxerga.

**Escondendo o recife B:** o modelo estuda nas visitas 1 e 3 (as do recife A) e
é testado nas 2 e 4 (as do B).

Mas olhe bem: a visita 1 e a visita 2 são **do mesmo ano**, com o **mesmo
calor**. O modelo já viu como foi 2005 e já viu como foi 2010 — só não conhecia
aquele pedaço de mapa. **Ele acerta as duas.** Parece um ótimo modelo.

**Escondendo o ano 2010:** o modelo estuda nas visitas 1 e 2, onde branqueamento
veio junto com muito calor. É testado nas 3 e 4, onde veio com pouco.

Ele aprendeu "muito calor, branqueia". Vê pouco calor e responde "não branqueia".
**Erra as duas.**

O modelo nunca foi bom. Ele estava **reconhecendo o ano**, não entendendo o
fenômeno. Esconder o recife não revelava isso; esconder o ano, sim.

> **E como o site precisa avisar sobre um branqueamento que ainda não
> aconteceu — um ano que ninguém viu —, o número honesto é o do ano.**

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

## 9. O que descobrimos quando finalmente olhamos branqueamento de verdade

A limitação da seção anterior — "o modelo prevê estresse térmico, não
branqueamento" — deixou de ser só uma ressalva. Nós fomos atrás do dado que
faltava e testamos.

### O problema com a pergunta antiga

O projeto queria saber: **temperatura explica tudo, ou salinidade e oxigênio
também importam?**

Só que na primeira parte a resposta que o modelo tentava adivinhar (o "alerta"
da NOAA) é **calculada a partir de temperatura**. É como perguntar se a altura
de alguém depende do peso, mas medir a altura com uma régua feita de peso: a
resposta vem viciada, e vai dizer que só o peso importa.

Então buscamos uma base em que a resposta veio de **gente de verdade**:
mergulhadores que foram ao recife, olharam e anotaram se o coral estava branco.
São **166 visitas** a recifes brasileiros, entre 1994 e 2010.

### A régua da NOAA, testada contra a realidade brasileira

A NOAA — o serviço americano que monitora recifes no mundo inteiro — tem uma
regra publicada. Ela soma quanto calor a mais o recife acumulou nas últimas 12
semanas, e quando esse acúmulo passa de um certo ponto, ela declara:
**"branqueamento esperado aqui"**.

Testamos essa regra nas 166 visitas brasileiras. O resultado:

| | |
|---|---|
| Visitas em que houve branqueamento | **88** |
| Quantas a regra da NOAA previu | **10** |
| Quantas ela errou apontando branqueamento onde não houve | **0** |

Leia devagar, porque as duas metades dizem coisas opostas:

**A regra nunca erra para mais.** Nas 10 vezes em que ela disse "vai
branquear", branqueou. Zero alarmes falsos. Isso é impressionante.

**Mas ela quase nunca fala.** Em **78 das 88 vezes** que o coral branqueou no
Brasil, a régua da NOAA marcava **zero** — nenhum calor acumulado. O recife
estava branqueando e o termômetro não tinha nada a dizer.

> Em linguagem comum: **calor demais é um jeito garantido de matar coral, mas
> está longe de ser o único.**

### Por que isso é a coisa mais importante que o projeto achou

Porque é exatamente o buraco que o projeto se propôs a preencher.

Se a temperatura explicasse tudo, este projeto seria redundante — bastaria
copiar o alerta da NOAA e exibi-lo em português. O que a medição mostra é que
**existem 78 branqueamentos brasileiros sem explicação térmica**, esperando
alguém investigar.

E apareceu uma pista. Entre as variáveis que sobraram, a segunda mais útil para
o modelo não foi de temperatura: foi **o vento**.

Isso faz sentido físico. Vento mexe a água, mistura a camada quente da
superfície com a água mais fria de baixo, e muda a salinidade e o oxigênio
perto do coral — que são justamente as duas coisas que este projeto mede e que
a NOAA não olha.

### ⚠️ O que ainda **não** dá para dizer

**Não descobrimos que salinidade e oxigênio explicam os 78 casos.** Nós não os
medimos nessa base — ela não os traz. Descobrimos que **há espaço para eles**,
não que eles ocupam esse espaço.

E mais três ressalvas honestas:

1. **Esse dado brasileiro para em 2010.** Nada do branqueamento de 2020 ou de
   2024 tem essa checagem de mergulhador.
2. **Picãozinho ficou de fora**: o recife com mergulhador mais próximo está a
   198 km, que é outro sistema de recifes.
3. **166 visitas é pouco.** Diferença pequena entre versões do modelo continua
   sendo sorte.

O próximo passo já está definido e orçado: buscar salinidade e oxigênio para os
90 dias anteriores a cada uma dessas visitas, e ver se eles explicam o que a
temperatura não explicou.

---

## 10. Fomos buscar salinidade e oxigênio. Não era isso.

Este é o resultado que o projeto inteiro estava perseguindo, e ele veio
**negativo**. Vale contar com cuidado, porque um resultado negativo bem medido
é resultado — e porque a forma como ele é negativo tem nuance.

### O que fizemos

Para cada uma das 166 visitas, buscamos como estavam a **salinidade** (quanto
sal tem a água) e o **oxigênio dissolvido** nos 90 dias anteriores. Foram
**30.212 medições diárias**, baixadas de um modelo oceanográfico europeu que
reconstrói o passado do oceano. Nenhuma falhou.

Depois comparamos três modelos:

| Modelo | O que ele vê |
|---|---|
| **A** | só temperatura e vento |
| **B** | temperatura, vento, **e mais** salinidade e oxigênio |
| **C** | **só** salinidade e oxigênio |

Se a hipótese do projeto estivesse certa, **B** seria melhor que **A**, e **C**
teria algum valor sozinho.

### O que aconteceu

**B não foi melhor que A. Foi pior.** E **C ficou no chute** — literalmente:
acertou tanto quanto sortear.

Nós então testamos as duas desculpas que tínhamos:

**"Talvez 90 dias seja muito tempo."** Faz sentido: uma enxurrada de água doce
dura dias, não três meses; uma janela longa demais diluiria o efeito. Refizemos
com 7, 14, 30 e 60 dias. **Nenhuma ajudou.**

**"Talvez essas variáveis só estejam dizendo qual recife é, não como ele
estava."** Testamos. Elas mudam de visita para visita no mesmo recife, e mal
conseguem identificar o lugar. **Não era isso também.**

### Mas elas *não* são inúteis — e essa é a parte interessante

Quando olhamos só a descrição, sem pedir previsão, elas **funcionam**:

> Os recifes que branquearam tinham, nos meses anteriores, **oxigênio mais
> baixo e caindo** e **salinidade mais baixa e caindo** — exatamente o que a
> biologia previa.

O efeito existe e aponta para o lado certo. Ele é só **cerca de metade da
força** do efeito da temperatura — e essa metade não é suficiente para
transformar em previsão útil.

**A diferença entre descrever e prever é o coração deste resultado.** Dizer
"nos recifes que branquearam o oxigênio estava mais baixo" é verdade. Dizer
"consigo saber se vai branquear olhando o oxigênio" é falso. Uma diferença
média entre dois grupos pode ser real e ainda assim pequena demais para decidir
casos individuais — é a mesma razão pela qual saber que fumantes vivem menos
não permite prever quando uma pessoa específica vai morrer.

### 🔁 E já tínhamos visto isso antes

Na primeira parte do projeto, o oxigênio também tinha aparecido como promessa —
ele separava bem o começo do fim de um episódio — e também não virou capacidade
de prever.

Agora aconteceu de novo, com **dados diferentes, período diferente e pergunta
diferente**. Uma vez é coincidência; duas vezes em bases independentes é uma
característica do problema.

### ⚠️ A ressalva honesta, que muda a conclusão

**Nós não medimos a salinidade e o oxigênio do recife. Medimos os do oceano ao
redor dele.**

O modelo europeu divide o oceano em quadrados. Para o oxigênio, cada quadrado
tem **28 km de lado**. E **69 das nossas 166 visitas ficam a menos de 1 km da
costa** — em 20 sítios, o oxigênio mais próximo disponível está a até 33 km de
distância.

Uma pluma de água doce saindo de um rio, ou uma faixa de água sem oxigênio
junto a um recife raso, é exatamente o tipo de coisa que some quando você tira
a média de uma área de 28 por 28 km. É como tentar detectar uma poça medindo a
umidade média do bairro.

Então ficam **duas explicações vivas**, e nossos dados não escolhem entre elas:

1. Salinidade e oxigênio realmente não explicam o branqueamento brasileiro.
2. Eles explicam, mas o instrumento que usamos não os enxerga nessa escala.

**Afirmar a primeira sem mencionar a segunda seria desonesto.** O que dá para
dizer é a frase completa: *com dados de reanálise global, nessa resolução, não
há ganho.* Resolver isso exigiria sensores no próprio recife — que não existem
para esses 119 sítios naquele período.

### O que parecia sobrar: o vento — e a lição de checar

Entre todas as variáveis que não são temperatura, **uma parecia funcionar**: o
vento. Segunda mais importante do modelo, e na direção que faz sentido — mais
vento, menos branqueamento. Vento mexe a água, quebra a camada quente parada na
superfície e traz água mais fria de baixo.

Ficamos animados. Fomos criar conta num serviço europeu de dados de clima para
buscar vento de verdade.

**E aí veio a parte importante.**

Antes de escrever o programa que baixaria tudo, resolvemos fazer uma conferência
simples: pegar vento de verdade nos **mesmos 166 lugares e nas mesmas datas**, e
comparar com o número que o GCBD trazia.

Porque tinha uma coisa que ninguém tinha checado: **o "vento" que estávamos
usando era só uma coluna numa planilha.** Ninguém sabia de onde ela vinha nem se
descrevia mesmo o vento.

O resultado:

| | |
|---|---|
| Os dois medem a mesma coisa? | **Sim** — concordam bem |
| Os dois dizem que vento protege o coral? | **Não.** A planilha diz que sim; o vento de verdade não diz nada |

E quando trocamos um pelo outro dentro do modelo, ele ficou **pior do que não
ter vento nenhum**.

> **Ou seja: o vento não funcionava. Funcionava aquela coluna específica — e
> provavelmente por acaso.**

### Então o placar honesto é este

Testamos três coisas que não são temperatura: **salinidade, oxigênio e vento**.

As três descrevem o branqueamento — nos lugares que branquearam, as três
estavam diferentes, e na direção que a biologia previa. **Nenhuma das três
consegue prever.**

Não é o resultado que a gente queria. É o resultado que tem.

### E a lição vale mais que o vento

O ganho que o vento dava era de **0,025** numa escala em que nós mesmos já
tínhamos escrito, em outro documento, que *"diferença abaixo de 0,05 é ruído"*.

Sabíamos que era ruído. E mesmo assim viramos o projeto de cabeça para baixo
atrás dele — porque a explicação fazia sentido demais.

> **Explicação convincente é justamente o que faz um número de ruído parecer
> uma descoberta.** Foi barato descobrir isso: uma tarde e uma conta gratuita.
> Teria sido caro descobrir depois de escrever o programa inteiro.

### Uma coisa boa saiu disso

Descobrimos que **o tamanho do quadrado de 28 km não atrapalha para o vento** —
as duas fontes concordaram bem.

Isso melhora a nossa ressalva anterior. Antes dizíamos "28 km é grosseiro
demais". Agora dá pra dizer melhor: **28 km é grosseiro demais para coisas
irregulares e coladas na costa — como nutriente e oxigênio — mas serve bem para
coisas grandes e espalhadas, como vento e temperatura.**

Afirmação mais precisa, e sustentada por medição.

---

## 11. Última tentativa: poluição da água

Faltava testar uma coisa: **poluição**. Adubo de plantação, esgoto, água de rio.

E deu pra testar quase de graça — porque o mesmo arquivo de onde tiramos o
oxigênio já tinha, do lado, mais três medidas:

| | O que é |
|---|---|
| **Clorofila** | Quanta alga microscópica tem na água. Muita alga = água poluída |
| **Nitrato** | Adubo, de plantação e de esgoto |
| **Silicato** | Marca **água de rio** — rio traz silicato, mar aberto não tem |

O silicato era o que interessava, e por um motivo específico.

### A hipótese do rio

Água de rio é doce. Então, se rio chega no recife, a **salinidade** deveria
cair — e a salinidade não mostrou nada.

Mas talvez a salinidade seja um jeito ruim de detectar isso: chuva também
dessalga, o mar mistura rápido. **Silicato é outro jeito de perguntar a mesma
coisa**, e mais específico: rio carrega silicato de rocha moída, e o mar aberto
praticamente não tem.

Se silicato aparecesse onde salinidade falhou, aprenderíamos algo real.

### Não apareceu — e a hipótese caiu junto

**Nenhuma das três melhora a previsão.** Todas pioram.

E o silicato falhou de um jeito que vale explicar, porque é bonito de ver:

> Se o silicato estivesse marcando água de rio, ele teria que **subir quando a
> salinidade desce** — é a mesma água doce fazendo as duas coisas.
>
> Medimos: **os dois sobem juntos.** Exatamente o contrário.

Ou seja, o silicato que estamos medindo não é água de rio. É outra coisa —
provavelmente enriquecimento costeiro genérico, que sobe perto da costa por
vários motivos.

**A hipótese foi testada e não sobreviveu.** Que é o que se quer de uma
hipótese: que ela possa morrer.

### Um detalhe honesto que preciso registrar

Houve **uma** medida que passou no teste estatístico: a *variação* do silicato.
Nos recifes que branquearam, ele estava subindo mais.

Mas eu **não** vou chamar isso de descoberta, por dois motivos:

1. O resultado passou por muito pouco — ficou colado no limite.
2. Testamos **nove** medidas. Quando você testa nove coisas, é esperado que uma
   pareça significativa por puro acaso.

E o principal: **é exatamente o mesmo erro que cometi com o vento** ontem — pegar
um número fraco, achar uma explicação bonita e transformar em prioridade. Não
duas vezes no mesmo dia.

### 🚨 E aqui a ressalva do tamanho do quadrado é a pior de todas

Lembra dos quadrados de 28 km?

**Para nutriente, é o pior caso possível.** Uma mancha de adubo saindo de um rio
tem uns 2 ou 3 km, colada na praia. Medir isso pela média de 28 por 28 km é
como tentar achar uma mancha de café numa mesa medindo a cor média da mesa
inteira.

E tem evidência disso no próprio processo: em **84 das 498 buscas**, o
computador teve que procurar até **33 km de distância** do recife para achar um
quadrado que fosse mar e não terra.

> **Este é o resultado negativo menos confiável do projeto.** Ele não distingue
> "poluição não importa" de "não conseguimos enxergar poluição no tamanho certo".

### O placar final das variáveis que não são temperatura

| Testamos | Descreve o branqueamento? | Consegue prever? |
|---|---|---|
| Salinidade | sim | **não** |
| Oxigênio | sim | **não** |
| Vento | ~~sim~~ (era a coluna, não o vento) | **não** |
| Clorofila e nitrato | não | **não** |
| Silicato | mal e mal | **não** |

Quatro famílias testadas. **Nenhuma prevê.**

E as três explicações possíveis, sendo honesta — os dados não escolhem entre
elas:

1. Essas coisas realmente não preveem branqueamento no Brasil.
2. Preveem, mas nossos instrumentos são grossos demais para enxergá-las.
3. **166 mergulhos é pouco.** Só a temperatura aparece porque o efeito dela é
   grande. Um efeito médio ficaria invisível nesse tamanho de amostra.

A terceira vale para as outras duas. E ela não se resolve com dado novo de
satélite — se resolveria com **mais mergulhos**. Os do Brasil param em 2010.

---

## 12. O número que o site ia mostrar estava mentindo

Esta é a parte que quase foi para o ar errada.

### A promessa que uma porcentagem faz

O site vai mostrar algo como **"risco de branqueamento: 37%"**. Esse número faz
uma promessa bem específica, e verificável:

> Se você juntar todos os dias em que o site disse 37%, o alerta tem que ter
> acontecido em mais ou menos 37 de cada 100 deles.

Se acontecer em 5, o número é enfeite.

### E ele estava prometendo o dobro

Fomos conferir. Juntamos todos os dias, agrupamos pelo que o modelo tinha dito,
e olhamos o que de fato aconteceu:

| O modelo dizia | Aconteceu de verdade |
|---|---|
| 2,7% | 0,6% |
| 6,9% | 0,4% |
| **8,4%** | **0%** |
| 10,1% | 1,5% |
| 96,1% | 74,8% |

Na média, ele dizia **16,5%** quando a realidade era **8,4%**. Prometia o dobro.

Repare na linha do meio: nos dias em que o modelo disse "8,4% de risco",
**nunca** houve alerta. Nenhuma vez.

### Por que isso acontecia — e não era bug

Aqui está a parte interessante: **não era um defeito. Era um efeito colateral
conhecido de uma decisão que está certa.**

Lembra que só 8% dos dias têm alerta? Um modelo deixado sozinho aprende o
caminho preguiçoso: *"responder sempre não dá 92% de acerto"*. Para impedir
isso, dissemos a ele para tratar os dois casos como se fossem igualmente
comuns.

Funciona — ele passa a avisar. Mas, como consequência, **ele passa a achar que
alerta é muito mais comum do que é.** O número que ele cospe vem inflado.

Ou seja: a decisão de *quando avisar* ficou boa, e a de *quanto dizer* ficou
ruim. São duas coisas, e nós só tínhamos cuidado de uma.

### O outro número que nos enganou

Tem uma medida chamada **Brier**, que a gente vinha olhando. Estava em 0,043 —
parecia ótimo.

Só que o Brier mistura três coisas, e existe uma conta que as separa:

| Parte | O que mede | O nosso |
|---|---|---|
| Confiabilidade | se o número prometido bate | 0,0098 |
| Resolução | se o modelo separa os casos | 0,0493 |
| **Incerteza** | **o quanto o problema é difícil** | **0,0769** |

**A incerteza sozinha é o dobro do Brier inteiro.** Ou seja, aquele número bonito
vinha principalmente de o problema ser fácil de acertar por omissão — 92% dos
dias não têm nada acontecendo —, e não de o modelo ser bom.

> É como se orgulhar de acertar 92% das provas quando 92% das respostas são
> "não".

### O conserto

Existe uma técnica que pega a probabilidade torta e endireita: olha o histórico,
descobre que "quando ele diz 30%, na verdade acontece 8%", e passa a traduzir.

Resultado, na mesma tabela de antes:

| O modelo diz | Acontece de verdade |
|---|---|
| 0,3% | 0,3% |
| 8,1% | 7,9% |
| 72,3% | 73,7% |

O erro médio caiu de **8,1 pontos para 0,4** — vinte vezes menor.

⚠️ Um cuidado que precisou ser tomado: o tradutor é montado **usando só os anos
que o modelo estudou**, nunca o ano que está sendo testado. Senão ele estaria
consertando usando o gabarito, e a conferência sairia perfeita sem valer nada.

### E não custou nada em capacidade de avisar

Essa era a preocupação óbvia: se a probabilidade encolhe, o modelo não vai
deixar de avisar?

Não. Porque **o que ele fazia não era detectar mais — era gritar mais alto.**
Inflar a probabilidade equivale a baixar o ponto de corte sem dizer a ninguém.

Conferido:

| | Corte | Avisa quantos dos alertas reais |
|---|---|---|
| Antes | 50% | 90,9% |
| Depois | **20%** | **90,3%** |

Mesma detecção. O que mudou é que **agora o corte é uma decisão declarada**, e
não um efeito colateral escondido dentro do treino.

> **Probabilidade honesta para mostrar. Corte declarado para avisar.**
> São duas decisões, e agora estão em dois lugares.

### E achamos um defeito no nosso próprio medidor

Ao escrever os testes do medidor de calibração, um caso quebrou.

Se o modelo respondesse **sempre o mesmo número**, o medidor devolvia "erro
zero" — ou seja, **calibração perfeita**.

Mas um modelo que responde sempre 30% quando a realidade é 8% é o pior possível.
Ele passaria como o melhor.

O motivo era técnico e chato (o agrupamento colapsava quando não havia
variação), mas a lição não é: **o caso degenerado é justamente o que um medidor
existe para denunciar** — e era exatamente onde ele estava cego.

Corrigido, e travado com teste.

---

## 13. A pergunta que sobrou: a partir de quantos por cento o site avisa?

A seção anterior terminou com uma frase que parece encerrar o assunto e na
verdade abre outro:

> Probabilidade honesta para mostrar. **Corte declarado para avisar.**

O modelo agora diz "9%" e isso quer dizer mesmo 9%. Mas o site não pode exibir
só um número e ir embora — em algum momento ele precisa **decidir se acende a
luz**. E aí vem a pergunta: 9% é para avisar ou não?

### Essa pergunta não tem resposta técnica

Isso é o mais importante desta seção, e o que demorou para ficar claro.

Não existe um cálculo que produza "o limiar certo". O modelo entrega uma
probabilidade; onde traçar a linha depende de **quanto incômodo você aceita
para não perder um evento**. É uma escolha de produto, não de estatística.

E as duas pontas são ruins de formas diferentes:

| Se o corte for muito baixo | Se o corte for muito alto |
|---|---|
| O site avisa toda hora | O site quase nunca avisa |
| As pessoas param de olhar | Quando avisa, é tarde |
| O aviso vira ruído | Eventos passam batido |

O pior resultado dos dois é o mesmo: **ninguém confia no aviso**.

### O que o projeto estava usando, e por quê (spoiler: por acidente)

O site estava operando com **20%**. E ninguém tinha escolhido esse número.

Ele apareceu assim: o corte original era 50%, que é o padrão de qualquer
biblioteca. Mas — como a seção 12 conta — o modelo estava com um ajuste que
**empurrava todas as probabilidades para cima**. Então o "50%" daquele modelo
inflado se comportava, na prática, como um corte bem mais baixo. Quando
consertamos a probabilidade, tivemos que baixar o corte para 20% só para manter
o mesmo comportamento.

Ou seja: **20% era o número que reproduzia um acidente anterior.** Não era uma
decisão. Era uma herança.

### Como transformamos isso em algo decidível

O problema de tabelas de "precisão e revocação" é que ninguém consegue ter
opinião sobre elas. *"Precisão 0,719"* não é uma frase sobre a qual uma pessoa
pense "concordo" ou "discordo".

Então traduzimos tudo para unidades da vida real:

> **Quantos dias por ano, em cada recife, o site mostraria alerta sem que nada
> acontecesse?**

E medimos três coisas diferentes para cada corte possível, de 5% a 95%:

| O que medimos | A pergunta que responde |
|---|---|
| **Episódios detectados** | quantos eventos reais o site pegaria? |
| **Avisados no 1º dia** | de quantos ele avisaria logo no começo? |
| **Alarme falso** | quantos dias por ano ele grita à toa? |

### Por que "episódios" e não "dias"

Isso já apareceu na [seção 5](#5-por-que-contamos-eventos-e-não-dias), e aqui
importa de novo.

Um episódio de estresse térmico dura semanas. Se o site avisa no dia 3 de um
evento de 9 dias, ele **acertou o evento** — errou só alguns dias. Contar dias
puniria isso como se fosse erro grave, quando não é.

O que seria erro grave é o evento inteiro passar sem aviso nenhum.

### O primeiro achado: não é sobre o limiar

Rodamos os 19 cortes. E apareceu uma coisa que nenhum deles resolve:

> **Um episódio escapa em TODOS os cortes testados.**
> Picãozinho, 21 a 23 de abril de 2026. Três dias.

Mesmo baixando o corte para 5% — o ponto em que o site praticamente grita o
tempo todo — esse evento não é pego.

Isso muda a natureza da conversa. **Não é escolha de limiar que resolve; é o
modelo que não vê esse caso.** Discutir 10% contra 20% é discutir os *outros*
episódios. Aquele fica de fora de qualquer jeito, e continua como problema em
aberto.

> É o tipo de coisa que só aparece quando se mede o intervalo inteiro em vez de
> testar dois ou três valores. Se tivéssemos comparado só 20% e 30%, teríamos
> concluído "os dois perdem 3 eventos" sem nunca perceber que **um deles é
> impossível de pegar**.

### O segundo achado: eu tinha concluído errado

Esta parte fica registrada porque o erro é instrutivo.

Olhando a tabela, entre 15% e 40% a contagem de episódios **não muda**: são
sempre 16 de 19. Só o alarme falso diminui. A leitura óbvia é:

> "Nessa faixa, apertar o corte é de graça — pego os mesmos eventos e incomodo
> menos gente."

Foi o que escrevi. **Estava errado.**

Faltava medir uma coisa: **quando** o aviso chega.

| Corte | Eventos pegos | Avisados já no 1º dia | Atraso médio |
|---|---|---|---|
| 20% | 16/19 | **16 de 20** | 1,5 dia |
| 30% | 16/19 | 13 de 20 | 2,6 dias |
| 40% | 16/19 | 11 de 20 | 3,9 dias |

O evento continua sendo detectado — **mais tarde**. Em 40%, o aviso médio sai
quase **quatro dias** depois do começo do evento.

Para um sistema de aviso, isso é quase tudo. Avisar no quarto dia de um evento
de nove não é o mesmo que avisar no primeiro, mesmo que os dois contem como
"detectado" na planilha.

> **A lição de método:** quando uma métrica fica parada num intervalo, isso
> raramente significa "aqui não muda nada". Quase sempre significa **"aqui muda
> alguma coisa que essa métrica não mede"**.

### Um exemplo pequeno, para a ideia ficar concreta

Imagine um único episódio de **5 dias**, e o que o modelo respondeu em cada um:

| Dia do evento | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Probabilidade | 12% | 18% | 35% | 60% | 55% |

Agora veja o que cada corte faria:

| Corte | Dias em que avisa | Pegou o evento? | Avisou no 1º dia? |
|---|---|---|---|
| **10%** | 1, 2, 3, 4, 5 | ✅ sim | ✅ sim |
| **20%** | 3, 4, 5 | ✅ sim | ❌ dois dias tarde |
| **50%** | 4, 5 | ✅ sim | ❌ três dias tarde |

**Os três "pegaram o evento".** Na coluna de episódios, os três empatam.

Mas o de 10% avisou no dia 1 e o de 50% avisou no dia 4. Se alguém precisava
agir, essa diferença é o produto inteiro. E ela **não aparece** se você olhar
só a contagem de eventos.

Era exatamente esse o buraco na minha primeira conclusão.

### A decisão de 27/07: 10% — e por que ela foi revista

Com as três dimensões na mesa, escolhemos **10%**, declarando o critério
priorizar antecedência: este site existe para que alguém possa reagir, e um
aviso que chega tarde vale quase o mesmo que aviso nenhum.

🚨 **Depois descobrimos que a justificativa escrita estava errada.**

Registramos que 10% *"comprava o episódio de nove dias em Picãozinho, de
fevereiro/março de 2022"*. **Não comprava.** Conferindo episódio por episódio,
em vez de ler só a contagem total:

```
5%  -> pega 18 de 19   perde: Picãozinho, abril/2026 (3 dias)
10% -> pega 17 de 19   perde: Picãozinho, abril/2026 (3 dias)
                              Picãozinho, fev/2022  (9 dias)  <- também perde!
20% -> pega 16 de 19   perde: os dois acima
                              Porto de Galinhas, mai/2020 (1 dia)
```

O que 10% recuperava em relação a 20% era o episódio de **um dia** em Porto de
Galinhas. O de nove dias escapa nos dois.

⚠️ **O dado nunca esteve errado — a leitura esteve.** O programa já guardava
*quais* episódios cada corte perdia. A tabela do documento foi montada à mão a
partir do número total, e duas linhas trocaram de lugar. É a terceira vez que
este projeto comete o mesmo erro: **dado certo, leitura confortável**.

### A decisão de 30/07: quatro degraus em vez de um número

Ao revisar o critério, ficou claro que a pergunta *"a partir de quantos por
cento o site avisa?"* forçava uma escolha que não precisava ser feita.

Um corte único obriga a decidir entre **cobrir tudo** (avisar cedo, errar
muito) e **ser levado a sério** (avisar pouco, quase sempre acertar). Com mais
de um degrau, os dois objetivos deixam de competir:

| Degrau | A partir de | Dos avisos, quantos se confirmam | O que fazer |
|---|---|---|---|
| **Alerta alto** | 50% | **83%** | acionar com prioridade |
| **Alerta** | 20% | **72%** | acionar |
| **Observação** | 5% | 50% | acompanhar, sem mobilizar |
| Sem aviso | — | — | nada |

O degrau de **Observação** é o que alcança o teto do modelo: 18 dos 19
episódios. Metade dos seus avisos não se confirma, e ele existe justamente para
que **nada que o modelo alcança passe despercebido** — quem age só quando o
custo se justifica olha os degraus de cima.

📌 **Cada degrau carrega a ação esperada junto**, e não só a cor. Um selo
colorido sem instrução transfere para o leitor a decisão que o projeto deveria
ter tomado.

🚨 **E isso quase ficou só no papel.** Por um dia a escala existiu no servidor e
não na tela: o site recebia a instrução de cada degrau e a **descartava**,
mostrando só o nome e a cor. Corrigido em 31/07/2026 — a página de cada recife
agora mostra o degrau de hoje, o que fazer, e a escala inteira ao lado, para
quem lê um degrau do meio saber se ainda há algo pior a ser dito.

### O que essa decisão não resolve, e a gente não vai fingir que resolve

1. **O episódio de abril de 2026 continua escapando.** Nenhum corte o pega — o
   teto é do modelo, não da escolha.
2. **O de fevereiro de 2022 também**, em qualquer degrau acima de 5%. E 2022 já
   era o pior ano do modelo, o que liga os dois assuntos.
3. ⚠️ **Os cortes foram comparados usando os mesmos dados que os avaliaram.**
   Isso serve para escolher entre eles. **Não** é promessa de quantos alarmes
   falsos o ano que vem terá.

### E, principalmente: agora é uma decisão

O 20% original não era pior por ser 20%. Era pior por **ninguém saber por que
era 20%**.

Hoje a escala inteira está num lugar único, com o corte medido e a ação escrita
ao lado, viajando na resposta da API para quem consome poder discordar — e com
um comando que reconstrói a tabela quando alguém quiser rediscutir.

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
| 31/07/2026 | 🚨 **§13 corrigida — a justificativa escrita do limiar estava errada, e §2 ganhou a segunda régua.** O documento afirmava que o corte de 10% *"comprava o episódio de nove dias de Picãozinho, em 2022"*. **Ele também perde esse episódio.** O que 10% recuperava em relação a 20% era um episódio de **um dia** em Porto de Galinhas. O dado nunca esteve errado — o programa já guardava quais episódios cada corte perdia; a tabela do documento foi montada à mão a partir do total, e duas linhas trocaram de lugar. Terceira vez que este projeto comete o erro de *dado certo, leitura confortável*. Registrada também a decisão que substituiu o corte único: **quatro degraus**, cada um com o percentual de acerto medido e a ação esperada — com um número só era preciso escolher entre cobrir tudo e ser levado a sério. E §2 deixou de ter uma régua só: faltava a **regra que a NOAA já publica diariamente**, que é um piso mais alto que a previsão burra. Contra ela, o modelo pega dois episódios a mais e dispara o alarme cinco a sete vezes mais — a frase honesta é que ele é *mais sensível*, não *melhor*. |
| 27/07/2026 | **§13 criada — a decisão do limiar de alerta, explicada por inteiro.** Fecha o assunto que a §12 abriu: a probabilidade ficou honesta, mas faltava decidir a partir de quantos por cento o site acende a luz. Registrado que **essa pergunta não tem resposta técnica** — é troca entre incômodo e evento perdido, e portanto escolha de produto. Contado também que o 20% em uso **nunca havia sido escolhido**: era o número que reproduzia um acidente anterior, quando o modelo inflava as probabilidades. Dois achados: 🚨 **um episódio (Picãozinho, abril/2026) escapa em todos os 19 cortes testados**, então ali o teto é do modelo e não da escolha; e **eu havia concluído errado** que apertar o corte entre 15% e 40% era de graça — faltava medir *quando* o aviso chega, e ao medir os avisados no 1º dia caem de 16/20 para 11/20. Incluído um exemplo trabalhado de cinco dias mostrando três cortes que "pegam o evento" e avisam no dia 1, 3 e 4 — a diferença que a contagem de episódios não enxerga. Decisão: **10%**, com o critério declarado (priorizar antecedência) e o custo declarado (16 dias de alarme falso por ano em cada recife). |
| 27/07/2026 | **§12 criada — o número que o site ia mostrar estava mentindo.** Contada a promessa que uma porcentagem faz e por que ela não estava sendo cumprida: o modelo dizia 16,5% onde a realidade era 8,4%, e nos dias em que dizia "8,4%" **nunca** houve alerta. Explicado que não era bug e sim efeito colateral de uma decisão correta — mandar o modelo tratar as duas classes como igualmente comuns conserta *quando avisar* e estraga *quanto dizer*. Registrado por que o Brier de 0,043 enganava (a **incerteza sozinha é o dobro dele** — o problema é fácil de acertar por omissão), o conserto que levou o erro de 8,1 pontos a 0,4, e que **calibrar não custou detecção**, só mudou o corte de 50% para 20%. Fecha com o defeito encontrado no próprio medidor: predição constante dava "calibração perfeita", quando é o pior caso possível. |
| 27/07/2026 | **§11 criada — a última tentativa, poluição da água, também não deu.** Contada a hipótese do rio e por que ela caiu de um jeito verificável: se o silicato marcasse água de rio, teria que subir quando a salinidade desce, e **os dois sobem juntos**. Registrado, com o motivo, por que **não** estou chamando de descoberta a única medida que passou no teste estatístico — passou colado e foram nove medidas testadas, e seria repetir o erro do vento no mesmo dia. E que esta é a ressalva de resolução na sua forma pior: 28 km é o tamanho errado para uma mancha de rio de 2 km, com 84 das 498 buscas precisando ir a 33 km de distância. Fecha com o placar das quatro famílias testadas e as três explicações que os dados não separam — incluindo a de que **166 mergulhos é pouco**, que não se resolve com satélite. |
| 26/07/2026 | 🚨 **§10 corrigida — o vento também caiu, e a lição virou a parte principal.** Contada a conferência que derrubou a animação com o vento: o "vento" que o modelo usava era só uma coluna de planilha que ninguém tinha checado, e vento de verdade não mostra o efeito. Registrado o placar honesto — salinidade, oxigênio e vento descrevem o branqueamento, nenhum prevê — e a lição de que **explicação convincente é o que faz um número de ruído parecer descoberta**, já que o ganho de 0,025 estava abaixo do limiar de ruído que o próprio projeto tinha escrito. Acrescentado o achado positivo: 28 km serve para vento, então a ressalva de resolução passa a ser específica de variáveis irregulares e costeiras. |
| 26/07/2026 | **§10 criada — o resultado negativo, em linguagem comum.** Salinidade e oxigênio foram buscados (30.212 medições) e **não explicam o que a temperatura não explica**. Contadas as duas desculpas testadas e derrubadas (tamanho da janela; "só dizem qual recife é"), e a distinção que é o coração do resultado: **descrever não é prever** — as duas variáveis apontam para o lado certo com metade da força da temperatura, e isso não basta. Registrada a ressalva de resolução com a analogia da poça e da umidade do bairro, e o achado positivo: **o vento funciona**, e hoje o vento do projeto é um número inventado. |
| 26/07/2026 | **§9 criada — o resultado da segunda parte, em linguagem comum.** Por que a pergunta antiga era viciada (a resposta que o modelo adivinhava era feita de temperatura — analogia da régua feita de peso), e o que apareceu quando o alvo passou a ser branqueamento visto por mergulhador: **a regra da NOAA acerta 10 de 10 quando fala, mas fica calada em 78 dos 88 branqueamentos brasileiros**. Acrescentado também, em §3, o exemplo de quatro visitas mostrando por que esconder um recife e esconder um ano dão respostas diferentes, e por que a do ano é a honesta. |
| 25/07/2026 | Acrescentado, em §6 e §7, o resultado da medida de importância: a "receita" **não** se explica neste projeto, porque cada variável é medida duas vezes (nível e mudança) e as linhas individuais deixam de fazer sentido — analogia das duas colheres de sal. E o indício do oxigênio, que a §7 anunciava, **não se confirmou**. |
| 25/07/2026 | Documento criado como versão sem jargão da METODOLOGIA.md, para leitura e apresentação. Mesmo conteúdo, com analogias: previsão do tempo, prova com as questões vazadas, alarme de incêndio, receita e cozinheiro. |
