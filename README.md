# Coral Brasil

Site e modelo de predição de estresse térmico em recifes de coral brasileiros.
Django 5 + DRF no backend, React no frontend, dados de NOAA Coral Reef Watch e
Copernicus Marine Service.

> **O site está deliberadamente offline** durante a reestruturação de backend e
> banco. As regras de liberação estão em [PLANEJAMENTO.md](PLANEJAMENTO.md).

## Documentação

| Documento | Conteúdo |
|---|---|
| [docs/FONTES.md](docs/FONTES.md) | Toda fonte de dados: origem, licença, citação e problemas de proveniência conhecidos |
| [docs/VARIAVEIS.md](docs/VARIAVEIS.md) | Por que cada variável entra ou fica de fora do modelo |
| [docs/arquitetura.md](docs/arquitetura.md) | Separação entre banco transacional e grafo científico |
| [backend/docs/contrato_canonico_variaveis.md](backend/docs/contrato_canonico_variaveis.md) | Nomes, unidades e regras de qualidade canônicas |
| [PLANEJAMENTO.md](PLANEJAMENTO.md) | Checklist de go-live |

---

## Setup

Requer **Python 3.13** (o Django 5.1+ ainda não suporta o 3.14) e Node 18+.

### 1. Backend

```bash
py -3.13 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

⚠️ **Ative o venv em cada terminal novo.** Sem ele, `python backend\manage.py`
usa o Python do sistema, que não tem as dependências — o projeto detecta isso e
diz qual Python está em uso, mas o erro só some ativando o ambiente.

### 2. Configuração — obrigatória

O projeto **não sobe sem um `backend/.env`**. Esse arquivo não é versionado,
então cada máquina precisa do seu — inclusive um clone novo.

```bash
copy backend\.env.example backend\.env
```

Isso já basta para desenvolvimento: com `DJANGO_DEBUG=True` e a chave
comentada, o projeto usa uma chave de desenvolvimento.

Para gerar uma chave própria (obrigatório se `DJANGO_DEBUG=False`):

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

⚠️ Não deixe `DJANGO_SECRET_KEY=` vazio no `.env`. Uma variável definida como
string vazia sobrescreve o valor padrão — ou comente a linha, ou preencha.

### 3. Banco

**PostgreSQL é a fonte única da verdade** desde 25/07/2026 — ver
[docs/arquitetura.md](docs/arquitetura.md). SQLite ainda funciona (é o
*fallback* quando não há `DATABASE_URL`), mas serve só para rodar teste rápido:
com duas máquinas, dois arquivos SQLite divergem em silêncio e não há como
saber qual está certo.

Os dois bancos sobem por **Docker Compose** — um comando, mesmas versões em
qualquer máquina, sem instalador e sem PATH.

#### 3.1 Instalar o Docker Desktop (Windows)

1. Baixe em **https://www.docker.com/products/docker-desktop/** →
   *Download for Windows*.
2. Rode o instalador e deixe **"Use WSL 2 instead of Hyper-V"** marcado.
   Se ele avisar que falta o WSL, aceite instalar.
3. **Reinicie o computador** quando ele pedir. Não é opcional — o WSL 2 só
   passa a valer depois do reboot.
4. Abra o Docker Desktop e espere o ícone da baleia ficar estável (a barra de
   status para de dizer *starting*). Ele precisa estar **aberto** para os
   comandos abaixo funcionarem.
5. Confirme:

```bash
docker --version; docker compose version
```

<details>
<summary><strong>"Virtualization support not detected"</strong> — leia antes de mexer na BIOS</summary>

Essa mensagem do Docker Desktop é enganosa: na maioria das vezes a
virtualização **está** ligada e o que falta é o WSL. Diagnostique antes:

```bash
wsl --status
```

**Se responder "O Subsistema do Windows para Linux não está instalado"**, a
causa é essa. Abra o PowerShell **como Administrador** e rode:

```bash
wsl --install --no-distribution
```

(`--no-distribution` instala só a plataforma WSL 2, que é o que o Docker
precisa — ele traz a própria distribuição. Se a sua versão do `wsl` não
reconhecer a opção, use `wsl --install`, que instala o Ubuntu junto.)

**Reinicie o computador.** O WSL 2 só vale depois do reboot.

**Se depois do reboot o `wsl --status` disser "O WSL2 não pode ser iniciado
porque a virtualização não está habilitada"**, o `wsl --install` instalou o
WSL mas não ligou o componente do Windows. Aconteceu nesta máquina em
25/07/2026. Ainda **como Administrador**:

```bash
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

