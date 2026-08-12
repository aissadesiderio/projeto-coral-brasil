import { ExternalLink, Fish, Info } from 'lucide-react';

import {
  resolverCreditoImagem,
  resolverLinkImagem,
  resolverRotuloLinkImagem,
} from '../utils/formatters';

/**
 * A categoria de conservacao — exibida **so quando pode ser datada**.
 *
 * 🚨 **Ate 31/07/2026 esta linha era `status_conservacao || 'Nao avaliado'`.**
 * Dois defeitos num `||`:
 *
 * 1. **Categoria sem ano se apresentava como fato.** Uma categoria da IUCN tem
 *    prazo de validade invisivel: `Dendrogyra cylindrus`, que esta neste
 *    acervo, foi *Vulneravel* de 2008 a 2022 e hoje e *Criticamente Ameacada*.
 *    Sem o ano, a tela nao distingue "e CR" de "era VU quando alguem digitou".
 * 2. **Campo vazio virava "Nao avaliado"**, que e uma **categoria real** da
 *    Lista Vermelha (NE). Ou seja: *"nao sabemos"* e *"a IUCN avaliou e o
 *    resultado foi NE"* saiam identicos na tela, e o leitor nao tinha como
 *    saber qual dos dois estava lendo.
 *
 * A regra agora: **sem `iucn_tem_procedencia`, nao se exibe categoria.** E o
 * mesmo principio que o resto do projeto ja segue — valor reprovado vira nulo
 * com motivo, nunca zero. Aqui, afirmacao sem data vira a frase que diz que
 * ela falta.
 */
function Conservacao({ especie }) {
  if (especie.iucn_tem_procedencia !== true) {
    return (
      <p className="text-slate-500">
        Categoria de conservacao <strong>sem procedencia registrada</strong> —
        falta o ano da avaliacao e a versao da Lista Vermelha. O projeto nao
        exibe categoria que nao consegue datar.
      </p>
    );
  }

  return (
    <>
      <p>
        <strong>{especie.iucn_categoria_rotulo}</strong> ({especie.iucn_categoria})
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Avaliada em {especie.iucn_avaliado_em}
        {especie.iucn_versao && ` — Lista Vermelha ${especie.iucn_versao}`}
        {especie.fonte_iucn_url && (
          <>
            {' · '}
            <a
              href={especie.fonte_iucn_url}
              target="_blank"
              rel="noreferrer"
              className="font-semibold text-ocean-dark underline"
            >
              ficha na IUCN
            </a>
          </>
        )}
      </p>
    </>
  );
}

export default function ModalEspecie({ especie, onClose }) {
  if (!especie) {
    return null;
  }

  const linkImagem = resolverLinkImagem(especie);
  const rotuloLinkImagem = resolverRotuloLinkImagem(especie);
  const creditoImagem = resolverCreditoImagem(especie);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ocean-dark/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-3xl bg-white shadow-2xl md:flex"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex h-64 items-center justify-center bg-sand-light md:h-auto md:w-1/2">
          {especie.foto_url ? (
            <img
              src={especie.foto_url}
              alt={especie.nome_comum}
              className="h-full w-full object-cover"
            />
          ) : (
            <Fish size={96} className="text-ocean-light/50" />
          )}
        </div>

        <div className="relative overflow-y-auto p-6 sm:p-8 md:w-1/2">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 rounded-full bg-sand-light px-3 py-1 text-sm font-semibold text-ocean-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-dark focus-visible:ring-offset-2 focus-visible:ring-offset-white"
          >
            Fechar
          </button>

          <span className="mb-3 inline-flex items-center gap-2 rounded-full bg-sand-light px-3 py-1 text-xs font-semibold uppercase tracking-wider text-ocean-dark">
            <Info size={14} />
            {especie.tipo}
          </span>
          <h3 className="text-3xl font-bold text-ocean-dark">
            {especie.nome_comum || 'Nome nao informado'}
          </h3>
          <p className="mt-1 text-lg italic text-gray-500">{especie.nome_cientifico}</p>

          <div className="mt-6 space-y-5 text-sm text-gray-600">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-ocean-light">
                Descricao
              </p>
              <p className="leading-relaxed">
                {especie.descricao || 'Sem descricao detalhada cadastrada.'}
              </p>
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-ocean-light">
                Conservacao
              </p>
              <Conservacao especie={especie} />
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-ocean-light">
                Credito da imagem
              </p>
              <p>{creditoImagem || 'Sem credito informado'}</p>
              {especie.local_captura_foto && (
                <p className="mt-1 text-xs text-slate-500">
                  Foto tirada em {especie.local_captura_foto}
                </p>
              )}
            </div>

            {linkImagem && (
              <a
                href={linkImagem}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-ocean-light/30 px-4 py-2 font-semibold text-ocean-dark transition hover:bg-ocean-dark hover:text-white"
              >
                <ExternalLink size={16} />
                {rotuloLinkImagem}
              </a>
            )}

            {especie.fonte_url && (
              <a
                href={especie.fonte_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-ocean-light/30 px-4 py-2 font-semibold text-ocean-dark transition hover:bg-ocean-dark hover:text-white"
              >
                <ExternalLink size={16} />
                Fonte e mais informacoes
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
