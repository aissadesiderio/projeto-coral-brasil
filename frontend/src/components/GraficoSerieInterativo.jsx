import { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-basic-dist-min';

import {
  CORTE_ALERTA_DHW,
  ROTULOS,
  VARIAVEIS_DA_SERIE,
} from '../utils/serie';

/**
 * A serie medida do recife, em quatro paineis empilhados e interativos.
 *
 * 🚨 **Um painel por variavel, e nao as quatro sobrepostas.** E a mesma decisao
 * que `ml/graficos.py::linha_do_tempo` registra para as figuras do TCC, pelo
 * mesmo motivo: num eixo unico o oxigenio varia +-5 mmol/m3 e a temperatura
 * +-1 C, entao a curva do oxigenio ocupa a figura inteira e as outras tres
 * viram uma linha reta. Padronizar resolveria a altura e custaria a unidade
 * fisica — que e justamente o que faz a figura ser lida por quem conhece o
 * oceano e nao o modelo.
 *
 * ⚠️ **`montarFigura` e pura de proposito.** O que decide a honestidade do
 * grafico — buraco onde a medida foi reprovada, faixa so onde houve alerta,
 * regua do DHW no lugar certo — fica testavel sem DOM, sem canvas e sem subir
 * o Plotly no jsdom. O componente abaixo so entrega o resultado ao Plotly.
 */

// Os hex ficam literais aqui porque SVG nao le classe do Tailwind — mesma
// razao (e o mesmo cuidado de manter em sync) do antigo `GraficoSerie`.
// `sst` e `dhw` sao os tokens do tema: ocean.dark e terra.
//
// ⚠️ Salinidade e oxigenio **nao tem token**: a paleta do projeto tem duas
// cores de dado, e aqui sao necessarias quatro. As duas abaixo foram
// escolhidas para nao competir com as outras duas nem entre si, e ficam
// declaradas so aqui — se a paleta ganhar cores de dado, e daqui que saem.
export const CORES = {
  sst: '#2b6978',
  dhw: '#D47046',
  salinidade: '#4E7A9B',
  oxigenio: '#5F7D4F',
};

// Rosa da faixa de alerta. Fraco de proposito: e fundo, nao dado — precisa
// aparecer atras da curva sem disputar leitura com ela.
export const COR_ALERTA = 'rgba(212,112,70,0.18)';

const ALTURA_DO_PAINEL = 0.22;
const ESPACO_ENTRE_PAINEIS = 0.04;

/** O dominio vertical de cada painel, de cima para baixo. */
export function dominioDoPainel(indice) {
  const topo = 1 - indice * (ALTURA_DO_PAINEL + ESPACO_ENTRE_PAINEIS);
  return [Number((topo - ALTURA_DO_PAINEL).toFixed(4)), Number(topo.toFixed(4))];
}

function eixoY(indice) {
  return indice === 0 ? 'y' : `y${indice + 1}`;
}

/**
 * A especificacao completa da figura: `{ data, layout, config }`.
 *
 * Recebe so o que ja foi organizado por `utils/serie.js` — nao busca, nao
 * ordena e nao decide recorte.
 */
export function montarFigura({ series = {}, alertas = [], variaveis = VARIAVEIS_DA_SERIE } = {}) {
  const desenhaveis = variaveis.filter((variavel) => (series[variavel] || []).length > 0);

  const data = desenhaveis.map((variavel, indice) => {
    const pontos = series[variavel] || [];
    const rotulo = ROTULOS[variavel] || { nome: variavel, unidade: '', casas: 2 };

    return {
      type: 'scatter',
      mode: 'lines',
      name: rotulo.nome,
      x: pontos.map((p) => p.data),
      // 🚨 `null` continua `null` ate o Plotly. Com `connectgaps: false` a
      // linha abre um buraco onde a validacao fisica reprovou a medida; com
      // `true` — ou trocando por zero — a curva costuraria por cima da falha
      // e o grafico afirmaria uma medicao que nao existe.
      y: pontos.map((p) => (Number.isFinite(p.valor) ? p.valor : null)),
      connectgaps: false,
      line: { color: CORES[variavel], width: 1.4 },
      xaxis: 'x',
      yaxis: eixoY(indice),
      showlegend: false,
      hovertemplate: `%{y:.${rotulo.casas}f} ${rotulo.unidade}<extra>${rotulo.nome}</extra>`,
    };
  });

  const layout = {
    height: 210 * Math.max(desenhaveis.length, 1) + 90,
    margin: { l: 74, r: 24, t: 16, b: 48 },
    // Transparente: o grafico se apoia no fundo areia da pagina em vez de
    // recortar um retangulo branco no meio dela.
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'IBM Plex Mono, ui-monospace, monospace', size: 11, color: '#17414c' },
    hovermode: 'x unified',
    hoverlabel: { bgcolor: '#fffaf7', bordercolor: '#17414c', font: { size: 11 } },
    xaxis: {
      type: 'date',
      // pt-BR: o bundle basic nao traz locale, entao o formato vai explicito —
      // sem isto a data sai em ingles no eixo e no hover.
      tickformat: '%d/%m/%Y',
      hoverformat: '%d/%m/%Y',
      showgrid: true,
      gridcolor: 'rgba(23,65,76,0.08)',
      linecolor: 'rgba(23,65,76,0.25)',
      domain: [0, 1],
    },
    shapes: [],
    annotations: [],
  };

  desenhaveis.forEach((variavel, indice) => {
    const rotulo = ROTULOS[variavel] || { nome: variavel, unidade: '' };
    const chave = indice === 0 ? 'yaxis' : `yaxis${indice + 1}`;

    layout[chave] = {
      domain: dominioDoPainel(indice),
      title: {
        text: `${rotulo.nome}<br>(${rotulo.unidade})`,
        font: { size: 10 },
        standoff: 8,
      },
      showgrid: true,
      gridcolor: 'rgba(23,65,76,0.08)',
      zeroline: false,
      linecolor: 'rgba(23,65,76,0.25)',
      anchor: 'x',
    };

    // A regua do DHW: "3,8" nao diz nada, "3,8 quase no 4" diz tudo.
    if (variavel === 'dhw') {
      layout.shapes.push({
        type: 'line',
        xref: 'paper',
        x0: 0,
        x1: 1,
        yref: eixoY(indice),
        y0: CORTE_ALERTA_DHW,
        y1: CORTE_ALERTA_DHW,
        line: { color: '#8A4A22', width: 1, dash: 'dash' },
        layer: 'above',
      });
      layout.annotations.push({
        xref: 'paper',
        x: 0,
        xanchor: 'left',
        yref: eixoY(indice),
        y: CORTE_ALERTA_DHW,
        yanchor: 'bottom',
        text: 'Alerta Nivel 1 da NOAA (DHW 4)',
        showarrow: false,
        font: { size: 9, color: '#8A4A22' },
      });
    }
  });

  // 🚨 As faixas atravessam os quatro paineis (`yref: 'paper'`) porque a
  // pergunta que elas respondem e "o que estava acontecendo nas variaveis
  // quando o alerta valia?" — separadas por painel, o olho perderia o
  // alinhamento vertical que e o proprio conteudo da figura.
  //
  // ⚠️ `layer: 'below'` mantem a curva por cima: a faixa e contexto, e o dado
  // nao pode ficar atras dela.
  alertas.forEach((intervalo) => {
    layout.shapes.push({
      type: 'rect',
      xref: 'x',
      x0: intervalo.inicio,
      x1: intervalo.fim,
      yref: 'paper',
      y0: 0,
      y1: 1,
      fillcolor: COR_ALERTA,
      line: { width: 0 },
      layer: 'below',
    });
  });

  const config = {
    displaylogo: false,
    responsive: true,
    // Sobram zoom, pan, caixa de zoom, autoescala e download — o que serve
    // para ler uma serie. Saem os de selecao, que so fazem sentido quando ha
    // o que selecionar, e o "lasso", que confunde sem uso aqui.
    modeBarButtonsToRemove: ['select2d', 'lasso2d'],
    toImageButtonOptions: { format: 'png', scale: 2, filename: 'serie-ambiental' },
  };

  return { data, layout, config };
}

export default function GraficoSerieInterativo({ series, alertas, rotuloDoLocal }) {
  const alvo = useRef(null);

  useEffect(() => {
    const node = alvo.current;
    if (!node) {
      return undefined;
    }

    const { data, layout, config } = montarFigura({ series, alertas });
    Plotly.react(node, data, layout, config);

    return () => {
      // Sem `purge` o Plotly deixa listeners e um nó de medição para trás a
      // cada troca de recife — a página do site troca de slug sem recarregar.
      Plotly.purge(node);
    };
  }, [series, alertas]);

  return (
    <div
      ref={alvo}
      role="img"
      aria-label={
        `Series ambientais medidas${rotuloDoLocal ? ` em ${rotuloDoLocal}` : ''}: ` +
        'temperatura da superficie, calor acumulado, salinidade e oxigenio dissolvido. ' +
        'Os numeros da serie estao no CSV para download logo abaixo.'
      }
    />
  );
}
