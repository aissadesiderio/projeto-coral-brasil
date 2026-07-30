# Coral Brasil

Site e modelo de predição de estresse térmico em recifes de coral brasileiros.
Django 5 + DRF no backend, React no frontend, dados de NOAA Coral Reef Watch e
Copernicus Marine Service.

> **O site está deliberadamente offline** durante a reestruturação de backend e
> banco. As regras de liberação estão em [PLANEJAMENTO.md](PLANEJAMENTO.md).

## Documentação

**Começando do zero? Leia [docs/VISAO_GERAL.md](docs/VISAO_GERAL.md).** Ele
explica o problema biológico, o que cada variável significa e como as peças se
encaixam, sem pressupor oceanografia nem aprendizado de máquina.

| Documento | Conteúdo |
|---|---|
| [docs/MANUAL.md](docs/MANUAL.md) | **Como rodar.** Do zero até o site aberto, passo a passo, com o que deve aparecer em cada etapa e o que fazer quando não aparece |
| [docs/VISAO_GERAL.md](docs/VISAO_GERAL.md) | **Porta de entrada.** O projeto explicado do início: branqueamento, DHW, BAA, o caminho do dado e o que falta |
| [docs/FONTES.md](docs/FONTES.md) | Toda fonte de dados: origem, licença, citação e problemas de proveniência conhecidos |
| [docs/VARIAVEIS.md](docs/VARIAVEIS.md) | Por que cada variável entra ou fica de fora do modelo |
| [docs/METODOLOGIA_SIMPLES.md](docs/METODOLOGIA_SIMPLES.md) | **Sem jargão — a ciência.** Como o modelo funciona e é testado, para ler e explicar |
| [docs/SISTEMA_SIMPLES.md](docs/SISTEMA_SIMPLES.md) | **Sem jargão — o software.** Backend e frontend, endpoints, onde os dados moram, o que é cada arquivo estranho |
| [docs/METODOLOGIA.md](docs/METODOLOGIA.md) | O mesmo, com os termos técnicos: a régua, o teste sem trapaça e por que acurácia não serve |
| [docs/RESULTADOS.md](docs/RESULTADOS.md) | O que o experimento produziu, e o que ainda não dá para concluir |
| [docs/GCBD.md](docs/GCBD.md) | A base de branqueamento observado: o que contém, o que custa integrar, seus defeitos e o resultado do passo 1 |
| [docs/arquitetura.md](docs/arquitetura.md) | Separação entre banco transacional e grafo científico |
| [backend/docs/contrato_canonico_variaveis.md](backend/docs/contrato_canonico_variaveis.md) | Nomes, unidades e regras de qualidade canônicas |
| [PLANEJAMENTO.md](PLANEJAMENTO.md) | Checklist de go-live |

### Cópia em `.docx`

Para ler fora do editor, anexar num e-mail ou levar para o Word:

```bash
python backend\manage.py exportar_docs
```

Gera um `.docx` de cada documento em `docs/exportado/`. Um só:

```bash
python backend\manage.py exportar_docs --doc=docs/RESULTADOS.md
```

⚠️ **O `.docx` é artefato derivado, não uma segunda cópia.** Ele não é
versionado e é regerado por este comando — se fosse versionado, em duas semanas
o `.docx` diria uma coisa e o `.md` outra, e ninguém saberia qual vale. Edite
sempre o Markdown.

O conversor cobre o subconjunto de Markdown que esta documentação usa
(cabeçalhos, tabelas, listas, citações, blocos de código e formatação inline),
com testes garantindo que **nenhum texto se perde** e que as tabelas saem com
as dimensões certas — elas carregam os resultados. Ver
[`backend/documentacao/`](backend/documentacao/).

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

⚠️ **De dentro de `backend/`, e não da raiz.** O `manage.py test` descobre os
testes a partir do diretório atual: da raiz ele encontra **zero** e imprime
`NO TESTS RAN` — saindo com sucesso, o que passa por "tudo passou". Verificado
em 29/07/2026; até então este README documentava a forma que não roda nada.

```bash
cd backend
python manage.py test
```

São 527 testes, ~90 s, terminando em `OK (skipped=1)`.

