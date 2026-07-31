/**
 * A serie ambiental de um recife, para desenhar na tela.
 *
 * 🚨 **O que esta tela mostra e dado observado, nao previsao.** A distincao e a
 * mesma que as figuras do TCC precisaram tornar explicita: a previsao do
 * projeto vive no painel de risco, sai do modelo e fala do futuro; isto aqui e
 * o que o satelite mediu, e fala do passado. Sao duas coisas na mesma pagina, e
 * quem le tem direito a saber qual esta olhando.
 *
 * ⚠️ **`valor` nulo nao e zero.** A API devolve nulo quando a validacao fisica
 * reprovou a medida, e `observacao` diz por que. Aqui isso vira **buraco na
 * linha**, nunca um ponto no eixo — desenhar zero seria repetir no grafico o
 * defeito que o pipeline legado cometia no banco.
 */

// 🚨 As duas variaveis do grafico, e o motivo de serem exatamente estas duas.
//
// `sst` e o que qualquer pessoa entende sem explicacao, e `dhw` e o que decide
// o alerta — a permutacao mediu queda de PR-AUC de 0,30 a 0,84 ao embaralha-lo,
// contra ~0,00 de salinidade e oxigenio (docs/RESULTADOS.md secao 7). Por o
// resto no mesmo grafico daria peso visual igual a variaveis que nao pesam.
export const VARIAVEIS_DA_SERIE = ['sst', 'dhw'];

export const DIAS_EXIBIDOS = 365;

// O corte da NOAA para Alerta Nivel 1. Fica marcado no painel do DHW porque
// sem ele a curva e um numero sem regua: "3,8" nao diz nada, "3,8 quase no 4"
// diz tudo.
export const CORTE_ALERTA_DHW = 4;

export const ROTULOS = {
  sst: { nome: 'Temperatura da superficie', unidade: '°C', casas: 1 },
  dhw: { nome: 'Calor acumulado (DHW)', unidade: '°C·semana', casas: 1 },
};

function dataDeCorte(dias, hoje = new Date()) {
  const corte = new Date(hoje);
  corte.setDate(corte.getDate() - dias);
  return corte.toISOString().slice(0, 10);
}

export function montarConsulta(slug, { dias = DIAS_EXIBIDOS, hoje } = {}) {
  const parametros = new URLSearchParams();
  parametros.set('local', slug);
  VARIAVEIS_DA_SERIE.forEach((v) => parametros.append('variavel', v));
  parametros.set('de', dataDeCorte(dias, hoje));
  // Um ano de duas variaveis sao ~730 pontos. O teto do servidor e 1000, e
  // pedir o teto inteiro deixa a folga visivel em vez de implicita.
  parametros.set('page_size', '1000');
  return `/api/medicoes/?${parametros.toString()}`;
}

export function urlDeDownload(slug) {
  const parametros = new URLSearchParams();
  parametros.set('local', slug);
  parametros.set('formato', 'csv');
  return `/api/medicoes/?${parametros.toString()}`;
}

/**
 * Registros crus -> uma serie por variavel, em ordem cronologica.
 *
 * Devolve `{ series, periodo, fontes, total, reprovadas }`. `reprovadas` nao e
 * detalhe: e quantas medidas a validacao fisica recusou no periodo, e some da
 * curva sem deixar rastro se ninguem a contar.
 */
export function organizarSerie(registros) {
  const series = {};
  const fontes = new Set();
  let reprovadas = 0;
  let inicio = null;
  let fim = null;

  (Array.isArray(registros) ? registros : []).forEach((registro) => {
    if (!registro || !VARIAVEIS_DA_SERIE.includes(registro.variavel)) {
      return;
    }

    const valor = registro.valor === null || registro.valor === undefined
      ? null
      : Number(registro.valor);

    if (valor === null || !Number.isFinite(valor)) {
      reprovadas += 1;
    }
    if (registro.fonte) {
      fontes.add(registro.fonte);
    }
    if (!inicio || registro.data < inicio) {
      inicio = registro.data;
    }
    if (!fim || registro.data > fim) {
      fim = registro.data;
    }

    series[registro.variavel] = series[registro.variavel] || [];
    series[registro.variavel].push({
      data: registro.data,
      valor: Number.isFinite(valor) ? valor : null,
      observacao: registro.observacao || null,
    });
  });

  Object.values(series).forEach((pontos) => {
    pontos.sort((a, b) => (a.data < b.data ? -1 : 1));
  });

  return {
    series,
    periodo: inicio && fim ? { inicio, fim } : null,
    fontes: [...fontes].sort(),
    total: Object.values(series).reduce((soma, p) => soma + p.length, 0),
    reprovadas,
  };
}

/**
 * Busca a serie de um recife.
 *
 * Mesmo contrato de `painelRisco.buscarPredicao`: devolve `{ estado, ... }` em
 * vez de lancar, porque cada estado tem uma tela diferente e transformar
 * "ainda nao ha serie" em erro generico esconderia a informacao util.
 *
 * ⚠️ `truncada` existe porque a resposta e paginada. Se a serie do periodo
 * passar do teto, o grafico estaria desenhando **parte** do recorte pedido
 * enquanto anuncia o recorte inteiro — e ninguem perceberia olhando a curva.
 */
export async function buscarSerie(slug, opcoes = {}) {
  if (typeof fetch !== 'function' || !slug) {
    return { estado: 'indisponivel' };
  }

  try {
    const resposta = await fetch(montarConsulta(slug, opcoes));
    if (resposta.status === 503) {
      return { estado: 'offline' };
    }
    if (!resposta.ok) {
      return { estado: 'indisponivel' };
    }

    const corpo = await resposta.json();
    const registros = Array.isArray(corpo?.results) ? corpo.results : [];
    if (!registros.length) {
      return { estado: 'sem-serie' };
    }

    return {
      estado: 'ok',
      ...organizarSerie(registros),
      truncada: Number(corpo?.count) > registros.length,
    };
  } catch (erro) {
    return { estado: 'indisponivel' };
  }
}
