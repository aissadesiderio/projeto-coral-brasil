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
import homeCardBanco from './assets/home/card-banco.png';
import homeCardPainel from './assets/home/card-painel.png';
import homeCardRecifes from './assets/home/card-recifes.png';
import homeHeroCoral from './assets/home/hero-coral.png';
import { CAMPOS_MONITORAMENTO_OBRIGATORIOS, RISCO_STATUS } from './monitoramentoConfig';
import { FALLBACK_DETALHES, FALLBACK_RECIFES } from './recifeData';
import svgPaths from './svg-r6f04ghq4r';

const DADOS_GERAIS = [
  {
    id: 'copernicus_sst_abrolhos_2026_03',
    titulo: 'Temperatura da superficie do mar - Abrolhos',
    tipoDado: 'Climatico',
    recorteTemporal: 'intervalo',
    dataInicio: '2026-03-01',
    dataFim: '2026-03-31',
    dataPublicacao: null,
    periodoRotulo: 'Mar/2026',
    estado: 'Bahia',
    cidade: 'Caravelas',
    localizacao: 'Parque Nacional Marinho de Abrolhos',
    localSlug: 'abrolhos-ba',
    fonte: 'Copernicus',
    tamanho: '1.8 GB',
    formato: 'CSV',
    resumo:
      'Serie mensal de temperatura da superficie do mar usada para acompanhamento termico do recife.',
    downloadUrl: '/dados/sst.csv',
  },
  {
    id: 'noaa_dhw_abrolhos_2026_03',
    titulo: 'Degree Heating Week - Banco dos Abrolhos',
    tipoDado: 'Oceanografico',
    recorteTemporal: 'intervalo',
    dataInicio: '2026-03-01',
    dataFim: '2026-03-31',
    dataPublicacao: null,
    periodoRotulo: 'Mar/2026',
    estado: 'Bahia',
    cidade: 'Caravelas',
    localizacao: 'Parque Nacional Marinho de Abrolhos',
    localSlug: 'abrolhos-ba',
    fonte: 'NOAA',
    tamanho: '420 MB',
    formato: 'NetCDF',
    resumo: 'Camada mensal de aquecimento acumulado para monitoramento de estresse termico.',
    downloadUrl: '/dados/dhw.csv',
  },
  {
    id: 'inventario_biodiversidade_abrolhos_2026_q1',
    titulo: 'Inventario de biodiversidade recifal - Abrolhos',
    tipoDado: 'Biodiversidade',
    recorteTemporal: 'publicacao',
    dataInicio: null,
    dataFim: null,
    dataPublicacao: '2026-04-06',
    periodoRotulo: 'Abr/2026',
    estado: 'Bahia',
    cidade: 'Caravelas',
    localizacao: 'Parque Nacional Marinho de Abrolhos',
    localSlug: 'abrolhos-ba',
    fonte: 'Projeto Coral Brasil',
    tamanho: '48 MB',
    formato: 'JSON',
    resumo: 'Levantamento consolidado de especies associadas ao recife e suas ocorrencias.',
    downloadUrl: '/dados/biodiversidade-abrolhos.json',
  },
  {
    id: 'microbioma_picaozinho_2026_03',
    titulo: 'Microbioma de agua recifal - Picaozinho',
    tipoDado: 'Microbioma',
    recorteTemporal: 'intervalo',
    dataInicio: '2026-03-10',
    dataFim: '2026-03-24',
    dataPublicacao: null,
    periodoRotulo: 'Mar/2026',
    estado: 'Paraiba',
    cidade: 'Joao Pessoa',
    localizacao: 'Recife de Picaozinho',
    localSlug: 'picaozinho-pb',
    fonte: 'NCBI',
    tamanho: '3.1 GB',
    formato: 'FASTQ',
    resumo: 'Sequenciamento metagenomico para avaliacao microbiana do ambiente recifal.',
    downloadUrl: null,
  },
  {
    id: 'genetico_abrolhos_2026_q1',
    titulo: 'Banco genetico de corais brasileiros - Abrolhos',
    tipoDado: 'Genetico',
    recorteTemporal: 'publicacao',
    dataInicio: null,
    dataFim: null,
    dataPublicacao: '2026-04-05',
    periodoRotulo: 'Abr/2026',
    estado: 'Bahia',
    cidade: 'Caravelas',
    localizacao: 'Parque Nacional Marinho de Abrolhos',
    localSlug: 'abrolhos-ba',
    fonte: 'NCBI',
    tamanho: '95 MB',
    formato: 'FASTA',
    resumo: 'Compilado genetico com sequencias de referencia para especies coralineas.',
    downloadUrl: null,
  },
  {
    id: 'imagem_porto_2026_04',
    titulo: 'Mosaico fotografico subaquatico - Porto de Galinhas',
    tipoDado: 'Imagem',
    recorteTemporal: 'intervalo',
    dataInicio: '2026-04-01',
    dataFim: '2026-04-12',
    dataPublicacao: null,
    periodoRotulo: 'Abr/2026',
    estado: 'Pernambuco',
    cidade: 'Ipojuca',
    localizacao: 'Piscinas Naturais de Porto de Galinhas',
    localSlug: 'porto-de-galinhas-pe',
    fonte: 'Projeto Coral Brasil',
    tamanho: '2.4 GB',
    formato: 'GeoTIFF',
    resumo: 'Colecao de imagens georreferenciadas para inspeção visual do recife.',
    downloadUrl: '/dados/mosaico-porto.tif',
  },
  {
    id: 'relatorio_picaozinho_2026_04',
    titulo: 'Relatorio tecnico de campo - Picaozinho',
    tipoDado: 'Relatorio',
    recorteTemporal: 'publicacao',
    dataInicio: null,
    dataFim: null,
    dataPublicacao: '2026-04-18',
    periodoRotulo: 'Abr/2026',
    estado: 'Paraiba',
    cidade: 'Joao Pessoa',
    localizacao: 'Recife de Picaozinho',
    localSlug: 'picaozinho-pb',
    fonte: 'Projeto Coral Brasil',
    tamanho: '12 MB',
    formato: 'PDF',
    resumo: 'Relatorio com observacoes de campo, fotografias e anotacoes de amostragem.',
    downloadUrl: '/dados/relatorio-picaozinho.pdf',
  },
  {
    id: 'modelo_branqueamento_nordeste_2026_q2',
    titulo: 'Modelo preditivo de branqueamento - Costa Nordeste',
    tipoDado: 'Modelo preditivo',
    recorteTemporal: 'publicacao',
    dataInicio: null,
    dataFim: null,
    dataPublicacao: '2026-04-22',
    periodoRotulo: 'Abr/2026',
    estado: 'Regional',
    cidade: 'Costa Nordeste',
    localizacao: 'Costa Nordeste',
    localSlug: null,
    fonte: 'Projeto Coral Brasil',
    tamanho: '680 MB',
    formato: 'Parquet',
    resumo: 'Saida consolidada de um modelo regional para risco de branqueamento coralino.',
    downloadUrl: '/dados/modelo-branqueamento.parquet',
  },
];

