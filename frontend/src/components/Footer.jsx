import { Link } from 'react-router-dom';

import svgPaths from '../svg-r6f04ghq4r';
import { ROTAS_APP } from '../utils/navigation';

function InstagramIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path d={svgPaths.p3c382d72} fill="currentColor" fillOpacity="0.45" />
    </svg>
  );
}

function LinkedinIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path
        clipRule="evenodd"
        d={svgPaths.p1fcf5070}
        fill="currentColor"
        fillOpacity="0.45"
        fillRule="evenodd"
      />
      <path d={svgPaths.pe7ea00} fill="#fff" />
      <path d={svgPaths.p1ab31680} fill="#fff" />
      <path d={svgPaths.p28c6df0} fill="#fff" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path d={svgPaths.pdaf0200} fill="currentColor" fillOpacity="0.45" />
    </svg>
  );
}

export default function Footer() {
  return (
    <footer className="bg-[#ffefeb]">
      <div className="mx-auto flex max-w-7xl flex-col gap-12 border-t border-black/10 px-4 py-14 sm:px-6 lg:flex-row lg:justify-between lg:px-8 lg:py-16">
        <div>
          <h2 className="text-2xl font-semibold tracking-[-0.02em] text-black">
            Projeto Coral Brasil
          </h2>
          <p className="mt-3 max-w-xs text-base leading-[1.45] text-black/55">
            Monitoramento, biodiversidade e conservacao dos recifes brasileiros.
          </p>
          <div className="mt-8 flex items-center gap-6 text-black/45">
            <InstagramIcon />
            <LinkedinIcon />
            <XIcon />
          </div>
        </div>

        <div className="grid gap-10 sm:grid-cols-3 sm:gap-12">
          <div>
            <p className="pb-4 text-sm font-semibold tracking-[-0.01em] text-black">Projeto</p>
            <div className="space-y-2">
              <Link
                to={ROTAS_APP.home}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Sobre
              </Link>
              <Link
                to={ROTAS_APP.recifes}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Banco de Especies
              </Link>
              <Link
                to={ROTAS_APP.recifes}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Monitoramento
              </Link>
            </div>
          </div>

          <div>
            <p className="pb-4 text-sm font-semibold tracking-[-0.01em] text-black">Dados</p>
            <div className="space-y-2">
              <Link
                to={ROTAS_APP.banco}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                NOAA
              </Link>
              <Link
                to={ROTAS_APP.banco}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Copernicus
              </Link>
              <Link
                to={ROTAS_APP.banco}
                className="block text-left text-base text-black/55 transition hover:text-black"
              >
                Metodologia
              </Link>
            </div>
          </div>

          <div>
            <p className="pb-4 text-sm font-semibold tracking-[-0.01em] text-black">Contato</p>
            <div className="space-y-2 text-base text-black/55">
              <p>GitHub</p>
              <p>Equipe</p>
              <Link
                to={ROTAS_APP.banco}
                className="block text-left transition hover:text-black"
              >
                Relatorios
              </Link>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