```bash
cd frontend
npm test
```

Os testes de ingestão não usam rede: o cliente ERDDAP é substituído por um
dublê. A chamada HTTP real precisa ser verificada rodando o comando `ingerir`.

Os testes do GCBD também não precisam do CSV de 16 MB: montam quadros pequenos
à mão.

---

## Modelos

### Entrega 1 — prever o BAA em `t+N`

Usa o banco. Ver [docs/RESULTADOS.md](docs/RESULTADOS.md) §1–§10.

#### Gravar o modelo que o painel vai usar

**Dois comandos, com propósitos opostos.** Para *medir* se o modelo presta:

```bash
python backend\manage.py treinar_modelo
```

Para *gravar* o que será servido — treina uma vez sobre todos os dados:

```bash
python backend\manage.py treinar_final
```

⚠️ **`treinar_final` não reporta desempenho, de propósito.** Um número calculado
sobre os mesmos dados do treino mediria memória, não previsão.

O artefato vai para `dados/modelos/`, **não versionado** — é derivado e
regerável. Consequência prática: **quem publicar precisa rodar este comando**.

```bash
python backend\manage.py treinar_final --listar
```

Opções: `--horizonte 14`, `--modelo boosting`, `--nome outro`, `--semente 7`.

#### Figuras: o que o modelo aprendeu

```bash
python backend\manage.py graficos
```

Gera cinco tipos de figura em `relatorios_gerados/graficos/`, escritas para
serem lidas por quem não é da área, cada uma com um `.txt` ao lado dizendo
sobre que dado foi feita. Nenhuma delas calcula nada novo — todo número já é
produzido por `ml/importancia.py`, `ml/calibracao.py` ou `ml/modelo.py` e já
sai em texto nos outros comandos.

| Figura | Responde |
|---|---|
| **`o_que_e_previsto`** | **o que prevemos, e por que isso não é branqueamento** |
| `linha_do_tempo_<recife>` | o que aconteceu, o que previmos, e o que o modelo viu |
| `coeficientes_por_ano` | o modelo dá o mesmo peso a cada variável todo ano? |
| `importancia_por_ano` | de qual variável a previsão realmente depende? |
| `resposta_a_variavel` | quanto cada variável precisa mudar para o aviso sair? |

🚨 **A primeira é pré-requisito das outras.** O modelo prevê **alerta de
estresse térmico** (`baa ≥ 3`, critério NOAA), e não branqueamento observado.
A diferença está medida: quando o alerta dispara houve branqueamento em 10 de
10 casos, mas **78 dos 88 branqueamentos registrados no Brasil ocorreram sem
alerta nenhum** ([RESULTADOS.md §11.2](docs/RESULTADOS.md)). Toda figura sai
com esse aviso carimbado no rodapé — por construção, não por disciplina: o
carimbo é aplicado por `_selar()`, e há teste exigindo-o em cada uma.

Opções: `--pdf` (para inserir no texto sem perder nitidez), `--so tempo`,
`--repeticoes N`.

⚠️ **Artefato derivado, não versionado.** Figura versionada envelhece em
silêncio — em duas semanas o PNG mostra um modelo e o código produz outro.

🚨 **As duas primeiras descrevem os modelos do leave-year-out; a última, o
modelo que está no ar.** São objetos diferentes de propósito: um responde
"isso generaliza?", o outro responde "o que está servindo faz o quê?".

#### Conferir se a probabilidade exibida é honesta

```bash
python backend\manage.py calibrar
```

Compara a probabilidade prometida com a frequência observada, por faixa, sobre
predição **fora da dobra**.

🚨 **Isto já pegou um defeito grave:** o modelo prometia **16,5%** onde a taxa
real é **8,4%** — porque `class_weight='balanced'` conserta a *decisão* e
distorce a *probabilidade*. Por isso `treinar_final` grava **recalibrado por
padrão** (`--calibrar isotonic`). Ver [docs/RESULTADOS.md](docs/RESULTADOS.md) §22.

⚠️ Consequência para o painel: **probabilidade calibrada para exibir, limiar
declarado para avisar**. No modelo recalibrado o corte equivalente ao antigo
fica em **0,20**, não em 0,50.

