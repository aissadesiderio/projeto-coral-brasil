"""Monta o `LOGGING` do Django a partir do ambiente.

🚨 **Ate aqui o projeto nao tinha `LOGGING` nenhum em `settings.py`.** As
chamadas de `logger.warning` espalhadas por `ingestao/`, `ml/` e `db/` caiam na
configuracao implicita do Django: visiveis no `runserver`, **invisiveis** sob
cron. A rotina diaria de `manage.py atualizar` e justamente a que roda sem
ninguem olhando, e era a que menos deixava rastro.

Decisao central: **um arquivo unico, nao um arquivo por dominio.**

O pedido admitia "unificado ou por classe/arquivo/dominio", e a tentacao e
separar (`ingestao.log`, `ml.log`, `db.log`) porque parece mais organizado.
Separar quebraria exatamente o que se quer:

- um fluxo real **atravessa** dominios — `atualizar` chama `ingestao`, depois
  `db.projecao`, e um erro de projecao muitas vezes tem causa na ingestao. Em
  arquivos separados, reconstruir isso vira juntar dois arquivos por horario,
  que e o problema que a `correlacao` foi criada para eliminar;
- a granularidade pedida ja existe **dentro** do registro: `logger` da o
  dominio, `arquivo` da o arquivo e a linha, `funcao` da a funcao. Filtrar por
  dominio e um `grep`, e continua permitindo cruzar dominios quando preciso.

O que e por dominio e o **nivel**, nao o destino: `LOG_NIVEL_INGESTAO=DEBUG`
deixa a ingestao falante sem inundar o log com o resto.

⚠️ **Arquivo desligado por padrao quando roda teste.** A suite escreveria em
`backend/logs/` a cada execucao, e um clone novo passaria a diferir de um clone
que ja rodou os testes — o mesmo defeito que derrubou o CI em 30/07 por outro
caminho. Ver `LOG_EM_ARQUIVO`.
"""

import sys

# Nivel de cada dominio, quando o ambiente nao disser outra coisa. Os nomes sao
# os pacotes reais do backend, e por isso o filho herda: `ingestao.conectores`
# nao precisa aparecer aqui.
DOMINIOS = ('aquaculture', 'db', 'dados', 'ingestao', 'ml', 'observabilidade')

# Nome do arquivo unificado e do arquivo so de falhas. O segundo e redundante
# por definicao (toda linha dele esta no primeiro) e existe assim mesmo: quem
# abre o log durante um incidente quer ver **so** o que quebrou, e um `grep`
# sobre centenas de megabytes de INFO nao e o que se faz com o site fora do ar.
ARQUIVO_UNIFICADO = 'coral.jsonl'
ARQUIVO_ERROS = 'erros.jsonl'

# 20 MB por arquivo, 10 arquivos. Sao ~200 MB de teto para o log inteiro, na
# mesma ordem de grandeza dos 78 MB de CSV que o projeto ja guarda. Sem
# rotacao, um `DEBUG` esquecido ligado enche o disco da VM em dias.
ROTACAO_MB_PADRAO = 20
BACKUPS_PADRAO = 10


def rodando_teste(argv=None):
    """Se o processo atual e uma execucao da suite.

    ⚠️ Checa `sys.argv`, e nao uma variavel de ambiente, porque precisa valer
    para `manage.py test` rodado a mao — que e como a suite roda aqui — sem
    exigir que ninguem se lembre de exportar nada antes.
    """
    argumentos = sys.argv if argv is None else argv
    return any(arg == 'test' for arg in argumentos[1:2]) or 'pytest' in argumentos[0]


