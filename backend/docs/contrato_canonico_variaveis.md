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

## Implementacao atual — atualizada em 27/07/2026

⚠️ **Esta secao estava desatualizada** e descrevia um estado que deixou de
existir. Ficava escrito que `neo4j_seed` derivava o grafo de `StatusPredicao` e
que *"a pipeline NOAA/Copernicus ainda nao esta implementada nesta branch"*. As
duas afirmacoes sao falsas desde 25–27/07/2026.

O estado real:

| Camada | Como esta |
|---|---|
| Ingestao NOAA/CRW e Copernicus | **implementada e verificada ao vivo**, escrevendo em `MedicaoAmbiental` com proveniencia por valor |
| Projecao do grafo | `manage.py neo4j_projetar` deriva do **PostgreSQL**, nao de `StatusPredicao` |
| `StatusPredicao` | caminho **legado**, 3 registros, sem consumidor desde que o frontend migrou |
| `Predicao` no grafo | **ainda nao existe** — o modelo novo nao grava saida em lugar nenhum |

## Tabela canonica — o caminho legado

⚠️ **Esta tabela descreve a traducao do `StatusPredicao`**, o caminho que
`neo4j_seed` usava. Ela **nao** e o vocabulario em vigor: a lista viva e a da
secao seguinte, que e a que `ingestao/normalizacao.py` implementa e a que tem
dado no banco.

Fica registrada porque explica de onde vieram nomes como `par` (era
`irradiancia`) e `kd490` (era `turbidez`), e porque quatro nomes daqui —
`limite_termico`, `anomalia_termica`, `vento_velocidade`, `ph`, `nitrato` —
**nunca chegaram a existir** no vocabulario implementado.

| Origem no Django (legado) | Propriedade canonica | No de destino | Existe hoje? |
|---|---|---|---|
| `sst_atual` | `sst` | `MedicaoAmbiental` | ✅ sim |
| `dhw_calculado` | `dhw` | `MedicaoAmbiental` | ✅ sim |
| `salinidade` | `salinidade` | `MedicaoAmbiental` | ✅ sim |
| `oxigenio` | `oxigenio` | `MedicaoAmbiental` | ✅ sim |
| `irradiancia` | `par` | `MedicaoAmbiental` | ⚠️ nome existe, **sem dado** |
| `turbidez` | `kd490` | `MedicaoAmbiental` | ⚠️ nome existe, **sem dado** |
| `clorofila` | `clorofila` | `MedicaoAmbiental` | ⚠️ nome existe, **sem dado** |
| `limite_termico` | `limite_termico` | `MedicaoAmbiental` | ❌ nunca implementado |
| `anomalia` | `anomalia_termica` | `MedicaoAmbiental` | ❌ nunca implementado (o nome em vigor e `sst_anomalia`) |
| `vento_velocidade` | `vento_velocidade` | `MedicaoAmbiental` | ❌ nunca implementado |
| `ph` | `ph` | `MedicaoAmbiental` | ❌ nunca implementado |
| `nitrato` | `nitrato` | `MedicaoAmbiental` | ❌ nunca implementado |
| `risco_integrado` | `risco_integrado` | `Predicao` | legado |
| `nivel_alerta` | `nivel_alerta` | `Predicao` | legado |

## Variaveis da pipeline NOAA/Copernicus

Estas ja sao gravadas em `MedicaoAmbiental` pelo pipeline de `backend/ingestao/`.

| Coluna na fonte | Propriedade canonica | Unidade | Tipo | Agregacao espacial |
|---|---|---|---|---|
| `CRW_SST` | `sst` | °C | continua | media |
| `CRW_DHW` | `dhw` | °C·semana | continua | media |
| `CRW_HOTSPOT` | `hotspot` | °C | continua | media |
| `CRW_SSTANOMALY` | `sst_anomalia` | °C | continua | media |
| `CRW_BAA` | `baa` | categoria | **ordinal (0-4)** | **maximo** |
| *(derivada)* | `baa_area_alerta` | fração | continua | fracao de pixels com BAA >= 3 |
| `so` | `salinidade` | PSU | continua | media |
| `o2` | `oxigenio` | mmol·m⁻³ | continua | media |
| `kd` | `kd490` | m⁻¹ | continua | media |

### Regra de agregacao por tipo

**Variavel ordinal nao pode ser agregada por media.** A media de categorias nao
e uma categoria: metade dos pixels em 0 e metade em 4 da 2, que nao descreve
pixel nenhum e subestima o alerta. Toda variavel ordinal declara sua agregacao
explicitamente em `AGREGACAO`, no conector; continuas caem no padrao (media).

`baa_area_alerta` nao existe em nenhuma fonte: e derivada no conector como a
fracao dos pixels validos do recife em Alerta Nivel 1 ou acima. Ela acompanha
`baa` porque o maximo diz **o quao grave** e o estresse, e so ela diz **o quanto
do recife** esta sob ele. Origem: `noaa_crw:v1`, a mesma do `baa`.

## Regras obrigatorias

1. Nenhuma nova ingestao deve gravar variaveis ambientais fora de `MedicaoAmbiental`.
2. `Predicao` deve guardar apenas a parte preditiva e de classificacao, nao o pacote inteiro de medidas.
3. Toda origem nova deve mapear suas colunas para os nomes canonicos desta tabela antes de gravar no Neo4j.
4. Toda origem nova deve registrar `FonteDados.id` no formato `fonte_slug:versao`.
5. Toda variavel **ordinal ou categorica** deve declarar sua regra de agregacao
   espacial junto com o mapeamento. Media e o padrao apenas para variavel
   continua, e usa-la fora disso e defeito, nao escolha.

