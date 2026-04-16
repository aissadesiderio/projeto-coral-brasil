# Documento de Arquitetura

## Escopo
Este documento define a separação de responsabilidades entre os bancos, os padrões de execução local e os critérios de dependência entre fases do pipeline de dados e modelagem.

## Responsabilidades por banco de dados

### PostgreSQL (sistema transacional)
Responsável por dados com integridade relacional e operação da aplicação:
- **Autenticação e administração** (usuários, grupos, permissões e recursos de admin).
- **Dados relacionais de suporte** (cadastros, tabelas de referência, metadados operacionais e configurações).
- **Fonte primária** para entidades que exigem constraints relacionais e histórico transacional.

### Neo4j (grafo científico)
Responsável por modelar relações científicas e consultas de travessia/impacto:
- Nós canônicos de domínio:
  - `Localizacao`
  - `MedicaoAmbiental`
  - `Predicao`
  - `Especie`
  - `FonteDados`
- **Fonte primária** para relacionamentos científicos e exploração de contexto (ex.: influência de medições por localização, espécie e fonte).

## Padrão de execução local

### 1) URI e credenciais via `.env`
Todas as conexões locais devem ser parametrizadas por variáveis de ambiente.

Exemplo mínimo de variáveis:

```dotenv
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=coral
POSTGRES_USER=coral_user
POSTGRES_PASSWORD=coral_pass

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j_pass
```

Diretrizes:
- Nunca versionar `.env` com credenciais reais.
- Manter `.env.example` atualizado com todas as chaves obrigatórias.
- Falta de variável obrigatória deve falhar rápido no bootstrap local.

### 2) Política de dados de desenvolvimento (seed mínimo)
O ambiente de desenvolvimento deve iniciar com **seed mínimo e determinístico** para validação funcional ponta a ponta.

Conteúdo mínimo obrigatório:
- PostgreSQL:
  - 1 usuário administrador.
  - registros essenciais de referência para o app iniciar sem erro.
- Neo4j:
  - ao menos 1 `Localizacao`.
  - ao menos 1 `Especie`.
  - ao menos 1 `MedicaoAmbiental` ligada a uma `Localizacao`.
  - ao menos 1 `Predicao` ligada a `Localizacao` e `Especie`.
  - ao menos 1 `FonteDados` ligada à `Predicao`.

### 3) Convenção de IDs canônicos por nó (Neo4j)
Cada nó deve possuir um `id` canônico, estável e derivado de atributos de negócio, para evitar duplicidade de ingestão.

Regras:
- Normalizar componentes para `slug` em minúsculas.
- Usar datas em formato ISO (`YYYY-MM-DD` ou `YYYY-MM-DDTHH:mm:ssZ`).
- Compor IDs com separador `:`.

Padrões:
- `Localizacao.id = localizacao_slug`
- `MedicaoAmbiental.id = localizacao_slug:data_iso`
- `Predicao.id = localizacao_slug:data_iso:modelo_slug`
- `Especie.id = nome_cientifico_slug`
- `FonteDados.id = fonte_slug:versao`

## Dependências de fase

### Gate 1 — Qualidade estrutural
- **Sem schema validado, não iniciar limpeza/mapeamento.**
- Validação mínima:
  - constraints/chaves obrigatórias definidas,
  - tipos e formatos de campos críticos validados,
  - contrato entre origem e destino documentado.

### Gate 2 — Estabilidade operacional
- **Sem ingestão estável, não iniciar treino de modelo.**
- Estabilidade mínima:
  - ingestão executa sem falhas recorrentes por janela acordada,
  - volume e completude de dados atingem limiar mínimo,
  - monitoramento básico (logs e contagem de registros) ativo.
