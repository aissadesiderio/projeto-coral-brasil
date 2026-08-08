import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import GerenciarEspeciesPage from './GerenciarEspeciesPage';

const FUTURE = { v7_startTransition: true, v7_relativeSplatPath: true };

function criarResposta(payload, { ok = true, status = 200 } = {}) {
  return { ok, status, json: async () => payload };
}

function renderPagina(usuario) {
  return render(
    <MemoryRouter future={FUTURE}>
      <GerenciarEspeciesPage usuario={usuario} />
    </MemoryRouter>,
  );
}

afterEach(() => {
  delete global.fetch;
});

describe('GerenciarEspeciesPage', () => {
  test('deslogado, pede para fazer login em vez de mostrar o formulario', () => {
    renderPagina({ autenticado: false });

    expect(screen.getByText(/Faca login para contribuir/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Nome cientifico/i)).toBeNull();
  });

  test('logado e nao aprovado, avisa que a conta aguarda aprovacao', () => {
    renderPagina({ autenticado: true, aprovado: false, master: false });

    expect(screen.getByText(/ainda nao foi aprovada/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Nome cientifico/i)).toBeNull();
  });

  test('usuario aprovado: espécie nova vira solicitacao pendente (202)', async () => {
    global.fetch = jest.fn(async (url, opcoes = {}) => {
      if (url === '/api/especies/' && (!opcoes.method || opcoes.method === 'GET')) {
        return criarResposta([]);
      }
      if (url === '/api/especies/' && opcoes.method === 'POST') {
        return criarResposta({ detail: 'Enviado para revisao.' }, { status: 202 });
      }
      return criarResposta({}, { ok: false, status: 404 });
    });

    renderPagina({ autenticado: true, aprovado: true, master: false });

    await waitFor(() =>
      expect(screen.getByText(/Nenhuma especie cadastrada/i)).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByLabelText(/Nome cientifico/i), {
      target: { value: 'Testus jestus' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Adicionar especie/i }));

    expect(await screen.findByText(/Enviado para revisao/i)).toBeInTheDocument();
  });

  test('master: cria direto (201) e a lista recarrega', async () => {
    let jaChamouPost = false;
    global.fetch = jest.fn(async (url, opcoes = {}) => {
      if (url === '/api/especies/' && opcoes.method === 'POST') {
        jaChamouPost = true;
        return criarResposta({ id: 1, nome_cientifico: 'Testus jestus' }, { status: 201 });
      }
      if (url === '/api/especies/') {
        return criarResposta(
          jaChamouPost
            ? [{ id: 1, nome_cientifico: 'Testus jestus', nome_comum: 'Coral jestus', tipo: 'CORAL' }]
            : [],
        );
      }
      return criarResposta({}, { ok: false, status: 404 });
    });

    renderPagina({ autenticado: true, aprovado: false, master: true });

    await waitFor(() =>
      expect(screen.getByText(/Nenhuma especie cadastrada/i)).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByLabelText(/Nome cientifico/i), {
      target: { value: 'Testus jestus' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Adicionar especie/i }));

    expect(await screen.findByText(/Especie criada/i)).toBeInTheDocument();
    expect(await screen.findByText('Testus jestus')).toBeInTheDocument();
  });

  test('🚨 so master ve quem criou/editou cada especie', async () => {
    global.fetch = jest.fn(async (url) => {
      if (url === '/api/especies/') {
        return criarResposta([
          {
            id: 1,
            nome_cientifico: 'Autorus testus',
            nome_comum: 'Coral teste',
            tipo: 'CORAL',
            autor: { criado_por: 'comum', editado_por: null },
          },
        ]);
      }
      return criarResposta({}, { ok: false, status: 404 });
    });

    renderPagina({ autenticado: true, aprovado: false, master: true });

    expect(await screen.findByText(/criado por comum/i)).toBeInTheDocument();
  });
});
