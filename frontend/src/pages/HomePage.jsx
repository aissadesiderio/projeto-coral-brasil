import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import RailLatitude from '../components/RailLatitude';
import TabelaLocalizacoes from '../components/TabelaLocalizacoes';
import { HOME_DESTAQUES, HOME_HERO_IMAGE } from '../data/datasets';
import { buscarPredicoes, formatarDataBr } from '../utils/painelRisco';
import { obterRotaPorPagina } from '../utils/navigation';
import { ordenarLocais } from '../utils/recifes';
import { useResumoDhw } from '../utils/serieResumo';

const NOTA_MONITOR =
  'A linha vermelha nas curvas e o Alerta Nivel 1 da NOAA (DHW 4). O numero e a '
  + 'probabilidade de estresse termico em 7 dias, nao de branqueamento observado, e a '
  + 'plataforma nao escreve 0% nem 100%.';

/**
 * Os quatro KPIs da faixa escura.
 *
 * 🚨 **Nenhum deles é inventado, e nenhum deles é constante escrita à mão.**
 * Todos saem do que a página já carregou — locais do grafo e predições do
 * modelo. Um KPI cravado no código é a forma mais discreta de a home mentir:
 * ele continua bonito e correto por meses depois de ter deixado de ser
 * verdade, porque nada o recalcula.
 *
 * ⚠️ Quando o dado falta, o cartão diz `--`. A alternativa — esconder o KPI —
 * faria a faixa parecer completa com três números em vez de quatro.
 */
function montarKpis(locais, predicoes, dataBase) {
  const comSerie = locais.filter((local) => !local.motivo_sem_serie);
  const previstos = Object.values(predicoes).filter((item) => item?.disponivel === true);
  const emAlerta = previstos.filter((item) => item.alerta === true).length;
  const especies = locais.reduce(
    (soma, local) => soma + (local.quantidade_especies || local.informacoes_disponiveis || 0),
    0,
  );

  return [
    {
      rotulo: 'localizacoes no catalogo',
      valor: locais.length > 0 ? String(locais.length) : '--',
      nota: `${comSerie.length} com serie de satelite ingerida`,
      cor: 'text-white',
    },
    {
      rotulo: 'com previsao hoje',
      valor: previstos.length > 0 ? String(previstos.length) : '--',
      nota: 'a janela de 7 dias fechou nestas',
      cor: 'text-white',
    },
    {
      rotulo: 'em degrau de alerta',
      valor: previstos.length > 0 ? String(emAlerta) : '--',
      nota: 'acima do limiar declarado pelo servidor',
      cor: emAlerta > 0 ? 'text-terra' : 'text-white',
    },
    {
      rotulo: 'dados ate',
      valor: dataBase || '--',
      nota: especies > 0 ? `${especies} especies associadas` : 'serie do satelite',
      cor: 'text-white',
    },
  ];
}

