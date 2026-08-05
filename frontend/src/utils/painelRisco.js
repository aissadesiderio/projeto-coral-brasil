/**
 * Regras de exibicao da predicao de risco.
 *
 * Ficam separadas do componente de proposito: sao elas que carregam as
 * decisoes dificeis, e decisao dificil precisa de teste direto, sem montar
 * arvore de React em volta.
 *
 * 🚨 A regra que existe por medicao, e nao por gosto: **esta tela nao pode
 * escrever "0%" nem "100%"**.
 *
 * O modelo devolve probabilidade recalibrada por regressao isotonica, que e
 * uma funcao escada. Ela produz `0,000` e `1,000` exatos por construcao — 12,2%
 * dos dias de treino caem no degrau mais baixo. O que `p = 0` afirma e "entre
 * os dias de treino deste degrau, nenhum virou alerta". Isso limita a
 * probabilidade; nao a zera.
 *
 * Traduzir esse degrau em "0% de risco" diria ao publico que branqueamento e
 * impossivel naquele recife. A API sinaliza o caso com `no_extremo: true`, e
 * aqui ele vira faixa qualitativa em vez de numero.
 *
 * Ver docs/RESULTADOS.md secao 22.8.
 */

const CASAS = 1;

// Abaixo disto o arredondamento para uma casa produziria "0,0%", que se le
// como zero. E problema de arredondamento, nao do modelo — por isso a saida
// declara o limite em vez de sumir com ele.
export const MENOR_PERCENTUAL_EXIBIVEL = 0.1;

export const FAIXA_EXTREMA = {
  baixo: {
    rotulo: 'Faixa mais baixa da escala',
    explicacao:
      'O modelo coloca este dia no degrau mais baixo da escala calibrada. '
      + 'Isso quer dizer que nenhum dia semelhante do periodo de treino virou '
      + 'alerta — nao que seja impossivel.',
  },
  alto: {
    rotulo: 'Faixa mais alta da escala',
    explicacao:
      'O modelo coloca este dia no degrau mais alto da escala calibrada. '
      + 'Isso quer dizer que todos os dias semelhantes do periodo de treino '
      + 'viraram alerta — nao que seja certo.',
  },
};

function comVirgula(texto) {
  return String(texto).replace('.', ',');
}

/**
 * Numero -> percentual em pt-BR, sem nunca devolver "0,0%".
 */
export function formatarPercentual(probabilidade) {
  const percentual = probabilidade * 100;

  if (percentual > 0 && percentual < MENOR_PERCENTUAL_EXIBIVEL) {
    return `< ${comVirgula(MENOR_PERCENTUAL_EXIBIVEL.toFixed(CASAS))}%`;
  }

  return `${comVirgula(percentual.toFixed(CASAS))}%`;
}

/**
 * Como a probabilidade deve aparecer na tela.
 *
 * Devolve `{ tipo, texto, explicacao }`. `tipo` e `'numero'` ou `'faixa'` —
 * quem desenha precisa saber, porque faixa nao cabe no mesmo lugar que "7,3%".
 */
export function formatarProbabilidade(item) {
  if (!item || item.disponivel !== true) {
    return null;
  }

  const probabilidade = Number(item.probabilidade);
  if (!Number.isFinite(probabilidade)) {
    return null;
  }

  if (item.no_extremo === true) {
    const faixa = probabilidade >= 1 ? FAIXA_EXTREMA.alto : FAIXA_EXTREMA.baixo;
    return { tipo: 'faixa', texto: faixa.rotulo, explicacao: faixa.explicacao };
  }

  return {
    tipo: 'numero',
    texto: formatarPercentual(probabilidade),
    explicacao: null,
  };
}

/**
 * O estado de alerta, ja com o limiar dito por extenso.
 *
 * ⚠️ O limiar vem do servidor e **nao** e reconstruido aqui. Ele e decisao de
 * operacao (0,20 hoje, por ser o ponto equivalente ao antigo 0,50), e duplicar
 * o numero no frontend criaria duas verdades que divergem em silencio no dia
 * em que uma mudar.
 */
