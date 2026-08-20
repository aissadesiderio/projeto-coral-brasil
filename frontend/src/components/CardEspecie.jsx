import { ExternalLink, Fish } from 'lucide-react';

import {
  resolverCreditoImagem,
  resolverLinkImagem,
  resolverRotuloLinkImagem,
} from '../utils/formatters';

/**
 * O cartão de espécie do desenho 3a.
 *
 * 🚨 **O crédito fica sobre a foto, e não num rodapé.** Nenhuma imagem de
 * espécie deste acervo é do projeto: todas vêm de terceiros, e a correção de
 * 11/08/2026 (docs/FONTES.md §2.1) tirou do banco nove créditos que afirmavam
 * "Acervo local do projeto" sobre fotos alheias. Um crédito em linha de rodapé
 * se separa da imagem no primeiro print, no primeiro slide, na primeira
 * captura de tela — e a foto passa a circular sem procedência. Na faixa, ele
 * viaja junto.
 *
 * ⚠️ Sem crédito, a faixa **diz que falta**, em vez de sumir. Uma foto sem
 * faixa nenhuma se lê como foto do projeto, que é exatamente o erro que a
 * migração 0026 desfez no banco.
 */
export default function CardEspecie({ especie, onOpen }) {
  const linkImagem = resolverLinkImagem(especie);
  const rotuloLinkImagem = resolverRotuloLinkImagem(especie);
  const creditoImagem = resolverCreditoImagem(especie);

  return (
    <article className="flex h-full flex-col">
      <button
        type="button"
        onClick={() => onOpen(especie)}
        className="block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-deep focus-visible:ring-offset-4 focus-visible:ring-offset-sand-lightest"
      >
        <div className="relative aspect-[3/2] overflow-hidden rounded-xl bg-sand-light">
          {especie.foto_url ? (
            <img
              src={especie.foto_url}
              alt={especie.nome_comum}
              loading="lazy"
              className="h-full w-full object-cover"
            />
          ) : (
            <span className="flex h-full w-full items-center justify-center">
              <Fish size={56} className="text-ocean-light" />
            </span>
          )}

          {especie.foto_url && (
            <span className="absolute inset-x-0 bottom-0 block bg-ocean-deep/75 px-3 py-1.5 font-mono text-3xs tracking-[0.06em] text-white/90">
              {creditoImagem || 'sem credito informado'}
            </span>
          )}
        </div>

        <div className="pt-4">
          <span className="olho-terra">{especie.tipo}</span>
          <h4 className="mt-1.5 font-serif text-[22px] font-normal text-ocean-deep">
            {especie.nome_comum || 'Nome nao informado'}
          </h4>
          <p className="mt-0.5 text-sm italic text-ocean-deep/60">{especie.nome_cientifico}</p>
          <p className="mt-2 line-clamp-3 text-[13px] leading-relaxed text-ocean-deep/60">
            {especie.descricao || 'Sem descricao cadastrada para esta especie.'}
          </p>
        </div>
      </button>

      {linkImagem && (
        <a
          href={linkImagem}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex w-fit items-center gap-1.5 text-2xs font-semibold text-ocean-dark transition hover:text-ocean-deep"
        >
          <ExternalLink size={13} />
          {rotuloLinkImagem}
        </a>
      )}
    </article>
  );
}
