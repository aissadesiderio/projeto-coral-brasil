import { Link } from 'react-router-dom';

import { obterItensNavegacao, ROTAS_APP } from '../utils/navigation';

const FOCO =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-ocean-deep';

// O botão claro sobre o chrome escuro. É o único elemento da barra com fundo:
// tudo o mais é texto, e por isso a ação de conta se destaca sem precisar de
// cor de alerta.
const CHIP = `rounded-md bg-ocean-light px-3.5 py-1.5 text-[13px] font-semibold text-ocean-deep transition hover:bg-white ${FOCO}`;
const CHIP_FANTASMA = `rounded-md px-3.5 py-1.5 text-[13px] font-semibold text-white/75 transition hover:text-white ${FOCO}`;

function ContaWidget({ usuario, onLogout }) {
  if (!usuario?.autenticado) {
    return (
      <>
        <Link to={ROTAS_APP.cadastro} className={CHIP_FANTASMA}>
          Cadastrar
        </Link>
        <Link to={ROTAS_APP.login} className={CHIP}>
          Entrar
        </Link>
      </>
    );
  }

  return (
    <>
      <span className="font-mono text-2xs text-white/50">
        {usuario.username}
        {usuario.master && ' (master)'}
      </span>
      <Link to={ROTAS_APP.minhasEspecies} className={CHIP}>
        Minhas especies
      </Link>
      <button type="button" onClick={onLogout} className={CHIP_FANTASMA}>
        Sair
      </button>
    </>
  );
}

/**
 * A barra de chrome do desenho 3a.
 *
 * ⚠️ O filete claro à esquerda do nome não é ornamento: é o que dá ao logotipo
 * a mesma altura de um rótulo de coluna, para que a marca não compita com o
 * título editorial da página logo abaixo. O item ativo da navegação leva o
 * filete terra — a mesma cor que marca "olho" e acento no resto do site.
 */
export default function Header({ paginaAtual, usuario, onLogout }) {
  const isHome = paginaAtual === 'home';
  const itensNavegacao = obterItensNavegacao(paginaAtual);

  return (
    <header
      className={
        isHome
          ? 'relative z-40 bg-ocean-deep text-white'
          : 'sticky top-0 z-40 bg-ocean-deep text-white shadow-md'
      }
    >
      <div className="faixa flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-3.5">
        <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
          <Link
            to={ROTAS_APP.home}
            className={`flex shrink-0 items-center gap-3 rounded-sm ${FOCO}`}
            aria-label="Ir para a pagina inicial"
          >
            <span aria-hidden="true" className="block h-[22px] w-2 rounded-sm bg-ocean-light" />
            <span className="font-serif text-xl font-medium tracking-[-0.015em]">
              Projeto Coral Brasil
            </span>
          </Link>

          <nav className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[13.5px] font-medium">
            {itensNavegacao.map((item) => (
              <Link
                key={item.id}
                to={item.to}
                aria-current={item.ativo ? 'page' : undefined}
                className={`rounded-sm pb-0.5 transition ${FOCO} ${
                  item.ativo
                    ? 'border-b-2 border-terra text-white'
                    : 'border-b-2 border-transparent text-white/65 hover:text-white'
                }`}
              >
                {item.rotulo}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          <ContaWidget usuario={usuario} onLogout={onLogout} />
        </div>
      </div>
    </header>
  );
}
