"""Material para escolher o limiar de alerta.

O limiar nao e propriedade do modelo. O modelo devolve **probabilidade**; o
limiar e a linha a partir da qual o site avisa, e essa linha e uma decisao de
operacao: quanto alarme falso se aceita para nao perder evento.

Ate 27/07/2026 o projeto operou em 0,50 **sem nunca ter escolhido**. O numero
veio do padrao do `predict`, e ainda por cima nao significava o que aparentava:
`class_weight='balanced'` empurrava a probabilidade para cima, entao aquele
0,50 se comportava como um corte bem mais baixo (docs/RESULTADOS.md secao 22.5).

🚨 **Este modulo nao escolhe.** Ele mede a troca e a traduz para unidades que
dao para decidir — alertas por ano, alarmes falsos por ano, episodios perdidos.
"Precisao 0,705" nao e uma frase sobre a qual alguem consiga formar opiniao;
"dois alarmes falsos por ano em cada recife" e.

⚠️ **Vies de selecao, declarado.** As metricas saem das predicoes fora da
dobra — cada amostra prevista por um modelo que nao a viu —, o que e o certo
para comparar limiares entre si. Mas o limiar escolhido olhando esta tabela
tende a parecer melhor aqui do que sera no ano que vem, porque foi escolhido
sobre estes mesmos dados. Mesma ressalva das secoes 12.3 e 22.5.

**Por que a contagem de episodios importa mais que a de dias.** Um episodio de
branqueamento dura semanas. Perder o dia exato do inicio custa pouco; perder o
episodio inteiro custa tudo. Um limiar pode ter revocacao de dias mediocre e
ainda assim pegar **todos** os eventos, porque basta acertar um dia de cada.
"""

from dataclasses import dataclass

# Faixa varrida por padrao. Comeca em 0,05 porque abaixo disso o alerta e
# praticamente permanente, e para em 0,95 porque acima disso ele quase nunca
# dispara — os dois extremos existem na tabela para mostrar o formato da troca,
# nao como candidatos serios.
LIMIARES_PADRAO = tuple(round(0.05 * n, 2) for n in range(1, 20))


@dataclass(frozen=True)
class Ponto:
    """O que acontece num limiar: os quatro numeros da matriz de confusao.

    Guardar a matriz inteira, e nao so precisao e revocacao, e o que permite
    responder as perguntas operacionais depois — elas precisam de contagens
    absolutas, nao de razoes.
    """

    limiar: float
    verdadeiros_positivos: int
    falsos_positivos: int
    falsos_negativos: int
    verdadeiros_negativos: int
    episodios_reais: int = 0
    episodios_detectados: int = 0
    episodios_falsos: int = 0
    # Quais episodios escaparam, e nao apenas quantos. E o que transforma
    # "perde 3 de 19" numa frase sobre a qual da para ter opiniao: um evento de
    # nove dias em Picaozinho pesa diferente de um de um dia so.
    perdidos: tuple = ()

    # 🚨 Quando o aviso chega, e nao apenas se chega.
    #
    # Sem isto a tabela mente por omissao. Entre 0,15 e 0,40 a contagem de
    # episodios nao se move, o que sugere que apertar o limiar sai de graca —
    # e nao sai: o aviso passa a chegar **mais tarde dentro do mesmo
    # episodio**. Medido em 27/07/2026: de 0,20 para 0,30 o atraso medio do
    # primeiro aviso vai de 1,50 para 2,60 dias, e tres episodios deixam de
    # ser avisados ja no primeiro dia.
    #
    # Para um sistema de aviso, avisar no terceiro dia de um evento de nove e
    # bem diferente de avisar no primeiro, ainda que os dois contem como
    # "detectado".
    episodios_no_primeiro_dia: int = 0
    atraso_medio_dias: float = 0.0

    @property
    def n(self):
        return (
            self.verdadeiros_positivos + self.falsos_positivos
            + self.falsos_negativos + self.verdadeiros_negativos
        )

    @property
    def alertas(self):
        """Dias em que o site avisaria."""
        return self.verdadeiros_positivos + self.falsos_positivos

    @property
    def precisao(self):
        return self.verdadeiros_positivos / self.alertas if self.alertas else 0.0

    @property
    def revocacao(self):
        reais = self.verdadeiros_positivos + self.falsos_negativos
        return self.verdadeiros_positivos / reais if reais else 0.0

    @property
    def f1(self):
        soma = self.precisao + self.revocacao
        return 2 * self.precisao * self.revocacao / soma if soma else 0.0

    @property
    def episodios_perdidos(self):
        return self.episodios_reais - self.episodios_detectados

    def por_ano(self, anos, locais=1):
        """Traduz as contagens para "por ano, por recife".

        E a unidade em que a decisao existe de fato: ninguem opera um site
        pensando em "falsos positivos por amostra".
        """
        divisor = anos * locais
        if divisor <= 0:
            return {}
        return {
            'dias_em_alerta': self.alertas / divisor,
            'dias_de_alarme_falso': self.falsos_positivos / divisor,
            'dias_de_evento_perdidos': self.falsos_negativos / divisor,
            'episodios_falsos': self.episodios_falsos / divisor,
        }


