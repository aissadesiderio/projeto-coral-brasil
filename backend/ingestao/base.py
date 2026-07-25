"""Contrato que todo conector de fonte externa implementa."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Observacao:
    """Uma leitura bruta, ainda no vocabulario da fonte.

    A traducao para o vocabulario canonico acontece depois, em
    `normalizacao.normalizar` - o conector nao decide nomes nem unidades.
    """

    data: date
    coluna: str
    valor: float | None


@dataclass
class ResultadoColeta:
    """O que um conector devolve para uma janela (local, periodo)."""

    observacoes: list = field(default_factory=list)
    dataset_id: str = ''
    erro: str = ''

    @property
    def houve_falha(self):
        return bool(self.erro)


class ConectorBase(ABC):
    """Base dos conectores.

    Responsabilidade do conector: **falar com a fonte externa e devolver
    leituras brutas**. Ele nao normaliza, nao valida e nao grava - isso e de
    `normalizacao`, `qualidade` e `persistencia`. Manter essa separacao e o
    que permite testar a logica sem rede.

    Um conector nunca deve levantar excecao de rede para cima: falha vira
    `ResultadoColeta(erro=...)`, para que uma fonte fora do ar nao derrube as
    demais.
    """

    slug: str = ''
    nome: str = ''
    url_fonte: str = ''
    variaveis: tuple = ()
    exige_credenciais: bool = False

    @abstractmethod
    def coletar(self, local, inicio, fim):
        """Busca dados de um local num periodo.

        `local` e um `LocalRecife` com coordenadas. Retorna `ResultadoColeta`.
        """

    def verificar_local(self, local):
        """Recusa locais sem coordenadas em vez de inventar uma bbox."""
        if not local.tem_coordenadas:
            raise ValueError(
                f'{local.slug} nao tem latitude/longitude - fora do pipeline. '
                'Preencha as coordenadas no admin antes de ingerir.'
            )
        return local.bbox()
