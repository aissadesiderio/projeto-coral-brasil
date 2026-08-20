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

/**
 * Um número, ou nada — nunca zero por acidente.
 *
 * 🚨 **`Number(null)` é `0`, e `Number('')` também.** Foi assim que a régua da
 * costa nasceu errada: `Number.isFinite(Number(local.latitude))` devolve `true`
 * para uma latitude nula, e a APA Costa dos Corais e o Recife de Fora — os dois
 * locais cadastrados **sem** coordenada, de propósito, para não inventar a
 * posição de onde o satélite mediu — apareciam plotados no **equador**, no topo
 * da régua e no topo da lista ordenada de norte a sul.
 *
 * É a mesma falha de categoria que o projeto persegue no resto do código:
 * ausência de dado virando o menor dos valores. Aqui ela é silenciosa porque
 * `isFinite` diz que sim.
 */
export function numeroOuNulo(valor) {
  if (valor === null || valor === undefined || valor === '') {
    return null;
  }
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : null;
}

/**
 * Latitude em grau e minuto, para a coluna e a régua da costa.
 *
 * ⚠️ Grau e minuto, e **não** a decimal com quatro casas da ficha. Os dois
 * números respondem perguntas diferentes: aqui a latitude serve para ordenar a
 * costa de norte a sul e situar o leitor, e "17°58′ S" faz isso melhor que
 * "-17.9720". A decimal continua na ficha do local, onde existe para ser colada
 * num mapa — ver `FichaDoLocal.formatarCoordenadas`.
 */
export function formatarLatitudeCurta(latitude) {
  const valor = numeroOuNulo(latitude);
  if (valor === null) {
    return null;
  }

  const absoluto = Math.abs(valor);
  let graus = Math.floor(absoluto);
  let minutos = Math.round((absoluto - graus) * 60);

  // 59,7' arredonda para 60' e sairia como "17°60′".
  if (minutos === 60) {
    graus += 1;
    minutos = 0;
  }

  return `${graus}°${String(minutos).padStart(2, '0')}′ ${valor < 0 ? 'S' : 'N'}`;
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
