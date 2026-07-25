export const ROTAS_APP = {
  home: '/',
  banco: '/banco-de-dados',
  recifes: '/localizacoes',
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

export function obterItensNavegacao(paginaAtual) {
  if (paginaAtual === 'banco') {
    return [
      { id: 'home', rotulo: 'Pagina inicial', to: ROTAS_APP.home },
      { id: 'recifes', rotulo: 'Explorar recifes', to: ROTAS_APP.recifes },
    ];
  }

  if (paginaAtual === 'recifes' || paginaAtual === 'detalhe') {
    return [
      { id: 'home', rotulo: 'Pagina inicial', to: ROTAS_APP.home },
      { id: 'banco', rotulo: 'Banco de dados', to: ROTAS_APP.banco },
    ];
  }

  return [
    { id: 'recifes', rotulo: 'Explorar recifes', to: ROTAS_APP.recifes },
    { id: 'banco', rotulo: 'Banco de dados', to: ROTAS_APP.banco },
  ];
}
