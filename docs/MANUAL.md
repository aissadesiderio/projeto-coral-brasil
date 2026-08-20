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

Abra o **PowerShell** e vá até a pasta onde o projeto está.

⚠️ **O caminho muda de máquina para máquina** — depende de onde você clonou.
Nas duas em uso hoje:

```bash
cd C:\Users\aissa\Documents\projeto-coral-brasil-main\projeto-coral-brasil
```

```bash
cd C:\Users\Aissa\Documents\GitHub\projeto-coral-brasil
```

Não sabe qual é o seu? Abra a pasta no Explorador de Arquivos, clique na barra
de endereço, copie, e cole depois do `cd `.

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

Com ela em `True`, o site abre, mostra uma tarja amarela de "modo manutenção" —
e **some com a previsão de risco**. Não é defeito: é uma trava deliberada,
porque o site público está fora do ar durante a reestruturação.

⚠️ **O site não fica todo vazio, e é isso que engana.** Os recifes e as
espécies continuam aparecendo, porque vêm de uma cópia local
(`frontend/src/data/recifeData.js`) que não depende da API. O que some é o que
precisa de conta na hora:

| O que | O que aparece no lugar |
|---|---|
| **Painel de predição de risco** | 🚨 **nada** — o bloco simplesmente não é desenhado, sem mensagem nenhuma |
| Gráficos da série ambiental | a frase "A serie nao e exibida em modo manutencao" |
| Recifes e espécies | continuam normais, da cópia local |

Ou seja: quem procura a previsão de estresse térmico e não a encontra **não
recebe nenhuma explicação na tela** — só a tarja amarela no topo, que é fácil
de ler como aviso genérico. Se a página do recife carregou com espécies e você
não acha o painel de risco em lugar nenhum, é esta linha.

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

A primeira vez baixa algumas centenas de MB e demora minutos. As próximas levam
segundos. Termina com duas linhas dizendo `Started`.

🚨 **`Started` não quer dizer que subiu — quer dizer que o Docker *mandou*
subir.** Um container que morre logo em seguida e reinicia em laço também
imprime `Started`, toda vez. A única prova é o comando abaixo:

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

