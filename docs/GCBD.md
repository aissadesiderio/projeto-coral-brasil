# GCBD — Global Coral-Bleaching Database

Levantamento de viabilidade feito em **25/07/2026**, antes de escrever
qualquer código de integração. Registra o que a base contém, o que ela custa
integrar, e o que ela permite ou não responder.

O GCBD é a fonte da **entrega 2** do projeto: o único caminho para trocar o
alvo de *classificação de estresse térmico por satélite* (o BAA) por
**branqueamento observado em campo**. A justificativa dessa troca está em
[VARIAVEIS.md](VARIAVEIS.md) §4.4.

---

## Identificação da fonte

| | |
|---|---|
| **Nome** | Bleaching and environmental data for global coral reef sites from 1980-2020 |
| **Artigo** | van Woesik, R. & Kratochwill, C. — *Scientific Data* (2022), DOI `10.1038/s41597-022-01121-y` |
| **Dado (repositório)** | van Woesik, R.; Burkepile, D. — BCO-DMO |
| **Repositório** | BCO-DMO, dataset **773466** |
| **DOI do dado** | `10.26008/1912/bco-dmo.773466.2` |
| **Licença** | **CC-BY 4.0** |
| **Arquivo** | `global_bleaching_environmental.csv` — 16,00 MB |
| **SHA-256** | `78cc014b1e7887f26f4c44a40d4d9213…` |
| **Baixado em** | 25/07/2026 |

**Citação obrigatória — são duas, para artefatos distintos:**

| O que está sendo citado | Citação |
|---|---|
| O **artigo** que descreve a base e o método | van Woesik, R. & Kratochwill, C. (2022). *A global coral-bleaching database, 1980–2020.* Scientific Data. doi:`10.1038/s41597-022-01121-y` |
| Os **dados** baixados | van Woesik, R., Burkepile, D. (2022). *Bleaching and environmental data for global coral reef sites from 1980-2020.* BCO-DMO. doi:`10.26008/1912/bco-dmo.773466.2` |

⚠️ Ao usar os dados, **cite as duas**: o artigo pelo método, o repositório pelo
dado. Citar só uma é erro de atribuição, não economia de espaço.

---

## Etapa 1 — Download e integridade

Baixado de `datadocs.bco-dmo.org` sobre TLS verificado (bundle do `certifi`,
mesmo mecanismo do pipeline de ingestão). Conferido tamanho, contagem de
linhas e hash.

**41.362 linhas**, sendo 41.361 registros mais o cabeçalho.

O arquivo **não é versionado** — 16 MB, reconstruível pelo DOI. O caminho para
obtê-lo está registrado aqui, que é o que a reprodutibilidade exige.

---

## Etapa 2 — Estrutura

**62 colunas.** As que importam:

| Grupo | Colunas |
|---|---|
| Identificação | `Site_ID`, `Sample_ID`, `Data_Source`, `Reef_ID` |
| Geografia | `Latitude_Degrees`, `Longitude_Degrees`, `Country_Name`, `Ecoregion_Name` |
| Tempo | `Date`, `Date_Day`, `Date_Month`, `Date_Year` |
| **Alvo** | **`Percent_Bleaching`**, `Bleaching_Level` |
| Contexto do sítio | `Depth_m`, `Distance_to_Shore`, `Exposure`, `Turbidity`, `Cyclone_Frequency` |
| Térmicas próprias | `ClimSST`, `Temperature_*`, `SSTA*`, `TSA*`, `TSA_DHW*`, `Windspeed` |

🚨 **Não há salinidade nem oxigênio dissolvido.** São exatamente as duas
variáveis que diferenciam este projeto — o que significa que a base **não
responde sozinha** à pergunta da entrega 2. Ver o plano abaixo.

### As 33 colunas térmicas não são 33 variáveis

⚠️ **Acrescentado em 26/07/2026**, ao usar as colunas de verdade. Duas
descobertas mudam quais delas servem.

