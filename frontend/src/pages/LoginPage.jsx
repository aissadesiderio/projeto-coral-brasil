import { useState } from 'react';
import { LogIn } from 'lucide-react';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import SectionTitle from '../components/SectionTitle';
import { ROTAS_APP } from '../utils/navigation';

const CAMPO_CLASSNAME =
  'w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light';

export default function LoginPage({ onLogin, usuario }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [enviando, setEnviando] = useState(false);

  if (usuario?.autenticado) {
    return <Navigate to={ROTAS_APP.minhasEspecies} replace />;
  }

  async function enviar(event) {
    event.preventDefault();
    setErro('');
    setEnviando(true);

    const resposta = await onLogin(username, senha);

    setEnviando(false);
    if (!resposta.ok) {
      setErro(resposta.dados?.detail || 'Nao foi possivel entrar. Confira usuario e senha.');
      return;
    }

    navigate(ROTAS_APP.minhasEspecies);
  }

  return (
    <section className="mx-auto flex w-full max-w-md flex-col gap-6 px-4 py-10 sm:px-6">
      <SectionTitle titulo="Entrar" descricao="Para contribuir espécie ou baixar dados." />

      <form
        onSubmit={enviar}
        className="flex flex-col gap-4 rounded-3xl border border-sand-dark/20 bg-white p-6 shadow-sm"
      >
        {erro && (
          <div className="rounded-2xl border border-red-300 bg-red-50 p-3 text-sm text-red-800">
            {erro}
          </div>
        )}

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">Usuario</span>
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className={CAMPO_CLASSNAME}
            autoComplete="username"
            required
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">Senha</span>
          <input
            type="password"
            value={senha}
            onChange={(event) => setSenha(event.target.value)}
            className={CAMPO_CLASSNAME}
            autoComplete="current-password"
            required
          />
        </label>

        <button
          type="submit"
          disabled={enviando}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-ocean-dark px-4 py-3 font-semibold text-white transition hover:bg-ocean-light disabled:opacity-60"
        >
          <LogIn size={18} />
          {enviando ? 'Entrando...' : 'Entrar'}
        </button>

        <p className="text-center text-sm text-gray-600">
          Ainda nao tem conta?{' '}
          <Link to={ROTAS_APP.cadastro} className="font-semibold text-ocean-dark underline">
            Cadastre-se
          </Link>
        </p>
      </form>
    </section>
  );
}
