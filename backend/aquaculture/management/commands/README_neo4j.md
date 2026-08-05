# Comandos do Neo4j

O Neo4j é **projeção derivada** do PostgreSQL, e não uma segunda fonte da
verdade. Ele pode ser destruído e reconstruído a qualquer momento; o PostgreSQL
não.

O vocabulário do grafo — rótulos, relações e constraints — está em
[`aquaculture/neo4j_schema.py`](../../neo4j_schema.py). Quem **escreve** é
[`db/projecao.py`](../../../db/projecao.py).

## Configuração

| Variável | Observação |
|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` no desenvolvimento |
| `NEO4J_USER` | 🚨 **precisa ser exatamente `neo4j`** |
| `NEO4J_PASSWORD` | sem valor padrão em produção |

🚨 **`NEO4J_USER` não é um botão.** O Neo4j Community recusa qualquer outro
nome de administrador — `Invalid admin username, it must be neo4j.` — e o
container entra em ciclo de reinício sem que nada apareça no log do Django. Por
isso o `docker-compose.yml` grava o usuário **literal** no `NEO4J_AUTH`, em vez
de interpolar a variável, e há teste que falha se alguém a reintroduzir ali.

⚠️ **Não deixe espaço no fim do valor no `.env`.** O `django-environ` lê até o
fim da linha e **não apara**; um espaço invisível já derrubou a conexão com o
PostgreSQL neste projeto. As chaves declaradas no `.env` passam por uma aparagem
explícita em `settings.py` justamente por causa disso.

## Criar o schema

Cria as constraints de unicidade, de forma idempotente:

```powershell
python backend/manage.py neo4j_init
```

## Projetar o grafo

Reconstrói o grafo **a partir do PostgreSQL** e confere o resultado item a item,
saindo com erro se algo divergir:

```powershell
python backend/manage.py neo4j_projetar
```

Só conferir, sem escrever:

```powershell
python backend/manage.py neo4j_projetar --conferir
```

| Nó | Vem de |
|---|---|
| `Localizacao` | `LocalRecife` |
| `Especie` | `Especie` |
| `MedicaoAmbiental` | `MedicaoAmbiental` — id `slug:data:variavel:fonte` |
| `FonteDados` | as fontes reais de ingestão |

`Predicao` **ainda não é materializado**: o modelo atual calcula na requisição e
não grava saída em lugar nenhum. Ver PLANEJAMENTO, fase 4.4.

## O que foi removido, e por quê

🚨 **Este documento descrevia, até 31/07/2026, três coisas que não existem mais
— e mandava executá-las.** Documentação que instrui a rodar um comando removido
é pior que documentação ausente: quem segue recebe um erro e não sabe se errou
ou se o projeto está quebrado.

| Removido | Quando | Por quê |
|---|---|---|
| `neo4j_seed` | 28/07/2026 | derivava o grafo de `StatusPredicao` — 3 registros de demonstração. Substituído por `neo4j_projetar`, que deriva do PostgreSQL |
| `db/setup_graph.py` | 28/07/2026 | só delegava para `neo4j_init` + `neo4j_seed` |
| `StatusPredicao` | 30/07/2026 | o modelo legado inteiro, migração `0021`. Com ele saiu a camada de escrita correspondente do `neo4j_schema.py` |

⚠️ **O `neo4j_seed` era o mais perigoso**, e não por estar errado — ele
funcionava. O problema era existirem **dois caminhos de escrita no mesmo
grafo**: o legado sobrescreveria a projeção com dados de abril de 2026. Há teste
que falha se o par voltar.
