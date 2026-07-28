# Planejamento de Go-Live

## Checklist obrigatório de go-live

Antes de publicar o site, **todos** os itens abaixo devem ser aprovados:

- [ ] Camada de persistência validada com constraints/índices.
  - [x] **PostgreSQL como fonte única da verdade** — migrado em 25/07/2026: 57.463 objetos vindos do SQLite, incluindo as 57.420 medições, com contagens e distribuição do BAA idênticas. Sobe por `docker-compose.yml` em versão fixa; 181 testes passam contra ele. Decisão e justificativa em [docs/arquitetura.md](docs/arquitetura.md).
  - [x] **Neo4j como projeção derivada** — ✅ **resolvido em 27/07/2026.** `manage.py neo4j_projetar` reconstrói o grafo do zero a partir do PostgreSQL: **57.420 medições, 172.286 elementos em 16 s**, conferidos item a item. Constraints de unicidade criadas de forma idempotente. O critério deste item era *reconstruir do zero e conferir* — é exatamente o que o comando faz, e a conferência roda sozinha ao final. 18 testes. Ver [docs/arquitetura.md](docs/arquitetura.md).
    - ⚠️ **`Predicao` ainda não entra**: o modelo novo não grava saída em lugar nenhum, e projetar o `StatusPredicao` legado repetiria o erro que este comando veio corrigir.
    - ⚠️ **A projeção não roda sozinha** — é artefato derivado, e o deploy precisa chamá-la.
- [x] Ingestão NOAA/Copernicus rodando localmente com logs e tratamento de falha.
  - [x] **NOAA CRW** — verificado ao vivo em 25/07/2026: 115 medições de Abrolhos (01–23/07, 5 variáveis) gravadas com proveniência por valor, `ExecucaoIngestao` registrando cada tentativa, retentativa de falha passageira, e idempotência confirmada com dado real. Validação física em [docs/FONTES.md](docs/FONTES.md) §9.
  - [x] **Copernicus** — verificado ao vivo em 25/07/2026: backfill de 14.382 medições (salinidade e oxigênio, três locais, 2020-01-01 a 2026-07-24), sem lacuna e sem valor nulo. Emenda reanálise→análise rastreável por valor via `dataset_id`, e corte que impede previsão de entrar como medição. Ver [docs/FONTES.md](docs/FONTES.md) §1.2.
