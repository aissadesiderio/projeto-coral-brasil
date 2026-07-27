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
- [ ] Endpoints backend estáveis: `localizacoes`, `banco-de-dados`, `painel-risco`.
  - [x] **`/api/medicoes/` criado** — 27/07/2026. As **57.420 medições ambientais não tinham endpoint nenhum**: o `/api/monitoramento/` que o frontend consome devolve `StatusPredicao`, o modelo legado com **3 registros**. Toda a série ingerida do NOAA e do Copernicus estava inalcançável pela API. Serve com proveniência por valor (`fonte`, `dataset_id`, `quality_flag`, `observacao`), filtros combináveis, e **data inválida falhando com 400** — sem isso `?de=ontem` seria ignorado e o cliente receberia tudo achando que recebeu o recorte. 22 testes.
    - ⚠️ **Paginação é por view, nunca global.** A primeira tentativa ligou `DEFAULT_PAGINATION_CLASS`; três testes existentes flagraram na hora, porque isso troca a resposta de **toda** lista de array cru para envelope `{count, results}` — e quatro endpoints já são consumidos como array. Seria quebra de contrato disfarçada de configuração. Ver o comentário em `coral_site/settings.py`.
  - [x] **`painel-risco` criado** — ✅ **27/07/2026, o primeiro endpoint que faz conta.** Todos os outros entregam dado guardado. Este carrega o modelo persistido, monta a janela de 7 dias a partir da série e responde a probabilidade **calibrada**, com data-base, atraso, entradas e limiar no payload. Verificado ao vivo contra o PostgreSQL: os três recifes respondem com data-base 24/07 e alvo 31/07. 54 testes. O contrato veio do artefato, não da view. Ver [docs/arquitetura.md](docs/arquitetura.md).
    - 🚨 **Descoberto ao executar: a probabilidade é uma escada que toca 0 e 1.** Os três recifes voltaram com **exatamente 0,0029** apesar de entradas diferentes — a recalibração isotônica é função escada, e 12,2% das amostras de treino saem em `p = 0,000` exato. Isso **muda um requisito da interface**: exibir "0% de risco" ou "100%" traduz um degrau finito em impossibilidade ou certeza. A API sinaliza com `no_extremo`; a decisão de exibição é do item abaixo. Ver [docs/RESULTADOS.md](docs/RESULTADOS.md) §22.8.
    - ⚠️ **O limiar 0,20 está em `settings.PAINEL_LIMIAR`, e ninguém o aprovou ainda.** É o ponto de desempenho equivalente ao antigo 0,50, não uma escolha de produto: subir troca alarme falso por evento perdido.
  - [ ] `banco-de-dados` — ainda não existe.
- [ ] Variáveis canônicas aprovadas.
- [x] **Modelo treinado persistido** — ✅ **resolvido em 27/07/2026.** `manage.py treinar_final` treina **uma vez sobre todos os dados** e grava o artefato em `dados/modelos/`, com os metadados ao lado em JSON legível. Gravado: `baa ≥ 3` em t+7, 4 colunas de trajetória, 7.095 amostras com 596 positivas. O carregamento **recusa** artefato sem a assinatura do projeto ou de outra versão do scikit-learn — `joblib.load` executa código, e o pickle de um `Pipeline` falha em silêncio entre versões. 16 testes. Ver [docs/VISAO_GERAL.md](docs/VISAO_GERAL.md) §7.4.
  - ⚠️ O artefato **não é versionado** — é derivado e regerável pelo comando. Isso significa que o **deploy precisa rodar `treinar_final`**, e esse passo ainda não existe em lugar nenhum.
  - ⚠️ O `.pkl` legado em `backend/ml_models/modelo_coral_rf.pkl` continua no repositório — é o que predizia `0.0` para tudo. **Não pode ser usado**, e ainda não foi removido.
- [x] **Calibração medida** — ✅ **resolvida em 27/07/2026, e o defeito era grave.** O modelo prometia **0,165** onde a taxa real é **0,084** (ECE 0,081, do tamanho do próprio fenômeno). O Brier "bom" de 0,043 escondia isso: a decomposição de Murphy mostrou que a **incerteza sozinha é o dobro do Brier**. Corrigido com recalibração isotônica — ECE **0,0039**, e a curva fecha. `manage.py calibrar` mede; `treinar_final` grava recalibrado por padrão. 24 testes. Ver [docs/RESULTADOS.md](docs/RESULTADOS.md) §22.
  - ⚠️ **O limiar de alerta virou decisão explícita.** Calibrar não custa detecção, mas move o corte: o ponto equivalente ao antigo fica em **0,20**, não em 0,50. O painel precisa declarar qual usa.
