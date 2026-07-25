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
    'crw_hotspot': 'hotspot',
    'crw_sstanomaly': 'sst_anomalia',
    'sst_anomaly': 'sst_anomalia',
    # Copernicus Marine
    'thetao': 'sst',
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

    # BAA e ordinal - normaliza para inteiro sem alterar a escala.
    if variavel == 'baa':
        valor = float(int(round(valor)))

    return ValorNormalizado(
        variavel=variavel,
        valor=valor,
        unidade=UNIDADES[variavel],
        quality_flag=flag,
        observacao=observacao,
    )
