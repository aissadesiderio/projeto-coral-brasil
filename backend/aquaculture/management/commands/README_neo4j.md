# Neo4j commands

Esta integracao popula o Neo4j em paralelo ao banco Django atual, usando um unico schema canonico definido em `aquaculture/neo4j_schema.py`.

## Configuracao

Defina as variaveis abaixo antes de rodar os comandos:

```powershell
$env:NEO4J_URI="bolt://localhost:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="sua_senha"
```

As mesmas variaveis tambem podem ser configuradas no ambiente do servidor:

- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

## Inicializar schema

Cria as constraints oficiais do schema canonico:

```powershell
python backend/manage.py neo4j_init
```

## Popular dados

Le os dados atuais do banco Django e sincroniza:

- `LocalRecife` -> `Localizacao`
- `Especie` -> `Especie`
- `StatusPredicao` -> `MedicaoAmbiental` + `Predicao`

```powershell
python backend/manage.py neo4j_seed
```

## Bootstrap legado

O arquivo `backend/db/setup_graph.py` ainda existe apenas como atalho de compatibilidade:

```powershell
python backend/manage.py shell < backend/db/setup_graph.py
```

Ele apenas chama `neo4j_init` e `neo4j_seed`. Nao ha mais uma segunda definicao de schema nesse arquivo.
