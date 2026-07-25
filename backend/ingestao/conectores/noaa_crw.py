"""NOAA Coral Reef Watch - SST, DHW, HotSpot, anomalia e BAA.

Fonte das tres variaveis mais importantes do projeto: `sst` e `dhw` como
features, e `baa` como target. Acesso publico via ERDDAP, sem credenciais.

Produto: Daily Global 5 km Coral Bleaching Heat Stress v3.1
https://coralreefwatch.noaa.gov/product/5km/

Nota sobre o BAA: ele e **categoria ordinal**, e por isso e agregado por
maximo, nao por media - com a fracao da area em alerta gravada ao lado. Ver
`AGREGACAO` abaixo e docs/FONTES.md secao 6.16.

Nota sobre o DHW: usar a coluna `CRW_DHW` oficial, nunca recalcular. O
`carregar_historico.py` calculava um DHW proprio com limiar fixo de 27 °C
somando todos os hotspots positivos - a norma NOAA usa a MMM por pixel e so
acumula hotspots >= 1 °C. Ver docs/VARIAVEIS.md secao 3.2.
"""

import logging
from datetime import datetime, timezone

from django.conf import settings

from ..base import ConectorBase, Observacao, PeriodoIndisponivel, ResultadoColeta
from ..erros import resumir_erro
from ..retentativa import TENTATIVAS_PADRAO, executar_com_retentativa

logger = logging.getLogger(__name__)

# Colunas pedidas ao ERDDAP. HOTSPOT e SSTANOMALY entram porque sao baratos e
# uteis para diagnostico - a decisao de usa-los ou nao como feature e do
# modelo, nao da ingestao. Ver docs/VARIAVEIS.md secao 5.
VARIAVEIS_ERDDAP = (
    'CRW_SST',
    'CRW_DHW',
    'CRW_BAA',
    'CRW_HOTSPOT',
    'CRW_SSTANOMALY',
)

# Como cada variavel e reduzida dos ~121 pixels da bbox para um valor diario.
#
# Media so faz sentido para grandeza continua. O **BAA e categoria ordinal**
# (0 = sem estresse, 1 = Vigilancia, 2 = Aviso, 3 = Alerta Nivel 1,
# 4 = Alerta Nivel 2), e media de categoria nao e uma categoria: um recife com
# metade dos pixels em 0 e metade em 4 vira 2, que nao e o estado de pixel
# nenhum e ainda por cima **subestima** o alerta. Medido em Abrolhos,
# 17/05/2024: 70 pixels em 3, 45 em 4 e 6 em 2 dao media 3,32 - gravada como
# Alerta Nivel 1, enquanto 37% da area estava em Alerta Nivel 2, o patamar em
# que a NOAA preve mortalidade e nao so branqueamento.
#
# Explicacao com exemplo trabalhado: docs/VARIAVEIS.md secao 4.5.
#
# Para um sistema de aviso, o valor representativo do recife e o **pior estado
# observado nele**, nao o estado do pixel medio. Ver docs/FONTES.md secao 6.16.
AGREGACAO = {'CRW_BAA': 'max'}
AGREGACAO_PADRAO = 'mean'

# BAA >= 3 e "Alerta Nivel 1", o patamar em que a NOAA passa a esperar
# branqueamento - e por isso o corte que a fracao de area mede.
LIMIAR_ALERTA = 3.0

# Variavel derivada, sem equivalente no ERDDAP: o maximo diz o pior estado mas
# nao distingue um pixel isolado de um recife inteiro em alerta. Sao coisas
# diferentes para quem le o aviso, e a diferenca some em qualquer agregacao de
# um numero so - por isso ela e gravada como segunda serie, e nao como nota.
COLUNA_FRACAO_ALERTA = 'CRW_BAA_FRACAO_ALERTA'


