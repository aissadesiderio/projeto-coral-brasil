import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CalendarRange,
  CheckCircle2,
  Database,
  Download,
  Filter,
  ImageOff,
  MapPin,
  Search,
} from 'lucide-react';
import PainelRisco from './PainelRisco';

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

const RECIFES = [
  {
    id: 'abrolhos_ba',
    nome: 'Parque Nacional Marinho de Abrolhos',
    estado: 'Bahia',
    cidade: 'Caravelas',
    imagem: '',
    informacoesDisponiveis: 32,
    variaveisMinimas: true,
    ultimaAtualizacao: '2026-04-14',
    descricao:
      'Area com serie historica de monitoramento e disponibilidade de variaveis essenciais para o painel de risco.',
  },
  {
    id: 'picaozinho_pb',
    nome: 'Recife de Picaozinho',
    estado: 'Paraiba',
    cidade: 'Joao Pessoa',
    imagem: '',
    informacoesDisponiveis: 17,
    variaveisMinimas: false,
    ultimaAtualizacao: '2026-04-10',
    descricao:
      'Local com catalogo biologico relevante, mas ainda com lacunas nas variaveis usadas para predicao.',
  },
  {
    id: 'porto_de_galinhas_pe',
    nome: 'Piscinas Naturais de Porto de Galinhas',
    estado: 'Pernambuco',
    cidade: 'Ipojuca',
    imagem: '',
    informacoesDisponiveis: 26,
    variaveisMinimas: true,
    ultimaAtualizacao: '2026-04-15',
    descricao:
      'Zona recifal de interesse turistico com dados ambientais recentes e historico de monitoramento.',
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
              Explore recifes, informacoes disponiveis e a disponibilidade do painel de risco.
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

function RecifesPage({ onSelect }) {
  return (
    <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h2 className="text-2xl font-bold text-ocean-dark">Localizacoes de corais</h2>
      <p className="mb-6 mt-2 text-gray-600">
        Selecione um local para ver suas informacoes e a disponibilidade do painel de risco.
      </p>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {RECIFES.map((local) => (
          <button
            key={local.id}
            type="button"
            onClick={() => onSelect(local.id)}
            className="overflow-hidden rounded-2xl border border-sand-dark/20 bg-white text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md"
          >
            <ImagemRecife nome={local.nome} imagem={local.imagem} />
            <div className="p-5">
              <h3 className="text-lg font-bold text-ocean-dark">{local.nome}</h3>
              <p className="mt-1 text-sm text-gray-500">
                {local.estado} - {local.cidade}
              </p>
              <p className="mt-3 text-sm font-medium text-gray-700">
                Informacoes disponiveis: {local.informacoesDisponiveis}
              </p>
              <p className="mt-2 text-sm text-gray-500">
                Ultima atualizacao: {formatarData(local.ultimaAtualizacao)}
              </p>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function LocalDetalhePage({ recife, onBack, siteOffline, offlineMessage }) {
  return (
    <section className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <button
        type="button"
        onClick={onBack}
        className="mb-4 font-medium text-ocean-dark transition hover:underline"
      >
        Voltar para localizacoes
      </button>

      <div className="overflow-hidden rounded-3xl border border-sand-dark/20 bg-white shadow-sm">
        <ImagemRecife nome={recife.nome} imagem={recife.imagem} />

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
                Informacoes disponiveis: {recife.informacoesDisponiveis}
              </p>
              <p className="mt-1 text-sm text-gray-600">
                Ultima atualizacao: {formatarData(recife.ultimaAtualizacao)}
              </p>
            </div>

            <div className="rounded-2xl border border-sand-dark/20 p-4">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-ocean-light">
                Painel de risco
              </p>
              {recife.variaveisMinimas ? (
                <p className="mt-2 inline-flex items-center gap-2 text-sm text-emerald-700">
                  <CheckCircle2 size={16} />
                  Variaveis minimas disponiveis para predicao.
                </p>
              ) : (
                <p className="mt-2 inline-flex items-center gap-2 text-sm text-amber-700">
                  <AlertTriangle size={16} />
                  Ainda faltam variaveis essenciais para predicao.
                </p>
              )}
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-sand-dark/20 p-4">
            <h3 className="mb-3 text-lg font-semibold text-ocean-dark">
              Painel de risco da localizacao
            </h3>

            {siteOffline ? (
              <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
                <strong>Modo manutencao:</strong>{' '}
                {offlineMessage || 'O backend esta temporariamente offline.'}
              </div>
            ) : recife.variaveisMinimas ? (
              <div className="space-y-4">
                <PainelRisco publicOffline={false} />
                <p className="text-sm text-gray-500">
                  Se o painel nao aparecer, a API pode estar sem registros recentes em
                  <code className="ml-1 rounded bg-sand-light px-1 py-0.5">/api/monitoramento/</code>.
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
                O painel de risco permanece desabilitado para este recife ate que as
                variaveis obrigatorias sejam completadas.
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
  const [recifeSelecionado, setRecifeSelecionado] = useState(null);
  const [siteOffline, setSiteOffline] = useState(false);
  const [offlineMessage, setOfflineMessage] = useState('');

  useEffect(() => {
    let ativo = true;

    if (typeof fetch !== 'function') {
      return undefined;
    }

    async function carregarStatus() {
      try {
        const response = await fetch('/api/status/');
        if (!response.ok) {
          return;
        }

        const payload = await response.json();
        if (!ativo) {
          return;
        }

        setSiteOffline(Boolean(payload.offline_mode));
        setOfflineMessage(payload.message || '');
      } catch (error) {
        if (!ativo) {
          return;
        }

        setSiteOffline(false);
        setOfflineMessage('');
      }
    }

    carregarStatus();

    return () => {
      ativo = false;
    };
  }, []);

  const recifeAtual = useMemo(
    () => RECIFES.find((item) => item.id === recifeSelecionado) || null,
    [recifeSelecionado],
  );

  const navegar = (destino) => {
    if (destino !== 'detalhe') {
      setRecifeSelecionado(null);
    }

    setPagina(destino);
  };

  const abrirRecife = (recifeId) => {
    setRecifeSelecionado(recifeId);
    setPagina('detalhe');
  };

  return (
    <div className="min-h-screen bg-sand-light text-gray-800">
      <Header onNavigate={navegar} />

      {siteOffline && (
        <div className="mx-auto max-w-7xl px-4 pt-6 sm:px-6">
          <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            <strong>Modo manutencao:</strong>{' '}
            {offlineMessage ||
              'Site em manutencao para reestruturacao do backend e banco de dados.'}
          </div>
        </div>
      )}

      {pagina === 'home' && <HomePage onNavigate={navegar} />}
      {pagina === 'banco' && <BancoDadosPage />}
      {pagina === 'recifes' && <RecifesPage onSelect={abrirRecife} />}
      {pagina === 'detalhe' && recifeAtual && (
        <LocalDetalhePage
          recife={recifeAtual}
          onBack={() => navegar('recifes')}
          siteOffline={siteOffline}
          offlineMessage={offlineMessage}
        />
      )}
    </div>
  );
}