- [x] **Endpoints backend estáveis: `localizacoes`, `banco-de-dados`, `painel-risco`** — ✅ **27/07/2026**, os três. Ao fechar este item apareceu um padrão que vale registrar: em **dois** dos três casos o problema não era o endpoint faltar, e sim ele **servir a coisa errada com aparência de certa** — as 57.420 medições sem nenhuma rota, e o catálogo anunciando seis conjuntos que a API não tem. "Existe" e "está estável" são critérios diferentes.
  - [x] **`/api/medicoes/` criado** — 27/07/2026. As **57.420 medições ambientais não tinham endpoint nenhum**: o `/api/monitoramento/` que o frontend consumia até então devolve `StatusPredicao`, o modelo legado com **3 registros**. Toda a série ingerida do NOAA e do Copernicus estava inalcançável pela API. Serve com proveniência por valor (`fonte`, `dataset_id`, `quality_flag`, `observacao`), filtros combináveis, e **data inválida falhando com 400** — sem isso `?de=ontem` seria ignorado e o cliente receberia tudo achando que recebeu o recorte. 22 testes.
    - ⚠️ **Paginação é por view, nunca global.** A primeira tentativa ligou `DEFAULT_PAGINATION_CLASS`; três testes existentes flagraram na hora, porque isso troca a resposta de **toda** lista de array cru para envelope `{count, results}` — e quatro endpoints já são consumidos como array. Seria quebra de contrato disfarçada de configuração. Ver o comentário em `coral_site/settings.py`.
  - [x] **`painel-risco` criado** — ✅ **27/07/2026, o primeiro endpoint que faz conta.** Todos os outros entregam dado guardado. Este carrega o modelo persistido, monta a janela de 7 dias a partir da série e responde a probabilidade **calibrada**, com data-base, atraso, entradas e limiar no payload. Verificado ao vivo contra o PostgreSQL: os três recifes respondem com data-base 24/07 e alvo 31/07. 54 testes. O contrato veio do artefato, não da view. Ver [docs/arquitetura.md](docs/arquitetura.md).
    - 🚨 **Descoberto ao executar: a probabilidade é uma escada que toca 0 e 1.** Os três recifes voltaram com **exatamente 0,0029** apesar de entradas diferentes — a recalibração isotônica é função escada, e 12,2% das amostras de treino saem em `p = 0,000` exato. Isso **muda um requisito da interface**: exibir "0% de risco" ou "100%" traduz um degrau finito em impossibilidade ou certeza. A API sinaliza com `no_extremo`; a decisão de exibição é do item abaixo. Ver [docs/RESULTADOS.md](docs/RESULTADOS.md) §22.8.
    - [x] **Limiar aprovado: 0,10** — ✅ 27/07/2026. O 0,20 anterior nunca tinha sido *escolhido*: era o ponto equivalente ao `0,50` do `predict`, que operava assim só porque `class_weight` empurrava a probabilidade para cima. Critério declarado: **priorizar antecedência**. Ver [docs/RESULTADOS.md](docs/RESULTADOS.md) §22.9.
  - [x] **`banco-de-dados`** — ✅ **27/07/2026.** ⚠️ **Correção:** a linha anterior deste item dizia *"ainda não existe"*, e estava **errada** — eu a escrevi sem verificar. O endpoint é o `/api/datasets/`, e existe desde antes. O problema era outro, e pior: 🚨 **o catálogo anunciava 9 conjuntos e a API servia 3.** pH, clorofila, nitrato, `thetao`, KD490 e o SST do Met Office apareciam com título, formato, período e tamanho **sem uma única medição no banco**. E `noaa_crw_dhw` declarava fim em 2025-11-30 com a série já em 2026-07-24 — anunciando dado inexistente e escondendo dado existente ao mesmo tempo. Resolvido derivando a cobertura do banco a cada resposta (`aquaculture/cobertura.py`), com **`consulta`** — a URL que comprova cada número. 29 testes. Ver [docs/FONTES.md](docs/FONTES.md) §6.20.
- [x] **Variáveis canônicas aprovadas** — ✅ **28/07/2026.** Auditado nos dois sentidos contra código, modelo e banco: **nenhuma inconsistência interna** — nenhum canônico sem unidade, nenhuma unidade sem mapeamento, `VARIAVEL_CHOICES` idêntico ao vocabulário, nenhuma variável no banco fora do contrato. As quatro conferências viraram teste. Duas decisões fecharam o item, e o documento tinha dois parágrafos **falsos** que foram corrigidos. Ver [contrato canônico](backend/docs/contrato_canonico_variaveis.md).
  - [x] 🚨 **`thetao` deixou de ser `sst`.** O mapeamento traduzia temperatura **potencial a 13,47 m** e temperatura **de superfície** para o mesmo nome canônico — afirmando que são a mesma medida. [FONTES.md](docs/FONTES.md) §6.10 já registrava a mistura de profundidades como problema do acervo; o vocabulário a **codificava**. Nunca houve ingestão (não está no `SERIES` do conector), então era armadilha dormente. Foi para `COLUNAS_RECUSADAS` e não apagada: coluna desconhecida devolve `None` em silêncio, recusada levanta **com o motivo**.
  - [x] **`clorofila`, `kd490` e `par` ficam, com o motivo declarado.** Têm nome, unidade e zero linhas — mas os três foram avaliados e rejeitados por razão medida, e apagar apagaria essa memória. Agora `normalizacao.SEM_DADO` guarda nome → motivo, e **há teste exigindo motivo para todo canônico sem conector**: a lista não cresce por descuido.
  - ⚠️ **Pendência declarada:** `par_error` (campo de **incerteza**) continua mapeando para `par` (a **grandeza**), como `degradado`. É o único caso assim no vocabulário. Não mexido porque `par` não tem fonte ativa; se ganhar uma, resolver antes. Ver [FONTES.md](docs/FONTES.md) §6.12.
