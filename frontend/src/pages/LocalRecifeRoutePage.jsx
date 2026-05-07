import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { obterDatasetsRelacionadosFallback } from '../data/datasets';
import { FALLBACK_RECIFES } from '../data/recifeData';
import { buscarDatasetsRelacionadosPorLocal, buscarJson } from '../utils/api';
import { normalizarDatasetCatalogo } from '../utils/datasets';
import { combinarDetalhe } from '../utils/recifes';
import { ROTAS_APP } from '../utils/navigation';
import LocalRecifePage from './LocalRecifePage';

function EstadoCarregandoDetalhe() {
  return (
    <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <div className="rounded-3xl border border-sand-dark/20 bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ocean-light">
          Localizacao monitorada
        </p>
        <h2 className="mt-3 text-3xl font-bold text-ocean-dark sm:text-4xl">
          Carregando localizacao...
        </h2>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-600">
          Estamos resolvendo o slug desta rota e carregando os dados mais recentes do
          recife selecionado.
        </p>
      </div>
    </section>
  );
}

function EstadoLocalizacaoNaoEncontrada() {
  return (
    <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <div className="rounded-3xl border border-dashed border-sand-dark/30 bg-white p-8 shadow-sm sm:p-10">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ocean-light">
          Localizacao nao encontrada
        </p>
        <h2 className="mt-3 text-3xl font-bold text-ocean-dark sm:text-4xl">
          Este recife nao esta disponivel na rota informada.
        </h2>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-600">
          Confira o link acessado ou volte para a lista de localizacoes monitoradas para
          abrir outro detalhe.
        </p>
        <Link
          to={ROTAS_APP.recifes}
          className="mt-6 w-fit rounded-[10px] bg-[#2b6978] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#245766]"
        >
          Voltar para localizacoes
        </Link>
      </div>
    </section>
  );
}

export default function LocalRecifeRoutePage({
  locais,
  carregandoLocais,
  detalhesPorSlug,
  setDetalhesPorSlug,
  siteOffline,
  offlineMessage,
  onOpenEspecie,
}) {
  const { slug } = useParams();
  const detalheCache = slug ? detalhesPorSlug[slug] : null;
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false);
  const [erroDetalhe, setErroDetalhe] = useState(false);
  const [datasetsRelacionados, setDatasetsRelacionados] = useState([]);
  const [carregandoDatasetsRelacionados, setCarregandoDatasetsRelacionados] = useState(false);
  const [erroDatasetsRelacionados, setErroDatasetsRelacionados] = useState(false);
  const [usandoFallbackDatasets, setUsandoFallbackDatasets] = useState(false);

  const localBase = useMemo(
    () =>
      locais.find((local) => local.slug === slug) ||
      FALLBACK_RECIFES.find((local) => local.slug === slug) ||
      null,
    [locais, slug],
  );

  useEffect(() => {
    let ativo = true;

    if (!slug || !localBase || detalheCache) {
      return undefined;
    }

    async function carregarDetalhe() {
      setCarregandoDetalhe(true);
      setErroDetalhe(false);

      const detalhePayload = await buscarJson(`/api/grafo/localizacoes/${slug}/`);
      const detalheValido =
        detalhePayload &&
        typeof detalhePayload === 'object' &&
        Object.keys(detalhePayload).length > 0;

      if (!ativo) {
        return;
      }

      if (detalheValido) {
        setDetalhesPorSlug((anterior) => ({
          ...anterior,
          [slug]: detalhePayload,
        }));
      } else {
        setErroDetalhe(true);
      }

      setCarregandoDetalhe(false);
    }

    carregarDetalhe();

    return () => {
      ativo = false;
    };
  }, [detalheCache, localBase, setDetalhesPorSlug, slug]);

  useEffect(() => {
    let ativo = true;

    if (!slug || !localBase) {
      setDatasetsRelacionados([]);
      setCarregandoDatasetsRelacionados(false);
      setErroDatasetsRelacionados(false);
      setUsandoFallbackDatasets(false);
      return undefined;
    }

    async function carregarDatasetsRelacionados() {
      setCarregandoDatasetsRelacionados(true);
      setErroDatasetsRelacionados(false);
      setUsandoFallbackDatasets(false);
      setDatasetsRelacionados([]);

      const payload = await buscarDatasetsRelacionadosPorLocal(slug);
      if (!ativo) {
        return;
      }

      if (Array.isArray(payload)) {
        setDatasetsRelacionados(payload.map(normalizarDatasetCatalogo).filter(Boolean));
        setCarregandoDatasetsRelacionados(false);
        return;
      }

      const fallbackDatasets = obterDatasetsRelacionadosFallback(slug)
        .map(normalizarDatasetCatalogo)
        .filter(Boolean);

      setDatasetsRelacionados(fallbackDatasets);
      setErroDatasetsRelacionados(true);
      setUsandoFallbackDatasets(fallbackDatasets.length > 0);
      setCarregandoDatasetsRelacionados(false);
    }

    carregarDatasetsRelacionados();

    return () => {
      ativo = false;
    };
  }, [localBase, slug]);

  const recifeAtual = useMemo(
    () => combinarDetalhe(localBase, detalheCache),
    [detalheCache, localBase],
  );

  if (carregandoLocais && !localBase) {
    return <EstadoCarregandoDetalhe />;
  }

  if (!localBase) {
    return <EstadoLocalizacaoNaoEncontrada />;
  }

  return (
    <LocalRecifePage
      recife={recifeAtual}
      siteOffline={siteOffline}
      offlineMessage={offlineMessage}
      onOpenEspecie={onOpenEspecie}
      carregandoDetalhe={carregandoDetalhe}
      erroDetalhe={erroDetalhe}
      datasetsRelacionados={datasetsRelacionados}
      carregandoDatasetsRelacionados={carregandoDatasetsRelacionados}
      erroDatasetsRelacionados={erroDatasetsRelacionados}
      usandoFallbackDatasets={usandoFallbackDatasets}
    />
  );
}
