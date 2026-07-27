# ERA5 — vento real

Levantamento feito em **26/07/2026**, antes de escrever qualquer conector.
Mesmo formato do [GCBD.md](GCBD.md): medir a fonte antes de depender dela.

> # 🚨 Conclusão: o levantamento derrubou a própria premissa
>
> O ERA5 foi promovido a prioridade máxima porque o vento parecia ser a única
> variável não térmica com sinal. **A validação contra o dado real mostrou que
> esse sinal não sobrevive à troca da fonte de vento.**
>
> Substituir o `Windspeed` do GCBD por vento medido do ERA5, nos mesmos pontos
> e nas mesmas datas, deixa o modelo **pior do que não ter vento nenhum**.
>
> Ver Etapa 6. **A recomendação de prioridade está revogada**, e o resto deste
> documento fica como registro da infraestrutura medida — que continua válida
> e reutilizável se algum dia o ERA5 voltar a fazer sentido.

---

## Por que esta fonte foi priorizada (e por que a premissa caiu)

O argumento original era:

| Onde apareceu | Evidência |
|---|---|
| [RESULTADOS.md](RESULTADOS.md) §12.2 | 2ª variável mais importante do modelo interpretável (+0,073 de queda no PR-AUC) |
| [RESULTADOS.md](RESULTADOS.md) §17 | Coeficiente **−0,72** — mais vento, menos branqueamento |
| [RESULTADOS.md](RESULTADOS.md) §17 | *d* de Cohen **−0,461**, maior que o de qualquer variável ambiental ingerida |

Mais o mecanismo, que é conhecido: vento mistura a coluna d'água, quebra a
camada quente parada na superfície e traz água mais fria de baixo.

E a assimetria: o vento do projeto é uma **constante inventada**
([FONTES.md](FONTES.md) §6.7) — o código legado escreve um número fixo.

**O furo do argumento:** toda essa evidência vinha de **uma única coluna**, o
`Windspeed` do próprio GCBD. Ninguém tinha conferido se aquela coluna descrevia
o vento. Era exatamente o tipo de suposição que este projeto se propôs a não
fazer — e foi a Etapa 6 que a testou.

---

## Identificação da fonte

| | |
|---|---|
| **Nome** | ERA5 hourly data on single levels from 1940 to present |
| **Produtor** | ECMWF, para o Copernicus Climate Change Service (C3S) |
| **Acesso** | Climate Data Store (CDS) — `https://cds.climate.copernicus.eu/api` |
| **Cliente** | `cdsapi==0.7.6` |
| **Variáveis** | `10m_u_component_of_wind`, `10m_v_component_of_wind` |
| **Resolução** | **0,25°** (~28 km), horária |
| **Licença** | Licença Copernicus — **atribuição obrigatória** |

**Citação — são duas, como no GCBD:**

| O que está sendo citado | Citação |
|---|---|
| O **artigo** que descreve a reanálise | Hersbach, H. et al. (2020). *The ERA5 global reanalysis.* Quarterly Journal of the Royal Meteorological Society, 146(730). doi:`10.1002/qj.3803` |
| Os **dados** baixados | Hersbach, H. et al. (2023). *ERA5 hourly data on single levels from 1940 to present.* Copernicus Climate Change Service (C3S) Climate Data Store (CDS). |

⚠️ **O DOI do dataset ainda não foi conferido na página oficial.** Fica na mesma
pendência dos DOIs dos produtos CMEMS ([FONTES.md](FONTES.md) §6.15) —
**bloqueante para submissão**, e não vale copiar de memória.

Mais a frase de atribuição exigida pela licença:

> "Contains modified Copernicus Climate Change Service information [ano]"

E a ressalva que a própria licença pede: nem o C3S nem o ECMWF respondem pelo
uso que se faz do dado.

---

## Etapa 1 — Credencial

**Por que ela não fica no projeto.** Mesma decisão já tomada para o Copernicus
Marine: a chave mora em `~/.cdsapirc`, na pasta do usuário, **fora do
repositório**. Nunca no `.env`, nunca no código, nunca na linha de comando.

O motivo é que chave em código vai para o Git, e chave que entrou no histórico
do Git **precisa ser revogada** — apagar a linha depois não resolve, porque o
valor continua em todo commit anterior. É irreversível de um jeito que a maioria
dos erros de configuração não é.

O `cdsapi` procura em três lugares, nesta ordem:

