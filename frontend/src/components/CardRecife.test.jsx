/**
 * Testes do cartao da listagem.
 *
 * 🚨 O motivo de existirem: o cartao e a **segunda superficie** que exibe
 * risco. Enquanto o painel de detalhe passou a usar o modelo novo e o cartao
 * continuava no legado, os dois mostravam numeros diferentes para o mesmo
 * recife, cada um de um modelo, sem nada indicando qual valia.
 *
 * E a regra de nunca escrever "0%" nem "100%" precisa valer aqui tambem — por
 * isso a formatacao passa pelos mesmos helpers, e nao por um `toFixed` local.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import CardRecife from './CardRecife';

const LOCAL = {
  slug: 'abrolhos-ba',
  nome: 'Abrolhos',
  estado: 'Bahia',
  cidade: 'Caravelas',
  quantidade_especies: 5,
  // Campos do caminho legado: continuam no objeto e **nao** podem aparecer.
  risco_atual: 78,
  nivel_alerta: 'ALERTA_1',
};

function predicao(extras = {}) {
  return {
    local: 'abrolhos-ba',
    disponivel: true,
    probabilidade: 0.073,
    limiar: 0.2,
    alerta: false,
    no_extremo: false,
    data_base: '2026-07-24',
    ...extras,
  };
}

function montar(props = {}) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <CardRecife local={LOCAL} {...props} />
    </MemoryRouter>,
  );
}

test('exibe a probabilidade do modelo', () => {
  montar({ predicao: predicao() });

  expect(screen.getByText('7,3%')).toBeInTheDocument();
});

test('🚨 nao exibe o risco do caminho legado', () => {
  montar({ predicao: predicao() });

  expect(screen.queryByText('78,0%')).not.toBeInTheDocument();
  expect(screen.queryByText(/Risco atual/i)).not.toBeInTheDocument();
});

test('🚨 sem predicao nao cai de volta no numero legado', () => {
  montar({ predicao: null });

  expect(screen.getByText('Nao calculado')).toBeInTheDocument();
  expect(screen.queryByText('78,0%')).not.toBeInTheDocument();
});

test('🚨 probabilidade zero exata nao vira "0%" nem no cartao', () => {
  montar({ predicao: predicao({ probabilidade: 0, no_extremo: true }) });

  expect(screen.queryByText('0%')).not.toBeInTheDocument();
  expect(screen.queryByText('0,0%')).not.toBeInTheDocument();
  expect(screen.getByText(/faixa mais baixa/i)).toBeInTheDocument();
});

test('o selo e binario, e nao os quatro niveis do modelo legado', () => {
  montar({ predicao: predicao({ alerta: true }) });

  expect(screen.getByText('Alerta termico')).toBeInTheDocument();
  expect(screen.queryByText(/Alerta nivel/i)).not.toBeInTheDocument();
});

test('sem alerta aparece como sem alerta', () => {
  montar({ predicao: predicao({ alerta: false }) });

  expect(screen.getByText('Sem alerta')).toBeInTheDocument();
});

test('sem predicao o selo diz que nao ha previsao', () => {
  montar({ predicao: null });

  expect(screen.getByText('Sem previsao')).toBeInTheDocument();
});

test('mostra a data-base do calculo', () => {
  montar({ predicao: predicao() });

  expect(screen.getByText(/dados ate 24\/07\/2026/)).toBeInTheDocument();
});

test('recife sem dado suficiente nao exibe numero', () => {
  montar({ predicao: predicao({ disponivel: false, probabilidade: undefined }) });

  expect(screen.getByText('Nao calculado')).toBeInTheDocument();
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});

test('o rotulo diz estresse termico, nao branqueamento', () => {
  montar({ predicao: predicao() });

  expect(screen.getByText(/Estresse termico em 7 dias/i)).toBeInTheDocument();
});
