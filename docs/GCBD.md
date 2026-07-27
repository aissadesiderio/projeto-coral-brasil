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

**2. ✅ Ingerir apenas salinidade e oxigênio** do Copernicus, em janela de 90
dias antes de cada observação — **feito em 26/07/2026**: **30.212 valores
diários**, 332 pares (visita, variável), **zero falhas**. Foram 166 visitas, e
não as 197 estimadas, pela correção da Etapa 3.

A reanálise começa em **1993** e o GCBD brasileiro em **1994** — conferido nos
dois produtos: a cobertura é exata, **sem emenda** com produto de análise.

**3. ✅ O experimento:** modelo térmico-apenas contra térmico + salinidade + O₂,
prevendo **branqueamento observado**. **Feito em 26/07/2026 — a resposta é
não.** Ver abaixo.

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
2. ~~**`Windspeed` é a segunda variável mais útil**~~ do modelo interpretável
   (queda de PR-AUC +0,073, contra +0,100 do `TSA_DHW`). ~~É o primeiro sinal
   não térmico que o projeto encontra.~~

   🚨 **Desmentido em 26/07/2026.** Essa evidência vinha da coluna `Windspeed`
   do próprio GCBD, e ninguém tinha conferido se ela descreve o vento. Contra
   vento medido do ERA5, nos mesmos pontos e datas, o efeito some — e substituir
   uma pela outra deixa o modelo **pior que sem vento**. Ver
   [RESULTADOS.md](RESULTADOS.md) §20 e [ERA5.md](ERA5.md).

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

## Passo 2 — a ingestão ambiental

Executado em **26/07/2026**. Busca **salinidade e oxigênio dissolvido** nos 90
dias que precedem cada uma das 166 visitas.

### Por que 90 dias

É a escala em que o estresse térmico opera — o DHW da NOAA acumula 12 semanas.
Usar a mesma janela mantém a comparação honesta: as duas famílias de variável
enxergam o mesmo intervalo, então uma diferença de desempenho não pode ser
atribuída a uma delas ter olhado mais longe.

⚠️ **A janela termina no dia da visita e inclui esse dia.** Um único dia
posterior seria vazamento direto — o mergulhador já tinha visto o coral branco.
Há teste travando isso.

### Verificações feitas antes de baixar

**1. A reanálise cobre o período?** [GCBD.md](GCBD.md) afirmava que "a reanálise
começa em 1993", mas isso nunca tinha sido conferido para o produto de
biogeoquímica, que costuma ter cobertura diferente do físico. Conferido no
catálogo real:

| Variável | Produto | Cobertura | Cobre 1994–2010? |
|---|---|---|---|
| salinidade | `cmems_mod_glo_phy_my_0.083deg_P1D-m` | 1993-01-01 → 2026-06-23 | ✅ |
| oxigênio | `cmems_mod_glo_bgc_my_0.25deg_P1D-m` | 1993-01-01 → 2026-05-31 | ✅ |

✅ **Só a reanálise é usada.** Ao contrário da série da entrega 1, aqui **não há
emenda** com produto de análise: a reanálise sozinha cobre todo o período do
GCBD brasileiro. É uma fonte de erro a menos.

**2. 🚨 Os recifes caem em célula de terra?** Este era o risco real. **69 das
166 visitas estão a menos de 1 km da costa** (mediana: 2,3 km), e a grade do
oxigênio é 0,25° ≈ **28 km**. Um recife costeiro pode simplesmente não ter
célula de oceano em cima dele.

Medido, por raio de busca:

| Raio | ~km | Salinidade | Oxigênio |
|---|---|---|---|
| 0,15° | 17 | 118 sítios | 99 sítios |
| 0,30° | 33 | +1 → **119** | +20 → **119** |
| **sem dado** | | **0** | **0** |

**Nenhum sítio fica sem dado.** Mas 20 sítios só encontram oxigênio a até 33 km
do recife — e isso fica gravado.

### O que é gravado, e por quê

O resultado **não entra no banco**. `MedicaoAmbiental` pendura em
`LocalRecife`, que são os três recifes monitorados, com foto, slug e página
pública. Os 119 sítios do GCBD não são recifes monitorados: são pontos de
amostragem de um estudo retrospectivo. Criá-los como `LocalRecife` encheria a
tabela pública de 119 registros falsos para viabilizar um experimento.

Então a janela vira **cache em `dados/gcbd_janelas_ambientais.csv`** — não
versionado, reconstruível por um comando, com proveniência por valor. É
coerente com o passo 1, que já lê arquivo em vez do banco.

Cada linha guarda:

| Coluna | Por quê |
|---|---|
| `dataset_id` | De qual produto o valor saiu |
| **`raio_graus`** | **A que distância do recife.** Um valor colhido a 33 km não é o mesmo que um colhido em cima dele, e quem lê o resultado precisa saber qual foi |
| `n_celulas` | Quantas células de oceano entraram na média |

### Qualidade da água — acrescentada em 27/07/2026