@dataclass(frozen=True)
class Varredura:
    """A tabela inteira, mais o contexto que da sentido a ela."""

    pontos: tuple
    n: int
    positivos: int
    anos: int
    locais: int

    @property
    def taxa_base(self):
        return self.positivos / self.n if self.n else 0.0

    def em(self, limiar):
        for ponto in self.pontos:
            if abs(ponto.limiar - limiar) < 1e-9:
                return ponto
        return None

    def melhor_f1(self):
        return max(self.pontos, key=lambda p: p.f1) if self.pontos else None

    def sem_perder_episodio(self):
        """O limiar mais alto que ainda detecta **todos** os episodios.

        E o candidato natural para quem trata evento perdido como inaceitavel.

        ⚠️ Pode nao existir — e na medicao de 27/07/2026 **nao existe**: um
        episodio de Picaozinho escapa em **todos** os limiares varridos. Quando
        isso acontece, o resultado nao e "aperte mais": e que o teto nao esta na
        escolha do limiar, e sim no modelo. Ver `melhor_cobertura`.
        """
        completos = [
            p for p in self.pontos
            if p.episodios_reais and p.episodios_detectados == p.episodios_reais
        ]
        return max(completos, key=lambda p: p.limiar) if completos else None

    def melhor_cobertura(self):
        """O limiar mais alto entre os que detectam o **maximo** de episodios.

        Serve quando nenhum limiar pega todos: responde "ate onde da para ir".
        Escolher o mais alto entre os empatados nao e detalhe — entre dois
        limiares que perdem os mesmos eventos, o mais alto custa menos alarme
        falso, entao o mais baixo seria dominado.
        """
        if not self.pontos:
            return None
        teto = max(p.episodios_detectados for p in self.pontos)
        empatados = [p for p in self.pontos if p.episodios_detectados == teto]
        return max(empatados, key=lambda p: p.limiar)

    def nunca_detectados(self):
        """Episodios que escapam em **todos** os limiares varridos.

        Sao os que nenhuma escolha de limiar resolve. Separa-los do resto e o
        que impede a discussao de virar "e so baixar o corte".
        """
        if not self.pontos:
            return ()

        def chave(e):
            return (e['local'], e['inicio'], e['fim'])

        conjuntos = [{chave(e) for e in p.perdidos} for p in self.pontos]
        sempre = set.intersection(*conjuntos) if conjuntos else set()

        return tuple(sorted(
            (e for e in self.pontos[0].perdidos if chave(e) in sempre),
            key=lambda e: (e['local'], e['inicio']),
        ))