# Servidor e dataset padrao. Escolhidos por evidencia, nao por preferencia:
#
# - `coastwatch.pfeg.noaa.gov` + `NOAA_DHW` foi verificado respondendo com as
#   cinco variaveis (incluindo CRW_BAA, o target) em 25/07/2026. E tambem o
#   servidor que o `coleta_de_dados.py` original usava.
# - PACIOOS (`pae-paha.pacioos.hawaii.edu` + `dhw_5km`) gerou os CSVs que o
#   projeto ja tem. Ja foi marcado aqui como "certificado invalido"; era
#   diagnostico errado - o `testar_fontes --ssl` mostra o mesmo host
#   verificando normalmente sob o bundle do certifi. A falha era de montagem de
#   cadeia no cliente. Ver ingestao/certificados.py.
# - `coastwatch.noaa.gov` + `noaacrwdhwDaily` respondeu 403 na mesma rede.
#   403 e bloqueio de aplicacao, nao de TLS: o handshake com esse host verifica.
#
# RESTRICAO DE REDE: os servidores da propria NOAA so respondem de dentro de
# rede com dominio federal (aqui, a UFF). O PACIOOS e da Universidade do Havai,
# nao da NOAA, e redistribui o mesmo produto - por isso funciona de qualquer
# rede. Para cron ou deploy fora da universidade, use o par PACIOOS.
#
# Servidor e dataset SEMPRE andam em par: cada espelho publica o mesmo produto
# sob um id proprio. Use `manage.py testar_fontes` para descobrir o par que
# funciona numa rede nova.
SERVIDOR_PADRAO = 'https://coastwatch.pfeg.noaa.gov/erddap'
DATASET_PADRAO = 'NOAA_DHW'

# Como cada espelho pode nomear as dimensoes de um jeito.
ALIASES_DIMENSAO = {
    'tempo': ('time',),
    'latitude': ('latitude', 'lat'),
    'longitude': ('longitude', 'lon'),
}


def _resolver_dimensoes(dim_names):
    """Descobre como este dataset chama tempo, latitude e longitude.

    Falhar aqui com o nome real das dimensoes e muito melhor que um KeyError
    seco la na frente, quando ninguem mais lembra que o problema era o espelho
    chamar a dimensao de `lat`.
    """
    encontradas = {}
    for canonico, aliases in ALIASES_DIMENSAO.items():
        nome = next((d for d in dim_names if d.lower() in aliases), None)
        if nome is None:
            raise ValueError(
                f'O dataset nao tem a dimensao "{canonico}". '
                f'Dimensoes publicadas: {list(dim_names)}.'
            )
        encontradas[canonico] = nome
    return encontradas


def _eixo_e_descendente(inicio_eixo, fim_eixo):
    """O eixo esta gravado do maior para o menor?

    O erddapy monta a URL griddap como `[(a):passo:(b)]`, e o ERDDAP espera que
    `a` e `b` sigam a ordem em que o eixo foi gravado - nao a ordem numerica.
    Num dataset com latitude descendente, pedir `(-18):(−17)` devolve vazio.
    """
    try:
        return float(inicio_eixo) > float(fim_eixo)
    except (TypeError, ValueError):
        # Eixo nao numerico (tempo vem como texto): assume ordem crescente.
        return False


def _ajustar_longitude(valor, inicio_eixo, fim_eixo):
    """Converte para 0..360 se for essa a convencao do dataset.

    Metade dos produtos de grade global usa −180..180 e a outra metade 0..360.
    Pedir −38,7 num dataset 0..360 nao da erro: devolve vazio, que e pior.
    """
    try:
        menor_do_eixo = min(float(inicio_eixo), float(fim_eixo))
    except (TypeError, ValueError):
        return valor

    if menor_do_eixo >= 0 and valor < 0:
        return valor + 360
    return valor


