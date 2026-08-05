import {
  CORTE_ALERTA_DHW,
  buscarSerie,
  montarConsulta,
  organizarSerie,
  urlDeDownload,
} from './serie';

const REGISTROS = [
  { data: '2026-07-24', variavel: 'sst', valor: 26.4, fonte: 'noaa_crw' },
  { data: '2026-07-22', variavel: 'sst', valor: 26.1, fonte: 'noaa_crw' },
  { data: '2026-07-23', variavel: 'sst', valor: 26.2, fonte: 'noaa_crw' },
  { data: '2026-07-24', variavel: 'dhw', valor: 0, fonte: 'noaa_crw' },
];

describe('montarConsulta', () => {
  test('pede as duas variaveis e recorta o periodo', () => {
    const url = montarConsulta('abrolhos-ba', { hoje: new Date('2026-07-31') });

    expect(url).toContain('local=abrolhos-ba');
    expect(url).toContain('variavel=sst');
    expect(url).toContain('variavel=dhw');
    expect(url).toContain('de=2025-07-31');
  });

  test('pede pagina grande o bastante para um ano de duas variaveis', () => {
    // ~730 pontos; abaixo disso o grafico desenharia parte do periodo.
    expect(montarConsulta('abrolhos-ba')).toContain('page_size=1000');
  });
});

describe('organizarSerie', () => {
  test('agrupa por variavel e ordena no tempo', () => {
    const { series } = organizarSerie(REGISTROS);

    expect(series.sst.map((p) => p.data)).toEqual([
      '2026-07-22', '2026-07-23', '2026-07-24',
    ]);
    expect(series.dhw).toHaveLength(1);
  });

  test('🚨 valor nulo vira buraco, e nunca zero', () => {
    const { series, reprovadas } = organizarSerie([
      { data: '2026-07-22', variavel: 'sst', valor: 26.1 },
      { data: '2026-07-23', variavel: 'sst', valor: null },
    ]);

    expect(series.sst[1].valor).toBeNull();
    expect(series.sst[1].valor).not.toBe(0);
    expect(reprovadas).toBe(1);
  });

  test('zero de verdade continua sendo zero', () => {
    const { series, reprovadas } = organizarSerie([
      { data: '2026-07-24', variavel: 'dhw', valor: 0 },
    ]);

    expect(series.dhw[0].valor).toBe(0);
    expect(reprovadas).toBe(0);
  });

  test('ignora variavel que este grafico nao desenha', () => {
    const { series } = organizarSerie([
      ...REGISTROS,
      { data: '2026-07-24', variavel: 'salinidade', valor: 37 },
    ]);

    expect(series.salinidade).toBeUndefined();
  });

  test('reune periodo e fontes para a legenda', () => {
    const { periodo, fontes, total } = organizarSerie(REGISTROS);

    expect(periodo).toEqual({ inicio: '2026-07-22', fim: '2026-07-24' });
    expect(fontes).toEqual(['noaa_crw']);
    expect(total).toBe(4);
  });
});

describe('urlDeDownload', () => {
  test('baixa a serie inteira do recife, nao so o periodo do grafico', () => {
    const url = urlDeDownload('abrolhos-ba');

    expect(url).toContain('formato=csv');
    expect(url).toContain('local=abrolhos-ba');
    expect(url).not.toContain('de=');
  });
});

describe('buscarSerie', () => {
  afterEach(() => {
    delete global.fetch;
  });

  function responder(corpo, status = 200) {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: status === 200, status, json: () => Promise.resolve(corpo) })
    );
  }

  test('estado ok com a serie organizada', async () => {
    responder({ count: 4, results: REGISTROS });

    const resultado = await buscarSerie('abrolhos-ba');

    expect(resultado.estado).toBe('ok');
    expect(resultado.series.sst).toHaveLength(3);
    expect(resultado.truncada).toBe(false);
  });

  test('🚨 avisa quando a pagina cortou o periodo pedido', async () => {
    responder({ count: 5000, results: REGISTROS });

    expect((await buscarSerie('abrolhos-ba')).truncada).toBe(true);
  });

  test('resposta vazia vira estado proprio, e nao erro', async () => {
    responder({ count: 0, results: [] });

    expect((await buscarSerie('abrolhos-ba')).estado).toBe('sem-serie');
  });

  test('503 vira offline', async () => {
    responder({}, 503);

    expect((await buscarSerie('abrolhos-ba')).estado).toBe('offline');
  });

  test('rede caida nao lanca', async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error('sem rede')));

    expect((await buscarSerie('abrolhos-ba')).estado).toBe('indisponivel');
  });
});

test('o corte desenhado e o Alerta Nivel 1 da NOAA', () => {
  expect(CORTE_ALERTA_DHW).toBe(4);
});
