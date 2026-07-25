# Seleção de Variáveis — Modelo de Branqueamento

> **Status:** decisão de *features* e de *target* fechadas (ver §4).
> **Última revisão:** 25/07/2026
> **Relacionados:** [FONTES.md](FONTES.md) · [contrato_canonico_variaveis.md](../backend/docs/contrato_canonico_variaveis.md)

Este documento registra **por que cada variável entra ou fica de fora** do modelo de predição de branqueamento. Serve para defender as escolhas em banca e para impedir que uma variável seja reintroduzida sem que o motivo da exclusão seja reexaminado.

---

## 1. Resumo da decisão

| Papel | Variáveis |
|---|---|
| **Features baseline** | `CRW_SST`, `CRW_DHW`, `salinidade`, `O₂` — ⚠️ `KD490` **sob revisão**, ver §3.5 |
| **Opcionais** (após baseline) | `CRW_HOTSPOT`, `CRW_SSTANOMALY` |
| **Target — entrega 1** | `CRW_BAA` **com horizonte de N dias** (previsão de estresse térmico) |
| **Target — entrega 2** | Branqueamento observado (Global Coral-Bleaching Database) |
| **Excluídas** | `temperatura`/`SST anomaly` (Copernicus), `pH`, `CO₂`, `alcalinidade`, `nitrato`, `fosfato`, `ferro dissolvido` |

---

## 2. Os quatro princípios que guiaram a seleção

**2.1 Escala temporal compatível com o fenômeno.** Branqueamento térmico é um evento agudo: instala-se em semanas. Uma variável só discrimina esse evento se ela própria variar em escala de dias a semanas. Variáveis que se movem em décadas (pH, CO₂) ou em meses com forte componente espacial (nitrato, fosfato) entram no modelo como quase-constantes — custam parâmetros e não separam caso de não-caso.

**2.2 Efeito mensurável acima de causa remota.** Quando existe uma cadeia causal, prefere-se medir o elo final. Nitrato alto → bloom de fitoplâncton → consumo de oxigênio → hipóxia → coral estressado. Se o O₂ está sendo medido, o nitrato acrescenta ruído da cadeia inteira sem informação nova sobre o desfecho.

**2.3 Fonte especializada acima de fonte genérica.** Quando duas fontes medem a mesma grandeza, usa-se a produzida especificamente para recifes. O NOAA Coral Reef Watch calibra SST e climatologia para o contexto coralino; o Copernicus é um modelo oceânico global.

**2.4 Ausência de vazamento (*data leakage*).** Nenhuma feature pode ser derivada do target. Isso vale nos dois sentidos — e é justamente onde a decisão sobre o `CRW_BAA` precisa ser reaberta (§4).

---

## 3. Variáveis usadas

### 3.1 `CRW_SST` — Temperatura da superfície do mar
- **Fonte:** NOAA Coral Reef Watch 5 km v3.1 (CoralTemp) · arquivo `dhw.csv`
- **Escala:** diária
- **Mecanismo:** temperatura acima do limiar térmico rompe a simbiose entre o coral e as zooxantelas. O aparato fotossintético da alga passa a produzir espécies reativas de oxigênio, e o coral expulsa o simbionte — perdendo cor e sua principal fonte de energia.
- **Por que esta e não outra:** é a base de toda a cadeia térmica. HotSpot, DHW e BAA derivam dela. O CoralTemp é o produto calibrado para recifes.
- **Situação no projeto:** disponível, 2020–2025, no acervo local.

### 3.2 `CRW_DHW` — Degree Heating Week
- **Fonte:** NOAA Coral Reef Watch 5 km v3.1 · arquivo `dhw.csv`
- **Escala:** diária, com janela acumulada de 12 semanas
- **Mecanismo:** o dano ao coral é cumulativo, não instantâneo. O DHW soma os HotSpots de pelo menos 1 °C acima do limiar de branqueamento ao longo das 12 semanas anteriores. Um DHW equivale a uma semana a 1 °C acima do limiar, ou meia semana a 2 °C acima.
- **Por que é a feature mais forte:** é a métrica com melhor sustentação na literatura para prever branqueamento. A partir de 4 °C·semana espera-se branqueamento significativo; a partir de 8, branqueamento severo e mortalidade.
- **Situação no projeto:** disponível. ⚠️ O `carregar_historico.py` calcula um DHW próprio, com limiar fixo de 27 °C e somando todos os HotSpots positivos — fora da metodologia NOAA, que usa a MMM por pixel e só acumula HotSpots ≥ 1 °C. Usar a coluna `CRW_DHW` oficial resolve isso.

