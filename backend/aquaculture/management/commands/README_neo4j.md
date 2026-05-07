# Neo4j commands

Esta integracao popula o Neo4j em paralelo ao banco Django atual.
A API continua usando Django ORM normalmente.

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

Cria as constraints iniciais no Neo4j com `IF NOT EXISTS`:

```powershell
python backend/manage.py neo4j_init
```

## Popular dados

Le os dados atuais do banco Django e sincroniza localizacoes, especies, predicoes e relacoes:

```powershell
python backend/manage.py neo4j_seed
```

## Observacao

Nesta etapa, o Neo4j esta sendo populado em paralelo.
As views, serializers e APIs atuais continuam consultando o banco Django via ORM.
