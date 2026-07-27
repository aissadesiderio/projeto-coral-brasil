/**
 * Testes das regras de exibicao da predicao.
 *
 * O que protegem, em ordem de gravidade:
 *
 * 1. 🚨 **A tela nunca escreve "0%" nem "100%".** Sao dois caminhos separados
 *    para o mesmo erro: o extremo exato que a isotonica produz por construcao,
 *    e o arredondamento de um valor pequeno para uma casa decimal.
 * 2. **O limiar vem do servidor, nao daqui.** Duplicar o numero criaria duas
 *    verdades que divergem em silencio.
 * 3. **Cada falha tem uma tela propria.** "Modelo nao treinado aqui" e
 *    "servidor sem modelo" pedem respostas diferentes de quem le.
 */

import {
  buscarPredicao,
  classificarAlerta,
  descreverAtraso,
  descreverEntrada,
  formatarDataBr,
  formatarPercentual,
  formatarProbabilidade,
} from './painelRisco';

function item(extras = {}) {
  return {
    disponivel: true,
    probabilidade: 0.073,
    limiar: 0.2,
    alerta: false,
    no_extremo: false,
    data_base: '2026-07-24',
    data_alvo: '2026-07-31',
    dias_de_atraso: 3,
    entradas: { sst_variacao_7d: 0.09 },
    ...extras,
  };
}

describe('formatarPercentual', () => {
  test('usa virgula decimal', () => {
    expect(formatarPercentual(0.073)).toBe('7,3%');
  });

  test('🚨 valor pequeno nao vira "0,0%"', () => {
    // 0,0004 -> 0,04% -> arredondado para uma casa daria "0,0%", que se le
    // como zero. O limite declarado e honesto; o zero seria mentira.
    expect(formatarPercentual(0.0004)).toBe('< 0,1%');
  });

  test('exatamente no limite ainda sai como numero', () => {
    expect(formatarPercentual(0.001)).toBe('0,1%');
  });

  test('zero exato continua zero aqui — quem barra e formatarProbabilidade', () => {
    // Esta funcao formata; a decisao de nao exibir extremo e da outra. Separar
    // evita que o limiar (0,20) tambem fosse reescrito como faixa.
    expect(formatarPercentual(0)).toBe('0,0%');
  });
});

describe('formatarProbabilidade', () => {
  test('valor comum sai como numero', () => {
    expect(formatarProbabilidade(item())).toEqual({
      tipo: 'numero',
      texto: '7,3%',
      explicacao: null,
    });
  });

  test('🚨 probabilidade zero exata vira faixa, nunca "0%"', () => {
    const saida = formatarProbabilidade(item({ probabilidade: 0, no_extremo: true }));

    expect(saida.tipo).toBe('faixa');
    expect(saida.texto).not.toMatch(/0%/);
    expect(saida.texto.toLowerCase()).toContain('mais baixa');
  });

  test('🚨 probabilidade um exata vira faixa, nunca "100%"', () => {
    const saida = formatarProbabilidade(item({ probabilidade: 1, no_extremo: true }));

    expect(saida.tipo).toBe('faixa');
    expect(saida.texto).not.toMatch(/100%/);
    expect(saida.texto.toLowerCase()).toContain('mais alta');
  });

  test('o extremo vem com explicacao, e ela nao afirma impossibilidade', () => {
    const saida = formatarProbabilidade(item({ probabilidade: 0, no_extremo: true }));

    expect(saida.explicacao).toContain('nao que seja impossivel');
  });

  test('o extremo alto nao afirma certeza', () => {
    const saida = formatarProbabilidade(item({ probabilidade: 1, no_extremo: true }));

    expect(saida.explicacao).toContain('nao que seja certo');
  });

  test('item indisponivel nao produz numero nenhum', () => {
    expect(formatarProbabilidade(item({ disponivel: false }))).toBeNull();
    expect(formatarProbabilidade(null)).toBeNull();
  });

  test('probabilidade ausente nao vira zero', () => {
    expect(formatarProbabilidade(item({ probabilidade: undefined }))).toBeNull();
  });
});

