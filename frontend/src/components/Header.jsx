import { Link } from 'react-router-dom';

import { obterItensNavegacao, ROTAS_APP } from '../utils/navigation';

const LINK_CLASSNAME =
  'rounded-full bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-ocean-dark sm:px-5';

function ContaWidget({ usuario, onLogout }) {
  if (!usuario?.autenticado) {
    return (
      <>
        <Link to={ROTAS_APP.login} className={LINK_CLASSNAME}>
          Entrar
        </Link>
        <Link to={ROTAS_APP.cadastro} className={LINK_CLASSNAME}>
          Cadastrar
        </Link>
      </>
    );
  }

  return (
    <>
      <Link to={ROTAS_APP.minhasEspecies} className={LINK_CLASSNAME}>
        Minhas especies
      </Link>
      <span className="px-1 text-sm text-white/80">
        {usuario.username}
        {usuario.master && ' (master)'}
      </span>
      <button type="button" onClick={onLogout} className={LINK_CLASSNAME}>
        Sair
      </button>
    </>
  );
}

function BrandMark({ claro = false }) {
  return (
    <div className={claro ? 'text-white' : 'text-ocean-dark'}>
      <span className="block text-brand-sm font-black leading-[0.88] tracking-tight sm:text-heading-sm">
        Projeto
      </span>
      <span className="block text-brand-sm font-black leading-[0.88] tracking-tight sm:text-heading-sm">
        Coral Brasil
      </span>
      <span
        className={`mt-1 block max-w-[14rem] text-micro font-semibold uppercase tracking-[0.2em] ${
          claro ? 'text-white/70' : 'text-ocean-dark/65'
        }`}
      >
        Monitoramento, biodiversidade e risco nos recifes brasileiros
      </span>
    </div>
  );
}

export default function Header({ paginaAtual, usuario, onLogout }) {
  const isHome = paginaAtual === 'home';
  const itensNavegacao = obterItensNavegacao(paginaAtual);

  return (
    <header
      className={
        isHome
          ? 'relative z-40 bg-ocean-dark text-white'
          : 'sticky top-0 z-40 border-b border-white/10 bg-ocean-dark/95 text-white shadow-md backdrop-blur'
      }
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <Link
          to="/"
          className="shrink-0 rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-ocean-dark"
          aria-label="Ir para a pagina inicial"
        >
          <BrandMark claro />
        </Link>

        <nav className="flex flex-wrap items-center gap-2 sm:gap-3 lg:justify-end">
          {itensNavegacao.map((item) => (
            <Link
              key={item.id}
              to={item.to}
              className="rounded-full bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-ocean-dark sm:px-5"
            >
              {item.rotulo}
            </Link>
          ))}
          <ContaWidget usuario={usuario} onLogout={onLogout} />
        </nav>
      </div>
    </header>
  );
}
