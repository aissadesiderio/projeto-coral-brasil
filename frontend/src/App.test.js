import { fireEvent, render, screen } from '@testing-library/react';

import App from './App';

test('renderiza a pagina inicial com destaque para explorar recifes', () => {
  render(<App />);

  expect(screen.getAllByText(/Projeto Coral Brasil/i).length).toBeGreaterThan(0);
  expect(
    screen.getByRole('heading', { name: /Mergulhe na biodiversidade coralina brasileira/i }),
  ).toBeInTheDocument();
  expect(screen.getByText(/Recifes Monitorados/i)).toBeInTheDocument();
});

test('altera a navegacao do topo conforme a pagina atual', () => {
  render(<App />);

  fireEvent.click(screen.getAllByRole('button', { name: /Explorar recifes/i })[0]);

  expect(screen.getAllByRole('button', { name: /Pagina inicial/i }).length).toBeGreaterThan(0);
  expect(screen.getAllByRole('button', { name: /Banco de dados/i }).length).toBeGreaterThan(0);
  expect(screen.queryByRole('button', { name: /Explorar recifes/i })).not.toBeInTheDocument();

  fireEvent.click(screen.getAllByRole('button', { name: /Banco de dados/i })[0]);

  expect(screen.getAllByRole('button', { name: /Pagina inicial/i }).length).toBeGreaterThan(0);
  expect(screen.getAllByRole('button', { name: /Explorar recifes/i }).length).toBeGreaterThan(0);
  expect(screen.queryByRole('button', { name: /Banco de dados/i })).not.toBeInTheDocument();
});
