export function obterItensNavegacao(paginaAtual) {
  if (paginaAtual === 'banco') {
    return [
      { id: 'home', rotulo: 'Pagina inicial', destino: 'home' },
      { id: 'recifes', rotulo: 'Explorar recifes', destino: 'recifes' },
    ];
  }

  if (paginaAtual === 'recifes' || paginaAtual === 'detalhe') {
    return [
      { id: 'home', rotulo: 'Pagina inicial', destino: 'home' },
      { id: 'banco', rotulo: 'Banco de dados', destino: 'banco' },
    ];
  }

  return [
    { id: 'recifes', rotulo: 'Explorar recifes', destino: 'recifes' },
    { id: 'banco', rotulo: 'Banco de dados', destino: 'banco' },
  ];
}
