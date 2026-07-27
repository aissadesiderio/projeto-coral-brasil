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
  - [ ] **`painel-risco` — é o próximo, e o contrato já está fixado.** Todos os endpoints acima entregam dado guardado; nenhum faz conta. Este carrega o modelo persistido e responde a probabilidade. O contrato **não é escolha de quem implementa**: o `dados/modelos/entrega1_baa.json` já declara as quatro colunas, o horizonte de 7 dias, o alvo `baa ≥ 3` e os três locais. Três decisões tomadas e registradas em [docs/arquitetura.md](docs/arquitetura.md): recusar em vez de preencher lacuna, data-base sempre no payload, local fora do treino como 404 com motivo.
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
  - ⚠️ **O limiar vai no payload junto da probabilidade.** Não existe corte natural: a recalibração isotônica moveu o ponto equivalente ao antigo 0,50 para **0,20**. Devolver só o rótulo "alto/baixo" esconde uma decisão de produto dentro de um número.

## Critério de aprovação

O go-live só é autorizado quando o checklist estiver **100% concluído** (todos os itens marcados como `[x]`).

## Regra de bloqueio

Se **qualquer** item do checklist falhar, o site deve permanecer **offline**.

---

## Histórico

| Data | Alteração |
|---|---|
| 27/07/2026 | **`/api/medicoes/` criado e contrato do `painel-risco` fixado.** A descoberta desconfortável: as **57.420 medições não tinham endpoint nenhum** — o `/api/monitoramento/` que o frontend consome devolve os 3 registros do `StatusPredicao` legado, e toda a série ingerida do NOAA e do Copernicus estava inalcançável pela API. Registrado também um erro cometido e revertido: ligar paginação global trocaria a resposta de toda lista de array para envelope, quebrando quatro endpoints já consumidos como array — **quebra de contrato disfarçada de configuração**, pega por três testes que não foram escritos pensando nisso. O `painel-risco` fica como próximo, com o contrato já derivado do artefato do modelo e três decisões registradas em [docs/arquitetura.md](docs/arquitetura.md). |
| 27/07/2026 | ✅ **Neo4j destravado — terceiro bloqueio do dia.** A projeção reconstrói o grafo a partir do PostgreSQL e confere item a item. Ficam duas pendências menores, ambas registradas: `Predicao` não entra enquanto o modelo novo não gravar saída, e a projeção precisa de um passo de deploy — que agora é a **terceira** coisa derivada nessa situação, junto do `.docx` e do `.joblib`. |
| 27/07/2026 | ✅ **Calibração resolvida — segundo bloqueio derrubado no mesmo dia.** O modelo prometia o dobro do que acontecia; recalibração isotônica levou o ECE de 0,081 a 0,0039. Fica uma pendência nova: **o limiar de alerta virou decisão explícita** (0,20 no modelo calibrado, contra 0,50 antes), e o painel precisa declarar qual usa. |
| 27/07/2026 | ✅ **Modelo persistido — o bloqueio identificado ontem está resolvido.** `manage.py treinar_final` treina uma vez sobre todos os dados e grava o artefato com metadados legíveis ao lado. O carregamento recusa artefato de origem ou versão desconhecida, porque `joblib.load` executa código e o pickle de um `Pipeline` falha em **silêncio** entre versões do scikit-learn. Ficam duas pendências novas e menores: o **deploy precisa rodar `treinar_final`** (passo que não existe ainda) e o `.pkl` legado continua no repositório. |
| 26/07/2026 | Acrescentados três itens ao checklist, todos identificados ao responder "onde os dados estão salvos?". O principal: **nenhum modelo treinado é persistido** — descoberto ao verificar que não há `joblib`, `pickle` nem `.dump()` em `backend/ml/`. É bloqueio duro para o painel, e não estava registrado em lugar nenhum. Os outros dois — calibração medida e nome honesto do produto na interface — já existiam como observação em documentos técnicos, mas não como critério de go-live. |