### 3.3 `salinidade` — Salinidade prática
- **Fonte:** Copernicus GLOBAL_ANALYSISFORECAST_PHY_001_024, variável `so` · arquivo `salinidade.csv`
- **Escala:** 6 horas
- **Mecanismo:** corais são osmoconformadores — não regulam ativamente a concentração salina interna. Desvios bruscos, para baixo ou para cima, provocam estresse osmótico que se soma ao térmico. Na costa brasileira o vetor típico é a pluma de rios e chuvas intensas de verão, que coincidem justamente com a estação de maior temperatura.
- **Por que entra:** é o único estressor do conjunto **independente da cadeia térmica**. Todo o resto correlaciona com temperatura de alguma forma; a salinidade traz um eixo de variação novo.
- **Situação no projeto:** disponível, 2022–2025.

### 3.4 `O₂` — Oxigênio dissolvido
- **Fonte:** Copernicus GLOBAL_MULTIYEAR_BGC_001_029 (reanálise), variável `o2` · arquivo `oxigenio.csv`
- **Escala:** diária
- **Mecanismo:** água mais quente dissolve menos oxigênio, e ao mesmo tempo o calor eleva a demanda metabólica do coral. As duas curvas andam em direções opostas. A hipóxia reduz o limiar de temperatura em que o branqueamento se instala — ou seja, o mesmo DHW causa mais dano em água pobre em oxigênio.
- **Por que entra:** é um **amplificador**, não um estressor paralelo. Permite que o modelo aprenda interação em vez de efeito aditivo, e captura o elo final da cadeia de eutrofização sem precisar dos nutrientes.
- **Situação no projeto:** disponível, 1993–2025. ⚠️ Produto de reanálise, não de previsão — não misturar com séries `*_recente` sem registrar a diferença.

### 3.5 `KD490` — Coeficiente de atenuação da luz
- **Fonte:** Copernicus GLOBAL_ANALYSISFORECAST_BGC_001_028, variável `kd` · arquivo `turbidez.csv`
- **Escala:** diária
- **Mecanismo:** luz e calor agem em sinergia. Sob estresse térmico, o excesso de radiação fotossinteticamente ativa sobrecarrega o fotossistema II das zooxantelas e acelera a produção de espécies reativas de oxigênio. O efeito é bidirecional: turbidez alta **protege** por sombreamento, turbidez baixa em água quente **agrava**.
- **Papel pretendido:** compor a irradiância que chega ao coral, via Beer-Lambert: `PAR_fundo = PAR_superfície × e^(−Kd · z)`.
- **Situação no projeto:** 🚨 **o papel pretendido está bloqueado.** O projeto não tem PAR de superfície utilizável — `par.csv` tem valores mas coordenadas irrecuperáveis, e `par_recente.csv` contém `PAR_error`, o campo de incerteza. Ver [FONTES.md §6.13](FONTES.md). Enquanto o PAR não for rebaixado (NOAA ERDDAP ou NASA OceanColor), o KD490 entra apenas como turbidez — o que ainda tem valor, mas não é o que a justificativa previa.
- **Bug relacionado:** a profundidade `z` está fixa em 7,5 m para todos os locais. O campo `profundidade_media_m` já existe em `LocalRecife`, mas só Abrolhos está preenchido (10,0 m).
- 🚨 **Segundo bloqueio, medido em 25/07/2026 no catálogo real do CMEMS:** o `kd` existe **apenas de 2023-11-15 em diante**, e **não há reanálise** dele. Como a série do NOAA já cobre 2020–2026, exigir KD490 no baseline cortaria o conjunto de treino de 6,5 para **2,7 anos** e eliminaria o evento de branqueamento brasileiro de 2020 — um dos dois picos da série.

  **Recomendação: tirar o KD490 do baseline.** O custo é alto e o benefício está duplamente reduzido — o papel previsto (`PAR_fundo`) já está bloqueado por falta de PAR, então ele entraria só como turbidez. Reavaliar depois como *experimento no subperíodo* 2023-11 → presente, comparando um modelo com e sem KD490 na mesma janela. Se agregar, aí sim vale discutir o custo da série curta.

