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

```bash
python backend\manage.py migrate
python backend\manage.py createsuperuser
```

⚠️ **O banco é local e não vem no repositório.** Toda máquina que puxa código
novo precisa rodar `migrate` de novo — inclusive quando você já tinha o projeto
funcionando ali antes. Os comandos de dados avisam se o banco está atrasado.

SQLite é o padrão local. Para PostgreSQL, defina `DATABASE_URL` no `.env` e
descomente `psycopg` no `requirements.txt` — nenhuma mudança de código é
necessária.

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

Situação verificada em 25/07/2026 — as duas primeiras linhas medidas **na rede
da UFF**, a terceira de fora:

| Espelho | Servidor | Dataset | Estado |
|---|---|---|---|
| pfeg (**padrão**) | `https://coastwatch.pfeg.noaa.gov/erddap` | `NOAA_DHW` | ✅ 5/5 variáveis — 503 intermitente |
| NOAA CoastWatch | `https://coastwatch.noaa.gov/erddap` | `noaacrwdhwDaily` | ⚠️ HTTP 403 |
| PACIOOS | `https://pae-paha.pacioos.hawaii.edu/erddap` | `dhw_5km` | ✅ entregou dado real (115 medições) |

O PACIOOS chegou a ser marcado aqui como "certificado inválido". Estava errado:
`testar_fontes --ssl` mostra o mesmo host verificando normalmente sob o bundle
do `certifi`. A falha era de montagem de cadeia **no cliente**, não no servidor.

⚠️ O estado de cada espelho depende da máquina e da rede tanto quanto do
servidor. Rode `testar_fontes` na máquina que vai ingerir.

**Copernicus** exige conta gratuita — preencha
`COPERNICUSMARINE_SERVICE_USERNAME` e `..._PASSWORD` no `.env`.

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