**1. Só 8 descrevem o dia da visita. As outras 23 descrevem o lugar.**

Medindo o desvio-padrão *dentro* de cada sítio, sobre os sítios visitados mais
de uma vez:

| Variam com a **data** (condição da visita) | Constantes no **sítio** (climatologia) |
|---|---|
| `Temperature_Kelvin`, `SSTA`, `SSTA_Frequency`, `SSTA_DHW`, `TSA`, `TSA_Frequency`, `TSA_DHW`, `Windspeed` | `Temperature_Mean/Minimum/Maximum`, todos os `*_Standard_Deviation`, `*Max`, `*Mean` — 23 colunas com desvio interno **exatamente 0** |

As constantes não são inúteis, mas respondem outra pergunta: *"este recife é
termicamente instável?"* em vez de *"fez calor antes desta visita?"*. Ficam
separadas em `CLIMATOLOGIA_DO_SITIO`, e medir a diferença mostrou que elas quase
não acrescentam ([RESULTADOS.md](RESULTADOS.md) §11.5).

**2. 🚨 `ClimSST` tem valor-sentinela — e o plano abaixo a recomendava.**

`ClimSST` vale exatamente **262,15 K em 115 dos 313 registros brasileiros
(36,7%)**. São **−11 °C** num recife tropical: não é climatologia, é **ausência
codificada como número**.

A origem fica clara na conta: 262,15 = 273,15 − 11. Alguém converteu um `-11`
de Celsius para Kelvin sem notar que `-11` era o código de "sem dado".

Um modelo que recebesse isso aprenderia que 37% dos recifes brasileiros têm
climatologia ártica. `ClimSST` foi **removida** do baseline e está em
`COLUNAS_RECUSADAS`, com teste travando a decisão.

`SSTA_Mean` também saiu: é **constante em 0,0** no recorte brasileiro inteiro.

> Este é o tipo de defeito que só aparece quando se olha o dado, e é a razão
> pela qual [FONTES.md](FONTES.md) §6 existe.

---

## Etapa 3 — O conteúdo brasileiro

| | |
|---|---|
| Registros | **384** (0,93% do global) |
| Sítios distintos | 137 |
| Período | **1994-03-15 → 2010-12-17** |
| Registros com `Percent_Bleaching` numérico | 313 |
| **Visitas** — a unidade amostral real | **166** (119 sítios) |
| **Branquearam** (> 0%) | **88 de 166 — 53,0%** |
| Ecorregião | `Brazil` (única) |

### 🚨 São 166 visitas, não 313 amostras

⚠️ **Correção de 26/07/2026.** Este documento dizia "313 amostras utilizáveis".
Está errado, e o erro inflava a amostra em **1,9×**.

O GCBD traz **uma linha por substrato amostrado** na mesma visita:

| Site_ID | Date | Substrate_Name | Percent_Cover | Percent_Bleaching |
|---|---|---|---|---|
| 1653 | 2005-04-05 | Hard Coral | 23,12 | 2,0 |
| 1653 | 2005-04-05 | Nutrient Indicator Algae | 10 | 2,0 |

São duas linhas, mas **uma observação de branqueamento**. Medido no recorte
brasileiro inteiro:

- **0 de 166 visitas** têm mais de um valor de `Percent_Bleaching`;
- **0 visitas** divergem em qualquer variável térmica.

Tratar linha como amostra não acrescentaria informação nenhuma, e poria cópias
exatas da mesma visita nos dois lados de qualquer divisão de validação — o que
inventaria desempenho. A agregação está em `ml/gcbd.py::agregar_por_visita`,
travada por teste.

Distribuição por ano — concentrada em 2002–2010:

