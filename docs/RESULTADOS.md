# Resultados

O desenho dos experimentos (a régua, a validação, as métricas e por que elas)
está em [METODOLOGIA.md](METODOLOGIA.md). Este documento é só o que saiu.

| Parte | O quê | Quando | Seções |
|---|---|---|---|
| **Entrega 1** | Prever o **BAA** em t+N, nos 3 recifes monitorados | 25/07/2026 | §1–§10 |
| **Entrega 2, passo 1** | Prever **branqueamento observado**, nos sítios do GCBD | 26/07/2026 | §11–§14 |

---

## Em uma frase, cada uma

> **Entrega 1** — Em 7 dias o modelo empata com a previsão burra no acerto
> diário, mas detecta 18 dos 19 episódios contra 15 dela; e em 14 dias passa a
> ganhar nas duas métricas.

> **Entrega 2, passo 1** — A regra de estresse térmico da NOAA, quando dispara,
> acerta quase sempre; mas dos 88 branqueamentos observados no Brasil ela pega
> **10**. O sinal térmico sozinho não explica o fenômeno.

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
| **J — `TSA_DHW`+`TSA`+`Windspeed`** | **3** | **0,722** | **0,717** | **0** |
| K — `TSA_DHW`+`SSTA_Freq`+`Windspeed` | 3 | 0,750 | 0,706 | 1 |

**A versão J é a adotada como conjunto interpretável.** Três entradas, nenhum
coeficiente invertido:

| Variável | Coeficiente | Leitura física |
|---|---|---|
| `TSA_DHW` | **+0,950** | estresse térmico acumulado piora |
| `Windspeed` | −0,355 | vento mistura a coluna d'água e resfria — negativo é o esperado |
| `TSA` | +0,210 | anomalia térmica do dia piora |

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

---

## Histórico

| Data | Alteração |
|---|---|
| 26/07/2026 | **Entrega 2, passo 1 rodado (§11–§14).** Alvo passa a ser branqueamento observado. Três correções ao levantamento inicial: a unidade amostral é a **visita** (166, não 313 amostras), `ClimSST` tem **sentinela** em 115 de 313 registros e saiu do baseline, e o equilíbrio de 53% **não** é artefato do limiar (só 2 dos 88 positivos têm < 0,1%). O resultado central: a regra da NOAA tem precisão 1,000 mas revocação 0,114 — **78 dos 88 branqueamentos ocorreram com `TSA_DHW` = 0**. Modelos térmicos ficam em 1,16×–1,35× o acaso ao serem testados num ano não visto, e o abismo sítio (0,803) × ano (0,614) mostra que a versão com 8 features reconhecia o evento, não o fenômeno. Adotada a versão **J** (`TSA_DHW`, `TSA`, `Windspeed`) como conjunto interpretável — 3 entradas, zero coeficientes invertidos, sítio 0,722 × ano 0,717 —, com ressalva de viés de seleção declarada em §12.3. `Windspeed` aparece como segunda variável mais útil: o primeiro sinal não térmico do projeto. |
| 25/07/2026 | **Versão D aplicada ao código.** `FEATURES_PADRAO` vazio e uma janela por variável — 4 entradas. Coeficientes todos com sinal fisicamente correto, e importância por coluna igual à por grupo, já que a colinearidade sumiu. Revelou o retrato honesto que a versão C disfarçava: **o modelo é essencialmente um modelo da trajetória do DHW** (+0,670 de 0,67 total), e as variáveis não térmicas não contribuem. Reforça a necessidade do GCBD para a entrega 2. |
| 25/07/2026 | **§8 — colinearidade diagnosticada, e o diagnóstico anterior estava errado.** Não é nível×trajetória (r ≈ 0,10) e sim **as duas janelas da mesma variável** (`dhw_variacao_7d` × `dhw_variacao_14d`, **r = 0,976**). Cinco versões comparadas: a **D — uma janela por variável** resolve, com 4 entradas em vez de 10, F1 0,728 contra 0,707, o melhor PR-AUC (0,790) e **nenhum coeficiente térmico invertido**. Custo: 16 episódios em vez de 18, dentro do ruído. Recomendação registrada: adotar D — ainda **não aplicada ao código**. |
| 25/07/2026 | Acrescentada a demonstração numérica de por que a colinearidade produz coeficiente absurdo — três fórmulas com coeficientes diferentes, incluindo um negativo, dando **a mesma predição**. E registrado o desenho do experimento que vai resolvê-la (§9), com as duas saídas possíveis já decididas. |
| 25/07/2026 | **§7 — importância das variáveis medida.** DHW e SST respondem por mais de 95% da capacidade preditiva. **O indício do oxigênio (VARIAVEIS §3.6) não se confirmou**: a trajetória contribui −0,001 e −0,006, ou seja, ruído; só o nível contribui algo pequeno (+0,021). Documentada também a divisão de crédito por correlação (grupo DHW cai 0,492 mas suas colunas isoladas somam 0,284) e — mais importante — que **os coeficientes da logística não são interpretáveis aqui**: `dhw` saiu negativo por colinearidade. Isso corrige o argumento de interpretabilidade da METODOLOGIA §5. |
| 25/07/2026 | Acrescentada a seção "Entendendo o resultado, com números pequenos": exemplo trabalhado de dois eventos (um de 60 dias, um de 5) mostrando por que contar dias e contar eventos dão respostas opostas, e por que a segunda é a que importa num sistema de aviso. |
| 25/07/2026 | Primeira rodada. Empate no acerto diário em 7 dias (F1 0,741 contra 0,738), vitória na detecção de episódios (18/19 contra 15/19) e vitória nas duas métricas em 14 dias. Confirmado que as features de trajetória são o que sustenta o resultado: sem elas o F1 cai para 0,489. 2022 identificado como o ano em que o modelo falha. |
