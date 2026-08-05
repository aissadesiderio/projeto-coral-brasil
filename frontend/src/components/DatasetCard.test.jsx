/**
 * Testes do cartao do catalogo.
 *
 * 🚨 O defeito que eles travam: a pagina "Banco de Dados" anunciava **nove**
 * conjuntos e a API servia **tres**. Os outros seis apareciam com titulo,
 * formato e periodo — e nada distinguia "temos isto" de "isto existe na NOAA".
 *
 * Os tres estados precisam continuar distintos, porque nenhum implica o outro:
 * disponivel, referencia externa, e nao verificado.
 */

import { render, screen } from '@testing-library/react';

import DatasetCard from './DatasetCard';
import { normalizarDatasetCatalogo } from '../utils/datasets';

function item(cobertura) {
  return normalizarDatasetCatalogo({
    id: 'teste',
    titulo: 'CoralTemp DHW',
    resumo: 'Grade diaria de 5 km.',
    fonte: 'NOAA',
    tipo_dado: 'Oceanografico',
    localizacao: 'Abrolhos',
    estado: 'BA',
    cidade: 'Caravelas',
    formato: 'CSV',
    data_inicio: '2020-01-01',
    data_fim: '2025-11-30',
    tamanho_mb: 12,
    cobertura,
  });
}

const DISPONIVEL = {
  espelhado: true,
  motivo: null,
  n_medicoes: 14346,
  variaveis: ['dhw', 'sst'],
  locais: ['abrolhos-ba'],
  data_inicio: '2020-01-01',
  data_fim: '2026-07-24',
  consulta: '/api/medicoes/?fonte=noaa_crw&local=abrolhos-ba',
};

const EXTERNO = {
  espelhado: false,
  motivo: 'Referencia externa.',
  n_medicoes: 0,
  variaveis: [],
  locais: [],
  data_inicio: null,
  data_fim: null,
  consulta: null,
};

test('dataset servido pela API aparece como disponivel', () => {
  render(<DatasetCard item={item(DISPONIVEL)} />);

  expect(screen.getByText(/Disponivel nesta API/i)).toBeInTheDocument();
});

test('mostra o volume e o periodo reais', () => {
  render(<DatasetCard item={item(DISPONIVEL)} />);

  expect(screen.getByText(/14\.346 medicoes/)).toBeInTheDocument();
  expect(screen.getByText(/01\/01\/2020 a 24\/07\/2026/)).toBeInTheDocument();
});

test('o numero anunciado vem com o link que o comprova', () => {
  render(<DatasetCard item={item(DISPONIVEL)} />);

  expect(screen.getByRole('link', { name: /Conferir na API/i })).toHaveAttribute(
    'href',
    DISPONIVEL.consulta,
  );
});

test('🚨 dataset nao espelhado nao pode parecer disponivel', () => {
  render(<DatasetCard item={item(EXTERNO)} />);

  expect(screen.getByText(/Referencia externa/i)).toBeInTheDocument();
  expect(screen.queryByText(/Disponivel nesta API/i)).not.toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /Conferir/i })).not.toBeInTheDocument();
});

test('🚨 espelhado com zero medicoes tambem nao parece disponivel', () => {
  render(<DatasetCard item={item({ ...EXTERNO, espelhado: true })} />);

  expect(screen.getByText(/Referencia externa/i)).toBeInTheDocument();
});

test('sem cobertura no payload a tela diz que nao verificou', () => {
  // Nao e o mesmo que "nao tem": um catalogo antigo ou o fallback local caem
  // aqui, e afirmar ausencia seria inventar.
  render(<DatasetCard item={item(undefined)} />);

  expect(screen.getByText(/nao verificada/i)).toBeInTheDocument();
  expect(screen.queryByText(/Referencia externa/i)).not.toBeInTheDocument();
});

test('🚨 o periodo do arquivo e rotulado como do arquivo', () => {
  // Ele descreve o CSV inventariado, nao a cobertura da API — e apresentar um
  // como o outro foi o defeito.
  render(<DatasetCard item={item(DISPONIVEL)} />);

  expect(screen.getByText(/^Arquivo:/)).toBeInTheDocument();
});

test('download ausente continua declarado como ausente', () => {
  render(<DatasetCard item={item(DISPONIVEL)} />);

  expect(screen.getByText(/Download indisponivel/i)).toBeInTheDocument();
});
