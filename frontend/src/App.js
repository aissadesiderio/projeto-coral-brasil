import React, { useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import Footer from './components/Footer';
import Header from './components/Header';
import ModalEspecie from './components/ModalEspecie';
import { FALLBACK_RECIFES } from './data/recifeData';
import BancoDadosPage from './pages/BancoDadosPage';
import HomePage from './pages/HomePage';
import LocalRecifeRoutePage from './pages/LocalRecifeRoutePage';
import RecifesPage from './pages/RecifesPage';
import { buscarJson } from './utils/api';
import { scrollToTopo } from './utils/formatters';
import { obterPaginaAtual, ROTAS_APP } from './utils/navigation';
import { combinarLocais } from './utils/recifes';

export default function App() {
  const location = useLocation();
  const paginaAtual = useMemo(() => obterPaginaAtual(location.pathname), [location.pathname]);
  const [locais, setLocais] = useState([]);
  const [detalhesPorSlug, setDetalhesPorSlug] = useState({});
  const [especieSelecionada, setEspecieSelecionada] = useState(null);
  const [siteOffline, setSiteOffline] = useState(false);
  const [offlineMessage, setOfflineMessage] = useState('');
  const [carregandoLocais, setCarregandoLocais] = useState(true);
  const [erroCarregamentoLocais, setErroCarregamentoLocais] = useState(false);

  useEffect(() => {
    scrollToTopo();
    setEspecieSelecionada(null);
  }, [location.pathname]);

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
      setErroCarregamentoLocais(locaisNormalizados.length === 0);
      setLocais(locaisNormalizados.length > 0 ? locaisNormalizados : FALLBACK_RECIFES);
      setCarregandoLocais(false);
    }

    carregarBase();

    return () => {
      ativo = false;
    };
  }, []);

  return (
    <div className="app-layout min-h-screen overflow-x-hidden bg-sand-light text-gray-800">
      <Header paginaAtual={paginaAtual} />

      <main className={`main-content flex-1 ${paginaAtual === 'recifes' ? 'bg-[#fff6f4]' : ''}`}>
        {siteOffline && paginaAtual !== 'home' && (
          <div className="mx-auto max-w-7xl px-4 pt-6 sm:px-6 lg:px-8">
            <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
              <strong>Modo manutencao:</strong>{' '}
              {offlineMessage ||
                'Site em manutencao para reestruturacao do backend e banco de dados.'}
            </div>
          </div>
        )}

        <Routes>
          <Route
            path={ROTAS_APP.home}
            element={<HomePage siteOffline={siteOffline} offlineMessage={offlineMessage} />}
          />
          <Route path={ROTAS_APP.banco} element={<BancoDadosPage />} />
          <Route
            path={ROTAS_APP.recifes}
            element={
              <RecifesPage
                locais={locais}
                carregando={carregandoLocais}
                erroCarregamento={erroCarregamentoLocais}
              />
            }
          />
          <Route
            path={`${ROTAS_APP.recifes}/:slug`}
            element={
              <LocalRecifeRoutePage
                locais={locais}
                carregandoLocais={carregandoLocais}
                detalhesPorSlug={detalhesPorSlug}
                setDetalhesPorSlug={setDetalhesPorSlug}
                siteOffline={siteOffline}
                offlineMessage={offlineMessage}
                onOpenEspecie={setEspecieSelecionada}
              />
            }
          />
          <Route path="*" element={<Navigate to={ROTAS_APP.home} replace />} />
        </Routes>
      </main>

      <Footer />
      <ModalEspecie especie={especieSelecionada} onClose={() => setEspecieSelecionada(null)} />
    </div>
  );
}
