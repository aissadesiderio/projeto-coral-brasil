/**
 * Testes da foto do recife.
 *
 * 🚨 O motivo de existirem: a correcao de 11/08/2026 (docs/FONTES.md §2.1)
 * alcancou as fotos de **especie**. A foto do **local** nao entrou naquela
 * auditoria porque nao havia nem campo de credito — e o que nao tem campo nao
 * aparece numa busca por campo errado. Ela ocupa a faixa mais visivel do site.
 *
 * ⚠️ E a licao daquele episodio precisa continuar valendo aqui: um padrao
 * calculado na leitura (`credito || 'Acervo local do projeto'`) vira
 * indistinguivel de dado real. "Sem credito informado" e texto de interface.
 */

import { render, screen } from '@testing-library/react';

import ImagemRecife from './ImagemRecife';

test('credita a foto a quem a fez', () => {
  render(
    <ImagemRecife
      nome="Abrolhos"
      imagem="/media/recifes/abrolhos.jpg"
      credito="ICMBio"
      localCaptura="Parcel dos Abrolhos, BA"
      fonteUrl="https://www.gov.br/icmbio/exemplo"
    />,
  );

  expect(screen.getByText(/Foto: ICMBio/)).toBeInTheDocument();
  expect(screen.getByText(/tirada em Parcel dos Abrolhos, BA/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /Ver fonte da imagem/ })).toHaveAttribute(
    'href',
    'https://www.gov.br/icmbio/exemplo',
  );
});

test('sem credito, diz que nao ha — e nao inventa um', () => {
  render(<ImagemRecife nome="Abrolhos" imagem="/media/recifes/abrolhos.jpg" />);

  expect(screen.getByText(/Foto sem credito informado/)).toBeInTheDocument();
  expect(screen.queryByText(/Acervo local do projeto/)).not.toBeInTheDocument();
});

test('local de captura e opcional', () => {
  render(
    <ImagemRecife
      nome="Abrolhos"
      imagem="/media/recifes/abrolhos.jpg"
      credito="ICMBio"
    />,
  );

  expect(screen.getByText(/Foto: ICMBio/)).toBeInTheDocument();
  expect(screen.queryByText(/tirada em/)).not.toBeInTheDocument();
});

test('sem fonte nao ha link a oferecer', () => {
  render(
    <ImagemRecife
      nome="Abrolhos"
      imagem="/media/recifes/abrolhos.jpg"
      credito="ICMBio"
    />,
  );

  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});

test('sem foto nenhuma nao ha credito a discutir', () => {
  // O gradiente do fallback e desenhado pelo proprio site: uma legenda
  // dizendo "sem credito" debaixo dele seria falsa.
  render(<ImagemRecife nome="Abrolhos" imagem="" />);

  expect(screen.queryByText(/credito/i)).not.toBeInTheDocument();
  expect(screen.getByText('Abrolhos')).toBeInTheDocument();
});
