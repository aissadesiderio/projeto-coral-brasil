# Diretrizes do projeto

**Para quem for mexer neste repositório — pessoa ou agente.** Não são preferências de estilo. Cada uma abaixo existe porque o projeto pagou por ela, e a coluna da direita diz quando.

Se uma diretriz conflitar com o que parece mais rápido, ela ganha. Se conflitar com outra diretriz, o caso está no fim do documento.

---

## 1. Proveniência

### 1.1 Não afirme o que não consegue datar

Um valor sem data de origem tem prazo de validade invisível. `Dendrogyra cylindrus` foi **Vulnerável de 2008 a 2022** e hoje é **Criticamente Ameaçada** — as duas afirmações estão certas, em anos diferentes. Sem o ano, a tela não distingue *"é CR"* de *"era VU quando alguém digitou isto"*, e a segunda leitura envelhece sozinha.

**Na prática:** todo dado citável carrega origem, data da origem e data da última conferência. São três campos diferentes e nenhum substitui os outros.

> Origem: migração `0022`, 31/07/2026 — nove espécies com conservação em texto livre e `fonte_url` vazio em todas.

### 1.2 Lacuna declarada vale mais que afirmação errada

Quando a migração `0022` encontrou `"Não avaliado"` em cinco espécies, a tentação era gravar `NE`. Mas `NE` é uma **categoria real da IUCN**, e afirmá-la seria provavelmente falso para duas delas, que têm avaliação publicada. Virou campo vazio.

O site parou de exibir categoria nas nove espécies. **Isso não foi regressão — foi parar de afirmar o que não se consegue datar.**

**Na prática:** entre gravar "desconhecido" como se fosse valor e deixar vazio, deixe vazio. Entre um relatório que omite o que falta e um que declara, declare.

### 1.3 Vazio continua vazio até a borda da tela

`credito or 'Acervo local do projeto'` — um valor-padrão calculado na leitura. Depois de escrito em arquivo, ficou **indistinguível de dado real**. Foi assim que uma foto sem licença nenhuma apareceu creditada ao projeto em três lugares diferentes, sem ninguém nunca ter digitado isso.

**Na prática:** `"Sem crédito informado"` é texto de interface, escrito no componente. Nunca um default no modelo, no serializer ou no exportador.

> Origem: migração `0026`, 11–12/08/2026.

### 1.4 Cite quem entregou, não quem originou

Wikidata e GBIF publicam a categoria da IUCN sem token, e são fonte legítima **se declaradas**. O que não pode é apresentá-las como se viessem da IUCN. Por isso existe `iucn_origem`.

**Na prática:** se o caminho de obtenção muda, o campo de origem muda junto — e a tela precisa ler esse campo. Um campo de origem que a interface ignora não audita nada.

---

## 2. Medição

### 2.1 Conte do dado, nunca de agregado gravado

A cobertura dos datasets estava **gravada** num campo. Envelheceu em silêncio. A tabela do RESULTADOS.md montada a partir dela trocou dois episódios de lugar — e **isso decidiu o limiar de alerta do projeto**. Pagamos 6,3 dias a mais de alarme falso por ano acreditando resgatar um episódio de nove dias; resgatamos um de um dia.

O dado nunca esteve errado. A leitura esteve.

**Na prática:** relatório, auditoria e figura leem a tabela real na hora. Mais lento, e é o único jeito da resposta ser sobre o presente.

> Origem: 27/07 e 30/07/2026.

### 2.2 Meça antes de otimizar

Cache, índice e paralelismo entram **depois** de existir número dizendo onde dói. Otimizar sem medida é adivinhar, e adivinhação em infraestrutura fica no código para sempre.

### 2.3 Reproduza antes de consertar

O CI rodou **6 vezes, todas vermelhas**, sem ninguém ver. A causa só ficou clara depois de apagar do disco exatamente o que o `.gitignore` esconde e rodar com as variáveis do CI — as mesmas 2 falhas, com os mesmos nomes. Sem essa reprodução, a alternativa era inferir a causa do *exit code*, erro que este projeto já pagou duas vezes.

### 2.4 O teste trava a decisão, não o código

Um teste que repete a implementação quebra em toda refatoração e não protege nada. Escreva o teste sobre a **razão** da escolha: que `--completo` refaz tudo, que categoria sem ano não é exibida, que o console não recebe emoji.

---

## 3. Operação

### 3.1 O que não escala não é conferir — é lembrar de conferir

Com 9 espécies alguém lembra. Com 300, não. A conferência virou `manage.py conferir_especies` e entrou no relatório diário.

