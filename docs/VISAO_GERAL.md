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
          ↓            treina, mede, recalibra
   [ artefato ]        dados/modelos/entrega1_baa.joblib
          ↓            gravado uma vez por manage.py treinar_final
   [ predição ]        backend/ml/predicao.py
          ↓            monta a janela de HOJE — sem alvo, que ainda não existe
   [ API + site ]      /api/painel-risco/
```

⚠️ **O ramo `dataset → modelo` e o ramo `artefato → predição` fazem a mesma
conta e por isso não podem ser dois códigos.** O primeiro monta a janela para
aprender; o segundo, para responder. Se divergirem, o modelo recebe colunas com
o nome certo e o conteúdo errado — e responde sem erro nenhum. Por isso
`predicao.py` **não recalcula nada**: ele traduz o nome da coluna de volta numa
`dataset.Janela` e chama o mesmo `dataset.aplicar_janela`.

Cada etapa tem uma responsabilidade só, e isso é deliberado: o conector **não**
decide nomes nem unidades, a normalização **não** fala com a rede, a validação
**não** grava. É o que permite testar a lógica difícil sem depender de
internet — 298 testes rodam offline.

### 7.1 A viagem de um número, concretamente

O diagrama acima é abstrato. Vale segui-lo com **um valor só**: a temperatura
do mar em **Abrolhos, no dia 24/07/2026**.

**Onde ela nasce.** Um satélite da NOAA mede a temperatura da superfície do
mar. O número fica num servidor nos EUA — e numa cópia no Havaí, o PACIOOS, que
é de onde o projeto lê (§6).

**"Conectar ao servidor" é literalmente isso:** o programa abre um endereço na
internet, como quem abre um site. Só que em vez de uma página, volta uma
tabela de números.

Rodando `python backend\manage.py ingerir`, em ordem:

| # | O que acontece | Onde no código |
|---|---|---|
| 1 | Monta o endereço: *"temperatura em volta de Abrolhos, de tal data a tal data"* | `ingestao/conectores/noaa_crw.py` |
| 2 | O PACIOOS responde com uma tabela | (rede, TLS verificado pelo `certifi`) |
| 3 | A tabela tem vários **quadradinhos de 5 km** cobrindo o recife; viram um número só — **28,4 °C** | agregação espacial |
| 4 | Confere se 28,4 °C é temperatura possível para o mar. **Se viesse 200 °C, grava `NULL` e o motivo — nunca o número absurdo** | `ingestao/qualidade.py` |
| 5 | Grava **uma linha** | `ingestao/persistencia.py` |

A linha gravada:

| local | data | variável | valor | fonte | dataset_id |
|---|---|---|---|---|---|
| Abrolhos | 2026-07-24 | `sst` | 28,4 | `noaa_crw` | `dhw_5km` |

E ela **fica salva**, até alguém apagar. Hoje são **57.420 linhas** dessas.

O Copernicus percorre o mesmo caminho. Duas diferenças: **exige senha** — que
mora em `~/.copernicusmarine`, fora do repositório e nunca na linha de comando
— e entrega salinidade e oxigênio em vez de temperatura.

### 7.2 Onde cada coisa fica salva — são três lugares

```
  PostgreSQL (Docker)   57.420 medições, 3 recifes, 2020–2026
                        ✅ é a fonte única da verdade da ENTREGA 1

  dados/                global_bleaching_environmental.csv  (o GCBD)
                        gcbd_janelas_ambientais.csv         (30.212 valores)
                        ✅ a ENTREGA 2 — não versionados, reconstruíveis

  backend/dados/        ~260 MB de CSV de abril/2026
                        ⛔ NÃO usados por nada — ver FONTES.md §6