O **mesmo arquivo** de onde vem o oxigênio publica também `chl` (clorofila),
`no3` (nitrato), `po4` (fosfato), `si` (silicato) e `nppv` — diários, 1993–2026.
Conferido no catálogo. Custo de acrescentar: **nenhuma fonte, credencial ou
código novo**, só mais nomes.

Escolhidas três, e o motivo de cada uma:

| Variável | Por quê |
|---|---|
| `chl` | Clorofila — o indicador de eutrofização mais estabelecido |
| `no3` | Nitrato — o nutriente de mecanismo mais direto |
| `si` | Silicato — marcador de **aporte continental** (água de rio) |

`po4` ficou de fora por andar junto com `no3`, e `nppv` por ser consequência
dos nutrientes e não causa.

**O `si` era o que interessava:** a salinidade deveria detectar água de rio e não
detectou. Silicato pergunta o mesmo por outro caminho.

🚨 **Resultado: não, e a hipótese do rio caiu.** Nenhuma combinação melhora a
validação por ano, e o silicato correlaciona **+0,363 com a salinidade** — o
oposto do que uma pluma de água doce produziria. Ver
[RESULTADOS.md](RESULTADOS.md) §21.

⚠️ **Estas variáveis ficam declaradas em `ml/gcbd_ambiental.py`, e não em
`conectores/copernicus.py::SERIES`.** Aquele dicionário alimenta o comando
`ingerir`, que grava em `MedicaoAmbiental`; uma variável listada lá sem nome
canônico em `ingestao/normalizacao.py` viraria uma opção que aceita o pedido e
quebra no meio da gravação. Há teste travando a separação.

### As features

Uma média e uma trajetória por variável — **quatro colunas novas** no passo 2,
mais seis se a qualidade da água entrar:

| Feature | O que responde |
|---|---|
| `salinidade_media_90d` | Como estava o ambiente no trimestre |
| `salinidade_variacao_90d` | Para onde ele ia (último menos primeiro) |
| `oxigenio_media_90d` | idem |
| `oxigenio_variacao_90d` | idem |

A distinção média×trajetória é a mesma que fez a entrega 1 funcionar
([RESULTADOS.md](RESULTADOS.md) §3). E o número é pequeno de propósito: a
entrega 1 aprendeu **duas vezes** que janelas demais sobre a mesma variável
viram a mesma coluna e quebram os coeficientes. Com 166 visitas, quatro
features novas sobre três térmicas já é o limite defensável.

⚠️ **Visita sem janela completa é descartada, nunca preenchida.** Imputar
salinidade por média inventaria exatamente a variável cujo efeito o experimento
quer medir — o defeito do `carregar_historico.py` legado
([FONTES.md](FONTES.md) §6.3).

### Como rodar

```bash
python backend\manage.py ingerir_gcbd --agua
```

Sem `--agua`, baixa só salinidade e oxigênio. Grava a cada visita concluída:
pode ser interrompido e retomado, porque o cache é consultado por (sítio, data,
variável).

```bash
python backend\manage.py treinar_gcbd --interpretavel --ambiental --importancia
```

O experimento espelho — só as não térmicas, sem nenhuma temperatura:

```bash
python backend\manage.py treinar_gcbd --so-ambiental --importancia
```

Código em `backend/ml/gcbd_ambiental.py`, testes em
`backend/ml/testes_gcbd_ambiental.py` (23).

### ✅ O que saiu — e a resposta é não

Números completos em [RESULTADOS.md](RESULTADOS.md) §15–§19.

> **Nenhuma combinação de salinidade e oxigênio superou o modelo só-térmico na
> validação por ano.** Sozinhas, as quatro features ambientais dão PR-AUC
> **0,527** contra taxa base 0,530 — acaso.

| Conjunto | PR-AUC ano |
|---|---|
| Só as 3 térmicas | **0,717** |
| \+ as 4 ambientais | 0,636 |
| Só as 4 ambientais | 0,527 *(acaso = 0,530)* |

As duas explicações alternativas foram testadas e **caíram**:

- **Não é o tamanho da janela.** Reconstruída de 7 a 90 dias a partir do mesmo
  cache: todas ficam entre 0,632 e 0,664, abaixo do modelo sem ambientais.
- **Não são identificador de sítio.** Variam com a visita (razão de desvio
  interno 0,48 a 0,87) e só acertam o sítio em 14,9% contra 3,0% de acaso.

**O achado que não é zero:** as quatro **separam as classes na direção
fisicamente esperada** — os sítios que branquearam tinham oxigênio mais baixo
e caindo (*d* = −0,38 e −0,32) e salinidade mais baixa e caindo (−0,28). O
efeito é cerca de metade do das térmicas, e **não vira previsão**. É a segunda
vez que o projeto vê exatamente esse padrão com o oxigênio, agora em base
independente ([VARIAVEIS.md](VARIAVEIS.md) §3.6).

