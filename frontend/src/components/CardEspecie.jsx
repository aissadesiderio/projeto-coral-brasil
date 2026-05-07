import { ExternalLink, Fish } from 'lucide-react';

import {
  resolverCreditoImagem,
  resolverLinkImagem,
  resolverRotuloLinkImagem,
} from '../utils/formatters';

export default function CardEspecie({ especie, onOpen }) {
  const linkImagem = resolverLinkImagem(especie);
  const rotuloLinkImagem = resolverRotuloLinkImagem(especie);
  const creditoImagem = resolverCreditoImagem(especie);

  return (
    <article className="overflow-hidden rounded-2xl border border-sand-dark/20 bg-white text-left shadow-sm transition hover:-translate-y-1 hover:shadow-md">
      <button type="button" onClick={() => onOpen(especie)} className="block w-full text-left">
        <div className="flex h-56 items-center justify-center overflow-hidden bg-sand-light">
          {especie.foto_url ? (
            <img
              src={especie.foto_url}
              alt={especie.nome_comum}
              className="h-full w-full object-cover"
            />
          ) : (
            <Fish size={64} className="text-ocean-light/50" />
          )}
        </div>
        <div className="p-5">
          <div className="mb-2 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h4 className="text-lg font-bold text-ocean-dark">
                {especie.nome_comum || 'Nome nao informado'}
              </h4>
              <p className="text-sm italic text-gray-500">{especie.nome_cientifico}</p>
            </div>
            <span className="rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-gray-700">
              {especie.tipo}
            </span>
          </div>

          <p className="line-clamp-3 text-sm text-gray-600">
            {especie.descricao || 'Sem descricao cadastrada para esta especie.'}
          </p>
        </div>
      </button>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-sand-dark/10 px-5 py-4 text-sm">
        <span className="text-gray-500">{creditoImagem || 'Sem credito de imagem'}</span>
        {linkImagem && (
          <a
            href={linkImagem}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 font-semibold text-ocean-dark hover:underline"
          >
            <ExternalLink size={14} />
            {rotuloLinkImagem}
          </a>
        )}
      </div>
    </article>
  );
}
