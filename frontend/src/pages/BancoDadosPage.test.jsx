import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import BancoDadosPage from './BancoDadosPage';

function criarRespostaJson(payload, ok = true) {
  return {
    ok,
    json: async () => payload,
  };
}

afterEach(() => {
  jest.resetAllMocks();
});

test('busca datasets na API real e preserva os filtros em memoria', async () => {
  global.fetch = jest.fn(async (url) => {
    if (url === '/api/datasets/') {
      return criarRespostaJson([
        {
          id: 'dataset_api_1',
          titulo: 'Temperatura API Abrolhos',
          resumo: 'Catalogo vindo do backend.',
          fonte: 'Copernicus',
          tipo_dado: 'Climatico',
          localizacao: 'Parque Nacional Marinho de Abrolhos',
          estado: 'Bahia',
          cidade: 'Caravelas',
          formato: 'CSV',
          recorte_temporal: 'intervalo',
          data_inicio: '2026-03-01',
          data_fim: '2026-03-31',
          periodo_rotulo: 'Mar/2026',
          tamanho_mb: 1843.2,
          url_download: '/dados/api-abrolhos.csv',
        },
        {
          id: 'dataset_api_2',
          titulo: 'Microbioma API Picaozinho',
          resumo: 'Segundo dataset vindo do backend.',
          fonte: 'NCBI',
          tipo_dado: 'Microbioma',
          localizacao: 'Recife de Picaozinho',
          estado: 'Paraiba',
          cidade: 'Joao Pessoa',
          formato: 'FASTQ',
          recorte_temporal: 'publicacao',
          data_publicacao: '2026-04-18',
          periodo_rotulo: 'Abr/2026',
          tamanho_mb: 3174.4,
          url_download: '',
        },
      ]);
    }

    return criarRespostaJson({}, false);
  });

  render(<BancoDadosPage />);

  expect(await screen.findByText(/Temperatura API Abrolhos/i)).toBeInTheDocument();
  expect(screen.getByText(/Microbioma API Picaozinho/i)).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(/Fonte/i), {
    target: { value: 'NCBI' },
  });

  expect(screen.queryByText(/Temperatura API Abrolhos/i)).not.toBeInTheDocument();
  expect(screen.getByText(/Microbioma API Picaozinho/i)).toBeInTheDocument();
  expect(screen.getByText(/1 dataset\(s\)/i)).toBeInTheDocument();
});

test('usa fallback local apenas quando a API falha', async () => {
  global.fetch = jest.fn(async () => criarRespostaJson({}, false));

  render(<BancoDadosPage />);

  expect(
    await screen.findByText(/Nao foi possivel carregar o catalogo pela API agora/i),
  ).toBeInTheDocument();
  expect(screen.getByText(/Temperatura da superficie do mar - Abrolhos/i)).toBeInTheDocument();
});

test('nao quebra quando a API retorna um catalogo vazio', async () => {
  global.fetch = jest.fn(async (url) => {
    if (url === '/api/datasets/') {
      return criarRespostaJson([]);
    }

    return criarRespostaJson({}, false);
  });

  render(<BancoDadosPage />);

  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith('/api/datasets/'));
  expect(
    await screen.findByText(/Nenhum conjunto de dados corresponde aos filtros atuais/i),
  ).toBeInTheDocument();
  expect(screen.getByText(/0 dataset\(s\)/i)).toBeInTheDocument();
});