❌ Se disser **`Restarting (1)`**, com a coluna PORTS **vazia**, o container
está morrendo e nascendo em laço. Rodar `up -d` de novo não resolve: ele
reinicia o mesmo laço. A causa aparece só no log — veja
[o container que reinicia sem parar](#o-container-que-reinicia-sem-parar).

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

Antes, confirme para onde o Django está apontando. Abra o console:

▶
```bash
python backend\manage.py shell
```

E no prompt `>>>`, uma linha por vez:

▶
```bash
from django.conf import settings as s
```

▶
```bash
s.DATABASES['default']['ENGINE']
```

▶
```bash
s.DATABASES['default']['NAME']
```

Saia com `exit()`.

✅ O primeiro precisa dizer `'django.db.backends.postgresql'`; o segundo,
`'coral_brasil'` — **sem espaço antes da aspa final**.

⚠️ Peça os dois campos separadamente, e não o dicionário inteiro: ele contém a
senha do banco, e senha impressa na tela é senha que aparece no próximo print.

❌ Se o `ENGINE` disser `sqlite3`, a `DATABASE_URL` do passo 7 não foi lida:
confira se o arquivo se chama `backend/.env` (e não `backend/.env.txt`, que o
Bloco de Notas gosta de criar) e se a linha não está comentada com `#`.

❌ Se o `NAME` sair `'coral_brasil '`, com espaço, vá direto para
[o espaço invisível no `.env`](#-o-espaço-invisível-no-env) — o `migrate` vai
falhar dizendo que o banco não existe.

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

🆕 **Desde 08/08/2026, é também o usuário "master" do próprio site** — a
mesma conta e a mesma senha logam em `http://localhost:3000/login`, e lá ela
aprova conta de visitante e edita espécie na hora, sem passar por moderação.
Não existe cadastro separado para isso: quem é superusuário aqui já é master
lá.

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

Se outro computador já tem os dados, exporte lá. Primeiro:

▶
```bash
$env:PYTHONUTF8='1'
```

⚠️ Esta linha **não é opcional no Windows**: sem ela o comando seguinte quebra
ao chegar na unidade `mmol·m⁻³` do oxigênio, com um erro que fala de `charmap`
e não menciona o motivo real. Ela vale só para esta janela de terminal.

Depois:

▶
```bash
python backend\manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.Permission --exclude admin.logentry --exclude sessions.session --indent 1 -o backend\dados_sqlite.json
```

⚠️ **Este é o comando mais longo do manual, e precisa cair no terminal como uma
linha só.** Se a colagem trouxer uma quebra, ele falha reclamando de um
argumento — não do que realmente aconteceu. Se não conseguir colar inteiro,
salve a linha num arquivo `exportar.ps1` na raiz do projeto e rode
`.\exportar.ps1`.

Copie o arquivo para a outra máquina e importe:

▶
```bash
$env:PYTHONUTF8='1'; python backend\manage.py loaddata backend\dados_sqlite.json
```

#### Conferindo o que entrou

Abra o console do Django:

▶
```bash
python backend\manage.py shell
```

No prompt `>>>` que aparecer, uma linha por vez:

▶
```bash
from aquaculture.models import MedicaoAmbiental as M
```

▶
```bash
M.objects.count()
```

Para sair: `exit()`.

✅ Nesta máquina, em 29/07/2026, responde **57426**, cobrindo 01/01/2020 a
27/07/2026, em 3 recifes: `abrolhos-ba`, `porto-de-galinhas-pe` e
`picaozinho-pb`.

⚠️ **Num computador novo, espere `0`** — e isso está certo. Cada máquina tem seu
próprio volume do Postgres; os dados do outro computador não vieram no `git
pull`. É para isso que existem os dois caminhos acima.

⚠️ **Por que em duas etapas, e não num comando só?** Existe a forma curta,
`manage.py shell -c "..."`, mas ela é uma linha muito longa — e uma linha longa
copiada de um terminal costuma trazer uma **quebra invisível** junto. Colada, o
PowerShell mostra `>>` e o Python reclama de sintaxe. Ver
[Parte 8](#o-prompt--que-não-sai).

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

*(o caminho é o da sua máquina — veja o [passo 0](#passo-0--abrir-o-terminal-na-pasta-do-projeto))*

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

*(de novo: o caminho da sua máquina, com `\frontend` no fim)*

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
| http://localhost:8000/api/medicoes/ | **a série medida** | as 57.426 medições, paginadas, com a proveniência de cada valor |
| http://localhost:8000/api/locais/ | os recifes | lista com nome, estado, cidade |
| http://localhost:8000/api/datasets/ | catálogo de dados | 9 datasets com cobertura |
| http://localhost:7474 | Neo4j Browser | interface do grafo (usuário `neo4j`) |

⚠️ **Previsão e medição são duas coisas.** `painel-risco` fala do **futuro** e
sai do modelo; `medicoes` fala do **passado** e sai do satélite. A página de
cada recife mostra as duas, uma abaixo da outra, e diz por extenso qual é qual.

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
  "dias_de_atraso": 7,
  "limitado_por": ["dhw", "sst"],
  "probabilidade": 0.0029,
  "limiar": 0.2,
  "alerta": false,
  "nivel": {
    "slug": "sem_aviso",
    "rotulo": "Sem aviso",
    "corte": 0.0,
    "acao": "Nada a fazer.",
    "exige_acao": false
  },
  "no_extremo": false
}
```

Em português: *"com base na série até 24/07, a chance de estresse térmico em
31/07 é de 0,3%; o degrau da escala é **Sem aviso**, e a ação esperada é
nenhuma; o dado mais recente tem 7 dias de atraso, e quem segura essa data são
o DHW e a SST."*

📌 **`nivel` é o campo que a tela deve exibir, e não `alerta`.** Desde
30/07/2026 o aviso tem **quatro degraus** em vez de um liga-desliga, e cada um
traz a **ação esperada** junto. `alerta` continua na resposta por
compatibilidade e corresponde a "chegou no degrau `Alerta` ou acima".

📌 **`limitado_por`** diz quais variáveis seguram a `data_base` — explicado
logo abaixo, em *"`dias_de_atraso` e `limitado_por`"*.

### O painel na tela: o degrau, a ação e a escala

Desde 31/07/2026 o painel de cada recife mostra três coisas, e não uma:

| O quê | Exemplo |
|---|---|
| **O degrau de hoje** | *Sem aviso* — com a cor e o ícone daquele degrau |
| **O que fazer** | *"Nada a fazer."* |
| **A escala inteira**, com o degrau de hoje marcado | os quatro, com o corte e a ação de cada um |

🚨 **A ação é o motivo de a escala existir.** Até 31/07 o painel recebia esse
campo do servidor e **descartava**: mostrava o rótulo, escolhia a cor e jogava
fora a instrução. Um selo colorido sem instrução devolve ao leitor a decisão que
o projeto já tinha tomado por ele — e aí quatro degraus não valem mais que um
liga-desliga.

⚠️ **A escala inteira aparece para dar régua ao degrau de hoje.** *"Observação"*
sozinho não diz se é o primeiro ou o último aviso da escala; ao lado dos outros
três, diz. Quem lê um degrau intermediário precisa saber se o projeto ainda tem
algo pior a dizer.

📌 **O ícone segue `exige_acao`, não o antigo liga-desliga.** *Observação* não
exige ação, mas também não é *Sem aviso* — com o binário anterior ela recebia o
mesmo escudo verde de um recife tranquilo, apagando na tela o degrau que o
servidor tinha acabado de calcular.

Na **lista de recifes**, o selo de cada cartão traz o nome do degrau, e a
distinção que muda a leitura da lista: degrau que exige ação vem **preenchido**;
os outros, só contornados. A instrução inteira fica no painel, a um clique.

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

O modelo precisa de 7 dias seguidos de quatro variáveis. Se falta um dia **no
meio** da janela, ele recusa em vez de preencher com zero — porque zero é um
valor legítimo de variação, e preencher diria "nada mudou" exatamente onde o
dado sumiu.

### `dias_de_atraso` e `limitado_por`

As duas fontes publicam com atrasos diferentes: a NOAA (SST, DHW) sai com 1 a 3
dias de defasagem, e o Copernicus (salinidade, oxigênio) vai até ontem. A série
por isso nunca termina reta.

O painel responde na **última data em que todas as quatro variáveis existem**, e
diz duas coisas sobre ela:

| Campo | O que significa |
|---|---|
| `dias_de_atraso` | há quantos dias é o dado usado |
| `limitado_por` | **quais variáveis** estão segurando essa data |

Um `limitado_por: ["dhw", "sst"]` com atraso de 2 ou 3 dias é o dia a dia
normal — é a NOAA publicando no ritmo dela. O mesmo campo com atraso de duas
semanas quer dizer outra coisa: aquele conector parou, e é hora de rodar
`testar_fontes`.

⚠️ **Até 30/07/2026 essa situação deixava o painel indisponível**, porque a
data-base caía na ponta da fonte mais adiantada e a janela nunca fechava. Se
você vir capturas de tela antigas com "Dados insuficientes" nos três recifes,
é isso.

### A série medida, logo abaixo da previsão

Na página de cada recife, abaixo do painel, há dois gráficos: **temperatura da
superfície** e **calor acumulado (DHW)**, dos últimos 365 dias.

⚠️ **Eles não são a previsão.** A previsão está acima e fala do futuro; estes
gráficos são o que o satélite **mediu**, e falam do passado. A própria tela diz
isso por extenso, porque é a confusão mais fácil de cometer olhando a página.

O que esperar de cada um:

| Gráfico | O que você vê num ano normal |
|---|---|
| Temperatura | uma onda: sobe no verão, desce no inverno |
| DHW | quase sempre rente ao zero, subindo só quando há episódio de calor |

📌 **A linha vermelha tracejada no gráfico do DHW é o corte 4** — o "Alerta
Nível 1" da NOAA. Ela está lá porque `3,8` sozinho não diz nada, e *"3,8, quase
no 4"* diz tudo. Em 31/07/2026, Abrolhos passou o ano inteiro rente ao zero, e
Picãozinho teve um episódio no começo de 2026 que **subiu até quase encostar**
nessa linha.

⚠️ **Buraco na linha é dia sem medida válida, e não zero.** Quando a validação
física reprova um valor, o gráfico **interrompe** a linha ali em vez de
desenhar um ponto no chão — e conta quantos dias foram, logo abaixo. Ligar os
dois lados do buraco desenharia dado que não existe.

### Baixar a série

O botão **"Baixar a série completa (CSV)"**, abaixo dos gráficos, entrega a
série inteira daquele recife — não só o ano desenhado. O mesmo arquivo sai
direto pelo endereço:

```
http://localhost:8000/api/medicoes/?local=abrolhos-ba&formato=csv
```

O CSV traz, além de data e valor, as quatro colunas de **proveniência**:
`fonte`, `dataset_id`, `quality_flag` e `observacao`.

🚨 **Elas não são enfeite.** Um CSV sem elas é uma planilha qualquer: quem
receber o arquivo de segunda mão não tem como saber de onde veio o número nem
se ele passou na validação. E **valor reprovado sai como célula vazia, nunca
`0`** — num arquivo que a pessoa abre no Excel, não há nenhum aviso por perto
para corrigir a leitura.

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

✅ Terminando em `OK (skipped=1)`, em cerca de 100 segundos. Na medição de
31/07/2026 eram **679 testes** — o número cresce a cada mudança, então o que
importa é o `OK` no fim, não bater com este número. Depois, `cd ..` para voltar
à raiz.

### Dados

| Comando | O que faz |
|---|---|
| `testar_fontes` | testa quais fontes respondem desta rede — **não grava nada** |
| `testar_fontes --ssl` | diagnostica erro de certificado |
| `ingerir` | baixa dados novos das fontes externas |
| `ingerir --completo --desde=2020-01-01` | rebaixa o período inteiro |
| `ingerir_gcbd` | baixa a janela ambiental da base de branqueamento observado |
| `inventariar_datasets` | reconstrói o catálogo público a partir dos arquivos em disco |
| `conferir_especies` | lista as espécies cuja categoria de conservação ninguém consegue citar, com o link para conferir |

### Modelo

| Comando | O que faz |
|---|---|
| `treinar_modelo` | **mede** se o modelo presta (leave-year-out), contra **duas** linhas de base. Não grava |
| `treinar_final` | **grava** o modelo que o painel usa. Não mede |
| `treinar_final --listar` | mostra a ficha do modelo gravado |
| `calibrar` | confere se a probabilidade exibida é honesta |
| `limiar` | mede a troca entre alarme falso e evento perdido, por limiar |
| `treinar_gcbd` | a segunda entrega — prevê branqueamento observado, a partir de CSV |

🚨 **`treinar_modelo` e `treinar_final` têm propósitos opostos.** Um mede sem
gravar, o outro grava sem medir. Trocá-los é a confusão mais cara do projeto:
publicar o resultado do primeiro seria publicar um modelo que não existe em
disco; confiar num número do segundo seria confiar em memória, não em previsão.

📌 **O `treinar_modelo` compara com duas linhas de base**, e o veredito julga
contra a mais forte das duas:

| Linha de base | O que é |
|---|---|
| persistência | *"daqui a 7 dias vai estar como está hoje"* |
| **regra da NOAA** | `HotSpot ≥ 1` e `DHW ≥ 4`, **publicada diariamente** pela própria NOAA |

A segunda é a que importa: ganhar de uma cópia do dado de ontem não é o mesmo
que ganhar do produto que já está no ar de graça. Medido em 30/07/2026, o
modelo pega **17 dos 19 episódios** contra 15 das duas linhas de base, e cobra
por isso **11 alarmes falsos contra 6**. Ver
[RESULTADOS.md](RESULTADOS.md) §24 antes de citar qualquer um desses números
sozinho.

### Grafo, documentação e publicação

| Comando | O que faz |
|---|---|
| `neo4j_init` | cria o schema do grafo |
| `neo4j_projetar` | reconstrói o grafo do zero a partir do PostgreSQL, e confere |
| `neo4j_projetar --conferir` | só confere, sem escrever |
| `exportar_docs` | gera uma cópia `.docx` de cada documento em `docs/exportado/` |
| `sync_admin_code` | regenera a cópia local dos recifes e espécies que o site usa quando a API não responde |
| `preparar_deploy` | **antes de publicar**: reconstrói modelo, grafo e docs, e confere |
| `atualizar` | a rotina diária: ingere, reprojeta, relata o envelhecimento |

📌 **Sobre o `sync_admin_code`:** ele grava dois arquivos de código
(`generated_admin_sync.py` e `recifeData.js`) com o conteúdo atual do banco,
para o site ter o que mostrar se o backend cair. Rode-o depois de mexer em
recifes ou espécies pelo painel administrativo.

⚠️ **Esses arquivos são cópia, e cópia envelhece em silêncio.** Por isso eles
guardam só identidade e conteúdo — nome, estado, descrição, espécies. Até
30/07/2026 carregavam também **números de risco**, que é o pior conteúdo
possível para um arquivo assim: ele sobrevive a qualquer limpeza do banco e
reaparece justamente quando a API cai, que é quando ninguém tem como conferir.

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
| `npm test` | roda os testes do frontend (117 em 31/07/2026) |
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
| `FATAL: database "coral_brasil " does not exist` — repare no **espaço antes das aspas** | espaço sobrando no fim da linha `DATABASE_URL` | veja o quadro logo abaixo |
| O terminal mostra `>>` e fica esperando | quebra de linha no meio do comando colado | `Ctrl+C` e cole em uma linha só — veja abaixo |
| `SyntaxError: invalid syntax` apontando para `line 2` | a mesma coisa | idem |
| O site abre com tarja amarela e telas vazias | `OFFLINE_MODE=True` | troque para `False` em `backend/.env` e reinicie o backend |
| **O painel de risco não aparece — e não há erro nenhum no lugar dele**, mas recifes e espécies carregam normalmente | a mesma coisa: `OFFLINE_MODE=True`. O painel é o único bloco que some **sem escrever nada** (o gráfico ao menos avisa) | idem — e veja o Passo 7(c), que detalha o que some e o que fica |
| O painel aparece dizendo **"O modelo ainda nao esta disponivel neste servidor"** logo depois de você desligar o `OFFLINE_MODE` | não é a correção que falhou: são dois problemas em fila, e o segundo só ficou visível agora | `python backend\manage.py treinar_final` (precisa do Postgres no ar **e com série ingerida**) |
| Site abre, mas nenhum dado carrega | backend parado | ligue o `runserver` na porta 8000 |
| `Something is already running on port 3000` | outra instância aberta | feche o outro terminal, ou responda `Y` para usar outra porta |
| `Error: That port is already in use` (8000) | backend já rodando | use o que já está, ou `runserver 8001` |
| Painel diz **503, modelo indisponível** | falta o `.joblib` | `python backend\manage.py treinar_final` |
| Painel diz **`disponivel: false`** nos três | janela não fecha | normal quando a NOAA está atrasada; rode `atualizar` mais tarde |
| Painel responde **404** para um recife | modelo não treinou nesse local | o modelo viu 3 recifes; um quarto seria extrapolação |
| `relation "aquaculture_..." does not exist` | tabelas não criadas | `python backend\manage.py migrate` |
| `no such table` mencionando SQLite | `DATABASE_URL` não foi lida | confira `backend/.env` (nome do arquivo e `#` na linha) |
| Página do grafo vazia / erro 503 no grafo | Neo4j sem dados ou parado | `docker compose ps`, depois `neo4j_projetar` |
| `docker compose ps` diz `Restarting (1)` e a coluna PORTS está vazia | o container morre e nasce em laço | `docker compose logs neo4j` — veja abaixo |
| `ServiceUnavailable: Couldn't connect to localhost:7687` | mesma coisa, vista do outro lado | idem |
| `UnicodeEncodeError` num comando | acentuação no console do Windows | rode com `$env:PYTHONUTF8='1';` na frente |
| `CERTIFICATE_VERIFY_FAILED` na ingestão | cadeia de certificados incompleta **nesta máquina** | `python backend\manage.py testar_fontes --ssl` — a tabela do README diz o que fazer |
| `HTTP 503` do ERDDAP | servidor sobrecarregado | espere alguns minutos e repita; a ingestão é idempotente |
| `WinError 10060` / timeout na NOAA | você não está numa rede federal | use o espelho PACIOOS (é o padrão — não configure nada) |
| Ingestão termina com **0 medições** e explicação | a fonte ainda não publicou | não é falha; satélite sai com 1–3 dias de atraso |

### O container que reinicia sem parar

```
coral-neo4j   neo4j:5-community   Restarting (1) 5 seconds ago
```

Duas coisas nessa linha dizem o que aconteceu: o **`(1)`** é o código de saída,
e a coluna **PORTS está vazia**. Container que não está de pé não publica porta
— é por isso que o `7687` recusa conexão e o `neo4j_projetar` falha.

🚨 **`docker compose up -d` não conserta, e ainda por cima parece que
consertou:** ele responde `✔ Started` e reinicia exatamente o mesmo laço. A
causa nunca aparece no `ps`, só no log:

▶
```bash
docker compose logs neo4j --tail=60
```

As duas causas que já aconteceram neste projeto:

| No log | O que é | Conserto |
|---|---|---|
| `Invalid admin username, it must be neo4j.` | um `NEO4J_USER` diferente de `neo4j` chegou ao container | veja abaixo |
| `The minimum password length is 8 characters` | senha curta | use `coral_dev_local` |

Para a primeira, veja o valor **já resolvido**, depois de todas as substituições:

▶
```bash
docker compose config | Select-String "NEO4J_AUTH"
```

✅ Precisa dizer `NEO4J_AUTH: neo4j/coral_dev_local`.

Desde 30/07/2026 o `docker-compose.yml` fixa o `neo4j/` literal, justamente
porque **o Neo4j só aceita esse nome** para o administrador inicial — o campo
era uma variável, e portanto um botão que não existia. Se ainda assim aparecer
outro valor, a origem é uma variável de ambiente do Windows:

▶
```bash
"[$env:NEO4J_USER]"
```

Se não sair `[]` nem `[neo4j]`, apague em definitivo e reabra o terminal:

▶
```bash
[Environment]::SetEnvironmentVariable('NEO4J_USER', $null, 'User')
```

⚠️ Nada disso ameaça o PostgreSQL, e nenhum dado do projeto está em risco: o
Neo4j é **projeção derivada**. Se o volume dele estiver corrompido, apagar e
rodar `neo4j_projetar` reconstrói tudo em ~16 segundos.

---

### O prompt `>>` que não sai

Você colou um comando e o terminal, em vez de executar, passou a mostrar isto e
ficar esperando:

```
>>
```

**Não travou.** O `>>` é o PowerShell dizendo *"suas aspas não fecharam,
continue digitando"*. Ele aparece quando o texto colado tinha uma **quebra de
linha no meio**, quase sempre porque o comando era longo, apareceu embrulhado na
tela, e a seleção levou a quebra junto.

O sintoma seguinte é um erro que parece de programação e não é:

```
  File "<string>", line 2
    as M; print(M.objects.count(), 'medicoes')
    ^^
SyntaxError: invalid syntax
```

Repare no `line 2`: o Python recebeu duas linhas onde deveria haver uma.

**Saída:** aperte `Ctrl+C` e cole de novo, garantindo que o comando fique numa
linha só. Se for um comando comprido, prefira a forma interativa — abrir o
`manage.py shell` e digitar linha por linha, como no
[passo 11](#conferindo-o-que-entrou).

⚠️ Isto **não** é defeito da documentação: no arquivo o comando é uma linha só.
A quebra nasce entre o terminal e a área de transferência.

---

### 🚨 O espaço invisível no `.env`

Este merece seção própria porque a mensagem **aponta para o lugar errado**:

```
FATAL:  database "coral_brasil " does not exist
```

Você lê "o banco não existe" e vai conferir o Docker — mas o servidor
**respondeu**. Ele está no ar; o que ele recusou foi o *nome*. E o nome tem um
**espaço no fim**, visível só entre as aspas.

A causa é um espaço sobrando no fim da linha `DATABASE_URL` em `backend/.env`,
geralmente vindo de um copiar-e-colar. Ele sobrevive porque o `django-environ`
lê a linha com `(.*)\Z` e **não apara espaço em branco no fim** — só remove
aspas. O espaço entra na URL, o parser o entrega como parte do caminho, e vira
nome de banco.

Para ver o problema, é a mesma conferência do
[passo 9](#passo-9--criar-as-tabelas): abra o `manage.py shell` e peça
`s.DATABASES['default']['NAME']`.

✅ Correto: `'coral_brasil'`. ❌ Com o defeito: `'coral_brasil '` — o espaço fica
visível porque o Python mostra as aspas em volta.

Para corrigir todas as linhas do arquivo de uma vez:

▶
```bash
[IO.File]::WriteAllLines("$PWD\backend\.env", ((Get-Content backend\.env) -replace '\s+$',''))
```

⚠️ **Vale para qualquer linha do `.env`, não só a do banco.** Um espaço sobrando
depois de `NEO4J_PASSWORD=coral_dev_local` produz uma senha errada por um
caractere, e o Neo4j responde "credencial inválida" — sem nenhuma pista de que a
senha digitada estava certa. Aconteceu em 29/07/2026 com a `DATABASE_URL`.

---

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

**Escala de aviso** — os quatro degraus em que a probabilidade cai: *Sem
aviso*, *Observação* (0,05), *Alerta* (0,20) e *Alerta alto* (0,50). Cada um
vem com a **ação esperada** junto. Substituiu o corte único em 30/07/2026: com
um número só era preciso escolher entre cobrir tudo e ser levado a sério, e com
quatro degraus os dois objetivos deixam de competir.

**Limiar** — dentro da escala, o degrau a partir do qual há alerta de fato.
Hoje é **0,20**. Ele continua no payload por compatibilidade, mas quem desenha
a tela deve usar `nivel`.

**Linha de base** — o resultado mínimo que o modelo precisa superar para se
justificar. Aqui são duas: a **persistência** (*"vai estar como está hoje"*) e
a **regra publicada da NOAA**.

**Medição × previsão** — medição é o que o satélite registrou (passado, vem do
`/api/medicoes/`); previsão é o que o modelo calcula a partir dela (futuro, vem
do `/api/painel-risco/`). A página de cada recife mostra as duas e diz qual é
qual.

**Migração** — mudança na estrutura do banco, aplicada por `migrate`.

**Painel de risco** — o único endpoint que calcula em vez de servir dado
guardado.

**Proveniência** — de onde cada valor veio: qual fonte, qual dataset, qual dia.
O projeto grava isso valor a valor — e o CSV baixado leva essas colunas junto,
senão o arquivo vira planilha qualquer.

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

*Manual escrito em 29/07/2026, revisado em 31/07/2026. Os números citados
(57.426 medições, série até 24/07/2026, modelo treinado em 28/07/2026, 679
testes de backend e 117 de frontend) descrevem o estado desta máquina naquele
dia e envelhecem — os comandos, não.*

*A revisão de 31/07 acertou o que três mudanças tinham deixado para trás: o
limiar do painel (de 0,10 para 0,20, com a escala de quatro degraus no lugar
do corte único), a resposta de exemplo do painel, a segunda linha de base do
`treinar_modelo` e a série medida com download, que passou a aparecer no site.*
