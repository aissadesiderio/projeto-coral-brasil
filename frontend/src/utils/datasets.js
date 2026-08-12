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
    // ⚠️ Vem do servidor, e o padrao e `false` — nunca `true`. Um catalogo
    // antigo (ou o fallback de `data/datasets.js`, que so tem link de
    // provedor) cai aqui, e assumir "exige conta" esconderia atras de um
    // convite ao login um download que qualquer um poderia fazer.
    exigeContaAprovada:
      (item.download_exige_conta ?? item.exigeContaAprovada) === true,
    cobertura: normalizarCobertura(item.cobertura),
  };
}

/**
 * A cobertura real, derivada do banco pelo servidor.
 *
 * 🚨 Existe por um defeito medido em 27/07/2026: a pagina anunciava **nove**
 * datasets e a API servia **tres**. Os outros seis apareciam com titulo,
 * formato e periodo sem uma unica medicao no banco.
 *
 * ⚠️ `null` significa **"o servidor nao informou"**, e nao "sem dado". Um
 * catalogo antigo (ou o fallback local de `data/datasets.js`) cai aqui, e a
 * tela precisa poder dizer "nao verificado" em vez de afirmar ausencia.
 */
export function normalizarCobertura(cobertura) {
  if (!cobertura || typeof cobertura !== 'object') {
    return null;
  }

  return {
    espelhado: cobertura.espelhado === true,
    motivo: cobertura.motivo || null,
    nMedicoes: Number(cobertura.n_medicoes) || 0,
    variaveis: Array.isArray(cobertura.variaveis) ? cobertura.variaveis : [],
    locais: Array.isArray(cobertura.locais) ? cobertura.locais : [],
    dataInicio: cobertura.data_inicio || null,
    dataFim: cobertura.data_fim || null,
    consulta: cobertura.consulta || null,
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