- [x] **Modelo treinado persistido** — ✅ **resolvido em 27/07/2026.** `manage.py treinar_final` treina **uma vez sobre todos os dados** e grava o artefato em `dados/modelos/`, com os metadados ao lado em JSON legível. Gravado: `baa ≥ 3` em t+7, 4 colunas de trajetória, 7.095 amostras com 596 positivas. O carregamento **recusa** artefato sem a assinatura do projeto ou de outra versão do scikit-learn — `joblib.load` executa código, e o pickle de um `Pipeline` falha em silêncio entre versões. 16 testes. Ver [docs/VISAO_GERAL.md](docs/VISAO_GERAL.md) §7.4.
  - ⚠️ O artefato **não é versionado** — é derivado e regerável pelo comando. Isso significa que o **deploy precisa rodar `treinar_final`**, e esse passo ainda não existe em lugar nenhum.
  - ⚠️ O `.pkl` legado em `backend/ml_models/modelo_coral_rf.pkl` continua no repositório — é o que predizia `0.0` para tudo. **Não pode ser usado**, e ainda não foi removido.
- [x] **Calibração medida** — ✅ **resolvida em 27/07/2026, e o defeito era grave.** O modelo prometia **0,165** onde a taxa real é **0,084** (ECE 0,081, do tamanho do próprio fenômeno). O Brier "bom" de 0,043 escondia isso: a decomposição de Murphy mostrou que a **incerteza sozinha é o dobro do Brier**. Corrigido com recalibração isotônica — ECE **0,0039**, e a curva fecha. `manage.py calibrar` mede; `treinar_final` grava recalibrado por padrão. 24 testes. Ver [docs/RESULTADOS.md](docs/RESULTADOS.md) §22.
  - ⚠️ **O limiar de alerta virou decisão explícita.** Calibrar não custa detecção, mas move o corte: o ponto equivalente ao antigo fica em **0,20**, não em 0,50. O painel precisa declarar qual usa.
- [x] **Nome do produto conferido na interface** — ✅ **27/07/2026.** O painel diz *"Previsão de estresse térmico"* e *"Risco de estresse térmico em 7 dias"*; o cartão da listagem diz *"Estresse térmico em 7 dias"*. Conferido que nenhuma outra tela promete branqueamento. O modelo prevê **estresse térmico**: a régua térmica da NOAA perde **78 dos 88** branqueamentos brasileiros observados ([docs/RESULTADOS.md](docs/RESULTADOS.md) §11), e chamar o painel de "previsão de branqueamento" seria prometer o que ele não entrega. Travado por teste em duas superfícies.
- [x] **Painel exibindo predição com dados suficientes e rastreáveis** — ✅ **27/07/2026.** `PainelPredicao` consome `/api/painel-risco/<slug>/` e trata os cinco estados: previsão, dado insuficiente, servidor sem modelo, local fora do treino, rede caída. **Nenhum deles exibe número no lugar do que falta.** 27 testes de frontend.
  - [x] **"Dados suficientes" virou critério verificável, e não adjetivo.** Janela incompleta vira a tela *"Dados insuficientes"* com o dia que faltou, e não uma probabilidade sobre lacuna. **Zero é valor legítimo para uma variação** — preencher devolveria "nada mudou" justamente onde o dado sumiu.
  - [x] **O limiar aparece junto da probabilidade** — *"Aviso emitido a partir de 20,0%"*, lido do payload. ⚠️ O frontend **não recalcula** `probabilidade >= limiar`: usa o campo `alerta` do servidor, senão as duas versões divergiriam em silêncio no dia em que a regra mudasse. Travado por teste.
  - [x] 🚨 **A interface nunca exibe "0%" nem "100%"** — o extremo vira faixa qualitativa com explicação (*"não que seja impossível"*). Vale nas **duas** superfícies, porque ambas passam pelo mesmo `formatarProbabilidade`. Um segundo caminho para o mesmo erro também foi fechado: `0,04%` arredondado para uma casa daria `"0,0%"`, e agora sai `"< 0,1%"`.
  - [x] **A data-base aparece** — *"Calculado sobre dados até 24/07/2026 · dado de 3 dias atrás"*, no painel e no cartão.
  - 🚨 **Descoberto ao fazer: o cartão da listagem era uma segunda superfície de risco**, ainda no caminho legado. Com o detalhe já no modelo novo, os dois mostravam **números diferentes para o mesmo recife**. Corrigido junto; o selo passou de quatro níveis herdados para **binário**, porque o modelo produz probabilidade e limiar, não nível.

## Critério de aprovação

