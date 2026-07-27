import { ExternalLink, MapPin } from 'lucide-react';
import { Link } from 'react-router-dom';

import { obterQuantidadeEspeciesLocal } from '../utils/recifes';
import { formatarQuantidadeEspecies } from '../utils/formatters';
import { obterRotaLocalizacao } from '../utils/navigation';
import {
  classificarAlerta,
  formatarDataBr,
  formatarProbabilidade,
} from '../utils/painelRisco';
import ImagemRecife from './ImagemRecife';

/**
 * O selo passou a ser **binario**, e isso e consequencia do modelo.
 *
 * Antes eram quatro niveis herdados do `StatusPredicao` legado
 * (SEM_RISCO / OBSERVACAO / ALERTA_1 / ALERTA_2). O modelo atual nao produz
 * nivel: ele produz uma probabilidade e um **limiar declarado**, e disso sai
 * uma decisao de duas pontas. Inventar quatro faixas por cima de um corte
 * unico seria dar ao publico uma granularidade que a conta nao tem.
 */
function BadgeAlerta({ alerta }) {
  if (!alerta) {
    return (
      <span className="inline-flex w-fit items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
        Sem previsao
      </span>
    );
  }

  const classes = alerta.emAlerta
    ? 'border-orange-200 bg-orange-50 text-orange-700'
    : 'border-emerald-200 bg-emerald-50 text-emerald-700';

  return (
    <span
      className={`inline-flex w-fit items-center rounded-full border px-3 py-1 text-xs font-semibold ${classes}`}
    >
      {alerta.emAlerta ? 'Alerta termico' : 'Sem alerta'}
    </span>
  );
}

/**
 * `predicao` vem de `/api/painel-risco/`, e nao do objeto do local.
 *
 * ⚠️ Ate 27/07/2026 este cartao lia `risco_atual` do caminho legado — os 3
 * registros do `StatusPredicao`. Com o painel de detalhe ja no modelo novo,
 * manter aquele numero aqui daria **dois valores diferentes para o mesmo
 * recife**, cada um de um modelo, sem nada indicando qual vale.
 *
 * 🚨 A formatacao passa pelos mesmos helpers do painel de detalhe, e nao por
 * um `toFixed` local: e o que garante que a regra de nunca exibir "0%" nem
 * "100%" valha tambem aqui. Ver docs/RESULTADOS.md secao 22.8.
 */
export default function CardRecife({ local, predicao = null }) {
  const quantidadeEspecies = obterQuantidadeEspeciesLocal(local);
  const alerta = classificarAlerta(predicao);
  const probabilidade = formatarProbabilidade(predicao);
  const dataBase = predicao?.disponivel ? formatarDataBr(predicao.data_base) : null;

  return (
    <Link
      to={obterRotaLocalizacao(local.slug)}
      className="group flex h-full flex-col text-left transition duration-300 hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2b6978] focus-visible:ring-offset-4 focus-visible:ring-offset-[#fff6f4]"
    >
      <div className="overflow-hidden rounded-[22px] bg-white shadow-[0_18px_45px_rgba(43,105,120,0.12)]">
        <ImagemRecife
          nome={local.nome}
          imagem={local.imagem_url}
          className="h-56 w-full object-cover transition duration-500 group-hover:scale-[1.03]"
        />
      </div>

      <div className="flex flex-1 flex-col px-1 pb-1 pt-5">
        <h3 className="text-[1.6rem] font-bold leading-[1.15] tracking-[-0.025em] text-[#2b6978]">
          {local.nome}
        </h3>

        <p className="mt-5 inline-flex items-center gap-2 text-sm text-slate-500">
          <MapPin size={16} className="text-[#2b6978]" />
          {local.estado} - {local.cidade}
        </p>

        <div className="mt-5 space-y-1.5 text-sm leading-6 text-slate-700">
          <p>{formatarQuantidadeEspecies(quantidadeEspecies)}</p>
          <p>
            Estresse termico em 7 dias:{' '}
            <span className={`font-semibold ${alerta ? alerta.corTexto : 'text-slate-500'}`}>
              {probabilidade ? probabilidade.texto : 'Nao calculado'}
            </span>
          </p>
          <p>
            {dataBase
              ? `Calculado sobre dados ate ${dataBase}`
              : 'Sem previsao disponivel para esta localizacao'}
          </p>
        </div>

        <div className="mt-5 inline-flex items-center gap-3">
          <BadgeAlerta alerta={alerta} />
          <span className="inline-flex items-center gap-1 text-sm font-semibold text-[#2b6978]">
            Abrir
            <ExternalLink
              size={15}
              className="transition duration-300 group-hover:translate-x-0.5"
            />
          </span>
        </div>
      </div>
    </Link>
  );
}
