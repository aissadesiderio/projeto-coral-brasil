# Documento de Arquitetura

## Escopo
Este documento registra a divisao de responsabilidades entre PostgreSQL, o treino do modelo e o Neo4j, e fixa o schema canonico do grafo usado pelo backend.

📖 **Existe uma versao sem jargao deste documento**, com as mesmas decisoes
explicadas em linguagem comum: [SISTEMA_SIMPLES.md](SISTEMA_SIMPLES.md). Use
aquela para entender ou explicar; esta para implementar e auditar.

---

## Decisao de arquitetura — 25/07/2026

Tres camadas, com **uma unica fonte de escrita**.

| Camada | Tecnologia | Papel |
|---|---|---|
| **Fonte da verdade** | PostgreSQL | Tudo o que e escrito: medicoes, locais, especies, usuarios, execucoes de ingestao, predicoes |
| **Treino e analise** | pandas, a partir do Postgres | Monta a tabela supervisionada (`backend/ml/dataset.py`) e calcula relacoes entre variaveis |
| **Projecao de grafo** | Neo4j | **Derivado**, reconstruivel. Proveniencia e travessia entre entidades |

### Regra que sustenta o desenho

**O Neo4j nunca recebe escrita direta.** Ele e reconstruido a partir do PostgreSQL, sempre no mesmo sentido. Se divergir, corromper ou for perdido, basta reconstruir — nao ha dado exclusivo dele.

A alternativa considerada era escrita paralela nos dois bancos, como o texto anterior deste documento sugeria. Foi descartada: nao existe transacao distribuida entre Postgres e Neo4j, entao uma falha no meio da ingestao deixaria os dois bancos divergentes **sem nenhuma forma de saber qual esta certo**. Num trabalho que se sustenta em proveniencia, isso e um risco maior do que o beneficio.

### Por que o treino nao le do grafo

Esta decisao foi tomada sobre uma pergunta especifica: *"a ideia e ver relacao dos dados das variaveis, e treinar a IA"*. As duas coisas parecem pedir um banco de grafo, e nenhuma pede.

**1. "Relacao entre variaveis" e estatistica, nao topologia.**

Um exemplo concreto: *a salinidade cai e tres dias depois o DHW sobe?* Isso e correlacao defasada entre duas series numericas — uma conta feita sobre uma tabela de numeros:

```
correlacao( salinidade[t-3] , dhw[t] )
```

Uma relacao de **grafo** e outra coisa: `(:Localizacao)-[:ABRIGA_ESPECIE]->(:Especie)`. Sao entidades ligadas por vinculos nomeados.

Colocar as medicoes diarias no Neo4j nao faz a correlacao entre variaveis aparecer. Para calcula-la seria preciso exportar tudo para uma tabela de qualquer forma.

**2. Treino de modelo consome matriz, nao travessia.**

O `sklearn` recebe linhas x colunas. E exatamente o que `backend/ml/dataset.py` produz a partir do banco relacional. Usar o Neo4j como origem do treino acrescentaria um passo de exportacao, nao uma capacidade — e agregacao temporal em Cypher e fraca justamente onde este projeto mais precisa (janelas, defasagens, media movel).

**3. Serie temporal densa em grafo e anti-padrao.**

Sao 57.420 medicoes hoje, crescendo ~66 por dia, cada uma com relacoes de proveniencia. O ganho de consulta e nulo: ninguem pergunta "qual medicao esta a tres saltos desta".

### Onde o grafo ganha de fato

Duas perguntas que a tabela responde mal, e que sao contribuicao real do trabalho:

- **Proveniencia completa de um valor exibido:** `(:Predicao)-[:DERIVADA_DE]->(:MedicaoAmbiental)-[:PROVENIENTE_DE]->(:FonteDados)`. Percorrer isso em SQL exige varios JOINs; em Cypher e uma travessia.
- **Comparacao entre recifes por vizinhanca de perfil:** "quais especies ocorrem em locais que compartilham perfil de risco". E busca por caminho, nao por agregacao.

### Escopo do que e projetado

| No | Entra no grafo? | Volume real |
|---|---|---|
| `Localizacao` | ✅ sim | 3 |
| `Especie` | ✅ sim | 9 |
| `FonteDados` | ✅ sim | 5 |
| **`MedicaoAmbiental` diaria** | ✅ **sim — medido em 27/07/2026** | **57.420** |
| `Predicao` | ⏳ nao ainda | ver "O que ainda nao esta materializado" |
| Agregado mensal | ⛔ dispensado | a opcao A cobre, sem perder proveniencia |

⚠️ **Este paragrafo dizia "a medir" e exigia medir antes de projetar. Foi feito** — o resultado esta na secao "A projecao, executada em 27/07/2026". Em resumo: a medicao diaria **cabe** (172 mil elementos, 16 s), o teto de nos que se temia era do **Neo4j 3.x** e nao existe na 5.26 Community, e o agregado mensal foi **dispensado** porque economizaria 30x ao custo de destruir a proveniencia por valor — que e a razao de o grafo existir.