O go-live só é autorizado quando o checklist estiver **100% concluído** (todos os itens marcados como `[x]`).

## Regra de bloqueio

Se **qualquer** item do checklist falhar, o site deve permanecer **offline**.

---

# Roadmap

Estado em **27/07/2026**. O checklist acima diz *o que falta para publicar*;
este roadmap diz *em que ordem*, e vai além do go-live.

## Onde o projeto está

O caminho do dado está **fechado de ponta a ponta, menos o último metro**:

```
satélite → ingestão → PostgreSQL → dataset → modelo → artefato → /api/painel-risco/ → ??? → tela
                                                                                       ↑
                                                                            é só aqui que falta
```

| Camada | Estado |
|---|---|
| Ingestão NOAA + Copernicus | ✅ verificada ao vivo, com proveniência por valor |
| PostgreSQL, 57.420 medições | ✅ fonte única |
| Neo4j como projeção | ✅ reconstruível e conferida |
| Conjunto supervisionado | ✅ com guardas contra vazamento |
| Modelo treinado e medido | ✅ leave-year-out contra linha de base |
| Calibração | ✅ ECE 0,081 → 0,0039 |
| Artefato persistido | ✅ `.joblib` + metadados legíveis |
| API da série | ✅ `/api/medicoes/` |
| **API da predição** | ✅ `/api/painel-risco/` |
| **Frontend** | ✅ consome o modelo novo nas duas superfícies |
| Deploy / agendamento / CI | ❌ não existem |

**489 testes de backend + 71 de frontend, todos offline.**

## Fase 1 — fechar o último metro (bloqueia o go-live)

| # | O quê | Estado |
|---|---|---|
| 1.1 | Painel ler `/api/painel-risco/` | ✅ **27/07** — `PainelPredicao` substituiu `PainelRisco`, que lia os 3 registros do legado |
| 1.2 | 🚨 Nunca exibir "0%" nem "100%" | ✅ **27/07** — extremo vira faixa; e `0,04%` vira `< 0,1%` em vez de `0,0%` |
| 1.3 | Data-base e estado "sem dado suficiente" | ✅ **27/07** — cinco estados tratados, nenhum exibe número no lugar do que falta |
| 1.4 | Nome honesto do produto | ✅ **27/07** — "estresse térmico" nas duas superfícies, travado por teste |
| 1.5 | Aprovar o limiar | ✅ **27/07 — decidido: 0,10**, priorizando antecedência. Compra o episódio de 9 dias de 2022 e o aviso no 1º dia em 18/20; custa 6,3 dias a mais de alarme falso por ano e por recife (§22.9.5) |
| 1.6 | Endpoint `banco-de-dados` | ✅ **27/07** — já existia (`/api/datasets/`); o defeito era o catálogo anunciar 9 conjuntos com a API servindo 3. Cobertura agora derivada do banco |
| 1.7 | Aprovar as variáveis canônicas | ✅ **28/07** — vocabulário consistente nos dois sentidos, `thetao` removido de `sst`, três nomes sem dado agora com motivo declarado e travado por teste |

⚠️ **1.1 acabou sendo maior do que a linha sugeria.** A listagem de recifes era
uma **segunda superfície** exibindo risco, ainda no caminho legado — e com o
detalhe já migrado, os dois mostravam números diferentes para o mesmo recife.
Foi corrigida junto, e o selo passou de quatro níveis herdados para **binário**,
porque o modelo produz probabilidade e limiar, não nível.

## Fase 2 — poder publicar sem quebrar

Nada aqui bloqueia o go-live *técnico*, e tudo aqui bloqueia o go-live
*sustentável*.

| # | O quê | Por que |
|---|---|---|
| 2.1 | **Passo de deploy que reconstrua os três derivados** | `.docx`, `.joblib` e o grafo são todos não versionados e regeráveis. Quem publicar hoje sobe um site **sem modelo** — a API responderia 503 |
| 2.2 | Agendamento da ingestão | Nada roda sozinho; a série congela no dia do deploy |
| 2.3 | CI rodando os 560 testes | Eles já pegaram cinco defeitos reais. Fora do CI, dependem de alguém lembrar |
| 2.4 | Monitorar `dias_de_atraso` | O campo existe; ninguém olha. É o sinal de ingestão parada |

