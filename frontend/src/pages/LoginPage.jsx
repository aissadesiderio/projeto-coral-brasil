import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import { ROTAS_APP } from '../utils/navigation';

/**
 * Entrar e criar conta na mesma tela — o painel escuro à direita não é
 * decoração.
 *
 * ⚠️ Ele existe para dizer, **antes** de o visitante tentar entrar, que o
 * cadastro é aberto mas a permissão não: baixar dado ou contribuir espécie
 * depende de um master aprovar depois. Sem essa frase visível ao lado do
 * formulário, quem cria a conta descobre a aprovação só ao esbarrar num 401.
 */
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
    <section className="faixa grid gap-7 py-14 lg:grid-cols-2">
      <div className="superficie p-8 sm:p-9">
        <h1 className="font-serif text-[32px] font-normal tracking-[-0.02em] text-ocean-deep sm:text-[36px]">
          Entrar
        </h1>
        <p className="mt-2.5 max-w-[44ch] text-[15px] leading-relaxed text-ocean-deep/65">
          Para contribuir com especie ou baixar dados.
        </p>

        <form onSubmit={enviar} className="mt-7 flex max-w-[400px] flex-col gap-6">
          {erro && (
            <p className="rounded-lg border-l-[3px] border-red-500 bg-red-50 p-3.5 text-sm text-red-800">
              {erro}
            </p>
          )}

          <label className="block">
            <span className="rotulo-mono mb-1.5 block text-ocean-deep/50">Usuario</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="campo-sublinhado"
              autoComplete="username"
              required
            />
          </label>

          <label className="block">
            <span className="rotulo-mono mb-1.5 block text-ocean-deep/50">Senha</span>
            <input
              type="password"
              value={senha}
              onChange={(event) => setSenha(event.target.value)}
              className="campo-sublinhado"
              autoComplete="current-password"
              required
            />
          </label>

          <button type="submit" disabled={enviando} className="botao-primario">
            {enviando ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>

      <div className="rounded-xl bg-ocean-deep p-8 text-white sm:p-9">
        <h2 className="font-serif text-[32px] font-normal tracking-[-0.02em] sm:text-[36px]">
          Ainda nao tem conta?
        </h2>
        <p className="mt-2.5 max-w-[46ch] text-[15px] leading-relaxed text-white/70">
          Cadastro aberto a qualquer visitante. Para contribuir com especie ou baixar dados, um
          master aprova a conta depois.
        </p>
        <Link
          to={ROTAS_APP.cadastro}
          className="mt-7 inline-flex w-fit items-center gap-2 rounded-lg bg-terra px-6 py-3 text-[15px] font-semibold text-white transition hover:brightness-110"
        >
          Cadastre-se →
        </Link>
      </div>
    </section>
  );
}
