import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { FALLBACK_RECIFES } from '../data/recifeData';
import LocalRecifeRoutePage from './LocalRecifeRoutePage';

function criarRespostaJson(payload, ok = true) {
  return {
    ok,
    json: async () => payload,
  };
}

function renderizarPagina(props = {}) {
  return render(
    <MemoryRouter
      initialEntries={['/localizacoes/abrolhos-ba']}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route
          path="/localizacoes/:slug"
          element={
            <LocalRecifeRoutePage
              locais={[FALLBACK_RECIFES[0]]}
              carregandoLocais={false}
              detalhesPorSlug={{ 'abrolhos-ba': {} }}
              setDetalhesPorSlug={jest.fn()}
              siteOffline={false}
              offlineMessage=""
              onOpenEspecie={jest.fn()}
              {...props}
            />
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  jest.resetAllMocks();
});

test('mostra estado vazio elegante quando a API retorna nenhum dataset relacionado', async () => {
  global.fetch = jest.fn(async (url) => {
    if (url === '/api/locais/abrolhos-ba/datasets/') {
      return criarRespostaJson([]);
    }

    return criarRespostaJson({}, false);
  });

  renderizarPagina();

  await waitFor(() =>
    expect(global.fetch).toHaveBeenCalledWith('/api/locais/abrolhos-ba/datasets/'),
  );
  expect(
    await screen.findByText(/Ainda nao ha datasets relacionados diretamente a esta localizacao/i),
  ).toBeInTheDocument();
});

test('usa fallback transitorio quando a API de datasets relacionados falha', async () => {
  global.fetch = jest.fn(async () => criarRespostaJson({}, false));

  renderizarPagina();

  expect(
    await screen.findByText(/Nao foi possivel atualizar os datasets relacionados por API agora/i),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Exibindo uma referencia local transitoria quando disponivel/i),
  ).toBeInTheDocument();
  expect(screen.getByText(/Temperatura da superficie do mar - Abrolhos/i)).toBeInTheDocument();
});
