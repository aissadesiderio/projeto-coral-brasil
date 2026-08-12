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

function nivel(extras = {}) {
  return {
    slug: 'alerta',
    rotulo: 'Alerta',
    corte: 0.2,
    acao: 'Acionar monitoramento. Sete em cada dez avisos neste nivel se confirmam.',
    exige_acao: true,
    ...extras,
  };
}

test('o selo mostra o degrau, com o nome que o servidor deu', () => {
  montar({ predicao: predicao({ alerta: true, nivel: nivel() }) });

  expect(screen.getByText('Alerta')).toBeInTheDocument();
});

test('🚨 o selo nao reconstroi o rotulo — ele vem do servidor', () => {
  // Um degrau que este cartao nao conhece precisa aparecer como o servidor o
  // nomeou, e nao virar "Alerta" ou "Sem alerta" por reconstrucao local.
  montar({
    predicao: predicao({
      alerta: true,
      nivel: nivel({ slug: 'alerta_maximo', rotulo: 'Alerta maximo' }),
    }),
  });

  expect(screen.getByText('Alerta maximo')).toBeInTheDocument();
});

test('degrau que exige acao vem preenchido; os outros, contornados', () => {
  const { unmount } = montar({
    predicao: predicao({ alerta: true, nivel: nivel() }),
  });
  const exigente = screen.getByText('Alerta').className;
  unmount();

  montar({
    predicao: predicao({
      nivel: nivel({ slug: 'observacao', rotulo: 'Observacao', exige_acao: false }),
    }),
  });
  const tranquilo = screen.getByText('Observacao').className;

  expect(exigente).toContain('text-white');
  expect(tranquilo).not.toContain('text-white');
});

test('a acao esperada fica no title, para quem passar o mouse', () => {
  montar({ predicao: predicao({ alerta: true, nivel: nivel() }) });

  expect(screen.getByText('Alerta')).toHaveAttribute(
    'title',
    expect.stringContaining('Acionar monitoramento'),
  );
});

test('⚠️ resposta sem `nivel` continua legivel, pelo caminho de reserva', () => {
  // Uma versao anterior da API nao manda `nivel`. O cartao nao pode ficar sem
  // selo por causa disso.
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

/**
 * O recife que nunca vai ter serie, e diz por que.
 *
 * 🚨 Ate 12/08/2026 a APA Costa dos Corais e o Recife de Fora — cadastrados sem
 * coordenada de proposito, para nao inventar a posicao de onde o satelite mediu
 * — apareciam com "Nao calculado" e "Sem previsao", exatamente como apareceria
 * um recife cuja ingestao quebrou. Decisao registrada e defeito ficavam com a
 * mesma cara.
 */
const SEM_COORDENADAS = {
  slug: 'apa-costa-dos-corais',
  nome: 'APA Costa dos Corais',
  estado: 'Alagoas/Pernambuco',
  cidade: 'Diversos municipios (AL/PE)',
  quantidade_especies: 0,
  tem_coordenadas: false,
  motivo_sem_serie: {
    codigo: 'sem_coordenadas',
    resumo: 'Cadastrado sem latitude/longitude.',
    detalhe: 'E uma area, nao um ponto.',
  },
};

test('🚨 recife sem coordenada explica a ausencia em vez de dizer "Nao calculado"', () => {
  render(
    <MemoryRouter>
      <CardRecife local={SEM_COORDENADAS} predicao={null} />
    </MemoryRouter>,
  );

  expect(screen.getByText(/cadastrado sem coordenadas/i)).toBeInTheDocument();
  expect(screen.queryByText(/Nao calculado/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Sem previsao/i)).not.toBeInTheDocument();
});

test('⚠️ recife com coordenada e sem previsao hoje continua dizendo "Nao calculado"', () => {
  // A distincao que o aviso existe para preservar: aqui a serie **vai**
  // existir, e trocar isto pelo mesmo aviso apagaria a diferenca entre "a
  // janela nao fechou hoje" e "nunca vai fechar".
  render(
    <MemoryRouter>
      <CardRecife local={{ ...LOCAL, tem_coordenadas: true, motivo_sem_serie: null }} predicao={null} />
    </MemoryRouter>,
  );

  expect(screen.getByText(/Nao calculado/i)).toBeInTheDocument();
  expect(screen.queryByText(/cadastrado sem coordenadas/i)).not.toBeInTheDocument();
});