export default function HomePage({
  siteOffline,
  offlineMessage,
  locais = [],
  carregandoLocais = false,
}) {
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

  // A data-base é a mesma para toda a costa (uma rodada do modelo), mas quem a
  // afirma é o servidor, um registro por vez. Pegar a mais recente entre as
  // respostas evita cravar aqui uma data que o modelo não confirmou.
  const dataBase = Object.values(predicoes)
    .map((item) => item?.data_base)
    .filter(Boolean)
    .sort()
    .pop();

  const kpis = montarKpis(locais, predicoes, formatarDataBr(dataBase));

  return (
    <>
      <section className="faixa grid items-center gap-10 pb-2 pt-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-12 lg:pt-14">
        <div>
          {siteOffline && (
            <div className="mb-8 rounded-lg border-l-[3px] border-terra bg-sand-aviso p-4 text-sm leading-relaxed text-ocean-deep/80">
              <strong className="text-terra-dark">Modo manutencao:</strong>{' '}
              {offlineMessage || 'Exibindo dados locais de referencia durante a reestruturacao.'}
            </div>
          )}

          <span className="olho-terra">
            Monitoramento continuo
            {locais.length > 0 && ` · ${locais.length} localizacoes`}
          </span>
          <h1 className="mt-4 font-serif text-[42px] font-normal leading-[1.03] tracking-[-0.025em] text-ocean-deep sm:text-[52px] lg:text-[58px]">
            Os recifes brasileiros, medidos dia a dia.
          </h1>
          <p className="mt-5 max-w-[48ch] text-[17px] leading-relaxed text-ocean-deep/70">
            Temperatura de satelite, calor acumulado e biodiversidade das localizacoes
            monitoradas — com a proveniencia de cada valor e a data sobre a qual cada conta
            foi feita.
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link to={obterRotaPorPagina('recifes')} className="botao-primario">
              Abrir o monitor
            </Link>
            <Link to={obterRotaPorPagina('banco')} className="botao-secundario">
              Baixar dados
            </Link>
          </div>
        </div>

        <div className="flex flex-col items-center">
          <img
            src={HOME_HERO_IMAGE}
            alt="Mussismilia braziliensis"
            width={1920}
            height={1080}
            fetchPriority="high"
            className="w-full max-w-[500px] object-contain drop-shadow-[0_26px_40px_rgba(19,74,87,0.22)]"
          />
          <p className="mt-2 w-full text-right font-mono text-3xs text-ocean-deep/45">
            Mussismilia braziliensis · acervo do projeto
          </p>
        </div>
      </section>

      {/* A faixa escura: os números vivem no chrome, o texto vive na areia. É a
          separação que dá ao 3a o "instrumento dentro do editorial". */}
      <section className="mt-10 bg-ocean-deep text-white">
        <div className="faixa py-11">
          <div className="grid gap-px border border-white/15 bg-white/15 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((kpi) => (
              <div key={kpi.rotulo} className="bg-ocean-deep px-5 py-4">
                <p className="rotulo-mono text-white/45">{kpi.rotulo}</p>
                <p
                  className={`mt-2.5 font-mono text-[30px] font-medium leading-none tracking-[-0.02em] ${kpi.cor}`}
                >
                  {kpi.valor}
                </p>
                <p className="mt-1.5 text-2xs text-white/50">{kpi.nota}</p>
              </div>
            ))}
          </div>

          <div className="mt-10 flex flex-wrap items-end justify-between gap-x-6 gap-y-2 border-b border-white/18 pb-4">
            <h2 className="font-serif text-[30px] font-normal tracking-[-0.02em] sm:text-[34px]">
              Estado da costa hoje
            </h2>
            <span className="font-mono text-2xs text-white/60">
              probabilidade calibrada
              {formatarDataBr(dataBase) && ` · dados ate ${formatarDataBr(dataBase)}`}
            </span>
          </div>

          <div className="grid gap-9 pt-7 lg:grid-cols-[220px_minmax(0,1fr)]">
            <div className="hidden lg:block">
              <RailLatitude
                locais={locais}
                predicoes={predicoes}
                altura={300}
                titulo="Latitude"
              />
            </div>

            <div>
              {carregandoLocais && locais.length === 0 ? (
                <p className="py-10 text-center text-sm text-white/60">
                  Carregando as localizacoes monitoradas...
                </p>
              ) : (
                <TabelaLocalizacoes
                  // ⚠️ Mesma ordem da régua ao lado, e não a ordem em que a API
                  // devolveu: duas listas dos mesmos recifes em sequências
                  // diferentes na mesma tela tirariam da régua a única função
                  // que ela tem, que é servir de índice da tabela.
                  locais={ordenarLocais(locais)}
                  predicoes={predicoes}
                  pontosDhwPorSlug={pontosDhwPorSlug}
                  variante="monitor"
                  nota={NOTA_MONITOR}
                />
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="faixa grid gap-8 py-14 md:grid-cols-3">
        {HOME_DESTAQUES.map((item) => (
          <Link key={item.id} to={obterRotaPorPagina(item.pagina)} className="group block">
            <div className="aspect-[4/3] overflow-hidden rounded-xl">
              <img
                src={item.imagem}
                alt={item.titulo}
                loading="lazy"
                decoding="async"
                className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
              />
            </div>
            <span className="olho-terra mt-4 block">{item.olho}</span>
            <h2 className="mt-1.5 font-serif text-[25px] font-normal tracking-[-0.015em] text-ocean-deep">
              {item.titulo}
            </h2>
            <p className="mt-1.5 text-[14.5px] leading-relaxed text-ocean-deep/65">
              {item.descricao}
            </p>
          </Link>
        ))}
      </section>
    </>
  );
}