| Ano | n | | Ano | n |
|---|---|---|---|---|
| 1994 | 1 | | 2005 | 30 |
| 1998 | 5 | | 2006 | 24 |
| 2000 | 1 | | 2007 | 66 |
| 2001 | 2 | | 2008 | 46 |
| 2002 | 51 | | 2009 | 36 |
| 2003 | 44 | | 2010 | 65 |
| 2004 | 13 | | | |

### 🚨 O dado brasileiro termina em 2010

A base global vai até 2020, **mas o Brasil para em 2010-12-17**. A
sobreposição com a série ambiental já ingerida (2020-01-01 em diante) é
**exatamente zero**.

Isso não inviabiliza — o CRW cobre desde **1985-04-01** e a reanálise do
Copernicus desde **1993** —, mas significa que a entrega 2 exige ingestão
**nova**, em período e locais diferentes. Não é extensão do que existe.

### ✅ O balanceamento é a boa notícia — e ele se confirmou

**53,0% de positivos** (88 de 166 visitas), contra os **8%** do BAA na entrega 1.

Isso muda a natureza do problema: some a necessidade de `class_weight`,
a acurácia deixa de ser enganosa por classe majoritária, e a métrica volta a
ser lida de forma direta. Ver [METODOLOGIA.md](METODOLOGIA.md) §4 para o que
isso resolve.

**A limitação 4 deste documento suspeitava que o equilíbrio fosse artefato do
limiar** — "0,1% de colônias branqueadas não é o mesmo fenômeno que 85%".
Medido em 26/07/2026: **não é artefato.** Dos 88 positivos, apenas **2 têm
menos de 0,1%**, e a mediana deles é **5%**. O quartil superior é 12,5%.

---

## Etapa 4 — Cobertura geográfica frente aos três recifes

Distância de cada registro brasileiro ao recife monitorado mais próximo,
calculada por *haversine*:

| Nosso recife | Sítios GCBD | Registros | Distância mediana | Mínima |
|---|---|---|---|---|
| **Abrolhos (BA)** | 41 | 117 | **8,4 km** | **1,3 km** |
| Porto de Galinhas (PE) | 39 | 110 | 43,8 km | 27,4 km |
| **Picãozinho (PB)** | 57 | 157 | **377,5 km** | 197,9 km |

Sítios dentro de um raio dos nossos:

| Raio | Sítios | Registros |
|---|---|---|
| 25 km | 15 | 60 |
| 50 km | 42 | 135 |
| 100 km | 57 | 180 |
| 200 km | 84 | 249 |

### 🚨 Picãozinho fica de fora

Os sítios "mais próximos" de Picãozinho estão a **200 a 400 km**. Para um
produto de grade de 5 km, isso é outro sistema recifal — não é o mesmo lugar
com outro nome.

**Abrolhos, ao contrário, é o caso ideal:** 41 sítios do GCBD, o mais próximo a
1,3 km, praticamente sobrepostos ao polígono monitorado.

Consequência de desenho: a entrega 2 **não é "os mesmos três recifes com outro
alvo"**. É um conjunto de 137 sítios brasileiros espalhados de −18,2° a −3,5°,
dos quais os nossos recifes são apenas parte.

Isso é, na verdade, **melhor para o experimento**: 119 sítios espalhados por
15 graus de latitude dão muito mais independência amostral que 3 recifes
colados que reagem ao mesmo forçante ([VARIAVEIS.md](VARIAVEIS.md) §7.2).

---

## Etapa 5 — Custo de ingestão

O erro seria ingerir série contínua para todos os sítios:

| Abordagem | Site-dias | Medições NOAA (×6) |
|---|---|---|
| Série contínua, 137 sítios × 16,8 anos | 838.577 | **5.031.462** |
| Janela de 30 dias antes de cada observação | 5.910 | 35.460 |
| **Janela de 90 dias antes de cada observação** | 17.730 | **106.380** |
| Janela de 180 dias | 35.460 | 212.760 |

> A série contínua seria **117× todo o backfill atual do projeto**.

