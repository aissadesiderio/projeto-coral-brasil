import { Link } from 'react-router-dom';

import { obterItensNavegacao } from '../utils/navigation';

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

export default function Header({ paginaAtual }) {
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
        <Link to="/" className="shrink-0 text-left" aria-label="Ir para a pagina inicial">
          <BrandMark claro />
        </Link>

        <nav className="flex flex-wrap items-center gap-2 sm:gap-3 lg:justify-end">
          {itensNavegacao.map((item) => (
            <Link
              key={item.id}
              to={item.to}
              className="rounded-full bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20 sm:px-5"
            >
              {item.rotulo}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
