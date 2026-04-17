import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CalendarRange,
  CheckCircle2,
  Database,
  Download,
  ExternalLink,
  Filter,
  Fish,
  ImageOff,
  Info,
  MapPin,
  Search,
} from 'lucide-react';

import PainelRisco from './PainelRisco';
import { FALLBACK_DETALHES, FALLBACK_RECIFES } from './recifeData';

const DADOS_GERAIS = [
  {
    id: 'copernicus_sst_2026_03',
    titulo: 'Temperatura da Superficie do Mar (SST) - Abrolhos',
    tipoData: 'intervalo',
    dataInicio: '2026-03-01',
    dataFim: '2026-03-31',
    dataPublicacao: null,
    estado: 'Bahia',
    cidade: 'Caravelas',
    fonte: 'Copernicus',
    tamanho: '1.8 GB',
    formato: 'CSV',
    downloadUrl: '/dados/sst.csv',
  },
  {
    id: 'noaa_dhw_2026_03',
    titulo: 'Degree Heating Week (DHW) - Banco dos Abrolhos',
    tipoData: 'intervalo',
    dataInicio: '2026-03-01',
    dataFim: '2026-03-31',
    dataPublicacao: null,
    estado: 'Bahia',
    cidade: 'Alcobaca',
    fonte: 'NOAA',
    tamanho: '420 MB',
    formato: 'NetCDF',
    downloadUrl: '/dados/dhw.csv',
  },
  {
    id: 'ncbi_especies_2026_q1',
    titulo: 'Compilado genetico de especies de corais',
    tipoData: 'publicacao',
    dataInicio: null,
    dataFim: null,
    dataPublicacao: '2026-04-05',
    estado: 'Bahia',
    cidade: 'Porto Seguro',
    fonte: 'NCBI',
    tamanho: '95 MB',
    formato: 'FASTA',
    downloadUrl: null,
  },
  {
    id: 'nasa_par_2026_03',
    titulo: 'Irradiancia PAR costeira',
    tipoData: 'intervalo',
    dataInicio: '2026-03-15',
    dataFim: '2026-03-31',
    dataPublicacao: null,
    estado: 'Pernambuco',
    cidade: 'Recife',
    fonte: 'NASA',
    tamanho: '780 MB',
    formato: 'CSV',
    downloadUrl: '/dados/par.csv',
  },
];

const FONTES = ['Todas', ...new Set(DADOS_GERAIS.map((item) => item.fonte))];
const ESTADOS = ['Todos', ...new Set(DADOS_GERAIS.map((item) => item.estado))];

function formatarData(data) {
  if (!data) {
    return 'Nao informado';
  }

  const [ano, mes, dia] = data.split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarPeriodo(item) {
  if (item.tipoData === 'publicacao') {
    return `Publicado em ${formatarData(item.dataPublicacao)}`;
  }

  return `${formatarData(item.dataInicio)} ate ${formatarData(item.dataFim)}`;
}

function ImagemRecife({ nome, imagem }) {
  if (imagem) {
    return <img src={imagem} alt={nome} className="h-48 w-full object-cover" />;
  }

  return (
    <div className="flex h-48 w-full items-end bg-gradient-to-br from-ocean-dark via-ocean-light to-cyan-400 p-4 text-white">
      <div>
        <ImageOff size={18} className="mb-2 opacity-80" />
        <p className="text-sm font-semibold">{nome}</p>
      </div>
    </div>
  );
}

function possuiPainelCompleto(monitoramento) {
  if (!monitoramento) {
    return false;
  }

  const camposObrigatorios = [
    'sst_atual',
    'dhw_calculado',
    'irradiancia',
    'salinidade',
    'ph',
    'oxigenio',
    'nitrato',
    'clorofila',
    'turbidez',
  ];

  return camposObrigatorios.every(
    (campo) => monitoramento[campo] !== null && monitoramento[campo] !== undefined,
  );
}

function combinarLocais(apiLocais = []) {
  const mapa = new Map(FALLBACK_RECIFES.map((local) => [local.slug, { ...local }]));

  apiLocais.forEach((local) => {
    const anterior = mapa.get(local.slug) || {};
    mapa.set(local.slug, {
      ...anterior,
      ...local,
      imagem_url: local.imagem_url || anterior.imagem_url || '',
      informacoes_disponiveis:
        local.informacoes_disponiveis ?? anterior.informacoes_disponiveis ?? 0,
    });
  });

  return Array.from(mapa.values());
}

function combinarDetalhe(recifeBase, detalheApi) {
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
      recifeBase.informacoes_disponiveis ??
      (especiesApi || detalheFallback.especies || []).length,
  };
}

