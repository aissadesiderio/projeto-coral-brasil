# Planejamento de Go-Live

## Checklist obrigatório de go-live

Antes de publicar o site, **todos** os itens abaixo devem ser aprovados:

- [ ] Schema Neo4j validado com constraints/índices.
- [ ] Ingestão NOAA/Copernicus rodando localmente com logs e tratamento de falha.
- [ ] Endpoints backend estáveis: `localizacoes`, `banco-de-dados`, `painel-risco`.
- [ ] Variáveis canônicas aprovadas.
- [ ] Painel exibindo predição com dados suficientes e rastreáveis.

## Critério de aprovação

O go-live só é autorizado quando o checklist estiver **100% concluído** (todos os itens marcados como `[x]`).

## Regra de bloqueio

Se **qualquer** item do checklist falhar, o site deve permanecer **offline**.