```

**Por que a entrega 2 não entra no banco.** `MedicaoAmbiental` pendura em
`LocalRecife`, e `LocalRecife` são os **três recifes monitorados**, com foto,
slug e página pública. O GCBD tem **119 pontos de mergulho** onde alguém
esteve uma vez em 2007. Cadastrá-los como `LocalRecife` criaria 119 recifes
falsos no site para viabilizar um experimento. Ver [GCBD.md](GCBD.md).

**A terceira pasta é lixo herdado.** É onde estão o `ph.csv` que na verdade
contém alcalinidade e o arquivo da NOAA com coordenadas do Mar Vermelho
([FONTES.md](FONTES.md) §6.2 e §6.3). O código novo não abre nenhum deles —
mas eles continuam ocupando disco, e apagá-los ainda não foi feito.

### 7.3 ✅ Os dados são salvos. O modelo, agora também.

> **Resolvido em 27/07/2026.** O texto abaixo descreve o problema como ele era,
> porque a distinção entre *dado* e *modelo* continua valendo. A solução está em
> §7.4.


Vale separar dois conceitos que o diagrama junta:

| | O que é | Está salvo? |
|---|---|---|
| **Dado** | o número — *"28,4 °C em Abrolhos no dia 24"* | ✅ sim, no PostgreSQL |
| **Modelo** | o que foi **aprendido** com os números — mais parecido com uma receita: *"quando o DHW sobe rápido e o vento está fraco, o risco é alto"* | ❌ **não** |

Hoje, `treinar_modelo` e `treinar_gcbd` fazem isto:

1. leem os dados
2. aprendem a receita
3. medem se a receita é boa
4. **jogam a receita fora**
5. imprimem a nota na tela

É um aluno que estuda, faz a prova, tira 7 e esquece tudo.

**E isso está certo para o que foi feito até aqui.** A validação treina cinco
modelos — um por dobra — e usa cada um só para prever a parte que ele não viu.
Nunca existe "o modelo"; existem cinco modelos parciais e uma métrica. Guardar
qualquer um deles seria guardar um modelo que viu 4/5 dos dados.

**Mas vira bloqueio no dia em que o site precisar responder.** Para exibir
*"risco hoje: 37%"*, alguém precisa treinar **uma vez sobre todos os dados** e
gravar o artefato junto com os metadados que o descrevem —
`ml/modelo.py::Ajuste.metadados()` já existe exatamente para isso e não é
chamado por ninguém.

O único `.pkl` do projeto é `backend/ml_models/modelo_coral_rf.pkl`, do caminho
legado — o mesmo que predizia `0.0` para tudo (§11).

### 7.4 Como o modelo passou a ser salvo

Um comando novo, que faz **o oposto** dos comandos de medição:

```bash
python backend\manage.py treinar_final
```

| | `treinar_modelo` / `treinar_gcbd` | `treinar_final` |
|---|---|---|
| Para quê | **medir** se o modelo presta | **gravar** o que será servido |
| Como treina | um modelo por dobra, cada um sem uma parte | **um só, sobre tudo** |
| O que sobra | uma métrica | um artefato |
| Reporta desempenho? | sim | **não, de propósito** |

⚠️ **`treinar_final` não mede nada, e isso é deliberado.** Um número calculado
sobre os mesmos dados do treino mediria memória, não previsão. Quem responde "o
modelo presta?" é o outro comando.

O que ficou gravado hoje:

| | |
|---|---|
| Alvo | `baa ≥ 3` em t+7 |
| Colunas | `sst_variacao_7d`, `dhw_variacao_7d`, `salinidade_variacao_7d`, `oxigenio_variacao_7d` |
| Amostras | 7.095, com 596 positivas (8,4%) |
| Locais | os três |

**Três decisões, e nenhuma é óbvia:**

**1. O artefato não é versionado.** Vai para `dados/modelos/`, no `.gitignore`.
Um `.joblib` no repositório envelhece em silêncio: em duas semanas o arquivo diz
uma coisa e o código diz outra, e ninguém sabe qual vale. Mesma decisão já
tomada para o `.docx` e para a projeção do Neo4j — **o comando reconstrói**.

**2. Os metadados viajam ao lado, em JSON legível.** Sem eles, ninguém consegue
responder *"este modelo foi treinado com quais colunas, sobre quantas amostras,
em que data"* sem abrir o pickle — e abrir é justamente o que se quer evitar
antes de saber o que é.

**3. 🚨 Carregar `joblib` executa código.** Por baixo é `pickle`, que pode
executar qualquer coisa durante a leitura. Não é problema para um arquivo que o
próprio projeto acabou de gerar; **é problema sério** para um vindo de fora. Por
isso `carregar` lê o JSON **primeiro**, confere a assinatura do projeto e a
versão do scikit-learn, e recusa o que não reconhece.

A versão do scikit-learn importa por um motivo prático além da segurança: o
pickle de um `Pipeline` não tem compatibilidade garantida entre versões, e **a
falha costuma ser silenciosa** — o objeto carrega e prevê errado. Melhor recusar
e mandar regerar.

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

📝 **Para escrever artigo ou monografia:** a [§7 do FONTES.md](FONTES.md#7-como-citar-e-onde-cada-fonte-entra)
é o mapa de citação. Ela liga cada fonte ao que ela produz no projeto, ao
arquivo do código, e **às afirmações documentadas que dependem dela** — para
que, ao escrever um parágrafo, dê para saber o que precisa ser citado nele.
Registra também duas pendências bloqueantes para submissão: os DOIs dos
produtos CMEMS e uma referência não identificada no código legado.

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

#### ✅ Passo 1 feito em 26/07/2026 — e ele muda a leitura do projeto

O primeiro passo era gratuito: usar as variáveis térmicas que já vêm no próprio
GCBD, sem ingerir nada, para saber **quanto do branqueamento observado a
temperatura sozinha explica**. São 166 visitas a recifes brasileiros, entre
1994 e 2010, metade delas com branqueamento.

> **A régua publicada da NOAA (`DHW ≥ 4`) acertou 10 de 10 quando disparou — e
> ficou calada em 78 dos 88 branqueamentos observados.**

Ou seja: estresse térmico acumulado é **suficiente** para branquear coral, mas
está **longe de ser necessário**. A maior parte do branqueamento brasileiro
registrado aconteceu sem que o termômetro tivesse o que dizer.

Isso é a justificativa do projeto inteiro, medida em vez de suposta. Se a
temperatura explicasse tudo, bastaria traduzir o alerta da NOAA para português.

#### 🚨 Passo 2 feito no mesmo dia — e a resposta é não

Buscados **30.212 valores diários** de salinidade e oxigênio para os 90 dias
antes de cada visita, zero falhas. **Nenhuma combinação supera o modelo
só-térmico**, e sozinhas as duas ficam no acaso.

Testadas e derrubadas as duas explicações alternativas: nenhum tamanho de
janela de 7 a 90 dias ajuda, e elas não são identificador de sítio disfarçado.

**O que não é zero:** as duas **separam as classes na direção que a biologia
previa** — onde branqueou, o oxigênio estava mais baixo e caindo, e a
salinidade também. Com cerca de metade da força das térmicas. Separação real
que não vira previsão — e é a **segunda vez** que o projeto vê isso com o
oxigênio, agora em base independente ([VARIAVEIS.md](VARIAVEIS.md) §3.6).

⚠️ **A ressalva é séria e não pode ser omitida.** A grade do produto de
oxigênio é **28 km**, e 20 sítios só têm dado a até 33 km do recife. Uma pluma
de água doce num recife costeiro é exatamente o que uma célula desse tamanho
calcula a média para fora. O resultado negativo é sobre **estes produtos nesta
resolução**, não sobre o mecanismo. Ver [RESULTADOS.md](RESULTADOS.md) §18.

#### 🚨 E o vento, que parecia a saída, também não se confirmou

Por algumas horas o vento pareceu ser a resposta: segunda variável mais
importante, coeficiente −0,72, e não térmica. Isso promoveu o ERA5 a prioridade
máxima do projeto.

**Mas toda essa evidência vinha de uma única coluna** — o `Windspeed` do próprio
GCBD — e ninguém tinha conferido se ela descreve o vento.

Baixamos vento real do ERA5 para os mesmos 166 pontos e datas. As duas fontes
**concordam sobre o vento** (r = +0,708), e **discordam sobre o coral**:
*d* = −0,461 na coluna do GCBD contra **−0,057** no ERA5. **Trocar por vento
medido de verdade deixa o modelo pior do que não ter vento nenhum.**

> **O placar real: nenhuma variável não térmica testada se confirma.**
> Salinidade, oxigênio e vento — os três descrevem o branqueamento, nenhum
> consegue prevê-lo.

Ver [RESULTADOS.md](RESULTADOS.md) §15–§20 e [ERA5.md](ERA5.md).

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
| **GCBD, passo 1** | branqueamento **observado** como alvo, sem ingerir nada: a régua da NOAA pega 10 dos 88 eventos brasileiros ([RESULTADOS.md](RESULTADOS.md) §11) |
| **GCBD, passo 2** | 30.212 valores de salinidade e O₂ nos 90 dias antes de cada visita: **não acrescentam sinal** (§15–§19) |
| **A pergunta científica respondida** | com os dados disponíveis, e com a ressalva de resolução declarada |
| **Documentação em .docx** | artefato derivado, regerável com `manage.py exportar_docs` |
| **Projeção do Neo4j** | 57.420 medições no grafo, com proveniência por valor, conferidas contra o Postgres |
| **Modelo persistido** | `manage.py treinar_final` grava `.joblib` + metadados legíveis; o carregamento recusa artefato de outra origem ou versão (§7.4) |
| **Calibração medida e corrigida** | o modelo prometia **o dobro** do que acontecia; recalibração isotônica levou o ECE de 0,081 a **0,0039** ([RESULTADOS.md](RESULTADOS.md) §22) |
| **API da série ambiental** | `/api/medicoes/`, com proveniência por valor, filtros combináveis e paginação com teto |
| **Predição servida** | `/api/painel-risco/` — o primeiro endpoint que **faz conta**: carrega o artefato, monta a janela de hoje e devolve probabilidade calibrada com data-base e limiar |
| **441 testes** | rodam offline |

### Falta

| | |
|---|---|
| **O site consumir o `painel-risco`** | O backend responde; a tela ainda mostra o caminho legado. 🚨 E ela **não pode exibir "0%" nem "100%"** — a isotônica devolve extremos exatos por construção ([RESULTADOS.md](RESULTADOS.md) §22.8) |
| **Nome honesto do produto na interface** | O modelo prevê **estresse térmico**, não branqueamento observado — a régua da NOAA perde 78 dos 88 branqueamentos brasileiros (§11) |
| **Passo de deploy que reconstrua os derivados** | São **três** agora, todos não versionados: o `.docx`, o `.joblib` e o grafo do Neo4j. Quem publicar precisa rodar os três comandos, e esse passo não existe |
| **Aprovar o limiar de alerta** | 0,20 está em `settings.PAINEL_LIMIAR` porque é o ponto equivalente ao antigo 0,50 — não porque alguém escolheu a troca entre alarme falso e evento perdido |
| **Variáveis canônicas aprovadas** | item de go-live ainda aberto |
| **Apagar os 9 CSVs ainda catalogados** | ⚠️ **Decisão pendente, não faxina.** Os 7 arquivos defeituosos (179,9 MB) foram apagados em 28/07/2026; sobram 80 MB que a página "Banco de Dados" inventaria. Apagá-los **esvazia a página** — ver [FONTES.md](FONTES.md) §6.21 |
| **Os 7 arquivos órfãos** | 1,8 MB que não estão catalogados **nem** declarados defeituosos. Não documentados, e por isso não apagados |
| **DOIs dos produtos CMEMS** | bloqueia submissão, não o site |
| **Agendamento** | nada roda sozinho ainda |
| **CI** | não existe |
| **Dado *in situ* de salinidade e O₂** | resolveria a ressalva de §18, mas não existe para os sítios do GCBD |
| ⛔ ~~ERA5 — vento real~~ | **Cancelado em 26/07/2026.** O vento medido piora o modelo ([RESULTADOS.md](RESULTADOS.md) §20). A infraestrutura medida fica registrada em [ERA5.md](ERA5.md) |

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
| 27/07/2026 | ✅ **§7 e §10 atualizadas — o caminho do dado chegou até a tela.** O diagrama ganhou os dois passos que faltavam: **artefato** (`dados/modelos/*.joblib`) e **predição** (`ml/predicao.py`), este último montando a janela de **hoje**, para a qual o alvo ainda não existe. Registrado por que os dois ramos — treinar e responder — não podem ser dois códigos: se divergirem, o modelo recebe colunas com o nome certo e o conteúdo errado e responde sem erro nenhum, então `predicao.py` traduz o nome da coluna de volta numa `dataset.Janela` e chama o mesmo `aplicar_janela`. Em §10 entram como prontos a **API da série ambiental** e a **predição servida**; entram como pendências o site consumir o painel — com a proibição nova de exibir "0%" ou "100%" (§22.8 de [RESULTADOS.md](RESULTADOS.md)) — e a **aprovação do limiar 0,20**, que hoje está no `settings` por ser o ponto equivalente ao antigo 0,50, e não por decisão de produto. |
| 27/07/2026 | §10 atualizada: **projeção do Neo4j concluída** — o grafo deixou de mostrar dado legado e passou a ter as 57.420 medições com proveniência por valor. Também entram em "pronto" a **persistência do modelo** e a **calibração da probabilidade**. Restam como pendências o passo de deploy que reconstrua os três artefatos derivados, os endpoints, o nome honesto do produto na interface e o painel. |
| 27/07/2026 | ✅ **§7.4 criada — o modelo passou a ser salvo.** `manage.py treinar_final` faz o oposto dos comandos de medição: um modelo só, sobre todos os dados, gravado em `dados/modelos/` com metadados em JSON ao lado. Registradas as três decisões e o motivo de cada uma — artefato **não versionado** (cópia versionada envelhece em silêncio), metadados **legíveis sem abrir o pickle** (é preciso saber o que é o arquivo antes de executá-lo), e recusa de artefato desconhecido porque 🚨 **`joblib.load` executa código** e o pickle de um `Pipeline` falha em silêncio entre versões do scikit-learn. §10 troca a pendência: sai "persistir o modelo", entra "**passo de deploy que rode `treinar_final`**", já que o artefato é derivado. |
| 26/07/2026 | 🚨 **§9 corrigida — o vento também não se confirmou, e o ERA5 foi cancelado.** A afirmação de que o vento era a variável não térmica que funciona vinha de **uma única coluna** do GCBD, nunca conferida. Contra vento medido do ERA5 nos mesmos 166 pontos e datas, as duas fontes concordam sobre o vento (r = +0,708) e discordam sobre o coral (*d* = −0,461 contra −0,057); trocar uma pela outra deixa o modelo **pior que sem vento**. O placar real passa a ser: **nenhuma variável não térmica testada se confirma** — salinidade, oxigênio e vento descrevem, nenhum prevê. §10 reordenada: persistir o modelo vira prioridade máxima, e o ERA5 sai como cancelado. |
| 26/07/2026 | **§7.1 a §7.3 criadas — onde os dados ficam salvos, e o que não fica.** §7.1 segue **um número só** (a SST de Abrolhos em 24/07/2026) do satélite até a linha gravada, com o que acontece em cada etapa da conexão. §7.2 registra que há **três lugares** e por que: PostgreSQL para a entrega 1, `dados/` para a entrega 2 (os 119 sítios do GCBD não são recifes monitorados e cadastrá-los como `LocalRecife` criaria recifes falsos no site), e `backend/dados/` que é lixo herdado e não é lido por nada. §7.3 separa **dado** de **modelo** e registra o achado: **o modelo treinado não é salvo em lugar nenhum**. Isso está correto para a validação atual — ela treina cinco modelos parciais e usa cada um só fora da própria dobra —, mas **bloqueia o site exibir qualquer previsão**. Duas pendências novas em §10. |
| 26/07/2026 | **§9 — passo 2 registrado, e a pergunta central do projeto tem resposta: não.** Salinidade e oxigênio de reanálise não preenchem a lacuna que o passo 1 abriu. Separam as classes na direção que a biologia previa, com metade da força das térmicas, sem virar previsão — segunda ocorrência do padrão. Registrada a ressalva de resolução (grade de 28 km, 20 sítios a até 33 km) como limitação séria e não omitível. §10 reordenada: o **ERA5** vira prioridade máxima, porque o vento é a única não térmica que funciona e o vento do projeto é constante inventada. |
| 26/07/2026 | **§9 — passo 1 da entrega 2 registrado.** Com branqueamento observado como alvo, a régua da NOAA acerta 10 de 10 quando dispara mas fica calada em **78 dos 88 branqueamentos brasileiros**. É a justificativa do projeto medida em vez de suposta: estresse térmico é suficiente, não necessário. §10 atualizada — 275 testes, GCBD passo 1 e exportação .docx entram em "pronto"; a prioridade máxima passa a ser o **passo 2**, agora com lacuna quantificada. |
| 25/07/2026 | Estado atualizado: importância das variáveis medida (DHW e SST respondem por mais de 95% da capacidade preditiva) e a colinearidade registrada como pendência — hoje os coeficientes não permitem afirmar direção de efeito. |
| 25/07/2026 | Documento criado como porta de entrada do projeto: o problema biológico, a cadeia MMM→HotSpot→DHW→BAA explicada com exemplo, as fontes e suas naturezas distintas, o caminho do dado, as duas entregas, o que falta e os defeitos herdados. |
