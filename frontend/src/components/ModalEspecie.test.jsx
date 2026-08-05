/**
 * Testes do modal de especie.
 *
 * 🚨 O foco e um so: **a tela nao pode afirmar uma categoria de conservacao
 * que ninguem consegue datar.**
 *
 * Categoria da IUCN tem prazo de validade invisivel. `Dendrogyra cylindrus`,
 * que esta neste acervo, foi *Vulneravel* de 2008 a 2022 e hoje e
 * *Criticamente Ameacada* — as duas afirmacoes certas, em anos diferentes.
 */

import { render, screen } from '@testing-library/react';

import ModalEspecie from './ModalEspecie';

function especie(extras = {}) {
  return {
    id: 1,
    nome_cientifico: 'Dendrogyra cylindrus',
    nome_comum: 'Coral-pilar',
    descricao: 'Coral formador de recife.',
    iucn_categoria: 'CR',
    iucn_categoria_rotulo: 'Criticamente ameacada',
    iucn_avaliado_em: 2022,
    iucn_versao: '2024-1',
    fonte_iucn_url: 'https://www.iucnredlist.org/species/133184/16576167',
    iucn_tem_procedencia: true,
    ...extras,
  };
}

test('com procedencia, mostra a categoria com o ano e a versao', () => {
  render(<ModalEspecie especie={especie()} onClose={() => {}} />);

  expect(screen.getByText('Criticamente ameacada')).toBeInTheDocument();
  expect(screen.getByText(/Avaliada em 2022/)).toBeInTheDocument();
  expect(screen.getByText(/Lista Vermelha 2024-1/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /ficha na IUCN/i })).toHaveAttribute(
    'href',
    expect.stringContaining('iucnredlist.org'),
  );
});

test('🚨 sem o ano, a categoria NAO e exibida', () => {
  // O estado das nove especies herdadas da lista digitada a mao.
  render(
    <ModalEspecie
      especie={especie({
        iucn_avaliado_em: null,
        iucn_versao: '',
        fonte_iucn_url: '',
        iucn_tem_procedencia: false,
      })}
      onClose={() => {}}
    />
  );

  expect(screen.getByText(/sem procedencia registrada/i)).toBeInTheDocument();
  expect(screen.queryByText('Criticamente ameacada')).not.toBeInTheDocument();
  expect(screen.queryByText('CR')).not.toBeInTheDocument();
});

test('🚨 campo vazio nao vira "Nao avaliado"', () => {
  // O defeito anterior era `status_conservacao || 'Nao avaliado'`: "nao
  // sabemos" e "a IUCN avaliou como NE" saiam identicos na tela, e NE e uma
  // categoria real da Lista Vermelha.
  render(
    <ModalEspecie
      especie={especie({
        iucn_categoria: '',
        iucn_categoria_rotulo: '',
        iucn_avaliado_em: null,
        iucn_tem_procedencia: false,
      })}
      onClose={() => {}}
    />
  );

  expect(screen.queryByText(/^Nao avaliad/i)).not.toBeInTheDocument();
  expect(screen.getByText(/sem procedencia registrada/i)).toBeInTheDocument();
});

test('⚠️ resposta antiga da API, sem o campo, tambem nao afirma', () => {
  // Um cliente contra servidor antigo nao recebe `iucn_tem_procedencia`. O
  // padrao precisa ser nao afirmar, e nao afirmar por omissao.
  render(
    <ModalEspecie
      especie={{ id: 2, nome_cientifico: 'Especie antiga', nome_comum: 'Teste' }}
      onClose={() => {}}
    />
  );

  expect(screen.getByText(/sem procedencia registrada/i)).toBeInTheDocument();
});