/**
 * A aparencia de cada degrau da escala.
 *
 * 🚨 **So a aparencia.** O nome, o corte e a acao vem do servidor, no campo
 * `nivel`. Repetir aqui o corte de cada degrau criaria uma segunda escala,
 * livre para divergir da primeira em silencio — o mesmo defeito que fez o
 * frontend deixar de recalcular `probabilidade >= limiar` em 27/07.
 *
 * A chave e o `slug`. Um degrau que o servidor invente e o frontend nao
 * conheca cai no visual neutro, e nao numa tela quebrada.
 */
const VISUAL_DO_NIVEL = {
  alerta_alto: {
    cor: 'bg-red-600',
    corTexto: 'text-red-700',
    corFundo: 'bg-red-50',
    corBorda: 'border-red-200',
  },
  alerta: {
    cor: 'bg-orange-500',
    corTexto: 'text-orange-700',
    corFundo: 'bg-orange-50',
    corBorda: 'border-orange-200',
  },
  observacao: {
    cor: 'bg-amber-400',
    corTexto: 'text-amber-700',
    corFundo: 'bg-amber-50',
    corBorda: 'border-amber-200',
  },
  sem_aviso: {
    cor: 'bg-emerald-600',
    corTexto: 'text-emerald-700',
    corFundo: 'bg-emerald-50',
    corBorda: 'border-emerald-200',
  },
};

const VISUAL_NEUTRO = {
  cor: 'bg-slate-500',
  corTexto: 'text-slate-700',
  corFundo: 'bg-slate-50',
  corBorda: 'border-slate-200',
};

export function classificarAlerta(item) {
  if (!item || item.disponivel !== true) {
    return null;
  }

  const limiar = Number(item.limiar);
  const emAlerta = item.alerta === true;
  const nivel = item.nivel || null;
  const visual = (nivel && VISUAL_DO_NIVEL[nivel.slug]) || null;

  // ⚠️ O rotulo vem do servidor quando ha nivel. O texto antigo fica como
  // reserva para resposta de uma versao anterior da API — nao como opiniao
  // propria sobre o que exibir.
  const rotulo =
    (nivel && nivel.rotulo) || (emAlerta ? 'Alerta de estresse termico' : 'Sem alerta');

  const corte = nivel && Number(nivel.corte);

  // Tres casos, escritos como tres casos. A versao anterior resolvia isto com
  // dois spreads condicionais encadeados: funcionava, e ninguem conseguiria
  // dizer por que sem simular na cabeca.
  let aparencia;
  if (visual) {
    aparencia = visual; // nivel conhecido
  } else if (nivel) {
    aparencia = VISUAL_NEUTRO; // nivel que esta versao do site nao conhece
  } else {
    aparencia = emAlerta ? VISUAL_DO_NIVEL.alerta : VISUAL_DO_NIVEL.sem_aviso;
  }

  return {
    emAlerta,
    exigeAcao: nivel ? nivel.exige_acao === true : emAlerta,
    slug: nivel ? nivel.slug : null,
    rotulo,
    acao: (nivel && nivel.acao) || null,
    ...aparencia,
    corte: Number.isFinite(corte) ? corte : null,
    corteTexto: Number.isFinite(corte) ? formatarPercentual(corte) : null,
    limiar: Number.isFinite(limiar) ? limiar : null,
    limiarTexto: Number.isFinite(limiar) ? formatarPercentual(limiar) : null,
  };
}

/**
 * Quao velho e o dado sobre o qual a conta foi feita.
 *
 * A serie tem latencia e ela varia. Sem esta frase, um risco calculado sobre
 * dado de tres semanas atras se apresenta igualzinho a um calculado sobre
 * ontem.
 */
