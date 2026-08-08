import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import Header from './Header';

const FUTURE = { v7_startTransition: true, v7_relativeSplatPath: true };

function renderHeader(props) {
  return render(
    <MemoryRouter future={FUTURE}>
      <Header paginaAtual="home" {...props} />
    </MemoryRouter>,
  );
}

describe('Header — widget de conta', () => {
  test('deslogado, mostra Entrar e Cadastrar', () => {
    renderHeader({ usuario: { autenticado: false } });

    expect(screen.getByRole('link', { name: 'Entrar' })).toHaveAttribute('href', '/login');
    expect(screen.getByRole('link', { name: 'Cadastrar' })).toHaveAttribute('href', '/cadastro');
    expect(screen.queryByText(/Sair/i)).toBeNull();
  });

  test('logado, mostra o usuario e o botao de sair', () => {
    renderHeader({ usuario: { autenticado: true, username: 'visitante', master: false } });

    expect(screen.getByText('visitante')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Minhas especies/i })).toHaveAttribute(
      'href',
      '/minhas-especies',
    );
    expect(screen.queryByRole('link', { name: 'Entrar' })).toBeNull();
  });

  test('master aparece marcado ao lado do nome', () => {
    renderHeader({ usuario: { autenticado: true, username: 'admin', master: true } });

    // O nome e o selo "(master)" saem como dois nos de texto dentro do mesmo
    // <span> — por isso um regex parcial, e nao a string exata "admin".
    expect(screen.getByText(/^admin/)).toBeInTheDocument();
    expect(screen.getByText(/\(master\)/)).toBeInTheDocument();
  });

  test('clicar em Sair chama onLogout', () => {
    const onLogout = jest.fn();
    renderHeader({ usuario: { autenticado: true, username: 'visitante' }, onLogout });

    fireEvent.click(screen.getByRole('button', { name: /Sair/i }));

    expect(onLogout).toHaveBeenCalledTimes(1);
  });
});