## Fase 3 — dívida acumulada

Barata de resolver, e cresce em silêncio.

| # | O quê | Tamanho |
|---|---|---|
| 3.1 | Apagar `backend/ml_models/modelo_coral_rf.pkl` | O modelo legado que predizia `0.0` para tudo. **Perigoso enquanto existir** |
| 3.2 | Apagar `backend/dados/` | ~260 MB de CSV que nada lê. ⚠️ **Não é mais uma exclusão livre:** a regra 2 do inventário desativa registro sem arquivo, então apagar a pasta **esvazia a página do catálogo**. Decidir antes, não descobrir depois ([FONTES.md](docs/FONTES.md) §6.20) |
| 3.3 | **Aposentar `/api/monitoramento/`** | ⬆️ **Desbloqueado em 27/07:** o frontend migrou (1.1) e não consome mais. O endpoint e o `StatusPredicao` continuam de pé, servindo 3 registros de um modelo que não é mais o do projeto — agora é só armadilha |
| 3.5 | Limpar a camada legada de `utils/recifes.js` | `possuiPainelCompleto`, `obterMetaRisco` e os campos `risco_atual`/`nivel_alerta` ficaram órfãos quando o cartão migrou. `RISCO_STATUS` tem quatro níveis que o modelo atual não produz |
| 3.4 | Resolver os `[cite: N]` de `treinar_modelo.py` | Seis referências apontando para um documento não identificado |

## Fase 4 — submissão acadêmica

Independente do site. Pode correr em paralelo.

| # | O quê | Estado |
|---|---|---|
| 4.1 | **DOIs dos produtos CMEMS e do ERA5** | ⛔ **bloqueia submissão.** Não bloqueia o site |
| 4.2 | Declarar §18 e §20 em qualquer texto | Os resultados negativos são **condicionais**; omitir as condições afirma demais |
| 4.3 | Investigar 2022 | Único ano em que o modelo perde claramente para a persistência |
| 4.4 | Gravar `Predicao` e projetá-la no grafo | Fecha a travessia de proveniência completa — hoje só metade dela existe |

## O que está fechado e não volta

| | Por quê |
|---|---|
| ⛔ Conector do ERA5 | O vento medido **piora** o modelo (0,673 contra 0,692 sem vento). [ERA5.md](docs/ERA5.md) |
| ⛔ Mais variáveis ambientais | Com 13 features sobre 166 visitas os coeficientes não se sustentam |
| ⛔ Ampliar a janela ambiental | Testado de 7 a 90 dias; nenhum tamanho ajuda |
| ⛔ Qualidade da água | 45.318 valores ingeridos, nenhuma combinação melhora |

---

## Histórico