const FONTES = ['Todas', ...new Set(DADOS_GERAIS.map((item) => item.fonte))];
const TIPOS_DADO = ['Todos', ...new Set(DADOS_GERAIS.map((item) => item.tipoDado))];
const LOCALIZACOES = ['Todas', ...new Set(DADOS_GERAIS.map((item) => item.localizacao))];
const FORMATOS = ['Todos', ...new Set(DADOS_GERAIS.map((item) => item.formato))];
const ESTADOS = ['Todos', ...new Set(DADOS_GERAIS.map((item) => item.estado))];
const PERIODOS = ['Todos', ...new Set(DADOS_GERAIS.map((item) => item.periodoRotulo))];

const HOME_DESTAQUES = [
  {
    id: 'recifes',
    pagina: 'recifes',
    imagem: homeCardRecifes,
    titulo: 'Recifes Monitorados',
    descricao: 'Veja dados ambientais, risco atual e especies associadas por localizacao.',
  },
  {
    id: 'painel',
    pagina: 'recifes',
    imagem: homeCardPainel,
    titulo: 'Painel de Risco',
    descricao: 'Acompanhe temperatura, DHW, PAR, salinidade, oxigenio e clorofila.',
  },
  {
    id: 'banco',
    pagina: 'banco',
    imagem: homeCardBanco,
    titulo: 'Banco de Dados',
    descricao: 'Consulte datasets climaticos, biologicos, geneticos, imagens e relatorios.',
  },
];

