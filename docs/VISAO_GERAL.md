# O projeto explicado

Documento de entrada. Explica **o que o Coral Brasil faz, por que cada peça
existe e como elas se encaixam** — sem pressupor conhecimento de oceanografia
nem de aprendizado de máquina.

Os outros documentos aprofundam pedaços:
[FONTES.md](FONTES.md) (de onde vêm os dados),
[VARIAVEIS.md](VARIAVEIS.md) (por que cada variável entra),
[METODOLOGIA.md](METODOLOGIA.md) (como o modelo é avaliado),
[arquitetura.md](arquitetura.md) (onde tudo mora).

## Índice

1. [O problema real](#1-o-problema-real)
2. [O que o projeto se propõe a fazer](#2-o-que-o-projeto-se-propõe-a-fazer)
3. [Os três recifes](#3-os-três-recifes)
4. [Como se mede estresse térmico de longe](#4-como-se-mede-estresse-térmico-de-longe)
5. [As variáveis, uma a uma](#5-as-variáveis-uma-a-uma)
6. [De onde vêm os dados](#6-de-onde-vêm-os-dados)
7. [O caminho de um valor, do satélite até a tela](#7-o-caminho-de-um-valor-do-satélite-até-a-tela)
8. [Por que proveniência é o coração do projeto](#8-por-que-proveniência-é-o-coração-do-projeto)
9. [As duas entregas](#9-as-duas-entregas)
10. [O que já existe e o que falta](#10-o-que-já-existe-e-o-que-falta)
11. [Os defeitos herdados](#11-os-defeitos-herdados)
12. [Vocabulário](#12-vocabulário)

---

## 1. O problema real

Corais não são pedras. São animais que vivem em simbiose com algas
microscópicas (**zooxantelas**) que moram dentro dos seus tecidos. As algas
fazem fotossíntese e entregam ao coral a maior parte da energia de que ele
precisa; o coral dá abrigo e nutrientes em troca.

**Quando a água esquenta demais, essa relação quebra.** O coral expulsa as
algas. Sem elas, ele fica transparente e o esqueleto branco de carbonato
aparece por baixo — daí o nome **branqueamento**.

Um coral branqueado **não está morto**. Está faminto. Se a água esfriar em
poucas semanas, as algas voltam e ele se recupera. Se o calor persistir, ele
morre.

E aqui está a chave de tudo o que o projeto faz:

> **O que mata não é a temperatura máxima. É o calor acumulado ao longo do
> tempo.**

Um dia a 30 °C não faz nada. Oito semanas a 1 °C acima do normal fazem muito.
É por isso que a variável central do projeto (o **DHW**, seção 4) mede
acúmulo, e não pico.

### Por que isso é urgente no Brasil

Em 2024 o mundo passou pelo quarto evento global de branqueamento em massa já
registrado. A série deste projeto capturou esse evento nos três recifes — e
capturou também 2025, quando **a totalidade da área de Abrolhos** chegou a
ficar em alerta ao mesmo tempo.

---

## 2. O que o projeto se propõe a fazer

Duas coisas, com públicos diferentes:

**Um site público** que mostre o estado atual dos recifes brasileiros
monitorados, com dados reais e rastreáveis.

**Um trabalho acadêmico** que responda uma pergunta específica: *variáveis
além da temperatura ajudam a prever branqueamento?*

O rigor vem primeiro. A publicação vem depois, e só do que estiver sustentado.

Isso tem uma consequência prática que aparece o tempo todo no código: **o
projeto prefere não mostrar um número a mostrar um número errado**. Valor
reprovado na validação vira nulo com motivo registrado, nunca zero. Lacuna
fica visível como lacuna. Previsão nunca entra como medição.

---

## 3. Os três recifes

| Local | Estado | Latitude | Característica |
|---|---|---|---|
| **Abrolhos** | Bahia | −17,97° | Maior complexo recifal do Atlântico Sul; águas mais frias |
| **Porto de Galinhas** | Pernambuco | −8,5° | Recife costeiro, alto uso turístico |
| **Picãozinho** | Paraíba | −7,1° | Recife costeiro, área de proteção |

A escolha não é aleatória: eles cobrem um **gradiente latitudinal de ~11
graus**. Isso permite comparar como o mesmo forçante oceanográfico atinge
recifes em condições térmicas diferentes.

O dado confirma o gradiente sem que ninguém tenha programado isso: Abrolhos,
mais ao sul e mais frio, tem salinidade e oxigênio dissolvido mais altos —
água fria dissolve mais gás.

⚠️ **Três locais é pouco, e isso importa.** Os eventos caem nos mesmos anos nos
três, porque é o mesmo forçante atingindo a mesma costa. Não são três amostras
independentes. Ver [VARIAVEIS.md](VARIAVEIS.md) §7.2.

---

## 4. Como se mede estresse térmico de longe

Ninguém mergulha todo dia em três recifes. A medição vem de **satélite**, e a
NOAA transformou isso numa metodologia padronizada. Vale entender a cadeia,
porque as quatro variáveis dela são encadeadas.

### Passo 1 — A temperatura normal daquele lugar (MMM)

Não existe "temperatura perigosa" universal. Um coral de Abrolhos está
adaptado a uma faixa; um do Caribe, a outra.

A NOAA calcula, **para cada pixel de 5 km do mapa**, a
**MMM — Maximum Monthly Mean**: a média do mês mais quente do ano, na
climatologia histórica daquele pixel específico.

Para Abrolhos, a MMM implícita nos dados do projeto é **26,975 °C** — o que
bate com a literatura (~27 °C).

> 🚨 **O código legado do projeto usava 27,0 °C fixo para o Brasil inteiro.**
> Isso superestima o estresse em recifes frios e subestima em quentes. Foi um
> dos defeitos que motivaram a reconstrução (§11).

### Passo 2 — Quanto acima do normal está hoje (HotSpot)

```
HotSpot = SST de hoje − MMM do pixel
```

Se der negativo, a água está mais fria que o normal do lugar: sem estresse.
Só valores **positivos** contam.

### Passo 3 — O acúmulo (DHW)

**DHW — Degree Heating Week** — é a variável mais importante do projeto.

Ela soma o HotSpot ao longo das **últimas 12 semanas**, contando apenas os dias
em que ele passou de **1 °C**:

> Se o recife ficou 4 semanas com 2 °C acima da MMM,
> o DHW é 4 × 2 = **8 °C·semana**.

E os limiares da NOAA:

| DHW | Significado |
|---|---|
| 0 | sem estresse acumulado |
| ≥ 4 | branqueamento significativo esperado |
| ≥ 8 | **mortalidade** esperada, não só branqueamento |

**Duas propriedades do DHW que confundem, e que o projeto já tropeçou em ambas:**

1. **É um acumulador de 12 semanas.** Ele continua subindo enquanto houver
   estresse recente, e cai devagar. Por isso *DHW subindo não significa
   "piorando agora"* — significa "esteve quente nas últimas semanas". Foi
   exatamente o que a medição de trajetória mostrou ([VARIAVEIS.md](VARIAVEIS.md) §3.6).
2. **Só acumula acima de 1 °C.** Somar todos os hotspots positivos, como o
   código legado fazia, infla o número.

### Passo 4 — O alerta (BAA)

O **BAA — Bleaching Alert Area** traduz DHW e HotSpot numa **categoria**:

| BAA | Nome | Significado |
|---|---|---|
| 0 | Sem estresse | — |
| 1 | Vigilância | água aquecendo |
| 2 | Aviso | estresse começando a acumular |
| 3 | **Alerta Nível 1** | branqueamento esperado |
| 4 | **Alerta Nível 2** | mortalidade esperada |

É **o alvo do modelo**: o que o projeto tenta prever.

⚠️ **BAA é categoria, não número.** A diferença entre 3 e 4 não é "mais um" —
é a diferença entre coral doente e coral morto. Isso tem consequência direta em
como o valor é agregado: ver [VARIAVEIS.md](VARIAVEIS.md) §4.5, que explica
por que a média espacial estava errada e o que a substituiu.

---

## 5. As variáveis, uma a uma

### Do NOAA — as térmicas

| Variável | O que é | Papel |
|---|---|---|
| `sst` | Temperatura da superfície do mar (°C) | feature |
| `dhw` | Calor acumulado (°C·semana) | feature |
| `hotspot` | SST menos a MMM do pixel (°C) | ⛔ **proibida como feature** |
| `sst_anomalia` | Desvio da média histórica (°C) | opcional |
| `baa` | Categoria de alerta 0–4 | 🎯 **alvo** |
| `baa_area_alerta` | Fração do recife em alerta (0–1) | ⛔ proibida como feature |

**Por que `hotspot` é proibida.** Junto com o DHW, ela determina o BAA
*exatamente*, pela regra da NOAA. Usá-la como feature seria dar a resposta ao
modelo — ele não estaria prevendo, estaria lendo a tabela de limiares.

**O que é `baa_area_alerta`.** O recife não é um ponto: são ~121 pixels de
5 km. O `baa` guarda o **pior estado** entre eles; a `baa_area_alerta` guarda
**quanto do recife** está em alerta. Juntas respondem "o quão grave" e "o
quanto". Separadas, cada uma engana.

### Do Copernicus — as não térmicas

| Variável | O que é | Hipótese |
|---|---|---|
| `salinidade` | Sal dissolvido (PSU) | estresse osmótico soma-se ao térmico |
| `oxigenio` | O₂ dissolvido (mmol·m⁻³) | água quente retém menos O₂; hipóxia agrava |

Essas duas existem para responder a pergunta científica do trabalho. Se o
branqueamento fosse explicado só pela temperatura, elas não acrescentariam
nada — e essa é uma resposta possível, que o experimento precisa poder dar.

**Primeira evidência medida:** a *trajetória* do oxigênio distingue o início do
fim de um episódio melhor que a do DHW ([VARIAVEIS.md](VARIAVEIS.md) §3.6). É
sugestivo, não estabelecido — mas é o primeiro sinal de que a pergunta vale.

### O que ficou de fora, e por quê

- **KD490** (turbidez): só existe de 2023-11 em diante e sem reanálise. Entrar
  cortaria o treino de 6,5 para 2,7 anos e apagaria o evento de 2020.
- **pH, nitrato, clorofila**: escala temporal incompatível ou mecanismo
  indireto demais.
- **Vento**: o valor no banco legado é a constante inventada `6.5`. Precisa
  vir do ERA5 antes de qualquer uso.

Justificativa completa de cada exclusão em [VARIAVEIS.md](VARIAVEIS.md) §6.

---

## 6. De onde vêm os dados

### NOAA Coral Reef Watch — observação de satélite

Produto *Daily Global 5 km Coral Bleaching Heat Stress v3.1*. Acesso público
por **ERDDAP**, um protocolo padrão de servidores oceanográficos.

**43.038 medições**, 2020-01-01 a 2026-07-24, três locais, seis variáveis.

⚠️ **A série tem 6 datas ausentes**, três delas consecutivas. Não é falha do
pipeline — é lacuna do produto, confirmada em dois espelhos independentes.
Toda janela ou defasagem que atravesse essas datas precisa lidar com isso
explicitamente, e o código lida.

**Restrição de rede que vale saber:** os servidores da própria NOAA só
respondem de dentro de rede com domínio federal. O espelho **PACIOOS**
(Universidade do Havaí) redistribui o mesmo produto e funciona de qualquer
lugar — é o padrão do projeto desde que isso foi medido.

### Copernicus Marine — saída de modelo

Serviço europeu. **14.382 medições** de salinidade e oxigênio, mesmo período.

Duas coisas aqui não são óbvias:

**1. Cada série emenda dois produtos.** A *reanálise* cobre desde 1993 mas para
cerca de um mês atrás; a *análise* começa depois e vai até hoje. Nenhum sozinho
cobre a série do projeto. O conector usa a reanálise (melhor, já reprocessada)
onde ela existe, e completa com a análise. **Cada medição grava de qual dos
dois veio.**

**2. Previsão nunca entra.** Os produtos de análise publicam datas *no futuro*.
Gravar isso como medição seria vazamento direto — o modelo aprenderia com a
previsão do próprio fenômeno que deve prever. O corte é sempre em ontem.

### Uma diferença que não é qualidade

| | NOAA | Copernicus |
|---|---|---|
| Natureza | observação de satélite | saída de modelo |
| Lacunas | 6 datas | **nenhuma** |

**Copernicus não ter lacuna não o torna melhor.** Modelo produz valor para todo
dia e todo pixel, inclusive onde não houve observação assimilada. O NOAA tem
buracos justamente por ser observacional. Comparar as duas séries pela
completude inverteria o que cada uma vale como evidência.

---

## 7. O caminho de um valor, do satélite até a tela

```
   satélite / modelo
          ↓
   [ conectores ]      backend/ingestao/conectores/
          ↓            fala com a fonte, devolve leitura bruta
   [ normalização ]    traduz nome e unidade para o vocabulário canônico
          ↓            (CRW_SST → sst, °C)
   [ validação ]       faixa física: reprovado vira NULL com motivo
          ↓            jamais zero
   [ persistência ]    upsert idempotente no PostgreSQL
          ↓            (local, data, variável, fonte)
   [ PostgreSQL ]      fonte única da verdade — 57.420 medições
          ↓
   [ dataset ]         backend/ml/dataset.py
          ↓            features em t, alvo em t+N, guardas contra vazamento
   [ modelo ]          backend/ml/modelo.py
          ↓
   [ API + site ]
```

Cada etapa tem uma responsabilidade só, e isso é deliberado: o conector **não**
decide nomes nem unidades, a normalização **não** fala com a rede, a validação
**não** grava. É o que permite testar a lógica difícil sem depender de
internet — 199 testes rodam offline.

### Três regras que valem em todo o caminho

**1. Idempotência.** Rodar a mesma ingestão duas vezes atualiza os mesmos
registros, não duplica nem apaga. O código legado fazia `delete_all()` antes de
gravar — uma falha no meio deixava o banco vazio.

**2. Nulo nunca vira zero.** O código legado preenchia lacunas com `.fillna(0)`,
gravando pH 0 e salinidade 0 — fisicamente impossíveis, e alimentados direto no
modelo. Aqui, valor reprovado vira `NULL` com `quality_flag` e o motivo escrito.

**3. Falha de uma fonte não derruba as outras.** Cada coleta vira um registro
em `ExecucaoIngestao` com status e erro. Falha passageira (503, timeout) é
repetida; falha definitiva (403, certificado) não gasta tentativa.

---

## 8. Por que proveniência é o coração do projeto

Cada medição no banco carrega:

| Campo | Exemplo | Para quê |
|---|---|---|
| `fonte` | `noaa_crw` | qual conector trouxe |
| `dataset_id` | `dhw_5km` | qual produto exatamente |
| `quality_flag` | `ok` / `degradado` / `invalido` | passou na validação? |
| `observacao` | *"fora da faixa esperada"* | por que foi degradado |
| `data_coleta` | timestamp | quando foi buscado |

Isso parece burocracia até a primeira vez que alguém pergunta **"de onde veio
esse número?"** — e numa banca, alguém pergunta.

O caso concreto do projeto: a série de salinidade **emenda dois produtos
diferentes** no meio. Sem `dataset_id` por valor, essa costura seria invisível
no banco. Com ela, dá para mostrar exatamente onde um produto termina e o outro
começa, e testar se isso introduziu degrau.

O documento [FONTES.md](FONTES.md) leva isso adiante: ele cataloga **19
problemas de proveniência** encontrados no projeto herdado, cada um com
medição, e o que foi feito com ele.

---

## 9. As duas entregas

O projeto tem duas perguntas, com dificuldades bem diferentes.

### Entrega 1 — Previsão de estresse térmico

> *Olhando o mar hoje, o recife estará em alerta daqui a N dias?*

Usa os dados que já estão em mãos. Destrava o painel do site.

**O nome honesto do produto é "previsão de estresse térmico", não "previsão de
branqueamento"** — porque o alvo é o BAA, que é uma classificação de *condição
ambiental*, não uma observação de coral branqueado.

Como isso é avaliado (a régua, o teste sem trapaça, as métricas) está em
[METODOLOGIA.md](METODOLOGIA.md).

### Entrega 2 — A pergunta científica

> *Salinidade e oxigênio acrescentam sinal além da temperatura?*

Exige **rótulo real**: branqueamento observado em campo, não classificação
derivada de satélite. A fonte é o **Global Coral-Bleaching Database** (van
Woesik & Kratochwill, 2022) — 34.846 registros, 1980–2020, com dados
brasileiros.

Essa é a contribuição científica do TCC. É também a mais difícil: a base atual
tem ~4 anos-evento, o que limita muito o que se pode afirmar.

### Por que quase foi circular

Vale registrar, porque é o tipo de armadilha que passa despercebida.

O plano original era treinar `{SST, DHW, salinidade, O₂} → BAA`. Mas o BAA é
**definido** a partir de SST e DHW. Medindo no dado real: uma árvore de decisão
usando *só* SST e DHW acerta o BAA em **95,7%**.

O modelo não aprenderia o fenômeno — aprenderia a tabela de limiares da NOAA.
Salinidade e oxigênio receberiam importância zero, não por serem irrelevantes,
mas porque não haveria nada a explicar.

**A saída foi o horizonte.** Prever o BAA *daqui a N dias* não é circular,
porque o DHW futuro não é conhecido hoje. Detalhe em
[VARIAVEIS.md](VARIAVEIS.md) §4.

---

## 10. O que já existe e o que falta

### Pronto

| | |
|---|---|
| **Ingestão automatizada** | NOAA e Copernicus, com retentativa, proveniência por valor e registro de execução |
| **57.420 medições** | 2020–2026, três locais, oito variáveis |
| **PostgreSQL** | fonte única, subindo por Docker |
| **Conjunto supervisionado** | features em `t`, alvo em `t+N`, com guardas contra vazamento |
| **Linha de base** | persistência medida: F1 0,840 em 7 dias |
| **Modelo treinado e comparado** | primeira rodada em [RESULTADOS.md](RESULTADOS.md): detecta 18 de 19 episódios contra 15 da persistência |
| **Importância das variáveis** | medida: DHW e SST respondem por >95% da capacidade preditiva |
| **227 testes** | rodam offline |

### Falta

| | |
|---|---|
| **Resolver a colinearidade** | ⚠️ hoje os coeficientes não são interpretáveis — o `dhw` sai negativo. Sem isso não há como afirmar direção de efeito |
| **GCBD** | sem rótulo observado não há entrega 2 |
| **Projeção do Neo4j** | ⚠️ o grafo ainda mostra dado do caminho legado |
| **Agendamento** | nada roda sozinho ainda |
| **API e site** | endpoints, paginação, mapa, séries temporais |
| **CI** | não existe |
| **ERA5** | o vento continua sendo constante inventada |

---

## 11. Os defeitos herdados

O projeto começou com um código que tinha problemas graves e silenciosos. Vale
listar porque **alguns ainda existem no caminho legado**, e porque explicam por
que várias decisões parecem exageradas.

| Defeito | O que acontecia | Situação |
|---|---|---|
| Predições todas 0,0 | Ordem de features divergia entre treino e predição; `except` sem tipo engolia o erro | ⛔ vive no `ml_models/` legado |
| IA aprendia uma fórmula | O alvo vinha de `calcular_risco()`, regra escrita à mão. R² alto e tautológico | ⛔ idem |
| `.fillna(0)` | Lacuna virava pH 0 e salinidade 0 | ✅ neutralizado no caminho novo |
| DHW fora da norma | Limiar fixo de 27 °C global, somando todo hotspot positivo | ✅ usa `CRW_DHW` oficial |
| Alcalinidade lida como pH | `talk` gravado no campo `ph` | ✅ recusado com teste |
| `delete_all()` antes de gravar | Falha no meio esvaziava o banco | ✅ upsert idempotente |
| Catálogo fictício | 8 datasets inventados, servidos por API real | ✅ removido |
| Vento inventado | Constante `6.5` em todos os registros | ⛔ ainda no banco legado |

O catálogo completo, com medição de cada um, está em [FONTES.md](FONTES.md) §6.

---

## 12. Vocabulário

| Termo | Significado |
|---|---|
| **Branqueamento** | Coral expulsa suas algas simbiontes por estresse. Não é morte, é fome |
| **Zooxantelas** | As algas que vivem no coral e o alimentam |
| **SST** | *Sea Surface Temperature* — temperatura da superfície do mar |
| **MMM** | *Maximum Monthly Mean* — média do mês mais quente, por pixel |
| **HotSpot** | SST menos MMM. Só conta se positivo |
| **DHW** | *Degree Heating Week* — calor acumulado em 12 semanas |
| **BAA** | *Bleaching Alert Area* — categoria de alerta, 0 a 4 |
| **PSU** | *Practical Salinity Unit* — unidade de salinidade |
| **ERDDAP** | Protocolo de servidor de dados oceanográficos |
| **Reanálise** | Dado de modelo reprocessado, com observações assimiladas |
| **Análise/previsão** | Dado de modelo em tempo quase real, incluindo futuro |
| **Idempotente** | Rodar duas vezes dá o mesmo resultado que rodar uma |
| **Vazamento** | O modelo enxerga informação que não teria na hora real |
| **Persistência** | Previsão burra: "daqui a N dias será igual a hoje" |
| **Episódio** | Sequência de dias contíguos em alerta |
| **Leave-year-out** | Validação escondendo um ano inteiro do treino |
| **Upsert** | Grava se não existe, atualiza se existe |
| **Proveniência** | O registro de onde cada valor veio |

---

## Histórico

| Data | Alteração |
|---|---|
| 25/07/2026 | Estado atualizado: importância das variáveis medida (DHW e SST respondem por mais de 95% da capacidade preditiva) e a colinearidade registrada como pendência — hoje os coeficientes não permitem afirmar direção de efeito. |
| 25/07/2026 | Documento criado como porta de entrada do projeto: o problema biológico, a cadeia MMM→HotSpot→DHW→BAA explicada com exemplo, as fontes e suas naturezas distintas, o caminho do dado, as duas entregas, o que falta e os defeitos herdados. |
