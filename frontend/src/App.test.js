import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import App from './App';

function criarRespostaJson(payload, ok = true) {
  return {
    ok,
    json: async () => payload,
  };
}

function renderizarApp(rotaInicial = '/') {
  return render(
    <MemoryRouter
      initialEntries={[rotaInicial]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  window.scrollTo = jest.fn();
  global.fetch = jest.fn(async (url) => {
    if (url === '/api/status/') {
      return criarRespostaJson({ offline_mode: false, message: '' });
    }

    if (url === '/api/grafo/localizacoes/') {
      return criarRespostaJson([
        {
          slug: 'abrolhos-ba',
          nome: 'Parque Nacional Marinho de Abrolhos',
          estado: 'Bahia',
          cidade: 'Caravelas',
          descricao: 'Area de referencia para monitoramento e biodiversidade coralinea.',
          quantidade_especies: 5,
          risco_atual: 78,
          nivel_alerta: 'ALERTA_1',
          ultima_predicao_data: '2026-04-14',
          monitoramento_recente: {
            data: '2026-04-14',
            risco_integrado: 78,
            nivel_alerta: 'ALERTA_1',
          },
        },
      ]);
    }

    if (url === '/api/grafo/localizacoes/abrolhos-ba/') {
      return criarRespostaJson({
        especies: [
          {
            id: 'mussismilia-braziliensis',
            nome_comum: 'Coral-cerebro brasileiro',
            nome_cientifico: 'Mussismilia braziliensis',
          },
        ],
        monitoramento_recente: {
          data: '2026-04-14',
          risco_integrado: 78,
          nivel_alerta: 'ALERTA_1',
        },
      });
    }

    if (url === '/api/locais/abrolhos-ba/datasets/') {
      return criarRespostaJson([
        {
          id: 'dataset_relacionado_abrolhos',
          titulo: 'Dataset relacionado via API',
          resumo: 'Catalogo associado ao detalhe do recife.',
          fonte: 'Projeto Coral Brasil',
          tipo_dado: 'Relatorio',
          localizacao: 'Parque Nacional Marinho de Abrolhos',
          local_slug: 'abrolhos-ba',
          estado: 'Bahia',
          cidade: 'Caravelas',
          formato: 'PDF',
          recorte_temporal: 'publicacao',
          data_publicacao: '2026-04-18',
          periodo_rotulo: 'Abr/2026',
          tamanho_mb: 12,
          url_download: '/dados/relatorio.pdf',
        },
      ]);
    }

    if (url === '/api/datasets/') {
      return criarRespostaJson([]);
    }

    return criarRespostaJson({}, false);
  });
});

afterEach(() => {
  jest.resetAllMocks();
});

test('renderiza a pagina inicial com o monitor da costa', async () => {
  renderizarApp('/');

  expect(screen.getAllByText(/Projeto Coral Brasil/i).length).toBeGreaterThan(0);
  expect(
    screen.getByRole('heading', { name: /Os recifes brasileiros, medidos dia a dia/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: /Estado da costa hoje/i })).toBeInTheDocument();
  expect(screen.getByText(/Pagina por localizacao/i)).toBeInTheDocument();
  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith('/api/grafo/localizacoes/'));
});

/**
 * 🚨 A barra do topo e **fixa**, e a pagina atual vem marcada.
 *
 * Ate 13/08/2026 cada rota escondia o proprio link da navegacao, e o teste que
 * ficava no lugar deste conferia justamente a ausencia. Numa barra de tres
 * itens, "o que falta e onde voce esta" e uma pista que ninguem le — e a barra
 * mudava de largura a cada clique. Ver `utils/navigation.obterItensNavegacao`.
 */
test('a navegacao do topo e fixa e marca a pagina atual', async () => {
  const { unmount } = renderizarApp('/localizacoes');

  expect((await screen.findAllByText(/Parque Nacional Marinho de Abrolhos/i)).length).toBeGreaterThan(0);

  expect(screen.getByRole('link', { name: 'Costa' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Dados' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Localizacoes' })).toHaveAttribute(
    'aria-current',
    'page',
  );
  expect(screen.getByRole('link', { name: 'Costa' })).not.toHaveAttribute('aria-current');

  unmount();
  renderizarApp('/banco-de-dados');
  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith('/api/grafo/localizacoes/'));

  expect(screen.getByRole('link', { name: 'Dados' })).toHaveAttribute('aria-current', 'page');
  expect(screen.getByRole('link', { name: 'Localizacoes' })).not.toHaveAttribute('aria-current');
});

test('abre o detalhe diretamente pela rota e usa o slug da URL', async () => {
  renderizarApp('/localizacoes/abrolhos-ba');

  expect(
    await screen.findByRole('heading', { name: /Parque Nacional Marinho de Abrolhos/i }),
  ).toBeInTheDocument();
  expect(await screen.findByText(/Dataset relacionado via API/i)).toBeInTheDocument();
  expect(global.fetch).toHaveBeenCalledWith('/api/grafo/localizacoes/abrolhos-ba/');
  expect(global.fetch).toHaveBeenCalledWith('/api/locais/abrolhos-ba/datasets/');
});
