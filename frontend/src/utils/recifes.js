/**
 * Junta o que a API devolve com o fallback gerado do banco.
 *
 * 🚨 **Nao ha calculo de risco aqui, e isso e deliberado.** Ate 30/07/2026
 * este arquivo montava `risco_atual`, `nivel_alerta_atual`,
 * `monitoramento_recente` e `quantidade_predicoes` — quatro campos com nome de
 * resultado, encadeados em cascatas de `??` de seis niveis, e **nenhum deles
 * era renderizado por componente nenhum**. Vinham do `StatusPredicao`, o
 * caminho legado do backend, removido no mesmo dia.
 *
 * Codigo morto que calcula risco e pior que codigo morto qualquer: ele parece
 * a fonte da verdade sobre o alerta. Quem viesse consertar o painel mexeria
 * aqui, e nada mudaria na tela.
 *
 * O risco vem de `/api/painel-risco/` e passa por `utils/painelRisco.js`. Este
 * arquivo cuida so de identidade e conteudo do recife.
 */

import { FALLBACK_DETALHES, FALLBACK_RECIFES } from '../data/recifeData';
import { numeroOuNulo } from './formatters';

function normalizarEspecie(especie, index) {
  if (!especie || typeof especie !== 'object') {
    return null;
  }

  return {
    ...especie,
    id: especie.id ?? especie.nome_cientifico ?? especie.nome_comum ?? `especie-${index}`,
    foto_url: especie.foto_url || '',
  };
}

export function combinarLocais(apiLocais = []) {
  if (!Array.isArray(apiLocais)) {
    return [];
  }

  return apiLocais
    .filter((local) => local && typeof local === 'object' && local.slug)
    .map((local) => {
      const anterior = FALLBACK_RECIFES.find((item) => item.slug === local.slug) || {};
      const quantidadeEspecies =
        local.quantidade_especies ??
        local.informacoes_disponiveis ??
        anterior.informacoes_disponiveis ??
        FALLBACK_DETALHES[local.slug]?.especies?.length ??
        0;

      return {
        ...anterior,
        ...local,
        imagem_url: local.imagem_url || anterior.imagem_url || '',
        ultima_atualizacao: local.ultima_atualizacao || anterior.ultima_atualizacao || '',
        quantidade_especies: quantidadeEspecies,
        informacoes_disponiveis: quantidadeEspecies,
        // ⚠️ Passa direto, sem reserva local. Desde 30/07/2026 o servidor o
        // deriva dos metadados do modelo — a mesma fonte que decide o 404 do
        // painel. Uma queda para o fallback poderia afirmar que ha painel
        // sobre um recife que o modelo nunca viu.
        possui_painel_risco: local.possui_painel_risco === true,
      };
    });
}

export function combinarDetalhe(recifeBase, detalheApi) {
  if (!recifeBase) {
    return null;
  }

  const detalheFallback = FALLBACK_DETALHES[recifeBase.slug] || {};
  const especiesApiNormalizadas =
    Array.isArray(detalheApi?.especies) && detalheApi.especies.length > 0
      ? detalheApi.especies.map(normalizarEspecie).filter(Boolean)
      : null;
  const especies = especiesApiNormalizadas || detalheFallback.especies || [];
  const quantidadeEspecies =
    detalheApi?.quantidade_especies ??
    detalheApi?.informacoes_disponiveis ??
    (especiesApiNormalizadas ? especiesApiNormalizadas.length : null) ??
    recifeBase.quantidade_especies ??
    recifeBase.informacoes_disponiveis ??
    detalheFallback.especies?.length ??
    0;

  return {
    ...recifeBase,
    ...detalheFallback,
    ...detalheApi,
    imagem_url: detalheApi?.imagem_url || recifeBase.imagem_url || '',
    especies,
    quantidade_especies: quantidadeEspecies,
    informacoes_disponiveis: quantidadeEspecies,
    ultima_atualizacao: detalheApi?.ultima_atualizacao || recifeBase.ultima_atualizacao || null,
    possui_painel_risco:
      detalheApi?.possui_painel_risco === true || recifeBase.possui_painel_risco === true,
  };
}

/**
 * A ordem do catálogo, usada pela home e pela listagem.
 *
 * 🚨 **Latitude é o padrão, e mora aqui e não em cada página.** A régua da
 * costa (`RailLatitude`) desenha os pontos de norte a sul; se a tabela ao lado
 * seguisse outra ordem, o leitor teria duas listas dos mesmos recifes em
 * sequências diferentes na mesma tela, e a régua deixaria de servir de índice.
 *
 * ⚠️ Ordenar por risco no topo faria a lista mudar de ordem a cada rodada do
 * modelo — quem abre a página duas vezes no mesmo dia encontraria uma costa
 * diferente. É uma ordem que o visitante pede, não uma que a página impõe.
 */
export function ordenarLocais(locais, ordem = 'latitude', predicoes = {}) {
  const copia = [...locais];

  if (ordem === 'risco') {
    return copia.sort((a, b) => {
      // Sem previsão vai para o fim, e não para o começo com risco zero: a
      // ausência de número não pode se ordenar como o menor dos números.
      const pa =
        predicoes[a.slug]?.disponivel === true ? Number(predicoes[a.slug].probabilidade) : -1;
      const pb =
        predicoes[b.slug]?.disponivel === true ? Number(predicoes[b.slug].probabilidade) : -1;
      return pb - pa;
    });
  }

  if (ordem === 'especies') {
    return copia.sort(
      (a, b) =>
        (b.quantidade_especies || b.informacoes_disponiveis || 0)
        - (a.quantidade_especies || a.informacoes_disponiveis || 0),
    );
  }

  // Norte para sul. Quem não tem latitude fica no fim, junto do motivo.
  //
  // ⚠️ Duas armadilhas neste `sort`, e as duas já morderam:
  //
  // 1. **`Number(null)` é `0`.** Sem `numeroOuNulo`, os dois locais sem
  //    coordenada se ordenavam como se estivessem no equador — ou seja, no
  //    topo de uma lista de recifes brasileiros. Ver `formatters.numeroOuNulo`.
  // 2. **O sentinela precisa ser finito.** Com `-Infinity`, comparar dois
  //    locais sem coordenada dá `NaN`, e um comparador que devolve `NaN` deixa
  //    a ordem indefinida: os dois trocariam de lugar entre renderizações sem
  //    nada tê-los mudado.
  const SEM_LATITUDE = -1000;

  return copia.sort((a, b) => {
    const la = numeroOuNulo(a.latitude) ?? SEM_LATITUDE;
    const lb = numeroOuNulo(b.latitude) ?? SEM_LATITUDE;
    return lb - la;
  });
}

export function obterQuantidadeEspeciesLocal(local) {
  const especiesFallback = FALLBACK_DETALHES[local.slug]?.especies?.length;
  return local.quantidade_especies ?? local.informacoes_disponiveis ?? especiesFallback ?? 0;
}