```bash
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

Reinicie de novo. Foi o que resolveu — e note que **a mensagem fala em
firmware, mas a causa era um componente do Windows desligado.**

---

**Só suspeite da BIOS se o WSL já estiver instalado.** Confirme com:

```bash
(Get-CimInstance Win32_ComputerSystem).HypervisorPresent
```

`True` significa que **já existe um hypervisor rodando** — o que é impossível
com a virtualização desligada no firmware. Nesse caso a BIOS está certa e o
problema é outro.

⚠️ Não use `Win32_Processor.VirtualizationFirmwareEnabled` para isso: quando
um hypervisor já tomou as extensões do processador, essa propriedade reporta
`False` mesmo com tudo habilitado, e leva à conclusão errada.

`False` em `HypervisorPresent`, aí sim: reinicie entrando na BIOS/UEFI
(geralmente `Del`, `F2` ou `F10` na tela do fabricante) e ative **Intel
VT-x**, **AMD-V** ou **SVM Mode**, conforme o processador.
</details>

#### 3.2 Subir os bancos

Na raiz do projeto:

```bash
docker compose up -d
```

A primeira vez baixa as imagens (algumas centenas de MB) e demora alguns
minutos. As próximas sobem em segundos.

Acompanhe até os dois ficarem `healthy`:

```bash
docker compose ps
```

O Postgres fica pronto em segundos; o Neo4j leva ~30. Enquanto diz
`starting`, ainda não aceita conexão — o container existir não significa que
o serviço responde, e é por isso que o compose declara *healthcheck*.

Comandos do dia a dia:

| Comando | O que faz |
|---|---|
| `docker compose up -d` | sobe os dois em segundo plano |
| `docker compose ps` | mostra estado e saúde |
| `docker compose stop` | para sem apagar nada |
| `docker compose logs neo4j` | mostra o log de um serviço |
| `docker compose down` | remove os containers, **mantém os dados** |
| `docker compose down -v` | remove os containers **e apaga os dados** |

⚠️ `down -v` é o único comando dessa lista que destrói dados. Os volumes são
nomeados justamente para o dado sobreviver a `down` e voltar no próximo `up`.

#### 3.3 Apontar o Django para eles

```bash
pip install -r requirements.txt
```

No `backend/.env`, acrescente:

```
DATABASE_URL=postgres://coral:coral_dev_local@localhost:5432/coral_brasil
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=coral_dev_local
```

*(conteúdo de arquivo, não comando)*. As senhas precisam bater com as do
`docker-compose.yml` — os padrões dele são exatamente estes. Para trocar, veja
[.env.example](.env.example) na raiz, que é o arquivo do Docker (o do Django é
o `backend/.env`).

A senha vai literal, sem aspas. Use só letras, números e sublinhado: `@ : / #`
têm significado dentro de uma URL e o erro não diz que a culpa é da senha.

Confirme para onde o Django está apontando **antes** de migrar:

```bash
python backend\manage.py shell -c "from django.conf import settings as s; print(s.DATABASES['default']['ENGINE'], s.DATABASES['default'].get('NAME'))"
```

Precisa dizer `postgresql`. Se disser `sqlite3`, a `DATABASE_URL` não foi lida.

```bash
python backend\manage.py migrate
```

#### 3.4 Levar os dados do SQLite para o PostgreSQL

Só necessário se você já tinha dados no SQLite. Com a `DATABASE_URL`
**comentada** (para exportar do SQLite):

```bash
$env:PYTHONUTF8='1'; python backend\manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.Permission --exclude admin.logentry --exclude sessions.session --indent 1 -o backend\dados_sqlite.json
```

⚠️ O `PYTHONUTF8=1` não é opcional no Windows: sem ele o `dumpdata` falha com
`'charmap' codec can't encode character '\u207b'` ao chegar na unidade
`mmol·m⁻³` do oxigênio. O erro não menciona encoding do arquivo de saída.

Agora **descomente** a `DATABASE_URL` e importe:

```bash
$env:PYTHONUTF8='1'; python backend\manage.py loaddata backend\dados_sqlite.json
```

Confira que veio tudo:

```bash
python backend\manage.py shell -c "from aquaculture.models import MedicaoAmbiental as M; print(M.objects.count(), 'medicoes')"
```

O arquivo `dados_sqlite.json` tem ~20 MB e está no `.gitignore` — é
reconstruível a qualquer momento. O `db.sqlite3` antigo pode ficar onde está
como backup; ele deixa de ser lido assim que a `DATABASE_URL` existe.

