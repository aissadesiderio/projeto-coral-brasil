# Planejamento de Go-Live

## Checklist obrigatório de go-live

Antes de publicar o site, **todos** os itens abaixo devem ser aprovados:

- [ ] Schema Neo4j validado com constraints/índices.
- [ ] Ingestão NOAA/Copernicus rodando localmente com logs e tratamento de falha.
  - [x] **NOAA CRW** — verificado ao vivo em 25/07/2026: 115 medições de Abrolhos (01–23/07, 5 variáveis) gravadas com proveniência por valor, `ExecucaoIngestao` registrando cada tentativa, retentativa de falha passageira, e idempotência confirmada com dado real. Validação física em [docs/FONTES.md](docs/FONTES.md) §9.
  - [ ] **Copernicus** — conector ainda não escrito; exige credenciais no `.env`.
- [ ] Endpoints backend estáveis: `localizacoes`, `banco-de-dados`, `painel-risco`.
- [ ] Variáveis canônicas aprovadas.
- [ ] Painel exibindo predição com dados suficientes e rastreáveis.

## Critério de aprovação

O go-live só é autorizado quando o checklist estiver **100% concluído** (todos os itens marcados como `[x]`).

## Regra de bloqueio

Se **qualquer** item do checklist falhar, o site deve permanecer **offline**.
