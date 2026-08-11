import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import GraficoSerie, { montarCaminho } from './GraficoSerie';
import SerieAmbiental from './SerieAmbiental';

function renderSerie(props) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <SerieAmbiental {...props} />
    </MemoryRouter>,
  );
}

function serie(valores) {
  return valores.map((valor, i) => ({
    data: `2026-07-${String(i + 1).padStart(2, '0')}`,
    valor,
  }));
}

describe('montarCaminho', () => {
  const x = (i) => i * 10;
  const y = (v) => v;

  test('linha continua quando nao ha lacuna', () => {
    expect(montarCaminho(serie([1, 2, 3]), x, y)).toBe('M0.0 1.0 L10.0 2.0 L20.0 3.0');
  });

  test('🚨 a linha quebra no nulo em vez de atravessa-lo', () => {
    const caminho = montarCaminho(serie([1, null, 3]), x, y);

    // Dois `M` = dois traços. Um só significaria uma reta cruzando o dia sem
    // medida, indistinguivel de dado real.
    expect(caminho.match(/M/g)).toHaveLength(2);
    expect(caminho).toBe('M0.0 1.0 M20.0 3.0');
  });

  test('serie que comeca com nulo nao produz comando solto', () => {
    expect(montarCaminho(serie([null, 2]), x, y)).toBe('M10.0 2.0');
  });
});

describe('GraficoSerie', () => {
  test('desenha e anuncia o ultimo valor', () => {
    const { container } = render(
      <GraficoSerie pontos={serie([26.1, 26.4])} rotulo="Temperatura" unidade="°C" />
    );

    expect(screen.getByRole('img', { name: /Temperatura/ })).toBeInTheDocument();
    // Dentro da legenda: "26,4" tambem aparece como rotulo do eixo, e um
    // `getByText` solto casaria com os dois.
    expect(container.querySelector('figcaption')).toHaveTextContent('ultimo: 26,4 °C');
  });

  test('conta os dias sem medida em vez de escondê-los', () => {
    render(
      <GraficoSerie pontos={serie([26.1, null, 26.4])} rotulo="Temperatura" unidade="°C" />
    );

    expect(screen.getByText(/1 dia\(s\) sem medida valida/)).toBeInTheDocument();
    expect(screen.getByText(/nao em zero/)).toBeInTheDocument();
  });

  test('sem pontos suficientes diz isso, em vez de desenhar nada', () => {
    render(<GraficoSerie pontos={serie([26.1])} rotulo="Temperatura" unidade="°C" />);

    expect(screen.getByText(/Sem pontos suficientes/)).toBeInTheDocument();
  });

  test('🚨 o eixo nao desce abaixo de zero numa serie que nunca e negativa', () => {
    // DHW e calor acumulado: nao existe acumulo negativo. A primeira versao
    // anunciava "-1,0" no rodape do eixo por causa da folga, o que se le como
    // o recife tendo perdido calor.
    render(
      <GraficoSerie
        pontos={serie([0, 0, 0.2])}
        rotulo="DHW"
        unidade="°C·semana"
        linhaDeCorte={4}
        rotuloDoCorte="Alerta"
      />
    );

    expect(screen.queryByText(/^-/)).toBeNull();
    expect(screen.getByText('0,0')).toBeInTheDocument();
  });

  test('serie com valor negativo real mantem o eixo negativo', () => {
    // O contraponto: a regra sai do dado, nao de uma lista de variaveis.
    render(<GraficoSerie pontos={serie([-2, 1])} rotulo="Anomalia" unidade="°C" />);

    expect(screen.getByText(/^-/)).toBeInTheDocument();
  });

  test('⚠️ serie constante nao achata a linha contra a borda', () => {
    const { container } = render(
      <GraficoSerie pontos={serie([4, 4, 4])} rotulo="DHW" unidade="°C·semana" />
    );

    const d = container.querySelector('path').getAttribute('d');

    expect(d).not.toContain('NaN');
  });
});

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
});
