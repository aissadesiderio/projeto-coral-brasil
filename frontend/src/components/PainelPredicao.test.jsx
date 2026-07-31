/**
 * Testes do painel de predicao.
 *
 * O foco e o que a tela **escreve**, porque o risco aqui e de comunicacao:
 * um numero certo apresentado de forma errada engana igual.
 */

import { render, screen, waitFor } from '@testing-library/react';

import PainelPredicao from './PainelPredicao';

// A escala como o servidor a manda — ver `ml/niveis.py`.
const ESCALA = [
  {
    slug: 'alerta_alto', rotulo: 'Alerta alto', corte: 0.5, exige_acao: true,
    acao: 'Acionar monitoramento com prioridade. Oito em cada dez avisos neste nivel se confirmam.',
  },
  {
    slug: 'alerta', rotulo: 'Alerta', corte: 0.2, exige_acao: true,
    acao: 'Acionar monitoramento. Sete em cada dez avisos neste nivel se confirmam.',
  },
  {
    slug: 'observacao', rotulo: 'Observacao', corte: 0.05, exige_acao: false,
    acao: 'Acompanhar, sem mobilizar. Metade dos avisos neste nivel nao se confirma.',
  },
  {
    slug: 'sem_aviso', rotulo: 'Sem aviso', corte: 0.0, exige_acao: false,
    acao: 'Nada a fazer.',
  },
];

function nivel(slug) {
  return ESCALA.find((n) => n.slug === slug);
}

function payload(extras = {}) {
  return {
    modelo: {
      nome: 'entrega1_baa',
      alvo: 'baa >= 3.0 em t+7',
      horizonte_dias: 7,
      calibracao: 'isotonic',
      probabilidade_em_degraus: true,
      limiar: 0.2,
      escala: ESCALA,
    },
    local: 'abrolhos-ba',
    nome: 'Abrolhos',
    disponivel: true,
    data_base: '2026-07-24',
    data_alvo: '2026-07-31',
    dias_de_atraso: 3,
    probabilidade: 0.073,
    limiar: 0.2,
    alerta: false,
    nivel: nivel('observacao'),
    no_extremo: false,
    entradas: {
      sst_variacao_7d: 0.0931,
      dhw_variacao_7d: 0.0,
      salinidade_variacao_7d: -0.0717,
      oxigenio_variacao_7d: 0.8181,
    },
    ...extras,
  };
}

function responder(corpo, status = 200) {
  global.fetch = jest.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => corpo,
  }));
}

afterEach(() => {
  jest.resetAllMocks();
});

test('exibe a probabilidade formatada', async () => {
  responder(payload());

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(await screen.findByText('7,3%')).toBeInTheDocument();
});

test('🚨 nunca escreve "0%" quando a probabilidade e zero exata', async () => {
  responder(payload({ probabilidade: 0, no_extremo: true }));

  render(<PainelPredicao slug="abrolhos-ba" />);

  await screen.findByText(/faixa mais baixa/i);
  expect(screen.queryByText('0%')).not.toBeInTheDocument();
  expect(screen.queryByText('0,0%')).not.toBeInTheDocument();
});

test('🚨 nunca escreve "100%" quando a probabilidade e um exato', async () => {
  responder(payload({ probabilidade: 1, no_extremo: true, alerta: true }));

  render(<PainelPredicao slug="abrolhos-ba" />);

  await screen.findByText(/faixa mais alta/i);
  expect(screen.queryByText('100%')).not.toBeInTheDocument();
  expect(screen.queryByText('100,0%')).not.toBeInTheDocument();
});

test('o extremo vem acompanhado da explicacao', async () => {
  responder(payload({ probabilidade: 0, no_extremo: true }));

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(
    await screen.findByText(/nao que seja impossivel/i),
  ).toBeInTheDocument();
});

test('mostra a data-base e o atraso da serie', async () => {
  responder(payload());

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(await screen.findByText(/24\/07\/2026/)).toBeInTheDocument();
  expect(screen.getByText('dado de 3 dias atras')).toBeInTheDocument();
});

test('diz sobre que dia a previsao fala', async () => {
  responder(payload());

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(await screen.findByText(/31\/07\/2026/)).toBeInTheDocument();
});

test('🚨 o texto fala em estresse termico, nao em branqueamento previsto', async () => {
  responder(payload());

  render(<PainelPredicao slug="abrolhos-ba" />);

  await screen.findByText('7,3%');
  expect(screen.getByText(/estresse termico em 7 dias/i)).toBeInTheDocument();
});

