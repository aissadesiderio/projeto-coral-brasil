function normalizarNumero(valor) {
  if (typeof valor === 'number' && Number.isFinite(valor)) {
    return valor;
  }

  const numero = Number.parseFloat(valor);
  return Number.isFinite(numero) ? numero : null;
}

function formatarNumero(valor) {
  if (Number.isInteger(valor)) {
    return String(valor);
  }

  return valor.toFixed(1).replace(/\.0$/, '');
}

function inferirRecorteTemporal(item) {
  if (item.recorte_temporal || item.recorteTemporal) {
    return item.recorte_temporal || item.recorteTemporal;
  }

  if (item.data_publicacao || item.dataPublicacao) {
    return 'publicacao';
  }

  return 'intervalo';
}

export function formatarTamanhoDataset(tamanhoMb, fallback = 'Nao informado') {
  const valorNormalizado = normalizarNumero(tamanhoMb);
  if (valorNormalizado === null) {
    return fallback;
  }

  if (valorNormalizado >= 1024) {
    return `${formatarNumero(valorNormalizado / 1024)} GB`;
  }

  return `${formatarNumero(valorNormalizado)} MB`;
}

export function normalizarDatasetCatalogo(item) {
  if (!item || typeof item !== 'object') {
    return null;
  }

  const tamanhoMb = normalizarNumero(item.tamanho_mb ?? item.tamanhoMb);
  const downloadUrl = item.url_download ?? item.downloadUrl ?? null;

  return {
    id: item.id,
    titulo: item.titulo || 'Dataset sem titulo',
    resumo: item.resumo || 'Resumo indisponivel.',
    fonte: item.fonte || 'Nao informado',
    tipoDado: item.tipo_dado || item.tipoDado || 'Nao informado',
    localizacao: item.localizacao || 'Nao informado',
    localSlug: item.local_slug || item.localSlug || null,
    estado: item.estado || '',
    cidade: item.cidade || '',
    formato: item.formato || 'Nao informado',
    recorteTemporal: inferirRecorteTemporal(item),
    dataInicio: item.data_inicio || item.dataInicio || null,
    dataFim: item.data_fim || item.dataFim || null,
    dataPublicacao: item.data_publicacao || item.dataPublicacao || null,
    periodoRotulo: item.periodo_rotulo || item.periodoRotulo || 'Nao informado',
    tamanhoMb,
    tamanho: item.tamanho || formatarTamanhoDataset(tamanhoMb),
    downloadUrl: downloadUrl || null,
  };
}

export function criarOpcoesFiltro(datasets, campo, opcaoPadrao) {
  const vistos = new Set();
  const opcoes = [opcaoPadrao];

  datasets.forEach((item) => {
    const valor = item?.[campo];
    if (!valor || vistos.has(valor)) {
      return;
    }

    vistos.add(valor);
    opcoes.push(valor);
  });

  return opcoes;
}