⚠️ **O Docker não faz as duas máquinas compartilharem dados.** Cada uma tem
seu próprio volume local. O que ele iguala é *versão e configuração* — nada de
"na minha máquina o Postgres é 14". Para os dados serem os mesmos nos dois
computadores é preciso um banco hospedado (Neon, Supabase, Railway têm plano
gratuito) e uma única `DATABASE_URL` apontando para lá. Enquanto isso não
existir, o procedimento é: ingerir sempre na mesma máquina, ou mover o dado
com `dumpdata`/`loaddata`.

#### 3.5 Superusuário

```bash
python backend\manage.py createsuperuser
```

⚠️ **O banco não vem no repositório.** Toda máquina que puxa código novo
precisa rodar `migrate` — inclusive quando o projeto já funcionava ali. Os
comandos de dados avisam se o banco está atrasado.

### 4. Rodar

```bash
python backend\manage.py runserver
```

```bash
cd frontend
npm install
npm start
```

---

## Ingestão de dados

O pipeline (`backend/ingestao/`) busca as séries ambientais das fontes
externas e grava com proveniência por valor.

```bash
python backend\manage.py ingerir --local=abrolhos-ba --desde=2026-07-01
python backend\manage.py ingerir --desde=ontem
python backend\manage.py ingerir --completo --desde=2020-01-01
```

Por padrão a ingestão é **incremental**: retoma da última data já gravada.
Use `--completo` para rebaixar o período inteiro. Rodar duas vezes o mesmo
período não duplica nem apaga — a gravação é idempotente.

### Backfill de séries longas

O período pedido é **fatiado em blocos** antes de virar requisição. Pedir seis
anos de uma vez faz o ERDDAP responder `HTTP 408` ou `ReadTimeout` — a
requisição é grande demais, e a execução inteira termina sem nada.

```bash
python backend\manage.py ingerir --desde=2020-01-01 --completo
```

O padrão é 180 dias por bloco (`INGESTAO_JANELA_DIAS` no `.env`, ou `--janela`
na linha de comando). Cada bloco é **gravado assim que chega**, então:

- Uma interrupção no meio preserva o que já veio.
- Rodar de novo **sem** `--completo` retoma de onde parou.
- Um bloco que falha não descarta os que deram certo — a execução termina como
  `parcial`, listando quais períodos faltaram.

Se três blocos seguidos falharem, o comando para em vez de percorrer dezenas de
blocos gastando a retentativa em cada um. A mensagem diz quantos não foram
tentados.

Se ainda houver timeout, diminua a janela:

```bash
python backend\manage.py ingerir --desde=2020-01-01 --completo --janela=90
```

### Atraso de publicação

Produtos de satélite saem com 1 a 3 dias de atraso. Como o padrão é
`--ate=hoje`, pedir dados até hoje é o caso normal — e o ERDDAP responde **404
à janela inteira** se ela passar do fim do eixo de tempo, em vez de devolver o
que existe.

O pipeline encolhe o período sozinho até onde a fonte publica e registra o que
fez:

```
[ok]  noaa_crw/abrolhos-ba: 115 medicoes
      Periodo encolhido de 2026-07-25 para 2026-07-23: e ate onde o dataset publica.
```

Se a janela inteira estiver além do que existe, a execução termina como
**sucesso com 0 medições** e a explicação junto — não é falha, a fonte só ainda
não publicou.

Cada execução gera um registro em `ExecucaoIngestao` com status, contagem e
motivo da falha. Uma fonte fora do ar não derruba as outras.

### Falhas passageiras

Servidores ERDDAP respondem `HTTP 503 — Service Unavailable` quando estão
sobrecarregados, pedindo para tentar de novo em um minuto. O pipeline faz isso
sozinho: **3 tentativas, esperando 10 s e 30 s**. Ajuste com
`INGESTAO_TENTATIVAS` no `.env`.

Só falhas passageiras são repetidas — 503, 504, timeout, conexão derrubada.
Certificado inválido, 403 e 404 falham na primeira tentativa, porque esperar
não muda a resposta. A regra está em [`backend/ingestao/retentativa.py`](backend/ingestao/retentativa.py).

Se o 503 persistir depois das três tentativas, é sobrecarga real do servidor:
espere alguns minutos e rode de novo. A ingestão é incremental e idempotente,
então repetir o comando não custa nada.

### `CERTIFICATE_VERIFY_FAILED`

