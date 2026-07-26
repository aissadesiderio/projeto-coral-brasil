# Planejamento de Go-Live

## Checklist obrigatório de go-live

Antes de publicar o site, **todos** os itens abaixo devem ser aprovados:

- [ ] Camada de persistência validada com constraints/índices.
  - [x] **PostgreSQL como fonte única da verdade** — migrado em 25/07/2026: 57.463 objetos vindos do SQLite, incluindo as 57.420 medições, com contagens e distribuição do BAA idênticas. Sobe por `docker-compose.yml` em versão fixa; 181 testes passam contra ele. Decisão e justificativa em [docs/arquitetura.md](docs/arquitetura.md).
  - [ ] **Neo4j como projeção derivada** — o container está de pé e vazio. Falta o comando de projeção e a validação de constraints/índices sobre o dado real. ⚠️ Este item mudou de natureza: até 25/07/2026 ele dizia "Schema Neo4j validado", quando o grafo era par transacional do Postgres. Agora é projeção reconstruível, e o critério passa a ser *reconstruir do zero a partir do Postgres e conferir*, não *validar escrita própria*.
- [x] Ingestão NOAA/Copernicus rodando localmente com logs e tratamento de falha.
  - [x] **NOAA CRW** — verificado ao vivo em 25/07/2026: 115 medições de Abrolhos (01–23/07, 5 variáveis) gravadas com proveniência por valor, `ExecucaoIngestao` registrando cada tentativa, retentativa de falha passageira, e idempotência confirmada com dado real. Validação física em [docs/FONTES.md](docs/FONTES.md) §9.
  - [x] **Copernicus** — verificado ao vivo em 25/07/2026: backfill de 14.382 medições (salinidade e oxigênio, três locais, 2020-01-01 a 2026-07-24), sem lacuna e sem valor nulo. Emenda reanálise→análise rastreável por valor via `dataset_id`, e corte que impede previsão de entrar como medição. Ver [docs/FONTES.md](docs/FONTES.md) §1.2.
- [ ] Endpoints backend estáveis: `localizacoes`, `banco-de-dados`, `painel-risco`.
- [ ] Variáveis canônicas aprovadas.
- [ ] Painel exibindo predição com dados suficientes e rastreáveis.

## Critério de aprovação

O go-live só é autorizado quando o checklist estiver **100% concluído** (todos os itens marcados como `[x]`).

## Regra de bloqueio

Se **qualquer** item do checklist falhar, o site deve permanecer **offline**.
