"""Validacao de faixa fisica das medicoes.

Regra central, herdada do defeito que este pipeline substitui: um valor
reprovado vira **NULL com flag**, nunca zero. O `carregar_historico.py`
preenchia lacunas com `.fillna(0)`, gravando pH 0 e salinidade 0 - valores
fisicamente impossiveis que iam direto para o modelo.

Faixas conforme backend/docs/contrato_canonico_variaveis.md.
"""

from dataclasses import dataclass

# variavel -> (minimo aceitavel, maximo aceitavel)
# Fora desta faixa o valor e fisicamente impossivel: vira NULL/invalido.
FAIXAS_VALIDAS = {
    'sst': (-2.0, 45.0),
    'dhw': (0.0, 40.0),
    'baa': (0.0, 5.0),
    'baa_area_alerta': (0.0, 1.0),
    'hotspot': (-10.0, 10.0),
    'sst_anomalia': (-8.0, 8.0),
    'salinidade': (0.0, 45.0),
    'oxigenio': (0.0, 600.0),
    'kd490': (0.0, 5.0),
    'clorofila': (0.0, 100.0),
    'par': (0.0, 3000.0),
}

# Faixa esperada em condicao normal. Fora dela o valor e plausivel mas
# suspeito: entra como 'degradado', com o valor preservado.
FAIXAS_ESPERADAS = {
    'sst': (15.0, 35.0),
    'salinidade': (30.0, 40.0),
    'oxigenio': (100.0, 350.0),
    'kd490': (0.0, 1.0),
}


@dataclass(frozen=True)
class ResultadoValidacao:
    valor: float | None
    quality_flag: str
    observacao: str

    @property
    def aprovado(self):
        return self.quality_flag != 'invalido'


def validar(variavel, valor, quality_flag='ok', observacao=''):
    """Aplica a validacao fisica a um valor ja normalizado."""
    if valor is None:
        return ResultadoValidacao(None, 'invalido', 'Valor ausente na fonte.')

    faixa = FAIXAS_VALIDAS.get(variavel)
    if faixa is not None:
        minimo, maximo = faixa
        if not (minimo <= valor <= maximo):
            return ResultadoValidacao(
                None,
                'invalido',
                (
                    f'{valor} fora da faixa fisicamente possivel de {variavel} '
                    f'[{minimo}, {maximo}]. Gravado como nulo, nao como zero.'
                ),
            )

    esperada = FAIXAS_ESPERADAS.get(variavel)
    if esperada is not None:
        minimo, maximo = esperada
        if not (minimo <= valor <= maximo):
            aviso = (
                f'{valor} fora da faixa esperada de {variavel} '
                f'[{minimo}, {maximo}] - plausivel, mas conferir.'
            )
            return ResultadoValidacao(
                valor,
                'degradado',
                (observacao + ' ' + aviso).strip(),
            )

    return ResultadoValidacao(valor, quality_flag, observacao)


def detectar_saltos(serie, variavel, limite_diario=None):
    """Sinaliza saltos diarios implausiveis numa serie ordenada por data.

    `serie` e uma lista de (data, valor). Retorna o conjunto de datas
    suspeitas. O contrato preve salto > 5 °C/dia para SST.
    """
    limites_padrao = {'sst': 5.0, 'salinidade': 5.0}
    limite = limite_diario or limites_padrao.get(variavel)
    if limite is None:
        return set()

    suspeitas = set()
    anterior = None
    for data, valor in sorted(serie):
        if valor is None:
            anterior = None
            continue
        if anterior is not None and abs(valor - anterior[1]) > limite:
            if (data - anterior[0]).days <= 1:
                suspeitas.add(data)
        anterior = (data, valor)

    return suspeitas
