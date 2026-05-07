import { ExternalLink, MapPin } from 'lucide-react';
import { Link } from 'react-router-dom';

import {
  obterMetaRisco,
  obterNivelAlertaLocal,
  obterMonitoramentoLocal,
  obterQuantidadeEspeciesLocal,
  obterValorRiscoAtualLocal,
} from '../utils/recifes';
import { formatarData, formatarQuantidadeEspecies } from '../utils/formatters';
import { obterRotaLocalizacao } from '../utils/navigation';
import ImagemRecife from './ImagemRecife';

function BadgeRisco({ nivelAlerta }) {
  const meta = obterMetaRisco(nivelAlerta);

  return (
    <span
      className={`inline-flex w-fit items-center rounded-full border px-3 py-1 text-xs font-semibold ${meta.bordaClasse} ${meta.fundoClasse} ${meta.textoClasse}`}
    >
      {meta.textoCurto}
    </span>
  );
}

export default function CardRecife({ local }) {
  const quantidadeEspecies = obterQuantidadeEspeciesLocal(local);
  const nivelAlerta = obterNivelAlertaLocal(local);
  const riscoAtual = obterValorRiscoAtualLocal(local);
  const metaRisco = obterMetaRisco(nivelAlerta);
  const ultimaAtualizacao = local.ultima_atualizacao || obterMonitoramentoLocal(local)?.data || null;

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
            Risco atual:{' '}
            <span className={`font-semibold ${metaRisco.textoClasse}`}>
              {riscoAtual !== null ? `${riscoAtual.toFixed(1)}%` : 'Nao informado'}
            </span>
          </p>
          <p>Ultima atualizacao: {formatarData(ultimaAtualizacao)}</p>
        </div>

        <div className="mt-5 inline-flex items-center gap-3">
          <BadgeRisco nivelAlerta={nivelAlerta} />
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