- [ ] **Nome do produto conferido na interface** — o modelo prevê **estresse térmico**, não branqueamento observado. Medido em 26/07/2026: a régua térmica da NOAA perde **78 dos 88** branqueamentos brasileiros observados ([docs/RESULTADOS.md](docs/RESULTADOS.md) §11). Chamar o painel de "previsão de branqueamento" seria prometer o que ele não entrega.
- [ ] Painel exibindo predição com dados suficientes e rastreáveis.
  - ⚠️ **"Dados suficientes" virou critério verificável, e não adjetivo.** A janela do modelo é de 7 dias; faltando dia, a resposta é *sem dado suficiente*, e não uma probabilidade calculada sobre lacuna. O motivo está registrado em [docs/arquitetura.md](docs/arquitetura.md): **zero é valor legítimo para uma variação** — `sst_variacao_7d = 0` afirma "a temperatura não mudou". Preencher lacuna com zero não gera número suspeito; gera a afirmação mais tranquilizadora possível, justamente quando o dado sumiu.
  - ⚠️ **O limiar vai no payload junto da probabilidade.** Não existe corte natural: a recalibração isotônica moveu o ponto equivalente ao antigo 0,50 para **0,20**. Devolver só o rótulo "alto/baixo" esconde uma decisão de produto dentro de um número. ✅ O endpoint já faz isso; falta o painel usar.
  - 🚨 **A interface não pode exibir "0%" nem "100%".** Requisito novo, descoberto em 27/07 ao executar o modelo — não estava previsto. A API já entrega `no_extremo: true` quando acontece; **falta o frontend tratar**. Ver [docs/RESULTADOS.md](docs/RESULTADOS.md) §22.8.
  - ⚠️ **O painel precisa mostrar a data-base, e não só o número.** A série tem latência variável; hoje são 3 dias. Um risco sem a data sobre a qual foi calculado é lido como "agora".

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
| **Frontend** | ❌ ainda lê `/api/monitoramento/`, o legado de 3 registros |
| Deploy / agendamento / CI | ❌ não existem |

**441 testes, todos offline.**

## Fase 1 — fechar o último metro (bloqueia o go-live)

Ordem sugerida. Os três primeiros são o mesmo trabalho no frontend.

| # | O quê | Por que agora | Onde |
|---|---|---|---|
| 1.1 | `PainelRisco.jsx` passar a ler `/api/painel-risco/` | Hoje ele consome `/api/monitoramento/`, que são **3 registros do modelo legado** — o que a tela mostra não vem do modelo novo | `frontend/src/components/PainelRisco.jsx` |
| 1.2 | 🚨 **Nunca exibir "0%" nem "100%"** | A isotônica devolve extremos exatos por construção; a API já sinaliza com `no_extremo`. Exibir traduziria degrau finito em impossibilidade/certeza | §22.8 |
| 1.3 | Exibir **data-base** e estado "sem dado suficiente" | Risco sem data é lido como "agora"; e a recusa precisa aparecer como recusa, não como ausência | — |
| 1.4 | **Nome honesto do produto** | O modelo prevê **estresse térmico**. A régua da NOAA perde 78 dos 88 branqueamentos brasileiros — chamar de "previsão de branqueamento" promete o que não entrega | §11 |
| 1.5 | Aprovar o **limiar 0,20** | Está no `settings` por ser o ponto equivalente ao antigo 0,50, não por decisão sobre alarme falso × evento perdido. **Decisão sua, não do modelo** | §22.5 |
| 1.6 | Endpoint `banco-de-dados` | Último item de "endpoints estáveis" ainda aberto | — |
| 1.7 | Aprovar as **variáveis canônicas** | Item de go-live que nunca foi fechado | — |

## Fase 2 — poder publicar sem quebrar

Nada aqui bloqueia o go-live *técnico*, e tudo aqui bloqueia o go-live
*sustentável*.

| # | O quê | Por que |
|---|---|---|
| 2.1 | **Passo de deploy que reconstrua os três derivados** | `.docx`, `.joblib` e o grafo são todos não versionados e regeráveis. Quem publicar hoje sobe um site **sem modelo** — a API responderia 503 |
| 2.2 | Agendamento da ingestão | Nada roda sozinho; a série congela no dia do deploy |
| 2.3 | CI rodando os 441 testes | Eles já pegaram cinco defeitos reais. Fora do CI, dependem de alguém lembrar |
| 2.4 | Monitorar `dias_de_atraso` | O campo existe; ninguém olha. É o sinal de ingestão parada |

## Fase 3 — dívida acumulada

Barata de resolver, e cresce em silêncio.

