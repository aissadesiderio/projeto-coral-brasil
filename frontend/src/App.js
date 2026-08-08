import React, { useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import Footer from './components/Footer';
import Header from './components/Header';
import ModalEspecie from './components/ModalEspecie';
import { FALLBACK_RECIFES } from './data/recifeData';
import BancoDadosPage from './pages/BancoDadosPage';
import CadastroPage from './pages/CadastroPage';
import GerenciarEspeciesPage from './pages/GerenciarEspeciesPage';
import HomePage from './pages/HomePage';
import LocalRecifeRoutePage from './pages/LocalRecifeRoutePage';
import LoginPage from './pages/LoginPage';
import RecifesPage from './pages/RecifesPage';
import { buscarJson, enviarFormulario } from './utils/api';
import { scrollToTopo } from './utils/formatters';
import { obterPaginaAtual, ROTAS_APP } from './utils/navigation';
import { combinarLocais } from './utils/recifes';

const USUARIO_DESLOGADO = { autenticado: false, username: null, master: false, aprovado: false };

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
  const [usuario, setUsuario] = useState(USUARIO_DESLOGADO);

  useEffect(() => {
    scrollToTopo();
    setEspecieSelecionada(null);
  }, [location.pathname]);

  useEffect(() => {
    let ativo = true;

    async function carregarBase() {
      const [statusPayload, locaisPayload, usuarioPayload] = await Promise.all([
        buscarJson('/api/status/'),
        buscarJson('/api/grafo/localizacoes/'),
        // Tambem funciona como "primer" do cookie csrftoken (ver EuView no
        // backend) — precisa rodar cedo, antes de qualquer escrita.
        buscarJson('/api/auth/eu/'),
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

      if (usuarioPayload) {
        setUsuario(usuarioPayload);
      }
    }

    carregarBase();

    return () => {
      ativo = false;
    };
  }, []);

  async function login(username, senha) {
    const resposta = await enviarFormulario('/api/auth/login/', {
      body: { username, password: senha },
    });
    if (resposta.ok) {
      setUsuario(resposta.dados);
    }
    return resposta;
  }

  async function cadastrar(username, email, senha) {
    const resposta = await enviarFormulario('/api/auth/cadastro/', {
      body: { username, email, password: senha },
    });
    if (resposta.ok) {
      setUsuario(resposta.dados);
    }
    return resposta;
  }

  async function logout() {
    await enviarFormulario('/api/auth/logout/', { method: 'POST' });
    setUsuario(USUARIO_DESLOGADO);
  }

  return (
    <div className="app-layout min-h-screen overflow-x-hidden bg-sand-light text-gray-800">
      <Header paginaAtual={paginaAtual} usuario={usuario} onLogout={logout} />

      <main className={`main-content flex-1 ${paginaAtual === 'recifes' ? 'bg-sand-lightest' : ''}`}>
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
                siteOffline={siteOffline}
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
                usuario={usuario}
              />
            }
          />
          <Route path={ROTAS_APP.login} element={<LoginPage onLogin={login} usuario={usuario} />} />
          <Route
            path={ROTAS_APP.cadastro}
            element={<CadastroPage onCadastrar={cadastrar} usuario={usuario} />}
          />
          <Route
            path={ROTAS_APP.minhasEspecies}
            element={<GerenciarEspeciesPage usuario={usuario} />}
          />
          <Route path="*" element={<Navigate to={ROTAS_APP.home} replace />} />
        </Routes>
      </main>

      <Footer />
      <ModalEspecie especie={especieSelecionada} onClose={() => setEspecieSelecionada(null)} />
    </div>
  );
}