| Ordem | Onde | Usar? |
|---|---|---|
| 1 | Variáveis `CDSAPI_URL` / `CDSAPI_KEY` | aceitável |
| 2 | Arquivo `~/.cdsapirc` | ✅ **é o adotado** |
| 3 | `cdsapi.Client(url=..., key=...)` | ⛔ **nunca** — põe a chave no `.py` |

**Dois passos, e o segundo é o que todo mundo esquece:**

1. Colar as duas linhas de `/how-to-api` em `~/.cdsapirc`
2. **Aceitar a licença do ERA5** no site, na aba Download do dataset

Sem o passo 2 a chave está correta e a API responde **`403`** assim mesmo. Um
teste que só distingue "funcionou/não funcionou" deixa a pessoa procurando erro
na chave por horas — por isso o diagnóstico separa 401 de 403.

### 🚨 O `403` do CDS é ambíguo — e o meu primeiro diagnóstico estava errado

Descoberto em 26/07/2026, ao pedir 13 anos de uma vez:

```
403 Client Error: Forbidden
cost limits exceeded
Your request is too large, please reduce your selection.
```

**O mesmo `403` significa duas coisas sem nenhuma relação entre si:**

| Texto na resposta | O que é | O que fazer |
|---|---|---|
| menciona *licence* | licença não aceita | aceitar no site |
| `cost limits exceeded` | **pedido grande demais** | partir em pedidos menores |

O primeiro diagnóstico que escrevi mapeava `403 → licença`. Se alguém tivesse
rodado aquilo, teria ido conferir uma licença que já estava aceita, enquanto o
problema era o tamanho do pedido.

**A lição é geral, não sobre o ERA5:** *código HTTP não é diagnóstico*. É o
**texto da resposta** que distingue, e ele precisa ser lido antes de traduzir o
erro para o humano. Mesmo tipo de defeito que o `except` sem tipo do modelo
legado, que engolia a causa real ([METODOLOGIA.md](METODOLOGIA.md) §8).

⚠️ No Windows há uma armadilha: o Bloco de Notas salva como `.cdsapirc.txt` sem
avisar, e o cliente não encontra o arquivo. Criar o arquivo antes, pelo caminho
completo, evita isso.

---

## Etapa 2 — A conexão funciona, e a fila não atrapalha

Medido em **26/07/2026**, com um pedido mínimo: uma hora, um retângulo pequeno
sobre Abrolhos.

| | |
|---|---|
| Resposta | **200** |
| Tempo total | **40,4 s** |
| Ciclo | `accepted` → `running` → `successful` em ~35 s |
| Arquivo | 33,3 KB, NetCDF |

**Por que isso precisava ser medido.** O CDS não é como o PACIOOS nem como o
Copernicus Marine: ele **não devolve o dado na hora**. Você submete um pedido,
ele entra numa fila compartilhada com o mundo inteiro, e você espera. Era o
risco número um da fonte — se a espera fosse de horas, as 166 janelas do GCBD
seriam inviáveis.

Não é. Quarenta segundos para um pedido mínimo é aceitável.

⚠️ **Isso não é promessa.** A fila é compartilhada e varia com a carga global.
Um pedido grande num dia movimentado pode demorar muito mais. O conector vai
precisar tolerar espera, e o dimensionamento real está na Etapa 4.

### O que veio

| | |
|---|---|
| Grade | 5 lat × 7 lon, resolução **0,25°** |
| Variáveis | `u10`, `v10` |
| Vento em Abrolhos, 15/01/2024 12:00 UTC | **5,39 m/s** |

O ERA5 entrega o vento em **duas componentes** — leste-oeste (`u10`) e
norte-sul (`v10`). A velocidade é `√(u² + v²)`. Isso não é detalhe de formato:
tirar a média de `u` e `v` separadamente **e depois** calcular a velocidade dá
resultado diferente de calcular a velocidade e depois tirar a média — e o
segundo é o correto para "quanto ventou". Ver Etapa 5.

---

## Etapa 3 — ⛔ O espelho sem fila foi testado e não serve

Antes de aceitar a fila, testei a alternativa: o **ARCO-ERA5**, um espelho
público do ERA5 em formato Zarr na Google Cloud, sem credencial e sem fila.

Era a mesma estratégia que funcionou com o PACIOOS — usar um espelho, citar a
fonte original, e registrar qual servidor foi usado.

**Resultado: abortado após ~25 minutos sem conseguir sequer abrir o dataset**,
quanto mais extrair um valor.

