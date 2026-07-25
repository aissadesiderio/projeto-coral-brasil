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

Cada execução gera um registro em `ExecucaoIngestao` com status, contagem e
motivo da falha. Uma fonte fora do ar não derruba as outras.

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

Situação verificada em 25/07/2026:

| Espelho | Servidor | Dataset | Estado |
|---|---|---|---|
| pfeg (**padrão**) | `https://coastwatch.pfeg.noaa.gov/erddap` | `NOAA_DHW` | ✅ 5/5 variáveis |
| NOAA CoastWatch | `https://coastwatch.noaa.gov/erddap` | `noaacrwdhwDaily` | ⚠️ HTTP 403 |
| PACIOOS | `https://pae-paha.pacioos.hawaii.edu/erddap` | `dhw_5km` | ⚠️ certificado inválido |

O PACIOOS gerou os CSVs que o projeto já tem, mas falhou com
`CERTIFICATE_VERIFY_FAILED` em duas redes independentes — problema no
certificado do servidor, não bloqueio local.

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