| # | O quê | Tamanho |
|---|---|---|
| 3.1 | Apagar `backend/ml_models/modelo_coral_rf.pkl` | O modelo legado que predizia `0.0` para tudo. **Perigoso enquanto existir** |
| 3.2 | Apagar `backend/dados/` | ~260 MB de CSV que nada lê, incluindo os arquivos defeituosos de [FONTES.md](docs/FONTES.md) §6 |
| 3.3 | Aposentar `/api/monitoramento/` | Só existe enquanto o frontend não migrar (1.1). Depois disso, é armadilha |
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
| 27/07/2026 | **Roadmap acrescentado.** O checklist dizia *o que falta*; faltava dizer *em que ordem*, e o que existe além do go-live. Quatro fases: fechar o último metro (o frontend ainda lê `/api/monitoramento/`, os 3 registros do modelo legado — **o que a tela mostra hoje não vem do modelo novo**), poder publicar sem quebrar (sem passo de deploy, quem publicar sobe um site **sem modelo**, e a API responde 503), dívida acumulada, e submissão acadêmica. Registrado separadamente o que está **fechado e não volta** — ERA5, mais variáveis ambientais, janela maior, qualidade da água —, para que nenhum deles seja retomado por esquecimento. |
| 27/07/2026 | ✅ **`painel-risco` no ar — o site passou a saber responder a pergunta que dá nome ao projeto.** É o primeiro endpoint que faz conta: carrega o modelo persistido, monta a janela de 7 dias e devolve a probabilidade calibrada com data-base, atraso, entradas e limiar. 🚨 **E a execução criou um requisito de interface que ninguém tinha previsto**: a probabilidade calibrada é uma **função escada que toca 0 e 1** — os três recifes voltaram com o mesmo 0,0029, e 12,2% das amostras de treino saem em `p = 0,000` exato. Exibir "0% de risco" seria traduzir um degrau finito em impossibilidade. A API sinaliza; o frontend ainda não trata. Registrados também: a distinção entre série que **acaba mais cedo** (responde, com atraso declarado) e série **furada** (recusa), e um defeito real — o modelo voltava do disco dizendo `calibracao: None` mesmo sendo isotônico. |
| 27/07/2026 | **`/api/medicoes/` criado e contrato do `painel-risco` fixado.** A descoberta desconfortável: as **57.420 medições não tinham endpoint nenhum** — o `/api/monitoramento/` que o frontend consome devolve os 3 registros do `StatusPredicao` legado, e toda a série ingerida do NOAA e do Copernicus estava inalcançável pela API. Registrado também um erro cometido e revertido: ligar paginação global trocaria a resposta de toda lista de array para envelope, quebrando quatro endpoints já consumidos como array — **quebra de contrato disfarçada de configuração**, pega por três testes que não foram escritos pensando nisso. O `painel-risco` fica como próximo, com o contrato já derivado do artefato do modelo e três decisões registradas em [docs/arquitetura.md](docs/arquitetura.md). |
| 27/07/2026 | ✅ **Neo4j destravado — terceiro bloqueio do dia.** A projeção reconstrói o grafo a partir do PostgreSQL e confere item a item. Ficam duas pendências menores, ambas registradas: `Predicao` não entra enquanto o modelo novo não gravar saída, e a projeção precisa de um passo de deploy — que agora é a **terceira** coisa derivada nessa situação, junto do `.docx` e do `.joblib`. |
| 27/07/2026 | ✅ **Calibração resolvida — segundo bloqueio derrubado no mesmo dia.** O modelo prometia o dobro do que acontecia; recalibração isotônica levou o ECE de 0,081 a 0,0039. Fica uma pendência nova: **o limiar de alerta virou decisão explícita** (0,20 no modelo calibrado, contra 0,50 antes), e o painel precisa declarar qual usa. |
| 27/07/2026 | ✅ **Modelo persistido — o bloqueio identificado ontem está resolvido.** `manage.py treinar_final` treina uma vez sobre todos os dados e grava o artefato com metadados legíveis ao lado. O carregamento recusa artefato de origem ou versão desconhecida, porque `joblib.load` executa código e o pickle de um `Pipeline` falha em **silêncio** entre versões do scikit-learn. Ficam duas pendências novas e menores: o **deploy precisa rodar `treinar_final`** (passo que não existe ainda) e o `.pkl` legado continua no repositório. |
| 26/07/2026 | Acrescentados três itens ao checklist, todos identificados ao responder "onde os dados estão salvos?". O principal: **nenhum modelo treinado é persistido** — descoberto ao verificar que não há `joblib`, `pickle` nem `.dump()` em `backend/ml/`. É bloqueio duro para o painel, e não estava registrado em lugar nenhum. Os outros dois — calibração medida e nome honesto do produto na interface — já existiam como observação em documentos técnicos, mas não como critério de go-live. |