---

## Responsabilidades por banco

### PostgreSQL — fonte unica da verdade
- autenticacao, admin e configuracoes operacionais;
- `LocalRecife`, `Especie`, `MedicaoAmbiental`, `ExecucaoIngestao`, `DatasetCatalogo`, `PerfilUsuario` e `SolicitacaoEspecie` (fila de moderação, desde 08/08/2026);
- integridade relacional e operacao normal dos endpoints REST;
- **origem de tudo o que o modelo treina** e de tudo o que o grafo projeta.

### Neo4j — projecao derivada
Um unico schema canonico para consultas de grafo e travessia:
- exploracao de `Localizacao`, `Especie`, `MedicaoAmbiental`, `Predicao` e `FonteDados`;
- leitura agregada para endpoints de grafo;
- **nunca recebe escrita que nao venha do PostgreSQL.**

### Artefatos derivados — uma terceira categoria

Acrescentada em **27/07/2026**, ao persistir o modelo treinado. O projeto passou
a ter tres tipos de coisa no disco, e confundi-los ja causou problema antes.

| Categoria | Exemplos | Regra |
|---|---|---|
| **Fonte da verdade** | PostgreSQL | E escrito, versionado por backup, nunca reconstruido |
| **Fonte externa** | `dados/*.csv` do GCBD e das janelas | Nao versionado, reconstruivel **pelo DOI ou pela API** |
| **Artefato derivado** | `.docx` da documentacao, `.joblib` do modelo, projecao do Neo4j | Nao versionado, reconstruivel **por um comando deste repositorio** |

A regra dos derivados e uma so, e vale para os tres:

> **Copia versionada envelhece em silencio.** Em duas semanas o artefato diz uma
> coisa e o codigo diz outra, e ninguem sabe qual vale. Se um comando
> reconstroi, o comando e a verdade.

Consequencia pratica que precisa estar declarada: **quem publicar o site precisa
rodar os comandos de reconstrucao**, porque nada disso viaja no `git push`.

| Artefato | Comando | Onde |
|---|---|---|
| Documentacao em `.docx` | `manage.py exportar_docs` | `docs/exportado/` |
| Modelo treinado | `manage.py treinar_final` | `dados/modelos/` |
| Projecao do grafo | `manage.py neo4j_projetar` | Neo4j |

🚨 **A regra acima foi escrita tres vezes e nunca foi executada por ninguem.**
Registrado em 28/07/2026, ao fechar o checklist de go-live: cada um dos tres
artefatos ganhou, no momento em que foi criado, uma linha dizendo "o deploy
precisa rodar isto" — e o deploy nunca existiu. Tres avisos corretos, escritos
em tres lugares diferentes, somam **zero** garantia.

O efeito de publicar sem eles nao e degradacao suave:

| Artefato ausente | O que o usuario ve |
|---|---|
| `.joblib` | `/api/painel-risco/` responde **503** nos tres recifes |
| projecao | `/api/grafo/localizacoes/` vazio |
| `.docx` | nada no site — so a documentacao offline falta |

Ver `manage.py preparar_deploy`, que executa os tres em ordem e confere o
resultado. **Aviso escrito nao e passo executado** — a diferenca entre os dois
custou o unico bloqueio real que sobrou depois do checklist fechar.

⚠️ **O modelo tem uma guarda que os outros nao precisam.** `joblib.load`
desserializa via `pickle`, que executa codigo durante a leitura. Nao e problema
para um arquivo que o proprio projeto gerou; e problema serio para um vindo de
fora. Por isso o carregamento le os metadados em JSON **primeiro**, confere a
assinatura do projeto e a versao do `scikit-learn`, e recusa o que nao
reconhece — ver `backend/ml/persistencia.py`.

A conferencia de versao nao e paranoia: o pickle de um `Pipeline` nao tem
compatibilidade garantida entre versoes do sklearn, e **a falha e silenciosa**.
O objeto carrega e preve errado.

### O que o artefato do modelo carrega junto

Um `.joblib` sozinho e opaco: ninguem responde "treinado com quais colunas,
sobre quantas amostras, quando" sem abrir o pickle — e abrir e justamente o que
se quer evitar antes de saber o que e. Entao ao lado vai um JSON legivel:

```json
{
  "assinatura": "coral-brasil/ml",
  "modelo": "logistica",
  "calibracao": "isotonic",
  "colunas": ["sst_variacao_7d", "dhw_variacao_7d",
              "salinidade_variacao_7d", "oxigenio_variacao_7d"],
  "alvo": "baa >= 3.0 em t+7",
  "n_treino": 7095,
  "positivos_treino": 596,
  "sklearn": "1.8.0"
}
```

O campo `calibracao` existe por um motivo medido: sem recalibracao o modelo
promete **0,165** onde a taxa real e **0,084**. Um artefato que nao declarasse
se a probabilidade e crua ou corrigida seria inutilizavel para o painel — a
diferenca vale 0,081 de ECE. Ver [RESULTADOS.md](RESULTADOS.md) §22.

