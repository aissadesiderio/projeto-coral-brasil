import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import LoginPage from './LoginPage';

const FUTURE = { v7_startTransition: true, v7_relativeSplatPath: true };

function renderComRotas(props) {
  return render(
    <MemoryRouter initialEntries={['/login']} future={FUTURE}>
      <Routes>
        <Route path="/login" element={<LoginPage {...props} />} />
        <Route path="/minhas-especies" element={<div>Pagina de minhas especies</div>} />
        <Route path="/cadastro" element={<div>Pagina de cadastro</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LoginPage', () => {
  test('envia usuario e senha digitados para onLogin', async () => {
    const onLogin = jest.fn().mockResolvedValue({ ok: true, status: 200, dados: {} });

    renderComRotas({ onLogin, usuario: null });

    fireEvent.change(screen.getByLabelText(/Usuario/i), { target: { value: 'visitante' } });
    fireEvent.change(screen.getByLabelText(/Senha/i), { target: { value: 'senha-123' } });
    fireEvent.click(screen.getByRole('button', { name: /Entrar/i }));

    await waitFor(() => expect(onLogin).toHaveBeenCalledWith('visitante', 'senha-123'));
  });

  test('mostra a mensagem de erro do backend quando o login falha', async () => {
    const onLogin = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      dados: { detail: 'Usuario ou senha invalidos.' },
    });

    renderComRotas({ onLogin, usuario: null });

    fireEvent.change(screen.getByLabelText(/Usuario/i), { target: { value: 'visitante' } });
    fireEvent.change(screen.getByLabelText(/Senha/i), { target: { value: 'errada' } });
    fireEvent.click(screen.getByRole('button', { name: /Entrar/i }));

    expect(await screen.findByText(/Usuario ou senha invalidos/i)).toBeInTheDocument();
  });

  test('navega para minhas especies depois de logar', async () => {
    const onLogin = jest.fn().mockResolvedValue({ ok: true, status: 200, dados: {} });

    renderComRotas({ onLogin, usuario: null });

    fireEvent.change(screen.getByLabelText(/Usuario/i), { target: { value: 'visitante' } });
    fireEvent.change(screen.getByLabelText(/Senha/i), { target: { value: 'senha-123' } });
    fireEvent.click(screen.getByRole('button', { name: /Entrar/i }));

    expect(await screen.findByText(/Pagina de minhas especies/i)).toBeInTheDocument();
  });

  test('🚨 quem ja esta logado nunca ve o formulario de novo', async () => {
    renderComRotas({ onLogin: jest.fn(), usuario: { autenticado: true } });

    expect(await screen.findByText(/Pagina de minhas especies/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Usuario/i)).toBeNull();
  });
});