describe('classificarAlerta', () => {
  test('usa o campo alerta do servidor, e nao recalcula', () => {
    // 🚨 Se o frontend comparasse probabilidade >= limiar por conta propria,
    // uma mudanca de regra no servidor deixaria as duas versoes divergindo.
    const semAlerta = classificarAlerta(item({ probabilidade: 0.9, alerta: false }));

    expect(semAlerta.emAlerta).toBe(false);
  });

  test('o limiar vem do payload', () => {
    expect(classificarAlerta(item({ limiar: 0.35 })).limiarTexto).toBe('35,0%');
  });

  test('o rotulo diz estresse termico, e nao branqueamento', () => {
    const alerta = classificarAlerta(item({ alerta: true }));

    expect(alerta.rotulo.toLowerCase()).toContain('estresse termico');
    expect(alerta.rotulo.toLowerCase()).not.toContain('branqueamento');
  });

  test('item indisponivel nao classifica', () => {
    expect(classificarAlerta(item({ disponivel: false }))).toBeNull();
  });
});

describe('descreverAtraso', () => {
  test.each([
    [0, 'dado de hoje'],
    [1, 'dado de ontem'],
    [3, 'dado de 3 dias atras'],
  ])('%s dias', (dias, esperado) => {
    expect(descreverAtraso(dias)).toBe(esperado);
  });

  test('valor invalido nao inventa frase', () => {
    expect(descreverAtraso(undefined)).toBeNull();
    expect(descreverAtraso(-1)).toBeNull();
  });
});

describe('descreverEntrada', () => {
  test('traduz a coluna e diz que e variacao', () => {
    const entrada = descreverEntrada('sst_variacao_7d', 0.0931);

    expect(entrada.rotulo).toBe('Temperatura');
    expect(entrada.periodo).toBe('variacao em 7 dias');
    expect(entrada.valor).toBe('0,09');
  });

  test('marca a direcao da mudanca', () => {
    expect(descreverEntrada('sst_variacao_7d', -0.31).subiu).toBe(false);
    expect(descreverEntrada('sst_variacao_7d', 0.31).subiu).toBe(true);
  });

  test('coluna desconhecida nao quebra a tela', () => {
    expect(descreverEntrada('vento_variacao_7d', 1).rotulo).toBe('vento');
  });
});

describe('formatarDataBr', () => {
  test('converte ISO para dd/mm/aaaa', () => {
    expect(formatarDataBr('2026-07-24')).toBe('24/07/2026');
  });

  test('entrada invalida nao vira data falsa', () => {
    expect(formatarDataBr('ontem')).toBeNull();
    expect(formatarDataBr(null)).toBeNull();
  });
});

describe('buscarPredicao', () => {
  afterEach(() => {
    jest.resetAllMocks();
  });

  function responder(status, corpo = {}) {
    global.fetch = jest.fn(async () => ({
      ok: status >= 200 && status < 300,
      status,
      json: async () => corpo,
    }));
  }

  test('200 devolve os dados', async () => {
    responder(200, item());

    const saida = await buscarPredicao('abrolhos-ba');

    expect(saida.estado).toBe('ok');
    expect(saida.dados.probabilidade).toBe(0.073);
  });

  test('chama o endpoint do recife pedido', async () => {
    responder(200, item());

    await buscarPredicao('picaozinho-pb');

    expect(global.fetch).toHaveBeenCalledWith('/api/painel-risco/picaozinho-pb/');
  });

  test('503 e "sem modelo", nao erro generico', async () => {
    responder(503, { detail: 'gere com treinar_final' });

    expect((await buscarPredicao('abrolhos-ba')).estado).toBe('sem-modelo');
  });

  test('404 e "fora do treino", com o motivo', async () => {
    responder(404, { detail: 'O modelo nao foi treinado em "x".' });

    const saida = await buscarPredicao('x');

    expect(saida.estado).toBe('fora-do-treino');
    expect(saida.detalhe).toContain('nao foi treinado');
  });

  test('rede caindo nao derruba a pagina', async () => {
    global.fetch = jest.fn(async () => {
      throw new Error('sem rede');
    });

    expect((await buscarPredicao('abrolhos-ba')).estado).toBe('indisponivel');
  });

  test('sem fetch disponivel devolve indisponivel', async () => {
    const anterior = global.fetch;
    global.fetch = undefined;

    expect((await buscarPredicao('abrolhos-ba')).estado).toBe('indisponivel');

    global.fetch = anterior;
  });
});
