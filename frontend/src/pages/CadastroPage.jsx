import { useState } from 'react';
import { UserPlus } from 'lucide-react';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import SectionTitle from '../components/SectionTitle';
import { ROTAS_APP } from '../utils/navigation';

const CAMPO_CLASSNAME =
  'w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light';

export default function CadastroPage({ onCadastrar, usuario }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
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

    const resposta = await onCadastrar(username, email, senha);

    setEnviando(false);
    if (!resposta.ok) {
      setErro(resposta.dados?.detail || 'Nao foi possivel criar a conta.');
      return;
    }

    navigate(ROTAS_APP.minhasEspecies);
  }

  return (
    <section className="mx-auto flex w-full max-w-md flex-col gap-6 px-4 py-10 sm:px-6">
      <SectionTitle
        titulo="Criar conta"
        descricao="Cadastro aberto a qualquer visitante. Para contribuir especie ou baixar dados, um master precisa aprovar a conta depois."
      />

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
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">
            E-mail (opcional)
          </span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className={CAMPO_CLASSNAME}
            autoComplete="email"
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">Senha</span>
          <input
            type="password"
            value={senha}
            onChange={(event) => setSenha(event.target.value)}
            className={CAMPO_CLASSNAME}
            autoComplete="new-password"
            required
          />
        </label>

        <button
          type="submit"
          disabled={enviando}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-ocean-dark px-4 py-3 font-semibold text-white transition hover:bg-ocean-light disabled:opacity-60"
        >
          <UserPlus size={18} />
          {enviando ? 'Criando conta...' : 'Criar conta'}
        </button>

        <p className="text-center text-sm text-gray-600">
          Ja tem conta?{' '}
          <Link to={ROTAS_APP.login} className="font-semibold text-ocean-dark underline">
            Entrar
          </Link>
        </p>
      </form>
    </section>
  );
}
