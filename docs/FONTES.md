# Fontes de Dados e Referências — Projeto Coral Brasil

> **Status:** documento vivo — obrigatório manter atualizado.
> **Regra:** nenhum dado entra no projeto sem uma linha correspondente neste documento.
> **Última revisão:** 24/07/2026

Este documento registra **toda** fonte de informação usada na construção do Coral Brasil: de onde veio cada dado, como foi obtido, onde é usado no código, sob qual licença e como deve ser citado. Serve tanto para reprodutibilidade acadêmica quanto para atribuição legal.

---

## Índice

1. [Fontes de dados ambientais](#1-fontes-de-dados-ambientais)
2. [Fontes de biodiversidade e imagens](#2-fontes-de-biodiversidade-e-imagens)
3. [Referências científicas](#3-referências-científicas)
4. [Fontes candidatas ainda não integradas](#4-fontes-candidatas-ainda-não-integradas)
5. [Bibliotecas e ferramentas](#5-bibliotecas-e-ferramentas)
6. [Problemas de proveniência detectados](#6-problemas-de-proveniência-detectados)
7. [Como citar](#7-como-citar)
8. [Modelo para registrar uma nova fonte](#8-modelo-para-registrar-uma-nova-fonte)

---

## 1. Fontes de dados ambientais

### 1.1 NOAA Coral Reef Watch (CRW)

**Instituição:** National Oceanic and Atmospheric Administration / NESDIS / STAR — Coral Reef Watch Program (EUA)
**Produto:** Daily Global 5 km (0,05°) Satellite Coral Bleaching Heat Stress Monitoring Product Suite, versão 3.1
**Página oficial:** https://coralreefwatch.noaa.gov/product/5km/
**Acesso programático:** ERDDAP — `noaacrwdhwDaily` em https://coastwatch.noaa.gov/erddap/info/noaacrwdhwDaily/index.html (espelho PACIOOS: `dhw_5km` em https://pae-paha.pacioos.hawaii.edu/erddap/info/dhw_5km/index.html)
**Licença:** domínio público (obra do governo federal dos EUA); citação requerida por cortesia científica.

| Arquivo local | Variáveis | Período | Como foi obtido |
|---|---|---|---|
| `backend/dados/dhw.csv` (78,8 MB) | `CRW_SST`, `CRW_SSTANOMALY`, `CRW_HOTSPOT`, `CRW_DHW`, `CRW_BAA` (+ máscaras) | 2020-01-01 em diante | Download manual via ERDDAP, grade completa da bbox de Abrolhos |
| `backend/dados/dhw_5km_6006_cdf9_04d9.csv` (78,8 MB) | idem | idem | **Duplicata byte-a-byte de `dhw.csv`** — ver §6.1 |
| `backend/dados/NOAA_DHW_monthly_1c77_436e_401f.csv` (42 MB) | `sea_surface_temperature`, `sea_surface_temperature_anomaly` | 1985-10 em diante | Download manual — **coordenadas erradas, ver §6.2** |

**Onde é usado no código:**
- `backend/aquaculture/management/commands/coleta_de_dados.py` — cliente ERDDAP ao vivo (`erddapy`), servidor `https://coastwatch.pfeg.noaa.gov/erddap`, `dataset_id="nest_0_5deg_881a_b53d_5941"`. ⚠️ Este script **não persiste nada** (ver §6.6).
- `backend/aquaculture/management/commands/carregar_historico.py` — lê `dhw.csv` em `mapa_arquivos['sst']` e `['dhw']`.
- `backend/db/setup_graph.py` — registra o nó `FonteDados {id: "noaa_crw"}`.
- `backend/docs/contrato_canonico_variaveis.md` — mapeia `CRW_SST → sst`, `CRW_DHW → dhw`, `CRW_HOTSPOT → hotspot`, `CRW_BAA → baa`, `CRW_SSTANOMALY → sst_anomalia`.

**Citação sugerida:**
> NOAA Coral Reef Watch. *Daily Global 5 km Satellite Coral Bleaching Heat Stress Monitoring Product Suite, Version 3.1.* College Park, Maryland, USA: NOAA Coral Reef Watch. Dados acessados em [DATA]. https://coralreefwatch.noaa.gov/product/5km/

---

### 1.2 Copernicus Marine Service (CMEMS)

**Instituição:** European Union — Copernicus Marine Environment Monitoring Service
**Página oficial:** https://marine.copernicus.eu
**Acesso programático:** Copernicus Marine Toolbox — https://toolbox-docs.marine.copernicus.eu/en/stable/ · https://pypi.org/project/copernicusmarine/
**Licença:** livre e aberta, com atribuição obrigatória: *"Generated using E.U. Copernicus Marine Service Information"*. Requer conta gratuita para download programático.

Vários arquivos trazem também o crédito do **Projeto NECCTON (EU)** — https://neccton.eu/ — que financia parte dos produtos biogeoquímicos.

#### Inventário completo dos arquivos Copernicus

| Arquivo local | Produto CMEMS | Dataset | Variável (unidade) | Ponto geográfico | Profundidade | Início |
|---|---|---|---|---|---|---|
| `temperatura.csv` | GLOBAL_ANALYSISFORECAST_PHY_001_024 | `cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m` | `thetao` (°C) | −38,714 / −17,977 | **13,47 m** | 2022-06-01 |
| `cmems_mod_glo_phy_anfc_0.083deg_PT1H-m_1764628183519.csv` | GLOBAL_ANALYSISFORECAST_PHY_001_024 | `cmems_mod_glo_phy_anfc_0.083deg_PT1H-m` | `thetao` (°C), horário | −38,706 / −17,846 | 0,494 m | 2022-06-01 |
| `sst.csv` | SST_GLO_SST_L4_REP_OBSERVATIONS_010_011 | `METOFFICE-GLO-SST-L4-REP-OBS-SST` | `analysed_sst` (header diz kelvin) | −38,721 / −17,982 | superfície | **1981-10-01** |
| `salinidade.csv` | GLOBAL_ANALYSISFORECAST_PHY_001_024 | `cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i` | `so` (1e−3 ≈ PSU) | −38,710 / −17,976 | 0,494 m | 2022-06-01 |
| `salinidade_recente.csv` | GLOBAL_ANALYSISFORECAST_PHY_001_024 | `cmems_mod_glo_phy_anfc_0.083deg_P1D-m` | `sob` — **salinidade no fundo** | −38,716 / −17,977 | fundo | 2022-06-01 |
| `clorofila.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | `cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m` | `chl` (mg·m⁻³) | −38,710 / −17,976 | 0,494 m | 2021-11-01 |
| `clorofila_recente.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | `cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m` | `chl` (mg·m⁻³) | −38,716 / −17,977 | 0,494 m | 2021-11-01 |
| `ph.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | `cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m` | **`talk`** — alcalinidade (mol·m⁻³), **não é pH** | −38,710 / −17,976 | 0,494 m | 2021-11-01 |
| `cmems_mod_glo_bgc-car_..._1764629137159.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | `cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m` | `ph` (escala total) — **o pH real** | −38,710 / −17,976 | 0,494 m | 2021-11-01 |
| `cmems_mod_glo_bgc-car_..._1764629291619.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | idem | `ph` (escala total) | −38,710 / −17,976 | 0,494 m | 2021-11-01 |
| `cmems_mod_glo_bgc-car_..._1764629196586.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | idem | `dissic` — carbono inorgânico dissolvido (mol·m⁻³) | −38,710 / −17,976 | 0,494 m | 2021-11-01 |
| `cmems_mod_glo_bgc-co2_..._1764629112534.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | `cmems_mod_glo_bgc-co2_anfc_0.25deg_P1D-m` | `spco2` — pressão parcial de CO₂ (Pa) | −38,710 / −17,976 | superfície | 2021-11-01 |
| `cmems_mod_glo_bgc-bio_..._1764629434573.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | `cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m` | `nppv` — produção primária líquida | −38,710 / −17,976 | 0,494 m | 2021-11-01 |
| `oxigenio.csv` | **GLOBAL_MULTIYEAR_BGC_001_029** (reanálise) | `cmems_mod_glo_bgc_my_0.25deg_P1D-m` | `o2` (mmol·m⁻³) | −38,710 / −17,976 | 0,506 m | **1993-01-01** |
| `nitrato.csv` | **GLOBAL_MULTIYEAR_BGC_001_029** (reanálise) | `cmems_mod_glo_bgc_my_0.25deg_P1D-m` | `no3` (mmol·m⁻³) | −38,710 / −17,976 | 0,506 m | **1993-01-01** |
| `nitrato_recente.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | `cmems_mod_glo_bgc-nut_anfc_0.25deg_P1D-m` | `no3` (mmol·m⁻³) | −38,716 / −17,977 | 0,494 m | 2021-11-01 |
| `turbidez.csv` | GLOBAL_ANALYSISFORECAST_BGC_001_028 | `cmems_mod_glo_bgc-optics_anfc_0.25deg_P1D-m` | `kd` (m⁻¹) | −38,710 / −17,977 | 0,494 m | 2023-11-15 |
| `turbidez_recente.csv` | idem | idem | `kd` (m⁻¹) | idem | idem | idem — **duplicata de `turbidez.csv`** |
| `par_recente.csv` | MULTIOBS_GLO_BIO_BGC_3D_REP_015_010 | `cmems_obs-mob_glo_bgc-chl-poc_my_0.25deg_P7D-m` | **`PAR_error`** — campo de erro, não o PAR | −37,683 / −17,713 | 0 m | 1998-01-07 |

**Como foi obtido:** todos os arquivos acima têm cabeçalho `# Values from graph: v(t): value vs. time`, o que indica **exportação manual pela interface web do Copernicus Marine Data Store** (ferramenta de gráfico ponto-a-ponto), não via API. Isso explica a heterogeneidade de pontos e profundidades.

**Onde é usado no código:**
- `backend/aquaculture/management/commands/carregar_historico.py` — `mapa_arquivos` e `mapa_colunas`.
- `backend/ml_models/treinar_modelo.py` — `FILES_CONFIG`.
- `backend/aquaculture/management/commands/coleta_de_dados.py` — chamada ao vivo a `cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m` com `variables=["chl","o2","so"]`.
- `backend/db/setup_graph.py` — nó `FonteDados {id: "copernicus_marine"}`.

**Citação obrigatória:**
> E.U. Copernicus Marine Service Information (CMEMS). Produto [ID DO PRODUTO], DOI [DOI DO PRODUTO]. Dados acessados em [DATA]. https://marine.copernicus.eu
>
> Produtos biogeoquímicos com crédito adicional: NECCTON Project (EU), https://neccton.eu/

⚠️ Cada produto CMEMS tem um DOI próprio, obtido na página do produto no Copernicus Marine Data Store. **Ainda não coletados — pendência para o TCC.**

---

### 1.3 Met Office / GHRSST (via Copernicus)

**Produto:** SST_GLO_SST_L4_REP_OBSERVATIONS_010_011 — `METOFFICE-GLO-SST-L4-REP-OBS-SST` (OSTIA reprocessado)
**Arquivo:** `backend/dados/sst.csv` — a série mais longa do projeto (desde **1981**)
**Status de uso:** ⚠️ **não utilizado.** A coluna se chama `analysed_sst`, que não consta em `mapa_colunas['sst']` (`['thetao','sst','CRW_SST']`) — o arquivo é lido e silenciosamente descartado. Ver §6.4.

---

### 1.4 Dados simulados (não são fonte real)

**Arquivo:** `backend/dados/copernicus_marine.py`

```python
"""MODO DE SEGURANÇA: Retorna dados simulados para evitar erro de login."""
return {'vento': 6.5, 'turbidez': 0.05, 'origem': 'SIMULADO'}
```

Esta função **inventa** valores de vento e turbidez para contornar a falta de credenciais Copernicus. É a origem da constante `vento_velocidade=6.5` gravada em todos os registros de `StatusPredicao` por `carregar_historico.py:182`.

🚨 **Nenhum valor de vento no banco de dados é observado.** Deve ser removido ou substituído por ERA5 antes de qualquer uso científico ou publicação.

---

## 2. Fontes de biodiversidade e imagens

### 2.1 iNaturalist

**Site:** https://www.inaturalist.org
**Uso:** fotografias das espécies exibidas nas fichas do site.
**Licença:** varia por observação (CC0, CC-BY, CC-BY-NC, ou "todos os direitos reservados"). ⚠️ **É obrigatório verificar a licença de cada observação individualmente** — o iNaturalist não licencia em bloco.

| Espécie | Nome científico | Observação de origem | Crédito registrado no banco |
|---|---|---|---|
| Coral-cérebro brasileiro | *Mussismilia braziliensis* | https://www.inaturalist.org/observations/326387144 | ⚠️ "Acervo local do projeto" — contradiz a URL |
| Coral-estrela | *Montastraea cavernosa* | https://www.inaturalist.org/observations/326387704 | ⚠️ "Acervo local do projeto" — contradiz a URL |
| Coral-fogo-vermelho | *Muricea flamma* | https://www.inaturalist.org/observations/137432286 | inaturalist.org |
| Coral-pilar | *Dendrogyra cylindrus* | https://www.inaturalist.org/observations/276213882 | inaturalist.org |

🚨 As duas primeiras estão creditadas como "Acervo local do projeto" mas apontam para observações do iNaturalist. **Uma das duas informações está errada** — resolver antes de publicar, é risco de violação de direito autoral.

**Onde é usado:** campos `foto`, `credito_imagem`, `fonte_imagem_url` do modelo `Especie` (`backend/aquaculture/models.py`); arquivos em `backend/media/especies/`; espelhado em `frontend/src/recifeData.js`.

### 2.2 Imagens sem proveniência registrada

Os diretórios `fotos_especies/{Corais,Peixes,Invertebrados}/` (9 arquivos), `especies/` (1 arquivo) e `visual/` (1 captura de tela) **não têm nenhum registro de origem, autor ou licença**. Precisam ser rastreados ou removidos.

### 2.3 Coordenadas dos locais de recife

Adicionadas em 24/07/2026 pela migration `0014_seed_coordenadas_locais.py`, para viabilizar a ingestão por local (Fase B). Cada registro guarda a origem no campo `LocalRecife.fonte_coordenadas`.

| Local | Latitude | Longitude | Origem | Situação |
|---|---|---|---|---|
| `abrolhos-ba` | −17,972 | −38,688 | Seed original do projeto (`backend/db/setup_graph.py`) | ⚠️ Conferir contra ICMBio |
| `picaozinho-pb` | −7,108 | −34,810 | Aproximada — zona recifal a ~1,5 km da praia de Tambaú, João Pessoa/PB | 🚨 **Pendente de verificação em fonte oficial** |
| `porto-de-galinhas-pe` | −8,510 | −34,998 | Aproximada — piscinas naturais a ~500 m da praia, Ipojuca/PE | 🚨 **Pendente de verificação em fonte oficial** |

Nenhuma das três veio de uma fonte oficial citável. Antes do go-live devem ser substituídas por coordenadas do ICMBio (unidades de conservação) ou do Allen Coral Atlas (polígonos recifais). Enquanto forem aproximadas, os dados extraídos para Picãozinho e Porto de Galinhas **não são citáveis academicamente**.

`profundidade_media_m` foi preenchida apenas para Abrolhos (10,0 m, também do seed original). `area_km2` ficou nula em todos — deliberadamente, para não inventar número sem fonte.

### 2.4 Status de conservação

Os valores do campo `status_conservacao` ("Vulnerável", "Criticamente ameaçado", "Pouco preocupante", "Não avaliado") seguem a nomenclatura da **IUCN Red List** — https://www.iucnredlist.org — mas **não há registro de qual avaliação, de que ano, foi consultada** para cada espécie. Pendência: registrar o link da ficha IUCN por espécie no campo `fonte_url`, hoje vazio para todas.

---

## 3. Referências científicas

### 3.1 Referência não identificada usada no modelo de risco

O arquivo `backend/ml_models/treinar_modelo.py` contém marcadores `[cite: N]` que apontam para um documento PDF consultado durante a construção da função `calcular_risco()`, mas **o documento não está no repositório e não foi identificado**:

| Marcador | Afirmação embasada no código | Linha |
|---|---|---|
| `[cite: 158]` | Hipóxia reduz o limiar de branqueamento em 1 °C; água quente retém menos gás | `treinar_modelo.py:137` |
| `[cite: 48]` | Luz alta só é tóxica na presença de estresse térmico | `treinar_modelo.py:160` |
| `[cite: 102]` | Clorofila moderada protege (sombra e alimento) | `treinar_modelo.py:167` |
| `[cite: 53]` | Excesso de clorofila indica poluição | `treinar_modelo.py:167` |
| `[cite: 159]` | pH abaixo de 8,05 desacopla o crescimento | `treinar_modelo.py:178` |
| `[cite: 308]` | Sinergia tripla calor + acidificação + hipóxia é o pior cenário | `treinar_modelo.py:183` |

🚨 **Pendência crítica para o TCC.** Essas seis afirmações são a base de toda a lógica de risco do projeto e estão sem referência rastreável. É necessário identificar o documento original e registrá-lo aqui com autor, título, ano e DOI.

### 3.2 Referências levantadas no planejamento

**Base global de branqueamento (fonte de rótulo observado)**
> van Woesik, R.; Kratochwill, C. *A global coral-bleaching database, 1980–2020.* Scientific Data, v. 9, n. 20, 2022. DOI: 10.1038/s41597-022-01121-y
> https://www.nature.com/articles/s41597-022-01121-y
> Dados: BCO-DMO, dataset 773466 — https://www.bco-dmo.org/dataset/773466 (SQLite e Access, CC-BY 4.0)

34.846 registros de branqueamento em 14.405 sítios de 93 países, com presença/ausência, exposição do sítio, distância à costa, turbidez média, frequência de ciclones e métricas de SST. **Ainda não integrada** — é a fonte de variável resposta que o projeto precisa para treinar um modelo de branqueamento de verdade.

**Metodologia DHW**
> NOAA Coral Reef Watch — *Methodology, Product Description, and Data Availability of NOAA CRW Daily Global 5 km Satellite Coral Bleaching Heat Stress Monitoring Products.*
> https://coralreefwatch.noaa.gov/product/5km/methodology.php

Define a MMM (Maximum Monthly Mean) por pixel, o HotSpot, a acumulação de DHW em janela de 12 semanas contando apenas hotspots ≥ 1 °C, e os limiares de alerta (DHW ≥ 4 → Alerta 1; ≥ 8 → Alerta 2). **Referência normativa** — o cálculo atual do projeto diverge dela (ver §6.5).

### 3.3 Contexto brasileiro

> Projeto Coral Vivo — Monitoramento da saúde dos recifes da costa brasileira.
> https://coralvivo.org.br/noticia/monitoramento/

20 pontos monitorados do Ceará a Santa Catarina; coordenador executivo do PAN Corais em parceria com o ICMBio. Balanço de 2024 reporta ameaça grave aos recifes brasileiros; dados indicam 84% dos recifes brasileiros afetados por estresse térmico entre 2023 e 2025 (Sistema Simaclim). **Consultado como contexto; dados não integrados** (não há download aberto — requer solicitação formal).

> Ministério do Meio Ambiente — *Monitoramento dos Recifes de Coral do Brasil: Situação Atual e Perspectivas.*
> https://antigo.mma.gov.br/estruturas/chm/_arquivos/18_introducaobr.pdf

---

## 4. Fontes candidatas ainda não integradas

Levantadas no planejamento, com justificativa de por que interessam ao projeto.

| Fonte | Link | Para quê |
|---|---|---|
| NOAA CRW — climatologia MMM | https://coralreefwatch.noaa.gov/product/5km/ | MMM por pixel, necessária para calcular DHW pela norma em vez do limiar fixo de 27 °C |
| NASA OceanColor (MODIS/VIIRS/PACE) | https://oceancolor.gsfc.nasa.gov | PAR e Kd490 reais, substituindo o `PAR_error` e a turbidez derivada por fórmula |
| ERA5 / Copernicus Climate Data Store | https://cds.climate.copernicus.eu | Vento, radiação e pressão — substitui o valor simulado de 6,5 m/s |
| OBIS | https://obis.org | Ocorrências reais de espécies por local (API pública) |
| GBIF | https://www.gbif.org | Idem, com cobertura complementar |
| Allen Coral Atlas | https://allencoralatlas.org | Polígonos e geomorfologia dos recifes brasileiros |
| SiMCosta (FURG) | https://simcosta.furg.br | Boias costeiras brasileiras — validação *in situ* dos dados de satélite |
| Reef Check | https://www.reefcheck.org | Monitoramento voluntário, complementa o GCBD |
| IUCN Red List | https://www.iucnredlist.org | Status de conservação rastreável por espécie |

---

## 5. Bibliotecas e ferramentas

| Ferramenta | Versão | Papel no projeto | Link |
|---|---|---|---|
| Django | 5.1.2 (pinado) | Backend, ORM, admin | https://www.djangoproject.com |
| Django REST Framework | — | API JSON | https://www.django-rest-framework.org |
| django-cors-headers | 4.4.0 | CORS para o frontend | https://github.com/adamchainz/django-cors-headers |
| django-environ | 0.12.0 | Leitura de `backend/.env` e da `DATABASE_URL` | https://django-environ.readthedocs.io |
| React | 19.2 (CRA 5.0.1) | Frontend SPA | https://react.dev |
| Tailwind CSS | 3.4.17 | Estilização | https://tailwindcss.com |
| lucide-react | — | Ícones | https://lucide.dev |
| pandas / numpy | — | Processamento das séries temporais | https://pandas.pydata.org |
| scikit-learn | — | Random Forest do modelo de risco | https://scikit-learn.org |
| joblib | — | Serialização do modelo (`.pkl`) | https://joblib.readthedocs.io |
| matplotlib | — | Gráficos dos relatórios | https://matplotlib.org |
| erddapy | — | Cliente ERDDAP para NOAA | https://github.com/ioos/erddapy |
| copernicusmarine | — | Cliente oficial Copernicus Marine | https://pypi.org/project/copernicusmarine/ |
| xarray + netcdf4 | — | Leitura de NetCDF | https://xarray.dev |
| neo4j (driver Python) | 5.20.0 | Grafo científico | https://neo4j.com/docs/python-manual/ |
| Pillow | — | Processamento de imagens | https://python-pillow.org |

---

## 6. Problemas de proveniência detectados

Auditoria de 24/07/2026. Todos verificados lendo os arquivos e o código.

### 6.1 Arquivos duplicados
Duplicação confirmada por MD5 em 24/07/2026:

| Arquivo | Tamanho | MD5 |
|---|---|---|
| `dhw.csv` | 78.819.377 B | `3bbaf9d4bf31e2079b2a17d3d6aad07f` |
| `dhw_5km_6006_cdf9_04d9.csv` | 78.819.377 B | `3bbaf9d4bf31e2079b2a17d3d6aad07f` |
| `turbidez.csv` | 35.419 B | `d1bf93d00f126630cbca21e857ac34ef` |
| `turbidez_recente.csv` | 35.419 B | `d1bf93d00f126630cbca21e857ac34ef` |

**~79 MB de duplicação pura.** (Verificado também que `clorofila.csv` ≠ `clorofila_recente.csv` e que os dois arquivos `bgc-car` com variável `ph` são distintos — diferem no ponto geográfico e na linha de crédito, então **não** são duplicatas.)

### 6.2 Arquivo com coordenadas do hemisfério errado
`NOAA_DHW_monthly_1c77_436e_401f.csv` (42 MB) tem `latitude ≈ 18,975` **N** e `longitude ≈ 38,025` **E** — isso é o Mar Vermelho, não Abrolhos (que fica em −17,97 / −38,69). O sinal foi perdido no download. **Este arquivo não descreve o Brasil.**

### 6.3 Alcalinidade sendo usada como pH
`ph.csv` contém a variável `talk` (alcalinidade total, ~2,50 mol·m⁻³), **não pH**. Como `mapa_colunas['ph'] = ['ph', 'talk']` em `carregar_historico.py:61`, o valor de alcalinidade é gravado no campo `ph` do banco. O `contrato_canonico_variaveis.md` proíbe explicitamente isso: *"`talk` não é pH e não deve substituir sem transformação química explícita"*. O pH real está em `cmems_mod_glo_bgc-car_..._1764629137159.csv` e `..._1764629291619.csv`, que não são lidos.

Consequência em cadeia: `calcular_risco()` penaliza pH < 8,05 — com pH = 2,5, a penalidade de acidificação satura em todos os registros.

### 6.4 Série mais longa do projeto está sendo descartada
`sst.csv` (Met Office, desde 1981) tem a coluna `analysed_sst`, ausente de `mapa_colunas['sst']`. O arquivo é aberto, não encontra coluna compatível e é ignorado sem aviso. São ~40 anos de SST perdidos.

### 6.5 DHW fora da metodologia NOAA
`carregar_historico.py:138-140` usa limiar fixo de 27,0 °C em vez da MMM por pixel, e acumula **todos** os hotspots positivos em janela de 84 dias, enquanto a norma NOAA acumula apenas hotspots ≥ 1 °C. O resultado superestima o DHW e não é comparável com o produto oficial.

### 6.6 Ingestão ao vivo não persiste
`coleta_de_dados.py` busca NOAA e Copernicus com sucesso e o "Passo 3 — Salvando no Banco" é apenas comentário. Os DataFrames são descartados ao fim da função.

### 6.7 Vento inventado
Ver §1.4 — todos os valores de vento no banco vêm de uma constante em uma função marcada `SIMULADO`.

### 6.8 Turbidez derivada por fórmula não referenciada
`carregar_historico.py:100` converte clorofila em turbidez por `kd = 0,05 + 0,3 × chl` quando não há Kd490. **Essa fórmula não tem fonte documentada.** Existem dados reais de `kd` em `turbidez.csv` (mas só desde 2023-11-15).

### 6.9 Mistura de pontos geográficos
Os arquivos vêm de pontos diferentes: −38,710/−17,976 (maioria), −38,716/−17,977, −38,706/−17,846, −38,721/−17,982 e **−37,683/−17,713** (o PAR, a ~110 km dos demais). São mesclados por `time` como se fossem o mesmo local.

### 6.10 Mistura de profundidades
`temperatura.csv` está a **13,47 m**; os demais a ~0,49 m; `salinidade_recente.csv` usa `sob` (salinidade **no fundo**). Tratados como uma única camada.

### 6.11 Mistura de reanálise e previsão
`oxigenio.csv` e `nitrato.csv` vêm de GLOBAL_MULTIYEAR_BGC_001_029 (reanálise, desde 1993); `nitrato_recente.csv` vem do produto de previsão. Produtos com viés diferente, concatenados sem flag.

### 6.12 Campo de erro usado como medida
`par_recente.csv` traz `PAR_error` — o campo de incerteza, não o PAR. O contrato canônico já marca isso como `quality=degradado`, mas o código o consome como valor.

### 6.13 `par.csv` corrompido
As coordenadas aparecem como `-17.187.504` e `-3.952.083` (separador de milhar aplicado indevidamente na exportação) e a coluna `par` está preenchida com `NaN` nas primeiras linhas. 58 MB provavelmente inúteis.

### 6.14 Catálogo público fictício
`frontend/src/App.js` expõe um array `DADOS_GERAIS` com 8 datasets inventados, datas de 2026, tamanhos fictícios e `downloadUrl` apontando para arquivos inexistentes (`/dados/biodiversidade-abrolhos.json`, `/dados/mosaico-porto.tif`, `/dados/relatorio-picaozinho.pdf`, `/dados/modelo-branqueamento.parquet`). Três deles são atribuídos à fonte "Projeto Coral Brasil" e dois ao "NCBI" — **sem que exista qualquer dado real do NCBI no projeto.**

### 6.15 DOIs dos produtos CMEMS não coletados
Cada produto Copernicus tem DOI próprio, exigido para citação formal. Nenhum foi registrado.

---

## 7. Como citar

Ao publicar o site ou o trabalho acadêmico, incluir uma seção de atribuição com:

1. **Copernicus** — *"Generated using E.U. Copernicus Marine Service Information"*, mais o DOI de cada produto usado. Créditos adicionais ao NECCTON Project (EU) nos produtos biogeoquímicos.
2. **NOAA Coral Reef Watch** — citação da versão 3.1 do produto de 5 km, com data de acesso.
3. **Met Office / GHRSST** — via produto Copernicus SST_GLO_SST_L4_REP_OBSERVATIONS_010_011, se vier a ser usado.
4. **iNaturalist** — crédito ao autor de cada fotografia, com a licença específica da observação e link.
5. **IUCN Red List** — se os status de conservação forem mantidos, citar a versão da Red List consultada.
6. **GCBD** — van Woesik & Kratochwill (2022), CC-BY 4.0, se integrado.

O projeto está sob licença MIT (`LICENSE`), mas isso **cobre apenas o código** — os dados e as imagens seguem as licenças de suas fontes originais.

---

## 8. Modelo para registrar uma nova fonte

Copie este bloco ao adicionar qualquer fonte nova:

```markdown
### [Nome da fonte]

- **Instituição:**
- **Link oficial:**
- **Forma de acesso:** (API / download manual / scraping / solicitação formal)
- **Credenciais necessárias:** (sim/não — se sim, qual variável de ambiente)
- **Licença:**
- **Citação exigida:**
- **Variáveis obtidas:** (nome original → nome canônico, unidade)
- **Cobertura:** (período, resolução espacial, resolução temporal, ponto/bbox)
- **Arquivos ou tabelas gerados:**
- **Onde é usado no código:** (arquivo:linha)
- **Data da coleta:**
- **Limitações conhecidas:**
```

Toda variável nova precisa também de uma linha correspondente em
[`backend/docs/contrato_canonico_variaveis.md`](../backend/docs/contrato_canonico_variaveis.md),
conforme a regra de governança daquele documento.

---

## 9. Histórico de alterações

| Data | Alteração |
|---|---|
| 24/07/2026 | Criação do documento. Auditoria inicial de proveniência dos 19 CSVs, das imagens e das referências: 15 problemas registrados na §6. |
| 24/07/2026 | Fase A do roadmap. Adicionadas coordenadas aos três locais de recife (§2.3) — duas delas aproximadas e pendentes de verificação. `django-environ` incluída na §5. |
