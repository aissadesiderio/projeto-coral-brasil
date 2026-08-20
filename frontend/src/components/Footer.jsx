import { Link } from 'react-router-dom';

import svgPaths from '../svg-r6f04ghq4r';
import { ROTAS_APP } from '../utils/navigation';

function InstagramIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path d={svgPaths.p3c382d72} fill="currentColor" fillOpacity="0.75" />
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
        fillOpacity="0.75"
        fillRule="evenodd"
      />
      <path d={svgPaths.pe7ea00} fill="#17414c" />
      <path d={svgPaths.p1ab31680} fill="#17414c" />
      <path d={svgPaths.p28c6df0} fill="#17414c" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
      <path d={svgPaths.pdaf0200} fill="currentColor" fillOpacity="0.75" />
    </svg>
  );
}

const LINK = 'block text-left text-[15px] text-white/60 transition hover:text-white';

/**
 * O rodapé do desenho 3a: chrome escuro fechando a página, e a linha de fontes
 * em mono.
 *
 * ⚠️ A linha de fontes não é assinatura — é a lista dos provedores de onde os
 * números da página vieram, no mesmo tipo em que os números aparecem. Ela fecha
 * a leitura como um rodapé de tabela fecha uma coluna.
 */
export default function Footer() {
  return (
    <footer className="bg-ocean-deep text-white">
      <div className="faixa flex flex-col gap-12 py-14 lg:flex-row lg:justify-between lg:py-16">
        <div>
          <h2 className="font-serif text-2xl font-medium tracking-[-0.015em]">
            Projeto Coral Brasil
          </h2>
          <p className="mt-3 max-w-xs text-[15px] leading-relaxed text-white/60">
            Monitoramento, biodiversidade e conservacao dos recifes brasileiros.
          </p>
          <div className="mt-8 flex items-center gap-6 text-white/70">
            <InstagramIcon />
            <LinkedinIcon />
            <XIcon />
          </div>
        </div>

        <div className="grid gap-10 sm:grid-cols-3 sm:gap-14">
          <div>
            <p className="rotulo-mono pb-4 text-white/45">Projeto</p>
            <div className="space-y-2">
              <Link to={ROTAS_APP.home} className={LINK}>
                Sobre
              </Link>
              <Link to={ROTAS_APP.recifes} className={LINK}>
                Banco de Especies
              </Link>
              <Link to={ROTAS_APP.recifes} className={LINK}>
                Monitoramento
              </Link>
            </div>
          </div>

          <div>
            <p className="rotulo-mono pb-4 text-white/45">Dados</p>
            <div className="space-y-2">
              <Link to={ROTAS_APP.banco} className={LINK}>
                NOAA
              </Link>
              <Link to={ROTAS_APP.banco} className={LINK}>
                Copernicus
              </Link>
              <Link to={ROTAS_APP.banco} className={LINK}>
                Metodologia
              </Link>
            </div>
          </div>

          <div>
            <p className="rotulo-mono pb-4 text-white/45">Contato</p>
            <div className="space-y-2 text-[15px] text-white/60">
              <p>GitHub</p>
              <p>Equipe</p>
              <Link to={ROTAS_APP.banco} className={LINK}>
                Relatorios
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-white/12">
        <div className="faixa flex flex-wrap items-center justify-between gap-3 py-6">
          <span className="font-serif text-[17px]">Projeto Coral Brasil</span>
          <span className="font-mono text-2xs tracking-[0.06em] text-white/55">
            NOAA CRW · Copernicus Marine · NCBI · IUCN
          </span>
        </div>
      </div>
    </footer>
  );
}
