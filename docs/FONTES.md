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

---

## 1. Fontes de dados ambientais

### 1.1 NOAA Coral Reef Watch (CRW)

**Instituição:** National Oceanic and Atmospheric Administration / NESDIS / STAR — Coral Reef Watch Program (EUA)
**Produto:** Daily Global 5 km (0,05°) Satellite Coral Bleaching Heat Stress Monitoring Product Suite, versão 3.1
**Página oficial:** https://coralreefwatch.noaa.gov/product/5km/
**Acesso programático:** ERDDAP. Três espelhos publicam o mesmo produto, cada um sob um identificador próprio — servidor e dataset **sempre andam em par**. Disponibilidade medida em 25/07/2026 com `manage.py testar_fontes`, **na rede da UFF**:

| Espelho | Servidor | Dataset | Estado |
|---|---|---|---|
| pfeg (**padrão do projeto**) | `coastwatch.pfeg.noaa.gov/erddap` | `NOAA_DHW` | ✅ responde com as 5 variáveis |
| NOAA CoastWatch | `coastwatch.noaa.gov/erddap` | `noaacrwdhwDaily` | ⚠️ HTTP 403 |
| PACIOOS | `pae-paha.pacioos.hawaii.edu/erddap` | `dhw_5km` | ✅ **entregou dado real** — 115 medições em 25/07/2026 |

O PACIOOS foi a origem dos CSVs que o projeto já possui. O padrão passou para o pfeg, que é também o servidor que o `coleta_de_dados.py` original usava.

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

Consequência para a operação: **o par padrão do projeto (pfeg) só funciona na UFF.** Agendamento automático, deploy ou trabalho de casa precisam do par PACIOOS. Como o estado de cada espelho depende da rede, rode `manage.py testar_fontes` na máquina que vai ingerir.

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

⚠️ **As medições de BAA já gravadas foram calculadas pela regra antiga.** A tabela abaixo é o estado do banco em 25/07/2026, antes da correção — os 7.170 registros vêm da média arredondada e **subestimam o alerta**. O upsert é idempotente por `(local, data, variável, fonte)`, então reexecutar o backfill do NOAA corrige em lugar, sem duplicar; até que isso seja feito, a série de `baa` não deve ser usada como alvo.

