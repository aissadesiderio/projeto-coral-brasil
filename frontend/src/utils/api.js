export async function buscarJson(url) {
  if (typeof fetch !== 'function') {
    return null;
  }

  try {
    const response = await fetch(url);
    if (!response.ok) {
      return null;
    }

    return await response.json();
  } catch (error) {
    return null;
  }
}

export async function buscarCatalogoDatasets() {
  return buscarJson('/api/datasets/');
}

export async function buscarDatasetsRelacionadosPorLocal(localSlug) {
  return buscarJson(`/api/locais/${localSlug}/datasets/`);
}

const METODOS_SEGUROS = new Set(['GET', 'HEAD', 'OPTIONS']);

export function lerCookie(nome) {
  if (typeof document === 'undefined') {
    return null;
  }

  const parte = document.cookie
    .split('; ')
    .find((linha) => linha.startsWith(`${nome}=`));

  return parte ? decodeURIComponent(parte.split('=')[1]) : null;
}

/**
 * POST/PATCH/DELETE autenticados, com CSRF anexado quando o metodo exige.
 *
 * ⚠️ Nao reaproveita `buscarJson` de proposito: aquele engole todo erro em
 * `null`, o que aqui esconderia exatamente a diferenca que a tela precisa
 * mostrar — 401 (faca login), 403 (aguarde aprovacao) e 202 (enviado para
 * revisao) sao estados diferentes, nao "deu errado".
 */
export async function enviarFormulario(url, { method = 'POST', body } = {}) {
  if (typeof fetch !== 'function') {
    return { ok: false, status: 0, dados: null };
  }

  const cabecalhos = { 'Content-Type': 'application/json' };
  if (!METODOS_SEGUROS.has(method.toUpperCase())) {
    const token = lerCookie('csrftoken');
    if (token) {
      cabecalhos['X-CSRFToken'] = token;
    }
  }

  try {
    const response = await fetch(url, {
      method,
      headers: cabecalhos,
      credentials: 'same-origin',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    let dados = null;
    try {
      dados = await response.json();
    } catch (error) {
      dados = null;
    }

    return { ok: response.ok, status: response.status, dados };
  } catch (error) {
    return { ok: false, status: 0, dados: null };
  }
}