**O motivo é o formato, e ele é estrutural.** O ARCO é fatiado (*chunked*) por
**instante de tempo**: cada pedaço do arquivo contém o mapa do mundo inteiro
numa hora. Isso é ótimo para quem quer "o vento global às 12h de hoje", e é o
pior caso possível para o que precisamos — a série de **um ponto ao longo de
anos** exigiria uma leitura separada por hora, dezenas de milhares delas.

> O formato de armazenamento decide para que serve um dado, e não só quanto ele
> pesa. O ARCO tem exatamente os mesmos números do CDS e é inútil para este uso.

**Fica registrado como alternativa medida e descartada**, com o motivo, para que
ninguém a tente de novo daqui a três meses achando que é atalho.

---

## Etapa 4 — Custo, medido

O ERA5 é **horário**, então o volume bruto é 24× o número de dias — e o CDS
cobra por campo pedido, não por byte baixado.

### O que já foi medido

| Pedido | Volume | Tempo | Resultado |
|---|---|---|---|
| 1 hora, 1 retângulo pequeno | 33 KB | **40 s** | ✅ |
| 3 anos, Brasil, 4 horários/dia | 40,8 MB | **642 s** (~10 min de fila) | ✅ |
| **13 anos**, Brasil, 4 horários/dia | — | — | ⛔ **`cost limits exceeded`** |

**Existe um teto por pedido, e ele é atingível.** 3 anos passam; 13 não. O
conector vai precisar **partir a requisição** — e isso não é otimização, é
requisito.

### Duas reduções que funcionam

**1. Quatro horários em vez de vinte e quatro.** `00, 06, 12, 18 UTC` cobrem o
ciclo diário a 1/6 do custo. ⚠️ Isso **suaviza a rajada**: um pico de vento às
15h não aparece. Serve para média diária; não serve se algum dia quisermos
máxima diária — e essa decisão precisa ser refeita se o alvo mudar.

**2. Pedir só os meses que têm visita.** Para a validação, o GCBD tem visitas em
apenas uma fração dos meses. Pedir ano a ano, só os meses úteis, corta a maior
parte do volume sem perder nada.

### O que ainda falta dimensionar

| Para quê | Pontos | Período |
|---|---|---|
| Entrega 1 — os 3 recifes | 3 | 2020-01-01 → hoje |
| Entrega 2 — janelas de 90 dias antes das 166 visitas | 119 sítios | 1994–2010 |

A janela de 90 dias é mais cara que a validação: precisa dos meses **anteriores**
a cada visita, não só o mês dela.

---

## Etapa 5 — Decisões que já se sabe que serão necessárias

Nenhuma é óbvia, e todas mudam o número final.

**1. Velocidade antes da média, nunca depois.** `u` e `v` são vetores com sinal.
Um dia com vento forte de leste de manhã e forte de oeste à tarde tem média de
`u` perto de **zero** — e ventou o dia inteiro. Calcular `√(u²+v²)` a cada hora
e só então tirar a média do dia é o que responde "quanto ventou".

**2. Média diária, máxima, ou as duas?** A entrega 1 aprendeu que trajetória
importa mais que nível ([RESULTADOS.md](RESULTADOS.md) §3). Mas cada feature
nova é um grau de liberdade que 166 visitas não sustentam — e a colinearidade
já mordeu o projeto duas vezes. Começar com **uma** e justificar qualquer
acréscimo.

**3. 🚨 A resolução é 0,25° — a mesma do produto de oxigênio.** É exatamente a
grade que virou a ressalva de [RESULTADOS.md](RESULTADOS.md) §18, onde 20
sítios só tinham oxigênio a até 33 km do recife.

O mesmo argumento se aplicaria ao vento — **mas talvez não com a mesma força**,
porque vento é um campo grande e suave, enquanto oxigênio junto à costa é
irregular. Isso precisa ser **medido, não assumido**. Ver Etapa 6.

**4. A unidade do `Windspeed` do GCBD.** Ver abaixo — houve uma afirmação
errada minha aqui, corrigida por medição.

---

## Etapa 6 — A validação de graça

O GCBD traz um `Windspeed` **próprio** para cada uma das 166 visitas. Isso
permite comparar o ERA5 contra outra fonte, nos mesmos pontos e nas mesmas
datas, **sem custo nenhum**.

O que essa comparação responde:

- **Se baterem:** o ERA5 a 28 km descreve bem o vento no recife. Isso valida a
  fonte *e* enfraquece a explicação concorrente de §18 — sinal de que 28 km não
  é fatal para variável de campo suave.
- **Se não baterem:** é aviso sério, e o motivo precisa ser encontrado antes de
  qualquer conclusão sobre o vento.

Nos dois casos se aprende algo, e não se gasta nada. Mesmo raciocínio que fez o
passo 1 do GCBD vir antes do passo 2.

### ⚠️ Primeira tentativa: subamostra escolhida por volume, e deu errado

Rodei a comparação primeiro sobre **2007, 2008 e 2010** — os três anos com mais
visitas. Escolher por volume parecia razoável. **Não era.**

| Recorte | *n* | *d* de Cohen do `Windspeed` |
|---|---|---|
| Todas as visitas | 166 | **−0,461** |
| A subamostra que escolhi | 88 | −0,128 |
| O resto | 78 | **−0,811** |

O motivo aparece na quebra por ano:

| Ano | *n* | *d* |
|---|---|---|
| 2003 | 15 | −0,646 |
| 2005 | 16 | **−1,761** |
| 2006 | 12 | **−1,491** |
| 2007 | 33 | −0,831 |
| **2008** | 23 | **+1,014** 🚨 |
| 2009 | 18 | −0,169 |
| 2010 | 32 | −1,084 |

**2008 é o único ano em que o efeito do vento inverte de sinal**, e a
subamostra o incluiu. O resultado foi comparar ruído contra ruído: as duas
fontes pareceram discordar, quando na verdade nenhuma das duas tinha sinal
naquele recorte.

> **Amostra escolhida por volume não é amostra representativa.** Num conjunto em
> que o efeito varia de −1,76 a +1,01 entre anos, três anos quaisquer não
> descrevem o todo — e o erro é silencioso, porque o número que sai parece
> válido.

É o mesmo tipo de armadilha que a validação agrupada por ano existe para
evitar ([METODOLOGIA.md](METODOLOGIA.md) §3.1).

### 🔎 E fica um achado que não é sobre o ERA5

**O efeito do vento é instável entre anos** — de −1,76 (2005) a +1,01 (2008).

Isso **não contradiz** a importância medida no passo 2 (+0,043 sob validação
agrupada por ano, 2ª colocada). Uma variável pode ajudar em quatro dobras,
atrapalhar numa, e ainda somar positivo. Mas tempera a leitura: o vento é a
melhor variável não térmica que temos, e ainda assim seu efeito não é estável.

Qualquer texto que diga "mais vento, menos branqueamento" precisa dizer também
que **em 2008 foi o contrário**.

---

## 🚨 Etapa 6, resultado — as duas fontes concordam sobre o vento e discordam sobre o coral

Rodado sobre **as 166 visitas**, com o ERA5 baixado ano a ano.

### As duas medem a mesma coisa

| | |
|---|---|
| Correlação de Pearson | **r = +0,708** |
| Erro absoluto médio | 1,20 m/s |
| Viés (ERA5 − GCBD) | −0,55 m/s |
| Dentro de 2 m/s | **80,7%** |
| Razão mediana | **0,905** |

✅ **A unidade fica confirmada: m/s.** Se o GCBD estivesse em nós, a razão seria
~1,94. A correção registrada na Etapa 5 se sustenta com fonte independente.

✅ **E 28 km serve para vento.** Duas fontes independentes, uma delas arredondada
para inteiro, concordando em r = 0,71. Isso responde à pergunta que motivou a
Etapa 6 e **enfraquece a hipótese de resolução** para campos suaves — reforçando
que a ressalva de [RESULTADOS.md](RESULTADOS.md) §18 é específica de variáveis
irregulares como oxigênio e nutrientes, não geral.

### Mas o efeito sobre o branqueamento só existe numa delas

| Fonte do vento | *d* de Cohen | IC 95% (bootstrap, 2.000 reamostragens) |
|---|---|---|
| `Windspeed` do GCBD | **−0,461** | [−0,783, −0,160] — **não inclui zero** |
| **ERA5** | **−0,057** | [−0,358, +0,254] — **inclui zero** |

E no modelo, que é o que decide:

| Features | PR-AUC sítio | **PR-AUC ano** |
|---|---|---|
| `TSA_DHW` + `TSA`, **sem vento** | 0,699 | 0,692 |
| \+ `Windspeed` do GCBD | 0,722 | **0,717** |
| \+ **vento do ERA5** | 0,698 | **0,673** |