---

## Fonte oficial do schema Neo4j

Arquivo oficial:
- `backend/aquaculture/neo4j_schema.py`

Comandos oficiais:
- `python backend/manage.py neo4j_init` — cria as constraints
- `python backend/manage.py neo4j_projetar` — reconstroi o grafo a partir do
  PostgreSQL e confere item a item

🚨 **`neo4j_seed` e `db/setup_graph.py` nao existem mais** (removidos em
28/07/2026), e este bloco mandava rodar o primeiro ate 31/07/2026. Documentacao
que instrui a executar um comando removido e pior que documentacao ausente:
quem segue recebe um erro e nao sabe se errou ou se o projeto esta quebrado. Ha
teste que falha se um bloco de codigo de qualquer documento citar um comando
inexistente.

⚠️ O `neo4j_schema.py` **so declara nomes e constraints**. A camada de escrita
que existia nele — quatro consultas `UPSERT_*` e oito funcoes, chamadas apenas
pelos proprios testes — saiu em 30/07/2026 junto com o `StatusPredicao`.

## Schema canonico adotado

### Nos implementados agora

`Localizacao`
- id canonico: `slug`
- origem atual: `LocalRecife`
- propriedades principais: `id`, `slug`, `nome`, `estado`, `cidade`, `descricao`, `ultima_atualizacao`, `ativo`, `origem_registro`, `django_pk`

`Especie`
- id canonico: `slugify(nome_cientifico)`
- origem atual: `Especie`
- propriedades principais: `id`, `nome_cientifico`, `nome_comum`, `tipo`, `descricao`, `iucn_categoria`, `iucn_categoria_rotulo`, `iucn_avaliado_em`, `iucn_versao`, `fonte_iucn_url`, `iucn_tem_procedencia`, `aphia_id`, `credito_imagem`, `fonte_imagem_url`, `fonte_url`
  - ⚠️ **Esta lista descrevia a intencao, nao o que `projetar_especies` gravava, ate 08/08/2026.** `tipo`, `descricao`, `credito_imagem`, `fonte_imagem_url`, `fonte_url` e os campos de proveniencia IUCN nunca eram escritos — so `nome_cientifico`, `nome_comum`, `iucn_categoria`, `iucn_avaliado_em` e `aphia_id` chegavam ao no. Corrigido; ver Historico de decisoes.

`MedicaoAmbiental`
- id canonico: `slug:data:variavel:fonte` — 🚨 o antigo era `slug:data`, herdado de quando uma linha era um dia inteiro; ele colidiria oito vezes por dia e o `MERGE` sobrescreveria em silencio. Ver `db/projecao.py`
- origem atual: **`MedicaoAmbiental` do PostgreSQL**, via `neo4j_projetar`
- propriedades principais: `id`, `local_slug`, `data`, `variavel`, `valor`, `unidade`, `fonte`, `dataset_id`, `quality_flag`, `observacao`

`Predicao`
- id canonico: `localizacao_slug:data_iso:modelo_slug`
- origem atual: **nenhuma** — o modelo atual nao grava saida em lugar nenhum. Ver PLANEJAMENTO fase 4.4
- propriedades principais: `id`, `localizacao_id`, `local_slug`, `data`, `modelo_slug`, `medicao_id`, `fonte_dados_id`

`FonteDados`
- id canonico: `fonte_slug:versao`
- origem atual: as fontes reais de ingestao (`noaa_crw`, `copernicus`, …)
- propriedades principais: `id`, `slug`, `nome`, `tipo`, `descricao`, `versao`, `pipeline`, `status`

### Relacoes implementadas agora

- `(:Localizacao)-[:ABRIGA_ESPECIE]->(:Especie)`
- `(:Localizacao)-[:TEM_MEDICAO]->(:MedicaoAmbiental)`
- `(:Localizacao)-[:TEM_PREDICAO]->(:Predicao)`
- `(:Predicao)-[:DERIVADA_DE]->(:MedicaoAmbiental)`
- `(:MedicaoAmbiental)-[:PROVENIENTE_DE]->(:FonteDados)`
- `(:Predicao)-[:PROVENIENTE_DE]->(:FonteDados)`

### Constraints oficiais

- `Localizacao.id` unico
- `Localizacao.slug` unico
- `Especie.id` unico
- `Especie.nome_cientifico` unico
- `MedicaoAmbiental.id` unico
- `Predicao.id` unico
- `FonteDados.id` unico

## Mapeamento do Django para o grafo

### Ja implementado

- `LocalRecife` alimenta `Localizacao`
- `Especie` alimenta `Especie`
- `MedicaoAmbiental` do PostgreSQL alimenta `MedicaoAmbiental` no grafo