🚨 **A explicação concorrente que estes dados não descartam** está em
[RESULTADOS.md](RESULTADOS.md) §18: a grade do oxigênio é 28 km e 20 sítios só
têm dado a até 33 km do recife. Uma pluma de água doce num recife costeiro é
exatamente o que uma célula desse tamanho calcula a média para fora. O
resultado negativo é sobre **estes produtos nesta resolução**, não sobre o
mecanismo.

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
8. 🚨 **A salinidade e o oxigênio vêm de reanálise global, não do recife.** A
   grade do oxigênio é 0,25° (~28 km) e **20 sítios só têm dado a até 33 km**.
   O resultado negativo do passo 2 é condicional a isso — ver
   [RESULTADOS.md](RESULTADOS.md) §18 e [FONTES.md](FONTES.md) §6.18. Afirmar
   "salinidade e oxigênio não explicam o branqueamento brasileiro" sem essa
   ressalva seria afirmar mais do que foi medido.

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
| 27/07/2026 | **`Windspeed` saiu do conjunto interpretável.** Passa a ser `TSA_DHW` + `TSA`, duas colunas. Custa 0,025 de PR-AUC — dentro do ruído declarado — e elimina a única entrada que exigia ressalva, já que o efeito do vento não sobrevive à troca por vento medido do ERA5. Ver [RESULTADOS.md](RESULTADOS.md) §20.1. |
| 27/07/2026 | **Qualidade da água acrescentada ao passo 2 — e a resposta é não.** O mesmo produto do oxigênio publica clorofila, nitrato e silicato; extraídos 45.318 valores, 498 pares, zero falhas, sem fonte nem código novo. **Nenhuma combinação melhora a validação por ano.** A hipótese que justificava o silicato — marcar água de rio — **caiu**: ele correlaciona +0,363 com a salinidade, o oposto do esperado para pluma de água doce. Registrado também por que essas variáveis ficam declaradas em `ml/gcbd_ambiental.py` e não no `SERIES` do conector: lá elas seriam oferecidas ao comando `ingerir` e quebrariam na normalização por falta de nome canônico. Ver [RESULTADOS.md](RESULTADOS.md) §21. |
| 26/07/2026 | 🚨 **Corrigido o achado 2 do passo 1 — o `Windspeed` não se confirma.** A afirmação de que ele era "o primeiro sinal não térmico do projeto" vinha da coluna do próprio GCBD, nunca conferida contra fonte independente. Contra vento medido do ERA5 nos mesmos pontos e datas, o efeito some, e substituir deixa o modelo pior que sem vento. Ver [RESULTADOS.md](RESULTADOS.md) §20 e [ERA5.md](ERA5.md). |
| 26/07/2026 | **Passos 2 e 3 executados — a resposta é não.** 30.212 valores diários de salinidade e oxigênio extraídos para as 166 visitas, zero falhas, só reanálise (cobertura conferida: 1993-01-01 nos dois produtos, sem emenda). **Nenhuma combinação supera o modelo só-térmico por ano**; sozinhas as ambientais ficam no acaso (0,527 contra base 0,530). Testadas e derrubadas as duas explicações alternativas: tamanho de janela (7 a 90 dias, nenhuma ajuda) e identidade de sítio (variam com a visita, e só acertam o sítio em 14,9%). O achado positivo: elas **separam as classes na direção fisicamente esperada**, com metade da força das térmicas, sem virar previsão — segunda ocorrência do mesmo padrão com o oxigênio. Acrescentada a **limitação 8**: a grade do oxigênio é 28 km e 20 sítios só têm dado a até 33 km, então o resultado negativo é sobre estes produtos nesta resolução, não sobre o mecanismo. |
| 26/07/2026 | **Passo 1 executado, com três correções ao levantamento.** (a) A unidade amostral é a **visita**: 166, não 313 — o GCBD traz uma linha por substrato, e 0 de 166 visitas divergem no alvo. (b) **`ClimSST` tem sentinela** (262,15 K = −11 °C) em 115 de 313 registros e foi removida do baseline, junto com `SSTA_Mean`, que é constante; o plano original recomendava `ClimSST`. (c) Das 33 colunas térmicas, só **8 variam com a data** — as outras 23 são climatologia constante do sítio. Resultado: a regra da NOAA tem precisão 1,000 e revocação **0,114**, com **78 dos 88 branqueamentos ocorrendo com `TSA_DHW` = 0**. O passo 2 passa a ter lacuna quantificada. A suspeita da limitação 4 (equilíbrio artificial) foi medida e **não** se confirmou. |
| 25/07/2026 | Documento criado. Levantamento de viabilidade em cinco etapas, antes de qualquer código: download e integridade, estrutura, conteúdo brasileiro, cobertura geográfica frente aos três recifes, e custo de ingestão. Conclusão: viável, mas como experimento separado — o dado brasileiro é de 1994–2010, termina em 2010, e Picãozinho fica sem cobertura. Balanceamento de 50/50 é vantagem real sobre os 8% do BAA. |
