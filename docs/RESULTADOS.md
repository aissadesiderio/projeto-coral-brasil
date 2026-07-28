# Resultados

O desenho dos experimentos (a régua, a validação, as métricas e por que elas)
está em [METODOLOGIA.md](METODOLOGIA.md). Este documento é só o que saiu.

| Parte | O quê | Quando | Seções |
|---|---|---|---|
| **Entrega 1** | Prever o **BAA** em t+N, nos 3 recifes monitorados | 25/07/2026 | §1–§10 |
| **Entrega 2, passo 1** | Prever **branqueamento observado** com as térmicas do GCBD | 26/07/2026 | §11–§14 |
| **Entrega 2, passo 2** | Acrescentar **salinidade e oxigênio** ingeridos | 26/07/2026 | §15–§19 |

---

## Em uma frase, cada uma

> **Entrega 1** — Em 7 dias o modelo empata com a previsão burra no acerto
> diário, mas detecta 18 dos 19 episódios contra 15 dela; e em 14 dias passa a
> ganhar nas duas métricas.

> **Entrega 2, passo 1** — A regra de estresse térmico da NOAA, quando dispara,
> acerta quase sempre; mas dos 88 branqueamentos observados no Brasil ela pega
> **10**. O sinal térmico sozinho não explica o fenômeno.

> **Entrega 2, passo 2** — Salinidade e oxigênio de reanálise **não preenchem
> essa lacuna**: separam as classes na direção certa, com metade da força das
> térmicas, e não viram capacidade de prever. Quem funciona entre as não
> térmicas é o **vento**.

---

# Entrega 1 — previsão do BAA

Primeira execução completa, em **25/07/2026**.

---

## Entendendo o resultado, com números pequenos

Essa frase parece contraditória: como o modelo pode empatar e ganhar ao mesmo
tempo? A resposta é que **existem dois jeitos de contar acerto**, e eles não
dão o mesmo resultado. Um exemplo inventado, pequeno, mostra por quê.

Imagine um recife com **dois eventos** num ano:

| | Duração |
|---|---|
| Evento A | 60 dias |
| Evento B | 5 dias |

### Como a previsão burra se comporta

Ela olha o dia de hoje e repete: *"daqui a 7 dias vai estar igual"*.

- No **evento A**, depois que o alerta começa, ela acerta quase todos os 60
  dias — enquanto o alerta durar, "igual a hoje" está certo.
- No **evento B**, ela **nunca percebe nada**. O evento acaba antes de ela
  sequer entrar nele.

> Placar: **acertou 60 dias, perdeu 1 dos 2 eventos.**

### Como o modelo se comporta

Ele olha se a água está esquentando e tenta antecipar.

- No **evento A**, acerta o início mas erra alguns dias no meio — fica um pouco
  mais bagunçado.
- No **evento B**, ele **percebe**, porque viu a temperatura subindo antes.

> Placar: **acertou 55 dias, pegou os 2 eventos.**

### Quem ganhou?

| Jeito de contar | Previsão burra | Modelo |
|---|---|---|
| Contando **dias** | 60 ✅ | 55 |
| Contando **eventos** | 1 de 2 | **2 de 2** ✅ |

**Depende de como se conta.** E foi exatamente isso que aconteceu no dado real:
empate contando dias, vitória clara contando eventos.

### Qual das duas contas importa

**Contando eventos.** Se o recife entrou em alerta e ninguém foi avisado, não
adianta o sistema ter acertado 60 dias tranquilos antes.

É como um alarme de incêndio que fica corretamente quieto 364 dias por ano — e
não toca no dia do incêndio.

Por isso a contagem por episódio foi construída **antes** do modelo existir
([METODOLOGIA.md](METODOLOGIA.md) §6). Se a avaliação tivesse só a contagem
diária, a conclusão desta rodada teria sido *"o modelo não se justifica"* — e
seria uma conclusão errada, tirada da métrica errada.

### O segundo achado, no mesmo espírito

Rodamos o modelo também **sem** as features que dizem se a temperatura está
subindo ou descendo:

| | Com direção | Sem direção |
|---|---|---|
| Placar | **0,707** | 0,489 |

Sem saber a direção, o modelo fica **pior que a própria previsão burra**.

Ou seja: saber *"a temperatura está subindo"* é o que faz o modelo funcionar.
Saber apenas *"a temperatura é 29 °C"* não basta — porque 29 °C subindo e
29 °C caindo são situações opostas.

---

## 1. O que foi rodado

| | |
|---|---|
| Conjunto | 7.059 amostras, três recifes, 2020-01-01 → 2026-07-24 |
| Entradas | 10 — as 4 variáveis do baseline mais 6 features de trajetória |
| Alvo | `BAA ≥ 3` (Alerta Nível 1 ou acima) em `t + N` |
| Validação | *leave-year-out*, 5 anos com evento (2021 e 2023 não tiveram) |
| Modelos | regressão logística e *gradient boosting*, ambos nos padrões |

---

## 2. Horizonte de 7 dias

### Acerto diário — empate

| Modelo | F1 do modelo | F1 da persistência | |
|---|---|---|---|
| Logística | 0,707 | 0,738 | persistência ganha |
| **Boosting** | **0,741** | 0,738 | empate técnico |

**A diferença de 0,003 é ruído**, não vitória. Com 5 dobras e ~4 anos-evento
efetivos, nenhuma conclusão se sustenta nessa margem.

**Se a avaliação parasse aqui, a leitura seria "o modelo não se justifica".**

### Detecção de episódios — o modelo ganha

| | Episódios detectados |
|---|---|
| **Modelo (logística)** | **18 de 19** |
| Modelo (boosting) | 17 de 19 |
| Persistência | 15 de 19 |

Ano a ano, com o modelo logístico:

| Ano | Modelo | Persistência |
|---|---|---|
| 2020 | **6/6** | 4/6 |
| 2022 | 3/4 | **4/4** |
| 2024 | 3/3 | 3/3 |
| 2025 | **4/4** | 3/4 |
| 2026 | **2/2** | 1/2 |

### Por que as duas métricas discordam