def _ultima_data_do_eixo(valor):
    """Converte o limite superior do eixo de tempo em `date`, se der.

    O erddapy devolve esse limite como o ERDDAP o publica: quase sempre texto
    ISO, as vezes epoch em segundos. Nao conseguir ler nao e motivo para travar
    a coleta - so significa que nao da para encolher o periodo.
    """
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor.strip().replace('Z', '+00:00')).date()
        except ValueError:
            pass

    try:
        return datetime.fromtimestamp(float(valor), tz=timezone.utc).date()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def limitar_periodo(inicio, fim, limite_do_eixo):
    """Encolhe o periodo pedido ate onde o dataset realmente tem dado.

    Produtos de satelite publicam com um a tres dias de atraso, e o padrao do
    comando `ingerir` e `--ate=hoje`. Sem isto, o caso mais comum de todos -
    pedir ate hoje - derruba a coleta inteira com um 404, em vez de trazer o
    que existe:

        Query error: ... "Stop" is greater than the axis maximum=2026-07-25
        (and even 2026-07-23T12:00:00Z)

    Retorna `(inicio, fim, nota)`.
    """
    ultima = _ultima_data_do_eixo(limite_do_eixo)

    if ultima is None or fim <= ultima:
        return inicio, fim, ''

    if inicio > ultima:
        raise PeriodoIndisponivel(
            f'O dataset vai ate {ultima.isoformat()}; o periodo pedido comeca em '
            f'{inicio.isoformat()}. Nada novo publicado ainda.'
        )

    return (
        inicio,
        ultima,
        f'Periodo encolhido de {fim.isoformat()} para {ultima.isoformat()}: '
        'e ate onde o dataset publica.',
    )


def fracao_em_alerta(df, coluna_data='__data', coluna_baa='CRW_BAA'):
    """Fracao dos pixels do recife em Alerta Nivel 1 ou acima, por data.

    Conta so os pixels com BAA valido: dividir pelo total da grade misturaria
    "sem estresse" com "sem dado" e diluiria o alerta exatamente nos dias de
    cobertura ruim, que sao os que mais importam.

    Retorna uma Series indexada por data, ou None se nao houver BAA valido.
    """
    valido = df[[coluna_data, coluna_baa]].dropna(subset=[coluna_baa])
    if valido.empty:
        return None

    return (valido[coluna_baa] >= LIMIAR_ALERTA).groupby(valido[coluna_data]).mean()


def montar_constraints(constraints_do_dataset, dim_names, bbox, inicio, fim):
    """Traduz a bbox e o periodo para as constraints que este dataset aceita.

    O erddapy exige que `e.constraints` mantenha **exatamente** as chaves que
    `griddap_initialize()` criou - inclusive as `*_step`. Substituir o
    dicionario levanta "keys in e.constraints have changed", que foi como esta
    funcao nasceu. Por isso devolvemos apenas os valores a atualizar.
    """
    dims = _resolver_dimensoes(dim_names)
    tempo, lat, lon = dims['tempo'], dims['latitude'], dims['longitude']

    lon_min, lat_min, lon_max, lat_max = bbox
    lon_min = _ajustar_longitude(
        lon_min, constraints_do_dataset[f'{lon}>='], constraints_do_dataset[f'{lon}<=']
    )
    lon_max = _ajustar_longitude(
        lon_max, constraints_do_dataset[f'{lon}>='], constraints_do_dataset[f'{lon}<=']
    )

    def na_ordem_do_eixo(dimensao, menor, maior):
        descendente = _eixo_e_descendente(
            constraints_do_dataset[f'{dimensao}>='],
            constraints_do_dataset[f'{dimensao}<='],
        )
        return (maior, menor) if descendente else (menor, maior)

    lat_a, lat_b = na_ordem_do_eixo(lat, lat_min, lat_max)
    lon_a, lon_b = na_ordem_do_eixo(lon, lon_min, lon_max)

    return {
        f'{tempo}>=': inicio.isoformat(),
        f'{tempo}<=': fim.isoformat(),
        f'{lat}>=': lat_a,
        f'{lat}<=': lat_b,
        f'{lon}>=': lon_a,
        f'{lon}<=': lon_b,
    }