⚠️ **Corrigido em 30/07/2026.** Esta secao dizia que `StatusPredicao` era
dividido em `MedicaoAmbiental` + `Predicao`, e as tres entradas acima diziam
"origem atual: derivada de `StatusPredicao`". Isso descrevia o `neo4j_seed`,
substituido em 27/07 — e a propria secao seguinte ja dizia isso, na mesma
pagina. O modelo `StatusPredicao` foi removido do Django em 30/07/2026
([FONTES.md](FONTES.md) §6.21).

### Mantido por compatibilidade

- os endpoints atuais do Django nao foram alterados;
- `neo4j_service.py` consulta o novo schema, mas devolve o mesmo formato esperado pelos endpoints de grafo ja existentes;
- `slug` continua sendo a chave publica usada nas URLs, embora o no tenha `id` canonico explicito.

## ✅ A projecao, executada em 27/07/2026

O grafo deixou de estar atrasado. `manage.py neo4j_projetar` reconstroi o Neo4j
a partir do PostgreSQL, e **substitui** o `neo4j_seed` — nao o estende. Aquele
derivava os nos de `StatusPredicao`, o modelo legado com **3 registros**, o
mesmo caminho que produziu os defeitos de [FONTES.md](FONTES.md) §6.

| | Postgres | Neo4j |
|---|---|---|
| `Localizacao` | 3 | 3 ✅ |
| `Especie` | 9 | 9 ✅ |
| `FonteDados` | 5 | 5 ✅ |
| `MedicaoAmbiental` | **57.420** | **57.420** ✅ |
| `TEM_MEDICAO` | 57.420 | 57.420 ✅ |
| `PROVENIENTE_DE` | 57.420 | 57.420 ✅ |

**172.286 elementos em 16 segundos**, conferidos item a item.

### A escolha de escopo, agora medida

Este documento exigia *"medir antes de projetar, e nao descobrir o limite quando
estourar"*. Medido:

| Opcao | Elementos | Proveniencia por valor? |
|---|---|---|
| **A. um no por (local, data, variavel, fonte)** | **172.277** | ✅ **sim** |
| B. um no por (local, data) | 21.590 | ❌ nao |
| C. agregado mensal | 5.705 | ❌ nao |

**Adotada a A.** As opcoes B e C sao 8× e 30× menores, e **as duas destroem a
razao de o grafo existir**: um no que junta a SST do NOAA com a salinidade do
Copernicus so pode apontar para uma fonte. Proveniencia por valor e a
contribuicao central do projeto ([VISAO_GERAL.md](VISAO_GERAL.md) §8); um grafo
que a perde nao vale o que economiza.

⚠️ **O temor deste documento nao se confirmou.** O texto dizia que passar de
100 mil elementos era problema — mas a instancia real e **Neo4j 5.26
Community**, que nao tem teto de nos. O limite de 34 mil nos era do **Neo4j
3.x**, e ficou obsoleto. 172 mil elementos e volume pequeno, crescendo **72 por
dia** (24 medicoes × 3 elementos).

### 🚨 O id canonico da medicao mudou, e a mudanca era obrigatoria

O schema anterior usava `localizacao_slug:data_iso`, herdado de
`StatusPredicao`, onde **uma linha era um dia**.

Em `MedicaoAmbiental` uma linha e **uma variavel, de uma fonte, num dia** —
oito por local por dia. Com o id antigo, o `MERGE` casaria as oito no mesmo no e
**sobrescreveria sete, sem erro nenhum**. O grafo pareceria completo e teria
1/8 do dado.

```
antes:  abrolhos-ba:2026-07-24
agora:  abrolhos-ba:2026-07-24:sst:noaa_crw
```

E exatamente a constraint de unicidade que o PostgreSQL ja usa
(`local_recife, data, variavel, fonte`). Ha teste travando a decisao.

### O que o grafo passou a responder

A pergunta que justifica sua existencia, agora em uma travessia:

```cypher
MATCH (l:Localizacao {slug:"abrolhos-ba"})-[:TEM_MEDICAO]->(m:MedicaoAmbiental)
      -[:PROVENIENTE_DE]->(f:FonteDados)
WHERE m.data = "2026-07-24"
RETURN m.variavel, m.valor, f.id
```

| variavel | valor | fonte |
|---|---|---|
| `sst` | 25,005 °C | `noaa_crw:dhw_5km` |
| `dhw` | 0,000 | `noaa_crw:dhw_5km` |
| `salinidade` | 37,406 PSU | `copernicus:cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m` |
| `oxigenio` | 209,072 mmol·m⁻³ | `copernicus:cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m` |

**E a emenda entre produtos ficou auditavel numa consulta so** — que era um
dos objetivos declarados e nunca tinha sido demonstrado:

| variavel | n | periodo | dataset |
|---|---|---|---|
| `oxigenio` | 7.029 | 2020-01-01 → 2026-05-31 | `bgc_my` *(reanalise)* |
| `oxigenio` | 162 | **2026-06-01** → 2026-07-24 | `bgc-bio_anfc` *(analise)* |
| `salinidade` | 7.098 | 2020-01-01 → 2026-06-23 | `phy_my` *(reanalise)* |
| `salinidade` | 93 | **2026-06-24** → 2026-07-24 | `phy-so_anfc` *(analise)* |

