"""Passo 2 da entrega 2: a janela ambiental antes de cada visita do GCBD.

O passo 1 mediu a lacuna: **78 dos 88 branqueamentos observados no Brasil
aconteceram com `TSA_DHW` = 0**, sem nenhum estresse termico acumulado pelo
criterio da NOAA ([RESULTADOS.md](../../docs/RESULTADOS.md) §11). Este modulo
busca o que pode ocupar esse espaco: **salinidade e oxigenio dissolvido** nos
90 dias que precedem cada visita.

**Por que 90 dias.** E a escala em que o estresse termico opera - o DHW da NOAA
acumula 12 semanas. Usar a mesma janela mantem a comparacao honesta: as duas
familias de variavel enxergam o mesmo intervalo.

**Por que nao entra no banco.** `MedicaoAmbiental` pendura em `LocalRecife`, que
sao os tres recifes monitorados, com foto, slug e pagina publica. Os 119 sitios
do GCBD nao sao recifes monitorados: sao pontos de amostragem de um estudo
retrospectivo de 1994-2010. Cria-los como `LocalRecife` encheria a tabela
publica de 119 registros falsos para viabilizar um experimento.

Entao a janela vira **cache em `dados/`**, do mesmo jeito que o proprio CSV do
GCBD: nao versionado, reconstruivel por um comando, com proveniencia gravada
valor a valor. E coerente com `ml/gcbd.py`, que ja le arquivo em vez do banco.

⚠️ **Tres decisoes de extracao ficam gravadas em cada linha**, porque nenhuma e
neutra:

1. **`raio_graus`** - o quadrado em volta do ponto de onde o valor saiu. A grade
   do oxigenio e 0,25° (~28 km) e **69 das 166 visitas estao a menos de 1 km da
   costa**: muitos recifes caem em celula mascarada como terra. Medido em
   26/07/2026: com 0,15° achamos oceano para 118 de 119 sitios na salinidade e
   99 de 119 no oxigenio; com 0,30°, para todos. Um valor colhido a 33 km do
   recife nao e o mesmo que um colhido em cima dele, e quem ler o resultado
   precisa saber qual foi.
2. **`n_celulas`** - quantas celulas de oceano entraram na media.
3. **`dataset_id`** - de qual produto. So a reanalise e usada aqui: ela cobre
   **1993-01-01 em diante** (conferido nos dois produtos em 26/07/2026) e o
   GCBD brasileiro comeca em 1994-03-15, entao **nao ha emenda com produto de
   analise** - ao contrario da serie da entrega 1.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_CACHE = RAIZ / 'dados' / 'gcbd_janelas_ambientais.csv'

DIAS_DA_JANELA = 90

# Raios tentados, em graus, do mais justo para o mais largo. Parar no primeiro
# que devolve oceano mantem o valor o mais perto possivel do recife.
RAIOS_BUSCA = (0.15, 0.30, 0.60, 1.00)

VARIAVEIS = ('salinidade', 'oxigenio')

# --- qualidade da agua -------------------------------------------------------
#
# **Estas tres saem do MESMO arquivo de onde ja vem o oxigenio**
# (`cmems_mod_glo_bgc_my_0.25deg_P1D-m`), diarias, de 1993 a 2026. Conferido no
# catalogo em 26/07/2026: o produto publica `chl`, `no3`, `po4`, `si`, `nppv` e
# `o2`. Nao ha fonte nova, credencial nova nem codigo novo - so mais nomes.
#
# ⚠️ **Por que ficam aqui e nao em `conectores/copernicus.py::SERIES`.**
# Aquele dicionario alimenta o comando `ingerir`, que grava em
# `MedicaoAmbiental`. Uma variavel listada la e que nao tenha nome canonico em
# `ingestao/normalizacao.py` viraria uma opcao que aceita o pedido e quebra no
# meio da gravacao. Estas tres existem **so** para o experimento retrospectivo,
# que grava em CSV - entao ficam declaradas onde sao usadas.
#
# Escolha deliberada de tres, e nao das seis disponiveis:
#   chl  - clorofila, o indicador de eutrofizacao mais estabelecido
#   no3  - nitrato, o nutriente de mecanismo mais direto
#   si   - silicato, marcador de APORTE CONTINENTAL (agua de rio)
#
# `po4` fica de fora porque anda junto com `no3` e a colinearidade ja quebrou os
# coeficientes deste projeto duas vezes (docs/RESULTADOS.md §8 e §12). `nppv` e
# consequencia dos nutrientes, nao causa.
#
# O `si` e o que interessa de verdade: a salinidade deveria detectar agua de rio
# e nao detectou (docs/RESULTADOS.md §15). Silicato pergunta a mesma coisa por
# outro caminho.
QUALIDADE_DA_AGUA = ('clorofila', 'nitrato', 'silicato')

VARIAVEIS_COM_AGUA = (*VARIAVEIS, *QUALIDADE_DA_AGUA)

DATASET_BGC = 'cmems_mod_glo_bgc_my_0.25deg_P1D-m'

# Coluna publicada por cada variavel nossa, no dataset acima.
COLUNAS_EXTRA = {
    'clorofila': 'chl',
    'nitrato': 'no3',
    'silicato': 'si',
}

# Colunas do cache. Formato longo, pelo mesmo motivo de `MedicaoAmbiental`:
# proveniencia por valor.
COLUNAS_CACHE = (
    'Site_ID', 'Date_obs', 'data', 'variavel', 'valor',
    'dataset_id', 'raio_graus', 'n_celulas',
)


class SemCelulaDeOceano(RuntimeError):
    """Nenhuma celula de oceano em volta do ponto, nem no raio maior."""


def _fonte_de(variavel):
    """A fonte de reanalise da variavel. Nao usa produto de analise: ver docstring.

    Procura primeiro nas series do conector (salinidade, oxigenio) e depois nas
    de qualidade da agua, que existem so aqui - ver `QUALIDADE_DA_AGUA`.
    """
    from ingestao.conectores.copernicus import SERIES, FonteCmems

    if variavel in SERIES:
        for fonte in SERIES[variavel]:
            if fonte.tipo == 'reanalise':
                return fonte
        raise ValueError(f'"{variavel}" nao tem produto de reanalise.')

    if variavel in COLUNAS_EXTRA:
        return FonteCmems(DATASET_BGC, COLUNAS_EXTRA[variavel], 'reanalise')

    disponiveis = sorted({*SERIES, *COLUNAS_EXTRA})
    raise ValueError(
        f'Variavel "{variavel}" desconhecida. Disponiveis: {disponiveis}.'
    )


def visitas_de(conjunto):
    """As visitas a extrair, uma linha por (sitio, data)."""
    import pandas as pd

    quadro = conjunto.quadro[
        ['Site_ID', 'Date', 'Latitude_Degrees', 'Longitude_Degrees']
    ].copy()
    quadro['Date'] = pd.to_datetime(quadro['Date']).dt.date
    return quadro.drop_duplicates(subset=['Site_ID', 'Date']).reset_index(drop=True)


def abrir_cobertura(variavel, visitas, margem=0.5):
    """Abre **uma vez** o produto sobre o retangulo que contem todas as visitas.

    Abrir custa ~8 s. Abrir por visita custaria 8 s x 332; abrir uma vez por
    variavel custa 8 s x 2, e as selecoes seguintes saem do mesmo objeto
    preguicoso. Foi medido em 26/07/2026.
    """
    import copernicusmarine

    from ingestao.conectores.copernicus import PROFUNDIDADE_MAX_M

    fonte = _fonte_de(variavel)
    return copernicusmarine.open_dataset(
        dataset_id=fonte.dataset_id,
        variables=[fonte.variavel],
        minimum_longitude=float(visitas['Longitude_Degrees'].min()) - margem,
        maximum_longitude=float(visitas['Longitude_Degrees'].max()) + margem,
        minimum_latitude=float(visitas['Latitude_Degrees'].min()) - margem,
        maximum_latitude=float(visitas['Latitude_Degrees'].max()) + margem,
        minimum_depth=0,
        maximum_depth=PROFUNDIDADE_MAX_M,
    ), fonte


def _recortar(serie, lat, lon, raio):
    return serie.sel(
        latitude=slice(lat - raio, lat + raio),
        longitude=slice(lon - raio, lon + raio),
    )


def mascara_de_oceano(ds, coluna):
    """Um instante basta para saber onde e terra: a mascara nao muda no tempo."""
    return ds[coluna].isel(time=0).squeeze().load()


def raio_util(mascara, lat, lon, raios=RAIOS_BUSCA):
    """O menor raio que contem alguma celula de oceano. Erro se nenhum contiver."""
    for raio in raios:
        if int(_recortar(mascara, lat, lon, raio).notnull().sum()) > 0:
            return raio
    raise SemCelulaDeOceano(
        f'Nenhuma celula de oceano em ({lat:.4f}, {lon:.4f}) ate '
        f'{max(raios)}° de raio.'
    )


def extrair_janela(ds, coluna, mascara, lat, lon, data_obs, dias=DIAS_DA_JANELA,
                   raios=RAIOS_BUSCA):
    """A serie diaria da janela que **termina no dia da visita**.

    A janela inclui o proprio dia da observacao e vai para tras. Olhar um dia
    sequer depois da visita seria vazamento - o mergulhador ja tinha visto o
    coral branco.
    """
    raio = raio_util(mascara, lat, lon, raios)
    inicio = data_obs - timedelta(days=dias)

    recorte = _recortar(ds[coluna], lat, lon, raio).sel(
        time=slice(inicio.isoformat(), data_obs.isoformat())
    )
    dimensoes = [
        d for d in ('latitude', 'longitude', 'depth', 'elevation')
        if d in recorte.dims
    ]
    n_celulas = int(
        _recortar(mascara, lat, lon, raio).notnull().sum()
    )
    if dimensoes:
        recorte = recorte.mean(dim=dimensoes, skipna=True)

    quadro = recorte.to_dataframe().reset_index()
    return quadro, raio, n_celulas


def carregar_cache(caminho=None):
    """O que ja foi extraido. Quadro vazio se o cache nao existe."""
    import pandas as pd

    arquivo = Path(caminho or CAMINHO_CACHE)
    if not arquivo.exists():
        return pd.DataFrame(columns=list(COLUNAS_CACHE))

    quadro = pd.read_csv(arquivo)
    for coluna in ('Date_obs', 'data'):
        quadro[coluna] = pd.to_datetime(quadro[coluna]).dt.date
    return quadro


def _chaves_prontas(cache):
    if cache.empty:
        return set()
    return set(zip(cache['Site_ID'], cache['Date_obs'], cache['variavel']))


@dataclass
class ResultadoExtracao:
    visitas_pedidas: int = 0
    visitas_novas: int = 0
    ja_no_cache: int = 0
    linhas_gravadas: int = 0
    falhas: list = None
    raios_usados: dict = None

    def resumo(self):
        raios = ', '.join(
            f'{raio}°: {n}' for raio, n in sorted((self.raios_usados or {}).items())
        )
        return (
            f'{self.visitas_pedidas} pares (visita, variavel) pedidos: '
            f'{self.visitas_novas} extraidos, {self.ja_no_cache} ja no cache, '
            f'{len(self.falhas or [])} falharam. '
            f'{self.linhas_gravadas} linhas gravadas. Raios: {raios}'
        )


def extrair(conjunto, caminho=None, variaveis=VARIAVEIS, dias=DIAS_DA_JANELA,
            limite=None, ao_progredir=None):
    """Extrai as janelas que faltam e as acrescenta ao cache.

    **Grava a cada visita concluida.** A extracao inteira leva alguns minutos e
    depende de rede; perder tudo por uma queda no meio seria desnecessario. Uma
    segunda execucao continua de onde parou, porque o cache e consultado por
    (sitio, data, variavel).
    """
    import pandas as pd

    arquivo = Path(caminho or CAMINHO_CACHE)
    cache = carregar_cache(arquivo)
    prontas = _chaves_prontas(cache)

    visitas = visitas_de(conjunto)
    if limite:
        visitas = visitas.head(limite)

    resultado = ResultadoExtracao(falhas=[], raios_usados={})
    resultado.visitas_pedidas = len(visitas) * len(variaveis)

    arquivo.parent.mkdir(parents=True, exist_ok=True)
    escreveu_cabecalho = arquivo.exists()

    for variavel in variaveis:
        pendentes = [
            v for v in visitas.itertuples()
            if (v.Site_ID, v.Date, variavel) not in prontas
        ]
        resultado.ja_no_cache += len(visitas) - len(pendentes)
        if not pendentes:
            continue

        ds, fonte = abrir_cobertura(variavel, visitas)
        mascara = mascara_de_oceano(ds, fonte.variavel)

        for indice, visita in enumerate(pendentes, start=1):
            try:
                quadro, raio, n_celulas = extrair_janela(
                    ds, fonte.variavel, mascara,
                    visita.Latitude_Degrees, visita.Longitude_Degrees,
                    visita.Date, dias,
                )
            except Exception as erro:
                resultado.falhas.append(
                    (visita.Site_ID, visita.Date, variavel, str(erro)[:200])
                )
                logger.warning(
                    'Falha em %s/%s (%s): %s',
                    visita.Site_ID, visita.Date, variavel, erro,
                )
                continue

            linhas = pd.DataFrame({
                'Site_ID': visita.Site_ID,
                'Date_obs': visita.Date,
                'data': pd.to_datetime(quadro['time']).dt.date,
                'variavel': variavel,
                'valor': quadro[fonte.variavel].astype(float),
                'dataset_id': fonte.dataset_id,
                'raio_graus': raio,
                'n_celulas': n_celulas,
            })[list(COLUNAS_CACHE)]

            linhas.to_csv(
                arquivo, mode='a', header=not escreveu_cabecalho, index=False,
            )
            escreveu_cabecalho = True

            resultado.visitas_novas += 1
            resultado.linhas_gravadas += len(linhas)
            resultado.raios_usados[raio] = resultado.raios_usados.get(raio, 0) + 1

            if ao_progredir:
                ao_progredir(variavel, indice, len(pendentes), visita, raio)

    return resultado


# ---------------------------------------------------------------------------
# Da janela diaria para features
# ---------------------------------------------------------------------------

# Uma media e uma trajetoria por variavel, e so.
#
# A entrega 1 aprendeu duas vezes que janelas demais sobre a mesma variavel
# viram a mesma coluna (`dhw_variacao_7d` x `dhw_variacao_14d`, r = 0,976) e
# quebram a interpretacao dos coeficientes. Com 166 visitas, quatro features
# novas sobre tres termicas ja e o limite defensavel.
#
# `media` responde "como estava o ambiente no trimestre"; `variacao` responde
# "para onde ele ia" - a mesma distincao que fez a entrega 1 funcionar
# (docs/RESULTADOS.md §3).
RESUMOS = ('media', 'variacao')


def _resumir_serie(valores, resumo):
    """`valores` ja vem ordenado por data."""
    limpos = valores.dropna()
    if limpos.empty:
        return None
    if resumo == 'media':
        return float(limpos.mean())
    if resumo == 'variacao':
        # Ultimo menos primeiro: a trajetoria ao longo da janela.
        return float(limpos.iloc[-1] - limpos.iloc[0])
    if resumo == 'minimo':
        return float(limpos.min())
    if resumo == 'maximo':
        return float(limpos.max())
    if resumo == 'desvio':
        return float(limpos.std())
    raise ValueError(f'Resumo "{resumo}" desconhecido.')


def nome_da_feature(variavel, resumo, dias=DIAS_DA_JANELA):
    return f'{variavel}_{resumo}_{dias}d'


def resumir(cache, variaveis=VARIAVEIS, resumos=RESUMOS, dias=DIAS_DA_JANELA):
    """Janela diaria -> uma linha por visita, com as features resumidas."""
    import pandas as pd

    if cache.empty:
        return pd.DataFrame(columns=['Site_ID', 'Date_obs'])

    ordenado = cache.sort_values(['Site_ID', 'Date_obs', 'variavel', 'data'])
    linhas = {}
    cobertura = {}

    for (sitio, data_obs, variavel), grupo in ordenado.groupby(
        ['Site_ID', 'Date_obs', 'variavel'], sort=False
    ):
        if variavel not in variaveis:
            continue
        chave = (sitio, data_obs)
        linhas.setdefault(chave, {})
        for resumo in resumos:
            linhas[chave][nome_da_feature(variavel, resumo, dias)] = (
                _resumir_serie(grupo['valor'], resumo)
            )
        # Guardado para o relatorio: uma janela com 40 de 91 dias nao vale o
        # mesmo que uma completa, e isso precisa ser visivel.
        cobertura.setdefault(chave, {})[variavel] = int(grupo['valor'].notna().sum())
        linhas[chave][f'{variavel}_raio_graus'] = float(grupo['raio_graus'].iloc[0])

    registros = []
    for (sitio, data_obs), valores in linhas.items():
        registro = {'Site_ID': sitio, 'Date_obs': data_obs, **valores}
        for variavel, n in cobertura[(sitio, data_obs)].items():
            registro[f'{variavel}_dias_validos'] = n
        registros.append(registro)

    return pd.DataFrame(registros)


def features_de(variaveis=VARIAVEIS, resumos=RESUMOS, dias=DIAS_DA_JANELA):
    """Os nomes das colunas que `resumir` produz, na ordem."""
    return tuple(
        nome_da_feature(v, r, dias) for v in variaveis for r in resumos
    )


def juntar(conjunto, cache=None, caminho=None, variaveis=VARIAVEIS,
           resumos=RESUMOS, dias=DIAS_DA_JANELA, features_termicas=None):
    """Devolve um `ConjuntoGCBD` com as features ambientais acrescentadas.

    Visita sem janela ambiental completa e **descartada**, nunca preenchida.
    Imputar salinidade por media seria inventar a variavel cujo efeito o
    experimento quer medir - o defeito exato do `carregar_historico.py` legado.
    """
    import pandas as pd

    from . import gcbd

    if cache is None:
        cache = carregar_cache(caminho)

    resumido = resumir(cache, variaveis, resumos, dias)
    novas = list(features_de(variaveis, resumos, dias))

    quadro = conjunto.quadro.copy()
    quadro['Date_obs'] = pd.to_datetime(quadro['Date']).dt.date

    juntado = quadro.merge(resumido, on=['Site_ID', 'Date_obs'], how='left')

    # Uma feature que nao existe no cache tem que virar coluna vazia, e nao
    # sumir: sem isso, um cache incompleto faria `dropna` levantar KeyError em
    # vez de descartar a visita — falharia em vez de reportar cobertura zero.
    for nome in novas:
        if nome not in juntado.columns:
            juntado[nome] = pd.NA

    antes = len(juntado)
    juntado = juntado.dropna(subset=novas)
    perdidas = antes - len(juntado)

    termicas = tuple(
        conjunto.features if features_termicas is None else features_termicas
    )

    return gcbd.ConjuntoGCBD(
        quadro=juntado.reset_index(drop=True),
        features=(*termicas, *novas),
        limiar=conjunto.limiar,
        linhas_originais=conjunto.linhas_originais,
        visitas=conjunto.visitas,
        descartadas_sem_feature=conjunto.descartadas_sem_feature + perdidas,
        sentinelas_trocadas=conjunto.sentinelas_trocadas,
    )
