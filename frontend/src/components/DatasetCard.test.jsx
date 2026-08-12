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
import { MemoryRouter } from 'react-router-dom';

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

/**
 * O download que sai deste projeto, e nao do provedor.
 *
 * 🚨 Desde 12/08/2026 metade do catalogo aponta para
 * `/api/medicoes/?formato=csv` — o proprio banco —, e esse endpoint exige conta
 * aprovada. Um `<a>` simples ali faria o visitante deslogado clicar em "Baixar
 * conjunto" e receber um JSON de 401 aberto no navegador.
 */
function itemBaixavel(extras = {}) {
  return normalizarDatasetCatalogo({
    id: 'serie-noaa_crw-noronha',
    titulo: 'Estresse termico - Noronha',
    resumo: 'Serie diaria.',
    fonte: 'NOAA',
    tipo_dado: 'Oceanografico',
    localizacao: 'Fernando de Noronha',
    estado: 'Pernambuco',
    cidade: 'Fernando de Noronha',
    formato: 'CSV',
    url_download: '/api/medicoes/?local=noronha&fonte=noaa_crw&formato=csv',
    download_exige_conta: true,
    cobertura: DISPONIVEL,
    ...extras,
  });
}

test('🚨 download que exige conta nao vira botao para quem nao esta aprovado', () => {
  render(
    <MemoryRouter>
      <DatasetCard item={itemBaixavel()} usuario={null} />
    </MemoryRouter>,
  );

  expect(screen.getByRole('link', { name: /Faca login/i })).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /Baixar conjunto/i })).not.toBeInTheDocument();
});

test('conta aprovada recebe o link de download de verdade', () => {
  render(
    <MemoryRouter>
      <DatasetCard item={itemBaixavel()} usuario={{ aprovado: true }} />
    </MemoryRouter>,
  );

  expect(screen.getByRole('link', { name: /Baixar conjunto/i })).toHaveAttribute(
    'href',
    '/api/medicoes/?local=noronha&fonte=noaa_crw&formato=csv',
  );
});

test('⚠️ download do provedor nao pede login a ninguem', () => {
  // O erro simetrico: esconder atras de um convite ao login um arquivo que
  // qualquer um poderia baixar direto da NOAA.
  render(
    <MemoryRouter>
      <DatasetCard
        item={itemBaixavel({ download_exige_conta: false })}
        usuario={null}
      />
    </MemoryRouter>,
  );

  expect(screen.getByRole('link', { name: /Baixar conjunto/i })).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /Faca login/i })).not.toBeInTheDocument();
});

test('catalogo antigo sem o campo nao passa a exigir conta', () => {
  // `undefined` precisa cair em "nao exige". Assumir `true` esconderia
  // downloads livres atras de um login que ninguem pediu.
  render(
    <MemoryRouter>
      <DatasetCard item={itemBaixavel({ download_exige_conta: undefined })} usuario={null} />
    </MemoryRouter>,
  );

  expect(screen.getByRole('link', { name: /Baixar conjunto/i })).toBeInTheDocument();
});

test('dataset de serie nao anuncia arquivo nem tamanho que nao existem', () => {
  // A metade derivada do banco nao tem arquivo. "Arquivo: Nao informado" se le
  // como cadastro incompleto, e o periodo real ja vem no bloco de cobertura.
  render(
    <MemoryRouter>
      <DatasetCard item={itemBaixavel()} usuario={{ aprovado: true }} />
    </MemoryRouter>,
  );

  expect(screen.queryByText(/^Arquivo:/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Tamanho:/)).not.toBeInTheDocument();
  expect(screen.getByText(/14\.346 medicoes/)).toBeInTheDocument();
});
