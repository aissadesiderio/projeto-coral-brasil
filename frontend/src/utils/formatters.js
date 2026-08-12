export function formatarData(data) {
  if (!data) {
    return 'Nao informado';
  }

  const [ano, mes, dia] = data.split('-');
  return `${dia}/${mes}/${ano}`;
}

export function formatarPeriodo(item) {
  if (item.recorteTemporal === 'publicacao' && item.dataPublicacao) {
    return `Publicado em ${formatarData(item.dataPublicacao)}`;
  }

  if (item.dataInicio || item.dataFim) {
    return `${formatarData(item.dataInicio)} ate ${formatarData(item.dataFim)}`;
  }

  return item.periodoRotulo || 'Periodo nao informado';
}

export function formatarLocal(item) {
  const partes = [item.estado, item.cidade].filter(Boolean);
  return partes.length > 0 ? partes.join(' - ') : 'Nao informado';
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

// 🚨 Ate 11/08/2026 esta funcao inventava o credito: sem `credito_imagem`,
// mas com foto, ela afirmava "Acervo local do projeto" — a mesma mentira que
// o exportador `backend/aquaculture/code_sync.py` gravava no fallback e que a
// migracao 0026 tirou do banco das nove especies. Ter arquivo nao e ter
// procedencia: quem nao tem credito nao ganha um, e a modal ja sabe dizer
// "Sem credito informado" sozinha. Ver docs/FONTES.md secao 2.1.
export function resolverCreditoImagem(especie) {
  return especie?.credito_imagem || '';
}
