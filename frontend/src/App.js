import React, { useEffect, useMemo, useState } from 'react';

import Footer from './components/Footer';
import Header from './components/Header';
import ModalEspecie from './components/ModalEspecie';
import { FALLBACK_RECIFES } from './data/recifeData';
import BancoDadosPage from './pages/BancoDadosPage';
import HomePage from './pages/HomePage';
import LocalRecifePage from './pages/LocalRecifePage';
import RecifesPage from './pages/RecifesPage';
import { buscarJson } from './utils/api';
import { scrollToTopo } from './utils/formatters';
import { combinarDetalhe, combinarLocais } from './utils/recifes';

export default function App() {
  const [pagina, setPagina] = useState('home');
  const [locais, setLocais] = useState([]);
  const [recifeSelecionado, setRecifeSelecionado] = useState(null);
  const [detalhesPorSlug, setDetalhesPorSlug] = useState({});
  const [especieSelecionada, setEspecieSelecionada] = useState(null);
  const [siteOffline, setSiteOffline] = useState(false);
  const [offlineMessage, setOfflineMessage] = useState('');
  const [carregandoLocais, setCarregandoLocais] = useState(true);

  useEffect(() => {
    let ativo = true;

    async function carregarBase() {
      const [statusPayload, locaisPayload] = await Promise.all([
        buscarJson('/api/status/'),
        buscarJson('/api/grafo/localizacoes/'),
      ]);

      if (!ativo) {
        return;
      }

      if (statusPayload) {
        setSiteOffline(Boolean(statusPayload.offline_mode));
        setOfflineMessage(statusPayload.message || '');
      }

      const locaisNormalizados = Array.isArray(locaisPayload) ? combinarLocais(locaisPayload) : [];
      setLocais(locaisNormalizados.length > 0 ? locaisNormalizados : FALLBACK_RECIFES);
      setCarregandoLocais(false);
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
      const detalhePayload = await buscarJson(`/api/grafo/localizacoes/${recifeSelecionado}/`);
      const detalheValido =
        detalhePayload &&
        typeof detalhePayload === 'object' &&
        Object.keys(detalhePayload).length > 0;

      if (!ativo || !detalheValido) {
        return;
      }

      const localBase = locais.find((local) => local.slug === recifeSelecionado);
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

    const localBase = locais.find((local) => local.slug === recifeSelecionado);
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
        {pagina === 'recifes' && (
          <RecifesPage locais={locais} onSelect={abrirRecife} carregando={carregandoLocais} />
        )}
        {pagina === 'detalhe' && recifeAtual && (
          <LocalRecifePage
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
