# Manual de operação — Coral Brasil

**Do zero até o site aberto no navegador.** Este documento supõe que você nunca
abriu um terminal, nunca instalou Python e não sabe o que é um container. Cada
passo tem o comando, **o que deve aparecer na tela** e **o que fazer quando não
aparece**.

> Os outros documentos explicam *por quê*. Este explica *como*.
> Se quiser entender o que o projeto faz antes de rodá-lo, leia
> [VISAO_GERAL.md](VISAO_GERAL.md) — não é pré-requisito, mas ajuda.

| Se você quer… | Vá para |
|---|---|
| instalar tudo pela primeira vez | [Parte 3](#parte-3--instalação-passo-a-passo) |
| só abrir o site numa máquina já instalada | [Parte 4](#parte-4--rodar-o-site) |
| saber o que rodar todo dia | [Parte 6](#parte-6--a-rotina-do-dia-a-dia) |
| consertar algo que quebrou | [Parte 8](#parte-8--quando-algo-dá-errado) |
| entender uma palavra estranha | [Glossário](#glossário) |

---

## Como ler este manual

Ao longo do texto:

| Símbolo | Significa |
|---|---|
| ▶ | um comando para digitar no terminal |
| ✅ | como saber que deu certo |
| ❌ | o erro mais comum nesse ponto, e a saída |
| ⚠️ | uma armadilha que já pegou alguém |
| 🚨 | algo que, se ignorado, produz resultado **errado sem parecer errado** |

**Blocos de código são para copiar e colar**, uma linha por vez, apertando
Enter no fim. Quando o bloco for *conteúdo de arquivo* e não comando, está
escrito antes dele — colar conteúdo de arquivo no terminal é um erro frequente
e o terminal responde com algo confuso como `CommandNotFoundException`.

---

## Parte 1 — O que você vai montar

O Coral Brasil não é um programa só. São **quatro peças** que rodam ao mesmo
tempo e conversam entre si. Entender quem é quem evita 90% da confusão.

```
   VOCÊ (navegador)
        │
        │  http://localhost:3000
        ▼
   ┌─────────────────┐
   │   FRONTEND      │   React. Desenha as telas.
   │   (porta 3000)  │   Não sabe nada sobre corais: só pede e mostra.
   └────────┬────────┘
            │  /api/...
            ▼
   ┌─────────────────┐
   │   BACKEND       │   Django. Responde às perguntas do frontend,
   │   (porta 8000)  │   e é quem CALCULA a previsão de risco.
   └───┬─────────┬───┘
       │         │
       ▼         ▼
 ┌──────────┐ ┌──────────┐
 │PostgreSQL│ │  Neo4j   │   Os dois bancos, dentro do Docker.
 │  (5432)  │ │  (7687)  │   Postgres = a verdade. Neo4j = uma cópia
 └──────────┘ └──────────┘   em forma de rede, para outras perguntas.
```

Em português comum:

1. **Os bancos** guardam os dados. Sobem com um comando de Docker e ficam
   rodando em segundo plano — você não os vê.
2. **O backend** (Django) lê os bancos e responde em `http://localhost:8000`.
   Ele também é quem roda os comandos de coleta e de treino do modelo.
3. **O frontend** (React) é o site em si, em `http://localhost:3000`.
4. **O modelo** não é um programa rodando: é um **arquivo** no disco
   (`dados/modelos/entrega1_baa.joblib`) que o backend carrega quando alguém
   pede a previsão.

⚠️ **Precisam dos quatro para o site funcionar por inteiro.** Faltando os
bancos, o backend não sobe. Faltando o backend, o site abre mas fica vazio.
Faltando o arquivo do modelo, tudo funciona **menos** o painel de risco, que
responde "modelo indisponível".

### O que é "deploy" e por que ele não aparece aqui

Rodar na sua máquina é o que este manual cobre. **Deploy** é publicar num
servidor para que outras pessoas acessem pela internet — outro assunto, coberto
pela [Parte 7](#parte-7--todos-os-comandos) (`preparar_deploy`) e pelo README.

---

## Parte 2 — Dez palavras que resolvem tudo

Leia uma vez. Você não precisa decorar; volte aqui quando tropeçar.

**Terminal** — a janela preta onde se digitam comandos. No Windows usamos o
**PowerShell**. Abra pelo menu Iniciar digitando "PowerShell".

**Pasta atual** — o terminal está sempre "dentro" de uma pasta, e os comandos
valem dali. Se você digitar um comando na pasta errada, ele não encontra os
arquivos. `pwd` mostra onde você está.

**Python** — a linguagem do backend. O projeto exige a **versão 3.13**
especificamente (nem 3.12, nem 3.14).

**venv** (*virtual environment*, ambiente virtual) — uma pasta com uma cópia
isolada do Python e das bibliotecas do projeto. Existe para que o Coral Brasil
não brigue com outro projeto na mesma máquina. **Precisa ser "ativado" em cada
terminal novo** — esse é o esquecimento mais comum de todos.

**Node / npm** — o equivalente do Python e do pip para o frontend.

**Docker** — programa que roda outros programas em caixas isoladas
(*containers*). Usamos para os dois bancos, para que a versão do PostgreSQL
seja a mesma em qualquer máquina, sem instalador.

**Porta** — um número que identifica quem responde numa máquina. `3000` é o
site, `8000` é o backend, `5432` é o PostgreSQL, `7474`/`7687` são o Neo4j.
Dois programas não podem usar a mesma porta ao mesmo tempo.

**Migração (`migrate`)** — o comando que cria as tabelas no banco. O banco
**não vem no repositório**; toda máquina nova precisa rodar isso.

**Ingestão (`ingerir`)** — o comando que baixa os dados de satélite das fontes
externas (NOAA, Copernicus) e grava no PostgreSQL.

**Artefato derivado** — arquivo que o projeto **gera** e por isso não guarda no
Git: o modelo `.joblib`, os `.docx` da documentação, o grafo do Neo4j, os CSVs.
Todos são reconstruíveis por um comando. Se sumirem, não se perdeu nada —
basta regerar. É por isso que um clone novo do projeto precisa de vários passos
antes de funcionar.

---

## Parte 3 — Instalação passo a passo

> **Tempo estimado:** 40 a 90 minutos na primeira vez, quase tudo esperando
> download. Fazendo de novo numa segunda máquina: uns 15 minutos.

### Passo 0 — Abrir o terminal na pasta do projeto

Abra o **PowerShell** e vá até a pasta onde o projeto está. No caso desta
máquina:

▶
```bash
cd C:\Users\aissa\Documents\projeto-coral-brasil-main\projeto-coral-brasil
```

✅ **Deu certo se** o começo da linha passar a mostrar esse caminho.

Confirme que você está no lugar certo:

▶
```bash
ls
```

✅ Precisa aparecer `backend`, `frontend`, `docs`, `docker-compose.yml`,
`requirements.txt`. Se não aparecer, você está em outra pasta.

⚠️ **Todos os comandos deste manual são digitados nessa pasta**, a raiz do
projeto — exceto os do frontend, que avisam explicitamente para entrar em
`frontend`.

---

### Passo 1 — Instalar o Python 3.13

Confira se já existe:

▶
```bash
py -3.13 --version
```

✅ Precisa responder algo como `Python 3.13.14`.

❌ Se disser que não encontrou: baixe em
**https://www.python.org/downloads/release/python-3130/** (versão *Windows
installer 64-bit*). Na primeira tela do instalador, **marque a caixa "Add
python.exe to PATH"** antes de clicar em Install. Feche e reabra o PowerShell
depois de instalar.

⚠️ **Não use a versão mais nova.** O Django 5.1+ ainda não suporta o Python
3.14. Se você já tem o 3.14 instalado, tudo bem — o `py -3.13` escolhe a versão
certa, desde que a 3.13 também esteja lá.

---

### Passo 2 — Instalar o Node

▶
```bash
node --version
```

✅ Precisa responder `v18` ou mais alto (esta máquina usa `v24.15.0`).

❌ Se não encontrou: baixe a versão **LTS** em **https://nodejs.org/**, instale
com as opções padrão, feche e reabra o PowerShell.

---

### Passo 3 — Instalar o Docker Desktop

Este é o passo mais chato, e o único que pode pedir para reiniciar o
computador. Ele é necessário porque os dois bancos rodam dentro dele.

1. Baixe em **https://www.docker.com/products/docker-desktop/** →
   *Download for Windows*.
2. Rode o instalador deixando **"Use WSL 2 instead of Hyper-V"** marcado. Se
   ele avisar que falta o WSL, aceite instalar.
3. **Reinicie o computador quando ele pedir.** Não é opcional.
4. Abra o Docker Desktop e espere o ícone da baleia parar de se mexer. **Ele
   precisa ficar aberto** enquanto você usa o projeto — se você fechar, os
   bancos param.

▶
```bash
docker --version
```

✅ Precisa responder algo como `Docker version 29.6.2` (qualquer versão recente
serve).

❌ **"Virtualization support not detected"** — essa mensagem é enganosa e
**quase nunca** é a BIOS. O README tem o diagnóstico completo, na seção
*Setup → 3.1*, incluindo os dois comandos `dism.exe` que resolveram o problema
nesta máquina em 25/07/2026. Não mexa na BIOS antes de ler aquilo.

---

### Passo 4 — Criar o ambiente virtual (venv)

▶
```bash
py -3.13 -m venv venv
```

✅ Não imprime nada e demora uns 10 segundos. Depois, `ls` mostra uma pasta
nova chamada `venv`.

⚠️ Se a pasta `venv` já existir (é o caso desta máquina), **pule este passo**.
Criar de novo por cima não estraga nada, mas é tempo perdido.

---

### Passo 5 — Ativar o ambiente virtual

▶
```bash
.\venv\Scripts\activate
```

✅ **Deu certo se** aparecer `(venv)` no começo da linha do terminal, assim:

```
(venv) PS C:\Users\aissa\Documents\...\projeto-coral-brasil>
```

🚨 **Esse `(venv)` é a coisa mais importante deste manual.** Sem ele, todos os
comandos `python backend\manage.py ...` usam o Python errado, aquele que não
tem as bibliotecas do projeto — e o erro que aparece fala de um módulo faltando,
não do venv.

⚠️ **A ativação vale só para aquela janela de terminal.** Abriu outra? Ative de
novo. Fechou e abriu? Ative de novo. Isso não é defeito: é como o venv funciona.

❌ **"não pode ser carregado porque a execução de scripts foi desabilitada
neste sistema"** — o Windows bloqueia scripts por padrão. Libere só para o seu
usuário (não precisa ser administrador):

▶
```bash
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Responda `S` (ou `Y`) e tente ativar de novo.

---

### Passo 6 — Instalar as bibliotecas do backend

Com o `(venv)` aparecendo:

▶
```bash
pip install -r requirements.txt
```

✅ Demora de 2 a 10 minutos e termina com uma lista longa começando em
`Successfully installed`. Alguns avisos amarelos são normais.

❌ Se aparecerem erros de compilação mencionando `netCDF4` ou `numpy`,
confirme que o venv é mesmo do Python 3.13:

▶
```bash
python --version
```

---

### Passo 7 — Criar o arquivo de configuração

O projeto **não sobe sem** um arquivo `backend/.env`. Ele não é versionado (tem
senhas), então **toda máquina precisa criar o seu** — inclusive um clone novo
recém-baixado.

▶
```bash
copy backend\.env.example backend\.env
```

✅ **Não imprime nada** — no PowerShell, `copy` que deu certo é silencioso.
Para confirmar que o arquivo existe:

▶
```bash
ls backend\.env
```

Agora abra `backend/.env` num editor de texto (Bloco de Notas serve) e confira
**três linhas**. As três já vêm quase certas; o que muda é o valor.

**(a) O endereço do banco.** Procure a linha que começa com `DATABASE_URL=` e
deixe exatamente assim:

```
DATABASE_URL=postgres://coral:coral_dev_local@localhost:5432/coral_brasil
```

*(conteúdo de arquivo, não comando)*. Essa senha `coral_dev_local` precisa ser
a mesma do `docker-compose.yml` — e é o padrão dele, então não mexa nas duas
sem mexer nas duas.

⚠️ Se você trocar a senha, use **só letras, números e sublinhado**. Os
caracteres `@ : / #` têm significado dentro de uma URL, e o erro resultante não
diz que a culpa é da senha.

**(b) A senha do Neo4j.** Procure `NEO4J_PASSWORD=` e preencha:

```
NEO4J_PASSWORD=coral_dev_local
```

*(conteúdo de arquivo)*. No `.env.example` ela vem **vazia**, e vazia o grafo
não conecta.

**(c) 🚨 O modo manutenção.** Procure esta linha:

```
OFFLINE_MODE=True
```

Com ela em `True`, **o site abre mas todas as telas ficam vazias**, mostrando
uma tarja amarela de "modo manutenção". Não é defeito: é uma trava deliberada,
porque o site público está fora do ar durante a reestruturação.

Para ver o site com dados de verdade na sua máquina, troque para:

```
OFFLINE_MODE=False
```

*(conteúdo de arquivo)*. É de longe a causa número um de "instalei tudo e não
apareceu nada".

---

### Passo 8 — Subir os bancos de dados

Com o Docker Desktop **aberto**:

▶
```bash
docker compose up -d
```

✅ A primeira vez baixa algumas centenas de MB e demora minutos. As próximas
levam segundos. Termina com duas linhas dizendo `Started`.

Confira até os dois ficarem saudáveis:

▶
```bash
docker compose ps
```

✅ Precisa aparecer assim — repare no `(healthy)`:

```
NAME             IMAGE                STATUS
coral-postgres   postgres:17-alpine   Up 3 days (healthy)
coral-neo4j      neo4j:5-community    Up 17 hours (healthy)
```

⚠️ Enquanto disser `starting`, **ainda não aceita conexão**. O Postgres fica
pronto em segundos; o Neo4j leva uns 30. Rodar `migrate` cedo demais falha com
"conexão recusada" — espere.

Os comandos de Docker do dia a dia:

| Comando | O que faz |
|---|---|
| `docker compose up -d` | sobe os dois em segundo plano |
| `docker compose ps` | mostra estado e saúde |
| `docker compose stop` | para os dois, **sem apagar nada** |
| `docker compose logs neo4j` | mostra o log de um deles |
| `docker compose down` | remove os containers, **mantém os dados** |
| `docker compose down -v` | remove os containers **e apaga os dados** |

🚨 **`down -v` é o único da lista que destrói dados.** Ele apaga as 57 mil
medições, e recuperá-las significa horas de ingestão de novo. Não use sem
motivo.

---

### Passo 9 — Criar as tabelas

Antes, confirme para onde o Django está apontando:

▶
```bash
python backend\manage.py shell -c "from django.conf import settings as s; print(s.DATABASES['default']['ENGINE'])"
```

✅ Precisa dizer `django.db.backends.postgresql`.

❌ Se disser `sqlite3`, a `DATABASE_URL` do passo 7 não foi lida: confira se o
arquivo se chama `backend/.env` (e não `backend/.env.txt`, que o Bloco de Notas
gosta de criar) e se a linha não está comentada com `#`.

Agora crie as tabelas:

▶
```bash
python backend\manage.py migrate
```

✅ Imprime uma lista de `Applying ...` terminando em `OK`.

⚠️ **Rode `migrate` toda vez que puxar código novo do Git**, mesmo que o
projeto já funcionasse ali. O banco não viaja no repositório, e as tabelas
mudam junto com o código.

---

### Passo 10 — Criar seu usuário de administrador

▶
```bash
python backend\manage.py createsuperuser
```

Ele pergunta usuário, e-mail (pode deixar vazio) e senha **duas vezes**. A
senha não aparece enquanto você digita — nem asteriscos. Isso é normal.

✅ Termina com `Superuser created successfully.`

Esse usuário serve para entrar em `http://localhost:8000/admin/`, o painel onde
se cadastram recifes, espécies e fotos.

---

### Passo 11 — Colocar dados no banco

Você acabou de criar tabelas **vazias**. Há dois caminhos.

#### Caminho A — baixar das fontes (o normal)

Antes de tudo, teste o que a sua rede alcança:

▶
```bash
python backend\manage.py testar_fontes
```

✅ Não grava nada. Lista cada espelho de dados, diz quais das 5 variáveis cada
um publica e recomenda qual usar.

🔒 **Os servidores da própria NOAA só respondem de dentro de uma rede com
domínio federal** — no caso deste projeto, a UFF. O espelho padrão (PACIOOS, da
Universidade do Havaí) redistribui exatamente o mesmo produto e **funciona de
qualquer rede**, então normalmente não há o que configurar.

Agora a coleta. Comece pequeno, para ver funcionar:

▶
```bash
python backend\manage.py ingerir --desde=2026-07-01
```

✅ Imprime uma linha por fonte e local, assim:

```
[ok]  noaa_crw/abrolhos-ba: 115 medicoes
```

Depois, a série completa (**demora bastante** — dezenas de minutos):

▶
```bash
python backend\manage.py ingerir --completo --desde=2020-01-01
```

Três coisas que tiram o medo desse comando:

- Ele **fatia o período em blocos** de 180 dias e grava cada bloco assim que
  chega. Interromper no meio (Ctrl+C) preserva o que já veio.
- Rodar de novo **sem** `--completo` retoma de onde parou.
- Rodar duas vezes o mesmo período **não duplica nada**.

Para os dados do Copernicus (salinidade e oxigênio) é preciso uma conta
gratuita em **https://data.marine.copernicus.eu/register**, e depois:

▶
```bash
copernicusmarine login
```

Ele **pergunta** usuário e senha e guarda fora do projeto. Use o *username* do
cadastro, não o e-mail. ⚠️ Não passe usuário e senha na mesma linha do comando:
isso deixa a senha guardada no histórico do terminal.

#### Caminho B — copiar de outra máquina

Se outro computador já tem os dados, exporte lá:

▶
```bash
$env:PYTHONUTF8='1'; python backend\manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.Permission --exclude admin.logentry --exclude sessions.session --indent 1 -o backend\dados_sqlite.json
```

⚠️ O `PYTHONUTF8='1'` **não é opcional no Windows**: sem ele o comando quebra
ao chegar na unidade `mmol·m⁻³` do oxigênio, com um erro que fala de `charmap`
e não menciona o motivo real.

Copie o arquivo para a outra máquina e importe:

▶
```bash
$env:PYTHONUTF8='1'; python backend\manage.py loaddata backend\dados_sqlite.json
```

#### Conferindo o que entrou

▶
```bash
python backend\manage.py shell -c "from aquaculture.models import MedicaoAmbiental as M; print(M.objects.count(), 'medicoes')"
```

✅ Nesta máquina, em 29/07/2026, responde **57426 medicoes**, cobrindo
01/01/2020 a 27/07/2026, em 3 recifes: `abrolhos-ba`, `porto-de-galinhas-pe` e
`picaozinho-pb`.

---

### Passo 12 — Gerar o arquivo do modelo

O modelo **não vem no repositório** — é artefato derivado. Sem este passo o
painel de risco responde erro 503 nos três recifes.

▶
```bash
python backend\manage.py treinar_final
```

✅ Demora alguns segundos e grava dois arquivos em `dados/modelos/`:
`entrega1_baa.joblib` (o modelo) e `entrega1_baa.json` (a ficha dele).

⚠️ **Este comando não diz se o modelo é bom, de propósito.** Ele treina usando
*todos* os dados; qualquer nota calculada aí mediria memória, não previsão.
Quem mede é o outro comando:

▶
```bash
python backend\manage.py treinar_modelo
```

Esse sim avalia honestamente (esconde um ano inteiro, treina no resto, testa no
ano escondido, repete). Ele **não grava nada** — só mede.

Para ver a ficha do modelo que está gravado:

▶
```bash
python backend\manage.py treinar_final --listar
```

---

### Passo 13 — Construir o grafo (opcional)

O Neo4j é uma **cópia derivada** do PostgreSQL, em forma de rede. O site
funciona sem ele; só a página do grafo fica indisponível.

▶
```bash
python backend\manage.py neo4j_projetar
```

✅ Reconstrói do zero — cerca de 172 mil elementos em ~16 segundos — e
**confere item a item** contra o PostgreSQL no fim.

Se algum dia o grafo divergir ou for perdido, rode de novo. Não existe dado que
só exista lá.

---

## Parte 4 — Rodar o site

Instalação feita. Daqui em diante, é isso que você repete.

Você vai precisar de **duas janelas de terminal abertas ao mesmo tempo** — uma
para o backend, outra para o frontend. Elas ficam ocupadas enquanto o site
roda; isso é normal, não travou.

### Terminal 1 — o backend

▶
```bash
cd C:\Users\aissa\Documents\projeto-coral-brasil-main\projeto-coral-brasil
```

▶
```bash
.\venv\Scripts\activate
```

▶
```bash
python backend\manage.py runserver
```

✅ Termina com:

```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

Teste no navegador: **http://localhost:8000/api/status/** deve mostrar

```json
{"offline_mode": false, "message": "Servico online."}
```

Se disser `"offline_mode": true`, volte ao [passo 7c](#passo-7--criar-o-arquivo-de-configuração).

⚠️ **Deixe essa janela aberta.** Fechar derruba o backend. Para parar de
propósito: `Ctrl+C`.

### Terminal 2 — o frontend

Abra **outra** janela do PowerShell:

▶
```bash
cd C:\Users\aissa\Documents\projeto-coral-brasil-main\projeto-coral-brasil\frontend
```

Só na primeira vez (demora, baixa centenas de MB):

▶
```bash
npm install
```

E então:

▶
```bash
npm start
```

✅ Depois de uns 30 segundos ele **abre o navegador sozinho** em
`http://localhost:3000` e o terminal mostra `Compiled successfully!`.

⚠️ O frontend **não** precisa do venv ativado — ele não usa Python. Mas
**precisa que o backend esteja rodando na porta 8000**, porque é para lá que
ele encaminha tudo que começa com `/api/`. Backend parado = site aberto, telas
vazias.

### Para desligar tudo

1. Em cada terminal, `Ctrl+C`.
2. Se quiser liberar a memória dos bancos: `docker compose stop` (não apaga
   nada; `docker compose up -d` traz de volta).

---

## Parte 5 — O que você deve ver

| Endereço | O que é | O que aparece |
|---|---|---|
| http://localhost:3000 | **o site** | Página inicial do Coral Brasil |
| http://localhost:3000/recifes | lista de recifes | 3 cartões, cada um com selo de alerta |
| http://localhost:8000/admin/ | **painel administrativo** | Login; entre com o usuário do passo 10 |
| http://localhost:8000/api/status/ | saúde do backend | `{"offline_mode": false, ...}` |
| http://localhost:8000/api/painel-risco/ | **a previsão** | modelo + um item por recife |
| http://localhost:8000/api/locais/ | os recifes | lista com nome, estado, cidade |
| http://localhost:8000/api/datasets/ | catálogo de dados | 9 datasets com cobertura |
| http://localhost:7474 | Neo4j Browser | interface do grafo (usuário `neo4j`) |

### Lendo a resposta do painel de risco

É o único endereço do projeto que **faz conta** em vez de devolver linha
guardada. A resposta tem duas partes: um bloco `modelo`, dizendo o que a
probabilidade significa, e uma lista com um item por recife.

Um recife disponível vem assim (valores reais desta máquina, calculados sobre a
série até 24/07/2026):

```json
{
  "local": "abrolhos-ba",
  "disponivel": true,
  "data_base": "2026-07-24",
  "data_alvo": "2026-07-31",
  "dias_de_atraso": 5,
  "probabilidade": 0.0029,
  "limiar": 0.1,
  "alerta": false,
  "no_extremo": false
}
```

Em português: *"com base na série até 24/07, a chance de estresse térmico em
31/07 é de 0,3%; abaixo do limiar de 10%, então não há alerta; o dado mais
recente tem 5 dias de atraso."*

⚠️ **Dois recifes podem sair com a probabilidade idêntica** — nesse mesmo dia,
os três deram `0,0029` apesar de entradas bem diferentes. Isso não é bug: a
recalibração é uma função escada com 313 degraus, e entradas distintas caem no
mesmo degrau. A resposta avisa disso no campo `probabilidade_em_degraus`.

🚨 **Nunca escreva "0%" nem "100%" na tela.** O modelo é recalibrado por uma
função escada, que devolve `0,000` e `1,000` exatos por construção — 12,2% das
amostras de treino caem em zero exato. Isso significa *"nenhum alerta neste
degrau"*, e **não** *"impossível"*. Quando isso acontece, a resposta traz
`"no_extremo": true` justamente para avisar.

Um recife **indisponível** vem assim, e isso é estado normal:

```json
{
  "local": "abrolhos-ba",
  "disponivel": false,
  "motivo": "A janela do modelo nao fecha em 2026-07-27 ...",
  "faltando": [{"variavel": "dhw", "data": "2026-07-27"}]
}
```

O modelo precisa de 7 dias seguidos de quatro variáveis. Se falta um dia, ele
**recusa em vez de preencher com zero** — porque zero é um valor legítimo de
variação, e preencher diria "nada mudou" exatamente onde o dado sumiu.

⚠️ **Isso acontece com frequência por um motivo previsível:** as duas fontes
publicam com atrasos diferentes. Em 29/07/2026 o Copernicus (salinidade,
oxigênio) já tinha dados até 27/07, e a NOAA (SST, DHW) só até 24/07. Como a
data-base é sempre **a última data da série**, os três dias em que só o
Copernicus publicou deixam o painel indisponível até a NOAA alcançar. A saída é
rodar a ingestão de novo mais tarde — a NOAA publica com 1 a 3 dias de atraso.

---

## Parte 6 — A rotina do dia a dia

### Já instalado, quero só abrir o site

Três coisas, nesta ordem:

1. Abrir o **Docker Desktop** e esperar a baleia estabilizar.
2. Terminal 1: `cd` na pasta → `.\venv\Scripts\activate` →
   `python backend\manage.py runserver`
3. Terminal 2: `cd frontend` → `npm start`

### Manter os dados frescos

Depois de instalado, **nada roda sozinho**. Sem isso a série congela no dia da
instalação e o painel passa a prever a partir de dado velho — declarando o
atraso, mas velho.

Um comando por dia resolve:

▶
```bash
python backend\manage.py atualizar
```

Ele ingere só o que falta, reprojeta o grafo e avisa o que envelheceu. É
idempotente: rodar duas vezes no mesmo dia não duplica nada. **Em dia normal
ele não diz nada** — rotina que fala todo dia ensina quem lê a ignorar.

🚨 **Ele não retreina o modelo, e isso é decisão, não esquecimento.** Um modelo
que muda toda noite é um modelo que ninguém mediu: `treinar_final` grava sem
avaliar, de propósito. Encadeá-lo num agendador trocaria, todo dia, um modelo
medido por um não medido. Então o modelo envelhece — e depois de 90 dias a
rotina **avisa**, deixando claro que não é erro.

### Deixando automático

O comando aceita `--silencioso`, que só imprime quando há algo a dizer. No
Windows, pelo Agendador de Tarefas, para rodar às 6h:

▶
```bash
schtasks /create /tn "coral-brasil-atualizar" /tr "C:\caminho\venv\Scripts\python.exe C:\caminho\backend\manage.py atualizar --silencioso" /sc daily /st 06:00
```

Troque `C:\caminho` pelo caminho real do projeto nas duas ocorrências.

---

## Parte 7 — Todos os comandos

Todos são digitados na raiz do projeto, com o `(venv)` ativado, no formato
`python backend\manage.py NOME`.

### Rodar e conferir

| Comando | O que faz |
|---|---|
| `runserver` | liga o backend na porta 8000 |
| `migrate` | cria/atualiza as tabelas do banco |
| `createsuperuser` | cria um usuário do painel administrativo |
| `conferir_persistencia` | confere índices, constraints e o tempo das consultas, contra o banco real |

🚨 **Os testes são a exceção da regra "rode da raiz".** O `manage.py test`
procura os testes **a partir da pasta onde você está**, então da raiz ele
encontra zero — e, pior, **não reclama**: imprime `NO TESTS RAN` e sai com
sucesso, o que passa facilmente por "tudo passou". Entre na pasta primeiro:

▶
```bash
cd backend
```

▶
```bash
python manage.py test
```

✅ São **527 testes**, em cerca de 90 segundos, terminando em `OK (skipped=1)`.
Depois, `cd ..` para voltar à raiz.

### Dados

| Comando | O que faz |
|---|---|
| `testar_fontes` | testa quais fontes respondem desta rede — **não grava nada** |
| `testar_fontes --ssl` | diagnostica erro de certificado |
| `ingerir` | baixa dados novos das fontes externas |
| `ingerir --completo --desde=2020-01-01` | rebaixa o período inteiro |
| `ingerir_gcbd` | baixa a janela ambiental da base de branqueamento observado |
| `inventariar_datasets` | reconstrói o catálogo público a partir dos arquivos em disco |

### Modelo

| Comando | O que faz |
|---|---|
| `treinar_modelo` | **mede** se o modelo presta (leave-year-out). Não grava |
| `treinar_final` | **grava** o modelo que o painel usa. Não mede |
| `treinar_final --listar` | mostra a ficha do modelo gravado |
| `calibrar` | confere se a probabilidade exibida é honesta |
| `limiar` | mede a troca entre alarme falso e evento perdido, por limiar |
| `treinar_gcbd` | a segunda entrega — prevê branqueamento observado, a partir de CSV |

🚨 **`treinar_modelo` e `treinar_final` têm propósitos opostos.** Um mede sem
gravar, o outro grava sem medir. Trocá-los é a confusão mais cara do projeto:
publicar o resultado do primeiro seria publicar um modelo que não existe em
disco; confiar num número do segundo seria confiar em memória, não em previsão.

### Grafo, documentação e publicação

| Comando | O que faz |
|---|---|
| `neo4j_init` | cria o schema do grafo |
| `neo4j_projetar` | reconstrói o grafo do zero a partir do PostgreSQL, e confere |
| `neo4j_projetar --conferir` | só confere, sem escrever |
| `exportar_docs` | gera uma cópia `.docx` de cada documento em `docs/exportado/` |
| `preparar_deploy` | **antes de publicar**: reconstrói modelo, grafo e docs, e confere |
| `atualizar` | a rotina diária: ingere, reprojeta, relata o envelhecimento |

Sobre o `preparar_deploy`: ele existe porque **nada do que é derivado viaja no
`git push`**. Sem ele, um clone novo seguido de publicação sobe um site sem
modelo — `/api/painel-risco/` responde 503 nos três recifes e o grafo vem
vazio, e nenhum item de checklist falha por isso. Ele para no primeiro erro, de
propósito: um site meio construído é pior do que um que não sobe, porque parece
ter funcionado.

### Frontend (dentro de `frontend/`)

| Comando | O que faz |
|---|---|
| `npm install` | instala as bibliotecas (só na primeira vez) |
| `npm start` | liga o site em desenvolvimento, na porta 3000 |
| `npm test` | roda os 71 testes do frontend |
| `npm run build` | gera a versão otimizada para publicar |

---

## Parte 8 — Quando algo dá errado

### Roteiro de 30 segundos

Antes de investigar qualquer erro, confira estes quatro na ordem:

1. O **Docker Desktop está aberto**? (`docker compose ps` mostra `healthy`?)
2. O terminal mostra **`(venv)`** no começo da linha?
3. Você está **na pasta certa**? (`ls` mostra `backend` e `frontend`?)
4. O **backend está rodando** noutra janela, na porta 8000?

Quatro entre cinco problemas são um desses.

### Por sintoma

| O que você vê | O que é | Como resolver |
|---|---|---|
| `ModuleNotFoundError: No module named 'django'` | venv não ativado | `.\venv\Scripts\activate` |
| `... não pode ser carregado porque a execução de scripts foi desabilitada` | política do PowerShell | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| `connection refused` / `could not connect to server` | bancos não subiram | Docker Desktop aberto? `docker compose up -d`, espere `healthy` |
| `django.db.utils.OperationalError: password authentication failed` | senha do `.env` ≠ senha do compose | as duas precisam ser a mesma |
| O site abre com tarja amarela e telas vazias | `OFFLINE_MODE=True` | troque para `False` em `backend/.env` e reinicie o backend |
| Site abre, mas nenhum dado carrega | backend parado | ligue o `runserver` na porta 8000 |
| `Something is already running on port 3000` | outra instância aberta | feche o outro terminal, ou responda `Y` para usar outra porta |
| `Error: That port is already in use` (8000) | backend já rodando | use o que já está, ou `runserver 8001` |
| Painel diz **503, modelo indisponível** | falta o `.joblib` | `python backend\manage.py treinar_final` |
| Painel diz **`disponivel: false`** nos três | janela não fecha | normal quando a NOAA está atrasada; rode `atualizar` mais tarde |
| Painel responde **404** para um recife | modelo não treinou nesse local | o modelo viu 3 recifes; um quarto seria extrapolação |
| `relation "aquaculture_..." does not exist` | tabelas não criadas | `python backend\manage.py migrate` |
| `no such table` mencionando SQLite | `DATABASE_URL` não foi lida | confira `backend/.env` (nome do arquivo e `#` na linha) |
| Página do grafo vazia / erro 503 no grafo | Neo4j sem dados ou parado | `docker compose ps`, depois `neo4j_projetar` |
| `UnicodeEncodeError` num comando | acentuação no console do Windows | rode com `$env:PYTHONUTF8='1';` na frente |
| `CERTIFICATE_VERIFY_FAILED` na ingestão | cadeia de certificados incompleta **nesta máquina** | `python backend\manage.py testar_fontes --ssl` — a tabela do README diz o que fazer |
| `HTTP 503` do ERDDAP | servidor sobrecarregado | espere alguns minutos e repita; a ingestão é idempotente |
| `WinError 10060` / timeout na NOAA | você não está numa rede federal | use o espelho PACIOOS (é o padrão — não configure nada) |
| Ingestão termina com **0 medições** e explicação | a fonte ainda não publicou | não é falha; satélite sai com 1–3 dias de atraso |

🚨 **Nunca desligue a verificação de certificado** para fazer um erro de SSL
sumir. Aceitar qualquer certificado aceita também o de quem estiver no meio do
caminho — e num projeto que declara a proveniência de cada valor, isso
invalidaria a cadeia de custódia que todo o resto do pipeline mantém.

---

## Parte 9 — Perguntas frequentes

**Preciso de internet?**
Para instalar, sim. Para *rodar* com os dados já baixados, não. Só a ingestão
(`ingerir`, `atualizar`) usa a rede.

**Apaguei a pasta `dados/modelos`. Perdi alguma coisa?**
Não. Rode `treinar_final` e ela volta. Vale o mesmo para `docs/exportado`
(`exportar_docs`), o grafo do Neo4j (`neo4j_projetar`) e os CSVs em
`backend/dados` (`ingerir`). Tudo isso é derivado.

**E se eu apagar o banco?**
Aí sim há trabalho: `docker compose down -v` apaga as 57 mil medições, e
recuperá-las significa rodar a ingestão completa de novo — dezenas de minutos e
dependente das fontes estarem no ar. É o único comando deste manual que destrói
algo caro.

**Dá para rodar sem Docker?**
Tecnicamente sim: sem `DATABASE_URL` o Django cai num arquivo SQLite local, e
os testes passam assim. Mas **não é o banco do projeto**: com duas máquinas,
dois arquivos SQLite divergem em silêncio e não há como saber qual está certo.
Use SQLite só para rodar teste rápido.

**Os dados são os mesmos nos meus dois computadores?**
Não. O Docker iguala *versão e configuração*, não conteúdo — cada máquina tem
seu próprio volume. Para os dados serem os mesmos seria preciso um banco
hospedado e uma única `DATABASE_URL`. Enquanto isso não existir: ingira sempre
na mesma máquina, ou mova com `dumpdata`/`loaddata` ([passo 11B](#caminho-b--copiar-de-outra-máquina)).

**Por que o site diz que está em manutenção?**
Porque `OFFLINE_MODE=True`, que é o padrão do `.env.example`. É deliberado — o
site público está fora do ar durante a reestruturação.

**Posso editar os `.docx` em `docs/exportado`?**
Pode, mas não adianta: eles são regerados por `exportar_docs` e sua edição
some. **Edite sempre o Markdown**, que é a única fonte.

**Quanto tempo demora a ingestão completa?**
De 2020 até hoje, dezenas de minutos, dependendo da rede e do humor dos
servidores. Pode ser interrompida e retomada sem perda.

**O modelo precisa ser retreinado?**
Não automaticamente — e a rotina diária deliberadamente não faz isso. Depois de
90 dias sem retreino, `atualizar` avisa. Aí a sequência é: `treinar_modelo`
(mede) e, se o resultado convencer, `treinar_final` (grava).

---

## Parte 10 — Checklist para copiar

**Instalação, do zero:**

```
[ ] Python 3.13 instalado          py -3.13 --version
[ ] Node 18+ instalado             node --version
[ ] Docker Desktop instalado       docker --version
[ ] venv criado                    py -3.13 -m venv venv
[ ] venv ativado                   .\venv\Scripts\activate      -> aparece (venv)
[ ] dependências                   pip install -r requirements.txt
[ ] backend/.env criado            copy backend\.env.example backend\.env
[ ]   DATABASE_URL preenchida
[ ]   NEO4J_PASSWORD preenchida
[ ]   OFFLINE_MODE=False
[ ] bancos no ar                   docker compose up -d         -> ps mostra healthy
[ ] tabelas criadas                python backend\manage.py migrate
[ ] usuário admin                  python backend\manage.py createsuperuser
[ ] dados no banco                 python backend\manage.py ingerir --completo --desde=2020-01-01
[ ] modelo gravado                 python backend\manage.py treinar_final
[ ] grafo projetado                python backend\manage.py neo4j_projetar
```

**Todo dia que for usar:**

```
[ ] Docker Desktop aberto
[ ] Terminal 1: activate -> python backend\manage.py runserver
[ ] Terminal 2: cd frontend -> npm start
[ ] http://localhost:3000 abre
```

---

## Glossário

**Artefato derivado** — arquivo gerado pelo projeto, não guardado no Git, e
reconstruível por um comando: o modelo `.joblib`, os `.docx`, o grafo, os CSVs.

**BAA** (*Bleaching Alert Area*) — a escala oficial de alerta de branqueamento
da NOAA, de 0 a 4. É o que o modelo tenta prever com 7 dias de antecedência.

**Backend** — a parte que não aparece: banco, regras, contas. Aqui, Django.

**Container** — programa rodando dentro de uma caixa isolada do Docker.

**DHW** (*Degree Heating Weeks*) — quanto calor acumulado o recife levou nas
últimas 12 semanas. A medida-chave de estresse térmico.

**Endpoint** — um endereço da API que responde a uma pergunta específica, como
`/api/painel-risco/`.

**Frontend** — a parte que aparece: as telas. Aqui, React.

**Idempotente** — rodar duas vezes dá o mesmo resultado que rodar uma. Vale
para `ingerir` e `atualizar`.

**Ingestão** — o processo de buscar dados nas fontes externas e gravar no banco
com a proveniência de cada valor.

**Limiar** — o número a partir do qual a probabilidade vira alerta. Aqui é
**0,10**, escolhido em 27/07/2026 priorizando antecedência do aviso.

**Migração** — mudança na estrutura do banco, aplicada por `migrate`.

**Painel de risco** — o único endpoint que calcula em vez de servir dado
guardado.

**Proveniência** — de onde cada valor veio: qual fonte, qual dataset, qual dia.
O projeto grava isso valor a valor.

**venv** — ambiente virtual do Python; precisa ser ativado em cada terminal.

---

## Onde ler mais

| Se você quer saber… | Leia |
|---|---|
| o que é branqueamento e por que este projeto existe | [VISAO_GERAL.md](VISAO_GERAL.md) |
| como o modelo funciona, sem jargão | [METODOLOGIA_SIMPLES.md](METODOLOGIA_SIMPLES.md) |
| como o software funciona, sem jargão | [SISTEMA_SIMPLES.md](SISTEMA_SIMPLES.md) |
| de onde vem cada dado, com licença e citação | [FONTES.md](FONTES.md) |
| o que o experimento mediu | [RESULTADOS.md](RESULTADOS.md) |
| por que há dois bancos | [arquitetura.md](arquitetura.md) |
| o que ainda falta no projeto | [PLANEJAMENTO.md](../PLANEJAMENTO.md) |

---

*Manual escrito em 29/07/2026. Os números citados (57.426 medições, série até
27/07/2026, modelo treinado em 28/07/2026) descrevem o estado desta máquina
naquele dia e envelhecem — os comandos, não.*
