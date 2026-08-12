# Fontes de Dados e Referências — Projeto Coral Brasil

> **Status:** documento vivo — obrigatório manter atualizado.
> **Regra:** nenhum dado entra no projeto sem uma linha correspondente neste documento.
> **Última revisão:** 12/08/2026

Este documento registra **toda** fonte de informação usada na construção do Coral Brasil: de onde veio cada dado, como foi obtido, onde é usado no código, sob qual licença e como deve ser citado. Serve tanto para reprodutibilidade acadêmica quanto para atribuição legal.

> **Documento irmão:** [VARIAVEIS.md](VARIAVEIS.md) explica *por que* cada variável entra ou fica de fora do modelo. Este aqui trata de *de onde os dados vêm*; aquele, de *quais deles são usados e por quê*.

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

> 📊 **Para saber o que está no banco agora**, sem ler o documento inteiro:
> [§1.5 Estado da base ingerida](#15-estado-da-base-ingerida--25072026).

---

## 1. Fontes de dados ambientais

### 1.1 NOAA Coral Reef Watch (CRW)

**Instituição:** National Oceanic and Atmospheric Administration / NESDIS / STAR — Coral Reef Watch Program (EUA)
**Produto:** Daily Global 5 km (0,05°) Satellite Coral Bleaching Heat Stress Monitoring Product Suite, versão 3.1
**Página oficial:** https://coralreefwatch.noaa.gov/product/5km/
**Acesso programático:** ERDDAP. Três espelhos publicam o mesmo produto, cada um sob um identificador próprio — servidor e dataset **sempre andam em par**. Disponibilidade medida em 25/07/2026 com `manage.py testar_fontes`, nas duas redes:

| Espelho | Servidor | Dataset | Na UFF | Fora da UFF |
|---|---|---|---|---|
| **PACIOOS** (**padrão do projeto**) | `pae-paha.pacioos.hawaii.edu/erddap` | `dhw_5km` | não medido | ✅ 5/5 |
| pfeg | `coastwatch.pfeg.noaa.gov/erddap` | `NOAA_DHW` | ✅ 5/5, com 503 intermitente | ❌ timeout (`WinError 10060`) |
| NOAA CoastWatch | `coastwatch.noaa.gov/erddap` | `noaacrwdhwDaily` | ⚠️ HTTP 403 | ⚠️ HTTP 403 |

⚠️ "Não medido" é literal: nenhuma execução do `testar_fontes` na UFF chegou a testar o PACIOOS antes de ele virar padrão. Não há motivo conhecido para falhar lá — a restrição documentada abaixo é dos servidores da NOAA, e o PACIOOS não é da NOAA —, mas **isso é inferência, não medição**, e fica assim registrado até alguém rodar `testar_fontes` na universidade.

**Por que o PACIOOS é o padrão** (decidido em 25/07/2026, depois de o pfeg ter ocupado esse lugar por alguns dias):

1. **É o único que funciona fora da rede federal**, onde os dois servidores da NOAA falham. A recíproca não vale: não há indício de que ele falhe dentro dela.
2. **Não é versão degradada.** O backfill 2020–2026 foi rodado nos dois espelhos e deu resultado idêntico bloco a bloco. As 6 datas ausentes são do produto CRW, não do espelho.
3. O pfeg devolve **503 intermitente** por sobrecarga mesmo quando alcançável.

O argumento a favor do pfeg era ser o espelho oficial da NOAA — e é o servidor que o `coleta_de_dados.py` original usava. Mas **um padrão que só funciona numa rede específica não é padrão**: é uma armadilha para quem clonar o repositório, e foi exatamente o que aconteceu na primeira tentativa de rodar fora da universidade. Quem estiver na UFF e quiser o servidor oficial descomenta `NOAA_ERDDAP_SERVER`/`NOAA_ERDDAP_DATASET` no `.env`.

O PACIOOS também foi a origem dos CSVs que o projeto já possuía, e é por ele que estão os 43.038 registros atuais (§1.5).

#### Cobertura obtida e lacunas do produto (backfill de 25/07/2026)

Série ingerida: **2020-01-01 a 2026-07-23**, três locais, 5 variáveis — **35.850 medições** (11.950 por local).

Cobertura: **2.390 de 2.396 dias (99,75%)**. Seis datas não existem no produto:

| Data ausente | Observação |
|---|---|
| 2024-01-30 | isolada |
| 2024-07-04, 07-05, 07-06 | **três dias consecutivos** |
| 2024-07-25 | isolada |
| 2026-04-25 | isolada |

Três propriedades verificadas que sustentam a conclusão de que a lacuna é **do produto CRW**, e não do pipeline nem de um servidor específico:

1. **As seis datas são exatamente as mesmas nos três locais** (Abrolhos-BA, Picãozinho-PB, Porto de Galinhas-PE), que ficam a mais de 1.500 km um do outro.
2. **Os dois espelhos concordam.** O backfill foi feito duas vezes de forma independente — pfeg `NOAA_DHW` na rede da UFF e PACIOOS `dhw_5km` fora dela — e produziu contagem idêntica bloco a bloco, incluindo os blocos deficitários (895, 880, 895 nas mesmas posições).
3. **Não há dia parcial.** Todos os 7.170 pares (data, local) gravados têm exatamente 5 variáveis. Ou o dia veio inteiro, ou não veio.

⚠️ **Consequência para a modelagem:** janelas e defasagens precisam tratar essas datas explicitamente. Uma janela de 30 dias que contenha 04–06/07/2024 tem 27 dias, não 30. Interpolar ou não é decisão do modelo, mas ignorar silenciosamente produziria uma feature com significado diferente do declarado. O pipeline ainda **não** emite relatório de lacunas — estas foram encontradas conferindo contagem à mão.

#### 🔒 Restrição de rede: os servidores da NOAA exigem domínio federal

Os espelhos da própria NOAA **só respondem de dentro de uma rede com domínio federal** — no caso deste projeto, a UFF. Medido em 25/07/2026, comparando uma máquina dentro da UFF com outra fora:

| Host | Dentro da UFF | Fora |
|---|---|---|
| `coastwatch.pfeg.noaa.gov` | ✅ responde (com 503 intermitente) | ❌ timeout |
| `coastwatch.noaa.gov` | ⚠️ HTTP 403 | TLS conecta; HTTP não medido de fora |
| `pae-paha.pacioos.hawaii.edu` | a confirmar | ✅ **dado real, 5/5 variáveis** |

**O PACIOOS não é da NOAA** — é do Pacific Islands Ocean Observing System, na Universidade do Havaí, e redistribui o mesmo produto Coral Reef Watch 5 km v3.1. Por isso não está sujeito à restrição, e foi por ele que a primeira ingestão bem-sucedida fora da rede federal aconteceu.

Consequência para a operação, e a razão de o padrão ter mudado: **o pfeg só funciona na UFF**, então agendamento automático, deploy ou trabalho de casa não podiam depender dele. Desde 25/07/2026 o padrão do projeto é o PACIOOS. Como o estado de cada espelho depende da rede, rode `manage.py testar_fontes` na máquina que vai ingerir.

#### ❌ Correção: o PACIOOS **não** tem certificado inválido

A versão anterior desta seção afirmava que a falha do PACIOOS em "duas redes independentes" indicava problema no servidor. **Estava errado por dois motivos, e a medição prova.** Diagnóstico com `manage.py testar_fontes --ssl` em 25/07/2026:

| Espelho | Cadeia do sistema | Bundle do `certifi` |
|---|---|---|
| PACIOOS | ❌ `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` | ✅ verifica |
| NOAA CoastWatch | ✅ verifica | ✅ verifica |
| pfeg | timeout (rota bloqueada nessa rede) | timeout |

O mesmo host que falha com a cadeia nativa da máquina **verifica normalmente com o bundle do `certifi`**. Isso é falha de montagem de cadeia **no cliente**, não certificado ruim no servidor: o OpenSSL que o Python usa não busca o certificado intermediário faltante (*AIA chasing*), coisa que o navegador faz — daí o site abrir no Edge e falhar no `urlopen`.

O erro de raciocínio foi tratar "falhou em duas redes independentes" como evidência sobre o servidor. Duas coisas estavam erradas nessa frase:

1. **As redes não eram duas.** Verificado com a autora em 25/07/2026: todas as execuções manuais foram feitas na UFF. A afirmação de duas redes entrou no documento por suposição minha, não por medição.
2. **Ainda que fossem, não seriam evidências independentes.** São máquinas Windows rodando Python, que compartilham exatamente a limitação envolvida. Duas amostras da mesma causa não somam.

Fica o método: registrar *onde* cada medição foi feita, não só o resultado. Sem isso, "falhou em dois lugares" vira argumento sem lastro.

Consequências:
- O PACIOOS continua utilizável e não deve ser descartado.
- **O estado de cada espelho depende da máquina e da rede tanto quanto do servidor.** Rode `testar_fontes` na máquina que vai ingerir, não em outra.

**Disponibilidade do pfeg (medida em 25/07/2026):** o espelho responde, mas devolve `HTTP 503 — Service Unavailable: There was a (temporary?) problem. Wait a minute, then try again.` de forma intermitente. É sobrecarga do servidor, não configuração do projeto: o `.das` do mesmo dataset respondia normalmente na mesma máquina e no mesmo minuto. Desde então o pipeline distingue falha passageira de falha definitiva e repete só a primeira — 3 tentativas, esperando 10 s e 30 s (`backend/ingestao/retentativa.py`, ajustável por `INGESTAO_TENTATIVAS`). Certificado inválido, 403 e 404 continuam falhando na primeira tentativa, porque não melhoram com espera.
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
- `backend/ingestao/conectores/copernicus.py` — **caminho novo**, por API, com proveniência por valor. Só ele alimenta `MedicaoAmbiental` com `fonte='copernicus'`.

#### Cobertura ingerida pelo pipeline

Backfill de 25/07/2026, `2020-01-01` a `2026-07-24`, três locais, em 14 blocos de 180 dias por local. **14.382 medições, 2.397 dias por local e variável, nenhuma data faltando e nenhum valor nulo.**

| Variável | Dataset | Tipo | Período gravado | n (3 locais) |
|---|---|---|---|---|
| salinidade | `cmems_mod_glo_phy_my_0.083deg_P1D-m` | reanálise | 2020-01-01 → 2026-06-23 | 7.098 |
| salinidade | `cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m` | análise | 2026-06-24 → 2026-07-24 | 93 |
| oxigênio | `cmems_mod_glo_bgc_my_0.25deg_P1D-m` | reanálise | 2020-01-01 → 2026-05-31 | 7.029 |
| oxigênio | `cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m` | análise | 2026-06-01 → 2026-07-24 | 162 |

A emenda cai em data **diferente por variável** — a reanálise física vai três semanas mais longe que a biogeoquímica. Por isso a data de corte não é constante no código: é lida do eixo de tempo de cada dataset aberto.

⚠️ **Série sem lacunas não é sinal de qualidade superior à do NOAA.** O CMEMS é saída de modelo: produz valor para todo dia e todo pixel, inclusive onde não houve observação assimilada. O produto do NOAA tem 6 datas ausentes justamente por ser observacional. Comparar as duas séries pela completude inverteria o que cada uma vale como evidência.

**Faixas medidas (2020–2026, média espacial da bbox, camada de ~0,494 m):**

| Local | Salinidade (PSU) | Oxigênio (mmol·m⁻³) |
|---|---|---|
| Abrolhos (BA, −18°) | 35,75 – 37,69 (méd. 37,12) | 199,9 – 214,2 (méd. 207,8) |
| Porto de Galinhas (PE, −8°) | 35,39 – 37,35 (méd. 36,74) | 194,4 – 207,0 (méd. 201,6) |
| Picãozinho (PB, −7°) | 35,32 – 37,19 (méd. 36,65) | 195,8 – 206,6 (méd. 201,6) |

O gradiente latitudinal está fisicamente correto nos dois sentidos: Abrolhos, mais ao sul e mais frio, tem mais O₂ dissolvido (a solubilidade cai com a temperatura) e salinidade mais alta.

**Profundidade:** o pipeline pede de 0 a 1 m, e a toolbox emite um `WARNING` a cada abertura dizendo que a seleção excede as coordenadas do dataset (`[0.494, 5727.9]`). É esperado e não é erro: o primeiro nível dos produtos globais fica em ~0,494 m, e o intervalo pedido seleciona esse nível e só ele. Pedir exatamente 0,494 deixaria o código preso a uma constante que muda entre produtos (o BGC usa 0,506 m).

**Citação obrigatória:**
> E.U. Copernicus Marine Service Information (CMEMS). *Global Ocean Physics Reanalysis*, `GLOBAL_MULTIYEAR_PHY_001_030`. DOI: 10.48670/moi-00021. Dados acessados em 25/07/2026. https://marine.copernicus.eu
>
> Produtos biogeoquímicos com crédito adicional: NECCTON Project (EU), https://neccton.eu/

✅ **Os quatro DOIs foram coletados em 31/07/2026** — a tabela completa, e por que cada variável precisa de **duas** citações (a série emenda reanálise e análise), está em §7.2.

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

### 1.5 Estado da base ingerida — 25/07/2026

O que está de fato em `MedicaoAmbiental`, gravado pelo pipeline de `backend/ingestao/`. Não inclui os CSVs legados nem o `StatusPredicao`, que vêm do caminho antigo.

**Onde vive:** PostgreSQL 17, subido por `docker-compose.yml`. Migrado do SQLite em 25/07/2026 sem perda — contagens e distribuição do BAA idênticas antes e depois. Ver [arquitetura.md](arquitetura.md) para o papel de cada camada.

| Fonte | Espelho / produto | Medições | Variáveis | Período |
|---|---|---|---|---|
| `noaa_crw` | PACIOOS `dhw_5km` | 43.038 | `sst`, `dhw`, `baa`, `baa_area_alerta`, `hotspot`, `sst_anomalia` | 2020-01-01 → 2026-07-24 |
| `copernicus` | CMEMS (reanálise + análise) | 14.382 | `salinidade`, `oxigenio` | 2020-01-01 → 2026-07-24 |
| **Total** | | **57.420** | 8 | |

Três locais em todas as séries: Abrolhos (BA), Porto de Galinhas (PE) e Picãozinho (PB).

**As duas fontes cobrem exatamente a mesma janela**, o que era pré-requisito para montar as janelas com defasagem sem cortar amostra por desalinhamento de cobertura.

Duas diferenças estruturais entre elas continuam valendo e não devem ser confundidas com qualidade:

- O **NOAA tem 6 datas ausentes** (§1.1) porque é produto observacional de satélite. O **Copernicus não tem nenhuma** porque é saída de modelo, que produz valor para todo dia e todo pixel — inclusive onde não houve observação assimilada.
- O NOAA vem de um único produto; o Copernicus **emenda reanálise e análise**, com a costura registrada em `dataset_id` valor a valor (§1.2).

---

## 2. Fontes de biodiversidade e imagens

### 2.1 iNaturalist — ✅ conferido e corrigido em 11/08/2026 (migração `0026`)

**Site:** https://www.inaturalist.org
**Uso:** fotografias das espécies exibidas nas fichas do site.
**Licença:** varia por observação (CC0, CC-BY, CC-BY-NC, ou "todos os direitos reservados"). ⚠️ **É obrigatório verificar a licença de cada observação individualmente** — o iNaturalist não licencia em bloco.

🚨 **O que estava registrado aqui era otimista demais.** Esta seção só apontava **duas** das nove espécies como mal creditadas — as que tinham URL documentada nesta tabela e contradiziam o próprio crédito. Ao conferir o banco direto (não só o que este documento já sabia), **as nove tinham exatamente o mesmo problema**: `credito_imagem = "Acervo local do projeto"` e `fonte_imagem_url` vazio, em **todas**, mesmo nas que claramente não são produção própria do projeto — são fotos de animal, de terceiros. Nenhuma das nove tinha `local_captura_foto` (campo que não existia até esta correção).

**Conferido agora pela API pública do iNaturalist** (`api.inaturalist.org/v1/observations/<id>` — responde sem autenticação, ao contrário da página HTML, que devolve 403 a acesso automatizado) para as quatro espécies com URL de observação documentada:

| Espécie | Nome científico | Observador | Licença | Local da observação | Data |
|---|---|---|---|---|---|
| Coral-cérebro brasileiro | *Mussismilia braziliensis* | Kai Lima (`kailimma_nascimento`) | CC BY-NC | Caravelas, BA | 23/02/2025 |
| Coral-estrela | *Montastraea cavernosa* | Kai Lima (`kailimma_nascimento`) | CC BY-NC | Caravelas, BA | 26/02/2025 |
| Coral-fogo-vermelho | *Muricea flamma* | João D'Andretta (`jpdandretta`) | CC BY | Arquipélago de Abrolhos, BA | 25/09/2022 |
| Coral-pilar | *Dendrogyra cylindrus* | Laura Proença (`lproenca`) | 🚨 **nenhuma** (`license_code` nulo) | Bahia, BR | 01/02/2024 |

**Observação:** https://www.inaturalist.org/observations/326387144, .../326387704, .../137432286 e .../276213882, respectivamente.

🚨 **`Dendrogyra cylindrus` não tinha licença concedida pelo fotógrafo.** `license_code` nulo na API do iNaturalist significa **"todos os direitos reservados"** — o padrão do site quando ninguém escolheu uma licença aberta. O projeto vinha hospedando uma cópia do arquivo (`backend/media/especies/Dendrogyra_cylindrus.jpeg`) e servindo-a no site, sem nenhuma permissão de reuso. **Corrigido**: o campo `foto` dela foi limpo pela migração `0026` — o site para de servir a cópia, mantendo só o crédito e o link da observação (linkar para a fonte não é violação; redistribuir a cópia, sem licença, é). O arquivo continua em disco, não apagado, para não destruir a única cópia enquanto ninguém decide se vale pedir permissão à fotógrafa.

⚠️ **As outras três (com licença de verdade) também tiveram `foto` limpo.** Não por problema de licença — CC BY e CC BY-NC permitem reuso com atribuição —, mas porque o caminho correto para exibir a foto de um terceiro é **linkar** `fonte_imagem_url` (o crédito completo mora na própria observação, incluindo a licença exata e futuras correções do autor), não redistribuir uma cópia estática que pode divergir da fonte com o tempo. O site mostra o ícone de espécie no lugar da miniatura e o link "Ver fonte da imagem" continua funcionando — mesmo padrão que as cinco abaixo já usavam antes desta correção.

**As outras cinco (Holacanthus ciliaris, Sparisoma axillare, Ocyurus chrysurus, Phyllogorgia dilatata, Condylactis gigantea) não têm URL de observação documentada em lugar nenhum do projeto.** Não há como confirmar procedência de uma foto sem fonte — a migração `0026` limpou `foto`, `credito_imagem` e `fonte_imagem_url` delas também, em vez de continuar afirmando um crédito já sabido falso. Ficam com o mesmo vazio que `iucn_categoria` já usa para "sem procedência registrada" (migração `0022`, §2.4) — a modal do site já sabe mostrar isso sem inventar texto. 📌 **Pendência aberta:** se alguém souber a origem real dessas cinco fotos, `local_captura_foto` e os demais campos agora existem para registrá-la — pelo formulário de contribuição do site (`/minhas-especies`) ou pelo Django admin.

🚨 **Limpar o banco não bastava: o crédito falso era _gerado por código_, em dois lugares, e sobrevivia à migração `0026`.** A correção acima só alcançava o PostgreSQL. Duas funções continuavam fabricando a mesma afirmação a partir da simples existência de um arquivo de foto:

| Onde | O que fazia | Alcance |
|---|---|---|
| `backend/aquaculture/code_sync.py::_credito_imagem` | sem `credito_imagem`, gravava a string `"Acervo local do projeto"` na cópia versionada | `frontend/src/data/recifeData.js` — o **fallback offline**, o que o site mostra quando a API cai |
| `backend/aquaculture/code_sync.py::_fonte_imagem_url` | sem `fonte_imagem_url`, gravava a URL do **próprio arquivo local**, fazendo a cópia se passar por fonte externa | idem |
| `frontend/src/utils/formatters.js::resolverCreditoImagem` | sem `credito_imagem`, exibia `"Acervo local do projeto"` na tela | **caminho ao vivo** — modal e card, sobre dados vindos da API |

Por isso o `recifeData.js` versionado ainda trazia as nove espécies com o crédito falso **e** `"foto_url": "/media/especies/Dendrogyra_cylindrus.jpeg"` — ou seja, com a API fora do ar o site continuava servindo exatamente a foto sem licença que a `0026` tirou do ar. **Corrigido em 12/08/2026:** as três funções deixaram de inventar; sem crédito no banco, nada é afirmado. O exportador passou a aplicar à imagem o mesmo critério que já aplicava à categoria IUCN — *sem procedência, não entra na cópia versionada*: sem `credito_imagem`, o `foto_url`, a fonte e o `local_captura_foto` saem vazios do `.js`, ainda que a API continue servindo o que houver no banco. Travado por 6 testes de backend (`ProcedenciaDeImagemNaCopiaVersionadaTests`) e 1 de frontend. Os dois arquivos gerados foram regerados: estavam parados em 04/08/2026, antes das migrações `0025` e `0026`, e por isso listavam três locais em vez de dez.

⚠️ **Lição de desenho, não só de dado:** um valor-padrão calculado na leitura (`credito or 'Acervo local do projeto'`) é indistinguível de um dado real depois de escrito em arquivo — foi assim que uma foto sem licença nenhuma apareceu creditada ao projeto em três lugares diferentes, sem ninguém nunca ter digitado isso. Vazio precisa continuar vazio até a borda da tela, onde "Sem credito informado" é escrito como texto de interface, e não como dado.

**Onde é usado:** campos `foto`, `credito_imagem`, `fonte_imagem_url`, `local_captura_foto` do modelo `Especie` (`backend/aquaculture/models.py`); arquivos em `backend/media/especies/`; espelhados na cópia versionada `frontend/src/data/recifeData.js` (gerada por `code_sync.py`, nunca editada à mão). `local_captura_foto` é novo (migração `0026`) — registra onde a **foto** foi tirada, que não é necessariamente onde a espécie ocorre nem um dos locais monitorados pelo projeto.

### 2.2 Fotos dos locais de recife — ✅ campos abertos em 12/08/2026 (migração `0030`)

**Uso:** a imagem que aparece no topo da página do recife (`LocalRecifePage`) e no cartão da listagem (`CardRecife`) — as duas faixas mais visíveis do site.

🚨 **A correção de 11/08/2026 (§2.1) alcançou as fotos de _espécie_ e parou ali.** `LocalRecife.imagem` existe desde o começo do projeto e **nunca teve onde registrar autor, fonte ou local de captura**. O caso não é o mesmo das espécies, e é pior de um jeito específico: lá havia um crédito errado, que uma auditoria de campo encontra; aqui não havia campo nenhum, e **o que não tem campo não aparece numa busca por campo errado**. A auditoria de 11/08 varreu `credito_imagem` e `fonte_imagem_url` em `Especie`; `LocalRecife` não tinha esses nomes para serem varridos.

**Corrigido:** a migração `0030` acrescenta a `LocalRecife` os mesmos três campos de `Especie`, com a mesma regra e a mesma opcionalidade:

| Campo | Obrigatório? | O que registra |
|---|---|---|
| `credito_imagem` | não — mas **sem ele nada é afirmado** | site, instituição ou nome de quem fotografou/cedeu |
| `fonte_imagem_url` | não | a página de origem — **nunca** a URL da cópia local |
| `local_captura_foto` | não | onde a foto foi tirada, quando se souber |

⚠️ **`local_captura_foto` não é a coordenada monitorada**, e a distinção importa mais aqui do que nas espécies. A foto de um recife pode ter sido feita num ponto específico da zona recifal, de um barco a 2 km ou do ar. Preenchê-la automaticamente com o `lat/lon` do local, só porque é a foto daquele recife, seria inventar a posição da câmera — exatamente o que `fonte_coordenadas` existe para impedir do outro lado (§2.3).

⚠️ **A regra de exibição é a mesma de §2.1, e vale nos dois caminhos.** Sem `credito_imagem`: o exportador (`code_sync.build_sync_payload`) deixa `imagem_url`, `fonte_imagem_url` e `local_captura_foto` vazios na cópia versionada `frontend/src/data/recifeData.js`, e a tela escreve *"Foto sem crédito informado"* como texto de interface. A API continua servindo o que houver no banco, com `imagem_tem_procedencia` dizendo se aquilo pode ser afirmado — mesma divisão já escolhida para a foto de espécie: **a API serve o acervo, a tela decide o que afirmar**.

**Situação hoje:** os 10 locais cadastrados estão com `imagem` vazia, então não há nenhum crédito pendente a corrigir. Os campos existem para a primeira foto que entrar — e ela só será exibida com crédito. Travado por 6 testes de backend (`ProcedenciaDaFotoDoLocalTests`) e 5 de frontend (`ImagemRecife.test.jsx`).

### 2.2.1 Imagens sem proveniência registrada

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

#### 2.3.1 Sete locais adicionados em 11/08/2026 — sem fonte primária, sem série ambiental

Migration `0025_seed_novos_locais_recife.py`. Vieram de uma tabela (nome, estado, coordenadas em graus/minutos/segundos, observação) trazida pelo usuário na conversa, **sem citação de fonte primária** — inclusive a própria tabela já marcava dois casos como sem coordenada confiável em vez de estimar. As coordenadas abaixo são só a conversão aritmética de GMS para decimal do que a tabela trazia; nenhuma foi conferida contra ICMBio ou Marinha do Brasil.

| Local | Latitude | Longitude | Situação |
|---|---|---|---|
| `fernando-de-noronha-pe` | −3,8522 | −32,4208 | 🚨 **Pendente de verificação em fonte oficial** |
| `atol-das-rocas-rn` | −3,8631 | −33,8061 | 🚨 **Pendente de verificação** (coordenada e município) |
| `parcel-manuel-luis-ma` | −0,9133 | −44,3194 | 🚨 **Pendente de verificação em fonte oficial** |
| `parrachos-de-maracajau-rn` | −5,4025 | −35,2969 | 🚨 **Pendente de verificação em fonte oficial** |
| `areia-vermelha-pb` | −7,0047 | −34,8125 | 🚨 **Pendente de verificação em fonte oficial** |
| `apa-costa-dos-corais` | *(nula)* | *(nula)* | Área de proteção que cruza 12 municípios entre AL e PE — não é um ponto; qualquer lat/lon único aqui seria inventado |
| `recife-de-fora-ba` | *(nula)* | *(nula)* | A tabela de origem não trazia coordenada exata ("não vou inventar um número aqui") — mantido nulo pela mesma razão |

⚠️ **`abrolhos-ba` já existia e foi deixado de fora desta migration.** A tabela trazia 17°57'47" S, 38°42'12" W para o mesmo local, que converte para −17,9631/−38,7033 — cerca de 1,5 km da coordenada já gravada (−17,972/−38,688). A migration não decide qual prevalece; isso fica pendente de decisão manual, não é assumido automaticamente.

Nenhum dos sete entra no pipeline de ingestão sem coordenada válida (`LocalRecife.tem_coordenadas`), então `apa-costa-dos-corais` e `recife-de-fora-ba` ficam cadastrados sem série ambiental possível até que uma coordenada real apareça.

#### 2.3.1.1 ✅ Os cinco com coordenada foram ingeridos e entraram no modelo — 12/08/2026

Ingestão rodada para os cinco: **2020-01-01 a 2026-08-11, 19.278 medições por local**, das duas fontes (NOAA CRW e Copernicus), pelo mesmo caminho e com a mesma proveniência por valor dos três originais. O banco passou a ter **8 locais com série** e 2 sem.

⚠️ **Ingerir não retreina, e a distância entre as duas coisas ficou visível.** O artefato em `dados/modelos/` continuou declarando três locais nos metadados, e `PainelRiscoDetail` responde **404 com motivo** para todo local fora dessa lista — então os cinco recifes com série completa apareciam no site **sem previsão**, corretamente. Remedido e regravado em 12/08 depois de medir; os números estão em [RESULTADOS.md](RESULTADOS.md) §25.

🚨 **As coordenadas continuam pendentes de verificação, e agora há dado extraído em cima delas.** A tabela acima não muda: nenhuma das cinco veio de fonte primária citável. A consequência que muda é o tamanho — antes era um cadastro sem lastro, agora são **96.390 medições** posicionadas por uma conversão de graus/minutos/segundos sem fonte declarada. Enquanto assim, a série desses cinco **não é citável academicamente**, pela mesma regra já aplicada a Picãozinho e Porto de Galinhas na §2.3. Conferir contra ICMBio continua sendo a pendência, e ela ficou mais cara de adiar: mudar uma coordenada depois implica reingerir o local inteiro, porque a `bbox` muda.

⚠️ **`abrolhos-ba` continua com a divergência de ~1,5 km registrada e não resolvida**, e a decisão de não mexer ficou mais fácil de justificar: as 19.278 medições dele foram extraídas na `bbox` da coordenada gravada. Trocar a coordenada sem reingerir deixaria a série descrevendo um ponto e o cadastro declarando outro.

### 2.4 Status de conservação — ✅ esquema corrigido em 31/07/2026, dados preenchidos em 04/08/2026

Os valores do antigo campo `status_conservacao` ("Vulnerável", "Criticamente ameaçado", "Pouco preocupante", "Não avaliado") seguiam a nomenclatura da **IUCN Red List** — https://www.iucnredlist.org — mas **sem registro de qual avaliação, de que ano**. `fonte_url` estava vazio nas **nove** espécies.

⚠️ **Era o campo mais grave do banco para estar sem procedência**, por um motivo específico: é o único que uma pessoa vai **citar**. Todo o resto do acervo ou é descritivo (nome comum, descrição) ou já carrega proveniência por valor.

**O que uma categoria sem ano esconde**, com o exemplo do próprio acervo:

| Espécie | Categoria | Quando |
|---|---|---|
| `Dendrogyra cylindrus` | **Vulnerável (VU)** | de 2008 a 2022 |
| `Dendrogyra cylindrus` | **Criticamente Ameaçada (CR)** | desde 2022 |

As duas afirmações estão certas — em anos diferentes. Sem o ano, a tela não distingue *"é CR"* de *"era VU quando alguém digitou isto"*, e a segunda leitura envelhece sozinha.

**Correção aplicada (migração `0022`).** O texto livre virou os códigos oficiais da Lista Vermelha, com os campos que faltavam:

| Campo | Para quê |
|---|---|
| `iucn_categoria` | o código oficial (`VU`, `CR`…), não a tradução |
| `iucn_avaliado_em` | **o ano da avaliação publicada** |
| `iucn_versao` | a versão da Lista Vermelha (ex.: `2024-1`) |
| `iucn_taxon_id`, `fonte_iucn_url` | onde conferir |

🚨 **Consequência imediata e deliberada: o site parou de exibir categoria de conservação nas nove espécies**, porque nenhuma tem ano registrado. Não é regressão — é parar de afirmar o que não se consegue datar. A tela mostra *"categoria sem procedência registrada"* até alguém preencher.

⚠️ **A decisão mais delicada da migração: "Não avaliado" virou categoria vazia, e não `NE`.** As duas leituras — *"a IUCN avaliou e devolveu NE"* e *"quem digitou não consultou"* — são indistinguíveis no dado, e `NE` é uma **categoria real**. Pior: afirmá-la seria **provavelmente falso** para pelo menos duas das cinco espécies que tinham esse valor, já que `Holacanthus ciliaris` e `Ocyurus chrysurus` têm avaliação publicada. Inventar afirmação errada é pior que registrar lacuna. Há teste travando isso.

📌 **Pendência que fica: preencher os anos.** São 9 espécies. O GBIF devolve a categoria **sem o ano**, e por isso não substitui a consulta — reproduziria o defeito com aparência de fonte.

🚨 **O pedido de acesso à API da IUCN foi RECUSADO em 31/07/2026** (e-mail institucional, `@id.uff.br`) **e novamente em 04/08/2026** (e-mail pessoal) — as duas vezes sem motivo declarado, com o mesmo texto-modelo padrão, parágrafo enlatado sobre uso comercial e o IBAT. Duas tentativas com e-mails diferentes caindo na mesma recusa-padrão sugerem que o formulário está classificando o pedido como comercial, não que o e-mail usado seja o problema.

📌 **Próximo passo sobre a API em si:** contestar direto por `conservation.informatics@iucn.org`, explicando tratar-se de projeto acadêmico não-comercial (TCC) e que não é IBAT — em vez de reenviar o mesmo formulário.

📬 **Atualização de 05/08/2026:** contato com o IBAT-Alliance (parceiro oficial da IUCN, citado na recusa-padrão) obteve resposta humana de Mark Leckie (IBAT Programme Officer) — não mais o texto-modelo. Oferece conta gratuita não-comercial com acesso a mapas, KBAs, PCAs e dados da IUCN Red List, com resumo de biodiversidade num raio de 50 km por site cadastrado. ⚠️ **Isso parece ser busca por local (desenhar/subir um site → resumo num raio), não busca por nome de espécie** — precisa confirmar se serve para o caso de uso do projeto (categoria de uma espécie nomeada) ou só para o caso de uso deles (triagem de risco por área, típico de EIA). Se for por local, ainda é uma fonte candidata legítima para quando as ocorrências vierem do OBIS/GBIF por bbox do recife (§2.4.1) — daria espécie **e** categoria de conservação na mesma consulta.

#### 📬 Investigação do IBAT, 11/08/2026 — schema certo, cobertura da amostra errada

Conta criada como **Organisation** (não Personal), vinculada à UFF, com e-mail institucional — segue a mesma linha de argumento da contestação à IUCN. Testes feitos num site de exemplo (`abrolhos-ba`, buffer de 10 km, tipo "Direct Operations", já que nenhum "site type" da lista — todos de indústria extrativa/infraestrutura — descreve monitoramento acadêmico):

1. **A contagem por site é gratuita, mas só agregada.** O site de teste devolveu 7 PAs, 1.816 espécies, 0 KBAs — sem lista nomeada. Pela dica de UI do próprio KBA, esse raio é **fixo em 50 km**, independente do buffer escolhido ao criar o site.
2. **A lista nomeada é paga.** `Reports → New report → Disclosure Preparation Report` cobra **US$ 1.000** — não seguido adiante. `GIS Downloads → New GIS Download` calcula custo por área (PAYG) — não testado, pra não gerar cobrança.
3. **Existe uma amostra gratuita** (`Download GIS Sample`) — arquivo Esri File Geodatabase (`.gdb`), a camada `redlist` sozinha com ~2,7 GB, contendo três camadas: `IUCN_RL_Species_List` (tabela sem geometria), `IUCN_RL_Species_Points` e `IUCN_RL_Species_Ranges` (`MultiPolygon`).
4. ✅ **`IUCN_RL_Species_List` tem exatamente o schema que o projeto precisa**: `scientific_name`, `category`, `common_name`, `criteria`, `publication_yr`, `assessment_date`, `authority`, mais taxonomia completa — dá pra montar a citação inteira só com essa tabela, sem tocar nos polígonos.
5. 🚨 **Mas o conteúdo da amostra não cobre o projeto.** 1.207 linhas, span de vários táxons (peixe, ave, fungo, planta, molusco...) como demonstração de formato — **zero registros de `ANTHOZOA`** (a classe dos corais) e **nenhuma das nove espécies do projeto** está presente. É recorte de demonstração, não recorte por região/grupo.

**Como abrir um `.gdb` sem ArcGIS** (registrado porque não é óbvio): `pip install geopandas pyogrio`, depois `pyogrio.list_layers(caminho)` lista as camadas, e `pyogrio.read_dataframe(caminho, layer=nome)` lê uma camada sem geometria direto — mais robusto que `geopandas.read_file` pra tabelas não-espaciais, e evita depender do `fiona`.

📌 **Pendência real, não a de antes:** confirmar com o Mark Leckie se o dataset completo (não-amostra) cobre Anthozoa/Brasil com essa mesma estrutura de tabela, e se existe caminho não-comercial pra acessar só a tabela de atributos (sem os polígonos multi-GB, sem o relatório de US$1.000, sem o PAYG por área). Pergunta enviada em 11/08/2026 — ✅ **respondida em 12/08/2026, ver abaixo.**

#### 📬 Resposta do IBAT, 12/08/2026 — a lista nomeada não é necessariamente paga

Resposta de Mark Leckie (IBAT Programme Officer) à pergunta enviada em 11/08. Três coisas, nessa ordem de importância:

1. ✅ **"Your work fits within our definition of non-commercial"** — confirmação explícita, por escrito, de que o projeto se enquadra. Encerra a dúvida que vinha desde a recusa-padrão da IUCN de 31/07, que tratava o pedido como comercial (§2.4).
2. ⚠️ **Busca por nome de espécie não existe mesmo** — confirma a suspeita registrada em 05/08. O acesso é sempre por local. **Mas** a triagem de um site *lista as espécies com os campos que o projeto precisa*: categoria da Lista Vermelha, ano da avaliação e versão da Lista.
3. 🚨 **A conta foi atualizada com 10 *proximity reports* gratuitos.** Fluxo indicado: subir o site → rodar o *proximity report* → filtrar a lista de espécies até os corais de interesse.

🚨 **Isto corrige o item 1 da investigação de 11/08** ("a contagem por site é gratuita, mas só agregada; a lista nomeada é paga"). A conclusão estava certa *para a conta como ela estava* — o que a conta gratuita padrão devolvia era só `7 PAs / 1.816 espécies / 0 KBAs`, e o único caminho visível até a lista nomeada era o `Disclosure Preparation Report` de US$ 1.000. O *proximity report* é um terceiro caminho, que não aparecia como opção antes do upgrade manual da conta. **A barreira era de permissão, não de preço.**

⚠️ **Os 10 relatórios são um orçamento finito e sem renovação declarada.** São 3 locais de recife (§1) — cabe com folga, mas não cabe gastar em teste exploratório como se gastou o site `abrolhos-ba`. Cada corrida precisa ser de um local real, com o buffer já decidido.

⚠️ **O raio de 50 km continua sendo o recorte, e ele não é o recife.** A lista devolvida é *"espécies num raio de 50 km do ponto"*, não *"espécies neste recife"*. Para o uso imediato — pegar categoria/ano/versão de nove espécies que já se sabe quais são — isso é irrelevante, porque a lista é usada como **tabela de consulta**, não como inventário. O que o raio afeta é a **cobertura**: se uma das nove não aparecer na lista de nenhum dos três locais, esta via simplesmente não responde por ela, e isso não é o mesmo que "não avaliada".

📌 **Decisão pendente antes de usar o dado: qual `iucn_origem`.** Nenhum dos três valores atuais (`api`, `ficha`, `terceiro`) descreve isto honestamente. Não é a API da IUCN; não é a ficha aberta uma a uma; e chamar de `terceiro` — a categoria criada para Wikidata/GBIF, que *republicam* a categoria — apaga que o IBAT é parceiro oficial da IUCN distribuindo o dado sob licença, com a versão da Lista carimbada na entrega. A citação correta é diferente das três. Provável quarto valor, `ibat`, pelo mesmo motivo que `origem` existe (§2.4.1): sem distinguir a via, não há como auditar depois o que pode ser citado como quê.

📌 **O que esta via vale agora:** as nove espécies já foram preenchidas por `ficha` em 04/08, então o ganho imediato **não é preencher** — é (a) **conferência independente** dos seis valores datados, por uma via que não é a mesma pessoa relendo a mesma ficha, e (b) o **caminho de escala de §2.4.1**, para quando as ocorrências vierem do OBIS/GBIF por `bbox()` e o catálogo crescer sozinho: aí a lista por raio deixa de ser tabela de consulta e passa a ser exatamente a forma certa do dado.

✅ **As 9 espécies foram preenchidas em 04/08/2026 pelo caminho `ficha`** (migração `0024_conferencia_iucn_agosto_2026.py`), sem precisar da API — confirmando que a recusa não bloqueava o que havia de mais urgente. Cada uma foi aberta individualmente em `iucnredlist.org` (busca manual, não scraping em lote):

| Espécie | Categoria | Publicado em | Versão | Observação |
|---|---|---|---|---|
| `Mussismilia braziliensis` | **CR** (A3c) | 2022 | 2022 | confirma o erro achado em §2.4.2 |
| `Montastraea cavernosa` | LC | 2022 | 2022 | |
| `Dendrogyra cylindrus` | **CR** (A2bce) | 2022 | 2022-2 | |
| `Holacanthus ciliaris` | LC | 2010 | 2010 | ⚠️ ficha marcada "Needs updating" pela própria IUCN |
| `Sparisoma axillare` | **DD** | 2012 | 2012 | ⚠️ "Needs updating"; resolve o "❓ a confirmar" de §2.4.2 — **não é NT** |
| `Ocyurus chrysurus` | **DD** | 2016 | 2016-1 | ⚠️ "Needs updating" |
| `Muricea flamma` | **NE** | — | — | 🔎 busca em iucnredlist.org devolveu **zero resultados** em 04/08/2026 — não é lacuna de conferência, é conferência com resposta negativa |
| `Phyllogorgia dilatata` | **NE** | — | — | idem — zero resultados |
| `Condylactis gigantea` | **NE** | — | — | idem — zero resultados |

`iucn_origem='ficha'` e `iucn_consultado_em=04/08/2026` em todas. As três `NE` ficam sem `iucn_avaliado_em` (não existe ano de uma avaliação que não existe) e por isso continuam com `iucn_tem_procedencia=False` — o site não exibe nada nelas, o que é correto: não há categoria de risco a afirmar. As outras seis passam a exibir categoria.

⚠️ **Convenção usada para `iucn_avaliado_em`**: o ano **publicado** ("YEAR PUBLISHED" na ficha, o que aparece na citação formal), não o ano em que o assessment foi assinado ("DATE ASSESSED", tipicamente um ano antes — ex.: `Dendrogyra cylindrus` foi assinado em 2021 mas publicado em 2022). É a mesma convenção que o exemplo do próprio `Dendrogyra cylindrus` em §2.4 já usa.

Ainda pendente, e não coberto por este preenchimento: os dois caminhos que **não dependem da API** continuam valendo para quando o catálogo escalar — `iucn_origem='ficha'` não escala manualmente além de dezenas de espécies (§2.4.1), e `iucn_origem='terceiro'` (Wikidata/GBIF) é o que assume a partir daí.

### 2.4.1 Isto não escala como tarefa, e por isso virou relatório

⚠️ **A conferência manual serve para 9 espécies e quebra para 300.** E o caminho já planejado leva a 300: se as ocorrências passarem a vir do OBIS/GBIF pela `bbox()` do recife, o catálogo cresce sozinho, **cada espécie chegando sem procedência nenhuma**.

O que não escala não é conferir — é **lembrar de conferir**. Duas consequências no desenho:

**1. `iucn_origem` registra por qual via o dado veio** (`api`, `ficha`, `terceiro`). Sem isso o acervo vira mistura indistinguível, e não há como auditar o que pode ser citado como IUCN.

📌 A opção `terceiro` existe para ser honesta sobre um caminho que pode vir a ser usado: **Wikidata e GBIF publicam a categoria sem token, e são fonte legítima se declarada** — *"categoria segundo o Wikidata, referenciando a Lista Vermelha 2022-2, consultado em tal data"* é verdadeiro e datável. O que não pode é apresentá-la como se viesse da IUCN.

**2. O vencimento entra no relatório diário.** `db/atualizacao.py` já reporta o que envelheceu — série parada, modelo velho — e fica **calado quando está tudo bem**. As espécies entram lá:

```
(!) 9 de 9 especies sem procedencia de conservacao — o site nao exibe
    categoria nelas, porque nao consegue data-la. Ver "manage.py
    conferir_especies".
```

Com 300 espécies isso continua sendo uma linha por dia, em vez de uma tarefa que alguém precisa recordar.

⚠️ **São duas faltas diferentes, contadas em separado:**

| | O que significa |
|---|---|
| **sem procedência** | falta a categoria ou falta o ano — o site não exibe nada |
| **conferência vencida** | há categoria e ano, mas ninguém confere há mais de 2 anos |

A segunda é a que pegaria o defeito real. `Mussismilia braziliensis` não mudou no banco: **a IUCN publicou outra avaliação**, e o registro local continuou apontando para a antiga. Sem uma data de última conferência, isso é invisível por definição.

### 2.4.2 🚨 E um dos quatro valores estava simplesmente errado

Conferido em 31/07/2026, ao coletar a procedência (via Wikidata, ver ressalva original abaixo):

| Espécie | No banco (pré-migração) | Na IUCN | |
|---|---|---|---|
| **`Mussismilia braziliensis`** | **VU** | **CR** *(2022-2, táxon 133586)* | ❌ **errada** |
| `Sparisoma axillare` | NT | DD? | ❓ a confirmar |
| `Dendrogyra cylindrus` | CR | CR | ✅ |
| `Montastraea cavernosa` | LC | LC | ✅ |

É o coral-cérebro brasileiro, **endêmico**, a espécie que abre a página de Abrolhos — exibida dois degraus abaixo do que a IUCN registra.

Isso muda a natureza do problema: não era só *falta de lastro*, era **dado errado** — e do tipo que a ausência de ano esconde perfeitamente. Alguém digitou uma categoria que já foi verdadeira, a IUCN reavaliou, e nada no sistema tinha como perceber.

⚠️ **Consequência para a decisão de esconder tudo.** A alternativa "menos destrutiva" — manter as categorias exibíveis enquanto a procedência não chega — deixaria essa afirmação errada no ar, agora com aparência de dado revisado.

⚠️ **Esta conferência foi feita em Wikidata e busca**, não na ficha da IUCN, que recusa acesso automatizado (403) — scraping em lote, não navegação normal. É forte mas é cópia, e **nada foi gravado no banco com essa procedência** — seria repetir o defeito com outra fonte.

✅ **Confirmado direto na ficha da IUCN em 04/08/2026** (não mais Wikidata) — ver a tabela completa em §2.4. As quatro linhas acima batem: `Mussismilia braziliensis` é CR de fato, e `Sparisoma axillare` é **DD**, resolvendo o "❓ a confirmar".

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

### 4.1 GCBD — Global Coral-Bleaching Database ✅ integrada (passo 1) em 26/07/2026

**Instituição:** van Woesik, R.; Burkepile, D. — publicada em *Scientific Data* (2022)
**Repositório:** BCO-DMO, dataset 773466 — https://www.bco-dmo.org/dataset/773466
**DOI do artigo:** `10.1038/s41597-022-01121-y` · **DOI do dado:** `10.26008/1912/bco-dmo.773466.2`
**Forma de acesso:** download direto de CSV, sem credencial
**Licença:** **CC-BY 4.0**
**Arquivo:** `global_bleaching_environmental.csv` — 16,00 MB, SHA-256 `78cc014b1e7887f26f4c44a40d4d9213…`
**Data da coleta:** 25/07/2026
**Não versionado** — reconstruível pelo DOI; o comando está em [GCBD.md](GCBD.md).

**Citação obrigatória:**
> van Woesik, R., Burkepile, D. (2022). *Bleaching and environmental data for global coral reef sites from 1980-2020.* BCO-DMO. doi:10.26008/1912/bco-dmo.773466.2

**Para quê:** é a única fonte de **branqueamento observado em campo** do projeto, e portanto a base da entrega 2 — trocar o alvo de classificação por satélite (BAA) por observação real. Ver [VARIAVEIS.md](VARIAVEIS.md) §4.4.

**Cobertura brasileira medida em 25/07/2026, revista em 26/07/2026:** 384 registros, 137 sítios, **1994-03-15 a 2010-12-17**. Alvo utilizável em 313 linhas, que são **166 visitas** em 119 sítios (ver §6.17), com **53,0% de positivos**.

**Onde é lida:** [`ml/gcbd.py`](../backend/ml/gcbd.py), comando `manage.py treinar_gcbd`. O arquivo é procurado em `dados/global_bleaching_environmental.csv`, ou onde `GCBD_CSV` apontar.

⚠️ **Cinco achados que condicionam o uso**, todos medidos:

1. **O dado brasileiro termina em 2010** — sobreposição **zero** com a série ambiental já ingerida (2020 em diante).
2. **Picãozinho fica sem cobertura**: sítio GCBD mais próximo a **198 km**. Abrolhos, ao contrário, tem 41 sítios, o mais próximo a **1,3 km**.
3. **A base não traz salinidade nem oxigênio** — as duas variáveis que diferenciam este projeto. Responder a pergunta da entrega 2 exige ingestão nossa.
4. 🚨 **`ClimSST` tem valor-sentinela** — 262,15 K (−11 °C) em 115 dos 313 registros brasileiros. Removida do baseline. Ver §6.17.
5. **A unidade amostral é a visita, não a linha** — o arquivo traz uma linha por substrato. Ver §6.17.

📖 **Levantamento completo de viabilidade, em cinco etapas, em [GCBD.md](GCBD.md)** — estrutura, conteúdo, cobertura geográfica, custo de ingestão e plano recomendado. Os resultados do passo 1 estão em [RESULTADOS.md](RESULTADOS.md) §11–§14.

---

### 4.2 ERA5 — vento real ⏳ credencial configurada, conector não escrito

**Instituição:** ECMWF, para o Copernicus Climate Change Service (C3S)
**Acesso:** Climate Data Store — `https://cds.climate.copernicus.eu/api`, cliente `cdsapi==0.7.6`
**Credencial:** `~/.cdsapirc` — **fora do repositório**, mesma decisão do Copernicus Marine
**Variáveis:** `10m_u_component_of_wind`, `10m_v_component_of_wind` (**0,25°**, horário)
**Licença:** Copernicus — atribuição obrigatória
**Data do teste de conexão:** 26/07/2026

**Citação obrigatória — são duas:**
> Hersbach, H. et al. (2020). *The ERA5 global reanalysis.* Quarterly Journal of the Royal Meteorological Society, 146(730). doi:10.1002/qj.3803

> Hersbach, H. et al. (2023). *ERA5 hourly data on single levels from 1940 to present.* Copernicus Climate Change Service (C3S) Climate Data Store (CDS). DOI: 10.24381/cds.adbb2d47

Mais a frase exigida pela licença: *"Contains modified Copernicus Climate Change Service information [ano]"*.

✅ **DOI conferido na página oficial do CDS em 31/07/2026** (§6.15). ⚠️ O conector foi cancelado, mas **a citação continua obrigatória**: os dados baixados sustentam o resultado de [RESULTADOS.md](RESULTADOS.md) §20.

**Para quê:** o vento é a **única variável não térmica que dá sinal** no projeto — 2ª mais importante no passo 2 da entrega 2, coeficiente −0,72, *d* de Cohen −0,461 ([RESULTADOS.md](RESULTADOS.md) §17). E o vento atual do projeto é uma **constante inventada** (§6.7). É a maior assimetria aberta: a variável que funciona é a que não temos.

**Medido em 26/07/2026:**

1. ✅ **A conexão funciona e a fila não atrapalha** — `200` em **40,4 s** num pedido mínimo, com o ciclo `accepted → running → successful` em ~35 s. Era o risco número um: o CDS não devolve dado na hora, e sim por fila compartilhada.
2. ⛔ **O espelho ARCO na Google Cloud foi testado e descartado** — ver §6.19.
3. ⚠️ **A resolução é 0,25°, a mesma do produto de oxigênio** que virou a ressalva de [RESULTADOS.md](RESULTADOS.md) §18. Precisa ser medida contra o `Windspeed` do próprio GCBD antes de qualquer conclusão.

📖 **Levantamento em [ERA5.md](ERA5.md)** — credencial, conexão, o espelho descartado, as decisões de agregação e a validação de graça contra o GCBD.

---

### 4.2 Demais candidatas

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
| react-router-dom | 6.30.1 | Roteamento do SPA (substituiu a navegação por `useState`) | https://reactrouter.com |
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

### 6.13 `par.csv` com coordenadas irrecuperáveis
*(Corrigido em 25/07/2026 — a descrição anterior dizia que a coluna `par` era majoritariamente nula, o que estava errado. Medição real abaixo.)*

O arquivo tem 1.146.600 linhas e a coluna `par` está **63,3% preenchida** — os valores existem. O problema está nas coordenadas: `latitude` e `longitude` foram exportadas como `-17.187.504` e `-3.952.083`, com separador de milhar aplicado sobre o número decimal. Nenhuma linha converte para float, então **não há como saber a que pixel cada medição pertence**. Os valores são reais, mas não georreferenciáveis.

Consequência prática: **o projeto não tem PAR de superfície utilizável.** `par_recente.csv` também não serve — tem 1.331 valores da variável `PAR_error`, o campo de incerteza. Isso bloqueia o cálculo de `PAR_fundo = PAR × e^(−Kd × z)`, que depende de PAR na superfície. Resolver exige rebaixar o PAR (NOAA ERDDAP ou NASA OceanColor) com a exportação correta.

### 6.14 Catálogo público fictício — ✅ RESOLVIDO em 24/07/2026
**Resolução:** a migration `0016_remove_seed_ficticio_datasetcatalogo` apagou os 8 registros inventados, e o catálogo passou a ser construído a partir dos arquivos que existem de fato, por `python backend/manage.py inventariar_datasets`.

O inventário atual tem **9 datasets reais**, todos com tamanho e período **lidos do arquivo** e não digitados:

| Fonte | Dataset | Período real | Tamanho real |
|---|---|---|---|
| NOAA | Estresse térmico coralino (CoralTemp/DHW) | 2020–2025 | 75,17 MB |
| Met Office / Copernicus | SST série histórica | 1981–2023 | 0,65 MB |
| Copernicus | Temperatura potencial (`thetao`) | 2022–2025 | 0,06 MB |
| Copernicus | Salinidade (`so`) | 2022–2025 | 0,22 MB |
| Copernicus | Clorofila-a (`chl`) | 2021–2025 | 0,07 MB |
| Copernicus | pH (`ph`) | 2021–2025 | 0,06 MB |
| Copernicus | Oxigênio dissolvido (`o2`) | 1993–2025 | 0,51 MB |
| Copernicus | Nitrato (`no3`) | 1993–2025 | 0,54 MB |
| Copernicus | Atenuação da luz (`kd`) | 2023–2025 | 0,03 MB |

Garantias implementadas em `backend/aquaculture/inventario_datasets.py`:

- **Nada é digitado à mão:** tamanho e intervalo temporal vêm de `ler_metadados_arquivo()`.
- **`url_download` fica vazio** — o projeto não serve esses arquivos, então o card não exibe botão de download. Quando existir endpoint real (Fase D), o campo passa a ser preenchido.
- **Arquivo ausente vira registro desativado**, nunca um registro com números inventados. Como os CSVs não são versionados, um clone novo começa com o catálogo vazio — que é a descrição correta do seu estado.
- **Arquivos com problema de integridade ficam fora**, com motivo registrado em `EXCLUIDOS`: `ph.csv` (contém alcalinidade), `NOAA_DHW_monthly` (hemisfério errado), `par.csv` (corrompido), `par_recente.csv` (campo de erro), as duas duplicatas e `salinidade_recente.csv` (salinidade de fundo).
- Picãozinho e Porto de Galinhas aparecem com **zero datasets**, que é a verdade: o acervo só cobre Abrolhos.

Oito testes em `InventarioDatasetsTests` travam isso — incluindo um que falha se qualquer registro voltar a declarar o NCBI como fonte.

<details>
<summary>Registro histórico do problema</summary>

**Status agravado em 24/07/2026** (commit `34879bf`).

Originalmente os 8 datasets inventados viviam num array `DADOS_GERAIS` hardcoded em `frontend/src/App.js`. A refatoração moveu **os mesmos 8 registros fictícios** para o modelo `DatasetCatalogo`, semeados pela migration `0014_seed_datasetcatalogo` e servidos pelo endpoint real `/api/datasets/`.

Isso **piora** o problema de integridade: o que antes era claramente um mock de frontend agora tem tabela, API, serializer e página de catálogo — passa a parecer dado real.

| Fonte declarada | Título | Problema |
|---|---|---|
| Copernicus | Temperatura da superfície do mar — Abrolhos | `tamanho_mb` = 1843,2 (o `sst.csv` real tem 0,68 MB); período "Mar/2026" inventado |
| NOAA | Degree Heating Week — Banco dos Abrolhos | Metadados inventados |
| Projeto Coral Brasil | Inventário de biodiversidade recifal — Abrolhos | Não existe tal inventário |
| **NCBI** | Microbioma de água recifal — Picãozinho | 🚨 **Não há nenhum dado do NCBI no projeto** |
| **NCBI** | Banco genético de corais brasileiros — Abrolhos | 🚨 **Idem** |
| Projeto Coral Brasil | Mosaico fotográfico subaquático — Porto de Galinhas | Não existe |
| Projeto Coral Brasil | Relatório técnico de campo — Picãozinho | Não existe |
| Projeto Coral Brasil | Modelo preditivo de branqueamento — Costa Nordeste | Não existe |

Atribuir dados ao NCBI e a um "Projeto Coral Brasil" que não os produziu é, num trabalho acadêmico, atribuição falsa de fonte. **Antes do go-live é obrigatório** substituir o seed por um inventário do que realmente existe no banco, ou marcar os registros como demonstração de forma visível na interface.

A infraestrutura criada (`DatasetCatalogo`, `/api/datasets/`, `BancoDadosPage`) está correta e é exatamente o que a Fase D previa — o problema era só o conteúdo semeado.

</details>

### 6.16 ✅ RESOLVIDO em 25/07/2026 — o BAA estava sendo tratado como número contínuo na agregação espacial

Detectado em 25/07/2026, ao conferir por que Abrolhos aparecia com DHW 8,38 em 2024 e mesmo assim BAA máximo 3.

O conector pede uma bbox (0,5° × 0,5° ≈ **121 pixels**) e agrega por média diária. Isso é razoável para SST, DHW e HotSpot, que são contínuos. **Para o BAA, não é** — ele é uma categoria ordinal de 0 a 4 (0 sem estresse, 1 vigilância, 2 alerta, 3 Alerta Nível 1, 4 Alerta Nível 2).

Medição em Abrolhos, 2024-05-17 (todos os 121 pixels com valor, sem NaN):

| | Valor |
|---|---|
| BAA por pixel | 70 pixels em **3**, 45 em **4**, 6 em **2** |
| Média dos pixels | 3,3223 |
| Gravado no banco | **3,000** |

Dois problemas encadeados:

1. **A média de uma categoria não é uma categoria.** 3,32 não corresponde a nenhum nível de alerta definido pela NOAA.
2. **O valor gravado perde o evento.** 37% da área estava em Alerta Nível 2 — o nível em que a NOAA prevê mortalidade, não só branqueamento — e o registro diz Alerta Nível 1. Os sumários regionais da própria NOAA reportam o **nível máximo** da área, não a média.

Efeito colateral: a média espacial também quebra a relação determinística entre BAA e (HotSpot, DHW). Nesse mesmo dia, HotSpot médio 1,214 e DHW médio 8,022 satisfazem a regra de BAA 4, mas o BAA agregado diz 3 — porque a média de uma função não linear não é a função das médias. Isso **não** invalida a análise de circularidade da [VARIAVEIS.md](VARIAVEIS.md) §4, que foi feita no dado por pixel, onde a relação vale exatamente.

**Consequência para o modelo:** o BAA é o alvo da entrega 1. Um alvo que subestima sistematicamente o pico de estresse ensina o modelo a subestimar também.

**Correção aplicada em 25/07/2026.** A regra de agregação deixou de ser uniforme: `ConectorNoaaCrw.AGREGACAO` declara a regra por variável, e só as contínuas caem no padrão (média).

| | Antes | Depois |
|---|---|---|
| SST, DHW, HotSpot, anomalia | média | média *(inalterado)* |
| **BAA** | média | **máximo** |
| extensão do alerta | — | **`baa_area_alerta`**, nova variável |

Em 17/05/2024 a nova regra grava BAA 4 e `baa_area_alerta` = 115/121 = **0,950**, o que confirma que o Alerta Nível 2 daquele dia era evento de recife inteiro e não artefato de um pixel.

📖 **A explicação completa — por que média de categoria ordinal é errada, por que máximo e não moda, e por que a fração de área precisa acompanhar o máximo — está em [VARIAVEIS.md](VARIAVEIS.md) §4.5**, com exemplo trabalhado. Aqui fica o registro de proveniência; lá, o raciocínio.

#### Efeito medido — backfill reexecutado em 25/07/2026

43.038 medições, três locais, 2020-01-01 a 2026-07-24, pelo espelho PACIOOS. São 7.173 por variável = (2.397 dias − 6 datas ausentes do produto) × 6 variáveis, o que fecha com as lacunas já documentadas na §1.1.

| Nível | Antes (média) | Depois (máximo) | Δ |
|---|---|---|---|
| 0 | 4.509 | 3.961 | −548 |
| 1 | 2.010 | 2.241 | +231 |
| 2 | 344 | 373 | +29 |
| 3 | 147 | 229 | +82 |
| 4 | 160 | **369** | **+209** |

**O Alerta Nível 2 mais que dobrou** — é precisamente a classe que a média apagava, e a que mais importa, por ser onde a NOAA prevê mortalidade e não só branqueamento.

`baa_area_alerta`: 7.173 valores, nenhum nulo, faixa 0–1, média 0,048; 312 dias com mais de metade do recife em Alerta Nível 1 ou acima.

**Verificação de consistência interna.** Em 17/05/2024 em Abrolhos o banco agora grava BAA 4 com DHW 8,02. A regra da NOAA define Alerta Nível 2 a partir de DHW ≥ 8: os dois campos **voltaram a concordar**. Sob a média, o BAA dizia 3 e contradizia o DHW do próprio registro — o efeito colateral descrito acima. A concordância se explica pela `baa_area_alerta` de 0,950: com o recife quase todo no mesmo estado, máximo e média espacial convergem.

**Padrão anual em Abrolhos** (dias em Alerta Nível 1 ou acima / fração máxima da área):

| Ano | Dias | Área máx. |
|---|---|---|
| 2020 | 7 | 0,157 |
| 2021 | 0 | 0,000 |
| 2022 | 15 | 0,347 |
| 2023 | 0 | 0,000 |
| **2024** | **71** | **0,950** |
| **2025** | **51** | **1,000** |
| 2026 (até 24/07) | 0 | 0,000 |

2024 e 2025 reproduzem o evento global de branqueamento; 2021 e 2023 ficam zerados. Em 2025 a fração chega a **1,000** — recife inteiro em alerta —, informação que a série agregada por média não conseguia representar.

A ingestão sofreu 10 `ReadTimeout` do PACIOOS, todos absorvidos pela retentativa. Nenhum bloco perdido.

#### Quanto a agregação afasta o banco da regra publicada — medido em 30/07/2026

O parágrafo acima sobre o efeito colateral (a média espacial quebra a relação determinística entre BAA e HotSpot/DHW) estava certo e era **qualitativo**: dizia que a relação quebra, não quanto. Ao construir a linha de base da NOAA foi preciso saber o tamanho, e ele foi medido nos 7.173 dias das três séries.

Regra publicada — `HotSpot ≥ 1 °C` **e** `DHW ≥ 4 °C·semana` ⟺ `BAA ≥ 3`, Alerta Nível 1 — aplicada aos valores **agregados** do banco:

| | regra diz **não** | regra diz **sim** |
|---|---|---|
| `BAA < 3` no banco | 6.575 | **0** |
| `BAA ≥ 3` no banco | 261 | 337 |

Concordância **0,964**, e o desvio é inteiramente de um lado: **a regra nunca dispara onde o BAA agregado não disparou**, e perde 261 dos 598 dias de alerta (43,6%).

O sentido único é consequência direta da regra de agregação da tabela acima — máximo para o BAA, média para HotSpot e DHW. O máximo é sempre ≥ a média, então o BAA do recife pode subir sem que nenhuma das duas médias alcance seu corte; o contrário não acontece.

Duas medições laterais, do mesmo dia:

- **Só `DHW ≥ 4`, sem a metade do HotSpot:** concordância cai para 0,903, e aparecem **479 dias** em que a regra dispararia e o BAA não. Nos 479, o HotSpot está abaixo de 1 — são os dias em que a água já esfriou e o calor acumulado ainda não decaiu. É a metade da regra que evita o alarme tardio.
- **Os 215 dias com `BAA ≥ 3` e `DHW < 4`:** DHW mediano 2,39 e HotSpot mediano 1,13. Recife com um pedaço em alerta e média morna.

⚠️ **Isto não é defeito de nenhum dos dois lados**, e nada aqui pede correção. `BAA = máximo` responde "qual o pior pedaço do recife"; `DHW = média` responde "quanto calor o recife acumulou em média". A regra da NOAA é exata **por pixel** — ver [VARIAVEIS.md](VARIAVEIS.md) §4.2 — e é a agregação, escolhida deliberadamente nesta seção, que faz as duas perguntas divergirem em escala de recife.

**Consequência prática, em [RESULTADOS.md](RESULTADOS.md) §24.2:** o corte publicado de `DHW ≥ 4` chega tarde na escala do recife. Ele pega 10 dos 19 episódios; movido para `DHW ≥ 1` — mantido o HotSpot — pega 15, com precisão 0,880. O número 4 continua correto para a grade de 5 km da NOAA; o que ele não é é transferível para uma média de bbox sem ser remedido.

### 6.21 Os arquivos defeituosos foram apagados — ✅ 28/07/2026

Os sete arquivos que as seções anteriores declaram inutilizáveis foram
removidos do disco. **179,9 MB, 72% da pasta `backend/dados/`.**

| Arquivo | MB | Por quê (seção) |
|---|---|---|
| `dhw_5km_6006_cdf9_04d9.csv` | 78,8 | duplicata byte-a-byte de `dhw.csv` |
| `par.csv` | 58,6 | coordenadas com separador de milhar, não georreferenciáveis (§6.13) |
| `NOAA_DHW_monthly_...csv` | 42,3 | coordenadas no Mar Vermelho (§6) |
| `ph.csv` | 0,1 | contém alcalinidade, não pH (§6.14) |
| `par_recente.csv` | 0,1 | campo de incerteza, não a medida (§6.12) |
| `salinidade_recente.csv` | 0,1 | salinidade de fundo, não superfície (§6.10) |
| `turbidez_recente.csv` | 0,0 | duplicata byte-a-byte |

**O que justifica apagar sem perda: o conhecimento sobre eles não estava
neles.** Está aqui, e em `inventario_datasets.EXCLUIDOS`, que continua listando
os sete com o motivo mesmo depois de os arquivos sumirem. Um arquivo defeituoso
guardado "por precaução" é só um convite a alguém usá-lo sem ler a ressalva.

⚠️ **Nenhum estava no Git** — a remoção é definitiva, sem histórico para
recuperar. Foi confirmada explicitamente antes de executar.

#### Os 7 órfãos: abertos um a um, e então removidos

Eram arquivos que não estavam **nem** catalogados **nem** declarados
defeituosos — ninguém os tinha aberto. Como a §6.14 deixou a regra de não
decidir sobre arquivo pelo nome, cada um foi lido antes de sair:

| Arquivo | Contém | Veredito |
|---|---|---|
| `..._bgc-car_...291619.csv` | `ph` | **duplicata de valor** do pH catalogado: MD5 diferente pelo cabeçalho, mas os **1.501 valores são idênticos** |
| `clorofila_recente.csv` | `chl` | produto de **análise** contra a reanálise de `clorofila.csv`; sobrepõem 1.501 datas, diferença até **0,0044** |
| `nitrato_recente.csv` | `no3` | idem; 1.430 datas, diferença até **0,235 mmol/m³** |
| `..._bgc-car_...196586.csv` | `dissic` | carbono inorgânico dissolvido — sem nome canônico |
| `..._bgc-bio_...434573.csv` | `nppv` | produtividade primária — nunca avaliada |
| `..._bgc-co2_...112534.csv` | `spco2` | pCO₂ de superfície — nunca avaliada |
| `..._phy_...183519.csv` | `thetao` horário | temperatura a **13,47 m**, recusada do vocabulário em 28/07 |

⚠️ **Os dois `_recente` confirmam a §6.11 com número.** Não eram duplicatas:
são o produto de **análise** ao lado do de **reanálise**, e para a mesma data e
o mesmo ponto o nitrato diverge em até **0,235 mmol/m³**. Essa medição é o que
valia guardar — não os arquivos. Ela está aqui; eles não estão mais.

Todos entraram em `inventario_datasets.EXCLUIDOS` com o motivo **antes** de
serem apagados. Total: mais 1,8 MB.

#### O que **não** foi apagado

Os **9 arquivos catalogados** (78 MB). Apagá-los **esvazia a página "Banco de
Dados"** (§6.20) — é decisão de produto, não faxina.

A pasta saiu de **251 MB para 78 MB**, e o que sobrou é exatamente o que a
página inventaria.

#### Três comandos legados removidos junto

| Comando | Por quê |
|---|---|
| `carregar_historico` | lia os CSVs apagados e o `.pkl` removido, e fazia `StatusPredicao.objects.all().delete()` antes de cada carga |
| `coleta_de_dados` | buscava dados e **descartava** o resultado; substituído por `ingerir` |
| `backend/ml_models/treinar_modelo.py` | o treinador legado, com os marcadores `[cite: N]` da §6.3 — não confundir com `manage.py treinar_modelo`, que é novo e não tem relação |

⚠️ **As docstrings do código atual continuam citando o
`carregar_historico.py`**, e isso é proposital: elas explicam *por que* a
validação física recusa zero, *por que* a persistência é idempotente, *por que*
o DHW não é recalculado. O arquivo saiu; a razão de o código atual ser como é
não sai com ele.

#### 🚨 O `gerar_relatorio` produzia um relatório executivo falso

Eu o tinha poupado supondo que servisse ao texto do TCC. Rodei antes de decidir,
e o que ele escreve em `relatorios_gerados/RELATORIO_EXECUTIVO.txt` é:

```
RELATÓRIO EXECUTIVO (2020 - 2025)
PROJETO CORAL BRASIL - ABROLHOS

1. ESCOPO DO RELATÓRIO
Período: 10/04/2026 a 15/04/2026 (3 dias)

3. SITUAÇÃO ATUAL (15/04/2026)
Temp. Superfície: 29.00°C
Luz Bentônica:    30.4 (µmol/m²/s)
Turbidez (Kd):    0.220
RISCO HOJE:       69.0%
```

Cinco defeitos num arquivo de 900 bytes, e **nenhum deles gera erro**:

| O que diz | O que é |
|---|---|
| "2020 – 2025" no título | os dados são de **abril de 2026** |
| "Período: 3 dias" | contradiz o próprio título, na linha seguinte |
| "SITUAÇÃO ATUAL" / "RISCO HOJE" | dado de **três meses e meio atrás** |
| "PROJETO CORAL BRASIL — **ABROLHOS**" | as 3 linhas são de **três recifes diferentes**, tratadas como uma série |
| "Luz Bentônica" e "Turbidez" | variáveis com **zero linhas** no banco (§6.21) |

E ele termina imprimindo *"Relatório 2020-2025 gerado com sucesso!"*.

**Removido.** É o oposto exato do que este projeto declara fazer: em vez de
recusar-se a mostrar um número que não sustenta, ele monta um documento com
aparência oficial a partir de três linhas de demonstração — e chama de sucesso.
Um `.txt` desses circulando é pior que nenhum relatório, porque parece resultado.

#### `/api/monitoramento/`, `neo4j_seed` e `setup_graph` também saíram

| Removido | Por quê |
|---|---|
| `/api/monitoramento/` | servia os 3 registros de `StatusPredicao`; o frontend migrou para `/api/painel-risco/` em 27/07 |
| `neo4j_seed` | derivava o grafo de `StatusPredicao`; substituído por `neo4j_projetar`, que deriva do PostgreSQL |
| `db/setup_graph.py` | só delegava para `neo4j_init` + `neo4j_seed` |

⚠️ **`neo4j_seed` era o mais perigoso dos três**, e não por estar errado: ele
funcionava. O problema é que existiam **dois caminhos de escrita no mesmo
grafo** — e o legado sobrescreveria a projeção com os dados de abril de 2026.
Ficou um teste que falha se o par voltar.

#### O que ficou de pé — e por que não bastava

O **modelo `StatusPredicao`** continuou existindo, com os 3 registros mais o
global. Removê-lo era mudança de esquema — migração, e mais admin, `code_sync`,
`neo4j_schema` e o campo `monitoramento_recente` que `/api/locais/<slug>/`
ainda devolvia.

🚨 **✅ REMOVIDO em 30/07/2026, e a decisão de adiar tinha um custo maior do que
o registrado acima.** Aposentar o endpoint não aposentou o dado: os mesmos 4
registros de demonstração continuaram saindo por `monitoramento_recente`, com
`risco_integrado` e `nivel_alerta` — dois campos com nome de resultado e
nenhuma conta por trás. O parágrafo original tratava isso como pendência de
esquema; era **um problema de proveniência ativo**, servido por HTTP.

E havia um segundo, não notado até agora: `possui_painel_risco` era
`bool(StatusPredicao)` **com queda para o registro global**. Como o global
existia, o campo respondia `true` para **qualquer** recife cadastrado —
inclusive um recém-criado, sobre o qual `/api/painel-risco/<slug>/` responde
404 por decisão explícita. A API afirmava cobertura que ela mesma negava uma
rota adiante.

Agora o campo sai da lista `locais` dos metadados do artefato, a mesma fonte
que decide o 404, e vale `false` quando não há artefato. Conferido ao vivo em
30/07/2026: os dois endpoints declaram o mesmo conjunto de três recifes.

| Também caiu junto | O que era |
|---|---|
| 4 consultas `UPSERT_*` e 8 funções do `neo4j_schema.py` | a camada de escrita do `neo4j_seed`, **chamada só pelos próprios testes** — o que lhe dava aparência de coberta e viva |
| a cascata de `utils/recifes.js` | `risco_atual`, `nivel_alerta_atual`, `monitoramento_recente` e `quantidade_predicoes`, computados em `??` de seis níveis e **renderizados por nenhum componente** |

⚠️ O `FALLBACK_RECIFES` versionado no `.js` também carregava `risco_atual` —
número de demonstração dentro de arquivo de código, que sobrevive a qualquer
limpeza do banco e reaparece justamente quando a API cai. Regenerado, e há
teste que falha se voltar.

### 6.20 O catálogo anunciava nove conjuntos; a API servia três — ✅ RESOLVIDO em 27/07/2026

Descoberto ao verificar se o endpoint `banco-de-dados` do checklist de go-live
existia. Ele existia (`/api/datasets/`), e servia **9 registros honestos sobre
os arquivos** — mas a página os apresentava como se fossem o acervo consultável
do projeto. Não eram.

| Dataset do catálogo | Medições no banco |
|---|---|
| `noaa_crw_dhw_abrolhos` | **14.346** |
| `cmems_salinidade_abrolhos` | **2.397** |
| `cmems_oxigenio_abrolhos` | **2.397** |
| `metoffice_sst_l4_abrolhos` | **0** |
| `cmems_thetao_abrolhos` | **0** |
| `cmems_clorofila_abrolhos` | **0** |
| `cmems_ph_abrolhos` | **0** |
| `cmems_nitrato_abrolhos` | **0** |
| `cmems_kd490_abrolhos` | **0** |

**Seis dos nove não têm uma única linha em `MedicaoAmbiental`**, e apareciam na
página com título, resumo, formato, período e tamanho — indistinguíveis dos
três reais.

#### A distinção que faltava, e por que ela é sutil

Nenhum dos seis é invenção — este é o ponto que separa 6.20 de [6.14](#614-catálogo-público-fictício--resolvido-em-24072026). Os arquivos
existem em `backend/dados/`, e o inventário lê deles o tamanho e o período. O
que estava errado **não era nenhum número**: era a página não dizer que
*"período do arquivo em disco"* e *"até quando a API tem dado"* são perguntas
diferentes.

E há um caso em que os dois divergem de forma alarmante: `noaa_crw_dhw` declara
fim em **2025-11-30**, porque é onde o CSV termina. A série no banco vai até
**2026-07-24** — sete meses adiante. O catálogo estava, ao mesmo tempo,
anunciando dado que não existe e **escondendo dado que existe**.

#### A causa é estrutural

Cobertura estava **gravada**. É o mesmo padrão que já custou caro três vezes
neste projeto — o `.docx`, o `.joblib` e o grafo do Neo4j — e a regra que saiu
de lá vale aqui sem emenda: **cópia guardada envelhece em silêncio**.

Agora a cobertura é **derivada a cada resposta**, em
`backend/aquaculture/cobertura.py`, a partir de uma agregação sobre
`MedicaoAmbiental`. Ela não tem como divergir do banco porque não é guardada em
lugar nenhum.

#### O que a API passou a devolver

```json
"cobertura": {
  "espelhado": true,
  "n_medicoes": 14346,
  "variaveis": ["baa", "baa_area_alerta", "dhw", "hotspot", "sst", "sst_anomalia"],
  "data_inicio": "2020-01-01",
  "data_fim": "2026-07-24",
  "consulta": "/api/medicoes/?fonte=noaa_crw&local=abrolhos-ba&variavel=baa&..."
}
```

⚠️ **`consulta` não é conveniência — é o recibo.** Sem ele, "14.346 medições" é
uma afirmação que ninguém consegue conferir. Verificado nos três: o `count` do
`/api/medicoes/` bate exatamente com o `n_medicoes` anunciado, e há teste
travando a igualdade.

Os seis externos devolvem `espelhado: false` com o motivo, e **não** oferecem
consulta. Um catálogo pode e deve apontar para produtos que o projeto não
espelha; o que não podia era não dizer qual é qual.

#### Três estados na tela, e nenhum implica o outro

| Estado | Significa |
|---|---|
| **Disponível nesta API** | o projeto serve, com o link que prova |
| **Referência externa** | existe na fonte original; o projeto não espelha |
| **Não verificada** | o servidor não informou (catálogo antigo, ou o fallback local) |

O terceiro existe porque afirmar ausência a partir de silêncio seria o mesmo
erro em outra direção.

#### Uma pendência que isto revela

`backend/dados/` é a pasta legada que nada mais lê e que o roadmap manda apagar
(~260 MB). No dia em que ela sumir, **os nove registros viram `ativo=False`**
pela regra 2 do inventário, e a única cobertura que sobrevive é a derivada. Ou
seja: apagar a pasta esvazia a página do catálogo. Isso precisa ser decidido, e
não descoberto.

29 testes: 21 em `aquaculture/testes_cobertura.py` e 8 em
`frontend/src/components/DatasetCard.test.jsx`.

### 6.15 ✅ RESOLVIDO em 31/07/2026 — DOIs dos produtos CMEMS e do ERA5

Cada produto Copernicus tem DOI próprio, exigido para citação formal, e nenhum
estava registrado. Era o único item marcado como **bloqueante para submissão**.

| Fonte | Produto | DOI |
|---|---|---|
| CMEMS | `GLOBAL_MULTIYEAR_PHY_001_030` | 10.48670/moi-00021 |
| CMEMS | `GLOBAL_ANALYSISFORECAST_PHY_001_024` | 10.48670/moi-00016 |
| CMEMS | `GLOBAL_MULTIYEAR_BGC_001_029` | 10.48670/moi-00019 |
| CMEMS | `GLOBAL_ANALYSISFORECAST_BGC_001_028` | 10.48670/moi-00015 |
| C3S | ERA5 hourly data on single levels from 1940 to present | 10.24381/cds.adbb2d47 |

Detalhe, modelo de citação e a ressalva sobre a série emendada em §7.2; o ERA5
em [ERA5.md](ERA5.md).

⚠️ **Dois achados ao coletar**, e os dois mudam a lista de referências:

1. **São quatro produtos CMEMS, não dois.** Salinidade e oxigênio parecem duas
   fontes, mas cada série **emenda reanálise e análise** — a reanálise termina
   meses atrás e a análise cobre até ontem. Citar só a reanálise omitiria a
   fonte exatamente dos dias que o painel usa.
2. **O ERA5 continua precisando de citação mesmo com o conector cancelado.** Ele
   não está no pipeline, mas os dados baixados dele **sustentam um resultado
   publicável** — a derrubada do efeito do vento ([RESULTADOS.md](RESULTADOS.md)
   §20). Fonte descartada como insumo não é fonte descartada como evidência.

### 6.17 ✅ TRATADO em 26/07/2026 — três defeitos no GCBD, detectados ao usá-lo

Medidos em 26/07/2026, ao integrar a base (§4.1). Nenhum aparece na
documentação do GCBD; todos aparecem quando se olha o dado.

#### (a) 🚨 `ClimSST` traz ausência codificada como número

`ClimSST` — a climatologia de SST do sítio — vale **exatamente 262,15 K em 115
dos 313 registros brasileiros (36,7%)**.

262,15 K são **−11 °C**. Num recife tropical, isso não é climatologia.

A origem fica clara na aritmética:

```
262,15 K  −  273,15  =  −11,00 °C
```

Ou seja: alguém tinha `-11` como código de "sem dado" em Celsius e converteu
para Kelvin junto com os valores reais. O código de falta virou uma temperatura
plausível para um programa, e absurda para um oceanógrafo.

**Consequência se não tratado:** o modelo aprenderia que 37% dos recifes
brasileiros têm climatologia ártica — e, pior, que essa característica separa
dois grupos de sítios, virando um identificador acidental.

**Tratamento:** `ClimSST` está em `COLUNAS_RECUSADAS` em
[`ml/gcbd.py`](../backend/ml/gcbd.py), e o valor 262,15 vira `NaN` no
carregamento (`SENTINELAS`). Dois testes travam a decisão.

⚠️ O plano registrado em [GCBD.md](GCBD.md) **recomendava `ClimSST`** como uma
das três variáveis do baseline. A recomendação foi escrita a partir da lista de
colunas, não da distribuição delas — e não sobreviveu à medição.

#### (b) `SSTA_Mean` é constante

Vale **0,0 em todos os 313 registros brasileiros**. Uma coluna sem variância não
pode informar nada e ainda consome um grau de liberdade. Também recusada.

#### (c) A unidade amostral não é a linha

O arquivo traz **uma linha por substrato amostrado** na mesma visita:

| Site_ID | Date | Substrate_Name | Percent_Bleaching |
|---|---|---|---|
| 1653 | 2005-04-05 | Hard Coral | 2,0 |
| 1653 | 2005-04-05 | Nutrient Indicator Algae | 2,0 |

Duas linhas, uma observação. Medido: **0 de 166 visitas** divergem em
`Percent_Bleaching`, e **0** divergem em qualquer variável térmica.

**Consequência se não tratado:** n inflado em **1,9×** (313 em vez de 166), com
cópias exatas da mesma visita caindo nos dois lados da validação — o que
inventaria desempenho sem que nada no resultado denunciasse.

**Tratamento:** `agregar_por_visita`, com quatro testes.

> Os três são o mesmo tipo de defeito que §6.3 (alcalinidade usada como pH) e
> §6.2 (hemisfério errado): dado que o programa aceita e o fenômeno não. É a
> razão de esta seção existir.

### 6.18 A janela ambiental do GCBD vem de longe do recife, e isso é gravado

Medido em 26/07/2026, ao extrair salinidade e oxigênio para as 166 visitas
(§4.1). Não é defeito da fonte — é limitação de resolução, e ela precisa
aparecer em qualquer resultado que dependa desses valores.

**69 das 166 visitas estão a menos de 1 km da costa** (mediana 2,3 km). A grade
do produto de oxigênio é **0,25° ≈ 28 km**; a de salinidade, 0,083° ≈ 9 km. Um
recife costeiro pode não ter nenhuma célula de oceano em cima dele — as células
próximas são máscara de terra.

A extração busca do raio mais justo para o mais largo e para no primeiro que
devolve oceano:

| Raio | ~km | Sítios atendidos (salinidade) | Sítios atendidos (oxigênio) |
|---|---|---|---|
| 0,15° | 17 | 118 | 99 |
| 0,30° | 33 | 119 | **119** |
| sem dado | | **0** | **0** |

**Nenhum sítio ficou sem dado.** Mas **20 sítios só têm oxigênio a até 33 km do
recife** — e o oxigênio perto de um recife costeiro raso é justamente onde a
diferença com o mar aberto seria maior.

**O que foi feito:** cada linha do cache grava `raio_graus` e `n_celulas`, além
do `dataset_id`. Um valor colhido a 33 km não é o mesmo que um colhido em cima
do recife, e a distinção fica auditável valor a valor em vez de virar nota de
rodapé.

⚠️ **Isto é uma limitação a declarar no trabalho**, não um problema resolvido.
Se as variáveis não térmicas mostrarem sinal fraco, "a resolução do produto é
grosseira demais para um recife costeiro" é uma explicação concorrente que os
dados atuais não permitem descartar.

### 6.19 ⛔ O espelho ARCO do ERA5 foi testado e não serve — o motivo é o formato

Medido em 26/07/2026, ao avaliar o ERA5 (§4.2).

O CDS entrega o dado **por fila**: submete-se um pedido, ele espera, e só então
baixa. Antes de aceitar isso, testei o **ARCO-ERA5** — um espelho público do
mesmo dado, em Zarr na Google Cloud, **sem credencial e sem fila**. Era a mesma
estratégia que deu certo com o PACIOOS (§1.1): ler do espelho, citar a origem, e
registrar qual servidor foi usado.

**Resultado: abortado após ~25 minutos sem conseguir nem abrir o dataset.**

**O motivo é estrutural, não passageiro.** O ARCO é fatiado (*chunked*) **por
instante de tempo**: cada pedaço do arquivo guarda o mapa do mundo inteiro numa
hora. Para quem quer "o vento global às 12h de hoje", é o formato ideal. Para o
que este projeto precisa — a série de **um ponto ao longo de anos** — é o pior
caso possível: exigiria uma leitura separada por hora, dezenas de milhares
delas.

> **O formato de armazenamento decide para que um dado serve, não só quanto ele
> pesa.** O ARCO tem exatamente os mesmos números do CDS e é inútil para este
> uso.

**Fica registrado como alternativa medida e descartada**, com o motivo, para que
ninguém a tente de novo daqui a alguns meses achando que é atalho. A decisão é:
**usar o CDS oficial**, cuja fila foi medida em ~35 s para pedido pequeno
([ERA5.md](ERA5.md) Etapa 2).

### 6.22 Contribuição pública de espécie não pode tocar proveniência — decisão de 08/08/2026

O site ganhou login e um formulário para visitantes aprovados proporem
espécie nova ou edição (fica pendente até um master aceitar — nunca aplica na
hora). A pergunta que isso levanta para este documento: **quais campos esse
formulário aceita?**

Resposta: `nome_cientifico`, `nome_comum`, `tipo`, `descricao`,
`credito_imagem`, `fonte_imagem_url`, `fonte_url` e `locais`. **Nunca**
`iucn_categoria`, `iucn_avaliado_em`, `iucn_versao`, `iucn_taxon_id`,
`fonte_iucn_url`, `aphia_id` ou `gbif_key` — os mesmos campos que a migração
`0022` (§2.4, acima) passou a exigir com data e origem depois do episódio de
`Mussismilia braziliensis` aparecer como VU no banco e CR na IUCN desde
2022-2. A lista
branca vale **igual para master**: quem quiser mudar categoria IUCN,
taxonomia ou foto continua indo pelo Django admin, nunca pelo formulário do
site.

O motivo de fechar isso mesmo para conta aprovada, e não só para conta
comum: um formulário público — ainda que moderado — é exatamente o tipo de
porta por onde entra uma categoria digitada de memória, sem data e sem link
para a ficha. Era isso que a migração `0022` fechou. Reabrir a mesma porta com
aprovação no meio ainda seria reabri-la — a aprovação audita *quem* editou,
não *se o dado tem procedência*.

Tentar mandar um desses campos no corpo da requisição não falha em silêncio:
`EspecieContribuicaoSerializer.to_internal_value` recusa com `400`, nomeando o
campo recusado. Coberto por teste (`CampoRecusadoTests`).

### 6.23 Decisão declarada em 11/08/2026 — para download, o projeto sempre serve o máximo que tiver, mesmo sem uso no modelo

**A política:** qualquer variável, de qualquer local, que chegue a
`MedicaoAmbiental` fica disponível para consulta e download em
`/api/medicoes/`, **independente de o modelo de predição usá-la ou não**. O
modelo consome só quatro (`sst`, `dhw`, `salinidade`, `oxigênio`, via
`ml/dataset.py::VARIAVEIS_BASELINE`); o banco de dados do site — o que fica
disponível para baixar — não é o mesmo contrato que o do modelo, e não deve
encolher para caber nele.

**Já é verdade hoje, por construção, não por filtro removido.**
`MedicaoAmbientalList.get_queryset()` nunca restringiu por variável — os
filtros (`local`, `variavel`, `fonte`, `de`/`ate`, `qualidade`) são todos
opcionais e todos definidos por quem consulta, nunca por uma lista fixa do
que "importa". `hotspot`, `baa` e `sst_anomalia` já são exemplos vivos disso:
nenhum dos três é feature do modelo (só alimentam o alvo e as linhas de
base — ver `ml/dataset.py::VARIAVEIS_DE_LINHA_DE_BASE` e
`PROIBIDAS_COMO_FEATURE`), e os três são baixáveis hoje pelo mesmo endpoint,
do mesmo jeito que `sst`/`dhw`. Travado por teste
(`test_variavel_nao_usada_pelo_modelo_continua_pesquisavel_e_baixavel`, em
`aquaculture/testes_api_medicoes.py`) para a política sobreviver a uma
refatoração futura da view.

⚠️ **O que essa política NÃO cobre: o catálogo `/api/datasets/`
(`DatasetCatalogo`).** Ele é outra coisa — uma lista curada de **nove
produtos-fonte** históricos (NOAA CoralTemp, os oito do Copernicus),
descrevendo os arquivos CSV legados em `backend/dados/`
(`aquaculture/inventario_datasets.py`), e **todos os nove estão fixados em
`local_slug='abrolhos-ba'`** (`LOCAL_PADRAO`). Consultar
`/api/locais/<slug>/datasets/` para Picãozinho, Porto de Galinhas, ou
qualquer um dos sete locais novos (§2.3.1) devolve **lista vazia** — não
porque falte dado real (Picãozinho e Porto de Galinhas têm série completa em
`MedicaoAmbiental` desde 25/07/2026), mas porque nenhum dos nove
`FonteDataset` descreve outro local além de Abrolhos.

🚨 **Pendência conhecida, registrada aqui para não virar surpresa depois:**
o catálogo curado não cresce sozinho com o projeto — ele é uma lista
Python fixa, escrita à mão. Não bloqueia a política acima (o dado
continua baixável por `/api/medicoes/`, sem passar pelo catálogo), mas
significa que a *descrição* dos produtos-fonte para os outros nove locais
não existe ainda. Consistente com o roadmap: `backend/dados/` está
marcado para remoção (PLANEJAMENTO.md, fase 3.2), e quando isso acontecer o
catálogo inteiro precisa ser repensado — não faz sentido investir em
estendê-lo por local antes disso.

### 6.24 ✅ RESOLVIDO em 12/08/2026 — o catálogo passou a descrever a série, e não só o arquivo

A pendência declarada logo acima em §6.23 fechou. O gatilho foi prático: com os
cinco locais novos já ingeridos (§2.3.1.1) e servidos pelo painel, a página de
cada um deles continuava dizendo *"Ainda não há datasets relacionados a esta
localização"* — sobre um recife com **19.278 medições** no banco.

🚨 **A frase não era um bug de tela; era o catálogo respondendo com precisão a
outra pergunta.** `DatasetCatalogo` descrevia **arquivos** de `backend/dados/`,
e todo arquivo do acervo foi extraído num ponto só, o Banco dos Abrolhos. Um
recife sem CSV próprio não tinha como aparecer, por mais série que tivesse.

**O que mudou:** `inventario_datasets.py` passou a ter duas metades, que
respondem perguntas diferentes e **não se substituem**:

| Metade | Descreve | Cobertura vem de | Vale para |
|---|---|---|---|
| `DATASETS_REAIS` | o arquivo em `backend/dados/` | `ler_metadados_arquivo` | só `abrolhos-ba` |
| `SERIES_INGERIDAS` | a série em `MedicaoAmbiental` | o próprio banco | todo local ingerido |

⚠️ **Apagar a primeira não era opção.** Metade dos arquivos catalogados (pH,
nitrato, `thetao`, clorofila, KD490) são variáveis que a ingestão **não** grava
— eles só existem como arquivo, e a segunda metade não os alcança.

A metade nova rende **16 registros** (8 locais × 2 fontes), e três decisões
nela são o que impede o defeito da §6.20 de voltar em roupa nova:

1. **Par sem medição não vira registro — nem desativado.** É a regra 2 do
   inventário aplicada ao banco em vez do disco. Os dois locais sem coordenada
   caem fora por consequência, não por exceção escrita à mão.
2. **Período e tamanho ficam nulos**, e a cobertura sai derivada por
   `cobertura.py` a cada resposta. Gravá-los aqui reintroduziria em 16
   registros exatamente a cópia que envelheceu em silêncio na §6.20.
3. **O `url_download` aponta para este projeto**, e não para o provedor:
   `/api/medicoes/?local=<slug>&fonte=<fonte>&formato=csv` — o mesmo endpoint
   citável da §7.5, agora alcançável pelo catálogo.

⚠️ **Consequência que exigiu um campo novo.** Esse endpoint **exige conta
aprovada**, enquanto todo `url_download` anterior apontava para a NOAA ou o
Copernicus e era livre. Sem distinguir os dois casos, o cartão ofereceria
"Baixar conjunto" a visitante deslogado e o clique devolveria **um JSON de 401
aberto no navegador**. `DatasetCatalogo.download_exige_conta` (migração `0029`)
carrega a diferença até a tela, que passa a mostrar o mesmo convite ao login
que `SerieAmbiental` já usava do lado do recife. O padrão do campo é `false`:
assumir o contrário esconderia atrás de login um arquivo que qualquer um baixa
direto do provedor.

📌 **O que continua pendente:** `backend/dados/` segue marcado para remoção
(PLANEJAMENTO.md fase 3.2) e, quando sumir, a primeira metade se desativa
sozinha pela regra 2 — restando o catálogo derivado do banco. Isso agora é uma
transição, e não mais um esvaziamento: em 27/07/2026 esta seção registrava que
*"apagar `backend/dados/` esvazia a página do catálogo"*, e desde hoje deixa de
esvaziar. ⚠️ Registrado também um efeito prático: numa máquina que clonou o
repositório, os CSVs **não estão lá** (são ignorados pelo Git), e a execução
completa de `inventariar_datasets` leria isso como "os nove arquivos sumiram",
gravando `ativo=False` por cima do que já estava medido. Por isso o comando
ganhou `--somente-series`, que atualiza só a metade derivada do banco.

### 6.25 ✅ RESOLVIDO em 12/08/2026 — a política de §6.23 valia na API e não aparecia em lugar nenhum do site

§6.23 declarou em 11/08/2026 que **o banco disponível ao usuário serve o máximo que o projeto tiver, mesmo o que o modelo não usa**, e mostrou que isso já era verdade por construção: `MedicaoAmbientalList` nunca filtrou por variável. Estava certo — e faltava a outra metade da mesma frase.

🚨 **Uma política que só existe no endpoint não é uma política do site.** Medido hoje, em Abrolhos: o banco tem **8 variáveis** ingeridas, **19.278 medições**, de 01/01/2020 a 11/08/2026. A página do recife desenhava **duas** (`sst` e `dhw`) e não dizia, em número nenhum, que as outras seis existiam — nem numa lista, nem numa contagem, nem numa frase. Quem visitasse o site concluiria, **corretamente pelo que via**, que o projeto tem SST e DHW. A rota `/api/medicoes/?local=abrolhos-ba&variavel=hotspot` respondia perfeitamente desde 27/07; ninguém que só use o site tinha como saber que ela existia.

⚠️ **O recorte do gráfico não estava errado — a omissão estava.** `VARIAVEIS_DA_SERIE = ['sst', 'dhw']` continua como está, e por dois motivos que seguem valendo: a permutação mede queda de PR-AUC de 0,84 → 0,30 ao embaralhar `dhw`, contra ~0,00 em salinidade e oxigênio (docs/RESULTADOS.md §7); e seis curvas no mesmo bloco dariam peso visual igual a variáveis que não pesam. **Escolher o que desenhar e esconder o que se tem são coisas diferentes**, e a segunda foi a que aconteceu.

**Corrigido:** `aquaculture/acervo.py` deriva do mesmo agregado que o catálogo já usa (`cobertura.resumo()`, uma consulta) o inventário por local: uma linha por variável **que tem medição**, com contagem, período coberto, fonte e o link `/api/medicoes/?...` que devolve exatamente aquele número. Sai em `/api/locais/<slug>/` no campo `acervo` e vira a tabela *"Tudo o que o projeto mede aqui"* (`AcervoDoLocal.jsx`), abaixo do gráfico.

🚨 **Cada linha diz o papel da variável no modelo, e isso não é enfeite.** Listar `baa` ao lado de `sst` sem dizer o papel de cada uma induziria o erro oposto ao que a correção resolve: `baa >= 3 em t+7` é o **alvo** do artefato servido — o que o modelo tenta prever —, não uma entrada dele. Confundir alvo com feature é o mal-entendido mais caro que um painel destes pode causar. Os papéis (`feature`, `alvo`, `contexto`, `opcional`) são declarados em `acervo.PAPEL_DA_VARIAVEL` a partir de docs/VARIAVEIS.md §§3, 5 e 6 — descrevem o **desenho do experimento**, não a lista de colunas de uma versão do `.joblib`.

⚠️ **Variável sem medição neste local não vira linha.** Uma linha *"kd490 — 0 medições"* seria lida como lacuna **daquele recife**, quando o que falta é o conector, para todos. Isso é assunto do catálogo, que já distingue referência externa de dado espelhado (`cobertura.MOTIVO_EXTERNO`).

**No mesmo movimento, a ficha física do local.** `profundidade_media_m` e `area_km2` estavam em `LocalRecife` desde a migração `0014` e **nunca saíram do Django admin** — não estavam em nenhum serializer, em nenhuma tela, em nenhuma cópia versionada. O motivo de ninguém ter reparado é exatamente o que torna o caso instrutivo: **nenhuma previsão usa esses campos**, então a ausência não quebrava teste, gráfico nem número. Agora saem na API (lista e detalhe), na cópia versionada e no bloco *"Ficha do local"* (`FichaDoLocal.jsx`), junto de coordenadas e `fonte_coordenadas`. 📌 **Pendência aberta:** dos 10 locais, só `abrolhos-ba` tem profundidade (10 m) e **nenhum** tem área. A ficha escreve *"Não registrado"* em vez de esconder a linha — pelo mesmo princípio de `iucn_categoria` sem ano (§2.4): a lacuna se declara. Quem preencher precisa registrar a fonte junto, aqui.

Travado por 22 testes de backend (`testes_acervo_local.py`) e 11 de frontend (`AcervoDoLocal.test.jsx`, `FichaDoLocal.test.jsx`).

---

## 7. Como citar, e onde cada fonte entra

Esta seção existe para uma pergunta específica: **ao escrever um parágrafo do
artigo, o que precisa ser citado ali?** Ela liga cada fonte ao que ela produz
no projeto, ao ponto do código, e às afirmações que dependem dela.

### 7.1 Mapa de proveniência

| Fonte | O que produz | Onde no código | Afirmações que dependem dela |
|---|---|---|---|
| **NOAA Coral Reef Watch 5 km v3.1** | `sst`, `dhw`, `baa`, `baa_area_alerta`, `hotspot`, `sst_anomalia` — **43.038 medições** | [`ingestao/conectores/noaa_crw.py`](../backend/ingestao/conectores/noaa_crw.py) | Todo o alvo e as features térmicas da entrega 1. [RESULTADOS.md](RESULTADOS.md) inteiro; [VARIAVEIS.md](VARIAVEIS.md) §3.1, §3.2, §4.5, §7.1, §7.2 |
| **Copernicus Marine (CMEMS)** | `salinidade`, `oxigenio` — **14.382 medições** nos 3 recifes (2020–2026) | [`ingestao/conectores/copernicus.py`](../backend/ingestao/conectores/copernicus.py) | As duas variáveis não térmicas. [VARIAVEIS.md](VARIAVEIS.md) §3.3, §3.4; e o achado de [RESULTADOS.md](RESULTADOS.md) §8 de que **elas não contribuem** com o BAA como alvo |
| **CMEMS — janelas do GCBD** | `salinidade`, `oxigenio` nos **90 dias antes de cada uma das 166 visitas** (1994–2010), em cache não versionado | [`ml/gcbd_ambiental.py`](../backend/ml/gcbd_ambiental.py), `manage.py ingerir_gcbd` | O experimento da entrega 2, passo 2. Ver §6.18 para as decisões de extração, e [GCBD.md](GCBD.md) |
| **GCBD** | O **alvo observado** da entrega 2 — 166 visitas brasileiras, 88 positivas — e as 8 térmicas do dia que as acompanham | [`ml/gcbd.py`](../backend/ml/gcbd.py), `manage.py treinar_gcbd` | Todo o [RESULTADOS.md](RESULTADOS.md) §11–§14, e em especial a afirmação central: **a regra `DHW ≥ 4` da NOAA perde 78 dos 88 branqueamentos observados no Brasil**. Também [GCBD.md](GCBD.md) e o desenho da entrega 2 em [VARIAVEIS.md](VARIAVEIS.md) §4.4 |
| **iNaturalist** | Fotografias de espécies | seed do banco | Nenhuma afirmação científica — uso ilustrativo |
| **IUCN Red List** | `iucn_categoria` + ano, versão e ficha por espécie | seed do banco (§2.4) | Nenhuma afirmação do modelo. ⚠️ **Os anos ainda não foram coletados**, e por isso o site não exibe categoria nenhuma hoje |
| **Met Office / GHRSST** | ⛔ nada no caminho novo | `dados/sst.csv` (legado) | Nenhuma — a série mais longa do projeto **não é usada** (§6.4) |

### 7.2 Citação exata de cada uma

**NOAA Coral Reef Watch** — produto `CoralTemp-v3.1`, acessado pelo espelho
PACIOOS em 25/07/2026:

> NOAA Coral Reef Watch. (2018, atualizado diariamente). *NOAA Coral Reef Watch
> Version 3.1 Daily Global 5km Satellite Coral Bleaching Heat Stress Products.*
> College Park, Maryland, USA: NOAA Coral Reef Watch. Dados acessados em
> 25/07/2026 via PACIOOS ERDDAP, dataset `dhw_5km`.

⚠️ Registrar **o espelho e a data**, não só "NOAA": o mesmo produto é
redistribuído por três servidores, e o par servidor+dataset é o que torna a
consulta reproduzível (§1.1).

**Copernicus Marine** — atribuição obrigatória pela licença:

> "Generated using E.U. Copernicus Marine Service Information"

mais o DOI de cada **produto** usado. ✅ **Coletados em 31/07/2026:**

| Dataset usado | Variável | Produto | DOI |
|---|---|---|---|
| `cmems_mod_glo_phy_my_0.083deg_P1D-m` | salinidade *(reanálise)* | `GLOBAL_MULTIYEAR_PHY_001_030` — Global Ocean Physics Reanalysis | **10.48670/moi-00021** |
| `cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m` | salinidade *(análise)* | `GLOBAL_ANALYSISFORECAST_PHY_001_024` — Global Ocean Physics Analysis and Forecast | **10.48670/moi-00016** |
| `cmems_mod_glo_bgc_my_0.25deg_P1D-m` | oxigênio *(reanálise)* | `GLOBAL_MULTIYEAR_BGC_001_029` — Global Ocean Biogeochemistry Hindcast | **10.48670/moi-00019** |
| `cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m` | oxigênio *(análise)* | `GLOBAL_ANALYSISFORECAST_BGC_001_028` — Global Ocean Biogeochemistry Analysis and Forecast | **10.48670/moi-00015** |

⚠️ **O DOI é do produto, não do dataset.** Cada produto reúne vários datasets
(diário, mensal, recortes de variável); o que se cita é o produto. Como este
projeto **emenda reanálise e análise na mesma série** — a reanálise termina
alguns meses atrás e a análise cobre até ontem (§1.3) —, cada variável precisa
de **duas** citações, e não uma. Um trabalho que cite só a reanálise estará
omitindo a fonte dos meses mais recentes, que são justamente os que o painel
usa.

📌 **O mapeamento dataset → produto foi conferido por duas vias independentes**,
e não deduzido do nome do dataset: a página de cada produto no Copernicus Marine
Data Store, e o catálogo consultado pela própria `copernicusmarine.describe()`
com o `dataset_id` como chave. As duas concordam nos quatro. Deduzir pelo nome
teria funcionado aqui, mas é o mesmo tipo de passo plausível-e-não-verificado
que já produziu três erros neste projeto.

Modelo de citação, com os campos preenchidos:

> E.U. Copernicus Marine Service Information (CMEMS). *Global Ocean Physics
> Reanalysis*, `GLOBAL_MULTIYEAR_PHY_001_030`. DOI: 10.48670/moi-00021. Dados
> acessados em 25/07/2026. https://marine.copernicus.eu

Produtos biogeoquímicos (`*_BGC_*`) levam crédito adicional ao **NECCTON
Project (EU)**, https://neccton.eu/.

⚠️ **O `cmems_mod_glo_bgc-optics_anfc_0.25deg_P1D-m` está declarado no conector
mas não tem medição no banco** — o KD490 saiu do baseline por só existir de
2023-11 em diante ([VARIAVEIS.md](VARIAVEIS.md) §3.5). Não entra na citação
enquanto não for usado; citar fonte de que não se usou dado é inflar a lista de
referências.

**GCBD** — são **duas citações distintas**, para artefatos distintos:

| O que você está citando | Citação |
|---|---|
| O **artigo** que descreve a base | van Woesik, R. & Kratochwill, C. (2022). *A global coral-bleaching database, 1980–2020.* Scientific Data. doi:10.1038/s41597-022-01121-y |
| Os **dados** que você baixou | van Woesik, R., Burkepile, D. (2022). *Bleaching and environmental data for global coral reef sites from 1980-2020.* BCO-DMO. doi:10.26008/1912/bco-dmo.773466.2 |

Ao usar os dados, cite as duas: o artigo pelo método, o repositório pelo dado.

⚠️ **Ao relatar os resultados de [RESULTADOS.md](RESULTADOS.md) §11–§14, cite
também a régua contra a qual eles são medidos.** A linha de base não é nossa: é
o limiar publicado da NOAA (`DHW ≥ 4` → Alerta Nível 1), que já tem a citação
do Coral Reef Watch em §7.2. Afirmar que "a regra perde 78 de 88 eventos" sem
citar de quem é a regra deixaria o leitor sem como verificar o que foi testado.

**iNaturalist** — crédito ao autor de cada fotografia, com a licença
específica daquela observação e link. Licença varia por foto.

**IUCN Red List** — citar **a versão e o ano da avaliação daquela espécie**, e não só "IUCN Red List". Uma categoria migra: `Dendrogyra cylindrus` foi VU de 2008 a 2022 e hoje é CR, e uma citação sem ano não diz qual das duas foi lida.

> IUCN {ano}. *{Nome científico}*. The IUCN Red List of Threatened Species {versão}. https://www.iucnredlist.org/species/{taxon}/{assessment}

⚠️ Os campos `iucn_avaliado_em` e `iucn_versao` existem no banco desde 31/07/2026 exatamente para que essa citação seja montável — e estão **vazios** nas nove espécies até a coleta (§2.4).

### 7.3 Referências científicas com problema de rastreabilidade

🚨 **Seis afirmações do modelo legado citam um documento que não existe no
repositório e não foi identificado** — marcadores `[cite: N]` em
`treinar_modelo.py`. Detalhe em §3.1.

**Nenhuma dessas afirmações pode ir para o artigo sem que a fonte seja
localizada ou substituída.** Elas embasam a função `calcular_risco()`, que a
entrega 1 já não usa — mas se algum raciocínio do texto se apoiar nelas
(hipóxia reduzindo o limiar, sinergia calor+acidificação), a referência
precisa ser encontrada primeiro.

### 7.4 Licenças

| O quê | Licença |
|---|---|
| Código deste projeto | MIT (`LICENSE`) |
| Dados NOAA CRW | domínio público (obra do governo dos EUA) |
| Dados Copernicus | livre e aberta, **com atribuição obrigatória** |
| GCBD | **CC-BY 4.0** |
| Fotografias iNaturalist | varia por observação — verificar uma a uma |

⚠️ A licença MIT **cobre apenas o código**. Dados e imagens seguem a licença
da fonte original, e algumas exigem atribuição na própria página que os exibe,
não só numa seção de créditos.

### 7.5 Como citar a série **deste** projeto — ✅ desde 31/07/2026

Até aqui esta seção só respondia "como citar as fontes". Faltava o outro lado:
**como alguém cita o recorte que este projeto montou.** Todo `url_download` do
catálogo aponta para o provedor, o que deixava o site na posição estranha de se
apresentar como banco de dados sem oferecer download de nada.

`/api/medicoes/?formato=csv` devolve o recorte inteiro, respeitando os mesmos
filtros do JSON:

```
GET /api/medicoes/?local=picaozinho-pb&formato=csv
GET /api/medicoes/?variavel=dhw&de=2024-01-01&ate=2024-12-31&formato=csv
```

| Coluna | O que é |
|---|---|
| `local`, `data`, `variavel`, `valor`, `unidade` | a medida |
| **`fonte`, `dataset_id`, `quality_flag`, `observacao`** | **a proveniência** |

🚨 **As quatro últimas não são opcionais, e é por isso que elas vão no arquivo
e não só na tela.** Um CSV sem `fonte` e sem `quality_flag` é uma planilha
qualquer: quem o receber de segunda mão não tem como saber de onde veio o
número nem se ele passou na validação física. Todo o esforço de proveniência
por valor deste documento se perde no momento em que o dado sai por um download
que não a carrega.

⚠️ **Valor nulo sai como célula vazia, nunca `0`.** É o defeito do pipeline
legado (pH 0, salinidade 0) reaparecendo em formato de arquivo — e num CSV o
leitor abre no Excel sem nenhum aviso por perto.

**Ao citar, declarar as duas camadas:** a fonte primária (§7.2, com o DOI dela)
e o recorte deste projeto — data de extração, filtros usados e o total de
linhas. O nome do arquivo baixado já carrega os filtros
(`medicoes-picaozinho-pb.csv`); a data de extração não, e precisa ser anotada
por quem baixa.

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
| 12/08/2026 | 🚨 **§6.25 — a política de §6.23 valia na API e não aparecia em lugar nenhum do site; §2.2 — a foto do local não tinha onde registrar autoria.** Dois defeitos da mesma família: *o projeto guardava e não mostrava*. **(1)** Abrolhos tem **8 variáveis** e **19.278 medições** no banco; a página desenhava duas (`sst`, `dhw`) e não dizia, em número nenhum, que as outras seis existiam — quem visitasse concluiria, corretamente pelo que via, que o projeto só tem SST e DHW. O recorte do gráfico continua (docs/RESULTADOS.md §7), porque *escolher o que desenhar* e *esconder o que se tem* são coisas diferentes; o que entrou foi `acervo.py` + a tabela "Tudo o que o projeto mede aqui", uma linha por variável com contagem, período, fonte e o link que devolve exatamente aquele número — **e o papel de cada uma no modelo**, para `baa` (o **alvo**, não uma entrada) não passar por feature. **(2)** `profundidade_media_m` e `area_km2` estavam em `LocalRecife` desde a migração `0014` e **nunca saíram do Django admin**: nenhuma previsão os usa, e por isso a ausência não quebrava teste, gráfico nem número. Agora saem na API, na cópia versionada e no bloco "Ficha do local", que escreve *"Não registrado"* em vez de esconder a linha — 📌 só Abrolhos tem profundidade, nenhum local tem área. **(3)** A correção de 11/08 (§2.1) alcançou as fotos de *espécie* e parou ali: `LocalRecife.imagem` — topo da página e cartão da lista — não tinha campo de crédito, e **o que não tem campo não aparece numa auditoria de campo errado**. Migração `0030` abre `credito_imagem`, `fonte_imagem_url` e `local_captura_foto` (os dois últimos opcionais), com a mesma regra: sem crédito, nada entra na cópia versionada e a tela escreve "Foto sem crédito informado". 22 testes de backend novos, 16 de frontend (162, era 140). |
| 12/08/2026 | ✅ **§2.3.1.1 e §6.24 — os cinco locais novos com coordenada passaram a ter série, previsão e dataset baixável.** Ingestão completa (2020-01-01 a 2026-08-11, **19.278 medições por local**, duas fontes), modelo remedido e regravado sobre **8 recifes** ([RESULTADOS.md](RESULTADOS.md) §25 — 19.056 amostras contra 7.095, 44/50 episódios contra 40 da persistência). ⚠️ **Ingerir não retreina:** o artefato continuava declarando três locais, e o painel respondia 404 com motivo para os cinco — corretamente, porque o modelo nunca os viu. **§6.24 fecha a pendência declarada em §6.23:** o catálogo descrevia *arquivos*, todos extraídos em Abrolhos, e por isso a página de um recife com 19.278 medições dizia "ainda não há datasets relacionados". `inventario_datasets.py` ganhou uma segunda metade derivada de `MedicaoAmbiental` — 16 registros (8 locais × 2 fontes), com período e tamanho **nulos** (a cobertura sai derivada, nunca gravada) e `url_download` apontando para `/api/medicoes/?...&formato=csv`, o primeiro do catálogo a apontar para este projeto e não para o provedor. Par sem medição **não vira registro**, nem desativado — é a regra da §6.20 aplicada ao banco. Campo novo `DatasetCatalogo.download_exige_conta` (migração `0029`) porque esse endpoint exige conta aprovada e um `<a>` simples devolveria um JSON de 401 ao visitante deslogado. Na tela, `motivo_sem_serie` faz os dois locais **sem coordenada** explicarem a própria ausência, em vez de exibirem "Não calculado" — a mesma frase que um pipeline quebrado mostraria. 12 testes de backend novos, 7 de frontend (147, era 140). |
| 12/08/2026 | 🚨 **§2.1 — a migração `0026` tinha corrigido só o banco; o crédito falso continuava sendo _gerado por código_.** Três funções fabricavam procedência a partir da mera existência de um arquivo de foto: `code_sync.py::_credito_imagem` gravava `"Acervo local do projeto"` na cópia versionada, `code_sync.py::_fonte_imagem_url` gravava a URL do próprio arquivo local no campo "fonte da imagem", e `formatters.js::resolverCreditoImagem` exibia o mesmo crédito falso na tela — esta última no **caminho ao vivo**, sobre dados da API, não só no fallback. Consequência concreta: `recifeData.js` ainda trazia as nove espécies com o crédito falso e com `foto_url` apontando para `/media/especies/Dendrogyra_cylindrus.jpeg`, então **com a API fora do ar o site continuava servindo a foto sem licença**. As três deixaram de inventar, e o exportador passou a aplicar à imagem o mesmo critério da categoria IUCN: sem `credito_imagem`, nada entra na cópia versionada — nem foto, nem fonte, nem local. Os dois arquivos gerados (`recifeData.js`, `generated_admin_sync.py`) foram regerados, estavam parados em 04/08 e listavam três locais em vez de dez. 768 testes de backend (era 762), 140 de frontend (era 139). |
| 11/08/2026 | **§6.23 — declarado: o banco de dados para download sempre serve o máximo disponível, mesmo sem uso no modelo.** Política pedida pelo usuário, confirmada como já verdadeira em `/api/medicoes/` (nunca filtrou por variável do modelo — `hotspot`, `baa` e `sst_anomalia` já provam isso ao vivo) e travada por teste novo. Registrada a exceção que a política não cobre: `/api/datasets/` (`DatasetCatalogo`) é um catálogo curado de nove produtos, todos fixados em Abrolhos — consultar por Picãozinho, Porto de Galinhas ou os sete locais novos (§2.3.1) devolve lista vazia, mesmo os dois primeiros tendo série real completa. Não bloqueia download (que passa por `/api/medicoes/`, não pelo catálogo); fica pendência declarada, consistente com o catálogo estar amarrado a `backend/dados/`, que o roadmap já manda apagar (fase 3.2). |
| 11/08/2026 | 🚨 **§2.1 corrigida — o defeito era nas nove espécies, não em duas.** Conferindo o banco direto (e não só o que este documento já sabia), as nove tinham o mesmo `credito_imagem="Acervo local do projeto"` e nenhuma tinha `fonte_imagem_url`. Conferidas as quatro com URL de observação documentada, pela API pública do iNaturalist (a página HTML recusa acesso automatizado com 403, a API não): três têm licença aberta (CC BY/CC BY-NC) e local da observação recuperado; **uma — `Dendrogyra cylindrus` — não tem licença nenhuma concedida** (`license_code` nulo = todos os direitos reservados), e o projeto vinha servindo uma cópia local do arquivo sem permissão. Migração `0026`: as quatro passam a ter crédito e fonte corretos; a cópia local de `Dendrogyra cylindrus` para de ser servida (campo `foto` limpo, arquivo mantido em disco); as outras três também param de servir cópia local, mas por preferir linkar a fonte a redistribuir (licença permite as duas, a fonte é a que não diverge com o tempo); as cinco sem URL documentada (`Holacanthus ciliaris`, `Sparisoma axillare`, `Ocyurus chrysurus`, `Phyllogorgia dilatata`, `Condylactis gigantea`) ficam sem crédito, sem foto e sem local — mesmo princípio de "não afirmar o que não se consegue verificar" já usado para `iucn_categoria` sem ano (§2.4). Campo novo `local_captura_foto` acrescentado ao modelo, ao formulário de contribuição do site e à modal — pendência aberta para quem souber a origem real das cinco preencher. |
| 11/08/2026 | **§2.3.1 — sete locais novos cadastrados, sem série ambiental.** Migration `0025_seed_novos_locais_recife.py`, a partir de uma tabela sem fonte primária citada trazida pelo usuário. Coordenadas convertidas de graus/minutos/segundos, marcadas **pendentes de verificação** — mesmo padrão dos três locais originais (§2.3). Dois ficaram sem latitude/longitude de propósito: `apa-costa-dos-corais` é uma área de 12 municípios, não um ponto; `recife-de-fora-ba` não tinha coordenada exata na tabela de origem, e a própria tabela já registrava isso em vez de estimar. `abrolhos-ba` já existia e foi deixado de fora — a tabela trazia uma coordenada ~1,5 km diferente da já gravada, e a divergência fica registrada, não resolvida. Grafo reprojetado (`neo4j_projetar`): 10 localizações, conferido item a item contra o Postgres. |
| 08/08/2026 | **§6.22 — a nova contribuição pública de espécie não pode tocar proveniência.** O site ganhou login e um formulário para conta aprovada propor espécie nova ou edição (fica pendente até um master aceitar). A lista branca de campos aceitos — `nome_cientifico`, `nome_comum`, `tipo`, `descricao`, `credito_imagem`, `fonte_imagem_url`, `fonte_url`, `locais` — **exclui `iucn_categoria`, `iucn_avaliado_em`, `iucn_versao`, `iucn_taxon_id`, `fonte_iucn_url`, `aphia_id` e `gbif_key` para todo mundo, master incluso**: são os mesmos campos que a migração `0022` (§2.4, abaixo) passou a exigir com data e origem depois do episódio de `Mussismilia braziliensis`. Um formulário público moderado ainda é uma porta para categoria digitada sem procedência — a aprovação audita quem editou, não se o dado tem lastro. Enviar um desses campos recusa com `400` nomeando o campo, não ignora em silêncio. |
| 31/07/2026 | 🚨 **§2.4.2 — um dos quatro valores estava ERRADO, não só sem lastro.** `Mussismilia braziliensis` estava gravada como **VU** e a IUCN a registra como **CR** desde 2022-2. É o coral-cérebro brasileiro, endêmico, a espécie que abre a página de Abrolhos. Não era falta de procedência: era **dado errado**, do tipo que a ausência de ano esconde perfeitamente — alguém digitou uma categoria que já foi verdadeira, a IUCN reavaliou, e nada tinha como perceber. Isso decide a favor de esconder tudo até haver ano: a alternativa "menos destrutiva" deixaria a afirmação errada no ar com aparência de dado revisado. ⚠️ Conferido em Wikidata e busca, **não** na ficha da IUCN (403 para acesso automatizado), e por isso **nada foi gravado** com essa procedência. §2.4.1 registra o que muda no desenho para isso escalar: `iucn_origem` (por qual via o dado veio, incluindo `terceiro` — Wikidata é fonte legítima **se declarada**), e o vencimento virando **recado diário** em `db/atualizacao.py` em vez de tarefa que alguém lembra. 🚨 **O pedido de API à IUCN foi recusado**, com e-mail institucional e sem motivo declarado. |
| 31/07/2026 | 🚨 **§2.4 — a metade sem procedência do projeto começou a ser corrigida.** Cada valor de `MedicaoAmbiental` grava fonte, dataset e flag de qualidade; as espécies vieram de lista digitada à mão, e a conservação era **texto livre** — sem id de táxon, sem ano e sem ficha, com `fonte_url` vazio nas **nove**. Era o campo mais grave para estar sem procedência, porque é **o único do banco que alguém vai citar**. Migração `0022`: o texto virou código oficial da Lista Vermelha, com `iucn_avaliado_em`, `iucn_versao`, `iucn_taxon_id` e `fonte_iucn_url`, mais `aphia_id` e `gbif_key` para o táxon. **Consequência deliberada: o site parou de exibir categoria nas nove**, porque nenhuma tem ano — a tela diz "sem procedência registrada" em vez de afirmar. ⚠️ Decisão travada por teste: **"Não avaliado" virou vazio, e não `NE`** — as duas leituras são indistinguíveis, `NE` é categoria real, e afirmá-la seria provavelmente falso para `Holacanthus ciliaris` e `Ocyurus chrysurus`, que têm avaliação publicada. O exemplo que motiva tudo está no acervo: `Dendrogyra cylindrus` foi VU de 2008 a 2022 e hoje é CR. |
| 31/07/2026 | ✅ **§6.15 resolvida — os cinco DOIs coletados.** Era o único item marcado como bloqueante para submissão. Quatro produtos CMEMS (10.48670/moi-00021, -00016, -00019, -00015) e o ERA5 (10.24381/cds.adbb2d47), todos conferidos na página oficial. **Dois achados que mudam a lista de referências:** são **quatro** produtos CMEMS e não dois, porque cada série emenda reanálise e análise — citar só a reanálise omitiria a fonte justamente dos dias que o painel usa; e o **ERA5 continua precisando de citação apesar de o conector ter sido cancelado**, porque os dados baixados sustentam o resultado de RESULTADOS §20. Fonte descartada como insumo não é fonte descartada como evidência. 📌 O mapeamento dataset → produto foi conferido por **duas vias independentes** (página do produto e `copernicusmarine.describe()`) em vez de deduzido do nome do dataset. |
| 31/07/2026 | **§7.5 criada — o projeto passou a publicar a própria série.** Até aqui todo `url_download` do catálogo apontava para o **provedor**: um banco de dados público sem nenhuma forma de baixar o que ele mesmo guarda, e sem forma de citar o recorte que este projeto montou. `/api/medicoes/?formato=csv` devolve o recorte inteiro com as quatro colunas de proveniência junto — sem `fonte` e `quality_flag`, o arquivo baixado perde exatamente o que distingue esta série de uma planilha qualquer. Valor nulo sai como célula vazia, nunca `0`. |
| 30/07/2026 | 🚨 **`StatusPredicao` removido (§6.21).** Aposentar o `/api/monitoramento/` em 28/07 **não** aposentou o dado: os mesmos 4 registros de demonstração continuaram saindo por `monitoramento_recente`, e `possui_painel_risco` era derivado deles com queda para o registro global — dizendo `true` para todo recife cadastrado, inclusive os que o painel responde com 404. Migração `0021`; o campo passou a sair dos metadados do artefato, e os dois endpoints concordam ao vivo. Caíram junto a camada de escrita legada do `neo4j_schema.py` (chamada só por testes) e a cascata morta do `utils/recifes.js`. |
| 30/07/2026 | **§6.16 quantificada.** O parágrafo sobre o efeito colateral da agregação (a média espacial quebra a relação entre BAA e HotSpot/DHW) estava certo e era qualitativo. Medido nos 7.173 dias: concordância **0,964** entre a regra publicada da NOAA e o `baa` do banco, com o desvio **inteiramente de um lado** — 0 casos em que a regra dispara sem o BAA, 261 em que o BAA dispara sem a regra. É consequência direta de agregar BAA por máximo e HotSpot/DHW por média, e não pede correção: são perguntas diferentes. **Consequência prática:** o corte publicado `DHW ≥ 4` não é transferível para média de bbox — pega 10 dos 19 episódios contra 15 do corte remedido de 1,0. Ver [RESULTADOS.md](RESULTADOS.md) §24 e [VARIAVEIS.md](VARIAVEIS.md) §4.6. |
| 28/07/2026 | **§6.21 — os arquivos defeituosos foram apagados, e um comando que não existia foi construído.** Removidos os **7 arquivos declarados inutilizáveis: 179,9 MB, 72% da pasta**. O que justifica apagar sem perda é que **o conhecimento sobre eles nunca esteve neles** — está nesta seção e em `inventario_datasets.EXCLUIDOS`, que continua listando os sete com o motivo depois de os arquivos sumirem. ⚠️ Nenhum estava no Git: remoção definitiva, confirmada antes. Mantidos os 9 catalogados (apagá-los esvazia a página, é decisão de produto) e os **7 órfãos** — nem catalogados nem declarados defeituosos, ou seja **não documentados**, e apagá-los sem entender repetiria em pequena escala o erro da §6.14. Removido também o `.pkl` legado que predizia `0.0` para tudo, via `git rm` (recuperável). 🚨 **Achado maior no caminho: `manage.py treinar_modelo` nunca existiu.** O README ensinava a rodá-lo, o `treinar_final` mandava usá-lo e o aviso de envelhecimento da rotina diária apontava para ele — confusão com o arquivo legado `backend/ml_models/treinar_modelo.py`, de mesmo nome. A falta importava porque a decisão de **não retreinar automaticamente** se apoia em "medir é ato deliberado", e não havia como medir sem escrever Python. Construído sobre o código que já existia e era testado. |
| 27/07/2026 | 🚨 **§6.20 criada — o catálogo anunciava nove conjuntos e a API servia três.** Descoberto ao verificar se o endpoint `banco-de-dados` do checklist existia: ele existia, e o problema era outro. **Seis dos nove datasets não têm uma única linha em `MedicaoAmbiental`** — pH, clorofila, nitrato, `thetao`, KD490 e o SST do Met Office apareciam na página com título, formato, período e tamanho, indistinguíveis dos três reais. Nenhum é invenção (ao contrário da §6.14): os arquivos existem em `backend/dados/` e o inventário lê deles. **O erro não era número nenhum** — era a página não dizer que *"período do arquivo em disco"* e *"até quando a API tem dado"* são perguntas diferentes. E os dois divergem no pior sentido: `noaa_crw_dhw` declarava fim em **2025-11-30** enquanto a série no banco vai a **2026-07-24**, ou seja o catálogo ao mesmo tempo anunciava dado inexistente e **escondia dado existente**. A causa é estrutural: cobertura estava **gravada**, e cópia guardada envelhece em silêncio — quarta vez que essa mesma regra cobra o preço, depois do `.docx`, do `.joblib` e do grafo. Agora é derivada a cada resposta em `aquaculture/cobertura.py`. Cada número anunciado vem com **`consulta`, o recibo**: a URL do `/api/medicoes/` que devolve exatamente aquilo, conferida nos três. Na tela, três estados que não se implicam: *disponível*, *referência externa* e *não verificada* — o terceiro porque afirmar ausência a partir de silêncio seria o mesmo erro invertido. ⚠️ Fica registrado o efeito colateral: **apagar `backend/dados/` esvazia a página do catálogo**, porque a regra 2 do inventário desativa registro sem arquivo. Isso precisa ser decidido, não descoberto. 29 testes. |
| 24/07/2026 | Criação do documento. Auditoria inicial de proveniência dos 19 CSVs, das imagens e das referências: 15 problemas registrados na §6. |
| 24/07/2026 | Fase A do roadmap. Adicionadas coordenadas aos três locais de recife (§2.3) — duas delas aproximadas e pendentes de verificação. `django-environ` incluída na §5. |
| 24/07/2026 | Merge do commit `34879bf` (react-router, split de componentes, `DatasetCatalogo`, serviço Neo4j). §6.14 **agravada**: os 8 datasets fictícios saíram do frontend e foram semeados no banco, passando a ser servidos por API real. `react-router-dom` 6.30.1 incluída na §5. |
| 24/07/2026 | **§6.14 resolvida.** Seed fictício removido pela migration `0016`; catálogo reconstruído a partir dos 9 arquivos reais via `manage.py inventariar_datasets`, com tamanho e período lidos do disco. Exclusões de arquivos com problema de integridade documentadas em código. |
| 25/07/2026 | **§6.13 corrigida** — a descrição anterior afirmava que a coluna `par` era majoritariamente nula; medição mostra 63,3% preenchida. O defeito real são as coordenadas irrecuperáveis. Criado [VARIAVEIS.md](VARIAVEIS.md) com a justificativa de uso e desuso de cada variável. |
| 25/07/2026 | Primeira ingestão ao vivo tentada na rede da faculdade. **§1.1 atualizada:** o espelho pfeg devolve HTTP 503 intermitente por sobrecarga. Pipeline passou a repetir falhas passageiras (`ingestao/retentativa.py`) e a preservar a causa real do erro — o resumidor apagava mensagens que usavam `<...>`, como as do `URLError`, e gravava só o tipo da exceção. |
| 25/07/2026 | **Backfill histórico concluído: 35.850 medições.** 2020-01-01 a 2026-07-23, três locais, 5 variáveis, em 14 blocos por local. Executado **duas vezes de forma independente** — pfeg `NOAA_DHW` na rede da UFF e PACIOOS `dhw_5km` fora dela — com resultado idêntico bloco a bloco, o que valida cruzadamente os dois espelhos. Cobertura e as 6 datas ausentes do produto documentadas na §1.1. |
| 25/07/2026 | **§6.16 resolvida — BAA passa a ser agregado por máximo.** A regra de agregação espacial deixou de ser uniforme: `ConectorNoaaCrw.AGREGACAO` a declara por variável, e média ficou restrita a grandeza contínua. Nova variável canônica **`baa_area_alerta`** (fração dos pixels válidos em Alerta Nível 1 ou acima) grava a extensão do evento, que nem média nem máximo preservam sozinhos. Contrato canônico ganhou a tabela de tipo/agregação e a regra 5: variável ordinal ou categórica precisa declarar sua agregação, e usar média fora de variável contínua é defeito, não escolha. |
| 25/07/2026 | **PACIOOS vira o espelho padrão do projeto**, no lugar do pfeg — `SERVIDOR_PADRAO`/`DATASET_PADRAO` no conector, defaults em `settings.py` e `.env.example` (onde as linhas `NOAA_ERDDAP_*` passam a vir comentadas). Razão: o pfeg exige rede com domínio federal, e um padrão que só funciona numa rede específica é armadilha para quem clona o repositório — foi exatamente o que travou a primeira tentativa de rodar fora da universidade. O PACIOOS não é versão degradada: os dois espelhos deram resultado idêntico bloco a bloco no backfill de 2020–2026. ⚠️ Registrado também o que **não** se sabe: o PACIOOS nunca foi testado de dentro da UFF, e a tabela da §1.1 diz "não medido" em vez de presumir sucesso. |
| 26/07/2026 | **§4.2 e §6.19 criadas — ERA5 avaliado, e o atalho descartado.** O vento virou prioridade por ser a **única variável não térmica que dá sinal** ([RESULTADOS.md](RESULTADOS.md) §17) enquanto o vento atual do projeto é constante inventada (§6.7). Credencial configurada em `~/.cdsapirc`, **fora do repositório** — o motivo é que chave que entra no histórico do Git precisa ser **revogada**, não apenas apagada. Conexão medida: **`200` em 40,4 s**; a fila do CDS era o risco número um da fonte e não se confirmou como impeditivo. **§6.19: o espelho ARCO na Google Cloud foi testado e descartado** — abortado após ~25 min sem abrir, porque é fatiado por instante de tempo, formato ideal para o mapa global de uma hora e inútil para a série de um ponto ao longo de anos. Registrado com o motivo para ninguém tentar de novo. Corrigida também uma afirmação minha não verificada sobre a unidade do `Windspeed` do GCBD — ver [ERA5.md](ERA5.md) Etapa 6. |
| 26/07/2026 | **§6.18 criada — a janela ambiental do GCBD vem de longe do recife.** Ao extrair salinidade e oxigênio para as 166 visitas, medido que **69 delas estão a menos de 1 km da costa** enquanto a grade do oxigênio é 0,25° (~28 km). Nenhum sítio ficou sem dado, mas **20 só encontram oxigênio a até 33 km**. Cada valor grava `raio_graus` e `n_celulas`, então a distância fica auditável valor a valor. Registrado como **limitação a declarar**: se as não térmicas derem sinal fraco, a resolução grosseira é explicação concorrente que estes dados não descartam. Confirmado também que a reanálise cobre **1993-01-01** nos dois produtos, então aqui **não há emenda** com produto de análise — ao contrário da série da entrega 1. §7.1 ganhou a linha do novo uso do CMEMS. |
| 26/07/2026 | **§6.17 criada — três defeitos no GCBD, detectados ao integrá-lo**, e §4.1 promovida a integrada. (a) 🚨 **`ClimSST` traz ausência codificada como número**: 262,15 K (= 273,15 − 11, ou seja um `-11` de "sem dado" convertido de Celsius) em **115 dos 313 registros brasileiros**; a coluna foi recusada e o valor vira `NaN` no carregamento. O plano de [GCBD.md](GCBD.md) **recomendava `ClimSST`** — a recomendação vinha da lista de colunas, não da distribuição delas. (b) `SSTA_Mean` é constante em 0,0 e também foi recusada. (c) **A unidade amostral é a visita, não a linha**: o arquivo traz uma linha por substrato, e as 313 linhas são **166 visitas**, com 0 divergindo no alvo — tratar linha como amostra inflaria n em 1,9× e poria cópias exatas nos dois lados da validação. §7.1 atualizada com onde o GCBD entra e quais afirmações dependem dele, e §7.2 com a ressalva de que a régua da entrega 2 é o limiar publicado da NOAA e precisa ser citada junto. |
| 25/07/2026 | **§7 reescrita — mapa de proveniência para citação.** Deixou de ser uma lista de fontes e passou a responder "ao escrever este parágrafo, o que preciso citar?": cada fonte ligada ao que produz, ao arquivo do código, e às afirmações documentadas que dependem dela. Corrigida uma imprecisão que atrapalharia a submissão — **o GCBD tem duas citações distintas**, van Woesik & Kratochwill (2022) para o artigo e van Woesik & Burkepile (2022) para o dado no BCO-DMO; a versão anterior misturava as duas. Registrado também que **seis afirmações do modelo legado citam documento não identificado** (§3.1) e não podem ir para o artigo, e que **os DOIs dos quatro produtos CMEMS usados continuam pendentes** — bloqueante para submissão. |
| 25/07/2026 | **§4.1 criada — GCBD baixado e avaliado.** Base de branqueamento observado (van Woesik & Burkepile 2022, CC-BY, BCO-DMO 773466), 16 MB, com hash e citação registrados. Levantamento de viabilidade em cinco etapas em [GCBD.md](GCBD.md), feito **antes** de qualquer código de integração. Três achados condicionam o uso: o dado brasileiro **termina em 2010** (sobreposição zero com a série atual), **Picãozinho fica sem cobertura** (sítio mais próximo a 198 km, contra 1,3 km em Abrolhos), e **a base não traz salinidade nem oxigênio**. Em compensação, o alvo é balanceado em 50,2%, contra 8% do BAA. Custo de ingestão dimensionado: janela de 90 dias por observação custa 106 mil medições, contra 5 milhões da série contínua. |
| 25/07/2026 | **§1.5 criada — estado da base ingerida.** Tabela consolidada do que está de fato em `MedicaoAmbiental`: 57.420 medições, 8 variáveis, três locais, **as duas fontes cobrindo exatamente a mesma janela** (2020-01-01 a 2026-07-24), pré-requisito para montar janelas com defasagem sem perder amostra. README: tabela de espelhos passa a registrar o comportamento nas **duas redes**, e o PACIOOS deixa de ser plano B — é o único que responde dentro e fora da UFF, foi por ele que os 43.038 registros entraram, e os dois espelhos já haviam sido comparados bloco a bloco com resultado idêntico. O padrão do código segue no pfeg, por ser o espelho oficial; quem roda fora da universidade sobrescreve no `.env`. |
| 25/07/2026 | **Backfill do NOAA reexecutado com a regra nova: 43.038 medições** (7.173 × 6 variáveis, PACIOOS, 2020-01-01 a 2026-07-24). O Alerta Nível 2 passou de 160 para 369 registros — a média escondia 209 dias de estresse máximo. `baa_area_alerta` mostra 2025 chegando a 1,000 em Abrolhos, recife inteiro em alerta. BAA e DHW voltaram a ser internamente consistentes sob a regra da NOAA (DHW ≥ 8 ⇒ Alerta Nível 2), o que a média espacial quebrava. Medições completas na §6.16. |
| 25/07/2026 | **Backfill do Copernicus concluído: 14.382 medições.** 2020-01-01 a 2026-07-24, três locais, salinidade e oxigênio, em 14 blocos por local (~13 min). Cobertura **completa**: 2.397 dias por local e variável, zero lacunas e zero nulos. A emenda reanálise→análise caiu em datas distintas por variável (salinidade 23/06, oxigênio 31/05), conforme o eixo de tempo de cada dataset — 99% da série vem da reanálise. Faixas e gradiente latitudinal registrados na §1.2, com a ressalva de que ausência de lacunas aqui é propriedade de saída de modelo, não indicador de qualidade. Nenhuma data futura gravada. |
| 25/07/2026 | **Conector Copernicus em produção.** Primeira ingestão ao vivo: 80 medições de Abrolhos (15/06–24/07/2026), salinidade 37,07–37,49 PSU e oxigênio 205,8–209,1 mmol·m⁻³ — coerentes com a Água Tropical do Atlântico Sul e com a saturação de superfície a 25 °C. A emenda caiu onde o catálogo previa: 9 dias de reanálise até 23/06 e 31 de análise a partir de 24/06, com `dataset_id` gravado por valor. O período foi cortado em 24/07 para impedir que previsão entrasse como medição — a §6.11 deixa de ser risco em aberto para o caminho novo. `Observacao` ganhou `dataset_id` próprio para tornar a costura rastreável. |
| 25/07/2026 | **Cobertura real do CMEMS medida no catálogo**, com credenciais criadas e `copernicusmarine.describe()`. Salinidade e O₂ têm reanálise de 1993 em diante (`cmems_mod_glo_phy_my_0.083deg_P1D-m` até 2026-06-23; `cmems_mod_glo_bgc_my_0.25deg_P1D-m` até 2026-05-31), cobrindo com folga a série 2020–2026 do NOAA. **KD490 só existe de 2023-11-15 em diante e não tem reanálise** — ver [VARIAVEIS.md](VARIAVEIS.md) §3.5, que passa a recomendar sua saída do baseline. Registrado também que os produtos *analysis and forecast* publicam datas futuras (até 2026-08-04, com hoje em 25/07), o que torna a §6.11 um risco ativo para a ingestão, não só para os CSVs antigos. |
| 25/07/2026 | **Limite de tamanho de requisição do ERDDAP medido.** O backfill 2020–2026 num único pedido (~2.400 dias × 5 variáveis × ~121 pixels) falhou com `ReadTimeout` e `HTTP 408` nos três locais, gravando zero. O pipeline passou a fatiar o período em blocos de 180 dias (`INGESTAO_JANELA_DIAS`), gravando bloco a bloco — o que também torna o backfill retomável e faz um bloco com falha não descartar os demais. O cliente ERDDAP passou a ser inicializado uma vez por conector, e não por bloco: o `griddap_initialize()` baixa o eixo de tempo inteiro do dataset a cada chamada. |
| 25/07/2026 | **§1.1 — restrição de rede registrada.** Os servidores da própria NOAA só respondem de dentro de rede com domínio federal (UFF); fora dela o pfeg dá timeout e o coastwatch.noaa.gov dá 403. O PACIOOS, por ser da Universidade do Havaí e não da NOAA, não tem essa restrição — foi por ele que a ingestão rodou fora da rede federal. Isso condiciona onde a ingestão pode ser agendada. |
| 25/07/2026 | **Primeira ingestão ao vivo bem-sucedida.** 115 medições de Abrolhos (01–23/07/2026, 5 variáveis) vindas do PACIOOS `dhw_5km` por ERDDAP, gravadas com proveniência por valor. Duas correções foram necessárias: o conector substituía `e.constraints` em vez de atualizá-lo (o erddapy exige as chaves criadas por `griddap_initialize()`, inclusive `*_step`), e o período pedido ia além do eixo de tempo do dataset — produto de satélite publica com 1–3 dias de atraso e o ERDDAP responde 404 à janela inteira. **Validação física:** SST 24,8–25,7 °C e HotSpot −2,19 a −1,30 °C dão MMM implícita de **26,975 °C**, coerente com a MMM conhecida de Abrolhos (~27 °C); DHW e BAA zerados no inverno austral, como esperado. Idempotência confirmada com dado real: 115 medições após três execuções. |
| 25/07/2026 | **§1.1 corrigida — o PACIOOS não tem certificado inválido.** A tentativa seguinte falhou com `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`, e o diagnóstico com `testar_fontes --ssl` mostrou o mesmo host verificando normalmente sob o bundle do `certifi`: é falha de cadeia no cliente, não no servidor. A conclusão anterior tratava "falhou em duas redes" como evidência sobre o servidor; verificado depois com a autora que **todas as execuções manuais foram na UFF** — a segunda rede nunca existiu, foi suposição minha. Criado `ingestao/certificados.py`; `certifi` promovido a dependência direta e deliberadamente **não** fixada, por ser uma lista de autoridades certificadoras. |
| 25/07/2026 | Pipeline de ingestão (`backend/ingestao/`) com o conector NOAA CRW. §6.3 (alcalinidade como pH) e §6.5 (DHW fora da norma) ficam **neutralizadas no novo caminho**, ainda presentes no `carregar_historico.py` legado. |
| 25/07/2026 | Espelho ERDDAP padrão definido por medição (`testar_fontes` na rede da UFF): **pfeg + `NOAA_DHW`**, único a responder com as 5 variáveis. PACIOOS com falha de certificado, CoastWatch com 403. ⚠️ Duas afirmações desta linha foram corrigidas depois — ver as entradas seguintes: a falha do PACIOOS era da cadeia de CAs local, não do servidor, e a medição foi feita numa rede só, não em duas. |