async function buscarJson(url) {
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

function resolverLinkImagem(especie) {
  return especie?.fonte_imagem_url || especie?.foto_url || '';
}

function resolverRotuloLinkImagem(especie) {
  return especie?.fonte_imagem_url ? 'Ver fonte da imagem' : 'Abrir imagem';
}

function resolverCreditoImagem(especie) {
  return especie?.credito_imagem || (especie?.foto_url ? 'Acervo local do projeto' : '');
}

function Header({ onNavigate }) {
  return (
    <header className="sticky top-0 z-40 bg-ocean-dark text-white shadow-md">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <button
          type="button"
          onClick={() => onNavigate('home')}
          className="text-left text-lg font-bold tracking-tight sm:text-xl"
        >
          Projeto Coral Brasil
        </button>

        <nav className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onNavigate('home')}
            className="rounded-lg bg-white/10 px-4 py-2 transition hover:bg-white/20"
          >
            Pagina inicial
          </button>
          <button
            type="button"
            onClick={() => onNavigate('recifes')}
            className="rounded-lg bg-terra px-4 py-2 font-semibold transition hover:opacity-90"
          >
            Escolher recifes
          </button>
          <button
            type="button"
            onClick={() => onNavigate('banco')}
            className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 font-semibold text-ocean-dark transition hover:bg-sand-light"
          >
            <Database size={16} />
            Banco de dados geral
          </button>
        </nav>
      </div>
    </header>
  );
}

function HomePage({ onNavigate }) {
  return (
    <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="rounded-3xl border border-sand-dark/20 bg-white p-8 shadow-lg md:p-12">
        <p className="mb-3 text-xs uppercase tracking-[0.2em] text-ocean-light">Introducao</p>
        <h1 className="mb-4 text-3xl font-bold text-ocean-dark md:text-5xl">
          Monitoramento integrado para recifes de coral do Brasil
        </h1>
        <p className="mb-8 max-w-3xl leading-relaxed text-gray-600">
          Esta plataforma centraliza dados ambientais, referencias complementares e
          acompanhamento de risco para apoiar pesquisa, gestao e observacao de recifes.
        </p>

        <div className="grid gap-4 md:grid-cols-2">
          <button
            type="button"
            onClick={() => onNavigate('recifes')}
            className="rounded-2xl border border-ocean-light/20 bg-sand-light/30 p-5 text-left transition hover:border-ocean-light/50 hover:shadow-md"
          >
            <div className="mb-2 inline-flex items-center gap-2 font-semibold text-ocean-dark">
              <MapPin size={18} />
              Pagina de localizacoes de corais
            </div>
            <p className="text-sm text-gray-600">
              Explore recifes, veja o painel de risco de cada local e consulte sua galeria
              de especies.
            </p>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('banco')}
            className="rounded-2xl border border-ocean-light/20 bg-sand-light/30 p-5 text-left transition hover:border-ocean-light/50 hover:shadow-md"
          >
            <div className="mb-2 inline-flex items-center gap-2 font-semibold text-ocean-dark">
              <Database size={18} />
              Banco de dados geral
            </div>
            <p className="text-sm text-gray-600">
              Consulte conjuntos de dados por fonte, periodo e localizacao antes de baixar.
            </p>
          </button>
        </div>
      </div>
    </section>
  );
}