> **Trocar a coluna do GCBD por vento medido de verdade deixa o modelo pior do
> que não ter vento nenhum.**

### Três hipóteses testadas para explicar a diferença

**H1 — a coluna do GCBD carrega outra variável escondida?** ⛔ Não. As duas
colunas se correlacionam quase igual com tudo o mais — mês (+0,54 nas duas),
latitude (+0,54 e +0,45), turbidez (−0,36 e −0,19). A maior diferença é 0,16.

**H2 — é o arredondamento para inteiro?** ⛔ Não. Arredondando o ERA5 também
para inteiro, o *d* vai de −0,057 para −0,040. Não muda nada.

**H3 — é ruído de 166 amostras?** ✅ **É a explicação que sobra.** Os dois
intervalos de confiança **se sobrepõem largamente**. As duas estimativas são
estatisticamente compatíveis entre si; a diferença é que só uma delas exclui o
zero — e ela exclui por pouco.

### O que isso estabelece, e o que não estabelece

**Estabelece:** o efeito do vento **não é robusto à escolha do produto de
vento**. Um ganho de +0,025 no PR-AUC — que
[RESULTADOS.md](RESULTADOS.md) §15 já classificava como **dentro do ruído** —
vira −0,019 ao trocar a fonte. Isso é suficiente para revogar "o vento é a
variável não térmica que funciona".

**Não estabelece** que não há efeito do vento. Os intervalos se sobrepõem; com
166 visitas nenhuma das duas estimativas é precisa. O que se sabe é que **a
evidência não sustenta o peso que eu coloquei nela**.

> **A lição não é sobre vento.** É que uma diferença dentro do ruído declarado
> não deve virar prioridade de projeto, por mais que o mecanismo faça sentido.
> Eu declarei o ruído em §15 e depois raciocinei como se ele não existisse.

### ⚠️ Correção — a unidade do `Windspeed` do GCBD

Em 26/07/2026 eu afirmei, num script de teste, que *"o GCBD traz Windspeed em
nós"*. **Não conferi antes de escrever, e a medição diz o contrário.**

| | GCBD `Windspeed` | ERA5 em Abrolhos |
|---|---|---|
| Faixa | 3 a 9 | — |
| Média | 5,80 | 5,39 m/s |
| Formato | **todos inteiros** | contínuo |

Se fosse em nós, a faixa de 3 a 9 equivaleria a **1,5 a 4,6 m/s** — vento
fraquíssimo o ano inteiro, num litoral dominado por alísios. A leitura
compatível é **m/s**.

Isso importa por dois motivos:

1. **Muda como as duas fontes se combinam.** Comparar m/s com nós daria um erro
   sistemático de 1,94× e a validação da Etapa 6 acusaria discordância onde não
   há.
2. **O arredondamento é limitação em si.** O GCBD não distingue 5,4 de 6,4 m/s.
   Qualquer concordância com o ERA5 tem esse piso de granularidade.

🚨 **Ainda assim, isto é inferência a partir da distribuição, não confirmação.**
Antes de ir para o artigo, precisa ser conferido no artigo do van Woesik. O
padrão do projeto vale aqui como em qualquer outro lugar: número medido orienta
o trabalho; só a fonte primária sustenta afirmação.

---

## Estado

| Etapa | Situação |
|---|---|
| 1 — Credencial | ✅ configurada e testada; o `403` do CDS é ambíguo |
| 2 — Conexão | ✅ `200` em 40,4 s |
| 3 — Espelho alternativo | ⛔ medido e descartado |
| 4 — Custo | ✅ há teto por pedido: 3 anos passam, 13 não |
| 5 — Decisões de agregação | ✅ velocidade-antes-da-média; unidade confirmada em m/s |
| 6 — Validação contra o GCBD | ✅ feita — **e derrubou a premissa** |
| 7 — Conector | ⛔ **não será escrito agora** |

## Decisão: não escrever o conector

**Motivo:** a Etapa 6 mostrou que o vento medido de verdade não melhora o
modelo — deixa pior que não ter vento. Escrever conector, ingerir 17 anos e
manter isso vivo para uma variável cujo efeito não se confirma seria trabalho
sem retorno.

**O que continua valendo, e por isso este documento não é desperdício:**

