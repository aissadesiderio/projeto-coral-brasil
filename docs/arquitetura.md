# Documento de Arquitetura

## Escopo
Este documento registra a divisao de responsabilidades entre PostgreSQL, o treino do modelo e o Neo4j, e fixa o schema canonico do grafo usado pelo backend.

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

| No | Entra no grafo? | Volume |
|---|---|---|
| `Localizacao`, `Especie`, `FonteDados` | ✅ sim | dezenas |
| `Predicao` | ✅ sim | centenas |
| Agregado mensal por local/variavel | ✅ sim | centenas |
| `MedicaoAmbiental` diaria | ⚠️ a medir | 57.420 e crescendo |

A medicao diaria como no depende do limite da instancia Neo4j em uso — com as relacoes de proveniencia, passa de 100 mil elementos. **Medir antes de projetar**, e nao descobrir o limite quando estourar. O agregado mensal cobre a consulta comparativa sem esse custo.

---

## Responsabilidades por banco

### PostgreSQL — fonte unica da verdade
- autenticacao, admin e configuracoes operacionais;
- `LocalRecife`, `Especie`, `StatusPredicao`, `MedicaoAmbiental`, `ExecucaoIngestao` e `DatasetCatalogo`;
- integridade relacional e operacao normal dos endpoints REST;
- **origem de tudo o que o modelo treina** e de tudo o que o grafo projeta.

### Neo4j — projecao derivada
Um unico schema canonico para consultas de grafo e travessia:
- exploracao de `Localizacao`, `Especie`, `MedicaoAmbiental`, `Predicao` e `FonteDados`;
- leitura agregada para endpoints de grafo;
- **nunca recebe escrita que nao venha do PostgreSQL.**

## Fonte oficial do schema Neo4j

Arquivo oficial:
- `backend/aquaculture/neo4j_schema.py`

Comandos oficiais:
- `python backend/manage.py neo4j_init`
- `python backend/manage.py neo4j_seed`

Compatibilidade legada:
- `backend/db/setup_graph.py` nao define schema proprio.
- Esse arquivo apenas delega para `neo4j_init` + `neo4j_seed`.

## Schema canonico adotado

### Nos implementados agora

`Localizacao`
- id canonico: `slug`
- origem atual: `LocalRecife`
- propriedades principais: `id`, `slug`, `nome`, `estado`, `cidade`, `descricao`, `ultima_atualizacao`, `ativo`, `origem_registro`, `django_pk`

`Especie`
- id canonico: `slugify(nome_cientifico)`
- origem atual: `Especie`
- propriedades principais: `id`, `nome_cientifico`, `nome_comum`, `tipo`, `descricao`, `status_conservacao`, `credito_imagem`, `fonte_imagem_url`, `fonte_url`, `origem_registro`, `django_pk`

`MedicaoAmbiental`
- id canonico: `localizacao_slug:data_iso`
- origem atual: derivada de `StatusPredicao`
- propriedades principais: `id`, `localizacao_id`, `local_slug`, `data`, `fonte_dados_id`, `sst`, `limite_termico`, `anomalia_termica`, `dhw`, `vento_velocidade`, `par`, `kd490`, `salinidade`, `ph`, `oxigenio`, `nitrato`, `clorofila`, `origem_registro`, `django_pk`

`Predicao`
- id canonico: `localizacao_slug:data_iso:status-predicao-django`
- origem atual: derivada de `StatusPredicao`
- propriedades principais: `id`, `localizacao_id`, `local_slug`, `data`, `modelo_slug`, `medicao_id`, `fonte_dados_id`, `risco_integrado`, `nivel_alerta`, `origem_registro`, `django_pk`

`FonteDados`
- id canonico: `fonte_slug:versao`
- origem atual: seed tecnico do backend
- no implementado agora: `django-statuspredicao:v1`
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
- `StatusPredicao` e dividido em:
  - `MedicaoAmbiental` para variaveis ambientais
  - `Predicao` para risco e nivel de alerta

### Mantido por compatibilidade