```
URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify
failed: unable to get local issuer certificate>
```

Isso **não** quer dizer que o servidor tenha um certificado ruim. Quer dizer
que esta máquina não conseguiu montar a cadeia até uma raiz confiável. No
Windows é comum: o OpenSSL do Python não busca o certificado intermediário que
falta (o navegador busca), e a loja de raízes do Windows é preenchida sob
demanda.

O comando `ingerir` já aponta o OpenSSL para o bundle do `certifi`, o que
resolve o caso normal. Se ainda falhar, diagnostique:

```bash
python backend\manage.py testar_fontes --ssl
```

O comando testa cada espelho com as duas cadeias — a do sistema e a do
`certifi` — e a diferença entre elas diz o que fazer:

| Resultado | Significado | O que fazer |
|---|---|---|
| Só o `certifi` verifica | Falta uma raiz nesta máquina | Nada — o pipeline já usa o `certifi` |
| Só o sistema verifica | A rede intercepta TLS com uma raiz já instalada no Windows | Não defina `SSL_CERT_FILE` |
| Nenhum dos dois | Proxy interceptando com raiz desconhecida, ou certificado realmente inválido | Ver abaixo |
| Nenhum, sem handshake | Porta bloqueada — não é certificado | Tentar de outra rede |

No caso do proxy, o comando imprime os nomes legíveis dentro do certificado
apresentado. Se aparecer o nome da instituição ou de um produto de firewall, é
interceptação: peça o certificado raiz ao suporte de TI e aponte para ele.

```bash
setx SSL_CERT_FILE "C:\caminho\para\raiz-da-instituicao.pem"
```

Um `SSL_CERT_FILE` já definido é respeitado — o projeto não sobrescreve.

⚠️ **Não desligue a verificação de certificado.** Um `verify=False` faz o erro
sumir aceitando qualquer certificado, inclusive o de quem estiver no meio do
caminho. Para dados científicos com proveniência declarada, isso invalidaria a
cadeia de custódia que o resto do pipeline se dá o trabalho de manter.

### Diagnóstico de rede

Antes da primeira ingestão numa máquina ou rede nova:

```bash
python backend\manage.py testar_fontes
```

Não grava nada. Testa cada espelho ERDDAP conhecido, informa **quais das 5
variáveis cada dataset publica**, e recomenda o par a usar. Também avisa se o
`.env` tem servidor e dataset de espelhos diferentes.

⚠️ `NOAA_ERDDAP_SERVER` e `NOAA_ERDDAP_DATASET` **andam em par** — cada espelho
publica o mesmo produto sob um id próprio. Trocar só um dos dois gera um 404
difícil de diagnosticar.

⚠️ Essas linhas são **conteúdo do arquivo `backend/.env`**, não comandos. Colar
`NOAA_ERDDAP_SERVER=...` no PowerShell devolve `CommandNotFoundException` — o
PowerShell define variável de ambiente com `$env:NOME = "valor"`, e mesmo assim
o valor sumiria ao fechar o terminal. Edite o arquivo.

🔒 **Os servidores da própria NOAA só respondem de rede com domínio federal**
(no caso deste projeto, a UFF). O PACIOOS não é da NOAA — é da Universidade do
Havaí e redistribui o mesmo produto, então funciona de qualquer rede. Se a
ingestão for rodar por cron, em deploy ou fora da universidade, use o par
PACIOOS.

Situação verificada em 25/07/2026, com `testar_fontes` nas duas redes:

| Espelho | Servidor | Dataset | Na UFF | Fora da UFF |
|---|---|---|---|---|
| **PACIOOS** (**padrão**) | `https://pae-paha.pacioos.hawaii.edu/erddap` | `dhw_5km` | não medido | ✅ 5/5 |
| pfeg | `https://coastwatch.pfeg.noaa.gov/erddap` | `NOAA_DHW` | ✅ 5/5 — 503 intermitente | ❌ `WinError 10060` (timeout) |
| NOAA CoastWatch | `https://coastwatch.noaa.gov/erddap` | `noaacrwdhwDaily` | ⚠️ HTTP 403 | ⚠️ HTTP 403 |

**Você não precisa configurar nada** — o PACIOOS é o padrão do código desde
25/07/2026. As linhas acima só são necessárias para *forçar* outro espelho.

Ele não é um plano B degradado: os dois espelhos foram comparados bloco a bloco
no backfill de 2020–2026 e deram **resultado idêntico**. Foi pelo PACIOOS que os
43.038 registros atuais do CRW foram ingeridos.