**A chave é que não são 384 tarefas de ingestão, e sim 197.** Os 384 registros
são múltiplas linhas de substrato da mesma visita: há **197 combinações
distintas de (sítio, data)**, em 147 datas.

E **não é preciso série contínua** — o modelo precisa apenas da janela que
*precede* cada observação. Isso reduz o problema em **47 vezes**.

A janela de 90 dias é o ponto de partida sugerido: cobre o acumulador de 12
semanas do DHW, que é a escala em que o estresse térmico opera.

---

## Plano recomendado

O caminho mínimo que responde à pergunta científica, em ordem:

**1. ✅ Usar as térmicas do próprio GCBD como baseline.** ~~`TSA_DHW`,
`ClimSST`, `SSTA`~~ — **feito em 26/07/2026**, com correção: `ClimSST` saiu por
ter sentinela (ver Etapa 2). Foram usadas as **8 térmicas do dia**. **Zero
ingestão**, como previsto.

**2. Ingerir apenas salinidade e oxigênio** do Copernicus, em janela de 90 dias
antes de cada uma das 197 observações: **35.460 medições**. Menos do que o
backfill do Copernicus já feito.

A reanálise começa em **1993** e o GCBD brasileiro em **1994** — a cobertura é
exata, sem emenda com produto de análise.

**3. O experimento:** modelo térmico-apenas contra térmico + salinidade + O₂,
prevendo **branqueamento observado**. É a pergunta da entrega 2, com rótulo
real e classes balanceadas.

### Por que essa ordem

O passo 1 é gratuito e já diz se o sinal térmico sozinho explica o
branqueamento observado nos sítios brasileiros. Se explicar quase tudo — como
aconteceu na entrega 1 ([RESULTADOS.md](RESULTADOS.md) §8) —, o passo 2 fica
mais informativo, porque a comparação passa a ser contra um baseline forte e
medido.

---

## ✅ Passo 1 — o que saiu

Rodado em **26/07/2026**. Os números completos estão em
[RESULTADOS.md](RESULTADOS.md) §11–§14; aqui fica só o que decide o passo 2.

> **A regra publicada da NOAA (`TSA_DHW ≥ 4`) tem precisão 1,000 e revocação
> 0,114. Dos 88 branqueamentos observados no Brasil, ela pega 10 — e 78
> aconteceram com `TSA_DHW = 0`.**

| | |
|---|---|
| Visitas | 166 (119 sítios) |
| Positivos | 88 (53,0%) |
| `TSA_DHW = 0` em | **87,3% das visitas** |
| Regra NOAA | P = 1,000 · R = 0,114 · F1 = 0,204 |
| Modelo térmico, testado em **ano** não visto | PR-AUC 0,614 a 0,683 (acaso = 0,530) |
| Modelo térmico, testado em **sítio** não visto | PR-AUC 0,803 a 0,867 |

**A resposta do passo 1 é: o sinal térmico sozinho não explica.** Ele é
*suficiente* — quando dispara, acerta — mas está longe de ser *necessário*.

Duas consequências para o passo 2:

1. **Há lacuna quantificada a preencher.** Não é mais "seria interessante testar
   salinidade e oxigênio": são **78 eventos observados sem estresse térmico
   acumulado** esperando explicação.
2. **`Windspeed` é a segunda variável mais útil** do modelo interpretável
   (queda de PR-AUC +0,073, contra +0,100 do `TSA_DHW`). É o primeiro sinal
   não térmico que o projeto encontra — e vento se liga a mistura da coluna
   d'água, que é justamente o mecanismo pelo qual salinidade e oxigênio
   importariam.

⚠️ **O que o passo 1 não disse:** que salinidade e oxigênio *são* a explicação.
Eles não foram medidos. O que se mostrou é que **há espaço**, não quem o ocupa.

### Como rodar

```bash
python backend\manage.py treinar_gcbd --importancia
```

```bash
python backend\manage.py treinar_gcbd --interpretavel --importancia
```