class ConectorNoaaCrw(ConectorBase):
    slug = 'noaa_crw'
    nome = 'NOAA Coral Reef Watch 5 km v3.1'
    url_fonte = 'https://coralreefwatch.noaa.gov/product/5km/'
    variaveis = ('sst', 'dhw', 'baa', 'hotspot', 'sst_anomalia', 'baa_area_alerta')
    exige_credenciais = False

    def __init__(
        self, servidor=None, dataset_id=None, cliente=None, tentativas=None, dormir=None
    ):
        self.servidor = servidor or getattr(
            settings, 'NOAA_ERDDAP_SERVER', SERVIDOR_PADRAO
        )
        self.dataset_id = dataset_id or getattr(
            settings, 'NOAA_ERDDAP_DATASET', DATASET_PADRAO
        )
        self.tentativas = tentativas or getattr(
            settings, 'INGESTAO_TENTATIVAS', TENTATIVAS_PADRAO
        )
        # `cliente` e `dormir` existem para injetar dubles nos testes; em
        # producao o conector monta o proprio ERDDAP e espera de verdade.
        self._cliente = cliente
        self._dormir = dormir
        self._erddap = None
        self._eixos = None

    def _preparar_cliente(self):
        """Inicializa o ERDDAP uma vez e guarda os limites originais dos eixos.

        Atribuir o `dataset_id` dispara `griddap_initialize()`, que faz quatro
        requisicoes - uma delas o eixo de tempo inteiro do dataset, decadas de
        datas diarias. Como o backfill fatia o periodo em blocos, refazer isso
        a cada bloco multiplicaria o trafego sem necessidade: o dataset e o
        mesmo do primeiro ao ultimo.
        """
        if self._erddap is None:
            from erddapy import ERDDAP

            e = ERDDAP(server=self.servidor, protocol='griddap')
            e.dataset_id = self.dataset_id

            # Copia antes de qualquer alteracao. A partir do segundo bloco,
            # `e.constraints` ja carrega os nossos valores - e o
            # `montar_constraints` precisa dos limites reais do eixo para
            # decidir a ordem e a convencao de longitude.
            self._eixos = dict(e.constraints)
            e.variables = self._variaveis_publicadas(e.variables)
            self._erddap = e

        return self._erddap, self._eixos

    def _montar_cliente(self, bbox, inicio, fim):
        cliente, eixos = self._preparar_cliente()

        # O eixo de tempo so e conhecido depois do initialize - por isso o
        # periodo e encolhido aqui, e nao antes da chamada de rede.
        inicio, fim, nota = limitar_periodo(inicio, fim, eixos.get('time<='))
        if nota:
            logger.warning('%s: %s', self.dataset_id, nota)

        cliente.constraints.update(
            montar_constraints(eixos, cliente.dim_names, bbox, inicio, fim)
        )
        return cliente, nota

    def _variaveis_publicadas(self, disponiveis):
        """Pede so o que este espelho publica.

        O erddapy recusa a consulta inteira se uma variavel nao existir no
        dataset. Trocar de espelho passaria a derrubar a coleta em vez de
        trazer menos colunas - e melhor trazer o que ha e dizer o que faltou.
        """
        disponiveis = list(disponiveis or [])
        pedidas = [v for v in VARIAVEIS_ERDDAP if v in disponiveis]

        if not pedidas:
            raise ValueError(
                f'O dataset "{self.dataset_id}" nao publica nenhuma das '
                f'variaveis esperadas {list(VARIAVEIS_ERDDAP)}. '
                f'Publica: {disponiveis[:15]}. '
                'Rode "manage.py testar_fontes" para achar o espelho certo.'
            )

        faltando = [v for v in VARIAVEIS_ERDDAP if v not in disponiveis]
        if faltando:
            logger.warning(
                'O dataset %s nao publica %s - seguindo sem essas variaveis.',
                self.dataset_id,
                ', '.join(faltando),
            )

        return pedidas

    def _buscar(self, bbox, inicio, fim):
        """Uma tentativa completa de busca.

        Montar o cliente faz parte da tentativa, e nao de um passo anterior: o
        erddapy em modo griddap ja faz HTTP no construtor (busca o `.dds` para
        descobrir as dimensoes do dataset). Se o servidor devolver 503 nesse
        momento, reaproveitar um cliente meio construido nao adiantaria.
        """
        if self._cliente is not None:
            return self._cliente.to_pandas(), ''

        cliente, nota = self._montar_cliente(bbox, inicio, fim)
        return cliente.to_pandas(), nota

    def coletar(self, local, inicio, fim):
        try:
            bbox = self.verificar_local(local)
        except ValueError as exc:
            return ResultadoColeta(erro=str(exc), dataset_id=self.dataset_id)

        # O try precisa envolver toda a busca, inclusive a montagem do cliente:
        # deixar qualquer parte de fora faria a falha de rede escapar sem virar
        # ResultadoColeta.
        try:
            argumentos = {'rotulo': f'NOAA CRW ({self.dataset_id})',
                          'tentativas': self.tentativas}
            if self._dormir is not None:
                argumentos['dormir'] = self._dormir

            df, nota = executar_com_retentativa(
                lambda: self._buscar(bbox, inicio, fim), **argumentos
            )
        except PeriodoIndisponivel as exc:
            # Nao e falha: a fonte so ainda nao publicou o periodo pedido.
            logger.info('NOAA CRW sem dado novo: %s', exc)
            return ResultadoColeta(dataset_id=self.dataset_id, nota=str(exc))
        except Exception as exc:
            # Falha de rede nunca sobe: viraria queda de todo o pipeline.
            resumo = resumir_erro(exc)
            logger.warning('Falha ao coletar do NOAA CRW: %s', resumo)
            logger.debug('Detalhe completo da falha do NOAA CRW', exc_info=exc)
            return ResultadoColeta(erro=resumo, dataset_id=self.dataset_id)

        resultado = self._extrair(df)
        if nota and not resultado.nota:
            resultado.nota = nota
        return resultado

    def _extrair(self, df):
        """Converte o DataFrame do ERDDAP em observacoes brutas.

        O produto e uma grade: varios pixels por data dentro da bbox, que
        precisam virar um valor diario por variavel. **A regra de agregacao e
        por variavel**, nao uniforme - ver `AGREGACAO`. Escolher um unico pixel
        seria a outra saida, e descartaria informacao sem criterio.
        """
        import pandas as pd

        if df is None or len(df) == 0:
            return ResultadoColeta(dataset_id=self.dataset_id)

        # O ERDDAP devolve nomes como "CRW_SST (degree_C)".
        renomeadas = {c: c.split('(')[0].strip() for c in df.columns}
        df = df.rename(columns=renomeadas)

        coluna_tempo = next(
            (c for c in df.columns if c.strip().lower() == 'time'), None
        )
        if coluna_tempo is None:
            return ResultadoColeta(
                erro='Resposta do ERDDAP sem coluna "time".',
                dataset_id=self.dataset_id,
            )

        df[coluna_tempo] = pd.to_datetime(df[coluna_tempo], errors='coerce', utc=True)
        df = df.dropna(subset=[coluna_tempo])
        df['__data'] = df[coluna_tempo].dt.date

        presentes = [c for c in VARIAVEIS_ERDDAP if c in df.columns]
        if not presentes:
            return ResultadoColeta(
                erro=(
                    'Nenhuma variavel esperada na resposta. '
                    f'Colunas recebidas: {list(df.columns)}'
                ),
                dataset_id=self.dataset_id,
            )

        for coluna in presentes:
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce')

        agregado = df.groupby('__data')[presentes].agg(
            {c: AGREGACAO.get(c, AGREGACAO_PADRAO) for c in presentes}
        )
        colunas_saida = list(presentes)

        if 'CRW_BAA' in presentes:
            fracao = fracao_em_alerta(df)
            if fracao is not None:
                # Alinhado pelo indice de data: um dia sem BAA valido fica NaN
                # aqui e vira observacao nula adiante, como qualquer lacuna.
                agregado[COLUNA_FRACAO_ALERTA] = fracao
                colunas_saida.append(COLUNA_FRACAO_ALERTA)

        observacoes = []
        for data, linha in agregado.iterrows():
            for coluna in colunas_saida:
                valor = linha[coluna]
                observacoes.append(
                    Observacao(
                        data=data,
                        coluna=coluna,
                        valor=None if pd.isna(valor) else float(valor),
                    )
                )

        return ResultadoColeta(
            observacoes=observacoes,
            dataset_id=self.dataset_id,
        )