function formatarData(data) {
  if (!data) {
    return 'Nao informado';
  }

  const [ano, mes, dia] = data.split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarPeriodo(item) {
  if (item.recorteTemporal === 'publicacao') {
    return `Publicado em ${formatarData(item.dataPublicacao)}`;
  }

  return `${formatarData(item.dataInicio)} ate ${formatarData(item.dataFim)}`;
}

function formatarLocal(item) {
  return `${item.estado} - ${item.cidade}`;
}

function formatarQuantidadeEspecies(total) {
  return `${total} ${total === 1 ? 'especie cadastrada' : 'especies cadastradas'}`;
}

function obterMetaRisco(nivelAlerta) {
  return RISCO_STATUS[nivelAlerta] || RISCO_STATUS.SEM_RISCO;
}

function scrollToTopo() {
  if (typeof window !== 'undefined' && typeof window.scrollTo === 'function') {
    try {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      window.scrollTo(0, 0);
    }
  }
}

function ImagemRecife({ nome, imagem, className = 'h-48 w-full object-cover' }) {
  const fallbackClassName = className.replace('object-cover', '').trim();

  if (imagem) {
    return <img src={imagem} alt={nome} className={className} />;
  }

  return (
    <div
      className={`flex items-end bg-gradient-to-br from-ocean-dark via-ocean-light to-cyan-400 p-4 text-white ${fallbackClassName}`}
    >
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

  return CAMPOS_MONITORAMENTO_OBRIGATORIOS.every(
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
        local.quantidade_especies ??
        local.informacoes_disponiveis ??
        anterior.informacoes_disponiveis ??
        0,
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
      detalheApi?.quantidade_especies ??
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

function obterQuantidadeEspeciesLocal(local) {
  const especiesFallback = FALLBACK_DETALHES[local.slug]?.especies?.length;
  return (
    local.quantidade_especies ??
    local.informacoes_disponiveis ??
    especiesFallback ??
    0
  );
}

function obterMonitoramentoLocal(local) {
  return (
    local.monitoramento_recente ||
    FALLBACK_DETALHES[local.slug]?.monitoramento_recente ||
    null
  );
}

function obterRiscoAtualLocal(local) {
  return (
    local.nivel_alerta ||
    local.risco_atual ||
    obterMonitoramentoLocal(local)?.nivel_alerta ||
    null
  );
}

function obterItensNavegacao(paginaAtual) {
  if (paginaAtual === 'banco') {
    return [
      { id: 'home', rotulo: 'Pagina inicial', destino: 'home' },
      { id: 'recifes', rotulo: 'Explorar recifes', destino: 'recifes' },
    ];
  }

  if (paginaAtual === 'recifes' || paginaAtual === 'detalhe') {
    return [
      { id: 'home', rotulo: 'Pagina inicial', destino: 'home' },
      { id: 'banco', rotulo: 'Banco de dados', destino: 'banco' },
    ];
  }

  return [
    { id: 'recifes', rotulo: 'Explorar recifes', destino: 'recifes' },
    { id: 'banco', rotulo: 'Banco de dados', destino: 'banco' },
  ];
}

function obterDatasetsRelacionados(localSlug) {
  return DADOS_GERAIS.filter((item) => item.localSlug === localSlug);
}

function BrandMark({ claro = false }) {
  return (
    <div className={claro ? 'text-white' : 'text-ocean-dark'}>
      <span className="block text-[1.55rem] font-black leading-[0.88] tracking-tight sm:text-[1.9rem]">
        Projeto
      </span>
      <span className="block text-[1.55rem] font-black leading-[0.88] tracking-tight sm:text-[1.9rem]">
        Coral Brasil
      </span>
      <span
        className={`mt-1 block max-w-[14rem] text-[0.58rem] font-semibold uppercase tracking-[0.2em] ${
          claro ? 'text-white/70' : 'text-ocean-dark/65'
        }`}
      >
        Monitoramento, biodiversidade e risco nos recifes brasileiros
      </span>
    </div>
  );
}

function InstagramIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path d={svgPaths.p3c382d72} fill="currentColor" fillOpacity="0.45" />
    </svg>
  );
}

function LinkedinIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path
        clipRule="evenodd"
        d={svgPaths.p1fcf5070}
        fill="currentColor"
        fillOpacity="0.45"
        fillRule="evenodd"
      />
      <path d={svgPaths.pe7ea00} fill="#fff" />
      <path d={svgPaths.p1ab31680} fill="#fff" />
      <path d={svgPaths.p28c6df0} fill="#fff" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path d={svgPaths.pdaf0200} fill="currentColor" fillOpacity="0.45" />
    </svg>
  );
}

