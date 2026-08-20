import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import SerieAmbiental from './SerieAmbiental';

// O desenho em si e testado em `GraficoSerieInterativo.test.jsx`, sobre a
// figura pura. Aqui interessa a moldura: proveniencia, download e os estados.
jest.mock('plotly.js-basic-dist-min', () => ({ react: jest.fn(), purge: jest.fn() }));

function renderSerie(props) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <SerieAmbiental {...props} />
    </MemoryRouter>,
  );
}

describe('SerieAmbiental', () => {
  const RESPOSTA = {
    count: 4,
    results: [
      { data: '2026-07-22', variavel: 'sst', valor: 26.1, fonte: 'noaa_crw' },
      { data: '2026-07-23', variavel: 'sst', valor: 26.4, fonte: 'noaa_crw' },
      { data: '2026-07-22', variavel: 'dhw', valor: 0, fonte: 'noaa_crw' },
      { data: '2026-07-23', variavel: 'dhw', valor: 0.2, fonte: 'noaa_crw' },
    ],
  };

  afterEach(() => {
    delete global.fetch;
  });

  test('🚨 separa medicao de previsao na propria tela', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(RESPOSTA) })
    );

    renderSerie({ slug: 'abrolhos-ba' });

    await waitFor(() =>
      expect(screen.getByText(/Isto e medicao, nao previsao/)).toBeInTheDocument()
    );
  });

  test('mostra proveniencia e o link de download, para quem esta aprovado', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(RESPOSTA) })
    );

    renderSerie({ slug: 'abrolhos-ba', usuario: { autenticado: true, aprovado: true } });

    await waitFor(() => expect(screen.getByText(/noaa_crw/)).toBeInTheDocument());

    const link = screen.getByRole('link', { name: /Baixar a serie completa/ });
    expect(link).toHaveAttribute('href', expect.stringContaining('formato=csv'));
    expect(link).toHaveAttribute('href', expect.stringContaining('local=abrolhos-ba'));
  });

  test('master baixa mesmo sem o proprio perfil marcar aprovado', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(RESPOSTA) })
    );

    renderSerie({ slug: 'abrolhos-ba', usuario: { autenticado: true, master: true, aprovado: false } });

    await waitFor(() =>
      expect(screen.getByRole('link', { name: /Baixar a serie completa/ })).toBeInTheDocument()
    );
  });

  test('🚨 sem conta aprovada, o download vira um convite para logar — nao um link morto', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(RESPOSTA) })
    );

    renderSerie({ slug: 'abrolhos-ba' });

    await waitFor(() => expect(screen.getByText(/noaa_crw/)).toBeInTheDocument());

    expect(screen.queryByRole('link', { name: /Baixar a serie completa/ })).toBeNull();
    const convite = screen.getByRole('link', { name: /Faca login e aguarde aprovacao/ });
    expect(convite).toHaveAttribute('href', '/login');
  });

  test('em modo manutencao nem chama a API', async () => {
    global.fetch = jest.fn();

    renderSerie({ slug: 'abrolhos-ba', publicOffline: true });

    await waitFor(() =>
      expect(screen.getByText(/nao e exibida em modo manutencao/)).toBeInTheDocument()
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('sem serie diz que falta ingestao, e nao que houve erro', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ count: 0, results: [] }) })
    );

    renderSerie({ slug: 'recife-novo' });

    await waitFor(() =>
      expect(screen.getByText(/Ainda nao ha medicoes ingeridas/)).toBeInTheDocument()
    );
  });

  /** Responde por variavel, como o servidor faria. */
  function responderPorVariavel(porVariavel) {
    global.fetch = jest.fn((url) => {
      const variavel = new URL(url, 'http://x').searchParams.get('variavel');
      const results = porVariavel[variavel] || [];
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ count: results.length, results }),
      });
    });
  }

  test('🚨 a faixa rosa e explicada como o que aconteceu, nao como previsao', async () => {
    responderPorVariavel({
      sst: RESPOSTA.results.filter((r) => r.variavel === 'sst'),
      baa: [
        { data: '2026-07-22', variavel: 'baa', valor: 4, fonte: 'noaa_crw' },
        { data: '2026-07-23', variavel: 'baa', valor: 4, fonte: 'noaa_crw' },
      ],
    });

    renderSerie({ slug: 'abrolhos-ba' });

    await waitFor(() =>
      expect(screen.getByText(/dias em que a NOAA manteve alerta termico/)).toBeInTheDocument()
    );
    expect(screen.getByText(/aconteceu/)).toBeInTheDocument();
  });

  test('sem episodio no periodo, a legenda da faixa nao aparece', async () => {
    responderPorVariavel({
      sst: RESPOSTA.results.filter((r) => r.variavel === 'sst'),
      baa: [{ data: '2026-07-22', variavel: 'baa', valor: 0, fonte: 'noaa_crw' }],
    });

    renderSerie({ slug: 'abrolhos-ba' });

    await waitFor(() => expect(screen.getByText(/noaa_crw/)).toBeInTheDocument());

    // Explicar uma cor que nao esta na tela e ruido.
    expect(screen.queryByText(/manteve alerta termico/)).toBeNull();
  });
});