O mecanismo está explicado com exemplo na seção
[Entendendo o resultado](#entendendo-o-resultado-com-números-pequenos), acima.
No dado real ele aparece assim: a persistência acerta muitos **dias** porque
episódio longo é estável no meio — o maior da série durou 117 dias — mas **não
vê o evento chegar**, e perde inteiros os que começam e terminam rápido.

É o comportamento que a [METODOLOGIA.md](METODOLOGIA.md) §2 previu antes de
qualquer modelo existir.

---

## 3. As features de trajetória são o que faz funcionar

Controle: mesmo modelo, mesmo horizonte, **sem** as 6 features de janela.

| | Com trajetória | Sem trajetória |
|---|---|---|
| F1 do modelo | **0,707** | 0,489 |
| Brier | **0,047** | 0,104 |
| Episódios | 18/19 | 15/19 |

**Sem trajetória o modelo é muito pior que a própria persistência** (0,489
contra 0,738) e a calibração piora por um fator de dois.

Isso confirma o raciocínio de [VARIAVEIS.md](VARIAVEIS.md) §3.6: o valor
instantâneo não diz a direção, e sem direção o modelo compete com a
persistência usando *menos* informação do que ela usa implicitamente.

**É o resultado mais sólido desta rodada** — a diferença é grande o bastante
para não ser ruído.

---

## 4. Horizonte de 14 dias — a vantagem cresce

| Modelo | F1 do modelo | F1 da persistência |
|---|---|---|
| Logística | 0,588 | 0,570 |
| **Boosting** | **0,628** | 0,570 |

Os dois superam a persistência, e a margem é maior que em 7 dias.

**O motivo é que a persistência degrada mais rápido que o modelo.** Quanto mais
longe o horizonte, menos "vai continuar igual" funciona — e mais vale ter
aprendido a trajetória. Em 2026, ano de episódios curtos, a persistência caiu
para F1 0,118 enquanto o boosting ficou em 0,500.

Isso sugere que **o horizonte útil do produto pode ser maior que 7 dias**, o
que é bom: 14 dias de antecedência tem mais valor prático de manejo.

---

## 5. Calibração

Brier score do boosting em 7 dias: **0,038**.

Para dar escala: um modelo que respondesse sempre "8,4% de chance" — a taxa
base — teria Brier de **0,077**. O modelo está em cerca de metade disso.

Isso importa porque o painel vai exibir "risco: 37%", e esse número precisa
querer dizer que em 100 dias parecidos o evento aconteceu em ~37.

⚠️ **Brier bom não é prova de calibração boa.** O próximo passo é a curva de
calibração por faixa de probabilidade, que ainda não foi feita.

---

## 6. Onde o modelo falha: 2022

| Ano | PR-AUC | F1 modelo | F1 persistência |
|---|---|---|---|
| 2024 | 0,973 | 0,907 | 0,922 |
| 2020 | 0,956 | 0,773 | 0,821 |
| 2025 | 0,895 | 0,831 | 0,840 |
| 2026 | 0,607 | 0,548 | 0,471 |
| **2022** | **0,371** | **0,476** | 0,636 |

**2022 é o pior ano do modelo por larga margem**, e é o único em que a
persistência ganha na detecção de episódios (4/4 contra 3/4).

Uma hipótese ainda não testada: 2022 é o único ano da série cujos episódios
ocorreram em **Abrolhos e Picãozinho, mas não em Porto de Galinhas**. Se o
modelo aprendeu um padrão de evento sincronizado nos três recifes, um ano em
que isso não vale seria justamente onde ele erra.

Não é conclusão — é a próxima coisa a medir.

---

## 7. Importância das variáveis — e o indício do oxigênio **não** se confirmou

⚠️ **Os números desta seção são da versão C** (10 entradas), que era o padrão
quando a medição foi feita. O padrão mudou para a versão D em 25/07/2026 — ver
§8 para os números atuais. Esta seção fica como registro do percurso: foi ela
que revelou a colinearidade que a §8 diagnosticou.

Medida em 25/07/2026, dentro do *leave-year-out*: para cada ano com evento,
treina sem ele e mede a importância **nele**. Duas medidas, porque uma sozinha
engana — ver [METODOLOGIA.md](METODOLOGIA.md) §5.

### Por grupo (variável + suas trajetórias, embaralhadas juntas)

Queda média do PR-AUC ao destruir a informação daquele grupo:

| Grupo | Logística | Boosting |
|---|---|---|
| **DHW** | **+0,492** | **+0,554** |
| **SST** | **+0,276** | **+0,157** |
| Oxigênio | +0,021 | +0,017 |
| Salinidade | −0,002 | +0,025 |

**As variáveis térmicas carregam praticamente tudo.** Juntas, DHW e SST
respondem por mais de 95% da capacidade preditiva do modelo.

### O indício do oxigênio não sobreviveu

Em [VARIAVEIS.md](VARIAVEIS.md) §3.6 medimos que a **trajetória** do oxigênio
separava início de fim de episódio em 0,61 σ — melhor que a do DHW — e
registramos que aquilo *"precisa ser confirmado no modelo treinado"*.

**Não se confirmou.** No modelo, a trajetória do oxigênio contribui:

| | Logística | Boosting |
|---|---|---|
| `oxigenio` (nível) | +0,021 | +0,021 |
| `oxigenio_variacao_7d` (trajetória) | **−0,001** | **−0,006** |

Negativo significa que embaralhar a coluna **melhorou levemente** o modelo — ou
seja, ela é ruído.

O **nível** de oxigênio contribui algo pequeno e consistente nos dois modelos.
A **trajetória**, nada.

Três explicações possíveis, nenhuma testada ainda:

1. A separação de 0,61 σ foi medida em 95 e 96 amostras. Pode ter sido ruído
   desde o início.
2. A informação existe mas é **redundante**: oxigênio dissolvido depende
   fortemente da temperatura, e o modelo já tem SST e DHW.
3. Separar dois grupos não é o mesmo que ajudar a prever — a primeira medida
   olhou só as transições, a segunda olha o ano inteiro.

**Registrar isso importa mais do que teria importado a confirmação.** Era o
primeiro indício de variável não-térmica no projeto, e ele não passou no teste
seguinte. A pergunta da entrega 2 continua em aberto, e agora com uma
expectativa menor.

### A correlação divide o crédito — e dá para ver

O grupo DHW cai +0,492, mas suas colunas isoladas somam bem menos:

| | Queda |
|---|---|
| `dhw` sozinho | +0,003 |
| `dhw_variacao_7d` sozinho | +0,092 |
| `dhw_variacao_14d` sozinho | +0,189 |
| **soma das três** | **+0,284** |
| **grupo inteiro** | **+0,492** |

Embaralhar uma coluna por vez subestima, porque as irmãs correlacionadas ainda
carregam parte da informação. **É por isso que a medida por grupo existe** — e
por que ler só a coluna isolada levaria à conclusão errada de que o `dhw` não
importa.

### ⚠️ Os coeficientes **não** são interpretáveis aqui

Isto corrige uma afirmação anterior deste projeto.

Coeficientes da logística, na escala padronizada:

| Variável | Coeficiente | |
|---|---|---|
| `sst` | +3,259 | |
| `dhw_variacao_14d` | +2,258 | |
| `oxigenio` | +1,333 | ⚠️ sinal contraintuitivo |
| `dhw` | **−0,164** | 🚨 **negativo** |

Ler isso como mecanismo daria duas conclusões absurdas: que **calor acumulado
reduz o risco** e que **mais oxigênio aumenta o risco**.

Nenhuma das duas é verdade. O que acontece é **colinearidade**: `dhw` e
`dhw_variacao_14d` andam juntos, o modelo usa a trajetória, e o coeficiente do
nível vira um termo de correção sem significado físico isolado.

#### Por que a colinearidade produz coeficiente absurdo

Suponha a verdade `risco = 2 × dhw`, e que na nossa série a variação seja
aproximadamente **metade** do dhw. Então estas três fórmulas são
**numericamente equivalentes**:

| Fórmula | Verificação |
|---|---|
| `2·dhw + 0·variação` | = 2·dhw |
| `0·dhw + 4·variação` | = 4·(dhw/2) = 2·dhw |
| **`−2·dhw + 8·variação`** | = −2·dhw + 4·dhw = **2·dhw** |

As três dão **exatamente a mesma predição**. O otimizador escolhe uma conforme
a regularização e o ruído da dobra — e nada impede que escolha a terceira, em
que o coeficiente do nível é negativo.

> **A predição não está errada. O que não é identificável é o coeficiente.**

É por isso que a queda por permutação **por grupo** (+0,492 para o DHW) é
confiável enquanto o coeficiente individual não é: a permutação mede o efeito
de destruir a informação, que é único; o coeficiente mede uma repartição, que
não é.

**Consequência para o trabalho:** o argumento de que "a logística é
interpretável" — registrado em [METODOLOGIA.md](METODOLOGIA.md) §5 — **só vale
com features não correlacionadas**. As nossas são correlacionadas por
construção: cada variável entra junto com a própria trajetória.

Para afirmar direção de efeito seria preciso ou remover a correlação (usar só
nível *ou* só trajetória), ou usar uma medida que a trate explicitamente. Até
lá, **a importância por grupo é a única leitura defensável**, e ela não dá
direção — só magnitude.

---

## 8. A colinearidade — o diagnóstico estava errado

Experimento rodado em 25/07/2026. **Ele derrubou a hipótese que este documento
registrava**, e vale começar por isso.

### O que eu supunha, e o que foi medido

A §7 dizia que a colinearidade vinha de *"cada variável entrar junto com a
própria trajetória"*. **Falso.** Correlação medida:

| Par | r |
|---|---|
| `sst` × `sst_variacao_7d` | +0,104 |
| `dhw` × `dhw_variacao_7d` | +0,107 |
| `oxigenio` × `oxigenio_variacao_7d` | +0,100 |
| `salinidade` × `salinidade_variacao_7d` | +0,253 |

Nível e trajetória **quase não se correlacionam** — o que, pensando depois, é
óbvio: saber que o DHW está em 8 diz pouco sobre ele ter subido ou descido.

A colinearidade real está em outro lugar:

| Par | r |
|---|---|
| `dhw_variacao_7d` × `dhw_variacao_14d` | **+0,976** |
| `sst_variacao_7d` × `sst_variacao_14d` | **+0,704** |

**São as duas janelas da mesma variável.** A variação em 14 dias contém a de 7
dias — a de 14 é quase a de 7 vezes dois. Estávamos medindo a mesma coisa duas
vezes, mas não no eixo que eu supunha.

### As cinco versões testadas

Regressão logística, horizonte 7 dias, mesmo *leave-year-out*:

| Versão | Entradas | F1 | PR-AUC | Brier | Episódios | Coef. térmico invertido |
|---|---|---|---|---|---|---|
| A — só níveis | 4 | 0,489 | 0,676 | 0,104 | 15/19 | 0 |
| B — só trajetórias (7d e 14d) | 6 | 0,731 | 0,757 | 0,044 | 17/19 | 1 |
| C — ambos *(no ar hoje)* | 10 | 0,707 | 0,760 | 0,047 | **18/19** | 1 |
| **D — só trajetórias de 7d** | **4** | **0,728** | **0,790** | **0,043** | 16/19 | **0** |
| E — níveis + trajetória 7d | 8 | 0,674 | 0,791 | 0,049 | 17/19 | 1 |

### O que isso resolve

**A versão D elimina o problema.** Com uma janela só por variável, a
correlação de 0,976 desaparece e os coeficientes voltam a fazer sentido físico:

| Variável | Coeficiente |
|---|---|
| `dhw_variacao_7d` | **+4,475** |
| `sst_variacao_7d` | +0,145 |
| `salinidade_variacao_7d` | +0,082 |
| `oxigenio_variacao_7d` | −0,079 |

Todos os térmicos positivos, com o DHW dominando — exatamente o que a física
prevê. **Nenhum sinal invertido.**

E ela não custa desempenho: F1 **0,728** contra 0,707 da versão atual, com o
**melhor PR-AUC de todas** (0,790) e a melhor calibração (0,043) — usando
**4 entradas em vez de 10**.

### O custo, e a decisão que ele exige

D detecta **16 episódios de 19**, contra 18 da versão C.

Essa é a única métrica em que C ganha, e é justamente a que este projeto
declarou ser a mais importante ([METODOLOGIA.md](METODOLOGIA.md) §6).

| | Interpretável | Episódios |
|---|---|---|
| **D** — 4 entradas | ✅ sim | 16/19 |
| **C** — 10 entradas | ❌ não | **18/19** |

⚠️ **Dois episódios em 19, com ~4 anos-evento efetivos, está dentro do ruído**
que este documento define como limite (§9). Não é diferença que sustente
escolha sozinha.

**Recomendação: adotar D.** Um modelo que se explica vale mais que dois
episódios de vantagem dentro da margem de erro — e a versão C não permite
afirmar direção de efeito nenhuma, que era o objetivo original do experimento.

### ✅ Aplicada ao código em 25/07/2026

`FEATURES_PADRAO` passou a ser vazio e `janelas_para` a gerar **uma janela por
variável**. O padrão do projeto agora é:

```
sst_variacao_7d, dhw_variacao_7d, salinidade_variacao_7d, oxigenio_variacao_7d
```

Um teste trava a regra (`test_uma_janela_por_variavel_e_so_uma`), com a
referência a esta seção — para que ninguém acrescente a segunda janela de novo
sem esbarrar no motivo.

### O que a mudança revelou na leitura

Com uma coluna por variável, **a importância por coluna e por grupo passam a
coincidir** — a repartição de crédito some junto com a colinearidade. E o
retrato fica muito mais direto:

| Variável | Queda do PR-AUC | Coeficiente |
|---|---|---|
| **`dhw_variacao_7d`** | **+0,670** | **+4,445** |
| `sst_variacao_7d` | +0,004 | +0,127 |
| `salinidade_variacao_7d` | +0,000 | +0,085 |
| `oxigenio_variacao_7d` | −0,001 | −0,090 |

**Todos os coeficientes agora fazem sentido físico**, e nenhum está invertido.

Mas o retrato honesto é mais duro do que o da versão C sugeria:

> 🚨 **O modelo é, essencialmente, um modelo da trajetória do DHW.** Sozinha,
> ela responde por praticamente toda a capacidade preditiva. SST contribui
> quase nada; salinidade e oxigênio, nada.

Na versão C esse fato ficava disfarçado, repartido entre dez colunas
correlacionadas. Ele não mudou — só ficou visível.

**Consequência para a entrega 2:** com os dados atuais, a resposta a *"variáveis
não térmicas acrescentam sinal?"* é **não**. Isso reforça, e não enfraquece, a
necessidade do GCBD: enquanto o alvo for o BAA — que é definido a partir de
temperatura —, é pouco provável que qualquer outra variável apareça.

---

## 9. O que **não** se pode concluir

Estes números orientam decisão de projeto. Não sustentam afirmação científica.

1. **São 5 dobras sobre ~4 anos-evento correlacionados.** Os episódios caem nos
   mesmos anos nos três recifes ([VARIAVEIS.md](VARIAVEIS.md) §7.2). Diferença
   de F1 abaixo de ~0,05 é ruído.
2. **Nenhum hiperparâmetro foi ajustado, e isso foi deliberado.** Com essa
   base, ajuste fino seria sobreajuste disfarçado de melhoria.
3. **O alvo continua sendo o BAA, não branqueamento observado.** O produto
   honesto ainda se chama *previsão de estresse térmico*. A pergunta científica
   — se salinidade e oxigênio acrescentam sinal — exige o GCBD (entrega 2).
4. **A importância das variáveis não foi medida.** Saber que a trajetória ajuda
   não diz *qual* trajetória ajudou. A medição de [VARIAVEIS.md](VARIAVEIS.md)
   §3.6 sugere SST e oxigênio, mas isso precisa ser confirmado no modelo
   treinado.

---

## 10. Próximos passos que estes resultados indicam

| Prioridade | O quê | Por quê |
|---|---|---|
| ✅ feito | ~~Importância das variáveis~~ | Feito em 25/07/2026 (§7): derrubou o indício do oxigênio e revelou que os coeficientes não são interpretáveis |
| ✅ feito | ~~Diagnosticar a colinearidade~~ | Feito (§8): a causa é a dupla janela 7d/14d (r = 0,976), não nível×trajetória como se supunha |
| ✅ feito | ~~Aplicar a versão D ao código~~ | Aplicada em 25/07/2026: 4 entradas, coeficientes íntegros, teste travando a regra |
| ✅ feito | ~~GCBD, passo 1~~ | Feito em 26/07/2026 (§11 e §12): o sinal térmico sozinho **não** explica o branqueamento observado no Brasil |
| **Alta** | **GCBD, passo 2 — ingerir salinidade e O₂** | §11 mudou a resposta: com rótulo observado, sobra o que explicar. Ver [GCBD.md](GCBD.md) |
| Alta | Investigar 2022 | É o único ano em que o modelo perde claramente |
| Média | Curva de calibração | Brier bom não basta para exibir porcentagem num site |
| Média | Testar horizontes entre 7 e 21 dias | A vantagem cresce com o horizonte; achar onde ela vira |
| Baixa | Ajuste de hiperparâmetro | Só faz sentido depois de ampliar a base com o GCBD |

---

# Entrega 2, passo 1 — branqueamento observado

Rodado em **26/07/2026**. Muda o alvo: de **BAA** (um rótulo que a NOAA calcula
a partir de temperatura) para **coral branqueado contado por mergulhador**.

A troca importa porque a pergunta central do projeto estava mal posta na
entrega 1. Perguntar "variáveis não térmicas ajudam a prever o BAA?" era
circular — o BAA é térmico por construção. Ver [GCBD.md](GCBD.md).

**Não houve ingestão.** Este passo usa só as variáveis térmicas que já vêm no
arquivo do GCBD, exatamente como o plano previa.

---

## 11. O resultado que muda o projeto

> **A regra de estresse térmico da NOAA, quando dispara, acerta quase sempre —
> mas ela quase nunca dispara. Dos 88 branqueamentos observados no Brasil, ela
> pega 10.**

### 11.1 O conjunto

| | |
|---|---|
| Linhas brasileiras utilizáveis | 313 |
| **Visitas** (unidade amostral real) | **166** |
| Sítios | 119 |
| Positivos (`Percent_Bleaching` > 0%) | **88 — 53,0%** |
| Período | 1994–2010 |

🚨 **São 166 visitas, não 313 amostras.** O GCBD traz uma linha por substrato
amostrado (`Hard Coral`, `Nutrient Indicator Algae`, `Fleshy Seaweed`). Dentro
de uma visita, as térmicas e o `Percent_Bleaching` são **idênticos** —
conferido: **0 de 166 visitas divergem no alvo**. Tratar linha como amostra
inflaria n em 1,9× sem acrescentar informação nenhuma, e ainda poria cópias da
mesma visita nos dois lados da validação.

Isso corrige o "313 amostras utilizáveis" do levantamento inicial.

### 11.2 A linha de base: a regra publicada da NOAA

`TSA_DHW ≥ 4` → Alerta Nível 1, branqueamento esperado. É o piso a ser batido,
o mesmo papel que a persistência teve na entrega 1.

| Métrica | Valor |
|---|---|
| Precisão | **1,000** |
| Revocação | **0,114** |
| F1 | 0,204 |
| Verdadeiros positivos | 10 |
| Falsos positivos | **0** |
| Falsos negativos | **78** |
| `TSA_DHW = 0` em | **87,3% das visitas** |

**Lido em palavras:** quando o DHW acumula estresse suficiente, houve
branqueamento — em 10 de 10 casos. Mas **78 dos 88 branqueamentos observados
aconteceram com `TSA_DHW = 0`**, isto é, sem nenhum estresse térmico acumulado
pelo critério da NOAA.

> O estresse térmico por DHW é **suficiente, mas está longe de ser necessário**
> para o branqueamento observado nos recifes brasileiros.

Esta é a frase mais importante que o projeto produziu até aqui, e ela só pôde
aparecer porque o alvo deixou de ser térmico.

### 11.3 O modelo, e o contraste que decide tudo

A validação é cruzada e **agrupada** — nunca aleatória. Duas versões, porque
respondem perguntas diferentes:

- **agrupado por sítio:** "generaliza para um **recife novo**?"
- **agrupado por ano:** "generaliza para um **evento novo**?"

Logística, as 8 térmicas do dia:

| | por **sítio** | por **ano** |
|---|---|---|
| PR-AUC | **0,803** | **0,614** |
| ganho sobre o acaso | 1,51× | 1,16× |
| F1 | 0,686 | 0,534 |
| Acurácia | 0,675 | **0,506** |
| *(classe majoritária)* | *0,530* | *0,530* |

🚨 **Agrupado por ano, a acurácia (0,506) fica abaixo da classe majoritária
(0,530).** Responder sempre "não branqueou" acertaria mais.

Boosting melhora, mas não muda a forma:

| Modelo | PR-AUC sítio | PR-AUC ano |
|---|---|---|
| logística | 0,803 | 0,614 |
| **boosting** | **0,867** | **0,683** |

O boosting ganhar aqui é o oposto da entrega 1, e faz sentido: as classes estão
equilibradas (53%), a relação com o DHW tem limiar, e a árvore acha interação.

### 11.4 Por que o número do "ano" é o que importa — com números pequenos

A diferença entre 0,803 e 0,614 não é detalhe técnico. Ela é o resultado.

Imagine dois recifes vizinhos, **A** e **B**, visitados em 2005 e em 2010.

| Visita | Recife | Ano | Anomalia térmica | Branqueou? |
|---|---|---|---|---|
| 1 | A | 2005 | +1,2 °C | sim |
| 2 | B | 2005 | +1,2 °C | sim |
| 3 | A | 2010 | +0,3 °C | sim |
| 4 | B | 2010 | +0,3 °C | sim |

Em 2005 branqueou com muito calor. Em 2010 branqueou com pouco — porque naquele
ano houve, digamos, uma pluma de água doce que o modelo não vê.

**Agrupando por sítio:** deixo o recife B de fora. Treino nas visitas 1 e 3 (do
A), testo nas 2 e 4 (do B). Mas as visitas 1 e 2 são o *mesmo ano*, com a
*mesma anomalia*. O modelo já viu 2005 e já viu 2010 — só não viu aquele
pedaço de mapa. **Ele acerta as duas.** Parece ótimo.

**Agrupando por ano:** deixo 2010 inteiro de fora. Treino nas visitas 1 e 2, em
que branqueamento veio com +1,2 °C. Testo nas 3 e 4, em que veio com +0,3 °C.
O modelo aprendeu "calor alto → branqueia", vê +0,3 e responde "não". **Erra as
duas.**

O modelo não era bom; ele estava **reconhecendo o ano**, não o fenômeno. E como
o que o site precisa fazer é avisar sobre um evento **futuro**, que por
definição ainda não está no treino, o número honesto é o do ano.

É a mesma lógica que a entrega 1 aplicou ao proibir divisão aleatória em série
temporal ([METODOLOGIA.md](METODOLOGIA.md) §3) — aqui ela só reaparece numa
base transversal.

### 11.5 O que **não** ajudou

| Conjunto | n | PR-AUC sítio | PR-AUC ano | taxa base |
|---|---|---|---|---|
| 8 térmicas do dia | 166 | 0,803 | 0,614 | 0,530 |
| \+ 23 de climatologia do sítio (31) | 166 | 0,842 | 0,662 | 0,530 |
| \+ 4 de contexto (12) | **148** | 0,628 | **0,457** | 0,473 |
| \+ climatologia e contexto (35) | 148 | 0,704 | 0,465 | 0,473 |

**A climatologia do sítio quase não acrescenta.** São 23 colunas a mais — 
`TSA_Mean`, `SSTA_Maximum`, os desvios-padrão — e o ganho por ano é de 0,614
para 0,662, com a acurácia caindo para 0,488. Elas descrevem o *lugar*, não a
*visita*: são constantes dentro de cada sítio.

🚨 **O contexto do sítio piora, e muito.** Profundidade, distância da costa,
turbidez e frequência de ciclones levam a PR-AUC por ano a **0,457, abaixo da
própria taxa base (0,473)** — pior que sortear. E ainda custam 18 visitas,
porque `Depth_m` falta em 18 delas.

Isso é resultado, não fracasso: com 166 visitas, cada coluna a mais é um grau
de liberdade que a amostra não sustenta.

### 11.6 O limiar de branqueamento importa

`Percent_Bleaching > 0%` é uma escolha, e ela foi declarada. Vale mostrar o
efeito:

| Limiar | Positivos | Taxa base | PR-AUC ano | ganho |
|---|---|---|---|---|
| **> 0%** | 88 | 0,530 | 0,717 | 1,35× |
| > 10% | 27 | 0,163 | 0,398 | 2,45× |

Duas leituras opostas do mesmo modelo: em valor absoluto ele é muito pior para
branqueamento severo (0,398 contra 0,717); em ganho relativo, muito melhor
(2,45× contra 1,35×), porque o evento é raro.

⚠️ **O equilíbrio de 53% não é artefato do limiar.** Dos 88 positivos, só **2
têm menos de 0,1%** de colônias branqueadas, e a mediana deles é **5%**. A
preocupação registrada em [GCBD.md](GCBD.md) — de que "0,1% não é o mesmo
fenômeno que 85%" — foi medida e não se confirmou como problema.

---

## 12. A colinearidade voltou — e a versão interpretável

Os coeficientes das 8 térmicas saíram invertidos, o mesmo defeito de §8:

| Variável | Coeficiente | |
|---|---|---|
| `TSA_DHW` | +1,264 | |
| `SSTA_Frequency` | +0,874 | |
| `TSA_Frequency` | **−0,786** | 🚨 invertido |
| `TSA` | +0,694 | |
| `SSTA` | **−0,577** | 🚨 invertido |
| `SSTA_DHW` | **−0,320** | 🚨 invertido |
| `Windspeed` | −0,150 | esperado — vento resfria |
| `Temperature_Kelvin` | **−0,136** | 🚨 invertido |

`SSTA = −0,58` afirma que **anomalia quente de SST protege o coral**. É
fisicamente falso.

### 12.1 A causa, medida

| Par | r |
|---|---|
| `SSTA_Frequency` × `TSA_Frequency` | **0,881** |
| `Temperature_Kelvin` × `TSA` | **0,881** |
| `SSTA_DHW` × `TSA_DHW` | 0,693 |
| `SSTA` × `TSA` | 0,649 |

Fator de inflação de variância (VIF acima de 5 já é sinal de alerta):

| Variável | VIF |
|---|---|
| `SSTA_Frequency` | **11,72** |
| `TSA` | **9,63** |
| `TSA_Frequency` | **7,85** |
| `SSTA_DHW` | 5,60 |
| `Temperature_Kelvin` | 5,31 |

A razão é estrutural, não acidental: o GCBD traz **duas famílias de anomalia**
para a mesma coisa. `SSTA` é a anomalia contra a média do mês; `TSA` é a
anomalia contra o **máximo** da climatologia mensal. São duas réguas do mesmo
calor — e o modelo não consegue repartir crédito entre elas.

### 12.2 Sete versões comparadas

Logística, PR-AUC agrupada:

| Versão | Features | sítio | **ano** | invertidos |
|---|---|---|---|---|
| A — as 8 | 8 | 0,803 | 0,614 | **4** |
| F — `TSA_DHW`+`SSTA_Freq`+`TSA`+`SSTA` | 4 | 0,769 | **0,732** | 2 |
| G — F sem `SSTA` | 3 | 0,703 | 0,686 | 1 |
| H — G + `Windspeed` | 4 | 0,718 | 0,692 | 1 |
| I — `TSA_DHW`+`TSA` | 2 | 0,699 | 0,692 | **0** |
| ~~J — `TSA_DHW`+`TSA`+`Windspeed`~~ | 3 | 0,722 | 0,717 | 0 |
| K — `TSA_DHW`+`SSTA_Freq`+`Windspeed` | 3 | 0,750 | 0,706 | 1 |

~~**A versão J é a adotada como conjunto interpretável.**~~ Três entradas,
nenhum coeficiente invertido:

| Variável | Coeficiente | Leitura física |
|---|---|---|
| `TSA_DHW` | **+0,950** | estresse térmico acumulado piora |
| `Windspeed` | −0,355 | vento mistura a coluna d'água e resfria — negativo é o esperado |
| `TSA` | +0,210 | anomalia térmica do dia piora |

🚨 **Superado em 27/07/2026.** A versão adotada passou a ser a **I —
`TSA_DHW` + `TSA`**, com o `Windspeed` removido. O motivo não é métrica (custa
0,025, dentro do ruído) e sim que o efeito do vento **não sobrevive à troca por
vento medido**. Ver §20 e §20.1.

E o mais revelador: **sítio 0,722 contra ano 0,717.** A diferença sumiu. A
versão A tinha um abismo (0,803 × 0,614); a J generaliza igualmente bem para um
recife novo e para um ano novo — que é a assinatura de um modelo que aprendeu o
fenômeno em vez de decorar os eventos.

Importância por permutação, medida fora da dobra (agrupado por ano):

| Variável | Queda do PR-AUC |
|---|---|
| `TSA_DHW` | +0,1002 |
| `Windspeed` | +0,0728 |
| `TSA` | +0,0064 |

**`Windspeed` é a segunda variável mais útil** — e ela não é térmica. É o
primeiro indício, em todo o projeto, de que algo além de temperatura carrega
sinal sobre branqueamento.

### 12.3 ⚠️ A ressalva de seleção

**As métricas da versão J são otimistas.** O conjunto foi escolhido olhando a
mesma validação que o avalia; sobre 166 visitas isso é viés real, não teórico.

Por isso:

- **A versão A (as 8 térmicas) é a que se relata sem ressalva.** Ela é o que o
  GCBD oferece, sem escolha nossa. É o padrão do código (`FEATURES_PADRAO`).
- **A versão J é o conjunto interpretável**, disponível em
  `FEATURES_INTERPRETAVEIS` e no `--interpretavel`, com esta ressalva anexada.
- **As conclusões de §11 não dependem da escolha:** a regra da NOAA pega 10 de
  88 em qualquer versão, e o abismo sítio×ano aparece em todas as sete.

Confirmar a versão J exigiria um conjunto de teste que não participou da
escolha. Com 166 visitas, ele não existe — e inventá-lo dividindo mais seria
trocar um viés por outro.

---

## 13. O que este passo permite e não permite concluir

**Permite:**

1. A regra publicada da NOAA, aplicada ao Brasil, **perde 78 de 88 eventos**.
2. Modelos treinados só com térmicas ficam entre 1,16× e 1,35× o acaso quando
   testados num ano que não viram.
3. **Sobra o que explicar** — que é exatamente a premissa do projeto, e que a
   entrega 1 não tinha como testar.

**Não permite:**

1. **Dizer que salinidade e oxigênio explicam o resto.** Eles não foram
   medidos aqui. O que se mostrou é que há espaço, não quem o ocupa.
2. **Estender ao presente.** O dado brasileiro do GCBD termina em **2010**.
   Nada dos eventos de 2020 ou 2024 tem rótulo observado.
3. **Falar de Picãozinho.** O sítio GCBD mais próximo está a 198 km.
4. **Tratar 166 visitas como amostra grande.** Diferença de PR-AUC abaixo de
   ~0,05 entre versões é ruído.

---

## 14. O próximo passo, agora com motivo medido

O passo 2 do plano de [GCBD.md](GCBD.md) — ingerir salinidade e oxigênio numa
janela de 90 dias antes de cada visita — deixou de ser "seria interessante" e
passou a ter uma lacuna quantificada para preencher:

> 78 branqueamentos observados sem nenhum estresse térmico acumulado.

O custo continua o mesmo: **35.460 medições**, menos que o backfill do
Copernicus já feito. E agora a comparação tem um baseline forte e medido, que
era a razão de fazer o passo 1 antes.

*(Executado em 26/07/2026 — ver §15 em diante.)*

---

# Entrega 2, passo 2 — salinidade e oxigênio

Rodado em **26/07/2026**, no mesmo dia do passo 1. É a pergunta que motivou o
projeto inteiro, feita pela primeira vez sem circularidade: com **branqueamento
observado** como alvo, e com as variáveis não térmicas efetivamente medidas.

**30.212 valores diários extraídos**, 332 pares (visita, variável), **zero
falhas**. O método está em [GCBD.md](GCBD.md), "Passo 2 — a ingestão ambiental".

---

## 15. A resposta é não

> **Salinidade e oxigênio, medidos pela reanálise do Copernicus na janela antes
> de cada visita, não acrescentam capacidade de prever branqueamento observado.
> Nenhuma combinação testada superou o modelo só-térmico na validação por ano.**

| Conjunto | Features | PR-AUC sítio | **PR-AUC ano** |
|---|---|---|---|
| **Térmicas J** (`TSA_DHW`, `TSA`, `Windspeed`) | 3 | 0,722 | **0,717** |
| J + só salinidade | 5 | 0,760 | 0,711 |
| J + só médias | 5 | 0,750 | 0,669 |
| J + só variações | 5 | 0,698 | 0,646 |
| **J + as 4 ambientais** | 7 | 0,739 | **0,636** |
| J + só oxigênio | 5 | 0,696 | 0,634 |
| 8 térmicas + ambientais | 12 | 0,810 | 0,618 |
| **Só ambientais** | 4 | 0,621 | **0,527** |
| Só as variações ambientais | 2 | 0,571 | 0,526 |

*(logística; taxa base = 0,530 em todas)*

Duas leituras:

**Acrescentar não ajuda.** O melhor resultado por ano continua sendo o de
0,717, do modelo com três térmicas e nenhuma variável ambiental. Acrescentar as
quatro **piora** para 0,636.

**Sozinhas, elas ficam no acaso.** PR-AUC 0,527 contra taxa base 0,530 —
ganho de **0,99×**. As não térmicas, isoladas, não distinguem nada.

⚠️ Diferenças entre 0,717, 0,711 e 0,669 estão dentro do ruído de 166 visitas.
O que é robusto é que **nada passa do teto de ~0,72**, e que o conjunto só
ambiental fica no acaso.

---

## 16. Não é a janela, e não é identidade do sítio

Antes de aceitar o resultado, testei as duas explicações alternativas que eu
tinha. **Nenhuma se sustentou.**

### 16.1 "90 dias dilui um efeito que é rápido"

Plausível: uma pluma de água doce dura dias, não um trimestre. E o cache guarda
os 91 valores diários de cada visita, então dá para reconstruir janelas menores
**sem baixar nada**.

| Janela | PR-AUC sítio | PR-AUC ano |
|---|---|---|
| 7 dias | 0,762 | 0,647 |
| 14 dias | 0,742 | 0,632 |
| 30 dias | 0,726 | 0,647 |
| **60 dias** | 0,736 | **0,664** |
| 90 dias | 0,739 | 0,636 |

*(logística, J + 4 ambientais)*

Todas ficam entre 0,632 e 0,664 — **todas abaixo dos 0,717 do modelo sem
ambientais**. Nenhum tamanho de janela resgata o sinal.

### 16.2 "Elas são identificador de lugar disfarçado"

Era a minha hipótese principal, e foi o que aconteceu com a climatologia do
próprio GCBD (§11.5). Dois testes:

**Variam com a visita?** Sim. O desvio-padrão *dentro* de cada sítio, dividido
pelo total:

| Variável | Razão | |
|---|---|---|
| `oxigenio_variacao_90d` | 0,87 | varia com a visita |
| `salinidade_variacao_90d` | 0,81 | varia com a visita |
| `oxigenio_media_90d` | 0,61 | varia com a visita |
| `salinidade_media_90d` | 0,48 | varia com a visita |
| *(comparação)* `TSA_DHW` | 0,20 | quase fixo do sítio |

**Dá para adivinhar o sítio a partir delas?** Um pouco: 14,9% de acerto contra
3,0% de acaso — 5× o acaso, mas longe de identificar. Carregam alguma
assinatura do lugar, e isso não é a explicação.

> **As duas hipóteses caíram. O sinal simplesmente não está lá — ou não está
> nestes produtos.** A distinção importa, e está em §18.

---

## 17. O que elas *fazem* — separação sem capacidade preditiva

Este é o achado mais interessante do passo 2, e ele não é zero.

As quatro variáveis **separam as classes na direção fisicamente esperada**.
Diferença de médias em desvios-padrão (*d* de Cohen):

| Variável | Branqueou | Não branqueou | *d* |
|---|---|---|---|
| `TSA_DHW` | 0,789 | 0,034 | **+0,602** |
| `TSA` | −0,573 | −1,142 | **+0,525** |
| `Windspeed` | 5,50 | 6,13 | **−0,461** |
| `oxigenio_media_90d` | 203,65 | 204,94 | −0,377 |
| `oxigenio_variacao_90d` | −2,17 | −1,32 | −0,315 |
| `salinidade_variacao_90d` | −0,108 | −0,014 | −0,284 |
| `salinidade_media_90d` | 36,70 | 36,83 | −0,281 |

Lido como mecanismo: os sítios que branquearam tinham **oxigênio mais baixo e
caindo mais rápido**, e **salinidade mais baixa e caindo**. Exatamente o que a
hipótese do projeto previa.

**Mas o efeito é cerca de metade do das térmicas, e não vira previsão.**

Na importância por permutação, medida fora da dobra e agrupada por ano:

| Variável | Queda do PR-AUC |
|---|---|
| `TSA_DHW` | +0,0681 |
| `Windspeed` | +0,0426 |
| `salinidade_media_90d` | +0,0199 |
| `TSA` | −0,0121 |
| `oxigenio_variacao_90d` | −0,0182 |
| `salinidade_variacao_90d` | −0,0297 |
| `oxigenio_media_90d` | **−0,0449** |

Só `salinidade_media_90d` contribui algo, e pouco. **O oxigênio piora o
modelo.**

### 🔁 É a segunda vez que o projeto vê exatamente isto

Na entrega 1, [VARIAVEIS.md](VARIAVEIS.md) §3.6 mediu que a trajetória do
oxigênio separa início de fim de episódio em **0,61 σ** — e §7 mostrou que essa
separação **não virou capacidade preditiva** (contribuição −0,001).

Agora, com **outro conjunto de dados, outro alvo e outro período**, o mesmo
padrão: separação descritiva real, contribuição preditiva nula ou negativa.

A repetição é, ela mesma, o resultado. Uma vez é indício; duas vezes em bases
independentes é um fato sobre o problema.

### E o `Windspeed` continua funcionando — ⚠️ **corrigido, ver §20**

`Windspeed` é a segunda variável mais útil em todas as versões (+0,043), com
coeficiente **−0,72**: mais vento, menos branqueamento. É **não térmica** e
funciona.

E a correlação explica parte do resto: `oxigenio_variacao_90d` × `Windspeed`
tem **r = +0,554**. O vento mistura a coluna d'água e a oxigena — então o vento
já carrega parte do que o oxigênio diria, e chega antes.

🚨 **Este parágrafo foi escrito em 26/07/2026 e desmentido no mesmo dia.** O
`Windspeed` usado aqui é uma coluna do próprio GCBD, e ninguém tinha conferido
se ela descreve o vento. Ao comparar com vento medido do ERA5, o efeito some.
**Ver §20.** O parágrafo fica com o aviso em cima porque apagá-lo esconderia o
percurso — mesma regra de [VARIAVEIS.md](VARIAVEIS.md) §3.6.

---

## 18. ⚠️ A explicação concorrente que estes dados não descartam

**O resultado negativo é sobre estes produtos nesta resolução, não sobre o
mecanismo.**

A grade do produto de oxigênio é **0,25° ≈ 28 km**. Medido em
[FONTES.md](FONTES.md) §6.18: **69 das 166 visitas estão a menos de 1 km da
costa**, e **20 sítios só encontram oxigênio a até 33 km do recife**.

Uma pluma de água doce ou um evento de hipóxia num recife costeiro raso é
exatamente o tipo de fenômeno que uma célula de 28 km de lado **calcula a média
para fora**. O que foi medido foi a salinidade e o oxigênio *do oceano ao redor*,
não *do recife*.

Então há duas explicações vivas, e estes dados não separam:

1. Salinidade e oxigênio não explicam o branqueamento brasileiro observado.
2. Eles explicam, mas a reanálise global não os enxerga na escala do recife.

**Escolher a primeira sem declarar a segunda seria erro.** O que se pode
afirmar é o enunciado condicional:

> Com salinidade e oxigênio de reanálise global (0,083° e 0,25°), numa janela
> de 7 a 90 dias antes da observação, não há ganho preditivo sobre um modelo
> térmico, em 166 visitas a recifes brasileiros entre 1994 e 2010.

O que resolveria: dado *in situ*, de sonda no recife. Não existe para estes 119
sítios neste período.

---

## 19. O que fica das duas entregas

| Pergunta | Resposta | Onde |
|---|---|---|
| Dá para prever estresse térmico com antecedência? | **Sim** — 18 de 19 episódios em 7 dias | §1–§7 |
| Variáveis não térmicas ajudam a prever o **BAA**? | **Não** — mas a pergunta era circular | §8 |
| O sinal térmico explica o branqueamento **observado**? | **Não** — a regra da NOAA pega 10 de 88 | §11 |
| Salinidade e oxigênio **de reanálise** explicam o resto? | **Não** — nenhuma combinação supera o só-térmico | §15 |
| Alguma variável não térmica funciona? | ~~Sim, o vento~~ → **não se confirmou** | **§20** |

O produto honesto continua se chamando **previsão de estresse térmico**. O que
mudou é que agora se sabe, com número, o quanto isso deixa de fora: **78 dos 88
branqueamentos brasileiros observados**.

---

## 20. 🚨 O vento também não se confirma

Medido em **26/07/2026**, poucas horas depois de §17 ser escrita.

§17 e §12.2 afirmaram que o vento é a variável não térmica que funciona, e essa
afirmação promoveu o ERA5 a prioridade máxima do projeto. **Ela não sobreviveu à
primeira verificação independente.**

### O furo do argumento original

Toda a evidência vinha de **uma única coluna**: o `Windspeed` do próprio GCBD.
Ninguém tinha conferido se aquela coluna descreve o vento — foi assumido.

O teste: baixar vento real do ERA5 para os **mesmos 166 pontos e as mesmas
datas**, e comparar.

### As duas fontes concordam sobre o vento

| | |
|---|---|
| Correlação | **r = +0,708** |
| Erro absoluto médio | 1,20 m/s |
| Dentro de 2 m/s | 80,7% |
| Razão mediana | 0,905 |

✅ Confirma também a **unidade**: m/s, não nós — se fossem nós a razão seria ~1,94.

### E discordam completamente sobre o coral

| Fonte do vento | *d* de Cohen | IC 95% *(bootstrap, 2.000)* |
|---|---|---|
| `Windspeed` do GCBD | **−0,461** | [−0,783, −0,160] — não inclui zero |
| **ERA5** | **−0,057** | [−0,358, +0,254] — **inclui zero** |

No modelo, que é o que decide:

| Features | PR-AUC sítio | **PR-AUC ano** |
|---|---|---|
| `TSA_DHW` + `TSA`, **sem vento** | 0,699 | 0,692 |
| \+ `Windspeed` do GCBD | 0,722 | **0,717** |
| \+ **vento do ERA5** | 0,698 | **0,673** |

> **Trocar a coluna do GCBD por vento medido de verdade deixa o modelo pior do
> que não ter vento nenhum.**

### Três hipóteses testadas

| Hipótese | Resultado |
|---|---|
| A coluna do GCBD carrega variável escondida | ⛔ **não** — as duas correlacionam quase igual com tudo (mês, latitude, turbidez); maior diferença 0,16 |
| É o arredondamento para inteiro | ⛔ **não** — ERA5 arredondado dá *d* = −0,040 |
| É ruído de 166 amostras | ✅ **é o que sobra** — os dois IC se sobrepõem largamente |

### O que isso estabelece

**Estabelece:** o efeito do vento **não é robusto à escolha do produto**. Um
ganho de +0,025 no PR-AUC — que §15 já classificava explicitamente como **dentro
do ruído** — vira −0,019 ao trocar a fonte.

**Não estabelece** que não existe efeito do vento. Os intervalos se sobrepõem;
com 166 visitas nenhuma das duas estimativas é precisa.

### 💡 E fica um achado positivo, que não é sobre vento

**28 km serve para vento.** Duas fontes independentes concordando em r = 0,71,
uma delas arredondada para inteiro.

Isso torna a ressalva de §18 **mais específica e mais forte**: a resolução
grosseira não é problema para campos suaves — o problema é com variáveis
**irregulares e costeiras**, como oxigênio e nutrientes. A ressalva deixa de ser
"28 km é grosseiro" e passa a ser "28 km é grosseiro *para este tipo de
variável*", que é uma afirmação melhor.

### ⚠️ A lição, que não é sobre vento nem sobre ERA5

> Uma diferença **dentro do ruído declarado** não deve virar prioridade de
> projeto, por mais que o mecanismo faça sentido.

O ruído foi declarado em §15 — *"diferenças abaixo de ~0,05 são ruído"* — e
depois raciocinei como se não estivesse, porque o mecanismo do vento é
convincente. Mecanismo plausível é justamente o que faz um número de ruído
parecer um achado.

### 20.1 ✅ Consequência aplicada: o `Windspeed` saiu do conjunto interpretável

Decidido e aplicado em **27/07/2026**. O conjunto interpretável passa de três
para **duas** colunas:

```
FEATURES_INTERPRETAVEIS = ('TSA_DHW', 'TSA')
```

| Conjunto | PR-AUC sítio | PR-AUC ano | Brier | Coef. invertidos |
|---|---|---|---|---|
| `TSA_DHW`, `TSA`, `Windspeed` *(antes)* | 0,722 | 0,717 | 0,225 | 0 |
| **`TSA_DHW`, `TSA`** *(agora)* | **0,699** | **0,692** | **0,229** | **0** |

**Custa 0,025 de PR-AUC — exatamente a diferença que §15 classifica como
ruído.** E compra uma coisa que não é métrica: cada entrada passa a ter
mecanismo defensável sem ressalva anexada.

Os coeficientes ficam limpos e o sinal é o físico:

| Variável | Coeficiente | Importância (por ano) | Leitura |
|---|---|---|---|
| `TSA_DHW` | **+1,011** | +0,076 | estresse térmico acumulado piora |
| `TSA` | **+0,374** | +0,040 | anomalia térmica do dia piora |

E as duas passam a contribuir positivamente na validação por ano — antes o `TSA`
ficava em +0,006, quase apagado pelo vento.

**O critério que orientou a escolha**, e que vale para decisões futuras:

> Entre um conjunto com número melhor dentro do ruído e um conjunto em que toda
> entrada se defende sozinha, escolher o segundo. Num trabalho que precisa ser
> defendido, duas variáveis com mecanismo claro valem mais que três em que uma
> exige duas páginas de ressalva.

⚠️ O `Windspeed` **continua** na versão de 8 features (`FEATURES_PADRAO`), e
deve continuar: ali ele não foi escolhido por nós, é o que o GCBD oferece. O que
saiu foi a escolha deliberada de mantê-lo. Há teste travando a remoção, com o
motivo escrito.

---

## 21. Qualidade da água — clorofila, nitrato e silicato

Rodado em **27/07/2026**. Extraídas **45.318 valores diários**, 498 pares
(visita, variável), **zero falhas**.

**Custo quase nulo, e esse foi o motivo de fazer:** as três saem do **mesmo
arquivo** de onde já vinha o oxigênio (`cmems_mod_glo_bgc_my_0.25deg_P1D-m`).
Nenhuma fonte nova, credencial nova ou código novo — só mais nomes numa tupla.

**A hipótese que justificava:** o `silicato` marca **aporte continental**, isto
é, água de rio chegando ao recife. A salinidade deveria detectar isso — rio é
água doce — e não detectou (§15). O silicato pergunta a mesma coisa por outro
caminho.

### 21.1 A resposta é não, pela terceira vez

| Conjunto | Features | PR-AUC sítio | **PR-AUC ano** |
|---|---|---|---|
| **Só as 3 térmicas** | 3 | 0,722 | **0,717** |
| \+ nitrato | 5 | 0,733 | 0,697 |
| \+ silicato | 5 | 0,710 | 0,679 |
| \+ clorofila | 5 | 0,707 | 0,617 |
| \+ as 6 de água | 9 | 0,724 | 0,630 |
| \+ água e salinidade/O₂ (tudo) | 13 | 0,751 | 0,630 |
| **Só ambientais, sem térmica** | 10 | **0,753** | 0,624 |

**Nenhuma combinação melhora a validação por ano.** Todas pioram.

E repare no padrão que já apareceu duas vezes: **por sítio o resultado sobe**
(0,722 → 0,753, o melhor de todos) **enquanto por ano cai**. É a assinatura de
um modelo que reconhece o evento em vez de aprender o fenômeno (§11.4).

### 21.2 O silicato é o único que passa no teste estatístico

Diferença entre branqueou e não branqueou, com intervalo por reamostragem
(2.000 vezes):

| Variável | *d* | IC 95% | |
|---|---|---|---|
| `TSA_DHW` | +0,602 | [+0,422, +0,788] | exclui zero |
| `TSA` | +0,525 | [+0,229, +0,846] | exclui zero |
| `Windspeed` | −0,461 | [−0,780, −0,166] | exclui zero *(mas ver §20)* |
| **`silicato_variacao_90d`** | **+0,396** | **[+0,077, +0,746]** | **exclui zero** |
| `silicato_media_90d` | +0,205 | [−0,112, +0,549] | inclui zero |
| `clorofila_media_90d` | +0,120 | [−0,207, +0,415] | inclui zero |
| `nitrato_variacao_90d` | +0,108 | [−0,180, +0,492] | inclui zero |
| `nitrato_media_90d` | −0,058 | [−0,314, +0,295] | inclui zero |
| `clorofila_variacao_90d` | +0,037 | [−0,254, +0,358] | inclui zero |

**`silicato_variacao_90d` é a única variável de qualidade da água cujo efeito se
distingue de zero.** Direção: o silicato estava **subindo** nos sítios que
branquearam — isto é, mais aporte continental chegando.

⚠️ **Mas o intervalo começa em +0,077, colado no zero.** E foram 9 variáveis
testadas: com esse número, esperar que uma cruze o limiar por acaso é o
esperado, não a exceção. Isto é indício fraco, e tratá-lo como achado seria
repetir exatamente o erro do vento (§20).

### 21.3 🚨 E a hipótese do rio **não** se sustenta

Se o silicato marcasse água de rio, ele deveria andar **contra** a salinidade —
rio dilui o sal. Medido:

| Par | r | O que se esperava |
|---|---|---|
| `silicato` × `salinidade` | **+0,363** | 🚨 **negativo** |
| `silicato` × `Distance_to_Shore` | −0,233 | negativo ✅ |
| `nitrato` × `silicato` | **+0,733** | positivo ✅ |
| `nitrato` × `clorofila` | +0,481 | positivo ✅ |

O silicato **sobe junto com a salinidade**, o oposto do que uma pluma de água
doce produziria. Ele se comporta como enriquecimento costeiro genérico — cai com
a distância da costa, anda junto com o nitrato — mas **não como marcador de água
de rio**.

> **A hipótese que motivou incluir o silicato foi testada e não se sustentou.**
> O efeito existe, é fraco, e não é o mecanismo que se supôs.

### 21.4 A colinearidade voltou, previsivelmente

`nitrato` × `silicato` dá **r = 0,733**. Excluí o fosfato justamente para evitar
isso — e as duas que entraram são quase a mesma coluna assim mesmo.

Os coeficientes voltam a ficar ininterpretáveis:

| Variável | Coeficiente | |
|---|---|---|
| `salinidade_media_90d` | −0,678 | |
| `silicato_media_90d` | +0,660 | |
| `TSA_DHW` | +0,651 | |
| `nitrato_media_90d` | **−0,607** | 🚨 mais nutriente, menos branqueamento |

`nitrato` negativo diria que **adubo protege o coral**. É falso, e é o mesmo
sintoma de §8 e §12: com 13 features sobre 166 visitas, o modelo reparte crédito
arbitrariamente entre colunas que dizem a mesma coisa.

### 21.5 A ressalva de §18, na sua forma mais forte

Tudo o que §18 diz sobre oxigênio **vale mais aqui**.

A grade é 0,25° ≈ **28 km**. §20 mostrou que isso **serve para vento**, um campo
suave e de grande escala. Nutriente é o oposto: uma pluma de rio tem poucos
quilômetros de largura e vive colada na costa — exatamente o que uma célula de
28 km calcula a média para fora.

E há evidência disso no próprio resultado: **84 das 498 extrações precisaram de
raio de 0,30°** (~33 km) para achar célula de oceano.

> Este resultado negativo é, entre todos os do projeto, o **menos conclusivo**.
> Não distingue "nutriente não importa" de "não conseguimos medir nutriente na
> escala do recife".

---

## 22. 🚨 A probabilidade que o painel ia exibir estava mentindo

Medido em **27/07/2026**. É o item que bloqueava o go-live.

O painel vai mostrar **"risco 37%"**. Para esse número não ser decorativo, ele
precisa cumprir uma promessa verificável:

> Entre os dias em que o modelo disse 37%, o alerta aconteceu em cerca de 37%
> deles.

### 22.1 Não cumpria — e por uma margem do tamanho do fenômeno

| | |
|---|---|
| Taxa real de evento | **0,084** |
| Probabilidade média que o modelo dizia | **0,165** |
| Viés | **+0,081** — promete o dobro |
| Erro esperado (ECE) | **0,081** |
| Erro máximo (MCE) | 0,213 |

**O erro de calibração (0,081) é praticamente do tamanho da taxa base
(0,084).** Ou seja: o número exibido erraria, em média, tanto quanto o próprio
fenômeno acontece.

A curva mostra o padrão, e ele é sistemático — **todas** as faixas prometem
demais:

| Prometido | Observado | Desvio |
|---|---|---|
| 0,027 | 0,006 | +0,021 |
| 0,069 | 0,004 | +0,065 |
| **0,084** | **0,000** | **+0,084** |
| 0,101 | 0,015 | +0,085 |
| 0,961 | 0,748 | +0,213 |

Na faixa em que o modelo dizia exatamente 8,4% — a taxa base —, o alerta
aconteceu **zero vezes**.

### 22.2 Não é defeito a descobrir; é consequência conhecida a medir

A causa está no próprio `ml/modelo.py`: `class_weight='balanced'`.

Esse parâmetro instrui o estimador a tratar as duas classes como se fossem do
mesmo tamanho. Isso é **correto para decidir** com 8% de positivos — sem ele o
modelo aprende que nunca avisar quase sempre acerta ([METODOLOGIA.md](METODOLOGIA.md)
§4) — e **destrói a probabilidade por construção**.

O que a medição acrescenta é o tamanho do estrago, que não era óbvio.

### 22.3 Por que o Brier "bom" escondia isso

O Brier era 0,043 e parecia ótimo. A decomposição de Murphy separa o que ele
mistura:

```
Brier = confiabilidade − resolução + incerteza
```

| Termo | Valor | Leitura |
|---|---|---|
| confiabilidade | 0,0098 | é a **calibração** — quanto menor, melhor |
| resolução | 0,0493 | quanto o modelo **separa** — quanto maior, melhor |
| **incerteza** | **0,0769** | a dificuldade do **problema**, não do modelo |

**A incerteza sozinha é o dobro do Brier.** O número parecia bom porque 92% dos
dias não têm alerta, não porque o modelo acertasse a probabilidade.

> Brier baixo pode vir de problema fácil. Só a decomposição distingue.

### 22.4 O conserto, com o custo medido

Quatro caminhos testados, todos com predição **fora da dobra** e com o
recalibrador ajustado **dentro** do treino (`cv=3` interno — ajustá-lo sobre as
predições avaliadas seria vazamento, e a curva sairia perfeita por construção):

| Versão | ECE | Viés | PR-AUC | R @ 0,5 | Confiabilidade |
|---|---|---|---|---|---|
| `balanced` *(o que estava no ar)* | **0,0811** | +0,081 | 0,885 | 0,909 | 0,0098 |
| sem `class_weight` | 0,0084 | −0,002 | 0,866 | 0,716 | 0,0002 |
| `balanced` + Platt | 0,0163 | −0,002 | 0,878 | 0,721 | 0,0005 |
| **`balanced` + isotônica** | **0,0039** | −0,001 | 0,871 | 0,775 | **0,0000** |

**Adotada a isotônica** — ECE 20× menor, e a curva passa a fechar:

| Prometido | Observado | Desvio |
|---|---|---|
| 0,003 | 0,003 | +0,001 |
| 0,081 | 0,079 | +0,001 |
| 0,723 | 0,737 | −0,015 |

### 22.5 Calibrar não custa detecção — custa mudar o corte

O PR-AUC quase não muda entre as versões (0,841 a 0,885). PR-AUC só depende da
**ordem**. Isso já sugeria que o `class_weight` não detectava mais — ele
**empurrava a probabilidade para cima**, o que equivale a baixar o limiar sem
declarar.

Confirmado, comparando pontos de operação:

| | Limiar | Precisão | Revocação | F1 |
|---|---|---|---|---|
| `balanced` | 0,50 | 0,721 | 0,909 | 0,804 |
| **isotônica** | **0,20** | 0,705 | **0,903** | 0,792 |

**No corte equivalente, o desempenho é o mesmo.** O que muda é onde fica o
corte — e agora ele é uma decisão declarada, em vez de efeito colateral de um
parâmetro de treino.

⚠️ Uma ressalva de método: os limiares ótimos foram escolhidos olhando as mesmas
predições que os avaliam. Serve para comparar as versões entre si, **não** como
estimativa de desempenho futuro — mesmo viés declarado em §12.3.

### 22.6 A separação que isso estabelece para o painel

> **Probabilidade calibrada para exibir. Limiar declarado para avisar.**
> São decisões diferentes e devem ser tomadas em lugares diferentes.

`treinar_final` passa a gravar o modelo **recalibrado por padrão**, e a
recalibração viaja nos metadados — sem isso ninguém saberia se a probabilidade
gravada é crua ou corrigida, e a diferença vale 0,081 de ECE.

### 22.7 Um defeito no próprio medidor, achado por teste

Ao escrever os testes, um caso quebrou: **predição constante produzia curva
vazia e ECE = 0,0** — que se lê como calibração perfeita.

Um modelo que responde sempre 30% sobre 8% de eventos é o pior calibrado
possível, e passava como o melhor. A causa era o agrupamento por quantil
colapsando todas as bordas quando não há variação.

Corrigido com um recuo para agrupamento por valores distintos, e travado por
teste. É o tipo de defeito que só aparece no caso degenerado — e o caso
degenerado é justamente o que se quer denunciar.

### 22.8 🚨 O preço da isotônica: a probabilidade vira escada, e a escada toca 0 e 1

Medido em 27/07/2026, ao aplicar o modelo persistido aos três recifes pela
primeira vez. Os três voltaram com **exatamente 0,0029** — apesar de entradas
bem diferentes:

| Recife | `sst_variacao_7d` | probabilidade crua | probabilidade calibrada |
|---|---|---|---|
| Abrolhos | +0,093 | 0,083 | **0,0029** |
| Picãozinho | −0,312 | — | **0,0029** |
| Porto de Galinhas | −0,321 | 0,066 | **0,0029** |

Parece defeito e não é. **A regressão isotônica é uma função escada por
construção**: ela ajusta um degrau por faixa, e tudo que cai no mesmo degrau
sai com o mesmo número. As probabilidades cruas 0,083 e 0,066 são diferentes;
o degrau que as contém é o mesmo.

Sobre as 7.095 amostras de treino:

| | Valor |
|---|---|
| valores distintos de probabilidade | **313** (de 7.095 amostras) |
| amostras em `p = 0,000` **exato** | **864 (12,2%)** |
| amostras em `p = 1,000` **exato** | 121 (1,7%) |
| fração no degrau mais baixo | 12,2% |

**O 0,000 e o 1,000 exatos são o problema real, e são de comunicação, não de
estatística.** O que a isotônica afirma em `p = 0` é *"no degrau mais baixo,
nenhuma das amostras de treino virou alerta"*. Isso limita a probabilidade;
não a zera. Um painel público que exibe **"risco de branqueamento: 0%"** está
traduzindo um degrau finito em impossibilidade — e **"100%"**, em certeza.
Nenhum dos dois é defensável.

**O que foi feito, e o que deliberadamente não foi.** A API devolve o número
como ele é e sinaliza o caso com `no_extremo: true`, mais
`probabilidade_em_degraus` no bloco do modelo. **Não** houve corte para 0,001 e
0,999: falsificar o número na direção oposta inventaria precisão que o modelo
não tem, e esconderia da interface exatamente a informação que ela precisa para
decidir como exibir. A decisão de apresentação fica em quem apresenta, com o
aviso na mão.

⚠️ Isto é um custo da recalibração que a §22.4 não tinha medido. Ele **não**
reverte a decisão — ECE de 0,081 para 0,0039 continua valendo muito mais que a
granularidade perdida —, mas passa a acompanhá-la.

---

## 22.9 O limiar de alerta: a troca, medida

Material para a decisão da §22.6 — *limiar declarado para avisar*. Produzido em
27/07/2026 por `manage.py limiar`, sobre as **predições fora da dobra** do
modelo servido (`logistica` + isotônica). 7.095 amostras, 596 positivas (8,4%),
7 anos, 3 recifes, **19 episódios reais**.

O limiar não é propriedade do modelo. O modelo devolve probabilidade; o limiar
é onde o site decide avisar, e isso é escolha de operação.

### 22.9.1 A tabela

Traduzida para a unidade em que a decisão existe — *por ano e por recife*, não
por amostra:

| Limiar | Precisão | Revocação | F1 | Episódios | Avisados no 1º dia | Atraso médio | Alarme falso/ano/recife |
|---|---|---|---|---|---|---|---|
| 0,05 | 0,498 | 0,943 | 0,652 | **18/19** | 18/20 | 0,80 d | 27,0 |
| 0,10 | 0,620 | 0,936 | 0,746 | 17/19 | 18/20 | 0,95 d | 16,3 |
| 0,15 | 0,678 | 0,919 | 0,781 | 16/19 | 16/20 | 1,30 d | 12,4 |
| **0,20** | 0,719 | 0,899 | 0,799 | 16/19 | **16/20** | **1,50 d** | 10,0 |
| 0,25 | 0,736 | 0,874 | 0,799 | 16/19 | 15/20 | 1,85 d | 8,9 |
| **0,30** | 0,753 | 0,859 | **0,803** | 16/19 | 13/20 | 2,60 d | 8,0 |
| 0,40 | 0,786 | 0,807 | 0,796 | 16/19 | 11/20 | 3,95 d | 6,2 |
| 0,50 | 0,826 | 0,747 | 0,784 | 14/19 | 10/20 | 4,94 d | 4,5 |
| 0,70 | 0,904 | 0,601 | 0,722 | 13/19 | 4/20 | 9,53 d | 1,8 |
| 0,95 | 0,961 | 0,367 | 0,532 | 7/19 | 2/20 | 12,43 d | 0,4 |

⚠️ **A contagem "16/19" e "16/20" usa duas réguas diferentes, e isso é
deliberado.** A dos episódios funde trechos separados por poucos dias num
evento só (`folga_dias`), porque a pergunta é *"o sistema percebeu este
evento?"*. A do atraso conta cada corrida contígua por si, porque fundir
trechos deslocaria o início para trás e inflaria o atraso. São 19 eventos com
folga, 20 corridas contíguas.

### 22.9.2 🚨 O achado principal não é sobre o limiar

**Nenhum limiar varrido detecta os 19 episódios.** Um escapa em *todos*:

> **Picãozinho, 21 a 23/04/2026 — 3 dias.**

Baixar o corte não o recupera. Isso muda a natureza da conversa: o teto não
está na escolha do limiar, está **no modelo**. Discutir 0,20 contra 0,30 é
discutir os outros dois episódios, não este.

Os outros dois que 0,20 perde, e que 0,05 recupera:

| Episódio | Duração | Recuperado a partir de |
|---|---|---|
| Picãozinho, 26/02–06/03/**2022** | 9 dias | 0,10 |
| Porto de Galinhas, 07/05/2020 | 1 dia | 0,05 |

⚠️ O de 2022 conecta com a pendência já aberta *"investigar 2022"* — é o único
ano em que o modelo perde claramente para a persistência, e agora sabemos que
o episódio perdido lá é de **nove dias**, não um caso de borda.

### 22.9.3 🚨 O patamar de episódios engana, e a correção importa

Entre **0,15 e 0,40** a contagem de episódios não se move: são sempre 16 de 19,
enquanto o alarme falso cai de 12,4 para 6,2 dias por ano e por recife. Lida
sozinha, essa faixa diz *"apertar o limiar é de graça"*.

**Não é.** Foi o que a coluna de atraso, acrescentada depois, mostrou:

| | 0,20 | 0,30 | 0,40 |
|---|---|---|---|
| Episódios detectados | 16/19 | 16/19 | 16/19 |
| **Avisados já no 1º dia** | **16/20** | 13/20 | 11/20 |
| **Atraso médio do 1º aviso** | **1,50 d** | 2,60 d | 3,95 d |
| Alarme falso/ano/recife | 10,0 | 8,0 | 6,2 |

O evento continua sendo detectado — **mais tarde**. Para um sistema de aviso,
alertar no terceiro dia de um episódio de nove não é o mesmo que alertar no
primeiro, ainda que ambos contem como "detectado".

> ⚠️ **Correção registrada.** A primeira versão desta seção concluía que
> *"0,20 é dominado por 0,30"*, com base só na contagem de episódios e no
> alarme falso. **Estava errado** — não havia domínio, havia uma dimensão não
> medida. Vale como aviso de método: um patamar numa métrica agregada quase
> sempre esconde movimento em alguma coisa que ela não mede.

### 22.9.4 Os candidatos, com a troca inteira à vista

| Candidato | Limiar | Episódios | 1º dia | Atraso | Alarme falso |
|---|---|---|---|---|---|
| Cobertura máxima | 0,05 | 18/19 | 18/20 | 0,80 d | 27,0 |
| Meio-termo | 0,10 | 17/19 | 18/20 | 0,95 d | 16,3 |
| **Em uso hoje** | **0,20** | 16/19 | 16/20 | 1,50 d | 10,0 |
| F1 máximo | 0,30 | 16/19 | 13/20 | 2,60 d | 8,0 |

Com as três dimensões na mesa, **0,20 deixa de ser dominado**: paga 2 dias a
mais de alarme falso por ano e por recife, e compra 3 episódios a mais avisados
já no primeiro dia, além de mais de um dia de antecedência média.

E **0,10** vira candidato sério, o que não aparecia antes: recupera o episódio
de nove dias de 2022 e mantém o aviso no primeiro dia em 18 dos 20, ao custo de
6 dias a mais de alarme falso por ano.

⚠️ **Viés de seleção, declarado.** Os limiares foram comparados sobre as mesmas
predições que os avaliam. Serve para escolher entre eles; **não** é estimativa
do desempenho no ano que vem. Mesma ressalva das §12.3 e §22.5.

### 22.9.5 ✅ Decisão: 0,10

Tomada em 27/07/2026, com a tabela acima na mesa. Está em
`settings.PAINEL_LIMIAR` e viaja no payload de `/api/painel-risco/`.

**O critério declarado foi priorizar antecedência.** Para um site cujo público
age sobre o aviso, perder um evento custa mais que um alarme falso — e chegar
tarde é quase o mesmo que não chegar.

| | 0,20 (anterior) | **0,10 (adotado)** | Diferença |
|---|---|---|---|
| Episódios detectados | 16/19 | **17/19** | +1 (o de 9 dias, 2022) |
| Avisados já no 1º dia | 16/20 | **18/20** | +2 |
| Atraso médio do 1º aviso | 1,50 d | **0,95 d** | −0,55 d |
| Alarme falso/ano/recife | 10,0 | **16,3** | +6,3 dias |

O que se compra: o episódio de **nove dias** de Picãozinho em 2022 — o mesmo
ano que já figurava como o pior do modelo. O que se paga: cerca de **seis dias
a mais de alarme falso por ano em cada recife**.

⚠️ **O 0,20 anterior nunca tinha sido escolhido.** Ele era o ponto de
desempenho equivalente ao `0,50` do `predict`, que por sua vez operava daquele
jeito só porque `class_weight='balanced'` empurrava a probabilidade para cima
(§22.5). Herança, não decisão.

⚠️ **A decisão não resolve o teto.** O episódio de Picãozinho de 21–23/04/2026
continua escapando, como escapa em todos os limiares. Isso é problema do
modelo, e permanece aberto.

---

## 23. O que estes resultados indicam fazer

| Prioridade | O quê | Por quê |
|---|---|---|
| ✅ feito | ~~Persistir um modelo~~ | Feito em 27/07/2026: `manage.py treinar_final`. Ver [VISAO_GERAL.md](VISAO_GERAL.md) §7.4 |
| **Alta** | Declarar §18 e §20 em qualquer texto | Os dois resultados negativos são condicionais, e omitir as condições seria afirmar demais |
| **Alta** | **Decidir o limiar de alerta** | §22.9 — material medido, com as três dimensões: episódios pegos, **quando** o aviso chega, e alarme falso. Dois achados: **nenhum limiar pega os 19 episódios**, e o patamar 0,15–0,40 **não** é de graça — o aviso só chega mais tarde |
| **Alta** | **A interface não pode exibir "0%" nem "100%"** | §22.8 — a isotônica devolve 0 e 1 exatos por construção (12,2% e 1,7% das amostras). A API sinaliza com `no_extremo`; traduzir isso em impossibilidade ou certeza é decisão de exibição, e seria errada |
| ✅ feito | ~~Curva de calibração~~ | Feito em 27/07/2026 (§22): o modelo prometia **o dobro** do que acontecia. Corrigido com recalibração isotônica, ECE de 0,081 para **0,0039** |
| Média | Investigar 2022 (entrega 1) | Único ano em que o modelo perde claramente |
| Baixa | Dado *in situ* | Resolveria §18 e §21.5, mas não existe para estes sítios |
| ⛔ | **Conector do ERA5** | §20 — o vento medido piora o modelo. Ver [ERA5.md](ERA5.md) |
| ⛔ | ~~Qualidade da água~~ | §21 — feita, e nenhuma combinação melhora |
| ⛔ | Mais variáveis ambientais | §21.4 — com 13 features sobre 166 visitas os coeficientes já não se sustentam |
| ⛔ | Ampliar a janela ambiental | Testado de 7 a 90 dias; nenhum tamanho ajuda (§16.1) |

### O padrão que se repete, e o que ele diz

Quatro famílias de variável não térmica foram testadas contra branqueamento
observado. **Todas descrevem; nenhuma prevê.**

| Variável | *d* distinguível de zero? | Melhora a previsão por ano? |
|---|---|---|
| Salinidade | não | não |
| Oxigênio | não | não |
| Vento | sim na coluna do GCBD, **não em vento medido** (§20) | não |
| Clorofila, nitrato | não | não |
| Silicato (variação) | **sim, mas colado no zero** (§21.2) | não |

Três leituras possíveis, e **estes dados não separam**:

1. Variáveis não térmicas realmente não preveem branqueamento no Brasil.
2. Preveem, mas a **resolução** de 28 km não as enxerga na escala do recife
   (§18, §21.5) — mais provável para nutriente que para vento, já que §20
   mostrou que 28 km serve para campo suave.
3. **166 visitas é pouco** para detectar um efeito de tamanho moderado. Todos os
   intervalos são largos; o próprio efeito térmico só se destaca por ser grande.

> A explicação 3 vale para as três leituras, e nenhuma fonte nova a resolve. O
> que resolveria é mais rótulo observado — e o GCBD brasileiro termina em 2010.

---

## Reprodução

```bash
python backend\manage.py shell -c "from aquaculture.models import LocalRecife; from ml.dataset import montar_todos; from ml.modelo import comparar_com_persistencia; locais=list(LocalRecife.objects.filter(latitude__isnull=False)); print(comparar_com_persistencia(montar_todos(locais, horizonte=7), nome='boosting').resumo())"
```

Semente fixa (`42`) em ambos os modelos; o resultado é determinístico.

Entrega 2, passo 1 (§11–§14) — não toca no banco nem na rede, só no CSV do GCBD:

```bash
python backend\manage.py treinar_gcbd --importancia
```

```bash
python backend\manage.py treinar_gcbd --interpretavel --importancia
```

O arquivo do GCBD não é versionado. Baixe pelo DOI de [GCBD.md](GCBD.md) e
coloque em `dados/global_bleaching_environmental.csv`, ou aponte `GCBD_CSV`
para ele.

Entrega 2, passo 2 (§15–§19) — o primeiro comando **usa rede** e exige a
credencial do Copernicus; leva alguns minutos e é retomável:

```bash
python backend\manage.py ingerir_gcbd
```

```bash
python backend\manage.py treinar_gcbd --interpretavel --ambiental --importancia
```

```bash
python backend\manage.py treinar_gcbd --so-ambiental --importancia
```

---

## Histórico

| Data | Alteração |
|---|---|
| 27/07/2026 | **§22.9.3 corrigida no mesmo dia — eu havia concluído domínio onde não havia.** A primeira versão dizia que *"0,20 é dominado por 0,30"*, olhando só episódios detectados e alarme falso. Ao medir **quando** o aviso chega, o suposto domínio some: entre 0,20 e 0,30 os episódios pegos são os mesmos, mas os avisados já no 1º dia caem de **16/20 para 13/20** e o atraso médio sobe de **1,50 para 2,60 dias**. O evento continua detectado — mais tarde. Fica o aviso de método: um patamar numa métrica agregada quase sempre esconde movimento em algo que ela não mede. Com a dimensão nova, **0,10 vira candidato sério** (recupera o episódio de nove dias de 2022, mantém aviso no 1º dia em 18/20). |
| 27/07/2026 | **§22.9 criada — a troca do limiar, medida e traduzida.** `manage.py limiar` varre 19 cortes sobre as predições fora da dobra e converte tudo para *dias de alarme falso por ano e por recife*, porque "precisão 0,719" não é uma frase sobre a qual alguém consiga formar opinião. 🚨 **O achado principal não é sobre o limiar:** nenhum dos 19 cortes detecta os 19 episódios — **Picãozinho, 21–23/04/2026, escapa em todos**. Baixar o corte não o recupera, então o teto é do modelo e não da escolha. Medido também que **entre 0,15 e 0,40 a contagem de episódios não se move** (sempre 16/19): nessa faixa apertar o limiar é de graça em termos de evento, e só reduz alarme falso (12,4 → 6,2 dias/ano/recife). Disso sai que **0,20 é dominado por 0,30** — mesma cobertura, 20% menos alarme falso. Os dois episódios que 0,20 perde e 0,05 recupera custam quase o triplo de alarme falso, e um deles dura um dia. ⚠️ O de 2022 (nove dias, Picãozinho) conecta com a pendência já aberta de investigar 2022. Viés de seleção declarado: os limiares são comparados sobre as mesmas predições que os avaliam. 19 testes. |
| 27/07/2026 | **§22.8 acrescentada — o custo da isotônica, achado ao aplicar o modelo pela primeira vez.** Os três recifes voltaram com **exatamente 0,0029**, apesar de entradas bem diferentes. Não é defeito: a isotônica é **função escada**, e as probabilidades cruas 0,083 e 0,066 caem no mesmo degrau. Medido sobre o treino: **313 valores distintos em 7.095 amostras, 864 (12,2%) em `p = 0,000` exato e 121 em `p = 1,000` exato**. O problema real é de comunicação — `p = 0` significa "nenhum alerta neste degrau", e exibir isso como "0% de risco" traduz um degrau finito em impossibilidade. **Deliberadamente não houve corte para 0,001/0,999**: falsificar o número na direção oposta inventaria precisão inexistente e esconderia da interface justamente o que ela precisa saber. A API sinaliza com `no_extremo`. O custo não reverte a decisão da §22.4 — 0,081 → 0,0039 de ECE continua valendo muito mais que a granularidade perdida — mas passa a acompanhá-la. |
| 27/07/2026 | 🚨 **§22 criada — a probabilidade que o painel ia exibir estava mentindo, e o bloqueio de go-live caiu.** O modelo dizia **0,165** onde a taxa real é **0,084**: ECE de **0,081**, praticamente do tamanho do próprio fenômeno, com **todas** as faixas prometendo demais — na faixa que dizia 8,4% o alerta aconteceu **zero vezes**. A causa não era defeito a descobrir e sim consequência conhecida a medir: `class_weight="balanced"` corrige a **decisão** e destrói a **probabilidade**. A decomposição de Murphy mostrou por que o Brier de 0,043 escondia isso — a **incerteza (0,0769) sozinha é o dobro do Brier**, ou seja o número parecia bom porque o problema é fácil. Testados quatro consertos; **adotada a recalibração isotônica** (ECE 0,0039, 20× melhor), com o calibrador ajustado **dentro** da dobra de treino. E medido que **calibrar não custa detecção**: no corte equivalente (0,20 em vez de 0,50) a revocação é a mesma — o `class_weight` não detectava mais, apenas baixava o limiar sem declarar. Fica a separação: **probabilidade calibrada para exibir, limiar declarado para avisar**. §22.7 registra um defeito no próprio medidor, achado por teste: predição constante produzia curva vazia e ECE 0,0, que se lê como calibração perfeita quando é o pior caso possível. |
| 27/07/2026 | **§20.1 — `Windspeed` removido do conjunto interpretável, e o critério registrado.** `FEATURES_INTERPRETAVEIS` passa de três para duas colunas: `TSA_DHW` e `TSA`. Custa **0,025** de PR-AUC por ano (0,717 → 0,692) — exatamente a diferença que §15 classifica como ruído — e compra que **toda entrada tenha mecanismo defensável sem ressalva**. Coeficientes limpos e no sinal físico (`TSA_DHW` +1,011, `TSA` +0,374), e as duas passam a contribuir positivamente na validação por ano, contra o `TSA` quase apagado antes. O `Windspeed` **continua** na versão de 8 features, onde não foi escolha nossa. Teste travando a remoção, com o motivo escrito. Critério para decisões futuras: *entre um número melhor dentro do ruído e um conjunto em que toda entrada se defende sozinha, escolher o segundo*. |
| 27/07/2026 | **§21 criada — qualidade da água testada, e a resposta é não pela terceira vez.** Extraídos **45.318 valores diários** de clorofila, nitrato e silicato, 498 pares, zero falhas, do **mesmo produto** de onde já vinha o oxigênio — custo quase nulo. **Nenhuma combinação melhora a validação por ano**; todas pioram, e reaparece a assinatura já conhecida de subir por sítio (0,753, o melhor de todos) enquanto cai por ano. O `silicato_variacao_90d` é a **única** variável de qualidade da água com efeito distinguível de zero (*d* = +0,396, IC [+0,077, +0,746]) — mas o intervalo começa colado no zero e foram 9 variáveis testadas, então tratá-lo como achado repetiria o erro do vento. 🚨 **E a hipótese que justificava o silicato não se sustentou**: ele correlaciona **+0,363 com a salinidade**, o oposto do que uma pluma de água doce produziria — comporta-se como enriquecimento costeiro genérico, não como marcador de rio. Colinearidade de volta (`nitrato` × `silicato` r = 0,733) com `nitrato` saindo em −0,607, o que diria que adubo protege coral. §21.5 registra que este é o resultado negativo **menos conclusivo** do projeto, porque 28 km é a pior escala possível para nutriente — e §20 já mostrou que essa grade serve para campo suave, o que torna a ressalva específica em vez de genérica. §22 acrescenta o quadro das quatro famílias testadas e as três leituras que os dados não separam. |
| 26/07/2026 | 🚨 **§20 criada — o vento também não se confirma, e §17 fica corrigida.** Poucas horas depois de §17 afirmar que o vento é a variável não térmica que funciona, o teste independente derrubou a afirmação. Toda a evidência vinha de **uma única coluna** — o `Windspeed` do próprio GCBD —, e ninguém tinha conferido se ela descreve o vento. Baixado vento real do ERA5 para os mesmos 166 pontos e datas: as duas fontes **concordam sobre o vento** (r = +0,708, 80,7% dentro de 2 m/s, razão 0,905 confirmando m/s) e **discordam sobre o coral** (*d* = −0,461 contra −0,057, com o IC do ERA5 incluindo zero). **Trocar a coluna do GCBD por vento medido deixa o modelo pior que não ter vento**: 0,717 → 0,673, contra 0,692 sem vento. Descartadas variável escondida e arredondamento; sobra ruído de 166 amostras. Fica um achado positivo — **28 km serve para vento** —, o que torna a ressalva de §18 específica de variáveis irregulares em vez de geral. E a lição: *uma diferença dentro do ruído declarado não deve virar prioridade de projeto*, que foi exatamente o erro cometido, já que §15 declarava o ruído. O conector do ERA5 fica **cancelado** ([ERA5.md](ERA5.md)). |
| 26/07/2026 | **Entrega 2, passo 2 rodado (§15–§19) — a resposta é não.** 30.212 valores diários de salinidade e oxigênio extraídos para os 90 dias antes de cada uma das 166 visitas, 332 pares, **zero falhas**. **Nenhuma combinação supera o modelo só-térmico na validação por ano** (0,717); acrescentar as quatro ambientais piora para 0,636, e sozinhas elas ficam em 0,527 contra taxa base 0,530 — acaso. As duas explicações alternativas foram testadas e caíram: **nenhum tamanho de janela** de 7 a 90 dias resgata o sinal (§16.1), e elas **não são identificador de sítio** (§16.2). O achado positivo é em §17: as quatro **separam as classes na direção fisicamente esperada** (oxigênio mais baixo e caindo nos sítios que branquearam, *d* = −0,38), com metade da força das térmicas, e essa separação **não vira previsão** — exatamente o que já acontecera com o oxigênio na entrega 1, agora repetido em base independente. §18 registra a explicação concorrente que estes dados **não descartam**: a grade do oxigênio é 28 km e 20 sítios só têm dado a até 33 km, então pode ser resolução e não mecanismo. O `Windspeed` segue como a única não térmica que funciona, o que promove o **ERA5** a prioridade alta. |
| 26/07/2026 | **Entrega 2, passo 1 rodado (§11–§14).** Alvo passa a ser branqueamento observado. Três correções ao levantamento inicial: a unidade amostral é a **visita** (166, não 313 amostras), `ClimSST` tem **sentinela** em 115 de 313 registros e saiu do baseline, e o equilíbrio de 53% **não** é artefato do limiar (só 2 dos 88 positivos têm < 0,1%). O resultado central: a regra da NOAA tem precisão 1,000 mas revocação 0,114 — **78 dos 88 branqueamentos ocorreram com `TSA_DHW` = 0**. Modelos térmicos ficam em 1,16×–1,35× o acaso ao serem testados num ano não visto, e o abismo sítio (0,803) × ano (0,614) mostra que a versão com 8 features reconhecia o evento, não o fenômeno. Adotada a versão **J** (`TSA_DHW`, `TSA`, `Windspeed`) como conjunto interpretável — 3 entradas, zero coeficientes invertidos, sítio 0,722 × ano 0,717 —, com ressalva de viés de seleção declarada em §12.3. `Windspeed` aparece como segunda variável mais útil: o primeiro sinal não térmico do projeto. |
| 25/07/2026 | **Versão D aplicada ao código.** `FEATURES_PADRAO` vazio e uma janela por variável — 4 entradas. Coeficientes todos com sinal fisicamente correto, e importância por coluna igual à por grupo, já que a colinearidade sumiu. Revelou o retrato honesto que a versão C disfarçava: **o modelo é essencialmente um modelo da trajetória do DHW** (+0,670 de 0,67 total), e as variáveis não térmicas não contribuem. Reforça a necessidade do GCBD para a entrega 2. |
| 25/07/2026 | **§8 — colinearidade diagnosticada, e o diagnóstico anterior estava errado.** Não é nível×trajetória (r ≈ 0,10) e sim **as duas janelas da mesma variável** (`dhw_variacao_7d` × `dhw_variacao_14d`, **r = 0,976**). Cinco versões comparadas: a **D — uma janela por variável** resolve, com 4 entradas em vez de 10, F1 0,728 contra 0,707, o melhor PR-AUC (0,790) e **nenhum coeficiente térmico invertido**. Custo: 16 episódios em vez de 18, dentro do ruído. Recomendação registrada: adotar D — ainda **não aplicada ao código**. |
| 25/07/2026 | Acrescentada a demonstração numérica de por que a colinearidade produz coeficiente absurdo — três fórmulas com coeficientes diferentes, incluindo um negativo, dando **a mesma predição**. E registrado o desenho do experimento que vai resolvê-la (§9), com as duas saídas possíveis já decididas. |
| 25/07/2026 | **§7 — importância das variáveis medida.** DHW e SST respondem por mais de 95% da capacidade preditiva. **O indício do oxigênio (VARIAVEIS §3.6) não se confirmou**: a trajetória contribui −0,001 e −0,006, ou seja, ruído; só o nível contribui algo pequeno (+0,021). Documentada também a divisão de crédito por correlação (grupo DHW cai 0,492 mas suas colunas isoladas somam 0,284) e — mais importante — que **os coeficientes da logística não são interpretáveis aqui**: `dhw` saiu negativo por colinearidade. Isso corrige o argumento de interpretabilidade da METODOLOGIA §5. |
| 25/07/2026 | Acrescentada a seção "Entendendo o resultado, com números pequenos": exemplo trabalhado de dois eventos (um de 60 dias, um de 5) mostrando por que contar dias e contar eventos dão respostas opostas, e por que a segunda é a que importa num sistema de aviso. |
| 25/07/2026 | Primeira rodada. Empate no acerto diário em 7 dias (F1 0,741 contra 0,738), vitória na detecção de episódios (18/19 contra 15/19) e vitória nas duas métricas em 14 dias. Confirmado que as features de trajetória são o que sustenta o resultado: sem elas o F1 cai para 0,489. 2022 identificado como o ano em que o modelo falha. |