**Na prática:** toda obrigação recorrente vira comando ou relatório. E o relatório **fica calado quando está tudo bem** — aviso diário treina quem lê a ignorar.

### 3.2 Falha precisa sair com código 1

`neo4j_projetar` imprimia o erro e retornava normalmente. O `preparar_deploy` registrava o passo como executado, e o deploy seguiria com o grafo vazio. Código de saída é o único canal que um agendador entende.

### 3.3 Um único caminho de escrita por banco

`neo4j_seed` e a projeção escreviam no mesmo grafo. O legado era o mais perigoso dos três comandos removidos **por funcionar**: sobrescreveria a projeção com dado de demonstração. Nenhuma rotina escreve no Neo4j sem passar pelo PostgreSQL antes.

### 3.4 Sem emoji no que é impresso

O console do Windows usa **cp1252**. Um emoji em `stdout.write` mata o processo no meio, e o sintoma não lembra a causa: o comando aparece como "falhou" depois de ter feito todo o trabalho. Há teste varrendo `management/commands/`.

⚠️ A regra vale só para o que é **impresso**. Docstrings e comentários continuam com emoji.

---

## 4. Código

### 4.1 Comentário que envelhece é pior que comentário ausente

O cartão do painel trazia *"o modelo atual não produz nível"* — verdade quando foi escrito, **falsa desde a véspera**. É a forma mais cara de comentário errado: o argumento continua convincente depois de deixar de ser verdadeiro.

**Na prática:** ao mudar o comportamento, procure o comentário que o justificava. Se ele explica *por que* algo é como é, ele é parte do código.

### 4.2 Explique com exemplo trabalhado

Decisão não óbvia se registra com um exemplo numérico pequeno. O raciocínio vai para VARIAVEIS.md; a medição, para FONTES.md.

### 4.3 Documente no mesmo commit

Toda fonte, referência ou correção de proveniência entra em [FONTES.md](FONTES.md) junto com a mudança. Decisão de arquitetura entra em [arquitetura.md](arquitetura.md). Documentação que chega depois não chega.

### 4.4 Não decida sobre arquivo pelo nome

Sete arquivos órfãos foram abertos um a um antes de sair. A leitura valeu: um era duplicata de valor do pH catalogado, e dois eram o produto de **análise** ao lado da reanálise, divergindo em até 0,235 mmol/m³ para a mesma data e o mesmo ponto. Essa medição era o que valia guardar — não os arquivos.

---

## 5. Rastro

### 5.1 Número vai em campo, não embutido na frase

`logger.info('406 medições')` só volta a ser número por regex sobre prosa. `extra={'medicoes': 406}` vira campo somável no JSON.

### 5.2 O rastro precisa de um fio

Uma execução de `manage.py atualizar` percorre 2 fontes × 10 locais × N blocos, e cada camada escreve suas próprias linhas. Sem `correlacao`, "log ponta a ponta" não existe — existe log embaralhado. Ver `observabilidade/`.

### 5.3 Checkpoint é sobre o que foi *tentado*, nunca sobre o que *existe*

Quem responde o que existe é o dado. Confundir os dois é o único jeito de a retomada causar dano: bastaria restaurar um backup antigo para blocos reais serem pulados **para sempre**, sem erro em lugar nenhum. Daí `conferir()`.

### 5.4 Um resultado sem versão de código não é reproduzível

Commit + estado da árvore acompanham todo artefato. Árvore suja não invalida a medição — invalida a **reconstrução**, e quem for citar precisa saber disso.

---

## 6. Quando as diretrizes conflitam

**Rigor × entrega.** Rigor ganha em tudo que vai ser **citado**; entrega ganha no resto. A categoria de conservação é citável — por isso parou de ser exibida em vez de ser estimada. O rótulo de um botão não é.

**Completude × silêncio.** O relatório diário fica calado em dia normal (§3.1). A auditoria (`manage.py auditar`), não: ela é pedida, e quem pede quer o retrato inteiro, incluindo o que está bem.

**Não inventar × não travar.** Metadado de proveniência nunca derruba o trabalho que ele só ia descrever. Sem git, `codigo` sai `None` com motivo — não levanta exceção e não inventa hash.

---

## Antes de abrir o pull request

- [ ] `cd backend && python manage.py test` — da pasta `backend/`, não da raiz (da raiz roda **zero** testes e sai com sucesso)
- [ ] `cd frontend && npm test`
- [ ] Documento correspondente atualizado no mesmo commit (§4.3)
- [ ] `manage.py auditar` — nenhuma lacuna nova bloqueando
- [ ] Nenhum dado novo sem origem e data (§1.1)