Em SQL isso exige varios JOINs sobre a tabela longa; aqui e uma travessia. **E
a primeira demonstracao concreta de que o grafo ganha de fato** — ate hoje o
argumento era so teorico.

### Duas guardas que o codigo tem, e por que

**1. `limpar` filtra por `origem_registro`.** Um `MATCH (n) DETACH DELETE n`
levaria junto qualquer no criado a mao para experimento. A projecao **nao tem
autoridade sobre o que nao produziu**. E vai em lotes: uma transacao unica com
172 mil elementos estoura a memoria da instancia.

**2. `--conferir` compara com o Postgres, item a item.** Uma projecao que falha
no meio deixa o grafo **parcial e silencioso**, e a consulta seguinte responde
com dado incompleto sem avisar. O comando roda a conferencia sozinho ao
terminar. **Projetar sem conferir nao vale.**

### Um defeito real, achado por teste

Ao escrever os testes, um caso quebrou: a lista de linhas passada ao driver era
**a mesma** que o `clear()` seguinte esvaziava.

Com o driver real isso passa despercebido — a consulta ja executou. Mas
qualquer coisa que guarde o parametro (uma retentativa, um log, um duble de
teste) fica com uma lista vazia. A projecao gravava 57.420 linhas e o parametro
registrado aparecia **vazio**.

Corrigido com uma copia explicita, e comentado no ponto.

---

## ✅ O `painel-risco`, construido em 27/07/2026

Os nove endpoints anteriores **entregam dado guardado**. Nenhum faz conta.
O `painel-risco` e o primeiro que carrega o modelo e responde uma probabilidade,
e por isso e o unico ponto do sistema onde o artefato do modelo, a serie do
PostgreSQL e o limiar declarado se encontram.

Verificado ao vivo contra o PostgreSQL: os tres recifes respondem com
`data_base` 24/07/2026, alvo 31/07, atraso de 3 dias. 54 testes.

```
GET /api/painel-risco/            lista os locais que o modelo viu
GET /api/painel-risco/<slug>/     um recife; 404 com motivo se ele nao treinou
```

### O contrato ja esta fixado — pelo proprio artefato

Nada aqui e escolha de quem escrever a view. O `dados/modelos/entrega1_baa.json`
gravado por `treinar_final` **ja declara** o que a view tem de montar:

| Campo do metadado | Valor | O que obriga na view |
|---|---|---|
| `colunas` | `sst_variacao_7d`, `dhw_variacao_7d`, `salinidade_variacao_7d`, `oxigenio_variacao_7d` | as quatro janelas, nesta ordem |
| `horizonte_dias` | 7 | a resposta e sobre t+7, nao sobre hoje |
| `alvo` | `baa >= 3.0 em t+7` | e **estresse termico**, nao branqueamento observado |
| `calibracao` | `isotonic` | a probabilidade sai recalibrada, e nao crua |
| `locais` | `abrolhos-ba`, `picaozinho-pb`, `porto-de-galinhas-pe` | tres, e so tres |

⚠️ **A janela precisa ser calculada exatamente como no treino.** Se a view
recomputar `sst_variacao_7d` com outra convencao — outro sinal, outro numero de
dias, outra forma de tratar dia faltante — o modelo recebe uma coluna que **tem
o nome certo e o conteudo errado**, e responde com aparente normalidade. Nao ha
erro que apareca: o `Pipeline` aceita qualquer matriz com quatro colunas. A
unica defesa e a view e o treino chamarem **o mesmo codigo**, e nao duas
implementacoes que se parecem.

### Tres decisoes, e o motivo de cada uma

**1. Recusar em vez de chutar.** Faltando dia na janela de 7, o endpoint
responde "sem dado suficiente" — nao preenche com zero, nao interpola, nao
encurta a janela em silencio.

E o mesmo defeito que o pipeline legado tinha e que os testes de
`/api/medicoes/` ja protegem: `.fillna(0)` gravava pH 0 e salinidade 0, valores
fisicamente impossiveis, que passavam adiante como medicao. Aqui o efeito seria
pior, porque **zero e um valor legitimo para uma variacao**: `sst_variacao_7d =
0` quer dizer "a temperatura nao mudou", que e uma afirmacao. Preencher lacuna
com zero nao produz um numero suspeito — produz a afirmacao mais tranquilizadora
possivel, exatamente quando o dado sumiu.

**2. A resposta carrega a data-base.** Todo retorno diz sobre que dia a conta
foi feita. A serie do Copernicus tem latencia; a do NOAA tambem. Um risco sem
data e um numero sem validade, e quem le assume "agora" — que e justamente o que
ele nao e.

**3. Local fora do treino e 404, com o motivo.** Pedir Fernando de Noronha
devolve "modelo nao treinado neste local", e nao uma extrapolacao. O modelo viu
tres pontos do litoral brasileiro; responder sobre um quarto seria inventar
cobertura que a [RESULTADOS.md](RESULTADOS.md) nao sustenta.

