import { render, screen } from '@testing-library/react';
import App from './App';

test('renderiza o cabecalho e a introducao principal', () => {
  render(<App />);

  expect(screen.getByText(/Projeto Coral Brasil/i)).toBeInTheDocument();
  expect(
    screen.getAllByRole('button', { name: /Banco de dados geral/i }).length,
  ).toBeGreaterThan(0);
  expect(
    screen.getByText(/Monitoramento integrado para recifes de coral do Brasil/i),
  ).toBeInTheDocument();
});