def montar(*, base_dir, nivel='INFO', nivel_console=None, pasta=None,
           em_arquivo=True, rotacao_mb=ROTACAO_MB_PADRAO,
           backups=BACKUPS_PADRAO, niveis_por_dominio=None):
    """Devolve o dicionario de `LOGGING`.

    `nivel` vale para os dominios do projeto; `nivel_console` filtra so o que
    aparece na tela, para que o arquivo possa guardar DEBUG enquanto o console
    mostra INFO — o caso normal de um backfill longo.
    """
    nivel_console = nivel_console or nivel
    niveis_por_dominio = niveis_por_dominio or {}

    if em_arquivo:
        # ⚠️ A pasta so e resolvida quando ha arquivo. Calcular `base_dir /
        # 'logs'` antes obrigaria quem so quer console a passar um `base_dir`
        # que nao vai ser usado — e foi assim que a primeira versao quebrou.
        pasta = pasta or (base_dir / 'logs')
        # Criar aqui, e nao no primeiro registro: o `RotatingFileHandler` abre
        # o arquivo ao ser construido, e um `FileNotFoundError` no meio da
        # configuracao do `logging` sai como um traceback do `dictConfig` que
        # nao menciona a pasta.
        pasta.mkdir(parents=True, exist_ok=True)

    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'level': nivel_console,
            'formatter': 'legivel',
            'filters': ['correlacao'],
            # 🚨 stderr, e nao stdout. Os comandos deste projeto escrevem
            # resultado em stdout (`conferir_especies`, `limiar`, o CSV de
            # `exportar_docs`), e log misturado nesse fluxo corromperia
            # qualquer redirecionamento para arquivo.
            'stream': 'ext://sys.stderr',
        },
    }

    if em_arquivo:
        handlers['arquivo'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'json',
            'filters': ['correlacao'],
            'filename': str(pasta / ARQUIVO_UNIFICADO),
            'maxBytes': rotacao_mb * 1024 * 1024,
            'backupCount': backups,
            'encoding': 'utf-8',
            # ⚠️ `delay` evita criar o arquivo em processos que nunca logam -
            # `manage.py shell`, os autocompletes, o proprio `--help`.
            'delay': True,
        }
        handlers['erros'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'json',
            'filters': ['correlacao'],
            'filename': str(pasta / ARQUIVO_ERROS),
            'maxBytes': rotacao_mb * 1024 * 1024,
            'backupCount': backups,
            'encoding': 'utf-8',
            'delay': True,
        }

    destinos = list(handlers)

    loggers = {}
    for dominio in DOMINIOS:
        loggers[dominio] = {
            'handlers': destinos,
            'level': niveis_por_dominio.get(dominio, nivel),
            'propagate': False,
        }

    # O Django tambem passa a ser gravado: um 500 em producao precisa estar no
    # mesmo arquivo, com a mesma correlacao, que o resto do fluxo que o causou.
    loggers['django'] = {
        'handlers': destinos, 'level': 'INFO', 'propagate': False,
    }
    loggers['django.request'] = {
        'handlers': destinos, 'level': 'WARNING', 'propagate': False,
    }
    # ⚠️ `django.db.backends` fica em WARNING **de proposito**. Em DEBUG ele
    # registra toda consulta SQL, e a suite de testes sozinha geraria centenas
    # de milhares de linhas - o log deixaria de ser legivel exatamente quando
    # alguem mais precisa dele.
    loggers['django.db.backends'] = {
        'handlers': destinos, 'level': 'WARNING', 'propagate': False,
    }

    return {
        'version': 1,
        # 🚨 Nunca `True`. Desligar os loggers existentes silenciaria as
        # bibliotecas que importam antes do Django configurar - entre elas o
        # `copernicusmarine`, cujo aviso de credencial expirada e a unica
        # pista quando a coleta volta vazia.
        'disable_existing_loggers': False,
        'filters': {
            'correlacao': {
                '()': 'observabilidade.correlacao.FiltroCorrelacao',
            },
        },
        'formatters': {
            'legivel': {'()': 'observabilidade.formatadores.TextoLegivel'},
            'json': {'()': 'observabilidade.formatadores.JsonLinhas'},
        },
        'handlers': handlers,
        'loggers': loggers,
        'root': {'handlers': destinos, 'level': 'WARNING'},
    }
