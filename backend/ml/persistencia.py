"""Grava e carrega o modelo treinado.

Ate 27/07/2026 **nenhum modelo era salvo**: `treinar_modelo` e `treinar_gcbd`
liam os dados, aprendiam, mediam e descartavam. Isso esta certo para *medir* -
a validacao treina um modelo por dobra e usa cada um so fora dela, entao nunca
existe "o modelo", existem cinco parciais e uma metrica.

Mas o painel precisa de um artefato para carregar. Este modulo cobre a
diferenca: treina **uma vez sobre todos os dados** e grava o resultado.

⚠️ **Tres decisoes aqui nao sao obvias.**

**1. O artefato e derivado, e nao versionado.** Vai para `dados/modelos/`, que
ja esta no `.gitignore`. Um `.joblib` no repositorio envelhece em silencio: em
duas semanas o arquivo diz uma coisa e o codigo diz outra, e ninguem sabe qual
vale. Mesma decisao ja tomada para o `.docx` da documentacao e para a projecao
do Neo4j. O comando reconstroi.

**2. Os metadados viajam ao lado, em JSON legivel.** Se so o `.joblib` existir,
ninguem consegue responder "este modelo foi treinado com quais colunas, sobre
quantas amostras, em que data" sem carregar o pickle - e carregar e justamente
o que se quer evitar antes de saber o que e.

**3. 🚨 Carregar `joblib` executa codigo.** `joblib.load` desserializa via
`pickle`, e pickle e capaz de executar qualquer coisa durante a leitura. Isso
nao e problema para um arquivo que este projeto acabou de gerar, e **e problema
serio** para um arquivo vindo de fora. Por isso `carregar` le o JSON primeiro,
confere a origem e a versao do scikit-learn, e recusa o que nao reconhece. Ver
`ArtefatoIncompativel`.

A versao do scikit-learn importa por um motivo pratico alem da seguranca: o
pickle de um `Pipeline` nao tem compatibilidade garantida entre versoes, e a
falha costuma ser silenciosa - o objeto carrega e preve errado.
"""

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[2]
PASTA_PADRAO = RAIZ / 'dados' / 'modelos'

# Marca de origem. Um arquivo sem isto nao foi gerado por este projeto.
ASSINATURA = 'coral-brasil/ml'
FORMATO = 1


class ArtefatoAusente(FileNotFoundError):
    """O modelo pedido nao existe no disco."""


class ArtefatoIncompativel(ValueError):
    """O artefato existe mas nao pode ser usado como esta."""


def _caminhos(nome, pasta=None):
    base = Path(pasta or PASTA_PADRAO)
    return base / f'{nome}.joblib', base / f'{nome}.json'


def _versao_sklearn():
    import sklearn

    return sklearn.__version__


def salvar(ajuste, nome, pasta=None, extras=None):
    """Grava o pipeline e os metadados. Devolve (caminho_modelo, caminho_json)."""
    import joblib

    caminho_modelo, caminho_json = _caminhos(nome, pasta)
    caminho_modelo.parent.mkdir(parents=True, exist_ok=True)

    metadados = {
        'assinatura': ASSINATURA,
        'formato': FORMATO,
        'nome': nome,
        'gerado_em': date.today().isoformat(),
        'sklearn': _versao_sklearn(),
        **ajuste.metadados(),
    }
    if extras:
        metadados.update(extras)

    joblib.dump(ajuste.pipeline, caminho_modelo)
    caminho_json.write_text(
        json.dumps(metadados, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    return caminho_modelo, caminho_json


def ler_metadados(nome, pasta=None):
    """Le o JSON **sem** tocar no pickle.

    E o que permite decidir se vale carregar o modelo - ou se ele e de outro
    projeto, de outro formato, ou treinado com colunas que nao temos.
    """
    _, caminho_json = _caminhos(nome, pasta)
    if not caminho_json.exists():
        raise ArtefatoAusente(
            f'{caminho_json} nao existe. Gere com:\n'
            f'  python backend/manage.py treinar_final'
        )

    metadados = json.loads(caminho_json.read_text(encoding='utf-8'))

    if metadados.get('assinatura') != ASSINATURA:
        raise ArtefatoIncompativel(
            f'{caminho_json} nao foi gerado por este projeto '
            f'(assinatura {metadados.get("assinatura")!r}). '
            f'Carregar joblib executa codigo: recusado.'
        )
    if metadados.get('formato') != FORMATO:
        raise ArtefatoIncompativel(
            f'Formato {metadados.get("formato")} desconhecido '
            f'(este codigo le o {FORMATO}). Regere o artefato.'
        )
    return metadados


def carregar(nome, pasta=None, exigir_mesma_versao=True):
    """Devolve um `Ajuste` pronto para prever. Confere o JSON antes do pickle."""
    import joblib

    from .modelo import Ajuste

    metadados = ler_metadados(nome, pasta)
    caminho_modelo, _ = _caminhos(nome, pasta)
    if not caminho_modelo.exists():
        raise ArtefatoAusente(
            f'{caminho_modelo} nao existe: os metadados estao la e o modelo '
            f'nao. Regere o artefato com "manage.py treinar_final".'
        )

    atual = _versao_sklearn()
    if metadados.get('sklearn') != atual:
        recado = (
            f'O modelo foi gravado com scikit-learn {metadados.get("sklearn")} '
            f'e esta sendo lido com {atual}. O pickle de um Pipeline nao tem '
            f'compatibilidade garantida entre versoes, e a falha costuma ser '
            f'silenciosa: o objeto carrega e preve errado.'
        )
        if exigir_mesma_versao:
            raise ArtefatoIncompativel(recado + ' Regere o artefato.')
        logger.warning(recado)

    return Ajuste(
        pipeline=joblib.load(caminho_modelo),
        nome=metadados['modelo'],
        colunas=tuple(metadados['colunas']),
        horizonte=metadados.get('horizonte_dias', 0),
        n_treino=metadados.get('n_treino', 0),
        positivos_treino=metadados.get('positivos_treino', 0),
        # ⚠️ Sem esta linha o `Ajuste` voltava do disco com `calibracao=None`
        # mesmo quando o artefato era isotonico. O pipeline carregado estava
        # certo — quem mentia era o campo, e ele e justamente o que o painel
        # exibe para dizer se a probabilidade e crua ou recalibrada. A
        # diferenca vale 0,081 de ECE (docs/RESULTADOS.md secao 22).
        calibracao=metadados.get('calibracao'),
    )


def listar(pasta=None):
    """Os modelos disponiveis, com o resumo de cada um."""
    base = Path(pasta or PASTA_PADRAO)
    if not base.exists():
        return []

    encontrados = []
    for arquivo in sorted(base.glob('*.json')):
        try:
            encontrados.append(ler_metadados(arquivo.stem, base))
        except (ArtefatoAusente, ArtefatoIncompativel) as erro:
            encontrados.append({'nome': arquivo.stem, 'erro': str(erro)})
    return encontrados


@dataclass
class Treino:
    """O que foi treinado, para o comando poder relatar."""

    ajuste: object
    conjunto: object
    caminho_modelo: object = None
    caminho_json: object = None

    def resumo(self):
        return (
            f'{self.ajuste.nome}: {self.ajuste.n_treino} amostras, '
            f'{self.ajuste.positivos_treino} positivas '
            f'({self.ajuste.positivos_treino / self.ajuste.n_treino:.1%}), '
            f'{len(self.ajuste.colunas)} colunas'
        )
