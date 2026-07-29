# Fontes de Dados e Referências — Projeto Coral Brasil

> **Status:** documento vivo — obrigatório manter atualizado.
> **Regra:** nenhum dado entra no projeto sem uma linha correspondente neste documento.
> **Última revisão:** 24/07/2026

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

> Hersbach, H. et al. (2023). *ERA5 hourly data on single levels from 1940 to present.* Copernicus Climate Change Service (C3S) Climate Data Store (CDS).

Mais a frase exigida pela licença: *"Contains modified Copernicus Climate Change Service information [ano]"*.

🚨 **O DOI do dataset ainda não foi conferido na página oficial** — mesma pendência dos produtos CMEMS (§6.15), **bloqueante para submissão**.

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

#### O que fica de pé, e por quê

O **modelo `StatusPredicao`** continua existindo, com os 3 registros. Removê-lo
é mudança de esquema — migração, e mais admin, `code_sync`, `neo4j_schema` e o
campo `monitoramento_recente` que `/api/locais/<slug>/` ainda devolve. É
trabalho de outra natureza que apagar comando morto, e merece decisão própria.

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

### 6.15 DOIs dos produtos CMEMS não coletados
Cada produto Copernicus tem DOI próprio, exigido para citação formal. Nenhum foi registrado.

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
| **IUCN Red List** | `status_conservacao` por espécie | seed do banco | Nenhuma afirmação do modelo |
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

mais o DOI de cada produto usado. Produtos efetivamente usados neste projeto:

| Dataset | Variável | Tipo |
|---|---|---|
| `cmems_mod_glo_phy_my_0.083deg_P1D-m` | salinidade | reanálise |
| `cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m` | salinidade | análise |
| `cmems_mod_glo_bgc_my_0.25deg_P1D-m` | oxigênio | reanálise |
| `cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m` | oxigênio | análise |

Produtos biogeoquímicos levam crédito adicional ao **NECCTON Project (EU)**.

🚨 **Os DOIs individuais desses quatro produtos ainda não foram coletados** —
pendência registrada em §6.15, e **bloqueante para submissão**.

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

**IUCN Red List** — citar a versão consultada.

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
