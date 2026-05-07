import { CAMPOS_MONITORAMENTO_OBRIGATORIOS, RISCO_STATUS } from '../config/monitoramentoConfig';
import { FALLBACK_DETALHES, FALLBACK_RECIFES } from '../data/recifeData';

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
  const mapa = new Map(FALLBACK_RECIFES.map((local) => [local.slug, { ...local }]));

  apiLocais.forEach((local) => {
    const anterior = mapa.get(local.slug) || {};
    mapa.set(local.slug, {
      ...anterior,
      ...local,
      imagem_url: local.imagem_url || anterior.imagem_url || '',
      informacoes_disponiveis:
        local.quantidade_especies ??
        local.informacoes_disponiveis ??
        anterior.informacoes_disponiveis ??
        0,
    });
  });

  return Array.from(mapa.values());
}

export function combinarDetalhe(recifeBase, detalheApi) {
  if (!recifeBase) {
    return null;
  }

  const detalheFallback = FALLBACK_DETALHES[recifeBase.slug] || {};
  const especiesApi =
    Array.isArray(detalheApi?.especies) && detalheApi.especies.length > 0
      ? detalheApi.especies
      : null;

  return {
    ...recifeBase,
    ...detalheFallback,
    ...detalheApi,
    imagem_url: detalheApi?.imagem_url || recifeBase.imagem_url || '',
    especies: especiesApi || detalheFallback.especies || [],
    monitoramento_recente:
      detalheApi?.monitoramento_recente || detalheFallback.monitoramento_recente || null,
    informacoes_disponiveis:
      detalheApi?.informacoes_disponiveis ??
      detalheApi?.quantidade_especies ??
      recifeBase.informacoes_disponiveis ??
      (especiesApi || detalheFallback.especies || []).length,
  };
}

export function obterQuantidadeEspeciesLocal(local) {
  const especiesFallback = FALLBACK_DETALHES[local.slug]?.especies?.length;
  return local.quantidade_especies ?? local.informacoes_disponiveis ?? especiesFallback ?? 0;
}

export function obterMonitoramentoLocal(local) {
  return local.monitoramento_recente || FALLBACK_DETALHES[local.slug]?.monitoramento_recente || null;
}

export function obterRiscoAtualLocal(local) {
  return local.nivel_alerta || local.risco_atual || obterMonitoramentoLocal(local)?.nivel_alerta || null;
}
