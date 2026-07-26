# Resultados — primeira rodada

Primeira execução completa do experimento da entrega 1, em **25/07/2026**.

O desenho do experimento (a régua, a validação, as métricas e por que elas)
está em [METODOLOGIA.md](METODOLOGIA.md). Este documento é só o que saiu.

---

## Em uma frase

> **Em 7 dias o modelo empata com a previsão burra no acerto diário, mas
> detecta 18 dos 19 episódios contra 15 dela — e em 14 dias passa a ganhar nas
> duas métricas.**

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
| **Alta** | **GCBD** | Com o BAA como alvo, a resposta a "variáveis não térmicas ajudam?" é **não**. Só rótulo observado pode mudar isso |
| Alta | Investigar 2022 | É o único ano em que o modelo perde claramente |
| Média | Curva de calibração | Brier bom não basta para exibir porcentagem num site |
| Média | Testar horizontes entre 7 e 21 dias | A vantagem cresce com o horizonte; achar onde ela vira |
| Baixa | Ajuste de hiperparâmetro | Só faz sentido depois de ampliar a base com o GCBD |

---

---

## Reprodução

```bash
python backend\manage.py shell -c "from aquaculture.models import LocalRecife; from ml.dataset import montar_todos; from ml.modelo import comparar_com_persistencia; locais=list(LocalRecife.objects.filter(latitude__isnull=False)); print(comparar_com_persistencia(montar_todos(locais, horizonte=7), nome='boosting').resumo())"
```

Semente fixa (`42`) em ambos os modelos; o resultado é determinístico.

---

## Histórico

| Data | Alteração |
|---|---|
| 25/07/2026 | **Versão D aplicada ao código.** `FEATURES_PADRAO` vazio e uma janela por variável — 4 entradas. Coeficientes todos com sinal fisicamente correto, e importância por coluna igual à por grupo, já que a colinearidade sumiu. Revelou o retrato honesto que a versão C disfarçava: **o modelo é essencialmente um modelo da trajetória do DHW** (+0,670 de 0,67 total), e as variáveis não térmicas não contribuem. Reforça a necessidade do GCBD para a entrega 2. |
| 25/07/2026 | **§8 — colinearidade diagnosticada, e o diagnóstico anterior estava errado.** Não é nível×trajetória (r ≈ 0,10) e sim **as duas janelas da mesma variável** (`dhw_variacao_7d` × `dhw_variacao_14d`, **r = 0,976**). Cinco versões comparadas: a **D — uma janela por variável** resolve, com 4 entradas em vez de 10, F1 0,728 contra 0,707, o melhor PR-AUC (0,790) e **nenhum coeficiente térmico invertido**. Custo: 16 episódios em vez de 18, dentro do ruído. Recomendação registrada: adotar D — ainda **não aplicada ao código**. |
| 25/07/2026 | Acrescentada a demonstração numérica de por que a colinearidade produz coeficiente absurdo — três fórmulas com coeficientes diferentes, incluindo um negativo, dando **a mesma predição**. E registrado o desenho do experimento que vai resolvê-la (§9), com as duas saídas possíveis já decididas. |
| 25/07/2026 | **§7 — importância das variáveis medida.** DHW e SST respondem por mais de 95% da capacidade preditiva. **O indício do oxigênio (VARIAVEIS §3.6) não se confirmou**: a trajetória contribui −0,001 e −0,006, ou seja, ruído; só o nível contribui algo pequeno (+0,021). Documentada também a divisão de crédito por correlação (grupo DHW cai 0,492 mas suas colunas isoladas somam 0,284) e — mais importante — que **os coeficientes da logística não são interpretáveis aqui**: `dhw` saiu negativo por colinearidade. Isso corrige o argumento de interpretabilidade da METODOLOGIA §5. |
| 25/07/2026 | Acrescentada a seção "Entendendo o resultado, com números pequenos": exemplo trabalhado de dois eventos (um de 60 dias, um de 5) mostrando por que contar dias e contar eventos dão respostas opostas, e por que a segunda é a que importa num sistema de aviso. |
| 25/07/2026 | Primeira rodada. Empate no acerto diário em 7 dias (F1 0,741 contra 0,738), vitória na detecção de episódios (18/19 contra 15/19) e vitória nas duas métricas em 14 dias. Confirmado que as features de trajetória são o que sustenta o resultado: sem elas o F1 cai para 0,489. 2022 identificado como o ano em que o modelo falha. |
