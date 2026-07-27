# Como o sistema funciona — versão sem jargão

Este documento explica **as peças de software do projeto**: onde os dados
moram, como as partes conversam, o que é cada arquivo estranho e por que as
decisões foram tomadas assim.

Não fala de coral nem de estatística. Para isso existe o par dele,
[METODOLOGIA_SIMPLES.md](METODOLOGIA_SIMPLES.md), que explica **a ciência** na
mesma linguagem.

Aqui a pergunta é outra: *o que essas pastas e comandos estão fazendo?*

## Índice

1. [As duas metades do site](#1-as-duas-metades-do-site)
2. [Como elas conversam: JSON e endpoints](#2-como-elas-conversam-json-e-endpoints)
3. [Os endpoints que existem hoje](#3-os-endpoints-que-existem-hoje)
4. [O que é paginação, e o erro que quase passou](#4-o-que-é-paginação-e-o-erro-que-quase-passou)
5. [Onde os dados moram — são três lugares](#5-onde-os-dados-moram--são-três-lugares)
6. [Dado e modelo são coisas diferentes](#6-dado-e-modelo-são-coisas-diferentes)
7. [Artefatos derivados, e por que não guardamos no Git](#7-artefatos-derivados-e-por-que-não-guardamos-no-git)
8. [O que é um teste, e por que existem 441](#8-o-que-é-um-teste-e-por-que-existem-441)
9. [Por que dois bancos de dados](#9-por-que-dois-bancos-de-dados)
10. [O que o Docker faz aqui](#10-o-que-o-docker-faz-aqui)
11. [Por que as senhas ficam fora do projeto](#11-por-que-as-senhas-ficam-fora-do-projeto)
12. [Vocabulário](#12-vocabulário)
13. [O endpoint que faz conta, e a escada escondida nele](#13-o-endpoint-que-faz-conta-e-a-escada-escondida-nele)

---

## 1. As duas metades do site

O projeto tem duas pastas grandes: `backend/` e `frontend/`. São **dois
programas diferentes**, em linguagens diferentes, que rodam ao mesmo tempo.

| | Backend | Frontend |
|---|---|---|
| Linguagem | Python (Django) | JavaScript (React) |
| Onde roda | **no servidor** | **no navegador do visitante** |
| O que faz | guarda os dados, faz as contas | desenha a tela |
| Como se liga | `python backend\manage.py runserver` | `npm start` |

### O detalhe que confunde

**O frontend não roda no servidor.** Ele é baixado e executa no computador de
quem abriu o site.

Por isso ele **não consegue** acessar o banco de dados: o banco está no
servidor, ele está na casa da pessoa. E é bom que seja assim — se o navegador
tivesse acesso direto ao banco, qualquer visitante poderia apagar tudo.

Então ele pede pela internet. Sempre.

```
   navegador                              servidor
       │                                      │
       │  "me dá os dados de Abrolhos"        │
       ├─────────────────────────────────────▶│
       │                                      ├── consulta o PostgreSQL
       │  {"nome": "Abrolhos", ...}           │
       │◀─────────────────────────────────────┤
       │
   desenha a tela
```

Cada seta dessas é uma chamada a um **endpoint**.

---

## 2. Como elas conversam: JSON e endpoints

### JSON é só um formato de texto

O backend não pode mandar "um objeto Python" pela internet — o frontend é
JavaScript e não entenderia. Então converte tudo para **texto**, num formato
que os dois sabem ler.

Uma linha do banco:

| local | data | variavel | valor | fonte |
|---|---|---|---|---|
| Abrolhos | 2026-07-24 | sst | 25.0 | noaa_crw |

Vira este texto:

```json
{
  "local": "abrolhos-ba",
  "data": "2026-07-24",
  "variavel": "sst",
  "valor": 25.0,
  "fonte": "noaa_crw"
}
```

Só isso. **Chaves `{ }` para um item, colchetes `[ ]` para uma lista de itens.**

Guarde essa diferença — ela vai importar na seção 4:

```json
[ {...}, {...}, {...} ]            ← uma LISTA de três itens

{ "count": 3, "results": [...] }   ← uma CAIXA, com a lista lá dentro
```

Para um humano parece a mesma informação. Para o programa, é a diferença entre
funcionar e dar erro.

### Endpoint é um endereço que o backend sabe atender

Quando a página de Abrolhos carrega, o navegador busca:

```
http://localhost:8000/api/locais/abrolhos-ba/
```

Cada endereço desses é um endpoint. É literalmente uma URL — você pode colar no
navegador e ver o JSON aparecer.

Alguns aceitam **filtros**, depois do `?`:

```
/api/medicoes/?local=abrolhos-ba&variavel=sst&de=2026-01-01
```

Lê-se: *"me dá as medições, só de Abrolhos, só temperatura, só de janeiro em
diante"*.

---

## 3. Os endpoints que existem hoje

| Endereço | Devolve | Quantos registros |
|---|---|---|
| `/api/status/` | se a API está viva | — |
| `/api/locais/` | os três recifes | 3 |
| `/api/locais/abrolhos-ba/` | um recife, com detalhes | 1 |
| `/api/locais/abrolhos-ba/datasets/` | os conjuntos de dados do recife | — |
| `/api/especies/` | as espécies catalogadas | 9 |
| `/api/datasets/` | o catálogo de fontes | 9 |
| `/api/monitoramento/` | ⚠️ o **modelo antigo** | 3 |
| `/api/grafo/localizacoes/` | os recifes, vindos do Neo4j | 3 |
| **`/api/medicoes/`** | ✅ **a série ambiental** | **57.420** |
| **`/api/painel-risco/`** | 🆕 **o risco calculado** | 3 |

Repare no contraste: tudo tem unidades ou dezenas de registros. **Só o
`/api/medicoes/` tem dezenas de milhares.**

E repare numa diferença maior, que não aparece na coluna dos números: **todos
menos o último entregam algo que já estava guardado.** O `painel-risco` é o
único que *faz uma conta* na hora em que alguém pergunta. Ver a seção 13.

### Por que o `/api/medicoes/` precisou existir

Passamos dias ingerindo 57.420 medições — temperatura, DHW, salinidade,
oxigênio — e elas ficaram no banco **sem nada para entregá-las à tela**. Se o
site quisesse desenhar um gráfico de temperatura, não tinha onde pedir.

O que existia era o `/api/monitoramento/`, servindo **3 registros** do modelo
antigo. O mesmo padrão que o grafo tinha: dado novo no banco, ninguém lendo.

### Três decisões nesse endpoint novo

**1. Cada valor vem com a etiqueta de onde saiu.** Não devolvemos só `25,0 °C`,
e sim o valor **mais** a fonte e o produto exato. O projeto inteiro se sustenta
em poder dizer de onde cada número veio.

**2. Quando não há dado, o campo vem vazio — nunca zero.** Se a validação
reprovou o valor (um pH de 2,5, impossível no mar), ele sai vazio com o motivo
escrito ao lado. O código antigo preenchia com **zero**, e aí o modelo aprendia
que o mar tem pH 0.

> Tem teste garantindo a distinção: DHW **zero** quer dizer *"não há estresse
> térmico"*; DHW **vazio** quer dizer *"não sabemos"*. São coisas diferentes, e
> confundi-las é o erro mais caro que este projeto já cometeu.

**3. Data inválida devolve erro.** Se alguém pedir `?de=ontem`, o certo é
recusar. O errado — e era o que aconteceria — seria **ignorar o filtro em
silêncio e mandar as 57 mil linhas**, com a pessoa achando que recebeu o
recorte que pediu.

---

## 4. O que é paginação, e o erro que quase passou

São 57.420 medições. Se alguém abre `/api/medicoes/` e o servidor manda todas
de uma vez, é uma resposta de vários megabytes, montada inteira na memória
antes de sair.

**Paginação** é entregar aos poucos:

```json
{
  "count": 57420,
  "total_paginas": 575,
  "results": [ ...100 itens... ]
}
```

E quem quiser mais pede a página seguinte.

### 🚨 O erro

Liguei a paginação **para todos os endpoints de uma vez**, achando que era uma
melhoria geral. Três testes que já existiam quebraram na hora — e estavam
certos.

Lembra da diferença entre lista e caixa? Antes, `/api/locais/` devolvia uma
**lista**:

```json
[{"slug": "abrolhos-ba"}, {"slug": "picaozinho-pb"}]
```

Com a paginação ligada, virou uma **caixa**:

```json
{"count": 3, "results": [{"slug": "abrolhos-ba"}, ...]}
```

O frontend já está escrito esperando a lista. Ele quebraria — e eu descobriria
só quando alguém abrisse o site.

E não havia motivo nenhum: esses endpoints têm **3, 9, 9 e 3** registros.

Revertido. A paginação ficou ligada só onde há volume.

> **A lição:** mudar o formato de uma resposta que alguém já consome é quebrar
> um contrato, mesmo quando a mudança parece uma melhoria. Ligar "por
> precaução" custou mais do que não ligar.

---

## 5. Onde os dados moram — são três lugares

```
  PostgreSQL (no Docker)   57.420 medições dos 3 recifes, 2020–2026
                           ✅ é a fonte da verdade

  dados/                   os arquivos do GCBD e das janelas ambientais
                           ✅ vêm de fora, não são versionados

  backend/dados/           ~260 MB de CSV de abril
                           ⛔ NÃO usados por nada — é lixo antigo
```

### Por que a segunda pasta existe

O banco é organizado por **recife monitorado** — e o projeto tem três, com
foto, nome e página no site.

O GCBD tem **119 pontos de mergulho** espalhados pelo Brasil. Não são recifes
monitorados: são lugares onde alguém mergulhou uma vez em 2007 e anotou o que
viu. Colocá-los no banco criaria 119 "recifes" falsos no site.

Então eles ficam em arquivo.

### Por que a terceira ainda está lá

É a pasta de abril, de antes da reconstrução. É onde estão o `ph.csv` que na
verdade contém alcalinidade e o arquivo da NOAA com coordenadas do Mar
Vermelho. **O código novo não abre nenhum deles**, mas eles continuam ocupando
disco — apagar ainda está na lista.

---

## 6. Dado e modelo são coisas diferentes

Essa distinção causou confusão real, e vale separar bem:

| | O que é | Exemplo |
|---|---|---|
| **Dado** | um número medido | *"28,4 °C em Abrolhos no dia 24"* |
| **Modelo** | o que foi **aprendido** com os números | *"quando o DHW sobe rápido, o risco é alto"* |

O modelo é mais parecido com uma **receita** do que com um número. Ele não
guarda as medições — guarda o padrão que ele encontrou nelas.

### Por que o modelo não era salvo

Até 27/07 ele **não era**. Os comandos de medição faziam isto:

1. liam os dados
2. aprendiam a receita
3. mediam se a receita é boa
4. **jogavam a receita fora**
5. imprimiam a nota

Como um aluno que estuda, faz a prova, tira 7 e esquece tudo.

**E isso está certo para medir.** Para saber se o modelo aprende de verdade, a
gente treina vários, cada um sem uma parte dos dados, e vê se acerta na parte
que não viu. Nenhum deles é "o modelo" — são pedaços de uma medição.

Mas o site precisa de **um** para carregar. Então agora existem dois comandos,
com propósitos opostos:

| Comando | Para quê |
|---|---|
| `treinar_modelo` | **medir** se presta — treina vários e descarta |
| `treinar_final` | **gravar** o que será servido — treina um, sobre tudo |

O segundo **não reporta desempenho, de propósito**: um número calculado sobre
os mesmos dados do treino mediria memória, não previsão.

---

## 7. Artefatos derivados, e por que não guardamos no Git

Três coisas neste projeto são **geradas por um comando**, e nenhuma delas entra
no Git:

| O quê | Comando que reconstrói |
|---|---|
| A documentação em `.docx` | `manage.py exportar_docs` |
| O modelo treinado | `manage.py treinar_final` |
| O grafo do Neo4j | `manage.py neo4j_projetar` |

A regra é uma só:

> **Cópia guardada envelhece em silêncio.** Em duas semanas o arquivo diz uma
> coisa e o código diz outra, e ninguém sabe qual vale. **Se um comando
> reconstrói, o comando é a verdade.**

É a mesma razão de não guardar o `.docx` junto com o `.md`: alguém editaria o
Word, e aí existiriam duas versões do mesmo documento discordando.

⚠️ **Consequência prática:** quem publicar o site precisa **rodar esses três
comandos**, porque nada disso viaja junto no `git push`. Está anotado no
checklist.

### Uma cautela extra com o modelo

O arquivo do modelo (`.joblib`) tem uma peculiaridade perigosa: **abri-lo
executa código**. É como o formato funciona por baixo.

Não é problema para um arquivo que o próprio projeto acabou de gerar. É
problema sério para um arquivo vindo de fora — alguém poderia mandar um
"modelo" que na verdade apaga arquivos ao ser carregado.

Por isso o código **lê primeiro uma ficha em texto** ao lado do arquivo, confere
se foi este projeto que gerou, e só então abre. Se não reconhecer, recusa.

---

## 8. O que é um teste, e por que existem 441

Um **teste automatizado** é um pedacinho de código que faz uma pergunta e
confere a resposta. Todos rodam com um comando, em cerca de 75 segundos:

```bash
python backend\manage.py test
```

E respondem uma coisa só: **OK** ou a lista do que quebrou.

### O que eles realmente compram

Não é "garantia de que não tem bug". É outra coisa, mais útil:

> **Eles avisam quando uma mudança quebra algo que funcionava** — inclusive
> algo que você nem lembrava que existia.

O caso da paginação é o exemplo perfeito. Um dos testes que quebrou fazia isto:

```python
resposta = pedir('/api/datasets/')
ids = [item['id'] for item in resposta]
```

*"Me dá os datasets, e para cada item pega o campo `id`."*

Ele **não foi escrito pensando em paginação**. Só verificava que o endpoint
devolve datasets com `id`. Mas, sem querer, ele estava **descrevendo o formato
da resposta** — e quando mudei o formato, avisou.

Sem ele, eu teria dito que estava tudo certo: o backend não dá erro nenhum. O
problema só apareceria com o site no ar e a página em branco.

**75 segundos, em vez de em produção.**

### Vários erros reais foram achados assim nesta reconstrução

- a lista que era esvaziada antes de o driver do Neo4j usá-la
- a medição de calibração que dava "perfeito" quando o modelo respondia sempre
  o mesmo número
- o dado de teste em que duas colunas eram idênticas, tornando a pergunta "qual
  importa mais" impossível de responder

Nenhum deles daria mensagem de erro sozinho.

---

## 9. Por que dois bancos de dados

| | PostgreSQL | Neo4j |
|---|---|---|
| Tipo | tabelas (como uma planilha) | grafo (bolinhas ligadas por setas) |
| Papel | **fonte da verdade** | **cópia derivada** |
| Recebe escrita? | sim | **nunca diretamente** |

### O Neo4j nunca é escrito à mão

Ele é **reconstruído** a partir do PostgreSQL, sempre no mesmo sentido. Se
divergir, corromper ou for perdido, roda-se o comando de novo.

O motivo é concreto: não existe jeito de gravar nos dois bancos "ao mesmo
tempo, ou em nenhum". Se a gravação falhasse no meio, os dois ficariam
diferentes — e **sem nenhuma forma de saber qual está certo**. Num projeto que
se sustenta em rastreabilidade, isso é pior do que o benefício.

### Para que serve o grafo, então

Para uma pergunta que a tabela responde mal: **de onde veio cada valor
exibido**.

Numa consulta só, o grafo mostra que a temperatura de Abrolhos veio do produto
`dhw_5km` da NOAA, a salinidade veio de um produto do Copernicus até 23/06 e de
**outro** produto dali em diante. Essa troca de produto no meio da série é
justamente o tipo de coisa que precisa ficar auditável — e em tabela exigiria
várias consultas encadeadas.

---

## 10. O que o Docker faz aqui

Os dois bancos **não estão instalados** na sua máquina. Eles rodam dentro do
Docker, e sobem com um comando:

```bash
docker compose up -d
```

Pense no Docker como uma **caixa lacrada com o programa e tudo de que ele
precisa dentro**. Você não instala o PostgreSQL, não configura, não mexe em
PATH — você baixa a caixa e liga.

Duas vantagens que importam aqui:

**Mesma versão em qualquer máquina.** O arquivo `docker-compose.yml` fixa
`postgres:17` e `neo4j:5`. No seu computador, no da faculdade e no servidor,
é exatamente a mesma coisa.

**Nada suja o sistema.** Se der problema, apaga a caixa e sobe outra. Nenhum
resíduo fica instalado no Windows.

⚠️ O Docker precisa estar **aberto** para os comandos funcionarem — não basta
estar instalado.

---

## 11. Por que as senhas ficam fora do projeto

O projeto usa três serviços que pedem credencial: Copernicus Marine, Climate
Data Store e o próprio banco.

**Nenhuma dessas senhas está dentro da pasta do projeto.** Elas moram na sua
pasta de usuário:

| Serviço | Onde a credencial mora |
|---|---|
| Copernicus Marine | `C:\Users\aissa\.copernicusmarine` |
| Climate Data Store | `C:\Users\aissa\.cdsapirc` |
| Banco de dados | `backend\.env` — **este está no `.gitignore`** |

### O motivo é que o erro é irreversível

Se uma chave entrar no Git, ela fica **em todos os commits anteriores para
sempre**. Apagar a linha depois não resolve: o histórico guarda tudo.

A única correção é **revogar a chave** no serviço e gerar outra. Não existe
"tirar do Git" de verdade.

Por isso a regra é dura: chave nunca no código, nunca no `.env` versionado,
nunca na linha de comando (que fica no histórico do terminal).

---

## 12. Vocabulário

| Palavra | O que quer dizer aqui |
|---|---|
| **Backend** | a metade que roda no servidor e guarda os dados |
| **Frontend** | a metade que roda no navegador e desenha a tela |
| **Endpoint** | um endereço que o backend sabe atender |
| **API** | o conjunto de todos os endpoints |
| **JSON** | o formato de texto em que os dois conversam |
| **Paginação** | entregar uma lista longa aos poucos |
| **Migração** | uma mudança na estrutura das tabelas do banco |
| **Commit** | um ponto salvo no histórico do código |
| **`.gitignore`** | a lista do que **não** entra no histórico |
| **Artefato derivado** | arquivo gerado por comando, não guardado |
| **Container** | a "caixa lacrada" do Docker |
| **Teste** | código que confere se outro código faz o esperado |
| **Ingestão** | o processo de buscar dados de fora e gravar |
| **Proveniência** | o registro de de onde cada valor veio |
| **Calibrar** | ajustar a probabilidade para que "30%" aconteça 30% das vezes |
| **Limiar** | o número a partir do qual se decide avisar |

---

## 13. O endpoint que faz conta, e a escada escondida nele

Todos os endpoints das seções anteriores fazem a mesma coisa: **procuram uma
linha guardada e devolvem**. Nenhum calcula nada.

O `/api/painel-risco/` é o primeiro diferente. Quando alguém o chama, ele:

1. abre o arquivo do modelo treinado,
2. busca no banco os últimos dias de temperatura, DHW, salinidade e oxigênio,
3. calcula o quanto cada uma **mudou em sete dias**,
4. entrega isso ao modelo, e
5. devolve a probabilidade de haver alerta daqui a sete dias.

### Uma armadilha silenciosa que quase ninguém veria

O modelo foi treinado com quatro números chamados, por exemplo,
`sst_variacao_7d` — *"quanto a temperatura mudou em 7 dias"*.

Agora imagine que, na hora de responder, o código calculasse esse número de
um jeito ligeiramente diferente — sete dias contados de outro jeito, ou uma
falta de dado tratada de outra forma. O modelo receberia **um número com o
nome certo e o conteúdo errado**.

E aqui está o problema: **nada quebraria.** Não apareceria erro nenhum. O
modelo aceitaria os quatro números, faria a conta e devolveria uma
probabilidade de aparência perfeitamente normal — só que errada, e sem nada
indicando isso.

> A defesa não foi "prestar atenção". Foi fazer com que **não exista um segundo
> jeito de calcular**: o código que responde chama exatamente a mesma função
> que o código que treinou. Não há duas versões para divergirem.

### Se falta dado, ele se recusa a responder

Se um dos dias necessários não estiver no banco, o endpoint responde
*"indisponível"* e diz **qual dia faltou** — em vez de completar com zero.

O motivo parece sutil e não é. O número que o modelo recebe é uma **variação**.
Preencher com zero não produz um valor estranho que alguém note: produz a
afirmação *"a temperatura não mudou nada"* — a mais tranquilizadora de todas,
exatamente no momento em que o dado sumiu.

E há uma distinção que custou um teste para ficar clara:

| Situação | O que acontece | Por quê |
|---|---|---|
| a série **termina** dois dias atrás | responde, avisando o atraso | é só a ingestão de hoje não ter rodado ainda |
| a série vai até hoje mas **falta um dia no meio** | recusa | é um buraco no que já foi coletado |

### 🚨 A escada: por que três recifes deram o mesmo número

Na primeira vez que rodamos o endpoint de verdade, os três recifes voltaram
com **exatamente o mesmo valor**: 0,0029. Com temperaturas e salinidades bem
diferentes. Parecia defeito.

Não era. É consequência de como a probabilidade foi **calibrada**.

Lembre da seção sobre calibração no [METODOLOGIA_SIMPLES.md](METODOLOGIA_SIMPLES.md):
o modelo prometia o dobro do que acontecia, e o conserto foi reajustar os
números. Esse reajuste funciona por **faixas** — como uma escada:

> Todos os casos que caem no mesmo degrau saem com o mesmo número.

Os três recifes tinham valores originais diferentes (0,083 e 0,066, por
exemplo), mas caíam no mesmo degrau. Então saem iguais. Sobre os 7.095 dias
usados no treino, existem só **313 valores possíveis** de probabilidade.

### E o degrau mais baixo vale exatamente zero

Essa é a parte que **muda o que a tela pode mostrar**.

O degrau mais baixo da escada vale **0,000 exato** — e 12,2% dos casos caem
nele. O mais alto vale **1,000 exato**.

Mas o que "0,000" significa aqui não é *"impossível"*. Significa: *"entre os
dias de treino que caíram neste degrau, nenhum virou alerta"*. É uma
afirmação sobre um punhado de dias, não sobre a natureza.

Se o site exibir **"risco de branqueamento: 0%"**, estará dizendo ao público
que branqueamento é impossível ali. E **"100%"** diria que é certo. Nenhum dos
dois é verdade, e nenhum dos dois é defensável num site que quer ser levado a
sério.

**O que fizemos — e o que decidimos não fazer.** A API avisa: junto da
probabilidade vai um campo dizendo *"este valor está no extremo"*. O que
**não** fizemos foi trocar o 0 por 0,001 para ficar mais apresentável. Isso
seria inventar uma precisão que o modelo não tem — mentir na direção oposta —
e ainda esconderia da tela justamente a informação de que ela precisa para
decidir como mostrar.

### Como a tela resolveu isso

Quando cai no extremo, a tela **não mostra número**. Mostra a faixa, com a
frase por extenso:

> **Faixa mais baixa da escala**
> O modelo coloca este dia no degrau mais baixo da escala calibrada. Isso quer
> dizer que nenhum dia semelhante do período de treino virou alerta — não que
> seja impossível.

E apareceu um **segundo caminho para o mesmo erro**, que ninguém tinha
previsto. Uma probabilidade de 0,04% arredondada para uma casa decimal vira
`"0,0%"` — que se lê como zero, mesmo sem o modelo ter dito zero. Agora esse
caso sai como `"< 0,1%"`: é uma afirmação sobre o arredondamento, não sobre o
mar.

### Uma regra que precisou valer em dois lugares

O risco aparece em **duas** telas: no painel de cada recife e no cartão da
lista. Enquanto o painel já usava o modelo novo e o cartão ainda mostrava o
número antigo, o mesmo recife aparecia com **dois valores diferentes**, cada
um de um modelo, e nada na tela dizia qual valia.

A correção não foi escrever a regra duas vezes com cuidado — foi fazer as duas
telas **chamarem a mesma função** de formatação. Uma regra escrita duas vezes
é uma regra que um dia vai divergir.

Pelo mesmo motivo, a tela **não decide sozinha** se deve avisar. Ela poderia
comparar a probabilidade com o limiar e concluir — mas então existiriam duas
respostas para a mesma pergunta, uma no servidor e outra no navegador. Quem
decide é o servidor; a tela mostra a decisão.

---

## Onde ver mais

| Documento | O que tem |
|---|---|
| [METODOLOGIA_SIMPLES.md](METODOLOGIA_SIMPLES.md) | **A ciência** sem jargão: como o modelo funciona e é testado |
| [VISAO_GERAL.md](VISAO_GERAL.md) | O projeto inteiro: branqueamento, variáveis, o caminho do dado |
| [arquitetura.md](arquitetura.md) | O mesmo deste documento, com os termos técnicos |
| [FONTES.md](FONTES.md) | De onde vem cada dado, e os problemas conhecidos |

---

## Histórico

| Data | Alteração |
|---|---|
| 27/07/2026 | **Seção 13 acrescentada, sobre o `/api/painel-risco/`** — o primeiro endpoint que faz conta em vez de servir linha guardada. Três coisas ficaram explicadas em linguagem comum: a armadilha de recalcular a mesma variável de outro jeito (o modelo receberia **o nome certo com o conteúdo errado** e responderia sem erro nenhum), a diferença entre série que *termina* mais cedo e série *furada*, e 🚨 **a escada da calibração** — por que os três recifes voltaram com exatamente o mesmo número, e por que o degrau mais baixo valer 0,000 significa "nenhum alerta entre estes dias", e não "impossível". Daí sai um requisito de tela: **o site não pode exibir "0%" nem "100%"**. Registrado também o que decidimos **não** fazer: trocar o 0 por 0,001 para ficar apresentável seria inventar precisão inexistente. |
| 27/07/2026 | Documento criado como par de software do [METODOLOGIA_SIMPLES.md](METODOLOGIA_SIMPLES.md), que cobre só a ciência. Reúne, em linguagem comum, as explicações que foram sendo pedidas ao longo da reconstrução: a separação entre backend e frontend e por que o navegador não acessa o banco, o que é JSON e por que a diferença entre lista e caixa quebrou três testes, os nove endpoints e por que só um precisa de paginação, os três lugares onde os dados moram, a distinção entre **dado** e **modelo**, a regra dos artefatos derivados (cópia guardada envelhece em silêncio), o que um teste realmente compra, por que há dois bancos e o segundo nunca recebe escrita direta, o papel do Docker e por que as credenciais ficam fora do projeto — sendo que essa última é irreversível, porque chave que entra no Git precisa ser revogada e não apagada. |