function Header({ onNavigate, paginaAtual }) {
  const isHome = paginaAtual === 'home';
  const itensNavegacao = obterItensNavegacao(paginaAtual);

  return (
    <header
      className={
        isHome
          ? 'relative z-40 bg-[#2b6978] text-white'
          : 'sticky top-0 z-40 border-b border-white/10 bg-[#2b6978]/95 text-white shadow-md backdrop-blur'
      }
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <button
          type="button"
          onClick={() => onNavigate('home')}
          className="shrink-0 text-left"
          aria-label="Ir para a pagina inicial"
        >
          <BrandMark claro />
        </button>

        <nav className="flex flex-wrap items-center gap-2 sm:gap-3 lg:justify-end">
          {itensNavegacao.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.destino)}
              className="rounded-full bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20 sm:px-5"
            >
              {item.rotulo}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}

function HomePage({ onNavigate, siteOffline, offlineMessage }) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-[#2b6978] via-[#b0d7d4] via-[40%] to-[#ffefeb]">
      <div className="absolute left-1/2 top-0 h-72 w-72 -translate-x-1/2 rounded-full bg-white/10 blur-3xl" />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 pb-20 pt-4 sm:px-6 sm:pb-24 lg:px-8">
        {siteOffline && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/95 p-4 text-sm text-amber-950 shadow-sm backdrop-blur">
            <strong>Modo manutencao:</strong>{' '}
            {offlineMessage || 'Exibindo dados locais de referencia durante a reestruturacao.'}
          </div>
        )}

        <div className="flex justify-center pt-4 sm:pt-8">
          <img
            src={homeHeroCoral}
            alt="Coral em destaque na pagina inicial"
            className="w-full max-w-[980px] object-contain drop-shadow-[0_32px_48px_rgba(19,74,87,0.18)]"
          />
        </div>

        <div className="max-w-3xl pb-4 sm:pb-10">
          <h1 className="text-[1.9rem] font-bold leading-[1.15] tracking-[-0.02em] text-[#2b6978] sm:text-[2.4rem] lg:text-[2.75rem]">
            Mergulhe na biodiversidade coralina brasileira.
          </h1>
          <p className="mt-4 max-w-2xl text-base font-medium leading-[1.55] text-black/60 sm:text-lg">
            Esta plataforma centraliza dados ambientais, referencias complementares e
            acompanhamento de risco para apoiar pesquisa, gestao e observacao de recifes.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => onNavigate('recifes')}
              className="rounded-[10px] bg-[#2b6978] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#245766] sm:w-auto"
            >
              Explorar recifes
            </button>
            <button
              type="button"
              onClick={() => onNavigate('banco')}
              className="rounded-[10px] border border-[#2b6978]/20 bg-white/70 px-5 py-3 text-sm font-medium text-[#2b6978] transition hover:bg-white"
            >
              Banco de dados geral
            </button>
          </div>
        </div>

        <ul className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {HOME_DESTAQUES.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onNavigate(item.pagina)}
                className="group block w-full text-left"
              >
                <div className="relative aspect-[362.66/483] overflow-hidden rounded-2xl shadow-lg shadow-ocean-dark/10">
                  <img
                    src={item.imagem}
                    alt={item.titulo}
                    className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
                  />
                </div>

                <div className="pt-6">
                  <h2 className="text-2xl font-semibold leading-[1.2] tracking-[-0.02em] text-[#2b6978]">
                    {item.titulo}
                  </h2>
                  <p className="mt-2 text-base leading-[1.55] text-black/60 sm:text-lg">
                    {item.descricao}
                  </p>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function CampoFiltro({ label, icon: Icon, children }) {
  return (
    <label className="block min-w-0">
      <span className="mb-2 inline-flex items-center gap-2 text-sm font-semibold text-ocean-dark">
        <Icon size={16} />
        {label}
      </span>
      {children}
    </label>
  );
}