## Relacao com NOAA e Copernicus — ✅ implementada

As tres regras abaixo eram promessa; em 27/07/2026 sao fato verificado:

- ✅ NOAA/CRW e Copernicus escrevem nas mesmas propriedades canonicas de
  `MedicaoAmbiental` — 57.420 medicoes, 8 variaveis, 2 fontes;
- ✅ a diferenca entre fontes vive em `fonte`/`dataset_id` por valor, e nao no
  nome da variavel;
- ✅ nao existe nomenclatura paralela: `MAPA_COLUNAS`, `UNIDADES` e
  `MedicaoAmbiental.VARIAVEL_CHOICES` foram conferidos em 27/07/2026 e **batem
  exatamente**, sem nome orfao em nenhuma das duas direcoes.

⚠️ **A unicidade permite a mesma variavel de duas fontes no mesmo dia**
(`local, data, variavel, fonte`). Isso e deliberado — e por isso que a
proveniencia precisa estar no valor. Mas cria uma obrigacao: **dois produtos so
podem compartilhar um nome canonico se medirem a mesma grandeza no mesmo
lugar.** Ver a ressalva do `thetao` na secao seguinte.

## ✅ Auditoria e aprovacao — 28/07/2026

O vocabulario foi conferido contra o codigo, contra o modelo e contra o banco,
nos dois sentidos. **Nenhuma inconsistencia interna:**

| Conferencia | Resultado |
|---|---|
| Canonico alcancavel sem unidade declarada | nenhum |
| Unidade declarada sem mapeamento que a produza | nenhum |
| `MedicaoAmbiental.VARIAVEL_CHOICES` × `MAPA_COLUNAS` | **identicos** |
| Variavel no banco fora do vocabulario | nenhuma |

As quatro conferencias viraram teste (`VocabularioCanonicoTests`). Nao sao
obvias lendo o codigo: sao tres dicionarios em dois arquivos, e a divergencia
entre eles nao falha na hora — falha com `KeyError` no meio de uma gravacao, ou
com o banco recusando a linha **depois** de a rede ja ter sido consultada.

Duas decisoes foram tomadas para fechar o item.

### Decisao 1 — 🚨 `thetao` deixa de ser `sst`

Ate 28/07/2026, `MAPA_COLUNAS` traduzia as duas colunas para o mesmo canonico:

| | `CRW_SST` | `thetao` |
|---|---|---|
| Grandeza | temperatura da superficie | temperatura **potencial** |
| Profundidade | superficie | **13,47 m** |
| Fonte | NOAA Coral Reef Watch | Copernicus |

Chamar as duas de `sst` afirma que sao a mesma medida. E
[FONTES.md](../../docs/FONTES.md) secao 6.10 ja registrava a mistura de
profundidades como problema conhecido do acervo — **o vocabulario a codificava**,
que e o lugar onde ela fica mais dificil de perceber.

**Removida de `MAPA_COLUNAS`.** Nunca houve ingestao de `thetao`: ele nao esta
em `SERIES` do conector do Copernicus. Era armadilha dormente, esperando alguem
acrescentar a coluna a uma fonte.

⚠️ **Foi para `COLUNAS_RECUSADAS`, e nao simplesmente apagada.** A diferenca
importa: coluna desconhecida devolve `None` **em silencio**; coluna recusada
levanta com o motivo. Quem tentar ingerir `thetao` daqui a seis meses precisa
receber a explicacao, e nao um campo que some do resultado.

Se a temperatura do Copernicus for necessaria um dia, ela volta com nome
canonico proprio e profundidade declarada — nunca sob `sst`.

### Decisao 2 — os tres nomes sem dado ficam, com o motivo escrito

`clorofila`, `kd490` e `par` tem unidade, mapeamento e entrada em
`VARIAVEL_CHOICES`, e **zero linhas** no banco. Ficam.

O motivo de manter: os tres foram **avaliados e rejeitados por razao medida**.
Apagar o nome apagaria essa memoria do codigo, e o proximo repetiria o teste.

O motivo de nao deixar como estava: um nome sem dado e sem explicacao e
indistinguivel de sobra esquecida.

A solucao foi declarar. `normalizacao.SEM_DADO` guarda nome → motivo:

| Nome | Por que nao tem dado |
|---|---|
| `kd490` | so existe de 2023-11-15 em diante e nao tem reanalise; cortaria o treino de 6,5 para 2,7 anos ([VARIAVEIS.md](../../docs/VARIAVEIS.md) secao 3.5) |
| `clorofila` | testada no GCBD sobre 45.318 valores, nenhuma combinacao melhora ([RESULTADOS.md](../../docs/RESULTADOS.md) secao 21) |
| `par` | o arquivo disponivel traz o campo de incerteza, nao a medida ([FONTES.md](../../docs/FONTES.md) secao 6.12) |

E ha teste exigindo que **todo canonico sem conector apareca em `SEM_DADO` com
motivo**. A lista nao cresce por descuido: quem acrescentar um nome sem fonte e
sem razao quebra a suite.

### Pendencia que fica declarada

`par_error` continua mapeando para `par` — o campo de **incerteza** recebendo o
nome da grandeza, com `quality_flag=degradado`. E o unico caso no vocabulario
em que uma coluna que nao e a medida usa o nome da medida. Nao foi mexido
porque `par` nao tem fonte ativa; se ganhar uma, isto precisa ser resolvido
antes. Ver [FONTES.md](../../docs/FONTES.md) secao 6.12.
