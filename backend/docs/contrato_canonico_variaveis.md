# Contrato Canonico de Variaveis Ambientais

## Status
- obrigatorio para qualquer ingestao que escreva em `MedicaoAmbiental`
- valido para a sincronizacao atual do Django e para a futura pipeline NOAA/Copernicus

## Objetivo
Padronizar os nomes de variaveis ambientais que entram no grafo Neo4j para que `MedicaoAmbiental` tenha um vocabulario unico, independentemente da origem.

## Onde esse contrato entra no schema

No schema canonico:
- variaveis ambientais vivem em `(:MedicaoAmbiental)`
- risco e classificacao vivem em `(:Predicao)`
- proveniencia vive em `(:FonteDados)`

Arquivo estrutural de referencia:
- `backend/aquaculture/neo4j_schema.py`

## Implementacao atual

Nesta fase, `neo4j_seed` nao consome NOAA nem Copernicus diretamente.
Ele transforma cada registro de `StatusPredicao` do Django em:
- um no `MedicaoAmbiental` com variaveis canonicas;
- um no `Predicao` com `risco_integrado` e `nivel_alerta`;
- relacoes de proveniencia para `FonteDados {id: "django-statuspredicao:v1"}`.

## Tabela canonica

| Origem atual no Django | Propriedade canonica no Neo4j | No de destino | Observacao |
|---|---|---|---|
| `sst_atual` | `sst` | `MedicaoAmbiental` | temperatura da superficie do mar |
| `limite_termico` | `limite_termico` | `MedicaoAmbiental` | limite termico de referencia |
| `anomalia` | `anomalia_termica` | `MedicaoAmbiental` | diferenca entre `sst` e limite |
| `dhw_calculado` | `dhw` | `MedicaoAmbiental` | grau-semana de aquecimento |
| `vento_velocidade` | `vento_velocidade` | `MedicaoAmbiental` | opcional no estado atual |
| `irradiancia` | `par` | `MedicaoAmbiental` | radiacao fotossintetica |
| `turbidez` | `kd490` | `MedicaoAmbiental` | atenuacao/clareza da agua |
| `salinidade` | `salinidade` | `MedicaoAmbiental` | salinidade observada |
| `ph` | `ph` | `MedicaoAmbiental` | pH da agua |
| `oxigenio` | `oxigenio` | `MedicaoAmbiental` | oxigenio dissolvido |
| `nitrato` | `nitrato` | `MedicaoAmbiental` | nutriente dissolvido |
| `clorofila` | `clorofila` | `MedicaoAmbiental` | clorofila-a |
| `risco_integrado` | `risco_integrado` | `Predicao` | saida de risco consolidada |
| `nivel_alerta` | `nivel_alerta` | `Predicao` | classificacao de alerta |

## Regras obrigatorias

1. Nenhuma nova ingestao deve gravar variaveis ambientais fora de `MedicaoAmbiental`.
2. `Predicao` deve guardar apenas a parte preditiva e de classificacao, nao o pacote inteiro de medidas.
3. Toda origem nova deve mapear suas colunas para os nomes canonicos desta tabela antes de gravar no Neo4j.
4. Toda origem nova deve registrar `FonteDados.id` no formato `fonte_slug:versao`.

## Relacao com NOAA e Copernicus

A pipeline NOAA/Copernicus ainda nao esta implementada nesta branch, mas o contrato ja define o destino esperado:
- NOAA/CRW e Copernicus devem escrever nas mesmas propriedades canonicas de `MedicaoAmbiental`;
- a diferenca entre fontes deve ser representada em `FonteDados` e nas relacoes `PROVENIENTE_DE`;
- nao deve existir uma segunda nomenclatura paralela quando essa pipeline entrar.