Código em `backend/ml/gcbd.py`, testes em `backend/ml/testes_gcbd.py` (26).

---

## Limitações a declarar no trabalho

1. **O dado brasileiro termina em 2010.** Nada do evento global de 2024, nem
   do de 2020, aparece com rótulo observado.
2. **Picãozinho não tem cobertura** (sítio mais próximo a 198 km).
3. **166 visitas utilizáveis** — ~~313 amostras~~, corrigido em 26/07/2026.
   Pequeno em termos absolutos, ainda que bem balanceado e espacialmente
   espalhado. Diferença de PR-AUC abaixo de ~0,05 entre versões é ruído.
4. **`Percent_Bleaching` é percentual, não presença/ausência.** Binarizar em
   "> 0%" é uma escolha, e o limiar está declarado em
   `ml/gcbd.py::LIMIAR_BRANQUEAMENTO`. A preocupação original — "0,1% não é o
   mesmo fenômeno que 85%" — **foi medida e não se confirmou**: só 2 dos 88
   positivos têm menos de 0,1%. Mas o limiar muda muito o resultado: em > 10%,
   a PR-AUC por ano cai de 0,717 para 0,398 ([RESULTADOS.md](RESULTADOS.md)
   §11.6).
5. **A base não traz salinidade nem oxigênio**, então a comparação depende de
   ingestão nossa, com todas as diferenças de produto e de resolução que isso
   implica.
6. **`ClimSST` e `SSTA_Mean` são inutilizáveis** no recorte brasileiro — ver
   Etapa 2. Qualquer trabalho que use este arquivo precisa checar sentinelas
   antes de treinar.
7. **A versão reduzida de features tem viés de seleção.** Ela foi escolhida
   olhando a mesma validação que a avalia; com 166 visitas não sobra conjunto
   para confirmá-la. Ver [RESULTADOS.md](RESULTADOS.md) §12.3.

---

## Reprodução

```bash
python -c "import urllib.request; urllib.request.urlretrieve('https://datadocs.bco-dmo.org/dataset/773466/file/B11vA82u7y2Owp/global_bleaching_environmental.csv', 'dados/global_bleaching_environmental.csv')"
```

O arquivo **não é versionado** (`dados/*.csv` está no `.gitignore`). Confira o
SHA-256 acima após baixar.

O código procura nesta ordem: o argumento `--csv`, a variável de ambiente
`GCBD_CSV`, e por fim `dados/global_bleaching_environmental.csv`.

---

## Histórico

| Data | Alteração |
|---|---|
| 26/07/2026 | **Passo 1 executado, com três correções ao levantamento.** (a) A unidade amostral é a **visita**: 166, não 313 — o GCBD traz uma linha por substrato, e 0 de 166 visitas divergem no alvo. (b) **`ClimSST` tem sentinela** (262,15 K = −11 °C) em 115 de 313 registros e foi removida do baseline, junto com `SSTA_Mean`, que é constante; o plano original recomendava `ClimSST`. (c) Das 33 colunas térmicas, só **8 variam com a data** — as outras 23 são climatologia constante do sítio. Resultado: a regra da NOAA tem precisão 1,000 e revocação **0,114**, com **78 dos 88 branqueamentos ocorrendo com `TSA_DHW` = 0**. O passo 2 passa a ter lacuna quantificada. A suspeita da limitação 4 (equilíbrio artificial) foi medida e **não** se confirmou. |
| 25/07/2026 | Documento criado. Levantamento de viabilidade em cinco etapas, antes de qualquer código: download e integridade, estrutura, conteúdo brasileiro, cobertura geográfica frente aos três recifes, e custo de ingestão. Conclusão: viável, mas como experimento separado — o dado brasileiro é de 1994–2010, termina em 2010, e Picãozinho fica sem cobertura. Balanceamento de 50/50 é vantagem real sobre os 8% do BAA. |
