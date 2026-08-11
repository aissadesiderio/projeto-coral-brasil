import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import CadastroPage from './CadastroPage';

const FUTURE = { v7_startTransition: true, v7_relativeSplatPath: true };

function renderComRotas(props) {
  return render(
    <MemoryRouter initialEntries={['/cadastro']} future={FUTURE}>
      <Routes>
        <Route path="/cadastro" element={<CadastroPage {...props} />} />
        <Route path="/minhas-especies" element={<div>Pagina de minhas especies</div>} />
        <Route path="/login" element={<div>Pagina de login</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CadastroPage', () => {
  test('envia usuario, email e senha para onCadastrar', async () => {
    const onCadastrar = jest.fn().mockResolvedValue({ ok: true, status: 201, dados: {} });

    renderComRotas({ onCadastrar, usuario: null });

    fireEvent.change(screen.getByLabelText(/Usuario/i), { target: { value: 'visitante' } });
    fireEvent.change(screen.getByLabelText(/E-mail/i), { target: { value: 'v@example.com' } });
    fireEvent.change(screen.getByLabelText(/Senha/i), { target: { value: 'uma-senha-forte' } });
    fireEvent.click(screen.getByRole('button', { name: /Criar conta/i }));

    await waitFor(() =>
      expect(onCadastrar).toHaveBeenCalledWith('visitante', 'v@example.com', 'uma-senha-forte'),
    );
  });

  test('mostra a mensagem de erro quando o cadastro falha', async () => {
    const onCadastrar = jest.fn().mockResolvedValue({
      ok: false,
      status: 400,
      dados: { detail: 'Este nome de usuario ja existe.' },
    });

    renderComRotas({ onCadastrar, usuario: null });

    fireEvent.change(screen.getByLabelText(/Usuario/i), { target: { value: 'ja-existe' } });
    fireEvent.change(screen.getByLabelText(/Senha/i), { target: { value: 'uma-senha-forte' } });
    fireEvent.click(screen.getByRole('button', { name: /Criar conta/i }));

    expect(await screen.findByText(/Este nome de usuario ja existe/i)).toBeInTheDocument();
  });

  test('navega para minhas especies depois do cadastro', async () => {
    const onCadastrar = jest.fn().mockResolvedValue({ ok: true, status: 201, dados: {} });

    renderComRotas({ onCadastrar, usuario: null });

    fireEvent.change(screen.getByLabelText(/Usuario/i), { target: { value: 'visitante' } });
    fireEvent.change(screen.getByLabelText(/Senha/i), { target: { value: 'uma-senha-forte' } });
    fireEvent.click(screen.getByRole('button', { name: /Criar conta/i }));

    expect(await screen.findByText(/Pagina de minhas especies/i)).toBeInTheDocument();
  });

  test('quem ja esta logado nao ve o formulario de cadastro', async () => {
    renderComRotas({ onCadastrar: jest.fn(), usuario: { autenticado: true } });

    expect(await screen.findByText(/Pagina de minhas especies/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Usuario/i)).toBeNull();
  });
});
