import { CAMPOS_MONITORAMENTO_OBRIGATORIOS, RISCO_STATUS } from '../config/monitoramentoConfig';
import { FALLBACK_DETALHES, FALLBACK_RECIFES } from '../data/recifeData';

function normalizarNumero(valor) {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : null;
}

function normalizarPredicao(predicao) {
  if (!predicao || typeof predicao !== 'object') {
    return null;
  }

  const riscoIntegrado = normalizarNumero(predicao.risco_integrado ?? predicao.risco_atual);

  return {
    ...predicao,
    data: predicao.data || predicao.ultima_predicao_data || null,
    risco_integrado: riscoIntegrado,
    nivel_alerta: predicao.nivel_alerta || predicao.nivel_alerta_atual || null,
  };
}

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

export function obterMetaRisco(nivelAlerta) {
  return RISCO_STATUS[nivelAlerta] || RISCO_STATUS.SEM_RISCO;
}

export function possuiPainelCompleto(monitoramento) {
  if (!monitoramento) {
    return false;
  }

  return CAMPOS_MONITORAMENTO_OBRIGATORIOS.every(
    (campo) => monitoramento[campo] !== null && monitoramento[campo] !== undefined,
  );
}

export function combinarLocais(apiLocais = []) {
  if (!Array.isArray(apiLocais)) {
    return [];
  }

  return apiLocais
    .filter((local) => local && typeof local === 'object' && local.slug)
    .map((local) => {
      const anterior = FALLBACK_RECIFES.find((item) => item.slug === local.slug) || {};
      const monitoramentoRecente =
        normalizarPredicao(local.monitoramento_recente) ||
        normalizarPredicao({
          data: local.ultima_predicao_data,
          risco_atual: local.risco_atual,
          nivel_alerta_atual: local.nivel_alerta_atual ?? local.nivel_alerta,
        });
      const quantidadeEspecies =
        local.quantidade_especies ??
        local.informacoes_disponiveis ??
        anterior.informacoes_disponiveis ??
        FALLBACK_DETALHES[local.slug]?.especies?.length ??
        0;
      const quantidadePredicoes = local.quantidade_predicoes ?? anterior.quantidade_predicoes ?? 0;
      const riscoAtual = normalizarNumero(local.risco_atual);
      const nivelAlertaAtual =
        local.nivel_alerta_atual ||
        local.nivel_alerta ||
        monitoramentoRecente?.nivel_alerta ||
        anterior.nivel_alerta_atual ||
        null;

      return {
        ...anterior,
        ...local,
        imagem_url: local.imagem_url || anterior.imagem_url || '',
        ultima_atualizacao:
          local.ultima_atualizacao || local.ultima_predicao_data || anterior.ultima_atualizacao || '',
        quantidade_especies: quantidadeEspecies,
        quantidade_predicoes: quantidadePredicoes,
        risco_atual: riscoAtual,
        ultima_predicao_data: local.ultima_predicao_data || monitoramentoRecente?.data || null,
        nivel_alerta_atual: nivelAlertaAtual,
        nivel_alerta: local.nivel_alerta || monitoramentoRecente?.nivel_alerta || null,
        informacoes_disponiveis: quantidadeEspecies,
        possui_painel_risco:
          local.possui_painel_risco ??
          anterior.possui_painel_risco ??
          Boolean(quantidadePredicoes || monitoramentoRecente),
        monitoramento_recente: monitoramentoRecente,
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
  const predicoesApi =
    Array.isArray(detalheApi?.predicoes) && detalheApi.predicoes.length > 0
      ? detalheApi.predicoes.map(normalizarPredicao).filter(Boolean)
      : null;
  const monitoramentoFallback = normalizarPredicao(detalheFallback.monitoramento_recente);
  const monitoramentoBase = normalizarPredicao(recifeBase.monitoramento_recente);
  const monitoramentoApi =
    normalizarPredicao(detalheApi?.monitoramento_recente) || predicoesApi?.[0] || null;
  const monitoramentoRecente =
    monitoramentoApi || monitoramentoFallback || monitoramentoBase || null;
  const quantidadeEspecies =
    detalheApi?.quantidade_especies ??
    detalheApi?.informacoes_disponiveis ??
    (especiesApiNormalizadas ? especiesApiNormalizadas.length : null) ??
    recifeBase.quantidade_especies ??
    recifeBase.informacoes_disponiveis ??
    detalheFallback.especies?.length ??
    0;
  const quantidadePredicoes =
    detalheApi?.quantidade_predicoes ??
    (predicoesApi ? predicoesApi.length : null) ??
    recifeBase.quantidade_predicoes ??
    0;
  const riscoAtual =
    normalizarNumero(detalheApi?.risco_atual) ??
    monitoramentoApi?.risco_integrado ??
    normalizarNumero(recifeBase.risco_atual) ??
    monitoramentoFallback?.risco_integrado ??
    monitoramentoBase?.risco_integrado ??
    null;
  const nivelAlertaAtual =
    detalheApi?.nivel_alerta_atual ||
    detalheApi?.nivel_alerta ||
    monitoramentoApi?.nivel_alerta ||
    recifeBase.nivel_alerta_atual ||
    recifeBase.nivel_alerta ||
    monitoramentoFallback?.nivel_alerta ||
    monitoramentoBase?.nivel_alerta ||
    null;

  return {
    ...recifeBase,
    ...detalheFallback,
    ...detalheApi,
    imagem_url: detalheApi?.imagem_url || recifeBase.imagem_url || '',
    especies: especiesApiNormalizadas || detalheFallback.especies || [],
    predicoes: predicoesApi || detalheApi?.predicoes || [],
    monitoramento_recente:
      monitoramentoRecente && {
        ...monitoramentoRecente,
        data:
          monitoramentoRecente.data ||
          detalheApi?.ultima_predicao_data ||
          recifeBase.ultima_predicao_data ||
          null,
        risco_integrado: monitoramentoRecente.risco_integrado ?? riscoAtual,
        nivel_alerta: monitoramentoRecente.nivel_alerta || nivelAlertaAtual,
      },
    informacoes_disponiveis: quantidadeEspecies,
    quantidade_especies: quantidadeEspecies,
    quantidade_predicoes: quantidadePredicoes,
    risco_atual: riscoAtual,
    ultima_predicao_data:
      detalheApi?.ultima_predicao_data || monitoramentoRecente?.data || recifeBase.ultima_predicao_data || null,
    ultima_atualizacao:
      detalheApi?.ultima_atualizacao || recifeBase.ultima_atualizacao || monitoramentoRecente?.data || null,
    possui_painel_risco:
      detalheApi?.possui_painel_risco ??
      recifeBase.possui_painel_risco ??
      Boolean(monitoramentoRecente || quantidadePredicoes),
    nivel_alerta_atual: nivelAlertaAtual,
    nivel_alerta:
      detalheApi?.nivel_alerta ||
      monitoramentoRecente?.nivel_alerta ||
      recifeBase.nivel_alerta ||
      monitoramentoFallback?.nivel_alerta ||
      monitoramentoBase?.nivel_alerta ||
      null,
  };
}

export function obterQuantidadeEspeciesLocal(local) {
  const especiesFallback = FALLBACK_DETALHES[local.slug]?.especies?.length;
  return local.quantidade_especies ?? local.informacoes_disponiveis ?? especiesFallback ?? 0;
}

export function obterMonitoramentoLocal(local) {
  return (
    normalizarPredicao(local.monitoramento_recente) ||
    normalizarPredicao(FALLBACK_DETALHES[local.slug]?.monitoramento_recente) ||
    null
  );
}

export function obterNivelAlertaLocal(local) {
  return (
    local.nivel_alerta_atual ||
    local.monitoramento_recente?.nivel_alerta ||
    local.nivel_alerta ||
    obterMonitoramentoLocal(local)?.nivel_alerta ||
    'SEM_RISCO'
  );
}

export function obterValorRiscoAtualLocal(local) {
  return (
    normalizarNumero(local.risco_atual) ??
    normalizarNumero(local.monitoramento_recente?.risco_integrado) ??
    normalizarNumero(obterMonitoramentoLocal(local)?.risco_integrado) ??
    null
  );
}

export function obterRiscoAtualLocal(local) {
  return obterValorRiscoAtualLocal(local);
}
