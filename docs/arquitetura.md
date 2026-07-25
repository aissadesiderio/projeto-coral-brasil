# Documento de Arquitetura

## Escopo
Este documento registra a divisao de responsabilidades entre PostgreSQL e Neo4j e fixa o schema canonico do grafo usado pelo backend.

## Responsabilidades por banco

### PostgreSQL
Permanece como fonte primaria transacional da aplicacao:
- autenticacao, admin e configuracoes operacionais;
- `LocalRecife`, `Especie` e `StatusPredicao` como registros oficiais do Django;
- integridade relacional e operacao normal dos endpoints REST existentes.

### Neo4j
Passa a usar um unico schema canonico para consultas de grafo e travessia:
- exploracao de `Localizacao`, `Especie`, `MedicaoAmbiental`, `Predicao` e `FonteDados`;
- leitura agregada para endpoints de grafo;
- representacao de relacoes cientificas sem substituir a escrita primaria no Django nesta fase.

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

Itens planejados para a proxima etapa:
- ingestao NOAA/CRW e Copernicus escrevendo diretamente em `MedicaoAmbiental`;
- `FonteDados` adicionais para NOAA e Copernicus com proveniencia por dataset;
- relacao direta entre `Predicao` e `Especie`, quando houver dado ou modelo realmente specie-specific;
- suporte a mais de um `modelo_slug` por local e data sem usar apenas o valor transicional `status-predicao-django`.

## Regras operacionais

- sem `neo4j_init`, nao existe garantia de constraints validas;
- sem `neo4j_seed`, o grafo nao reflete o estado atual do Django;
- toda alteracao estrutural no grafo deve partir de `backend/aquaculture/neo4j_schema.py` antes de tocar comandos, servico ou documentacao.
