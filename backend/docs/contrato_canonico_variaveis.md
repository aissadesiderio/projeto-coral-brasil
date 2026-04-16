# Contrato Canônico de Variáveis Ambientais

> **Status:** obrigatório  
> **Escopo:** ingestão, harmonização e deduplicação de séries temporais ambientais.  
> **Regra de governança:** **nenhuma rotina de deduplicação pode ser executada sem este contrato vigente**.

## Objetivo

Padronizar nomes, unidades, conversões e regras de qualidade das variáveis vindas de NOAA/CRW e Copernicus para evitar colisão semântica, mistura de unidades e deduplicação incorreta.

## Tabela única de mapeamento (fonte → canônico)

| Nome original da fonte | Nome canônico | Unidade canônica | Regra de conversão | Regra de qualidade/flag | Decisão | Ponto de ingestão correspondente |
|---|---|---|---|---|---|---|
| `CRW_SST` (NOAA/CRW) | `sst` | `°C` | Se valor vier em Kelvin, aplicar `°C = K - 273.15`; caso já esteja em °C, manter | Flag se fora de `[-2, 45]`, nulo, ou salto diário > `5°C/dia` | **manter** | `coleta_de_dados.py` (NOAA ERDDAP) + `carregar_historico.py` (`mapa_colunas['sst']`) + `setup_graph.py` (`SST`) |
| `thetao` (Copernicus) | `sst` | `°C` | Se `thetao > 200`, assumir Kelvin e converter para °C; caso contrário manter | Mesmas flags de `sst` | **revisar** (verificar unidade por dataset antes de produção) | `carregar_historico.py` (`mapa_colunas['sst']`) |
| `CRW_DHW` / `dhw` | `dhw` | `°C·semana` | Sem conversão; se escala for diária acumulada, normalizar para °C·semana | Flag se `<0`, `>40`, nulo prolongado, ou queda brusca > `8` em 1 dia sem reset de série | **manter** | `setup_graph.py` (`DHW`) + `carregar_historico.py` (`mapa_colunas['dhw']`) |
| `CRW_HOTSPOT` | `hotspot` | `°C` | Sem conversão (anomalia térmica positiva) | Flag se `<0` (quando definido como hotspot), `>10`, ou discrepante de `sst - limite_termico` | **manter** | `setup_graph.py` (`HOTSPOT`); cálculo auxiliar em `carregar_historico.py` (`hotspot_calc`) |
| `CRW_BAA` | `baa` | `categoria` (`0`, `1`, `2`, `3`, `4`) | Mapear texto/código externo para escala ordinal padrão | Flag se valor fora da escala; se máscara de qualidade indicar inválido | **manter** | `setup_graph.py` (`BAA`) + NOAA CSV (`CRW_BAA`) |
| `CRW_SSTANOMALY` / `SST_ANOMALY` | `sst_anomalia` | `°C` | Sem conversão; alinhar sinal com `sst - climatologia` | Flag se `abs(valor) > 8` ou incoerente com `sst` | **revisar** (normalizar nomenclatura entre `SST_ANOMALY` e `CRW_SSTANOMALY`) | `setup_graph.py` (`SST_ANOMALY`) + NOAA CSV (`CRW_SSTANOMALY`) |
| `PAR`, `par`, `par_error`, `ppfd` | `par` | `µmol fótons·m⁻²·s⁻¹` | Se a fonte vier em `mol·m⁻²·dia⁻¹`, converter para `µmol·m⁻²·s⁻¹`; `par_error` só como fallback e com flag | Flag se `<0`, `>3000`, ou se origem for `par_error` (marca `quality=degradado`) | **manter** (`par_error` = **revisar**) | `setup_graph.py` (`PAR`) + `carregar_historico.py` (`mapa_colunas['irradiancia']`) |
| `KD490`, `kd`, `kd490` | `kd490` | `m⁻¹` | Sem conversão | Flag se `<0` ou `>5`; outlier por z-score mensal | **manter** | `setup_graph.py` (`KD490`) + `carregar_historico.py` (`mapa_colunas['turbidez']`) |
| `chl`, `chlor_a` | `clorofila` | `mg·m⁻³` | Sem conversão | Flag se `<0` ou `>100`; mudança > `20 mg·m⁻³/dia` | **manter** | `setup_graph.py` (`CHL`) + `coleta_de_dados.py` (`variables=['chl', ...]`) + `carregar_historico.py` |
| `o2`, `oxygen`, `dissolved_oxygen`, `do` | `oxigenio` | `mmol·m⁻³` | Se em `mg·L⁻¹`, converter para `mmol·m⁻³` por temperatura/salinidade de referência | Flag se `<0` ou supersaturação física implausível | **revisar** (unidade da fonte precisa ser registrada por dataset) | `setup_graph.py` (`O2`) + `coleta_de_dados.py` (`variables=['...','o2',...]`) + `carregar_historico.py` |
| `so`, `sal`, `sob` | `salinidade` | `PSU` | Sem conversão (assumindo Practical Salinity) | Flag se `<0` ou `>45` | **manter** | `setup_graph.py` (`SAL`) + `coleta_de_dados.py` (`variables=['...','so']`) + `carregar_historico.py` |
| `ph`, `talk` (fallback legado) | `ph` | `escala total` (adimensional) | `ph`: sem conversão; `talk` não é pH e não deve substituir sem transformação química explícita | Flag crítica se origem `talk` sem transformação documentada | **revisar** (evitar uso direto de `talk` como pH) | `carregar_historico.py` (`mapa_colunas['ph']`) |

## Regras mandatórias para deduplicação

1. **Pré-requisito obrigatório:** deduplicar apenas após mapeamento para nome canônico + unidade canônica desta tabela.  
2. Para colisões no mesmo `time`, priorizar registro com melhor `quality_flag`; em empate, manter o mais recente (`keep='last'`).  
3. Nunca deduplicar misturando variáveis semanticamente diferentes (ex.: `kd490` vs `clorofila`) mesmo que compartilhem timestamp.  
4. Toda rotina nova de deduplicação deve referenciar este contrato explicitamente.