---

## 4. Target — decisão tomada (caminho C)

> **Decidido em 25/07/2026: caminho C — as duas entregas, em sequência.**
>
> **Entrega 1 (imediata):** prever o `CRW_BAA` **com horizonte de N dias**, a partir das condições de hoje. Usa os dados já em mãos, destrava o painel de risco e não é circular, porque o DHW futuro não é conhecido no presente.
> **Nome honesto do produto:** *previsão de estresse térmico* — não "previsão de branqueamento".
>
> **Entrega 2 (contribuição científica):** target = branqueamento observado, via Global Coral-Bleaching Database. É o que sustenta a seção de resultados do TCC e permite responder se salinidade, O₂ e turbidez acrescentam sinal além do DHW.
>
> As cinco features baseline valem nas duas entregas.

**Regras que a entrega 1 impõe:**

1. `CRW_HOTSPOT` fica **fora** das features — junto com o DHW determina o BAA exatamente.
2. As features são medidas em `t`; o target é o BAA em `t + N`. Nenhuma janela pode conter informação posterior a `t`.
3. A validação é **temporal** (*leave-year-out*), nunca aleatória.
4. O baseline a bater é a **persistência**: "o BAA de daqui a N dias é igual ao de hoje". Um modelo que não supera persistência não se justifica.
5. `N` é um parâmetro do experimento, não uma constante escondida no código. Valores a testar: 7, 14, 30 dias.

### 4.1 O que estava definido antes

`CRW_BAA` (Bleaching Alert Area) como única variável resposta, **nunca como feature**. O raciocínio original: o BAA deriva de SST e DHW, então usá-lo como entrada seria o modelo colar na prova.

**Esse raciocínio está correto.** O problema é que a mesma constatação, levada um passo adiante, também compromete o BAA como *target* — quando SST e DHW são as features.

### 4.2 A medição

O BAA é definido pela NOAA como função de HotSpot e DHW. Testando isso diretamente no `dhw.csv` do projeto (1.024.100 linhas, Abrolhos, 2020–2025):

| Verificação | Resultado |
|---|---|
| Combinações distintas de (`HOTSPOT`, `DHW`) | 178.759 |
| Combinações que mapeiam para **mais de um** valor de BAA | **0** |
| Árvore de decisão, profundidade 3, features = só `SST` + `DHW` | **93,6%** de acurácia |
| Árvore de decisão, profundidade 10, features = só `SST` + `DHW` | **95,7%** de acurácia |

Distribuição do target: 743.195 registros em BAA 0; 200.056 em 1; 43.514 em 2; 21.536 em 3; 15.799 em 4.

### 4.3 O que isso significa

Treinar `{SST, DHW, salinidade, O₂, KD490} → BAA` produz um modelo que atinge ~96% de acurácia **usando apenas SST e DHW**. Salinidade, O₂ e KD490 receberiam importância próxima de zero — não porque sejam biologicamente irrelevantes, mas porque não há nada a explicar: o target já é uma função fechada das outras duas features.

Estruturalmente é o mesmo defeito do `calcular_risco()` em `treinar_modelo.py`, que o roadmap identificou: **o modelo aprende uma fórmula, não o fenômeno.** A diferença é que a fórmula passa a ser a da NOAA em vez de uma escrita à mão — mais respeitável, igualmente circular. Uma acurácia de 96% numa banca convida à pergunta "o que exatamente o seu modelo aprendeu que a tabela de limiares da NOAA já não dizia?".

### 4.4 Três caminhos

**A — Branqueamento observado como target.** Usar o *Global Coral-Bleaching Database* (van Woesik & Kratochwill 2022; 34.846 registros, 1980–2020, CC-BY, BCO-DMO 773466). O target passa a ser presença/ausência observada em campo. Todas as cinco features viram legítimas, e "salinidade acrescenta sinal além do DHW?" vira pergunta científica com resposta real.
*Custo:* juntar registros de sítio a séries ambientais; cobertura brasileira mais rala.

