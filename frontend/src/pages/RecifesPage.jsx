import { useEffect, useMemo, useState } from 'react';
import { MapPin } from 'lucide-react';

import RailLatitude from '../components/RailLatitude';
import TabelaLocalizacoes from '../components/TabelaLocalizacoes';
import { buscarPredicoes } from '../utils/painelRisco';
import { ordenarLocais } from '../utils/recifes';
import { useResumoDhw } from '../utils/serieResumo';

// As três ordens que o visitante pode pedir. A regra de cada uma vive em
// `utils/recifes.ordenarLocais`, junto da explicação de por que latitude é o
// padrão.
const ORDENS = [
  { id: 'latitude', rotulo: 'latitude' },
  { id: 'risco', rotulo: 'risco' },
  { id: 'especies', rotulo: 'especies' },
];

const NOTA_CATALOGO =
  'Cinza e ausencia de dado, nao risco baixo. Uma localizacao sem serie ingerida aparece '
  + 'no catalogo pela latitude publicada e nada mais.';

export default function RecifesPage({
  locais,
  carregando = false,
  erroCarregamento = false,
  siteOffline = false,
}) {
  const possuiLocais = locais.length > 0;
  const [ordem, setOrdem] = useState('latitude');

  // Uma requisicao para a lista inteira, e nao uma por linha: o endpoint ja
  // devolve os recifes de uma vez, e chamar por linha multiplicaria leituras do
  // mesmo artefato sem nenhum ganho.
  const [predicoes, setPredicoes] = useState({});

  useEffect(() => {
    if (siteOffline) {
      return undefined;
    }

    let ativo = true;
    buscarPredicoes().then((resposta) => {
      if (ativo) {
        setPredicoes(resposta.porLocal || {});
      }
    });

    return () => {
      ativo = false;
    };
  }, [siteOffline]);

  const pontosDhwPorSlug = useResumoDhw(locais, { ativo: !siteOffline });
  const ordenados = useMemo(
    () => ordenarLocais(locais, ordem, predicoes),
    [locais, ordem, predicoes],
  );
  const comSerie = locais.filter((local) => !local.motivo_sem_serie).length;

  return (
    <section className="faixa py-12">
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div>
          <span className="olho-terra">
            Catalogo da costa
            {possuiLocais && ` · ${locais.length} localizacoes`}
          </span>
          <h1 className="mt-3.5 font-serif text-[36px] font-normal leading-[1.05] tracking-[-0.025em] text-ocean-deep sm:text-[44px]">
            Localizacoes monitoradas
          </h1>
          <p className="mt-3 max-w-[68ch] text-base leading-relaxed text-ocean-deep/70">
            Ordenadas por latitude, de norte a sul. {comSerie} tem serie de satelite ingerida;
            as demais entram no catalogo sem numero, porque ainda nao ha dado ingerido para
            elas.
          </p>
          {carregando && (
            <p className="mt-3 font-mono text-2xs text-ocean-deep/50">
              Carregando localizacoes do grafo...
            </p>
          )}
          {erroCarregamento && (
            <p className="mt-3 text-sm text-terra-dark">
              Nao foi possivel atualizar todas as localizacoes agora. Exibindo os dados de
              referencia disponiveis.
            </p>
          )}
        </div>

        <div className="flex shrink-0 gap-1.5">
          {ORDENS.map((opcao) => (
            <button
              key={opcao.id}
              type="button"
              onClick={() => setOrdem(opcao.id)}
              aria-pressed={ordem === opcao.id}
              className={`rounded-md px-3 py-1.5 font-mono text-2xs transition ${
                ordem === opcao.id
                  ? 'bg-ocean-deep text-white'
                  : 'border border-ocean-deep/18 text-ocean-deep/60 hover:border-ocean-deep/40'
              }`}
            >
              {opcao.rotulo}
            </button>
          ))}
        </div>
      </div>

      {possuiLocais ? (
        <div className="mt-8 grid items-start gap-7 lg:grid-cols-[270px_minmax(0,1fr)]">
          <div className="hidden lg:block">
            <RailLatitude locais={locais} predicoes={predicoes} altura={420} />
          </div>

          <TabelaLocalizacoes
            locais={ordenados}
            predicoes={predicoes}
            pontosDhwPorSlug={pontosDhwPorSlug}
            variante="catalogo"
            nota={NOTA_CATALOGO}
          />
        </div>
      ) : carregando ? (
        <div className="superficie mt-8 px-6 py-12 text-center text-sm text-ocean-deep/55">
          Buscando dados mais recentes dos recifes monitorados.
        </div>
      ) : (
        <div className="superficie mt-8 flex min-h-[320px] flex-col items-center justify-center px-6 py-12 text-center">
          <div className="rounded-full bg-sand-light p-4 text-ocean-deep">
            <MapPin size={28} />
          </div>
          <h2 className="mt-5 font-serif text-[26px] font-normal text-ocean-deep">
            Nenhuma localizacao disponivel no momento
          </h2>
          <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-ocean-deep/65">
            Assim que novas localizacoes forem carregadas, elas aparecerao aqui
            automaticamente com seus dados de risco, biodiversidade e atualizacao.
          </p>
        </div>
      )}
    </section>
  );
}