function DatasetCard({ item, compact = false }) {
  const padding = compact ? 'p-4' : 'p-5';

  return (
    <article
      className={`flex h-full flex-col rounded-2xl border border-sand-dark/20 bg-white ${padding} shadow-sm`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-ocean-light">
            {item.fonte}
          </p>
          <h3 className="mt-1 text-lg font-bold text-ocean-dark">{item.titulo}</h3>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-gray-700">
            {item.tipoDado}
          </span>
          <span className="rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-gray-700">
            {item.formato}
          </span>
        </div>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-gray-600">{item.resumo}</p>

      <div className="mt-4 space-y-2 text-sm text-gray-600">
        <p className="inline-flex items-center gap-2">
          <MapPin size={15} />
          {item.localizacao} - {formatarLocal(item)}
        </p>
        <p className="inline-flex items-center gap-2">
          <CalendarRange size={15} />
          {formatarPeriodo(item)}
        </p>
        <p>
          <strong>Tamanho:</strong> {item.tamanho}
        </p>
      </div>

      <div className="mt-5 flex flex-1 items-end">
        {item.downloadUrl ? (
          <a
            href={item.downloadUrl}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-ocean-dark px-4 py-2 text-sm font-semibold text-white transition hover:bg-ocean-light sm:w-auto"
          >
            <Download size={16} />
            Baixar conjunto
          </a>
        ) : (
          <span className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900 sm:w-auto">
            <AlertTriangle size={16} />
            Download indisponivel no momento
          </span>
        )}
      </div>
    </article>
  );
}

function BancoDadosPage() {
  const [termoBusca, setTermoBusca] = useState('');
  const [fonteSelecionada, setFonteSelecionada] = useState('Todas');
  const [tipoDadoSelecionado, setTipoDadoSelecionado] = useState('Todos');
  const [localizacaoSelecionada, setLocalizacaoSelecionada] = useState('Todas');
  const [formatoSelecionado, setFormatoSelecionado] = useState('Todos');
  const [estadoSelecionado, setEstadoSelecionado] = useState('Todos');
  const [periodoSelecionado, setPeriodoSelecionado] = useState('Todos');

  const resultados = useMemo(() => {
    const termoNormalizado = termoBusca.trim().toLowerCase();

    return DADOS_GERAIS.filter((item) => {
      const bateBusca =
        !termoNormalizado ||
        item.titulo.toLowerCase().includes(termoNormalizado) ||
        item.cidade.toLowerCase().includes(termoNormalizado) ||
        item.estado.toLowerCase().includes(termoNormalizado) ||
        item.resumo.toLowerCase().includes(termoNormalizado);

      const bateFonte =
        fonteSelecionada === 'Todas' || item.fonte === fonteSelecionada;
      const bateTipo =
        tipoDadoSelecionado === 'Todos' || item.tipoDado === tipoDadoSelecionado;
      const bateLocalizacao =
        localizacaoSelecionada === 'Todas' || item.localizacao === localizacaoSelecionada;
      const bateFormato =
        formatoSelecionado === 'Todos' || item.formato === formatoSelecionado;
      const bateEstado =
        estadoSelecionado === 'Todos' || item.estado === estadoSelecionado;
      const batePeriodo =
        periodoSelecionado === 'Todos' || item.periodoRotulo === periodoSelecionado;

      return (
        bateBusca &&
        bateFonte &&
        bateTipo &&
        bateLocalizacao &&
        bateFormato &&
        bateEstado &&
        batePeriodo
      );
    });
  }, [
    estadoSelecionado,
    formatoSelecionado,
    fonteSelecionada,
    localizacaoSelecionada,
    periodoSelecionado,
    termoBusca,
    tipoDadoSelecionado,
  ]);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <div className="rounded-3xl border border-sand-dark/20 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <Database className="mt-1 text-ocean-dark" />
            <div>
              <h2 className="text-2xl font-bold text-ocean-dark">Banco de dados geral</h2>
              <p className="mt-1 max-w-3xl text-sm leading-relaxed text-gray-600 sm:text-base">
                Catalogo amplo de datasets climaticos, oceanograficos, biologicos,
                geneticos, imagens, relatorios e modelos preditivos associados ao projeto.
              </p>
            </div>
          </div>

          <span className="rounded-full bg-sand-light px-4 py-2 text-sm font-semibold text-ocean-dark">
            {resultados.length} dataset(s)
          </span>
        </div>
      </div>

      <div className="grid gap-4 rounded-3xl border border-sand-dark/20 bg-white p-5 shadow-sm md:grid-cols-2 xl:grid-cols-4">
        <CampoFiltro label="Buscar" icon={Search}>
          <input
            value={termoBusca}
            onChange={(event) => setTermoBusca(event.target.value)}
            placeholder="Titulo, resumo, cidade ou estado"
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          />
        </CampoFiltro>

        <CampoFiltro label="Fonte" icon={Filter}>
          <select
            value={fonteSelecionada}
            onChange={(event) => setFonteSelecionada(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {FONTES.map((fonte) => (
              <option key={fonte} value={fonte}>
                {fonte}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Tipo de dado" icon={Database}>
          <select
            value={tipoDadoSelecionado}
            onChange={(event) => setTipoDadoSelecionado(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {TIPOS_DADO.map((tipo) => (
              <option key={tipo} value={tipo}>
                {tipo}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Localizacao" icon={MapPin}>
          <select
            value={localizacaoSelecionada}
            onChange={(event) => setLocalizacaoSelecionada(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {LOCALIZACOES.map((localizacao) => (
              <option key={localizacao} value={localizacao}>
                {localizacao}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Formato" icon={Download}>
          <select
            value={formatoSelecionado}
            onChange={(event) => setFormatoSelecionado(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {FORMATOS.map((formato) => (
              <option key={formato} value={formato}>
                {formato}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Estado" icon={MapPin}>
          <select
            value={estadoSelecionado}
            onChange={(event) => setEstadoSelecionado(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {ESTADOS.map((estado) => (
              <option key={estado} value={estado}>
                {estado}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Periodo" icon={CalendarRange}>
          <select
            value={periodoSelecionado}
            onChange={(event) => setPeriodoSelecionado(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {PERIODOS.map((periodo) => (
              <option key={periodo} value={periodo}>
                {periodo}
              </option>
            ))}
          </select>
        </CampoFiltro>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {resultados.length === 0 && (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500 lg:col-span-2">
            Nenhum conjunto de dados corresponde aos filtros atuais.
          </div>
        )}

        {resultados.map((item) => (
          <DatasetCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  );
}

function BadgeRisco({ nivelAlerta }) {
  const meta = obterMetaRisco(nivelAlerta);

  return (
    <span
      className={`inline-flex w-fit items-center rounded-full border px-3 py-1 text-xs font-semibold ${meta.bordaClasse} ${meta.fundoClasse} ${meta.textoClasse}`}
    >
      {meta.textoCurto}
    </span>
  );
}

function RecifesPage({ locais, onSelect }) {
  const possuiLocais = locais.length > 0;

  return (
    <section className="py-8 sm:py-10 lg:py-12">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl">
          <h2 className="text-4xl font-bold tracking-[-0.03em] text-[#2b6978] sm:text-[3.15rem]">
            Explorar Localizacoes
          </h2>
          <p className="mt-4 text-base leading-7 text-slate-600">
            Visualize as localizacoes monitoradas e abra cada pagina para consultar
            biodiversidade, risco atual e historico recente.
          </p>
        </div>

        {possuiLocais ? (
          <div className="grid gap-x-6 gap-y-10 md:grid-cols-2 lg:grid-cols-3">
            {locais.map((local) => {
              const quantidadeEspecies = obterQuantidadeEspeciesLocal(local);
              const nivelAlerta = obterRiscoAtualLocal(local);
              const metaRisco = obterMetaRisco(nivelAlerta);
              const ultimaAtualizacao =
                local.ultima_atualizacao || obterMonitoramentoLocal(local)?.data || null;

              return (
                <button
                  key={local.slug}
                  type="button"
                  onClick={() => onSelect(local.slug)}
                  className="group flex h-full flex-col text-left transition duration-300 hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2b6978] focus-visible:ring-offset-4 focus-visible:ring-offset-[#fff6f4]"
                >
                  <div className="overflow-hidden rounded-[22px] bg-white shadow-[0_18px_45px_rgba(43,105,120,0.12)]">
                    <ImagemRecife
                      nome={local.nome}
                      imagem={local.imagem_url}
                      className="h-56 w-full object-cover transition duration-500 group-hover:scale-[1.03]"
                    />
                  </div>

                  <div className="flex flex-1 flex-col px-1 pb-1 pt-5">
                    <h3 className="text-[1.6rem] font-bold leading-[1.15] tracking-[-0.025em] text-[#2b6978]">
                      {local.nome}
                    </h3>

                    <p className="mt-5 inline-flex items-center gap-2 text-sm text-slate-500">
                      <MapPin size={16} className="text-[#2b6978]" />
                      {local.estado} - {local.cidade}
                    </p>

                    <div className="mt-5 space-y-1.5 text-sm leading-6 text-slate-700">
                      <p>{formatarQuantidadeEspecies(quantidadeEspecies)}</p>
                      <p>
                        Risco atual:{' '}
                        <span className={`font-semibold ${metaRisco.textoClasse}`}>
                          {metaRisco.textoCurto}
                        </span>
                      </p>
                      <p>Ultima atualizacao: {formatarData(ultimaAtualizacao)}</p>
                    </div>

                    <div className="mt-5 inline-flex items-center gap-3">
                      <BadgeRisco nivelAlerta={nivelAlerta} />
                      <span className="inline-flex items-center gap-1 text-sm font-semibold text-[#2b6978]">
                        Abrir
                        <ExternalLink
                          size={15}
                          className="transition duration-300 group-hover:translate-x-0.5"
                        />
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="flex min-h-[320px] flex-col items-center justify-center rounded-[32px] border border-dashed border-[#2b6978]/20 bg-white/80 px-6 py-12 text-center shadow-sm">
            <div className="rounded-full bg-[#f4fbfc] p-4 text-[#2b6978]">
              <MapPin size={28} />
            </div>
            <h3 className="mt-5 text-2xl font-semibold text-[#194452]">
              Nenhuma localizacao disponivel no momento
            </h3>
            <p className="mt-3 max-w-xl text-base leading-7 text-slate-600">
              Assim que novas localizacoes forem carregadas, elas aparecerao aqui
              automaticamente com seus dados de risco, biodiversidade e atualizacao.
            </p>
          </div>
        )}
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
            <img
              src={especie.foto_url}
              alt={especie.nome_comum}
              className="h-full w-full object-cover"
            />
          ) : (
            <Fish size={64} className="text-ocean-light/50" />
          )}
        </div>
        <div className="p-5">
          <div className="mb-2 flex items-start justify-between gap-3">
            <div className="min-w-0">
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
        <div className="flex h-64 items-center justify-center bg-sand-light md:h-auto md:w-1/2">
          {especie.foto_url ? (
            <img
              src={especie.foto_url}
              alt={especie.nome_comum}
              className="h-full w-full object-cover"
            />
          ) : (
            <Fish size={96} className="text-ocean-light/50" />
          )}
        </div>

        <div className="relative overflow-y-auto p-6 sm:p-8 md:w-1/2">
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

function SectionTitle({ titulo, descricao }) {
  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-xl font-semibold text-ocean-dark sm:text-2xl">{titulo}</h3>
      <p className="text-sm leading-relaxed text-gray-600 sm:text-base">{descricao}</p>
    </div>
  );
}

function LocalDetalhePage({ recife, onBack, siteOffline, offlineMessage, onOpenEspecie }) {
  const medicaoAmbientalAtual = recife.monitoramento_recente;
  const painelDisponivel = possuiPainelCompleto(medicaoAmbientalAtual);
  const especiesAssociadas = recife.especies || [];
  const datasetsRelacionados = obterDatasetsRelacionados(recife.slug);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <button
        type="button"
        onClick={onBack}
        className="w-fit font-medium text-ocean-dark transition hover:underline"
      >
        Voltar para localizacoes
      </button>

      <div className="overflow-hidden rounded-3xl border border-sand-dark/20 bg-white shadow-sm">
        <ImagemRecife
          nome={recife.nome}
          imagem={recife.imagem_url}
          className="h-56 w-full object-cover sm:h-72"
        />

        <div className="p-5 sm:p-6 lg:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ocean-light">
            Localizacao monitorada
          </p>
          <h2 className="mt-2 text-3xl font-bold text-ocean-dark sm:text-4xl">{recife.nome}</h2>
          <p className="mt-2 text-base text-gray-600">{formatarLocal(recife)}</p>
          <p className="mt-4 max-w-4xl leading-relaxed text-gray-600">{recife.descricao}</p>
          <p className="mt-4 text-sm text-gray-500">
            Ultima atualizacao: {formatarData(recife.ultima_atualizacao)}
          </p>
        </div>
      </div>

      {siteOffline && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          <strong>Modo manutencao:</strong>{' '}
          {offlineMessage || 'Exibindo dados locais de referencia.'}
        </div>
      )}

      <section className="space-y-4">
        <SectionTitle
          titulo="Painel de predicao"
          descricao={`Painel consolidado de predicao de risco e monitoramento associado a ${recife.nome}.`}
        />

        {painelDisponivel ? (
          <PainelRisco dados={medicaoAmbientalAtual} />
        ) : (
          <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            O painel de predicao permanece desabilitado para este recife ate que as
            variaveis obrigatorias sejam completadas.
          </div>
        )}

        <div className="rounded-2xl border border-sand-dark/20 bg-white p-4 shadow-sm sm:p-5">
          <p className="inline-flex items-center gap-2 text-sm font-medium text-ocean-dark">
            {painelDisponivel ? (
              <>
                <CheckCircle2 size={16} />
                Variaveis minimas disponiveis para predicao nesta localizacao.
              </>
            ) : (
              <>
                <AlertTriangle size={16} />
                Ainda faltam variaveis essenciais para liberar a predicao.
              </>
            )}
          </p>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <SectionTitle
            titulo="Especies associadas"
            descricao={`Especies vinculadas a ${recife.nome} na camada biologica da plataforma.`}
          />
          <span className="inline-flex w-fit items-center gap-2 rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-ocean-dark">
            <Activity size={14} />
            {especiesAssociadas.length} especie(s)
          </span>
        </div>

        {especiesAssociadas.length > 0 ? (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {especiesAssociadas.map((especie) => (
              <CardEspecie key={especie.id} especie={especie} onOpen={onOpenEspecie} />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500">
            Nenhuma especie foi associada a esta localizacao ainda no painel administrativo.
          </div>
        )}
      </section>

      <section className="space-y-4">
        <SectionTitle
          titulo="Datasets relacionados"
          descricao={`Datasets do catalogo geral que fazem referencia direta a ${recife.nome}.`}
        />

        {datasetsRelacionados.length > 0 ? (
          <div className="grid gap-5 lg:grid-cols-2">
            {datasetsRelacionados.map((dataset) => (
              <DatasetCard key={dataset.id} item={dataset} compact />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500">
            Ainda nao ha datasets relacionados diretamente a esta localizacao.
          </div>
        )}
      </section>
    </section>
  );
}

function Footer({ onNavigate }) {
  return (
    <footer className="bg-[#ffefeb]">
      <div className="mx-auto flex max-w-7xl flex-col gap-12 border-t border-black/10 px-4 py-14 sm:px-6 lg:flex-row lg:justify-between lg:px-8 lg:py-16">
        <div>
          <h2 className="text-2xl font-semibold tracking-[-0.02em] text-black">
            Projeto Coral Brasil
          </h2>
          <p className="mt-3 max-w-xs text-base leading-[1.45] text-black/55">
            Monitoramento, biodiversidade e conservacao dos recifes brasileiros.
          </p>
          <div className="mt-8 flex items-center gap-6 text-black/45">
            <InstagramIcon />
            <LinkedinIcon />
            <XIcon />
          </div>
        </div>

        <div className="grid gap-10 sm:grid-cols-3 sm:gap-12">
          <div>
            <p className="pb-4 text-sm font-semibold tracking-[-0.01em] text-black">
              Projeto
            </p>
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => onNavigate('home')}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Sobre
              </button>
              <button
                type="button"
                onClick={() => onNavigate('recifes')}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Banco de Especies
              </button>
              <button
                type="button"
                onClick={() => onNavigate('recifes')}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Monitoramento
              </button>
            </div>
          </div>

          <div>
            <p className="pb-4 text-sm font-semibold tracking-[-0.01em] text-black">
              Dados
            </p>
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => onNavigate('banco')}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                NOAA
              </button>
              <button
                type="button"
                onClick={() => onNavigate('banco')}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Copernicus
              </button>
              <button
                type="button"
                onClick={() => onNavigate('banco')}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Metodologia
              </button>
            </div>
          </div>

          <div>
            <p className="pb-4 text-sm font-semibold tracking-[-0.01em] text-black">
              Contato
            </p>
            <div className="space-y-2 text-base text-black/55">
              <p>GitHub</p>
              <p>Equipe</p>
              <button
                type="button"
                onClick={() => onNavigate('banco')}
                className="block text-left transition hover:text-black"
              >
                Relatorios
              </button>
            </div>
          </div>
        </div>
      </div>
    </footer>
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
    scrollToTopo();
  };

  const abrirRecife = (recifeSlug) => {
    setRecifeSelecionado(recifeSlug);
    setEspecieSelecionada(null);
    setPagina('detalhe');
    scrollToTopo();
  };

  return (
    <div className="app-layout min-h-screen overflow-x-hidden bg-sand-light text-gray-800">
      <Header onNavigate={navegar} paginaAtual={pagina} />

      <main className={`main-content flex-1 ${pagina === 'recifes' ? 'bg-[#fff6f4]' : ''}`}>
        {siteOffline && pagina !== 'home' && (
          <div className="mx-auto max-w-7xl px-4 pt-6 sm:px-6 lg:px-8">
            <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
              <strong>Modo manutencao:</strong>{' '}
              {offlineMessage ||
                'Site em manutencao para reestruturacao do backend e banco de dados.'}
            </div>
          </div>
        )}

        {pagina === 'home' && (
          <HomePage
            onNavigate={navegar}
            siteOffline={siteOffline}
            offlineMessage={offlineMessage}
          />
        )}
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
      </main>

      <Footer onNavigate={navegar} />
      <ModalEspecie especie={especieSelecionada} onClose={() => setEspecieSelecionada(null)} />
    </div>
  );
}
