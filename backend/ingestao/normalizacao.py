"""Traducao de nomes e unidades de fonte para o vocabulario canonico.

Implementa a tabela de mapeamento de
`backend/docs/contrato_canonico_variaveis.md`. Nenhuma rotina de deduplicacao
pode rodar sem passar por aqui - e a regra de governanca daquele contrato.
"""

from dataclasses import dataclass

# Unidade canonica de cada variavel.
UNIDADES = {
    'sst': '°C',
    'dhw': '°C·semana',
    'baa': 'categoria',
    'baa_area_alerta': 'fração',
    'hotspot': '°C',
    'sst_anomalia': '°C',
    'salinidade': 'PSU',
    'oxigenio': 'mmol·m⁻³',
    'kd490': 'm⁻¹',
    'clorofila': 'mg·m⁻³',
    'par': 'µmol·m⁻²·s⁻¹',
}

# Nome na fonte -> nome canonico. Comparacao sempre em minusculas.
MAPA_COLUNAS = {
    # NOAA Coral Reef Watch
    'crw_sst': 'sst',
    'crw_dhw': 'dhw',
    'crw_baa': 'baa',
    # Derivada pelo conector, nao publicada pelo ERDDAP: fracao dos pixels do
    # recife em Alerta Nivel 1 ou acima. Ver conectores/noaa_crw.py.
    'crw_baa_fracao_alerta': 'baa_area_alerta',
    'crw_hotspot': 'hotspot',
    'crw_sstanomaly': 'sst_anomalia',
    'sst_anomaly': 'sst_anomalia',
    # Copernicus Marine
    # ⚠️ `thetao` **nao** aparece aqui de proposito. Ver COLUNAS_RECUSADAS.
    'so': 'salinidade',
    'o2': 'oxigenio',
    'kd': 'kd490',
    'kd490': 'kd490',
    'chl': 'clorofila',
    'chlor_a': 'clorofila',
    'par': 'par',
    'ppfd': 'par',
    # Fallback previsto pelo contrato: aceito, mas sempre marcado como
    # degradado por COLUNAS_DEGRADADAS abaixo.
    'par_error': 'par',
}

# Colunas que o contrato marca como proibidas ou degradadas.
COLUNAS_RECUSADAS = {
    'talk': (
        'Alcalinidade nao e pH. O contrato canonico proibe a substituicao sem '
        'transformacao quimica documentada.'
    ),
    'sob': (
        'Salinidade no fundo, nao em superficie - grandeza diferente de "so".'
    ),
    # 🚨 Removida de MAPA_COLUNAS em 28/07/2026, na auditoria do vocabulario.
    #
    # Ate entao `thetao` era traduzida para `sst`, o mesmo nome canonico do
    # `CRW_SST` da NOAA. As duas nao sao a mesma grandeza:
    #
    #   CRW_SST : temperatura da superficie do mar
    #   thetao  : temperatura POTENCIAL, extraida a 13,47 m de profundidade
    #
    # docs/FONTES.md secao 6.10 ja registrava a mistura de profundidades como
    # problema conhecido do acervo; o mapeamento a **codificava** no
    # vocabulario, que e o lugar onde ela fica mais dificil de perceber.
    #
    # ⚠️ Entra em RECUSADAS em vez de simplesmente sumir. Coluna desconhecida
    # devolve `None` em silencio; recusada levanta com o motivo. Quem tentar
    # ingerir `thetao` daqui a seis meses precisa receber a explicacao, nao um
    # campo que nao aparece.
    #
    # Se a temperatura do Copernicus for necessaria um dia, ela volta com nome
    # canonico proprio e profundidade declarada — nunca sob `sst`.
    'thetao': (
        'Temperatura potencial a 13,47 m, nao temperatura de superficie. '
        'Compartilhar o nome canonico "sst" com o CRW_SST afirmaria que sao a '
        'mesma grandeza. Ver docs/FONTES.md secao 6.10 e o contrato canonico.'
    ),
}