O espelho oficial da NOAA seria o pfeg, mas **um padrão que só funciona numa
rede específica não é padrão** — é uma armadilha para quem clonar o projeto.
Quem estiver na UFF e quiser o servidor da própria NOAA descomenta as duas
linhas de `NOAA_ERDDAP_*` no `.env`.

⚠️ "Não medido" na tabela é literal: o PACIOOS nunca foi testado de dentro da
UFF. Não há motivo conhecido para falhar lá, mas isso é inferência. Se você
rodar `testar_fontes` na universidade, atualize a tabela.

O PACIOOS chegou a ser marcado aqui como "certificado inválido". Estava errado:
`testar_fontes --ssl` mostra o mesmo host verificando normalmente sob o bundle
do `certifi`. A falha era de montagem de cadeia **no cliente**, não no servidor.

⚠️ O estado de cada espelho depende da máquina e da rede tanto quanto do
servidor. Rode `testar_fontes` na máquina que vai ingerir.

### Credenciais do Copernicus

Exige conta gratuita em
[data.marine.copernicus.eu/register](https://data.marine.copernicus.eu/register).

⚠️ **Não** é o cadastro de `www.copernicus.eu` (portal do programa, hoje
arquivado) nem do Climate Data Store. São três serviços distintos, com contas
que não se conversam. Use o **username** do cadastro, não o e-mail.

Autentique pelo próprio cliente:

```bash
copernicusmarine login
```

Ele **pergunta** usuário e senha e guarda em `~/.copernicusmarine`, fora do
projeto. Digite no prompt — não passe `--username`/`--password` na linha de
comando, que isso deixa a senha no histórico do shell.

Existem também `COPERNICUSMARINE_SERVICE_USERNAME` e `..._PASSWORD` no `.env`,
mas prefira o login: senha em arquivo dentro do projeto é senha que uma hora
vaza num commit ou num print. O `testar_fontes` reconhece as duas formas e diz
qual está em uso.

### O que o conector Copernicus coleta

**Salinidade** e **oxigênio**. Cada série emenda dois produtos: reanálise
(`*_my_*`, 1993 até cerca de um mês atrás) no histórico, análise (`*_anfc_*`)
no período recente. Cada medição grava o `dataset_id` de onde saiu — a costura
fica rastreável valor a valor.

⚠️ **Previsão nunca entra no banco.** Os produtos `anfc` publicam dias no
futuro: em 25/07/2026 o catálogo ia até 04/08. São valores previstos, não
medidos, e gravá-los como medição seria vazamento direto num modelo com
horizonte de N dias. O corte é sempre em ontem.

**KD490 fica fora do padrão** — só existe de 2023-11-15 em diante e não tem
reanálise, o que cortaria o treino de 6,5 para 2,7 anos e apagaria o evento de
branqueamento de 2020. Continua disponível para o experimento no subperíodo:

```
COPERNICUS_SERIES=salinidade,oxigenio,kd490
```

A justificativa está em [docs/VARIAVEIS.md](docs/VARIAVEIS.md) §3.5.

### Catálogo de datasets

```bash
python backend\manage.py inventariar_datasets --dry-run
python backend\manage.py inventariar_datasets
```

Reconstrói o catálogo público a partir dos arquivos que existem de fato em
`backend/dados/`, lendo tamanho e período do disco. Os CSVs **não são
versionados** — um clone novo começa com o catálogo vazio até rodar a ingestão.

---

## Testes

```bash
python backend\manage.py test
```

```bash
cd frontend
npm test
```

Os testes de ingestão não usam rede: o cliente ERDDAP é substituído por um
dublê. A chamada HTTP real precisa ser verificada rodando o comando `ingerir`.

---

## Estrutura

```
backend/
  coral_site/      configuração Django
  aquaculture/     modelos, API, admin
  ingestao/        pipeline de coleta (conectores, normalização, qualidade)
  ml_models/       modelo de predição
  dados/           CSVs brutos (não versionados)
  db/              conexão e schema Neo4j
frontend/src/
  pages/           páginas roteadas
  components/      componentes reutilizáveis
  utils/           helpers de API e formatação
docs/              documentação do projeto
```

---

## Licença

Código sob licença MIT (ver [LICENSE](LICENSE)). **Os dados e as imagens seguem
as licenças de suas fontes originais** — NOAA, Copernicus e iNaturalist exigem
atribuição específica. Ver [docs/FONTES.md](docs/FONTES.md) seção 7.