test('declara onde comeca o degrau em que o recife esta', async () => {
  responder(payload());

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(await screen.findByText(/degrau comeca em 5,0%/i)).toBeInTheDocument();
});

test('⚠️ resposta sem `nivel` cai no limiar unico, e nao fica muda', async () => {
  // Contrato de uma versao anterior da API. Sem a reserva, a frase inteira
  // sumiria contra um servidor antigo.
  responder(payload({ nivel: undefined }));

  render(<PainelPredicao slug="abrolhos-ba" />);

  // A frase da reserva, e nao o "a partir de" que a lista da escala repete.
  expect(
    await screen.findByText(/Aviso emitido a partir de/i),
  ).toHaveTextContent('20,0%');
});

// --- a escala na tela ------------------------------------------------------

test('🚨 mostra a ACAO esperada, e nao so o rotulo do degrau', async () => {
  responder(payload());

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(await screen.findByText('O que fazer')).toBeInTheDocument();
  expect(
    screen.getAllByText(/Acompanhar, sem mobilizar/i).length,
  ).toBeGreaterThan(0);
});

test('a acao de "Sem aviso" tambem aparece — quem abriu quer saber', async () => {
  responder(payload({ nivel: nivel('sem_aviso'), probabilidade: 0.003 }));

  render(<PainelPredicao slug="abrolhos-ba" />);

  // "Sem aviso" aparece no selo e na lista da escala — os dois sao esperados.
  expect((await screen.findAllByText('Sem aviso')).length).toBeGreaterThan(1);
  expect(screen.getAllByText('Nada a fazer.').length).toBeGreaterThan(0);
});

test('a escala inteira aparece, com o degrau de hoje marcado', async () => {
  responder(payload());

  render(<PainelPredicao slug="abrolhos-ba" />);

  await screen.findByText('A escala de aviso');
  for (const rotulo of ['Alerta alto', 'Alerta', 'Observacao', 'Sem aviso']) {
    expect(screen.getAllByText(rotulo).length).toBeGreaterThan(0);
  }
  expect(screen.getByText('hoje')).toBeInTheDocument();
});

test('⚠️ sem escala do servidor, o bloco some em vez de ser reconstruido', async () => {
  // Repetir os cortes aqui criaria uma segunda escala, livre para divergir da
  // primeira em silencio.
  responder(payload({ modelo: { limiar: 0.2, calibracao: 'isotonic' } }));

  render(<PainelPredicao slug="abrolhos-ba" />);

  await screen.findByText('7,3%');
  expect(screen.queryByText('A escala de aviso')).not.toBeInTheDocument();
});

test('mostra as entradas que o modelo usou', async () => {
  responder(payload());

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(await screen.findByText('Temperatura')).toBeInTheDocument();
  expect(screen.getAllByText('variacao em 7 dias')).toHaveLength(4);
});

test('🚨 dado insuficiente nao vira probabilidade', async () => {
  responder(
    payload({
      disponivel: false,
      motivo: 'A janela do modelo nao fecha em 2026-07-24: falta sst em 2026-07-17',
      probabilidade: undefined,
    }),
  );

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(await screen.findByText(/dados insuficientes/i)).toBeInTheDocument();
  expect(screen.getByText(/nenhum valor foi estimado/i)).toBeInTheDocument();
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});

test('a recusa diz qual dia faltou', async () => {
  responder(
    payload({
      disponivel: false,
      motivo: 'falta sst em 2026-07-17',
    }),
  );

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(await screen.findByText(/2026-07-17/)).toBeInTheDocument();
});

test('servidor sem modelo tem tela propria', async () => {
  responder({ detail: 'rode treinar_final' }, 503);

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(
    await screen.findByText(/modelo ainda nao esta disponivel/i),
  ).toBeInTheDocument();
});

test('local fora do treino explica por que nao responde', async () => {
  responder({ detail: 'nao foi treinado' }, 404);

  render(<PainelPredicao slug="fernando-de-noronha" />);

  expect(
    await screen.findByText(/nao foi treinado nesta localizacao/i),
  ).toBeInTheDocument();
});

test('rede caindo nao exibe numero nenhum', async () => {
  global.fetch = jest.fn(async () => {
    throw new Error('sem rede');
  });

  render(<PainelPredicao slug="abrolhos-ba" />);

  expect(await screen.findByText(/nao foi possivel calcular/i)).toBeInTheDocument();
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});

test('em modo offline nao chama a API', async () => {
  responder(payload());

  render(<PainelPredicao slug="abrolhos-ba" publicOffline />);

  await waitFor(() => expect(global.fetch).not.toHaveBeenCalled());
});