function BancoDadosPage() {
  const [termoBusca, setTermoBusca] = useState('');
  const [fonteSelecionada, setFonteSelecionada] = useState('Todas');
  const [estadoSelecionado, setEstadoSelecionado] = useState('Todos');

  const resultados = useMemo(() => {
    const termoNormalizado = termoBusca.trim().toLowerCase();

    return DADOS_GERAIS.filter((item) => {
      const bateBusca =
        !termoNormalizado ||
        item.titulo.toLowerCase().includes(termoNormalizado) ||
        item.cidade.toLowerCase().includes(termoNormalizado) ||
        item.estado.toLowerCase().includes(termoNormalizado);

      const bateFonte =
        fonteSelecionada === 'Todas' || item.fonte === fonteSelecionada;

      const bateEstado =
        estadoSelecionado === 'Todos' || item.estado === estadoSelecionado;

      return bateBusca && bateFonte && bateEstado;
    });
  }, [estadoSelecionado, fonteSelecionada, termoBusca]);

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center gap-3">
        <Database className="text-ocean-dark" />
        <div>
          <h2 className="text-2xl font-bold text-ocean-dark">Banco de dados geral</h2>
          <p className="text-sm text-gray-600">
            Dados de predicao e referencias complementares reunidos em um unico catalogo.
          </p>
        </div>
      </div>

      <div className="grid gap-4 rounded-2xl border border-sand-dark/20 bg-white p-5 shadow-sm md:grid-cols-3">
        <label className="block">
          <span className="mb-2 inline-flex items-center gap-2 text-sm font-semibold text-ocean-dark">
            <Search size={16} />
            Buscar
          </span>
          <input
            value={termoBusca}
            onChange={(event) => setTermoBusca(event.target.value)}
            placeholder="Titulo, cidade ou estado"
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 outline-none transition focus:border-ocean-light"
          />
        </label>

        <label className="block">
          <span className="mb-2 inline-flex items-center gap-2 text-sm font-semibold text-ocean-dark">
            <Filter size={16} />
            Fonte
          </span>
          <select
            value={fonteSelecionada}
            onChange={(event) => setFonteSelecionada(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 outline-none transition focus:border-ocean-light"
          >
            {FONTES.map((fonte) => (
              <option key={fonte} value={fonte}>
                {fonte}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-2 inline-flex items-center gap-2 text-sm font-semibold text-ocean-dark">
            <MapPin size={16} />
            Estado
          </span>
          <select
            value={estadoSelecionado}
            onChange={(event) => setEstadoSelecionado(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 outline-none transition focus:border-ocean-light"
          >
            {ESTADOS.map((estado) => (
              <option key={estado} value={estado}>
                {estado}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="mt-4 text-sm text-gray-600">
        {resultados.length} conjunto(s) encontrado(s).
      </p>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        {resultados.length === 0 && (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500">
            Nenhum conjunto de dados corresponde aos filtros atuais.
          </div>
        )}

        {resultados.map((item) => (
          <article
            key={item.id}
            className="rounded-2xl border border-sand-dark/20 bg-white p-5 shadow-sm"
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-ocean-light">
                  {item.fonte}
                </p>
                <h3 className="mt-1 text-lg font-bold text-ocean-dark">{item.titulo}</h3>
              </div>
              <span className="rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-gray-700">
                {item.formato}
              </span>
            </div>

            <div className="space-y-2 text-sm text-gray-600">
              <p className="inline-flex items-center gap-2">
                <MapPin size={15} />
                {item.estado} - {item.cidade}
              </p>
              <p className="inline-flex items-center gap-2">
                <CalendarRange size={15} />
                {formatarPeriodo(item)}
              </p>
              <p>
                <strong>Tamanho:</strong> {item.tamanho}
              </p>
            </div>

            <div className="mt-5">
              {item.downloadUrl ? (
                <a
                  href={item.downloadUrl}
                  className="inline-flex items-center gap-2 rounded-xl bg-ocean-dark px-4 py-2 text-sm font-semibold text-white transition hover:bg-ocean-light"
                >
                  <Download size={16} />
                  Baixar conjunto
                </a>
              ) : (
                <span className="inline-flex items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900">
                  <AlertTriangle size={16} />
                  Download indisponivel no momento
                </span>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function RecifesPage({ locais, onSelect }) {
  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h2 className="text-2xl font-bold text-ocean-dark">Localizacoes de corais</h2>
      <p className="mb-6 mt-2 text-gray-600">
        Cada pagina de local possui painel de risco e galeria de especies associadas.
      </p>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {locais.map((local) => (
          <button
            key={local.slug}
            type="button"
            onClick={() => onSelect(local.slug)}
            className="overflow-hidden rounded-2xl border border-sand-dark/20 bg-white text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md"
          >
            <ImagemRecife nome={local.nome} imagem={local.imagem_url} />
            <div className="p-5">
              <h3 className="text-lg font-bold text-ocean-dark">{local.nome}</h3>
              <p className="mt-1 text-sm text-gray-500">
                {local.estado} - {local.cidade}
              </p>
              <p className="mt-3 text-sm font-medium text-gray-700">
                Informacoes disponiveis: {local.informacoes_disponiveis}
              </p>
              <p className="mt-2 text-sm text-gray-500">
                Ultima atualizacao: {formatarData(local.ultima_atualizacao)}
              </p>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function CardEspecie({ especie, onOpen }) {
  const linkImagem = resolverLinkImagem(especie);
  const rotuloLinkImagem = resolverRotuloLinkImagem(especie);
  const creditoImagem = resolverCreditoImagem(especie);

  return (
    <article className="overflow-hidden rounded-2xl border border-sand-dark/20 bg-white text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md">
      <button type="button" onClick={() => onOpen(especie)} className="block w-full text-left">
        <div className="flex h-56 items-center justify-center overflow-hidden bg-sand-light">
          {especie.foto_url ? (
            <img src={especie.foto_url} alt={especie.nome_comum} className="h-full w-full object-cover" />
          ) : (
            <Fish size={64} className="text-ocean-light/50" />
          )}
        </div>
        <div className="p-5">
          <div className="mb-2 flex items-start justify-between gap-3">
            <div>
              <h4 className="text-lg font-bold text-ocean-dark">
                {especie.nome_comum || 'Nome nao informado'}
              </h4>
              <p className="text-sm italic text-gray-500">{especie.nome_cientifico}</p>
            </div>
            <span className="rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-gray-700">
              {especie.tipo}
            </span>
          </div>

          <p className="line-clamp-3 text-sm text-gray-600">
            {especie.descricao || 'Sem descricao cadastrada para esta especie.'}
          </p>
        </div>
      </button>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-sand-dark/10 px-5 py-4 text-sm">
        <span className="text-gray-500">{creditoImagem || 'Sem credito de imagem'}</span>
        {linkImagem && (
          <a
            href={linkImagem}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 font-semibold text-ocean-dark hover:underline"
          >
            <ExternalLink size={14} />
            {rotuloLinkImagem}
          </a>
        )}
      </div>
    </article>
  );
}

function ModalEspecie({ especie, onClose }) {
  if (!especie) {
    return null;
  }

  const linkImagem = resolverLinkImagem(especie);
  const rotuloLinkImagem = resolverRotuloLinkImagem(especie);
  const creditoImagem = resolverCreditoImagem(especie);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ocean-dark/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-3xl bg-white shadow-2xl md:flex"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex h-72 items-center justify-center bg-sand-light md:h-auto md:w-1/2">
          {especie.foto_url ? (
            <img src={especie.foto_url} alt={especie.nome_comum} className="h-full w-full object-cover" />
          ) : (
            <Fish size={96} className="text-ocean-light/50" />
          )}
        </div>

        <div className="relative overflow-y-auto p-8 md:w-1/2">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 rounded-full bg-sand-light px-3 py-1 text-sm font-semibold text-ocean-dark"
          >
            Fechar
          </button>

          <span className="mb-3 inline-flex items-center gap-2 rounded-full bg-sand-light px-3 py-1 text-xs font-semibold uppercase tracking-wider text-ocean-dark">
            <Info size={14} />
            {especie.tipo}
          </span>
          <h3 className="text-3xl font-bold text-ocean-dark">
            {especie.nome_comum || 'Nome nao informado'}
          </h3>
          <p className="mt-1 text-lg italic text-gray-500">{especie.nome_cientifico}</p>

          <div className="mt-6 space-y-5 text-sm text-gray-600">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-ocean-light">
                Descricao
              </p>
              <p className="leading-relaxed">
                {especie.descricao || 'Sem descricao detalhada cadastrada.'}
              </p>
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-ocean-light">
                Conservacao
              </p>
              <p>{especie.status_conservacao || 'Nao avaliado'}</p>
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-ocean-light">
                Credito da imagem
              </p>
              <p>{creditoImagem || 'Sem credito informado'}</p>
            </div>

            {linkImagem && (
              <a
                href={linkImagem}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-ocean-light/30 px-4 py-2 font-semibold text-ocean-dark transition hover:bg-ocean-dark hover:text-white"
              >
                <ExternalLink size={16} />
                {rotuloLinkImagem}
              </a>
            )}

            {especie.fonte_url && (
              <a
                href={especie.fonte_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-ocean-light/30 px-4 py-2 font-semibold text-ocean-dark transition hover:bg-ocean-dark hover:text-white"
              >
                <ExternalLink size={16} />
                Fonte e mais informacoes
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function LocalDetalhePage({ recife, onBack, siteOffline, offlineMessage, onOpenEspecie }) {
  const painelDisponivel = possuiPainelCompleto(recife.monitoramento_recente);
  const especies = recife.especies || [];

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <button
        type="button"
        onClick={onBack}
        className="mb-4 font-medium text-ocean-dark transition hover:underline"
      >
        Voltar para localizacoes
      </button>

      <div className="overflow-hidden rounded-3xl border border-sand-dark/20 bg-white shadow-sm">
        <ImagemRecife nome={recife.nome} imagem={recife.imagem_url} />

        <div className="p-6">
          <h2 className="text-2xl font-bold text-ocean-dark">{recife.nome}</h2>
          <p className="mt-1 text-gray-600">
            {recife.estado} - {recife.cidade}
          </p>
          <p className="mt-4 leading-relaxed text-gray-600">{recife.descricao}</p>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-sand-dark/20 p-4">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-ocean-light">
                Catalogo local
              </p>
              <p className="mt-2 text-sm text-gray-600">
                Informacoes disponiveis: {recife.informacoes_disponiveis}
              </p>
              <p className="mt-1 text-sm text-gray-600">
                Ultima atualizacao: {formatarData(recife.ultima_atualizacao)}
              </p>
            </div>

            <div className="rounded-2xl border border-sand-dark/20 p-4">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-ocean-light">
                Painel de risco
              </p>
              {painelDisponivel ? (
                <p className="mt-2 inline-flex items-center gap-2 text-sm text-emerald-700">
                  <CheckCircle2 size={16} />
                  Variaveis minimas disponiveis para predicao neste local.
                </p>
              ) : (
                <p className="mt-2 inline-flex items-center gap-2 text-sm text-amber-700">
                  <AlertTriangle size={16} />
                  Ainda faltam variaveis essenciais para predicao.
                </p>
              )}
            </div>
          </div>

          {siteOffline && (
            <div className="mt-6 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
              <strong>Modo manutencao:</strong> {offlineMessage || 'Exibindo dados locais de referencia.'}
            </div>
          )}

          <div className="mt-6 rounded-2xl border border-sand-dark/20 p-4">
            <h3 className="mb-4 text-lg font-semibold text-ocean-dark">
              Painel de risco da localizacao
            </h3>

            {painelDisponivel ? (
              <PainelRisco dados={recife.monitoramento_recente} />
            ) : (
              <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
                O painel de risco permanece desabilitado para este recife ate que as
                variaveis obrigatorias sejam completadas.
              </div>
            )}
          </div>

          <div className="mt-8">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-ocean-dark">Galeria de especies</h3>
                <p className="text-sm text-gray-500">
                  Especies cadastradas e associadas a este local.
                </p>
              </div>
              <span className="inline-flex items-center gap-2 rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-ocean-dark">
                <Activity size={14} />
                {especies.length} especie(s)
              </span>
            </div>

            {especies.length > 0 ? (
              <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                {especies.map((especie) => (
                  <CardEspecie key={especie.id} especie={especie} onOpen={onOpenEspecie} />
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500">
                Nenhuma especie foi associada a este recife ainda no painel administrativo.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [pagina, setPagina] = useState('home');
  const [locais, setLocais] = useState(FALLBACK_RECIFES);
  const [recifeSelecionado, setRecifeSelecionado] = useState(null);
  const [detalhesPorSlug, setDetalhesPorSlug] = useState({});
  const [especieSelecionada, setEspecieSelecionada] = useState(null);
  const [siteOffline, setSiteOffline] = useState(false);
  const [offlineMessage, setOfflineMessage] = useState('');

  useEffect(() => {
    let ativo = true;

    async function carregarBase() {
      const [statusPayload, locaisPayload] = await Promise.all([
        buscarJson('/api/status/'),
        buscarJson('/api/locais/'),
      ]);

      if (!ativo) {
        return;
      }

      if (statusPayload) {
        setSiteOffline(Boolean(statusPayload.offline_mode));
        setOfflineMessage(statusPayload.message || '');
      }

      if (Array.isArray(locaisPayload) && locaisPayload.length > 0) {
        setLocais(combinarLocais(locaisPayload));
      }
    }

    carregarBase();

    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    let ativo = true;

    if (pagina !== 'detalhe' || !recifeSelecionado) {
      return undefined;
    }

    async function carregarDetalhe() {
      const detalhePayload = await buscarJson(`/api/locais/${recifeSelecionado}/`);
      if (!ativo || !detalhePayload) {
        return;
      }

      const localBase =
        locais.find((local) => local.slug === recifeSelecionado) ||
        FALLBACK_RECIFES.find((local) => local.slug === recifeSelecionado);

      if (!localBase) {
        return;
      }

      setDetalhesPorSlug((anterior) => ({
        ...anterior,
        [recifeSelecionado]: combinarDetalhe(localBase, detalhePayload),
      }));
    }

    carregarDetalhe();

    return () => {
      ativo = false;
    };
  }, [locais, pagina, recifeSelecionado]);

  const recifeAtual = useMemo(() => {
    if (!recifeSelecionado) {
      return null;
    }

    const localBase =
      locais.find((local) => local.slug === recifeSelecionado) ||
      FALLBACK_RECIFES.find((local) => local.slug === recifeSelecionado);

    return combinarDetalhe(localBase, detalhesPorSlug[recifeSelecionado]);
  }, [detalhesPorSlug, locais, recifeSelecionado]);

  const navegar = (destino) => {
    if (destino !== 'detalhe') {
      setRecifeSelecionado(null);
      setEspecieSelecionada(null);
    }

    setPagina(destino);
  };

  const abrirRecife = (recifeSlug) => {
    setRecifeSelecionado(recifeSlug);
    setEspecieSelecionada(null);
    setPagina('detalhe');
  };

  return (
    <div className="min-h-screen bg-sand-light text-gray-800">
      <Header onNavigate={navegar} />

      {siteOffline && (
        <div className="mx-auto max-w-7xl px-4 pt-6 sm:px-6">
          <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            <strong>Modo manutencao:</strong>{' '}
            {offlineMessage || 'Site em manutencao para reestruturacao do backend e banco de dados.'}
          </div>
        </div>
      )}

      {pagina === 'home' && <HomePage onNavigate={navegar} />}
      {pagina === 'banco' && <BancoDadosPage />}
      {pagina === 'recifes' && <RecifesPage locais={locais} onSelect={abrirRecife} />}
      {pagina === 'detalhe' && recifeAtual && (
        <LocalDetalhePage
          recife={recifeAtual}
          onBack={() => navegar('recifes')}
          siteOffline={siteOffline}
          offlineMessage={offlineMessage}
          onOpenEspecie={setEspecieSelecionada}
        />
      )}

      <ModalEspecie especie={especieSelecionada} onClose={() => setEspecieSelecionada(null)} />
    </div>
  );
}