#### Servir a predição: `/api/painel-risco/`

O único endpoint que **faz conta**. Carrega o artefato gravado por
`treinar_final`, monta a janela de 7 dias a partir da série do PostgreSQL e
devolve a probabilidade calibrada.

```bash
curl http://localhost:8000/api/painel-risco/
```

| Situação | Resposta |
|---|---|
| tudo certo | `200` com `probabilidade`, `limiar`, `data_base`, `entradas` |
| janela incompleta | `200`, item com `disponivel: false` e **qual dia faltou** |
| local que o modelo não treinou | `404` com a lista dos disponíveis |
| artefato ausente | `503` pedindo `treinar_final` |

⚠️ **O limiar vem de `settings.PAINEL_LIMIAR`** (padrão `0.20`) e vai no
payload. Subir o número troca alarme falso por evento perdido — é decisão de
quem opera, não de quem treina.

🚨 **Quem exibir isso não pode escrever "0%" nem "100%".** A recalibração
isotônica é função escada e devolve `0,000` e `1,000` exatos por construção —
12,2% das amostras de treino caem em `p = 0` exato. Isso significa *"nenhum
alerta neste degrau"*, não *"impossível"*. A API sinaliza com `no_extremo:
true`. Ver [docs/RESULTADOS.md](docs/RESULTADOS.md) §22.8.

### Entrega 2 — prever branqueamento observado (GCBD)

**Não usa o banco nem a rede** — lê só o CSV do GCBD.

```bash
python backend\manage.py treinar_gcbd --importancia
```

Versão reduzida, com os três coeficientes fisicamente interpretáveis:

```bash
python backend\manage.py treinar_gcbd --interpretavel --importancia
```

O arquivo **não é versionado** (16 MB). Baixe pelo DOI registrado em
[docs/GCBD.md](docs/GCBD.md) e coloque em
`dados/global_bleaching_environmental.csv`, ou aponte a variável de ambiente
`GCBD_CSV` para ele.

Opções úteis: `--modelo boosting`, `--limiar 10` (percentual de branqueamento
que conta como positivo), `--com-climatologia`, `--com-contexto`.

#### Janela ambiental (passo 2)

Baixa salinidade e oxigênio nos 90 dias antes de cada visita. **Usa rede** e
exige a credencial do Copernicus, a mesma de `ingerir`.

```bash
python backend\manage.py ingerir_gcbd
```

Leva alguns minutos e **grava a cada visita**: pode ser interrompido, e rodar de
novo continua de onde parou. O resultado vai para
`dados/gcbd_janelas_ambientais.csv`, não para o banco — o porquê está em
[docs/GCBD.md](docs/GCBD.md).

Depois, para treinar com as variáveis não térmicas junto:

```bash
python backend\manage.py treinar_gcbd --interpretavel --ambiental --importancia
```

E o experimento espelho, só com as não térmicas:

```bash
python backend\manage.py treinar_gcbd --so-ambiental --importancia
```

Resultados em [docs/RESULTADOS.md](docs/RESULTADOS.md) §11–§14.

---

## Publicar

Um comando, antes de qualquer deploy:

```bash
python backend\manage.py preparar_deploy
```

Ele reconstrói **o que não viaja no `git push`** e confere o resultado:

| # | Passo | Por quê |
|---|---|---|
| 1 | `migrate` | sem o schema, nada mais roda |
| 2 | `treinar_final` | o `.joblib` não é versionado |
| 3 | `neo4j_projetar` | o grafo é derivado do PostgreSQL |
| 4 | `exportar_docs` | os `.docx` derivam do Markdown |
| 5 | `conferir_persistencia` | valida o resultado, não a intenção |

🚨 **Sem ele, um `git clone` seguido de deploy sobe um site sem modelo:**
`/api/painel-risco/` responde **503** nos três recifes e o grafo vem vazio.
Nenhum item do checklist falha por isso — é o buraco *entre* eles.

⚠️ **Para no primeiro erro, e sai com código 1.** Um deploy que segue depois de
um passo quebrado entrega um site meio construído, que é pior do que um que não
sobe: ele parece ter funcionado.

Opções: `--sem-grafo` (ambiente que só serve a API), `--sem-docs`.

Para conferir sem reconstruir nada — índices, constraints e o tempo das
consultas quentes, contra o banco real:

```bash
python backend\manage.py conferir_persistencia
```

## Manter o site atualizado

Depois de publicado, **nada roda sozinho**. Sem agendamento a série congela no
dia do deploy, e o painel passa a prever a partir de dado velho — declarando o
atraso, mas velho.

Um comando por dia resolve:

```bash
python backend\manage.py atualizar
```

Ele ingere só o que falta (retoma da última data), reprojeta o grafo e relata o
que envelheceu. É idempotente: rodar duas vezes no mesmo dia não duplica nada.

### 🚨 Ele **não** retreina o modelo, e isso é decisão

A rotina óbvia seria ingerir + retreinar + projetar, deixando tudo fresco. Seria
errado:

> Um modelo que muda toda noite é um modelo que **ninguém mediu**. O
> `treinar_final` grava sem avaliar de propósito — quem avalia é o
> `treinar_modelo`, com leave-year-out. Encadear o primeiro num agendador
> trocaria, todo dia, um modelo medido por um não medido.

Então o modelo envelhece — e a rotina **torna isso visível** em vez de esconder.
Depois de 90 dias sem retreino ela avisa, deixando claro que não é erro:

```
(!) O modelo foi treinado ha 94 dias, sobre dados ate 2026-07-28.
    Isto nao e erro - o retreino e deliberado de proposito. Mas vale
    medir antes de decidir: "manage.py treinar_modelo" avalia,
    "treinar_final" grava.
