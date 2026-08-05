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