- os endpoints atuais do Django nao foram alterados;
- `neo4j_service.py` consulta o novo schema, mas devolve o mesmo formato esperado pelos endpoints de grafo ja existentes;
- `slug` continua sendo a chave publica usada nas URLs, embora o no tenha `id` canonico explicito.

## O que ainda nao esta materializado

⚠️ **O grafo esta uma versao atrasada em relacao ao banco relacional.** O
`neo4j_seed` ainda deriva os nos de `StatusPredicao`, o modelo legado. As
57.420 medicoes reais que a ingestao gravou em `MedicaoAmbiental` no
PostgreSQL **nao estao projetadas** no Neo4j. O container sobe vazio.

Enquanto isso durar, **nenhuma consulta ao grafo reflete o dado atual** — o
que ele mostra vem do caminho antigo, com os defeitos ja documentados em
docs/FONTES.md secao 6.

Itens da proxima etapa:
- comando de projecao lendo `MedicaoAmbiental` do PostgreSQL (o `neo4j_seed`
  atual le `StatusPredicao` e precisa ser substituido, nao estendido);
- `FonteDados` para NOAA e Copernicus com proveniencia por dataset — o campo
  `dataset_id` por valor ja existe no relacional e nao tem no correspondente;
- medir se as medicoes diarias cabem como no, ou se entram so agregadas
  (ver "Escopo do que e projetado" acima);
- relacao direta entre `Predicao` e `Especie`, quando houver dado ou modelo
  realmente specie-specific;
- suporte a mais de um `modelo_slug` por local e data sem usar apenas o valor
  transicional `status-predicao-django`.

### Ja materializado

- ingestao NOAA/CRW e Copernicus escrevendo em `MedicaoAmbiental` no
  PostgreSQL, com proveniencia por valor (`fonte`, `dataset_id`,
  `quality_flag`, `data_coleta`) — concluida em 25/07/2026;
- PostgreSQL como fonte unica, com os dois bancos subindo por
  `docker-compose.yml`.

## Regras operacionais

- sem `neo4j_init`, nao existe garantia de constraints validas;
- sem `neo4j_seed`, o grafo nao reflete o estado atual do Django;
- toda alteracao estrutural no grafo deve partir de `backend/aquaculture/neo4j_schema.py` antes de tocar comandos, servico ou documentacao;
- **nenhuma rotina escreve no Neo4j sem passar pelo PostgreSQL antes.** Um dado que exista so no grafo e um dado sem proveniencia e sem backup — se aparecer um, e defeito, nao funcionalidade.

## Historico de decisoes

| Data | Decisao |
|---|---|
| 25/07/2026 | **Migracao concluida: SQLite → PostgreSQL.** 57.463 objetos importados via `dumpdata`/`loaddata`, incluindo as 57.420 medicoes (43.038 NOAA + 14.382 Copernicus), 3 locais, 9 especies, 18 execucoes de ingestao e 9 datasets. Contagens e distribuicao do BAA identicas as do SQLite. 181 testes passam contra o PostgreSQL. O `db.sqlite3` fica no disco como backup e deixa de ser lido. |
| 25/07/2026 | **Infraestrutura por Docker Compose.** PostgreSQL e Neo4j sobem de `docker-compose.yml` na raiz, em versoes fixas (`postgres:17-alpine`, `neo4j:5-community`), com volumes nomeados e *healthcheck*. Nao ha Dockerfile: as duas imagens sao oficiais, e escrever uma propria seria reconstruir o que ja existe. **O Django fica fora do container** de proposito — em desenvolvimento o `manage.py` roda dezenas de vezes por sessao e cada uma custaria um rebuild. Registrado tambem o que o Docker **nao** resolve: os volumes sao locais, entao duas maquinas continuam com dados separados; o que ele iguala e versao e configuracao. |
| 25/07/2026 | **Tres camadas com fonte unica de escrita.** PostgreSQL como fonte da verdade, treino em pandas a partir dele, Neo4j como projecao derivada e reconstruivel. Substitui a descricao anterior, que tratava Postgres e Neo4j como par transacional — inviavel sem transacao distribuida. Registrado tambem por que o treino nao le do grafo: "relacao entre variaveis" e correlacao estatistica sobre tabela, nao travessia de entidades, e `sklearn` consome matriz. |