| O que | Onde | Por que continua útil |
|---|---|---|
| A credencial configurada | `~/.cdsapirc` | funciona; não precisa refazer |
| O `403` ambíguo | Etapa 1 | armadilha que mordeu e vai morder de novo |
| O teto por pedido | Etapa 4 | 3 anos passam, 13 não — dimensionamento real |
| O espelho descartado | Etapa 3 | impede que alguém tente o atalho de novo |
| Velocidade antes da média | Etapa 5 | erro que qualquer pessoa comete uma vez |
| **28 km serve para vento** | Etapa 6 | r = 0,71 contra fonte independente — informa a leitura de §18 |

**Quando reabrir:** se o alvo mudar (rajada em vez de média, por exemplo), ou se
houver amostra maior. Com 166 visitas, um efeito de +0,025 no PR-AUC não se
distingue de zero, e nenhuma fonte nova resolve isso.

---

## Histórico

| Data | Alteração |
|---|---|
| 26/07/2026 | 🚨 **Etapa 6 concluída — o levantamento derrubou a própria premissa, e a prioridade do ERA5 está revogada.** As duas fontes de vento **concordam sobre o vento** (r = +0,708, EAM 1,20 m/s, 80,7% dentro de 2 m/s, razão 0,905 confirmando m/s) e **discordam sobre o coral**: `Windspeed` do GCBD dá *d* = −0,461 (IC95% [−0,783, −0,160], exclui zero) e o ERA5 dá *d* = −0,057 (IC95% [−0,358, +0,254], inclui zero). No modelo, **trocar a coluna do GCBD por vento medido deixa pior que não ter vento**: PR-AUC por ano de 0,717 para 0,673, contra 0,692 sem vento nenhum. Testadas e descartadas as hipóteses de variável escondida (as duas colunas correlacionam quase igual com tudo) e de arredondamento (ERA5 arredondado dá −0,040); sobra ruído de 166 amostras, com os intervalos se sobrepondo. **Decidido não escrever o conector.** Fica um achado positivo colateral: **28 km serve para vento**, o que torna a ressalva de [RESULTADOS.md](RESULTADOS.md) §18 específica de variáveis irregulares e não geral. E fica a lição: *uma diferença dentro do ruído declarado não deve virar prioridade de projeto* — o ganho de +0,025 já estava classificado como ruído em §15, e eu raciocinei como se não estivesse. |
| 26/07/2026 | **Etapa 4 medida e duas armadilhas registradas.** (a) **O CDS tem teto por pedido**: 3 anos passam (40,8 MB em 642 s), 13 devolvem `cost limits exceeded` — partir a requisição é requisito, não otimização. (b) 🚨 **O `403` do CDS é ambíguo**: significa tanto "licença não aceita" quanto "pedido grande demais", e o meu primeiro diagnóstico mapeava `403 → licença`, o que mandaria a pessoa conferir uma licença já aceita. A lição é geral — *código HTTP não é diagnóstico*, o texto da resposta é. (c) **Erro meu de amostragem**: escolhi 2007/2008/2010 por volume, e a subamostra incluiu **2008, o único ano em que o efeito do vento inverte de sinal**; o *d* do GCBD caiu de −0,461 para −0,128 e a comparação virou ruído contra ruído. Fica o achado independente de que **o efeito do vento é instável entre anos**, de −1,76 (2005) a +1,01 (2008) — o que não contradiz a importância medida sob validação agrupada, mas exige que nenhum texto afirme "mais vento, menos branqueamento" sem essa ressalva. |
| 26/07/2026 | Documento criado. Credencial configurada em `~/.cdsapirc` — fora do repositório, porque chave que entra no histórico do Git precisa ser revogada e não apenas apagada. Conexão medida: **200 em 40,4 s**, com o ciclo de fila do CDS levando ~35 s; a fila era o risco número um da fonte e não se confirmou como impeditivo. **Espelho ARCO na Google Cloud testado e descartado**: abortado após ~25 min sem abrir, porque é fatiado por instante de tempo — ótimo para o mapa global de uma hora, inútil para a série de um ponto ao longo de anos. Registradas as decisões de agregação que já se sabe necessárias, com destaque para calcular a velocidade **antes** da média diária, já que `u` e `v` têm sinal. E **corrigida uma afirmação minha não verificada**: o `Windspeed` do GCBD não está em nós — os valores são inteiros de 3 a 9 com média 5,80, compatíveis com m/s e não com nós; segue pendente de confirmação na fonte primária. |
