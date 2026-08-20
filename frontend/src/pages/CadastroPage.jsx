import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import { ROTAS_APP } from '../utils/navigation';

/**
 * Criar conta, no painel escuro — o espelho de `LoginPage`.
 *
 * ⚠️ A frase sobre aprovação vem **antes** do formulário, e não como aviso
 * depois do envio: cadastro aberto e permissão aprovada são duas coisas, e o
 * visitante tem direito a saber disso antes de digitar a senha.
 */
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
    <section className="faixa grid gap-7 py-14 lg:grid-cols-2">
      <div className="rounded-xl bg-ocean-deep p-8 text-white sm:p-9">
        <h1 className="font-serif text-[32px] font-normal tracking-[-0.02em] sm:text-[36px]">
          Criar conta
        </h1>
        <p className="mt-2.5 max-w-[46ch] text-[15px] leading-relaxed text-white/70">
          Cadastro aberto a qualquer visitante. Para contribuir com especie ou baixar dados, um
          master aprova a conta depois.
        </p>

        <form onSubmit={enviar} className="mt-7 flex max-w-[400px] flex-col gap-6">
          {erro && (
            <p className="rounded-lg border-l-[3px] border-terra bg-white/10 p-3.5 text-sm text-white">
              {erro}
            </p>
          )}

          <label className="block">
            <span className="rotulo-mono mb-1.5 block text-white/55">Usuario</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="campo-sublinhado-claro"
              autoComplete="username"
              required
            />
          </label>

          <label className="block">
            <span className="rotulo-mono mb-1.5 block text-white/55">E-mail (opcional)</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="campo-sublinhado-claro"
              autoComplete="email"
            />
          </label>

          <label className="block">
            <span className="rotulo-mono mb-1.5 block text-white/55">Senha</span>
            <input
              type="password"
              value={senha}
              onChange={(event) => setSenha(event.target.value)}
              className="campo-sublinhado-claro"
              autoComplete="new-password"
              required
            />
          </label>

          <button
            type="submit"
            disabled={enviando}
            className="inline-flex w-fit items-center justify-center rounded-lg bg-terra px-6 py-3 text-[15px] font-semibold text-white transition hover:brightness-110 disabled:opacity-60"
          >
            {enviando ? 'Criando conta...' : 'Criar conta'}
          </button>
        </form>
      </div>

      <div className="superficie p-8 sm:p-9">
        <h2 className="font-serif text-[32px] font-normal tracking-[-0.02em] text-ocean-deep sm:text-[36px]">
          Ja tem conta?
        </h2>
        <p className="mt-2.5 max-w-[44ch] text-[15px] leading-relaxed text-ocean-deep/65">
          Entre para contribuir com especie ou baixar dados.
        </p>
        <Link to={ROTAS_APP.login} className="botao-primario mt-7">
          Entrar →
        </Link>
      </div>
    </section>
  );
}