export function descreverAtraso(dias) {
  const numero = Number(dias);
  if (!Number.isFinite(numero) || numero < 0) {
    return null;
  }
  if (numero === 0) {
    return 'dado de hoje';
  }
  if (numero === 1) {
    return 'dado de ontem';
  }
  return `dado de ${numero} dias atras`;
}

export function formatarDataBr(iso) {
  if (typeof iso !== 'string') {
    return null;
  }
  const partes = iso.split('-');
  if (partes.length !== 3) {
    return null;
  }
  const [ano, mes, dia] = partes;
  return `${dia}/${mes}/${ano}`;
}

/**
 * Rotulo legivel de uma coluna do modelo: `sst_variacao_7d` -> "Temperatura".
 *
 * As entradas sao **variacoes**, nao niveis, e o rotulo diz isso. Chamar de
 * "Temperatura: 0,09" sugeriria 0,09 °C de agua.
 */
const NOMES_DE_VARIAVEL = {
  sst: 'Temperatura',
  dhw: 'Calor acumulado (DHW)',
  salinidade: 'Salinidade',
  oxigenio: 'Oxigenio',
};

export function descreverEntrada(coluna, valor) {
  const partes = String(coluna).split('_');
  const dias = partes[partes.length - 1];
  const variavel = partes.slice(0, -2).join('_');
  const numero = Number(valor);

  return {
    coluna,
    rotulo: NOMES_DE_VARIAVEL[variavel] || variavel,
    periodo: `variacao em ${String(dias).replace('d', '')} dias`,
    valor: Number.isFinite(numero) ? comVirgula(numero.toFixed(2)) : '--',
    subiu: Number.isFinite(numero) && numero > 0,
  };
}

/**
 * Busca a predicao de um recife.
 *
 * Devolve `{ estado, ... }` em vez de lancar: cada estado tem uma tela
 * diferente, e transformar "modelo ainda nao treinado" em erro generico
 * esconderia justamente a informacao acionavel.
 *
 * | estado | quando |
 * |---|---|
 * | `ok` | resposta com predicao |
 * | `sem-modelo` | 503 — o artefato e derivado e pode nao existir |
 * | `fora-do-treino` | 404 — o modelo nao viu este recife |
 * | `indisponivel` | rede caiu, ou resposta que nao da para ler |
 */
export async function buscarPredicoes() {
  if (typeof fetch !== 'function') {
    return { estado: 'indisponivel', porLocal: {} };
  }

  try {
    const resposta = await fetch('/api/painel-risco/');

    if (resposta.status === 503) {
      return { estado: 'sem-modelo', porLocal: {} };
    }
    if (!resposta.ok) {
      return { estado: 'indisponivel', porLocal: {} };
    }

    const corpo = await resposta.json();
    const lista = Array.isArray(corpo?.results) ? corpo.results : [];

    const porLocal = {};
    lista.forEach((registro) => {
      if (registro?.local) {
        porLocal[registro.local] = registro;
      }
    });

    return { estado: 'ok', porLocal, modelo: corpo?.modelo || null };
  } catch (erro) {
    return { estado: 'indisponivel', porLocal: {} };
  }
}

export async function buscarPredicao(slug) {
  if (typeof fetch !== 'function') {
    return { estado: 'indisponivel' };
  }

  try {
    const resposta = await fetch(`/api/painel-risco/${slug}/`);

    if (resposta.status === 503) {
      return { estado: 'sem-modelo' };
    }
    if (resposta.status === 404) {
      const corpo = await resposta.json().catch(() => null);
      return { estado: 'fora-do-treino', detalhe: corpo?.detail || null };
    }
    if (!resposta.ok) {
      return { estado: 'indisponivel' };
    }

    const corpo = await resposta.json();
    if (!corpo || typeof corpo !== 'object') {
      return { estado: 'indisponivel' };
    }

    return { estado: 'ok', dados: corpo };
  } catch (erro) {
    return { estado: 'indisponivel' };
  }
}