| Data | Alteração |
|---|---|
| 28/07/2026 | ✅ **Variáveis canônicas aprovadas — o último item da fase 1.** Auditado nos dois sentidos, e a boa notícia veio primeiro: **nenhuma inconsistência interna** entre `MAPA_COLUNAS`, `UNIDADES` e `VARIAVEL_CHOICES`, e nenhuma variável no banco fora do contrato. As quatro conferências viraram teste, porque nenhuma delas falha na hora — falham com `KeyError` no meio de uma gravação, ou com o banco recusando a linha **depois** de a rede já ter sido consultada. 🚨 **Um defeito real, e do tipo mais difícil de ver:** `thetao` (temperatura potencial a **13,47 m**) e `CRW_SST` (superfície) traduziam para o **mesmo** nome canônico. [FONTES.md](docs/FONTES.md) §6.10 já registrava a mistura de profundidades como problema do acervo — o vocabulário a **codificava**, que é onde ela fica mais difícil de perceber. Nunca foi ingerido, então era armadilha dormente. Removido, e movido para `COLUNAS_RECUSADAS` em vez de apagado: desconhecida devolve `None` em silêncio, recusada levanta com o motivo. Segunda decisão: `clorofila`, `kd490` e `par` **ficam**, porque os três foram avaliados e rejeitados por razão medida e apagar apagaria essa memória — mas agora com motivo em `SEM_DADO` e **teste exigindo motivo para todo canônico sem conector**. Corrigidos também dois parágrafos do contrato que eram **falsos** desde 25–27/07 (diziam que a pipeline NOAA/Copernicus não estava implementada e que o grafo derivava de `StatusPredicao`). Um teste meu falhou primeiro por esquecer que `baa_area_alerta` é **derivada** no conector e não vem do ERDDAP. 8 testes novos. |
| 27/07/2026 | ✅ **Limiar de alerta decidido: 0,10** — o penúltimo item aberto da fase 1. `manage.py limiar` varre 19 cortes sobre as predições fora da dobra e traduz tudo para *dias de alarme falso por ano e por recife*. ⚠️ **Uma conclusão minha caiu no meio do caminho:** eu havia escrito que "0,20 é dominado por 0,30" olhando só episódios e alarme falso; ao medir **quando** o aviso chega, o domínio some — entre 0,20 e 0,30 os avisados no 1º dia caem de 16/20 para 13/20. Fica o aviso de método: patamar em métrica agregada esconde movimento no que ela não mede. Critério declarado da decisão: **priorizar antecedência** — para um público que age sobre o aviso, chegar tarde é quase o mesmo que não chegar. 0,10 compra o episódio de **nove dias** de Picãozinho em 2022 e o aviso no 1º dia em 18/20; custa 6,3 dias a mais de alarme falso por ano e por recife. 🚨 Registrado que a decisão **não resolve o teto**: um episódio (Picãozinho, 21–23/04/2026) escapa em **todos** os limiares — isso é do modelo, e continua aberto. E que o 0,20 anterior nunca havia sido escolhido: era herança do `0,50` do `predict` sob `class_weight`. 19 testes. |
| 27/07/2026 | ✅ **Endpoints estáveis fechados — e o último trouxe o quarto caso da mesma regra.** ⚠️ Começa com uma correção minha: eu havia registrado que o endpoint `banco-de-dados` *"ainda não existe"*, **sem verificar**. Ele existe (`/api/datasets/`) desde antes. O defeito real era outro e mais grave: 🚨 **o catálogo anunciava 9 conjuntos e a API servia 3** — pH, clorofila, nitrato, `thetao`, KD490 e o SST do Met Office apareciam com título, formato, período e tamanho **sem uma única medição no banco**, indistinguíveis dos reais. E `noaa_crw_dhw` declarava fim em 2025-11-30 com a série já em 2026-07-24: anunciando dado inexistente e **escondendo dado existente** ao mesmo tempo. A causa é a mesma que já cobrou preço três vezes — **cobertura estava gravada**, e cópia guardada envelhece em silêncio. Agora é derivada do banco a cada resposta, e cada número vem com **`consulta`**, a URL que o comprova (conferida nos três: o `count` bate). Na tela, três estados que não se implicam: *disponível*, *referência externa* e *não verificada*. Fecha o item pai, e com ele um padrão: em **dois dos três** endpoints o problema não era faltar, era servir a coisa errada com aparência de certa. ⚠️ Efeito colateral registrado: **apagar `backend/dados/` esvazia a página do catálogo** (fase 3.2). 29 testes. |
| 27/07/2026 | ✅ **O site passou a mostrar o modelo deste projeto — fase 1.1–1.4 concluída.** `PainelPredicao` substituiu o `PainelRisco`, que lia `/api/monitoramento/`: até hoje **o número na tela não vinha do modelo treinado, calibrado e persistido**, e sim dos 3 registros do `StatusPredicao` legado. 🚨 **Descoberto ao fazer: a listagem de recifes era uma segunda superfície de risco**, também no legado — com o detalhe já migrado, os dois exibiriam números diferentes para o mesmo recife, cada um de um modelo. Corrigida junto, e o selo virou **binário**, porque o modelo produz probabilidade e limiar declarado, não os quatro níveis herdados. As regras de exibição ficaram em funções puras (`utils/painelRisco.js`) e são compartilhadas pelas duas superfícies — é o que garante que **nenhuma delas consiga escrever "0%" ou "100%"**. Um segundo caminho para o mesmo erro foi fechado no caminho: `0,04%` arredondado para uma casa daria `"0,0%"`, e agora sai `"< 0,1%"`. E o frontend **não recalcula** `probabilidade >= limiar`: usa o campo `alerta` do servidor, senão as duas versões divergiriam em silêncio. 63 testes de frontend. Dois itens do checklist caíram: nome honesto do produto e painel exibindo predição. |
| 27/07/2026 | **Roadmap acrescentado.** O checklist dizia *o que falta*; faltava dizer *em que ordem*, e o que existe além do go-live. Quatro fases: fechar o último metro (o frontend ainda lê `/api/monitoramento/`, os 3 registros do modelo legado — **o que a tela mostra hoje não vem do modelo novo**), poder publicar sem quebrar (sem passo de deploy, quem publicar sobe um site **sem modelo**, e a API responde 503), dívida acumulada, e submissão acadêmica. Registrado separadamente o que está **fechado e não volta** — ERA5, mais variáveis ambientais, janela maior, qualidade da água —, para que nenhum deles seja retomado por esquecimento. |
| 27/07/2026 | ✅ **`painel-risco` no ar — o site passou a saber responder a pergunta que dá nome ao projeto.** É o primeiro endpoint que faz conta: carrega o modelo persistido, monta a janela de 7 dias e devolve a probabilidade calibrada com data-base, atraso, entradas e limiar. 🚨 **E a execução criou um requisito de interface que ninguém tinha previsto**: a probabilidade calibrada é uma **função escada que toca 0 e 1** — os três recifes voltaram com o mesmo 0,0029, e 12,2% das amostras de treino saem em `p = 0,000` exato. Exibir "0% de risco" seria traduzir um degrau finito em impossibilidade. A API sinaliza; o frontend ainda não trata. Registrados também: a distinção entre série que **acaba mais cedo** (responde, com atraso declarado) e série **furada** (recusa), e um defeito real — o modelo voltava do disco dizendo `calibracao: None` mesmo sendo isotônico. |
| 27/07/2026 | **`/api/medicoes/` criado e contrato do `painel-risco` fixado.** A descoberta desconfortável: as **57.420 medições não tinham endpoint nenhum** — o `/api/monitoramento/` que o frontend consome devolve os 3 registros do `StatusPredicao` legado, e toda a série ingerida do NOAA e do Copernicus estava inalcançável pela API. Registrado também um erro cometido e revertido: ligar paginação global trocaria a resposta de toda lista de array para envelope, quebrando quatro endpoints já consumidos como array — **quebra de contrato disfarçada de configuração**, pega por três testes que não foram escritos pensando nisso. O `painel-risco` fica como próximo, com o contrato já derivado do artefato do modelo e três decisões registradas em [docs/arquitetura.md](docs/arquitetura.md). |
| 27/07/2026 | ✅ **Neo4j destravado — terceiro bloqueio do dia.** A projeção reconstrói o grafo a partir do PostgreSQL e confere item a item. Ficam duas pendências menores, ambas registradas: `Predicao` não entra enquanto o modelo novo não gravar saída, e a projeção precisa de um passo de deploy — que agora é a **terceira** coisa derivada nessa situação, junto do `.docx` e do `.joblib`. |
| 27/07/2026 | ✅ **Calibração resolvida — segundo bloqueio derrubado no mesmo dia.** O modelo prometia o dobro do que acontecia; recalibração isotônica levou o ECE de 0,081 a 0,0039. Fica uma pendência nova: **o limiar de alerta virou decisão explícita** (0,20 no modelo calibrado, contra 0,50 antes), e o painel precisa declarar qual usa. |
| 27/07/2026 | ✅ **Modelo persistido — o bloqueio identificado ontem está resolvido.** `manage.py treinar_final` treina uma vez sobre todos os dados e grava o artefato com metadados legíveis ao lado. O carregamento recusa artefato de origem ou versão desconhecida, porque `joblib.load` executa código e o pickle de um `Pipeline` falha em **silêncio** entre versões do scikit-learn. Ficam duas pendências novas e menores: o **deploy precisa rodar `treinar_final`** (passo que não existe ainda) e o `.pkl` legado continua no repositório. |
| 26/07/2026 | Acrescentados três itens ao checklist, todos identificados ao responder "onde os dados estão salvos?". O principal: **nenhum modelo treinado é persistido** — descoberto ao verificar que não há `joblib`, `pickle` nem `.dump()` em `backend/ml/`. É bloqueio duro para o painel, e não estava registrado em lugar nenhum. Os outros dois — calibração medida e nome honesto do produto na interface — já existiam como observação em documentos técnicos, mas não como critério de go-live. |