```

Também avisa se a ingestão parar (7 dias sem dado novo) ou se não houver modelo
no disco. **Em dia normal, não diz nada** — rotina que avisa todo dia treina
quem lê a ignorar.

### Agendando

O comando aceita `--silencioso`, que só imprime quando há algo a dizer. Saída
vazia = dia normal.

Linux/macOS, 6h todo dia:

```bash
0 6 * * * cd /caminho/do/projeto && venv/bin/python backend/manage.py atualizar --silencioso
```

Windows, pelo Agendador de Tarefas:

```bash
schtasks /create /tn "coral-brasil-atualizar" /tr "C:\caminho\venv\Scripts\python.exe C:\caminho\backend\manage.py atualizar --silencioso" /sc daily /st 06:00
```

⚠️ **Sai com código 1 quando falha.** É o único canal que o agendador entende —
não há ninguém lendo a tela quando a rotina roda.

## Grafo (Neo4j)

O Neo4j é **projeção derivada**: nunca recebe escrita que não venha do
PostgreSQL. Se divergir ou for perdido, reconstrua.

```bash
python backend\manage.py neo4j_projetar
```

Reconstrói o grafo do zero — 57.420 medições, **172 mil elementos em ~16 s** —
e **confere item a item** contra o PostgreSQL ao terminar. Projetar sem
conferir não vale: uma projeção que falha no meio deixa o grafo parcial e
silencioso, e a consulta seguinte responde incompleto sem avisar.

Só conferir, sem escrever:

```bash
python backend\manage.py neo4j_projetar --conferir
```

⚠️ **Substitui o `neo4j_seed`**, que derivava de `StatusPredicao` — o modelo
legado, com 3 registros.

O que o grafo responde e a tabela não responde bem: **a proveniência de cada
valor exibido**, e a emenda entre produtos do Copernicus, numa travessia só.
Ver [docs/arquitetura.md](docs/arquitetura.md).

---

## Estrutura

```
backend/
  coral_site/      configuração Django
  aquaculture/     modelos, API, admin
  ingestao/        pipeline de coleta (conectores, normalização, qualidade)
  ml/              conjunto supervisionado, linha de base, modelo, importância
                   (gcbd.py = entrega 2, lê CSV em vez do banco)
  ml_models/       modelo de predição legado
  documentacao/    conversor Markdown -> .docx
  dados/           CSVs brutos (não versionados)
  db/              conexão e schema Neo4j
dados/             GCBD e outros CSVs de fonte externa (não versionados)
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
