import { MapPin } from 'lucide-react';

import CardRecife from '../components/CardRecife';

export default function RecifesPage({ locais, carregando = false, erroCarregamento = false }) {
  const possuiLocais = locais.length > 0;

  return (
    <section className="py-8 sm:py-10 lg:py-12">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl">
          <h2 className="text-4xl font-bold tracking-[-0.03em] text-[#2b6978] sm:text-[3.15rem]">
            Explorar Localizacoes
          </h2>
          <p className="mt-4 text-base leading-7 text-slate-600">
            Visualize as localizacoes monitoradas e abra cada pagina para consultar
            biodiversidade, risco atual e historico recente.
          </p>
          {carregando && (
            <p className="mt-3 text-sm text-slate-500">Carregando localizacoes do grafo...</p>
          )}
          {erroCarregamento && (
            <p className="mt-3 text-sm text-amber-700">
              Nao foi possivel atualizar todas as localizacoes agora. Exibindo os dados de
              referencia disponiveis.
            </p>
          )}
        </div>

        {possuiLocais ? (
          <div className="grid gap-x-6 gap-y-10 md:grid-cols-2 lg:grid-cols-3">
            {locais.map((local) => (
              <CardRecife key={local.slug} local={local} />
            ))}
          </div>
        ) : carregando ? (
          <div className="rounded-[32px] border border-dashed border-[#2b6978]/20 bg-white/80 px-6 py-10 text-center text-sm text-slate-500 shadow-sm">
            Buscando dados mais recentes dos recifes monitorados.
          </div>
        ) : (
          <div className="flex min-h-[320px] flex-col items-center justify-center rounded-[32px] border border-dashed border-[#2b6978]/20 bg-white/80 px-6 py-12 text-center shadow-sm">
            <div className="rounded-full bg-[#f4fbfc] p-4 text-[#2b6978]">
              <MapPin size={28} />
            </div>
            <h3 className="mt-5 text-2xl font-semibold text-[#194452]">
              Nenhuma localizacao disponivel no momento
            </h3>
            <p className="mt-3 max-w-xl text-base leading-7 text-slate-600">
              Assim que novas localizacoes forem carregadas, elas aparecerao aqui
              automaticamente com seus dados de risco, biodiversidade e atualizacao.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
