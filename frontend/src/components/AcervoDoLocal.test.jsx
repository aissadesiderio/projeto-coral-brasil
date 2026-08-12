/**
 * Testes da tabela do acervo.
 *
 * 🚨 O motivo de existirem: a tela do recife desenhava duas variaveis e o
 * projeto guardava oito. As outras seis — ~7.200 medicoes de cada, por local,
 * desde 2020 — nao apareciam em numero nenhum do site, e quem visitasse
 * concluiria, corretamente pelo que via, que so ha SST e DHW.
 *
 * 🚨 E a leitura errada oposta precisa continuar impossivel: listar `baa` ao
 * lado de `sst` sem dizer o papel de cada uma faria o alvo do modelo passar por
 * entrada dele.
 */

import { render, screen } from '@testing-library/react';

import AcervoDoLocal from './AcervoDoLocal';

const ACERVO = [
  {
    variavel: 'sst',
    nome: 'Temperatura da superficie do mar',
    unidade: '°C',
    n_medicoes: 7173,
    data_inicio: '2020-01-01',
    data_fim: '2026-07-24',
    fontes: ['noaa_crw'],
    papel: 'feature',
    papel_rotulo: 'Entra na previsao',
    entra_no_modelo: true,
    motivo: null,
    consulta: '/api/medicoes/?local=abrolhos-ba&variavel=sst',
  },
  {
    variavel: 'baa',
    nome: 'Bleaching Alert Area',
    unidade: '0-5',
    n_medicoes: 7173,
    data_inicio: '2020-01-01',
    data_fim: '2026-07-24',
    fontes: ['noaa_crw'],
    papel: 'alvo',
    papel_rotulo: 'E o que o modelo preve',
    entra_no_modelo: false,
    motivo: 'O modelo servido preve "baa >= 3 daqui a 7 dias".',
    consulta: '/api/medicoes/?local=abrolhos-ba&variavel=baa',
  },
  {
    variavel: 'oxigenio',
    nome: 'Oxigenio dissolvido',
    unidade: 'mmol/m³',
    n_medicoes: 7191,
    data_inicio: '2020-01-01',
    data_fim: '2026-07-24',
    fontes: ['copernicus'],
    papel: 'feature',
    papel_rotulo: 'Entra na previsao',
    entra_no_modelo: true,
    motivo: null,
    consulta: '/api/medicoes/?local=abrolhos-ba&variavel=oxigenio',
  },
];

test('mostra as variaveis que o grafico nao desenha', () => {
  render(<AcervoDoLocal acervo={ACERVO} />);

  expect(screen.getByText(/Oxigenio dissolvido/)).toBeInTheDocument();
  expect(screen.getByText(/Bleaching Alert Area/)).toBeInTheDocument();
});

test('diz o papel de cada variavel no modelo', () => {
  render(<AcervoDoLocal acervo={ACERVO} />);

  expect(screen.getByText('E o que o modelo preve')).toBeInTheDocument();
  expect(screen.getAllByText('Entra na previsao')).toHaveLength(2);
});

test('cada contagem leva ao endpoint que a devolve', () => {
  render(<AcervoDoLocal acervo={ACERVO} />);

  const link = screen.getByRole('link', { name: '7.191' });
  expect(link).toHaveAttribute(
    'href',
    '/api/medicoes/?local=abrolhos-ba&variavel=oxigenio',
  );
});

test('resume o total e quantas entram na previsao', () => {
  render(<AcervoDoLocal acervo={ACERVO} />);

  expect(screen.getByText('21.537 medicoes')).toBeInTheDocument();
  expect(
    screen.getByText(/2 delas entra\(m\) na previsao/),
  ).toBeInTheDocument();
});

test('sem medicao nenhuma nao inventa tabela vazia', () => {
  render(<AcervoDoLocal acervo={[]} />);

  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  expect(screen.getByText(/Nenhuma medicao ingerida/)).toBeInTheDocument();
});