**B — Previsão de BAA com horizonte.** Manter o BAA, mas mudar a pergunta: em vez de "qual o BAA de hoje dadas as condições de hoje" (circular), prever **o BAA daqui a N dias a partir das condições de hoje**. Não é circular, porque o DHW futuro não é conhecido no presente — e aí salinidade, O₂ e turbidez podem genuinamente antecipar a trajetória térmica.
*Custo:* nenhum dado novo. Exige rigor na montagem das janelas para não vazar futuro. **Muda o nome honesto do produto:** é previsão de estresse térmico, não de branqueamento.

**C — Híbrido.** B como entrega imediata (funciona com os dados em mãos e destrava o painel), A como contribuição científica do TCC.

**Recomendação: C.** O caminho B entrega um painel defensável em semanas; o A é o que sustenta a seção de resultados do trabalho. E a seleção de features desta decisão **vale integralmente nos três caminhos** — nada do trabalho de seleção se perde.

### 4.5 A agregação do target (corrigida em 25/07/2026)

#### O que estava acontecendo

Abrolhos não é um ponto no mapa. Quando o conector pede dados à NOAA, ele recebe uma **grade de ~121 quadradinhos** (pixels de 5 km) cobrindo a área do recife. Cada quadradinho tem seu próprio nível de alerta, de 0 a 4:

| Nível | Significado |
|---|---|
| 0 | sem estresse |
| 1 | vigilância |
| 2 | aviso |
| 3 | **Alerta Nível 1** — branqueamento esperado |
| 4 | **Alerta Nível 2** — mortalidade esperada |

Mas o banco guarda **um número por dia**, não 121. Então é preciso resumir os 121 num só. O código estava tirando a **média** — e é aí que está o erro.

#### Por que a média está errada

Um recife imaginário de 10 quadradinhos, num dia ruim:

| Quadradinhos | Nível |
|---|---|
| 6 deles | 3 — Alerta Nível 1 |
| 4 deles | 4 — Alerta Nível 2 |

Média = (6×3 + 4×4) ÷ 10 = **3,4** → arredondado para **3**.

O banco grava "Alerta Nível 1". Mas **40% do recife estava em Alerta Nível 2**, o nível em que corais morrem e não apenas branqueiam. Essa informação desapareceu.

O problema de fundo é que esses números **não são quantidades, são rótulos ordenados**. Média de rótulo não devolve rótulo — é como tirar a média de "fundamental, médio, superior" e obter 2,4. O valor 3,4 não corresponde a nenhum estado que a NOAA define.

O caso real, medido em Abrolhos em **17/05/2024**: 70 pixels em nível 3, 45 em nível 4, 6 em nível 2. Média 3,32 → gravado **3**. Trinta e sete por cento da área estava em Alerta Nível 2.

#### A correção

**1. O BAA passa a ser o máximo, não a média.** No exemplo acima, grava 4. A pergunta que um sistema de alerta responde não é "como está o pedaço médio do recife", e sim "qual a pior situação dentro dele". Os sumários regionais da própria NOAA reportam o nível máximo da área.

*Por que não a moda:* ela daria 3 em 17/05/2024 — o mesmo valor errado que a média, porque os 70 pixels em nível 3 são mais numerosos que os 45 em nível 4. Moda responde "qual o estado típico"; não é a pergunta.

**2. Nova variável `baa_area_alerta`**, que guarda **quanto** do recife está em alerta — 0,40 no exemplo, 115/121 = 0,950 no caso real. Ela existe porque o máximo sozinho tem um defeito simétrico: daria 4 tanto para "1 quadradinho em alerta" quanto para "os 121 em alerta". São situações muito diferentes.

Juntas, as duas respondem a perguntas complementares: o máximo diz **o quão grave**, a fração diz **o quanto do recife**.

A fração conta apenas pixels com valor válido. Dividir pelo total da grade misturaria "sem estresse" com "sem dado", e diluiria o alerta justamente nos dias de pior cobertura — os que mais importam.

#### O que isso muda para o experimento

1. **A distribuição do alvo muda** — e mudou de fato. Reingerido em 25/07/2026, o Alerta Nível 2 passou de 160 para **369** registros e o Alerta Nível 1 de 147 para 229. As classes altas deixam de ser raras por artefato de agregação. Qualquer balanceamento de classe calibrado na distribuição antiga precisa ser refeito.
2. **`baa_area_alerta` é uma segunda variável resposta candidata** — contínua em [0, 1]. Prever *extensão* é pergunta diferente de prever *severidade*, e possivelmente mais útil para manejo. Não entra na entrega 1; fica registrada para não se perder.
3. **A medição de circularidade da §4.2 não é afetada.** Ela foi feita no dado por pixel, onde a relação BAA = f(HotSpot, DHW) vale exatamente. O defeito era da agregação, não da relação.

