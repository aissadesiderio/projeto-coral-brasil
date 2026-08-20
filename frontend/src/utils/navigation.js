export const ROTAS_APP = {
  home: '/',
  banco: '/banco-de-dados',
  recifes: '/localizacoes',
  login: '/login',
  cadastro: '/cadastro',
  minhasEspecies: '/minhas-especies',
};

function normalizarPathname(pathname = '/') {
  if (!pathname || pathname === '/') {
    return '/';
  }

  return pathname.replace(/\/+$/, '');
}

export function obterRotaPorPagina(pagina) {
  return ROTAS_APP[pagina] || ROTAS_APP.home;
}

export function obterRotaLocalizacao(slug) {
  return `${ROTAS_APP.recifes}/${slug}`;
}

export function obterPaginaAtual(pathname) {
  const rotaAtual = normalizarPathname(pathname);

  if (rotaAtual === ROTAS_APP.banco) {
    return 'banco';
  }

  if (rotaAtual === ROTAS_APP.recifes) {
    return 'recifes';
  }

  if (rotaAtual.startsWith(`${ROTAS_APP.recifes}/`)) {
    return 'detalhe';
  }

  return 'home';
}

/**
 * A navegação é **fixa**, e a página atual vem marcada.
 *
 * 🚨 Até 13/08/2026 este arquivo devolvia um conjunto diferente de links por
 * página — a atual sumia da barra. O efeito era que a barra mudava de tamanho a
 * cada rota e nunca dizia onde o visitante estava: numa listagem de três itens,
 * "a que falta é onde você está" é uma pista que ninguém lê.
 *
 * Com o desenho 3a a barra tem os mesmos três destinos sempre, e o atual leva o
 * filete terra embaixo. `ativo` sai daqui e não do componente para que a regra
 * de "detalhe do recife também acende Localizações" viva num lugar só.
 */
export function obterItensNavegacao(paginaAtual) {
  return [
    { id: 'home', rotulo: 'Costa', to: ROTAS_APP.home, ativo: paginaAtual === 'home' },
    {
      id: 'recifes',
      rotulo: 'Localizacoes',
      to: ROTAS_APP.recifes,
      ativo: paginaAtual === 'recifes' || paginaAtual === 'detalhe',
    },
    { id: 'banco', rotulo: 'Dados', to: ROTAS_APP.banco, ativo: paginaAtual === 'banco' },
  ];
}