### O limiar tem de ser declarado no payload

A recalibracao isotonica moveu o corte: o ponto equivalente ao antigo 0,50 fica
em **0,20** no modelo calibrado ([RESULTADOS.md](RESULTADOS.md) §22). Nao ha
limiar "natural" — e decisao de produto sobre quanto alarme falso se aceita para
nao perder evento.

Por isso o endpoint devolve **a probabilidade e o limiar usado**, lado a lado, e
nao apenas um rotulo "alto/baixo". Quem consome precisa poder discordar do corte
sem precisar refazer a conta.

O limiar mora em `settings.PAINEL_LIMIAR`, e nao no codigo do modelo — subir o
numero troca alarme falso por evento perdido, e essa troca e de quem opera o
site.

### O que a execucao ensinou, e que o contrato nao previa

**1. 🚨 A probabilidade e uma escada, e a escada toca 0 e 1.** Os tres recifes
voltaram com **exatamente 0,0029**, apesar de entradas diferentes. Nao e
defeito: a recalibracao isotonica e funcao escada por construcao, e as
probabilidades cruas 0,083 e 0,066 caem no mesmo degrau. Medido sobre o treino:
313 valores distintos em 7.095 amostras, **864 (12,2%) em `p = 0,000` exato**.

Isso e problema de comunicacao, nao de estatistica. `p = 0` afirma "nenhum
alerta neste degrau", nao "impossivel" — e um painel publico que exibe **"0% de
risco"** traduz um degrau finito em impossibilidade. A API sinaliza com
`no_extremo: true` e **nao corta** o numero para 0,001: falsificar na direcao
oposta inventaria precisao inexistente e esconderia da interface exatamente o
que ela precisa para decidir como exibir. Ver [RESULTADOS.md](RESULTADOS.md)
secao 22.8.

**2. Serie que acaba mais cedo nao e a mesma coisa que serie furada.** A
distincao so apareceu quando um teste escrito como "recife sem dado nao derruba
os outros" passou onde deveria falhar — e estava certo o codigo, nao o teste:

| Estado | Resposta | Por que |
|---|---|---|
| a serie acaba em `t-2` | responde, `data_base = t-2`, atraso 2 | indistinguivel de "a ingestao de hoje ainda nao rodou" |
| a serie vai ate `t` mas falta `t-7` | **recusa** | e um buraco no meio do que ja foi coletado |

O primeiro caso e operacao normal com atraso declarado; o segundo nao tem
numero honesto a dar. Sem essa separacao, ou o painel recusaria toda vez que a
ingestao atrasasse um dia, ou aceitaria janela furada.

🚨 **Faltava um terceiro estado, e ele era o mais comum de todos — corrigido em
30/07/2026.** A tabela acima trata a serie como se ela terminasse num dia so.
Ela nao termina: sao duas fontes com latencias diferentes, e a borda e sempre
irregular. O CoralTemp da NOAA publica com 1 a 3 dias de atraso; a analise do
Copernicus vai ate ontem. Como a data-base era `max()` sobre a serie inteira,
ela caia na ponta do Copernicus, `sst` e `dhw` ainda nao tinham chegado ali, e
a janela **nunca fechava**.

Medido em duas maquinas independentes, com bancos e ingestoes separadas:

| Quando | Copernicus | NOAA | Painel |
|---|---|---|---|
| 29/07/2026 | ate 27/07 | ate 24/07 | `disponivel: false` nos 3 recifes |
| 30/07/2026 | ate 29/07 | ate 28/07 | `disponivel: false` nos 3 recifes |

Nao era um recife com problema: era o painel inteiro escuro na maior parte dos
dias, **por um dado que nem entrava na conta daquele dia**. E o pior e que a
resposta parecia correta — cada item trazia o motivo certo, dizendo exatamente
qual dia faltava. O defeito nao estava no diagnostico, estava na pergunta.

| Estado | Agora | Por que |
|---|---|---|
| **borda irregular** — cada fonte com sua latencia | responde na ultima data em que **todas** as variaveis existem, com `limitado_por` | e o formato normal de uma serie multi-fonte |
| **buraco no meio** — falta um dia dentro da janela | **recusa**, como sempre | continua sendo defeito |

⚠️ **A correcao nao e "andar para tras ate achar um dia que funcione"** — isso
mascararia ingestao parada como operacao normal, que era a razao original da
regra e continua valendo. A janela ainda precisa fechar **na** data escolhida;
so a borda direita mudou de lugar.

⚠️ **E a troca nao sai de graca.** Uma fonte que quebre de vez deixa de
bloquear o painel e passa a apenas atrasa-lo — o sintoma mais silencioso dos
dois. Por isso a resposta ganhou **`limitado_por`**: as variaveis cuja serie
para exatamente na data-base enquanto as outras seguem adiante. O
`dias_de_atraso` diz ha quanto tempo; o `limitado_por` diz por causa de quem, e
sem ele nao haveria como distinguir "a NOAA publica com atraso" de "o conector
da NOAA parou de funcionar" sem cruzar `/api/medicoes/` variavel a variavel.