⚠️ **`baa_area_alerta` não pode ser feature de um modelo que prevê `baa`.** As duas saem da mesma grade, no mesmo instante: saber que 95% do recife está em alerta é praticamente saber o alerta máximo. É a mesma armadilha do `CRW_HOTSPOT` (§4, regra 1) — o modelo não estaria prevendo, estaria lendo a resposta.

Medições, evidência e o registro do defeito em [FONTES.md](FONTES.md) §6.16. A regra geral — variável ordinal precisa declarar sua agregação — está no [contrato canônico](../backend/docs/contrato_canonico_variaveis.md), regra 5.

---

## 5. Variáveis opcionais

Entram somente se, após o baseline, mostrarem sinal independente.

### 5.1 `CRW_HOTSPOT`
Anomalia térmica positiva em relação ao limiar de branqueamento. É o elo intermediário da cadeia `SST → HOTSPOT → DHW → BAA`, e o DHW já absorve boa parte do seu sinal.
⚠️ **Se o target for BAA, o HOTSPOT não pode entrar como feature em hipótese alguma** — junto com o DHW ele determina o BAA exatamente, levando a acurácia a 100% e a interpretabilidade a zero.

### 5.2 `CRW_SSTANOMALY`
Desvio da SST em relação à climatologia. Mais útil para detectar aquecimento fora de estação, e mais relevante em arquiteturas sequenciais (LSTM) que em árvores. Redundante com HotSpot na maior parte do tempo.

---

## 6. Variáveis excluídas

### 6.1 Redundância direta

| Variável | Duplica | Detalhe |
|---|---|---|
| `temperatura` (Copernicus `thetao`) | `CRW_SST` | Mesma grandeza. O CRW é especializado em recifes; o `thetao` local ainda foi extraído a 13,47 m de profundidade, não em superfície. |
| `SST anomaly` (Copernicus) | `CRW_SSTANOMALY` | Mesma fórmula sobre climatologias diferentes; correlação acima de 0,92. Manter as duas só infla a dimensionalidade. |

### 6.2 Escala temporal incompatível — sistema carbônico

`pH`, `CO₂` e `alcalinidade` formam um sistema interdependente: conhecidos dois dos três mais a temperatura, o terceiro é calculável. Incluí-los juntos cria colinearidade tripla.

Mais decisivo é a escala: a acidificação oceânica move o pH em cerca de 0,2 unidade ao longo de dois séculos. O mecanismo é real e grave — afeta a calcificação e a recuperação pós-evento — mas é **crônico**. Num recorte de dias a semanas, o pH é praticamente uma constante e não separa evento de não-evento.

> **Nota:** o `ph.csv` do projeto contém, na verdade, `talk` (alcalinidade). O pH real está em outro arquivo. Ver [FONTES.md §6.3](FONTES.md) — é um bug ativo em `carregar_historico.py`, independente desta decisão de modelagem.

### 6.3 Mecanismo indireto — eutrofização crônica

`nitrato` e `fosfato` atuam por uma cadeia longa: enriquecimento → bloom → sombreamento e consumo de O₂ → fragilização do coral. A escala é de meses, e a variação espacial supera a temporal — num único ponto, quase não se movem.

Aplica-se o princípio 2.2: o O₂ mede o elo final dessa cadeia.

> **Ressalva honesta para a banca:** existe literatura ligando enriquecimento de nitrogênio à **redução do limiar térmico** de branqueamento, por um caminho fisiológico direto e não apenas pelo bloom. A exclusão aqui se defende pela escala temporal e pela cobertura do O₂ — não pela inexistência do mecanismo. Se algum avaliador levantar o ponto, a resposta correta é essa, não "nitrato não afeta coral".

### 6.4 Sem mecanismo estabelecido para corais

`ferro dissolvido` é micronutriente limitante para fitoplâncton em oceano aberto, sobretudo em regiões HNLC. Não há via estabelecida de efeito direto sobre a simbiose coral–zooxantela, e os efeitos indiretos que teria já estão cobertos por KD490 e O₂.

---

## 7. Bloqueios abertos

