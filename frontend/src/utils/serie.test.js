import {
  CORTE_ALERTA_BAA,
  CORTE_ALERTA_DHW,
  VARIAVEIS_DA_SERIE,
  buscarSerie,
  intervalosDeAlerta,
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
  test('pede as quatro variaveis e o alerta, e recorta o periodo', () => {
    const url = montarConsulta('abrolhos-ba', { hoje: new Date('2026-07-31') });

    expect(url).toContain('local=abrolhos-ba');
    VARIAVEIS_DA_SERIE.forEach((v) => expect(url).toContain(`variavel=${v}`));
    expect(url).toContain('variavel=baa');
    expect(url).toContain('de=2025-07-31');
  });

  test('aceita uma variavel so, que e como `buscarSerie` chama', () => {
    const url = montarConsulta('abrolhos-ba', { variaveis: ['sst'] });

    expect(url).toContain('variavel=sst');
    expect(url).not.toContain('variavel=dhw');
  });

  test('pede o teto de pagina do servidor', () => {
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

  test('salinidade e oxigenio passaram a entrar', () => {
    // Ate 16/08/2026 as duas eram descartadas aqui: o grafico era um eixo so,
    // e nele uma engoliria as outras. Com um painel por variavel, entram.
    const { series } = organizarSerie([
      { data: '2026-07-24', variavel: 'salinidade', valor: 36.1 },
      { data: '2026-07-24', variavel: 'oxigenio', valor: 201.4 },
    ]);

    expect(series.salinidade).toHaveLength(1);
    expect(series.oxigenio).toHaveLength(1);
  });

  test('variavel fora do recorte da tela continua ignorada', () => {
    const { series } = organizarSerie([
      ...REGISTROS,
      { data: '2026-07-24', variavel: 'hotspot', valor: 0.4 },
    ]);

    expect(series.hotspot).toBeUndefined();
  });

  test('reune periodo e fontes para a legenda', () => {
    const { periodo, fontes, total } = organizarSerie(REGISTROS);

    expect(periodo).toEqual({ inicio: '2026-07-22', fim: '2026-07-24' });
    expect(fontes).toEqual(['noaa_crw']);
    expect(total).toBe(4);
  });
});

describe('intervalosDeAlerta', () => {
  function baa(valores) {
    return valores.map((valor, i) => ({
      data: `2026-07-${String(i + 1).padStart(2, '0')}`,
      valor,
    }));
  }

  test('um trecho continuo vira um intervalo', () => {
    expect(intervalosDeAlerta(baa([0, 3, 4, 0]))).toEqual([
      { inicio: '2026-07-02', fim: '2026-07-03' },
    ]);
  });

  test('dois episodios separados nao viram um so', () => {
    expect(intervalosDeAlerta(baa([3, 0, 0, 4]))).toHaveLength(2);
  });

  test('alerta que segue ate o fim da serie fecha no ultimo dia', () => {
    expect(intervalosDeAlerta(baa([0, 3, 4]))).toEqual([
      { inicio: '2026-07-02', fim: '2026-07-03' },
    ]);
  });

  test('🚨 abaixo do corte nao e alerta — BAA 2 e vigilancia, nao Nivel 1', () => {
    expect(intervalosDeAlerta(baa([0, 1, 2]))).toEqual([]);
  });

  test('⚠️ dia sem medida interrompe a faixa em vez de esticar por cima', () => {
    // Sem medida nao ha como afirmar que o alerta valia naquele dia.
    expect(intervalosDeAlerta(baa([3, null, 3]))).toHaveLength(2);
  });

  test('o corte desenhado e o mesmo que monta o alvo do modelo', () => {
    expect(CORTE_ALERTA_BAA).toBe(3);
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

  /** Responde por variavel, como o servidor faria. */
  function responderPorVariavel(porVariavel, { count } = {}) {
    global.fetch = jest.fn((url) => {
      const variavel = new URL(url, 'http://x').searchParams.get('variavel');
      const results = porVariavel[variavel] || [];
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ count: count ?? results.length, results }),
      });
    });
  }

  test('estado ok com a serie organizada', async () => {
    responderPorVariavel({
      sst: REGISTROS.filter((r) => r.variavel === 'sst'),
      dhw: REGISTROS.filter((r) => r.variavel === 'dhw'),
    });

    const resultado = await buscarSerie('abrolhos-ba');

    expect(resultado.estado).toBe('ok');
    expect(resultado.series.sst).toHaveLength(3);
    expect(resultado.truncada).toBe(false);
  });

  test('uma requisicao por variavel, para nao estourar a pagina', async () => {
    responderPorVariavel({ sst: REGISTROS.filter((r) => r.variavel === 'sst') });

    await buscarSerie('abrolhos-ba');

    // 🚨 Um ano das cinco juntas passa de 1800 pontos, e o teto do servidor e
    // 1000: pedidas juntas, a serie viria cortada em silencio.
    expect(global.fetch).toHaveBeenCalledTimes(5);
  });

  test('o alerta da NOAA chega como intervalos, prontos para virar faixa', async () => {
    responderPorVariavel({
      sst: REGISTROS.filter((r) => r.variavel === 'sst'),
      baa: [
        { data: '2026-07-22', variavel: 'baa', valor: 0 },
        { data: '2026-07-23', variavel: 'baa', valor: 4 },
        { data: '2026-07-24', variavel: 'baa', valor: 4 },
      ],
    });

    const resultado = await buscarSerie('abrolhos-ba');

    expect(resultado.alertas).toEqual([
      { inicio: '2026-07-23', fim: '2026-07-24' },
    ]);
  });

  test('🚨 avisa quando a pagina cortou o periodo pedido', async () => {
    responderPorVariavel(
      { sst: REGISTROS.filter((r) => r.variavel === 'sst') },
      { count: 5000 },
    );

    expect((await buscarSerie('abrolhos-ba')).truncada).toBe(true);
  });

  test('resposta vazia vira estado proprio, e nao erro', async () => {
    responderPorVariavel({});

    expect((await buscarSerie('abrolhos-ba')).estado).toBe('sem-serie');
  });

  test('503 vira offline', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({}) })
    );

    expect((await buscarSerie('abrolhos-ba')).estado).toBe('offline');
  });

  test('⚠️ uma variavel que falha nao derruba as outras quatro', async () => {
    global.fetch = jest.fn((url) => {
      const variavel = new URL(url, 'http://x').searchParams.get('variavel');
      if (variavel === 'oxigenio') {
        return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) });
      }
      const results = variavel === 'sst' ? REGISTROS.filter((r) => r.variavel === 'sst') : [];
      return Promise.resolve({
        ok: true, status: 200, json: () => Promise.resolve({ count: results.length, results }),
      });
    });

    const resultado = await buscarSerie('abrolhos-ba');

    expect(resultado.estado).toBe('ok');
    expect(resultado.series.sst).toHaveLength(3);
  });

  test('rede caida nao lanca', async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error('sem rede')));

    expect((await buscarSerie('abrolhos-ba')).estado).toBe('indisponivel');
  });
});

test('o corte desenhado e o Alerta Nivel 1 da NOAA', () => {
  expect(CORTE_ALERTA_DHW).toBe(4);
});
