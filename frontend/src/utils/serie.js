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

// 🚨 **Eram duas variaveis ate 16/08/2026, e a razao de serem duas nao era
// falta de dado — era falta de espaco.** O argumento registrado aqui antes era
// que `sst` e `dhw` decidem o alerta (queda de PR-AUC de 0,30 a 0,84 na
// permutacao, contra ~0,00 de salinidade e oxigenio — docs/RESULTADOS.md §7) e
// que por o resto no mesmo grafico daria "peso visual igual a variaveis que nao
// pesam". O problema era o *mesmo grafico*: num eixo so, o oxigenio varia
// +-5 mmol/m3 e a temperatura +-1 C, entao uma curva engole as outras. Com um
// painel por variavel — que e como `ml/graficos.py::linha_do_tempo` sempre
// desenhou as figuras do TCC — o argumento cai: cada uma tem seu proprio eixo,
// na sua propria unidade, e nenhuma esconde nenhuma. As quatro sao as mesmas
// que o modelo consome (`ml/dataset.py::VARIAVEIS_BASELINE`).
export const VARIAVEIS_DA_SERIE = ['sst', 'dhw', 'salinidade', 'oxigenio'];

// 🚨 O `baa` **nao vira painel** — vira as faixas rosa por tras dos quatro.
// E o que aconteceu (a NOAA emitiu alerta), e nao uma medida ambiental que se
// leia numa curva. Sem ele o grafico responderia "o que o satelite mediu" sem
// nunca dizer "e ai, deu alerta?".
export const VARIAVEL_DO_ALERTA = 'baa';

// Nivel 1 da NOAA na escala Bleaching Alert Area (0-5). E o mesmo corte que
// `ml/dataset.py` usa para montar o alvo do modelo.
export const CORTE_ALERTA_BAA = 3;

const VARIAVEIS_CONSULTADAS = [...VARIAVEIS_DA_SERIE, VARIAVEL_DO_ALERTA];

export const DIAS_EXIBIDOS = 365;

// O corte da NOAA para Alerta Nivel 1 em DHW. Fica marcado no painel do DHW
// porque sem ele a curva e um numero sem regua: "3,8" nao diz nada, "3,8 quase
// no 4" diz tudo.
export const CORTE_ALERTA_DHW = 4;

export const ROTULOS = {
  sst: { nome: 'Temperatura da superficie', unidade: '°C', casas: 1 },
  dhw: { nome: 'Calor acumulado (DHW)', unidade: '°C·semana', casas: 1 },
  salinidade: { nome: 'Salinidade', unidade: 'PSU', casas: 2 },
  oxigenio: { nome: 'Oxigenio dissolvido', unidade: 'mmol/m³', casas: 1 },
  baa: { nome: 'Alerta de branqueamento (NOAA)', unidade: '0-5', casas: 0 },
};

function dataDeCorte(dias, hoje = new Date()) {
  const corte = new Date(hoje);
  corte.setDate(corte.getDate() - dias);
  return corte.toISOString().slice(0, 10);
}

/**
 * 🚨 **Uma variavel por requisicao, e isso nao e desperdicio.**
 * `DRF_MAX_PAGE_SIZE` e 1000 (settings.py). Um ano das cinco variaveis sao
 * ~1825 pontos: pedidas juntas, a resposta vem cortada e o grafico desenharia
 * **parte** do periodo anunciando o periodo inteiro. Separadas, cada uma tem
 * ~365 pontos e sobra folga; de quebra, um recife sem salinidade perde so o
 * painel dela, em vez de contaminar a resposta das outras quatro.
 */
export function montarConsulta(slug, { variaveis = VARIAVEIS_CONSULTADAS, dias = DIAS_EXIBIDOS, hoje } = {}) {
  const parametros = new URLSearchParams();
  parametros.set('local', slug);
  variaveis.forEach((v) => parametros.append('variavel', v));
  parametros.set('de', dataDeCorte(dias, hoje));
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
    if (!registro || !VARIAVEIS_CONSULTADAS.includes(registro.variavel)) {
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
 * Os trechos em que a NOAA de fato manteve alerta, para virarem faixa no fundo.
 *
 * ⚠️ **Nao e o alvo do modelo, e a diferenca sao 7 dias.**
 * `ml/graficos.py::linha_do_tempo` pinta `baa >= 3` **em t+7**, porque ali a
 * faixa serve para julgar uma previsao com 7 dias de antecedencia. Aqui a
 * secao e "a serie medida": a faixa marca os dias em que o alerta **estava
 * valendo**, que e o que alguem lendo dado observado espera. Mesma fonte,
 * pergunta diferente.
 *
 * Valor nulo interrompe a faixa em vez de estende-la: sem medida nao ha como
 * afirmar que havia alerta.
 */
export function intervalosDeAlerta(pontos, corte = CORTE_ALERTA_BAA) {
  const intervalos = [];
  let abertura = null;
  let anterior = null;

  (Array.isArray(pontos) ? pontos : []).forEach((ponto) => {
    const emAlerta = Number.isFinite(ponto?.valor) && ponto.valor >= corte;

    if (emAlerta && abertura === null) {
      abertura = ponto.data;
    }
    if (!emAlerta && abertura !== null) {
      intervalos.push({ inicio: abertura, fim: anterior });
      abertura = null;
    }
    if (emAlerta) {
      anterior = ponto.data;
    }
  });

  if (abertura !== null) {
    intervalos.push({ inicio: abertura, fim: anterior });
  }

  return intervalos;
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
    const respostas = await Promise.all(
      VARIAVEIS_CONSULTADAS.map((variavel) =>
        fetch(montarConsulta(slug, { ...opcoes, variaveis: [variavel] })),
      ),
    );

    if (respostas.some((r) => r.status === 503)) {
      return { estado: 'offline' };
    }
    // 🚨 Uma variavel que falha nao invalida as outras — mas uma que falha
    // **sem ninguem notar** viraria painel vazio indistinguivel de "este
    // recife nao mede isso". So desiste se nenhuma das cinco respondeu.
    const boas = respostas.filter((r) => r.ok);
    if (!boas.length) {
      return { estado: 'indisponivel' };
    }

    const corpos = await Promise.all(boas.map((r) => r.json()));
    const registros = corpos.flatMap((corpo) =>
      Array.isArray(corpo?.results) ? corpo.results : [],
    );
    if (!registros.length) {
      return { estado: 'sem-serie' };
    }

    const organizada = organizarSerie(registros);
    const truncada = corpos.some(
      (corpo) => Number(corpo?.count) > (corpo?.results?.length || 0),
    );

    return {
      estado: 'ok',
      ...organizada,
      alertas: intervalosDeAlerta(organizada.series[VARIAVEL_DO_ALERTA] || []),
      truncada,
    };
  } catch (erro) {
    return { estado: 'indisponivel' };
  }
}
