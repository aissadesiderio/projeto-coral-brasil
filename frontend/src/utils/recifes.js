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

export function obterQuantidadeEspeciesLocal(local) {
  const especiesFallback = FALLBACK_DETALHES[local.slug]?.especies?.length;
  return local.quantidade_especies ?? local.informacoes_disponiveis ?? especiesFallback ?? 0;
}