**3. O `Ajuste` voltava do disco sem a calibracao.** Defeito real achado ao
montar o payload: `persistencia.carregar` nao repassava o campo, entao o
artefato isotonico se apresentava como `calibracao: None`. O pipeline carregado
estava certo — quem mentia era o metadado, e ele e justamente o que o painel
exibe para dizer se a probabilidade e crua ou recalibrada.

**4. O artefato e lido uma vez, com cache invalidado por mtime.** `joblib.load`
a cada visita seria desserializar o pickle por requisicao. ⚠️ O cache **nao** e
por tempo: um TTL continuaria servindo o modelo antigo por N minutos depois de
`treinar_final`, sem nada indicando isso.

## O que ainda nao esta materializado

- **`Predicao` nao entra ainda.** O modelo atual
  ([RESULTADOS.md](RESULTADOS.md) §22) calcula na requisicao e **nao grava
  saida em lugar nenhum**: o alerta que o site mostra evapora quando a resposta
  e enviada. **Primeiro decidir onde a predicao e persistida**, depois projetar.
  Ate 30/07/2026 havia aqui um `StatusPredicao` com 3 registros de
  demonstracao, e projeta-lo teria sido repetir o erro que `neo4j_projetar` veio
  corrigir; o modelo foi removido, e a pendencia continua igual.
- **`(:Predicao)-[:DERIVADA_DE]->(:MedicaoAmbiental)`** depende do item acima —
  e e justamente a travessia de proveniencia completa que o documento cita como
  ganho principal do grafo. Metade dela ja existe.
- **Relacao direta entre `Predicao` e `Especie`**, quando houver modelo
  realmente especie-especifico.

✅ **A projecao ja tem passo de deploy** desde 28/07/2026: ela continua sendo
artefato derivado, como o `.docx` e o `.joblib`, mas `manage.py preparar_deploy`
reconstroi os tres em ordem e para no primeiro erro.

### Ja materializado

- ingestao NOAA/CRW e Copernicus escrevendo em `MedicaoAmbiental` no
  PostgreSQL, com proveniencia por valor (`fonte`, `dataset_id`,
  `quality_flag`, `data_coleta`) — concluida em 25/07/2026;
- PostgreSQL como fonte unica, com os dois bancos subindo por
  `docker-compose.yml`.

## Regras operacionais

- sem `neo4j_init`, nao existe garantia de constraints validas;
- sem `neo4j_projetar`, o grafo nao reflete o estado atual do PostgreSQL;
- toda alteracao estrutural no grafo deve partir de `backend/aquaculture/neo4j_schema.py` antes de tocar comandos, servico ou documentacao;
- **nenhuma rotina escreve no Neo4j sem passar pelo PostgreSQL antes.** Um dado que exista so no grafo e um dado sem proveniencia e sem backup — se aparecer um, e defeito, nao funcionalidade.

## Historico de decisoes

