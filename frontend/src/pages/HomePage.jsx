import { Link } from 'react-router-dom';

import { HOME_DESTAQUES, HOME_HERO_IMAGE } from '../data/datasets';
import { obterRotaPorPagina } from '../utils/navigation';

export default function HomePage({ siteOffline, offlineMessage }) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-ocean-dark via-[#b0d7d4] via-[40%] to-sand-lightest">
      <div className="absolute left-1/2 top-0 h-72 w-72 -translate-x-1/2 rounded-full bg-white/10 blur-3xl" />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 pb-20 pt-4 sm:px-6 sm:pb-24 lg:px-8">
        {siteOffline && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/95 p-4 text-sm text-amber-950 shadow-sm backdrop-blur">
            <strong>Modo manutencao:</strong>{' '}
            {offlineMessage || 'Exibindo dados locais de referencia durante a reestruturacao.'}
          </div>
        )}

        <div className="flex justify-center pt-4 sm:pt-8">
          <img
            src={HOME_HERO_IMAGE}
            alt="Coral em destaque na pagina inicial"
            width={1920}
            height={1080}
            fetchPriority="high"
            className="w-full max-w-[980px] object-contain drop-shadow-[0_32px_48px_rgba(19,74,87,0.18)]"
          />
        </div>

        <div className="max-w-3xl pb-4 sm:pb-10">
          <h1 className="text-heading-sm font-bold leading-[1.15] tracking-[-0.02em] text-ocean-dark sm:text-heading lg:text-heading-lg">
            Mergulhe na biodiversidade coralina brasileira.
          </h1>
          <p className="mt-4 max-w-2xl text-base font-medium leading-[1.55] text-black/60 sm:text-lg">
            Esta plataforma centraliza dados ambientais, referencias complementares e
            acompanhamento de risco para apoiar pesquisa, gestao e observacao de recifes.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              to={obterRotaPorPagina('recifes')}
              className="rounded-[10px] bg-ocean-dark px-5 py-3 text-sm font-medium text-white transition hover:brightness-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-dark focus-visible:ring-offset-2 focus-visible:ring-offset-sand-lightest sm:w-auto"
            >
              Explorar recifes
            </Link>
            <Link
              to={obterRotaPorPagina('banco')}
              className="rounded-[10px] border border-ocean-dark/20 bg-white/70 px-5 py-3 text-sm font-medium text-ocean-dark transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-dark focus-visible:ring-offset-2 focus-visible:ring-offset-sand-lightest"
            >
              Banco de dados geral
            </Link>
          </div>
        </div>

        <ul className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {HOME_DESTAQUES.map((item) => (
            <li key={item.id}>
              <Link to={obterRotaPorPagina(item.pagina)} className="group block w-full text-left">
                <div className="relative aspect-[362.66/483] overflow-hidden rounded-2xl shadow-lg shadow-ocean-dark/10">
                  <img
                    src={item.imagem}
                    alt={item.titulo}
                    loading="lazy"
                    decoding="async"
                    className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
                  />
                </div>

                <div className="pt-6">
                  <h2 className="text-2xl font-semibold leading-[1.2] tracking-[-0.02em] text-ocean-dark">
                    {item.titulo}
                  </h2>
                  <p className="mt-2 text-base leading-[1.55] text-black/60 sm:text-lg">
                    {item.descricao}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