| # | Bloqueio | Impacto |
|---|---|---|
| 1 | ~~Target `CRW_BAA` circular~~ | ✅ **Resolvido** pelo caminho C: horizonte de N dias na entrega 1, branqueamento observado na entrega 2 (§4) |
| 2 | Sem PAR de superfície utilizável | `PAR_fundo` não é calculável; KD490 fica reduzido a turbidez |
| 3 | `profundidade_media_m` só preenchida para Abrolhos | Beer-Lambert usaria 7,5 m fixo para os demais locais |
| 4 | ~~`carregar_historico.py` lê `talk` como `ph`~~ | ✅ **Neutralizado no novo pipeline**: `normalizacao.resolver_variavel('talk')` levanta `ColunaRecusada`, com teste. O script antigo segue com o bug até ser aposentado. |
| 5 | ~~DHW recalculado fora da norma NOAA~~ | ✅ **Resolvido no novo pipeline**: o conector lê a coluna `CRW_DHW` oficial, sem recalcular. |
| 6 | **6 datas ausentes na série do CRW** | Janelas e defasagens que as atravessem ficam mais curtas do que declaram — ver §7.1 |
| 7 | ~~Target agregado por média espacial~~ | ✅ **Resolvido e reingerido** em 25/07/2026: BAA agregado por máximo, com `baa_area_alerta` ao lado (§4.5). Banco reconstruído — 43.038 medições, Alerta Nível 2 de 160 para 369 registros. |

### 7.1 Lacunas na série do CRW (medido em 25/07/2026)

A série ingerida (2020-01-01 a 2026-07-23, três locais) tem **6 datas ausentes no produto**, iguais nos três locais e confirmadas em dois espelhos independentes: `2024-01-30`, `2024-07-04`, `2024-07-05`, `2024-07-06`, `2024-07-25`, `2026-04-25`.

São 99,75% de cobertura, mas **três delas são consecutivas** (04–06/07/2024). Isso importa para toda feature construída sobre janela ou defasagem: uma média móvel de 30 dias que atravesse esse trecho é média de 27. A decisão — interpolar, encurtar a janela ou descartar a amostra — precisa ser **explícita no código do modelo** e registrada aqui quando for tomada. O risco não é a perda de 0,25% do dado; é uma feature cujo nome diz uma coisa e cujo conteúdo diz outra.

Detalhes e a evidência de que a lacuna é do produto, não do pipeline, em [FONTES.md](FONTES.md) §1.1.

---

## 8. Como revisar esta decisão

Antes de adicionar ou remover qualquer variável:

1. Verificar em qual **escala temporal** ela varia no ponto de interesse — não em teoria, medindo na série.
2. Checar se ela **duplica** algo já presente (correlação e, principalmente, relação analítica).
3. Confirmar que **não deriva do target**, nem o target deriva dela.
4. Registrar o **mecanismo biológico** que justifica a entrada, com referência.
5. Atualizar este documento, o [contrato canônico](../backend/docs/contrato_canonico_variaveis.md) e o [FONTES.md](FONTES.md) no mesmo commit.

---

## 9. Histórico

| Data | Alteração |
|---|---|
| 25/07/2026 | Documento criado a partir da sessão de seleção de variáveis. Registradas as 5 features baseline, 2 opcionais e 7 exclusões. Acrescentadas duas constatações verificadas em dados: a circularidade do `CRW_BAA` como target (§4.2) e a indisponibilidade de PAR de superfície (§3.5). |
| 25/07/2026 | **Agregação do target corrigida (§4.5).** O BAA é categoria ordinal e estava sendo agregado dos ~121 pixels por média, o que subestimava o alerta — Alerta Nível 1 registrado num dia com 37% da área em Alerta Nível 2. Passa a ser agregado por máximo. Nova variável `baa_area_alerta` (fração do recife em Alerta Nível 1 ou acima) fica registrada como segunda resposta candidata, e **proibida como feature** de um modelo que prevê `baa`. A medição de circularidade da §4.2 não é afetada: foi feita no dado por pixel. |
| 25/07/2026 | **Target decidido: caminho C.** Entrega 1 = previsão de `CRW_BAA` com horizonte de N dias; entrega 2 = branqueamento observado via GCBD. Registradas as cinco regras que a entrega 1 impõe ao pipeline e ao treino. |
