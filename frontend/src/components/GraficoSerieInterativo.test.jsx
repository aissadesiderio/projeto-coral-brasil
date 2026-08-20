/**
 * Testes do grafico interativo da serie medida.
 *
 * 🚨 O foco esta em `montarFigura`, que e pura: o que decide se o grafico
 * mente ou nao — buraco onde a medida foi reprovada, faixa so onde houve
 * alerta, regua do DHW no painel do DHW — se verifica sem subir o Plotly no
 * jsdom. O Plotly em si e mockado: testar que ele desenha SVG seria testar o
 * Plotly, nao este componente.
 */

import { render } from '@testing-library/react';

import GraficoSerieInterativo, {
  COR_ALERTA,
  dominioDoPainel,
  montarFigura,
} from './GraficoSerieInterativo';

jest.mock('plotly.js-basic-dist-min', () => ({
  react: jest.fn(),
  purge: jest.fn(),
}));

// eslint-disable-next-line import/first
const Plotly = require('plotly.js-basic-dist-min');

function serie(valores, inicio = 1) {
  return valores.map((valor, i) => ({
    data: `2026-07-${String(inicio + i).padStart(2, '0')}`,
    valor,
  }));
}

const SERIES = {
  sst: serie([26.1, 26.4, 26.8]),
  dhw: serie([0, 0.2, 4.3]),
  salinidade: serie([36.1, 36.2, 36.0]),
  oxigenio: serie([201.4, 200.9, 202.2]),
};

describe('montarFigura', () => {
  test('um painel por variavel, cada um no seu proprio eixo', () => {
    const { data, layout } = montarFigura({ series: SERIES });

    expect(data).toHaveLength(4);
    expect(data.map((t) => t.yaxis)).toEqual(['y', 'y2', 'y3', 'y4']);
    // 🚨 Eixo Y separado e o ponto todo: o oxigenio varia ~200 e a temperatura
    // ~26. Num eixo so, a temperatura vira uma reta colada no chao.
    expect(layout.yaxis.domain).not.toEqual(layout.yaxis2.domain);
  });

  test('todos os paineis compartilham o eixo do tempo', () => {
    const { data } = montarFigura({ series: SERIES });

    expect(new Set(data.map((t) => t.xaxis))).toEqual(new Set(['x']));
  });

  test('🚨 valor nulo vira buraco, e nunca zero nem linha costurada', () => {
    const { data } = montarFigura({ series: { sst: serie([26.1, null, 26.4]) } });

    expect(data[0].y).toEqual([26.1, null, 26.4]);
    expect(data[0].y).not.toContain(0);
    // Com `connectgaps: true` a curva atravessaria o dia sem medida e ficaria
    // indistinguivel de dado real.
    expect(data[0].connectgaps).toBe(false);
  });

  test('variavel sem ponto nenhum nao vira painel vazio', () => {
    const { data } = montarFigura({
      series: { sst: serie([26.1, 26.4]), salinidade: [] },
    });

    expect(data).toHaveLength(1);
    expect(data[0].name).toMatch(/Temperatura/);
  });

  test('a regua do DHW fica no painel do DHW, e nao em outro', () => {
    const { layout } = montarFigura({ series: SERIES });

    const regua = layout.shapes.find((s) => s.type === 'line');
    // dhw e a segunda variavel -> eixo y2.
    expect(regua.yref).toBe('y2');
    expect(regua.y0).toBe(4);
  });

  test('sem DHW na serie, nao existe regua sobrando', () => {
    const { layout } = montarFigura({ series: { sst: serie([26.1, 26.4]) } });

    expect(layout.shapes.filter((s) => s.type === 'line')).toHaveLength(0);
  });

  test('a faixa de alerta atravessa os quatro paineis', () => {
    const { layout } = montarFigura({
      series: SERIES,
      alertas: [{ inicio: '2026-07-02', fim: '2026-07-03' }],
    });

    const faixa = layout.shapes.find((s) => s.type === 'rect');
    // `paper` = a altura inteira da figura. Preso a um eixo, a faixa cobriria
    // um painel so e o alinhamento vertical — que e o conteudo da figura —
    // se perderia.
    expect(faixa.yref).toBe('paper');
    expect(faixa.x0).toBe('2026-07-02');
    expect(faixa.fillcolor).toBe(COR_ALERTA);
  });

  test('⚠️ a faixa fica atras da curva, nunca por cima', () => {
    const { layout } = montarFigura({
      series: SERIES,
      alertas: [{ inicio: '2026-07-02', fim: '2026-07-03' }],
    });

    expect(layout.shapes.find((s) => s.type === 'rect').layer).toBe('below');
  });

  test('sem alerta no periodo, nenhuma faixa e desenhada', () => {
    const { layout } = montarFigura({ series: SERIES, alertas: [] });

    expect(layout.shapes.filter((s) => s.type === 'rect')).toHaveLength(0);
  });

  test('serie vazia nao quebra a montagem', () => {
    const { data, layout } = montarFigura({});

    expect(data).toEqual([]);
    expect(layout.height).toBeGreaterThan(0);
  });

  test('a data sai em formato brasileiro no eixo e no hover', () => {
    const { layout } = montarFigura({ series: SERIES });

    expect(layout.xaxis.tickformat).toBe('%d/%m/%Y');
    expect(layout.xaxis.hoverformat).toBe('%d/%m/%Y');
  });
});

describe('dominioDoPainel', () => {
  test('os paineis descem sem se sobrepor', () => {
    const primeiro = dominioDoPainel(0);
    const segundo = dominioDoPainel(1);

    expect(primeiro[1]).toBe(1);
    expect(segundo[1]).toBeLessThan(primeiro[0]);
  });
});

describe('GraficoSerieInterativo', () => {
  beforeEach(() => {
    Plotly.react.mockClear();
    Plotly.purge.mockClear();
  });

  test('entrega a figura ao Plotly', () => {
    render(<GraficoSerieInterativo series={SERIES} alertas={[]} />);

    expect(Plotly.react).toHaveBeenCalledTimes(1);
    expect(Plotly.react.mock.calls[0][1]).toHaveLength(4);
  });

  test('🚨 limpa o grafico ao sair, senao trocar de recife vaza listener', () => {
    const { unmount } = render(<GraficoSerieInterativo series={SERIES} alertas={[]} />);
    unmount();

    expect(Plotly.purge).toHaveBeenCalledTimes(1);
  });

  test('descreve o grafico para quem usa leitor de tela', () => {
    const { getByRole } = render(
      <GraficoSerieInterativo series={SERIES} alertas={[]} rotuloDoLocal="Abrolhos" />
    );

    expect(getByRole('img', { name: /Abrolhos/ })).toBeInTheDocument();
  });
});