| Nível gravado (regra antiga) | n |
|---|---|
| 0 | 4.509 |
| 1 | 2.010 |
| 2 | 344 |
| 3 | 147 |
| 4 | 160 |

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
| 24/07/2026 | Merge do commit `34879bf` (react-router, split de componentes, `DatasetCatalogo`, serviço Neo4j). §6.14 **agravada**: os 8 datasets fictícios saíram do frontend e foram semeados no banco, passando a ser servidos por API real. `react-router-dom` 6.30.1 incluída na §5. |
| 24/07/2026 | **§6.14 resolvida.** Seed fictício removido pela migration `0016`; catálogo reconstruído a partir dos 9 arquivos reais via `manage.py inventariar_datasets`, com tamanho e período lidos do disco. Exclusões de arquivos com problema de integridade documentadas em código. |
| 25/07/2026 | **§6.13 corrigida** — a descrição anterior afirmava que a coluna `par` era majoritariamente nula; medição mostra 63,3% preenchida. O defeito real são as coordenadas irrecuperáveis. Criado [VARIAVEIS.md](VARIAVEIS.md) com a justificativa de uso e desuso de cada variável. |
| 25/07/2026 | Primeira ingestão ao vivo tentada na rede da faculdade. **§1.1 atualizada:** o espelho pfeg devolve HTTP 503 intermitente por sobrecarga. Pipeline passou a repetir falhas passageiras (`ingestao/retentativa.py`) e a preservar a causa real do erro — o resumidor apagava mensagens que usavam `<...>`, como as do `URLError`, e gravava só o tipo da exceção. |
| 25/07/2026 | **Backfill histórico concluído: 35.850 medições.** 2020-01-01 a 2026-07-23, três locais, 5 variáveis, em 14 blocos por local. Executado **duas vezes de forma independente** — pfeg `NOAA_DHW` na rede da UFF e PACIOOS `dhw_5km` fora dela — com resultado idêntico bloco a bloco, o que valida cruzadamente os dois espelhos. Cobertura e as 6 datas ausentes do produto documentadas na §1.1. |
| 25/07/2026 | **§6.16 resolvida — BAA passa a ser agregado por máximo.** A regra de agregação espacial deixou de ser uniforme: `ConectorNoaaCrw.AGREGACAO` a declara por variável, e média ficou restrita a grandeza contínua. Nova variável canônica **`baa_area_alerta`** (fração dos pixels válidos em Alerta Nível 1 ou acima) grava a extensão do evento, que nem média nem máximo preservam sozinhos. Contrato canônico ganhou a tabela de tipo/agregação e a regra 5: variável ordinal ou categórica precisa declarar sua agregação, e usar média fora de variável contínua é defeito, não escolha. ⚠️ Os 7.170 registros de `baa` já gravados vêm da regra antiga e subestimam o alerta — exigem reexecução do backfill do NOAA. |
| 25/07/2026 | **Backfill do Copernicus concluído: 14.382 medições.** 2020-01-01 a 2026-07-24, três locais, salinidade e oxigênio, em 14 blocos por local (~13 min). Cobertura **completa**: 2.397 dias por local e variável, zero lacunas e zero nulos. A emenda reanálise→análise caiu em datas distintas por variável (salinidade 23/06, oxigênio 31/05), conforme o eixo de tempo de cada dataset — 99% da série vem da reanálise. Faixas e gradiente latitudinal registrados na §1.2, com a ressalva de que ausência de lacunas aqui é propriedade de saída de modelo, não indicador de qualidade. Nenhuma data futura gravada. |
| 25/07/2026 | **Conector Copernicus em produção.** Primeira ingestão ao vivo: 80 medições de Abrolhos (15/06–24/07/2026), salinidade 37,07–37,49 PSU e oxigênio 205,8–209,1 mmol·m⁻³ — coerentes com a Água Tropical do Atlântico Sul e com a saturação de superfície a 25 °C. A emenda caiu onde o catálogo previa: 9 dias de reanálise até 23/06 e 31 de análise a partir de 24/06, com `dataset_id` gravado por valor. O período foi cortado em 24/07 para impedir que previsão entrasse como medição — a §6.11 deixa de ser risco em aberto para o caminho novo. `Observacao` ganhou `dataset_id` próprio para tornar a costura rastreável. |
| 25/07/2026 | **Cobertura real do CMEMS medida no catálogo**, com credenciais criadas e `copernicusmarine.describe()`. Salinidade e O₂ têm reanálise de 1993 em diante (`cmems_mod_glo_phy_my_0.083deg_P1D-m` até 2026-06-23; `cmems_mod_glo_bgc_my_0.25deg_P1D-m` até 2026-05-31), cobrindo com folga a série 2020–2026 do NOAA. **KD490 só existe de 2023-11-15 em diante e não tem reanálise** — ver [VARIAVEIS.md](VARIAVEIS.md) §3.5, que passa a recomendar sua saída do baseline. Registrado também que os produtos *analysis and forecast* publicam datas futuras (até 2026-08-04, com hoje em 25/07), o que torna a §6.11 um risco ativo para a ingestão, não só para os CSVs antigos. |
| 25/07/2026 | **Limite de tamanho de requisição do ERDDAP medido.** O backfill 2020–2026 num único pedido (~2.400 dias × 5 variáveis × ~121 pixels) falhou com `ReadTimeout` e `HTTP 408` nos três locais, gravando zero. O pipeline passou a fatiar o período em blocos de 180 dias (`INGESTAO_JANELA_DIAS`), gravando bloco a bloco — o que também torna o backfill retomável e faz um bloco com falha não descartar os demais. O cliente ERDDAP passou a ser inicializado uma vez por conector, e não por bloco: o `griddap_initialize()` baixa o eixo de tempo inteiro do dataset a cada chamada. |
| 25/07/2026 | **§1.1 — restrição de rede registrada.** Os servidores da própria NOAA só respondem de dentro de rede com domínio federal (UFF); fora dela o pfeg dá timeout e o coastwatch.noaa.gov dá 403. O PACIOOS, por ser da Universidade do Havaí e não da NOAA, não tem essa restrição — foi por ele que a ingestão rodou fora da rede federal. Isso condiciona onde a ingestão pode ser agendada. |
| 25/07/2026 | **Primeira ingestão ao vivo bem-sucedida.** 115 medições de Abrolhos (01–23/07/2026, 5 variáveis) vindas do PACIOOS `dhw_5km` por ERDDAP, gravadas com proveniência por valor. Duas correções foram necessárias: o conector substituía `e.constraints` em vez de atualizá-lo (o erddapy exige as chaves criadas por `griddap_initialize()`, inclusive `*_step`), e o período pedido ia além do eixo de tempo do dataset — produto de satélite publica com 1–3 dias de atraso e o ERDDAP responde 404 à janela inteira. **Validação física:** SST 24,8–25,7 °C e HotSpot −2,19 a −1,30 °C dão MMM implícita de **26,975 °C**, coerente com a MMM conhecida de Abrolhos (~27 °C); DHW e BAA zerados no inverno austral, como esperado. Idempotência confirmada com dado real: 115 medições após três execuções. |
| 25/07/2026 | **§1.1 corrigida — o PACIOOS não tem certificado inválido.** A tentativa seguinte falhou com `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`, e o diagnóstico com `testar_fontes --ssl` mostrou o mesmo host verificando normalmente sob o bundle do `certifi`: é falha de cadeia no cliente, não no servidor. A conclusão anterior tratava "falhou em duas redes" como evidência sobre o servidor; verificado depois com a autora que **todas as execuções manuais foram na UFF** — a segunda rede nunca existiu, foi suposição minha. Criado `ingestao/certificados.py`; `certifi` promovido a dependência direta e deliberadamente **não** fixada, por ser uma lista de autoridades certificadoras. |
| 25/07/2026 | Pipeline de ingestão (`backend/ingestao/`) com o conector NOAA CRW. §6.3 (alcalinidade como pH) e §6.5 (DHW fora da norma) ficam **neutralizadas no novo caminho**, ainda presentes no `carregar_historico.py` legado. |
| 25/07/2026 | Espelho ERDDAP padrão definido por medição (`testar_fontes` na rede da UFF): **pfeg + `NOAA_DHW`**, único a responder com as 5 variáveis. PACIOOS com falha de certificado, CoastWatch com 403. ⚠️ Duas afirmações desta linha foram corrigidas depois — ver as entradas seguintes: a falha do PACIOOS era da cadeia de CAs local, não do servidor, e a medição foi feita numa rede só, não em duas. |
