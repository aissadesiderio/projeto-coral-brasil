export function formatarData(data) {
  if (!data) {
    return 'Nao informado';
  }

  const [ano, mes, dia] = data.split('-');
  return `${dia}/${mes}/${ano}`;
}

export function formatarPeriodo(item) {
  if (item.recorteTemporal === 'publicacao') {
    return `Publicado em ${formatarData(item.dataPublicacao)}`;
  }

  return `${formatarData(item.dataInicio)} ate ${formatarData(item.dataFim)}`;
}

export function formatarLocal(item) {
  return `${item.estado} - ${item.cidade}`;
}

export function formatarQuantidadeEspecies(total) {
  return `${total} ${total === 1 ? 'especie cadastrada' : 'especies cadastradas'}`;
}

export function scrollToTopo() {
  if (typeof window !== 'undefined' && typeof window.scrollTo === 'function') {
    try {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      try {
        window.scrollTo(0, 0);
      } catch (fallbackError) {
        // Ignora ambientes que nao implementam scroll programatico.
      }
    }
  }
}

export function resolverLinkImagem(especie) {
  return especie?.fonte_imagem_url || especie?.foto_url || '';
}

export function resolverRotuloLinkImagem(especie) {
  return especie?.fonte_imagem_url ? 'Ver fonte da imagem' : 'Abrir imagem';
}

export function resolverCreditoImagem(especie) {
  return especie?.credito_imagem || (especie?.foto_url ? 'Acervo local do projeto' : '');
}