| Data | Decisao |
|---|---|
| 08/08/2026 | 🚨 **`projetar_especies` nunca gravava a proveniencia que a leitura precisava, e a leitura ainda pedia um campo removido.** Achado ao revisar `neo4j_service.py`: a query da modal de especie da pagina do recife (`/api/grafo/localizacoes/<slug>/`) lia `e.status_conservacao`, campo removido do modelo Django pela migracao `0022` em 31/07/2026 (docs/FONTES.md secao 2.4). Mas o defeito de fundo era maior que o nome do campo — `projetar_especies` so escrevia `nome_cientifico`, `nome_comum`, `iucn_categoria`, `iucn_avaliado_em` e `aphia_id`; `tipo`, `descricao`, `credito_imagem`, `fonte_imagem_url`, `fonte_url` e os campos de proveniencia da IUCN nunca chegavam ao no. Resultado: toda especie exibida pela modal via grafo saia como "sem procedencia registrada" e sem link de fonte, **mesmo tendo categoria e ano cadastrados no Postgres** — o mesmo problema que a migracao `0022` fechou do lado relacional, reaberto do lado do grafo. Corrigido gravando os campos ja derivados pelo Django (`Especie.iucn_tem_procedencia`, `get_iucn_categoria_display()`) em vez de recalcula-los em Cypher — mesmo principio do `EspecieSerializer`, que existe para nao deixar cada consumidor reinventar a regra. O `MERGE` tambem passou a `REMOVE n.status_conservacao`: `SET n += linha` so soma ou sobrescreve chaves, nunca apaga uma que sumiu do dicionario novo, entao um no projetado antes desta correcao ficaria com a propriedade orfa para sempre. 4 testes novos em `db/testes_projecao.py` (754 no total). |
| 27/07/2026 | ✅ **`painel-risco` construido — o primeiro endpoint que faz conta.** Os tres recifes respondem contra o PostgreSQL real, com data-base, atraso, entradas e limiar no payload. 54 testes. Quatro coisas que a execucao ensinou e o contrato nao previa. A mais seria: 🚨 **a probabilidade calibrada e uma escada que toca 0 e 1** — os tres recifes voltaram com o mesmo 0,0029 apesar de entradas diferentes, e 12,2% das amostras de treino saem em `p = 0,000` exato. Exibir "0% de risco" traduziria um degrau finito em impossibilidade; a API sinaliza com `no_extremo` e **nao falsifica o numero** para 0,001. Segunda: **serie que acaba mais cedo nao e serie furada** — a primeira responde com atraso declarado, a segunda recusa, e sem essa separacao o painel recusaria toda vez que a ingestao atrasasse um dia. Terceira: defeito real corrigido — `persistencia.carregar` devolvia `calibracao: None` para artefato isotonico. Quarta: cache do artefato invalidado por **mtime** e nao por TTL, que continuaria servindo o modelo antigo depois do retreino. |
| 27/07/2026 | **Contrato do `painel-risco` fixado antes de escrever a view.** A decisao que importa: **o contrato nao e escolha de quem implementa** — o `entrega1_baa.json` gravado por `treinar_final` ja declara as quatro colunas, o horizonte de 7 dias, o alvo `baa >= 3` e os tres locais. A view obedece ao artefato. Registrado o risco silencioso associado: recomputar a janela com outra convencao produz uma coluna com **o nome certo e o conteudo errado**, e o `Pipeline` aceita sem erro; a defesa e view e treino chamarem o mesmo codigo. Tres decisoes tomadas: recusar em vez de preencher lacuna (zero e valor legitimo de variacao, entao preencher com zero devolve a afirmacao mais tranquilizadora possivel justo quando o dado sumiu), data-base sempre no payload, e local fora do treino como 404 com motivo. O **limiar vai no payload junto da probabilidade** — a recalibracao moveu o corte de 0,50 para 0,20, e quem consome precisa poder discordar sem refazer a conta. |
| 27/07/2026 | ✅ **Projecao executada — o grafo deixou de estar atrasado.** `manage.py neo4j_projetar` substitui o `neo4j_seed`, que derivava de `StatusPredicao` (3 registros do caminho legado). Projetados **57.420 medicoes, 5 fontes, 9 especies e 3 locais — 172.286 elementos em 16 s**, conferidos item a item contra o PostgreSQL. **Escopo medido antes de escrever**, como este documento exigia: as tres opcoes custam 172 mil, 21 mil e 5 mil elementos, e as duas menores **destroem a proveniencia por valor** — um no que junta SST do NOAA com salinidade do Copernicus so aponta para uma fonte. O temor de volume nao se confirmou: o teto de nos era do **Neo4j 3.x**, e a instancia e 5.26 Community, sem teto. 🚨 **O id canonico da medicao mudou** de `slug:data` para `slug:data:variavel:fonte` — com o antigo, o `MERGE` sobrescreveria sete das oito variaveis do dia **sem erro nenhum**. Demonstrado pela primeira vez o ganho concreto do grafo: a emenda reanalise→analise fica auditavel numa consulta so. Um defeito real foi achado por teste — a lista passada ao driver era a mesma que o `clear()` esvaziava. |
| 25/07/2026 | **Migracao concluida: SQLite → PostgreSQL.** 57.463 objetos importados via `dumpdata`/`loaddata`, incluindo as 57.420 medicoes (43.038 NOAA + 14.382 Copernicus), 3 locais, 9 especies, 18 execucoes de ingestao e 9 datasets. Contagens e distribuicao do BAA identicas as do SQLite. 181 testes passam contra o PostgreSQL. O `db.sqlite3` fica no disco como backup e deixa de ser lido. |
| 25/07/2026 | **Infraestrutura por Docker Compose.** PostgreSQL e Neo4j sobem de `docker-compose.yml` na raiz, em versoes fixas (`postgres:17-alpine`, `neo4j:5-community`), com volumes nomeados e *healthcheck*. Nao ha Dockerfile: as duas imagens sao oficiais, e escrever uma propria seria reconstruir o que ja existe. **O Django fica fora do container** de proposito — em desenvolvimento o `manage.py` roda dezenas de vezes por sessao e cada uma custaria um rebuild. Registrado tambem o que o Docker **nao** resolve: os volumes sao locais, entao duas maquinas continuam com dados separados; o que ele iguala e versao e configuracao. |
| 25/07/2026 | **Tres camadas com fonte unica de escrita.** PostgreSQL como fonte da verdade, treino em pandas a partir dele, Neo4j como projecao derivada e reconstruivel. Substitui a descricao anterior, que tratava Postgres e Neo4j como par transacional — inviavel sem transacao distribuida. Registrado tambem por que o treino nao le do grafo: "relacao entre variaveis" e correlacao estatistica sobre tabela, nao travessia de entidades, e `sklearn` consome matriz. |