def atraso_do_aviso(quadro, probabilidade, limiar):
    """Quantos dias depois do inicio do episodio o primeiro aviso sai.

    Devolve `(episodios_avisados, avisados_no_primeiro_dia, atraso_medio)`.

    ⚠️ **A contagem de episodios aqui difere da de `avaliar_episodios`**, e a
    diferenca e proposital, nao um desencontro. Ali, dois trechos separados por
    poucos dias sao fundidos num evento so (`folga_dias`), porque a pergunta e
    "o sistema percebeu este evento?". Aqui cada corrida contigua de dias em
    alerta e contada por si, porque a pergunta e "quando o aviso chegou?" — e
    fundir trechos deslocaria o inicio para tras, inflando o atraso.

    Na medicao de 27/07/2026 sao **20** corridas contiguas contra **19**
    episodios com folga.
    """
    corridas = []

    grupos = (
        quadro.groupby('local') if 'local' in quadro.columns
        else [('', quadro)]
    )

    for _, parte in grupos:
        parte = parte.sort_values('alvo_data')
        real = (parte['alvo'] >= _limiar_alerta()).to_numpy()
        datas = list(parte['alvo_data'])
        avisado = (probabilidade.loc[parte.index] >= limiar).to_numpy()

        inicio = None
        for i, ativo in enumerate(real):
            if ativo and inicio is None:
                inicio = i
            if inicio is not None and (not ativo or i == len(real) - 1):
                fim = i if ativo else i - 1
                corridas.append((datas[inicio:fim + 1], avisado[inicio:fim + 1]))
                inicio = None

    atrasos = []
    for datas, avisos in corridas:
        posicoes = [n for n, marcado in enumerate(avisos) if marcado]
        if posicoes:
            atrasos.append((datas[posicoes[0]] - datas[0]).days)

    if not atrasos:
        return 0, 0, 0.0

    return (
        len(atrasos),
        sum(1 for a in atrasos if a == 0),
        sum(atrasos) / len(atrasos),
    )


def _limiar_alerta():
    from ingestao.conectores.noaa_crw import LIMIAR_ALERTA

    return LIMIAR_ALERTA


def _matriz(verdadeiro, probabilidade, limiar):
    previsto = probabilidade >= limiar
    real = verdadeiro.astype(bool)

    return (
        int((previsto & real).sum()),
        int((previsto & ~real).sum()),
        int((~previsto & real).sum()),
        int((~previsto & ~real).sum()),
    )


def varrer(conjunto, nome='logistica', semente=42, calibrar='isotonic',
           limiares=LIMIARES_PADRAO):
    """Mede cada limiar sobre as predicoes **fora da dobra**.

    ⚠️ `calibrar='isotonic'` e o padrao de proposito: e o que o artefato
    servido usa. Varrer limiares sobre a probabilidade crua produziria uma
    tabela correta e **inutil**, porque descreve um modelo que nao esta no ar.
    """
    import numpy as np

    from .baseline import avaliar_episodios
    from .calibracao import predicoes_fora_da_dobra
    from .modelo import como_baa

    y, p = predicoes_fora_da_dobra(conjunto, nome, semente, calibrar)
    quadro = conjunto.quadro.loc[y.index]

    anos = len({d.year for d in quadro['alvo_data']})
    locais = (
        quadro['local'].nunique() if 'local' in quadro.columns else 1
    )

    pontos = []
    for limiar in limiares:
        vp, fp, fn, vn = _matriz(y.to_numpy(), p.to_numpy(), limiar)

        # Episodios sobre as mesmas amostras, com a mesma regra do experimento.
        previsto = (p >= limiar).astype(int)
        episodios = avaliar_episodios(quadro, como_baa(previsto))
        _, no_primeiro, atraso = atraso_do_aviso(quadro, p, limiar)

        pontos.append(Ponto(
            limiar=float(limiar),
            verdadeiros_positivos=vp,
            falsos_positivos=fp,
            falsos_negativos=fn,
            verdadeiros_negativos=vn,
            episodios_reais=episodios.episodios_reais,
            episodios_detectados=episodios.episodios_detectados,
            episodios_falsos=episodios.episodios_falsos,
            perdidos=tuple(
                {
                    'local': d['local'],
                    'inicio': d['inicio'],
                    'fim': d['fim'],
                    'dias': (d['fim'] - d['inicio']).days + 1,
                }
                for d in episodios.detalhes
                if not d.get('detectado')
            ),
            episodios_no_primeiro_dia=no_primeiro,
            atraso_medio_dias=atraso,
        ))

    return Varredura(
        pontos=tuple(pontos),
        n=int(len(y)),
        positivos=int(np.asarray(y).sum()),
        anos=anos,
        locais=locais,
    )