# Nomes canonicos que existem no vocabulario e **nao tem dado no banco**.
#
# ⚠️ Nao sao sobra: cada um foi avaliado e ficou de fora por um motivo medido.
# A lista existe para que "nome sem dado" seja sempre uma decisao declarada, e
# nunca resto de algo que se esqueceu de remover — ha teste exigindo que todo
# canonico nao ingerido apareca aqui com motivo.
#
# Um vocabulario que promete mais do que serve confunde quem le; um que apaga o
# que ja foi testado faz o proximo repetir o teste. Declarar resolve os dois.
SEM_DADO = {
    'kd490': (
        'So existe de 2023-11-15 em diante e nao tem reanalise, o que cortaria '
        'o treino de 6,5 para 2,7 anos. O conector sabe busca-la (esta em '
        'SERIES), mas ela fica fora do padrao. Ver docs/VARIAVEIS.md secao 3.5.'
    ),
    'clorofila': (
        'Testada no experimento do GCBD sobre 45.318 valores: nenhuma '
        'combinacao melhora a previsao. Nao ha conector para o pipeline '
        'principal. Ver docs/RESULTADOS.md secao 21.'
    ),
    'par': (
        'Sem fonte confiavel no acervo: o arquivo disponivel traz o campo de '
        'incerteza (PAR_error) e nao a medida. Ver docs/FONTES.md secao 6.12.'
    ),
}

COLUNAS_DEGRADADAS = {
    'par_error': (
        'Campo de incerteza do PAR, nao o PAR. Aceito apenas como fallback, '
        'sempre com quality_flag=degradado.'
    ),
}


class ColunaRecusada(ValueError):
    """A coluna existe na fonte mas o contrato canonico proibe seu uso."""


@dataclass(frozen=True)
class ValorNormalizado:
    variavel: str
    valor: float
    unidade: str
    quality_flag: str = 'ok'
    observacao: str = ''


def resolver_variavel(nome_coluna):
    """Traduz o nome de uma coluna de fonte para o nome canonico.

    Levanta `ColunaRecusada` quando o contrato proibe a coluna. Retorna None
    quando a coluna simplesmente nao interessa ao projeto.
    """
    chave = nome_coluna.strip().lower()

    if chave in COLUNAS_RECUSADAS:
        raise ColunaRecusada(f'{nome_coluna}: {COLUNAS_RECUSADAS[chave]}')

    return MAPA_COLUNAS.get(chave)


def normalizar(nome_coluna, valor):
    """Converte um valor bruto para a unidade canonica.

    Retorna `ValorNormalizado` ou None se a coluna nao for de interesse.
    """
    variavel = resolver_variavel(nome_coluna)
    if variavel is None:
        return None

    if valor is None:
        return None

    valor = float(valor)
    chave = nome_coluna.strip().lower()
    flag, observacao = 'ok', ''

    if chave in COLUNAS_DEGRADADAS:
        flag = 'degradado'
        observacao = COLUNAS_DEGRADADAS[chave]

    # Temperaturas: heuristica de Kelvin prevista no contrato.
    if variavel in ('sst', 'hotspot') and valor > 200:
        valor = valor - 273.15
        observacao = (observacao + ' Convertido de Kelvin para °C.').strip()

    # BAA e ordinal - normaliza para inteiro sem alterar a escala. Desde que a
    # agregacao espacial passou a ser por maximo o valor ja chega inteiro; isto
    # fica como rede para fontes que entreguem 3.0000001. Comparacao exata: a
    # fracao de area (`baa_area_alerta`) e continua e nao pode ser arredondada.
    if variavel == 'baa':
        valor = float(int(round(valor)))

    return ValorNormalizado(
        variavel=variavel,
        valor=valor,
        unidade=UNIDADES[variavel],
        quality_flag=flag,
        observacao=observacao,
    )
