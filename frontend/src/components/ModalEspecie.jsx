import { ExternalLink, Fish } from 'lucide-react';

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
      <p className="text-[14.5px] leading-relaxed text-ocean-deep/70">
        Categoria de conservacao{' '}
        <strong className="font-semibold text-ocean-deep">sem procedencia registrada</strong> —
        falta o ano da avaliacao e a versao da Lista Vermelha. O projeto nao exibe categoria que
        nao consegue datar.
      </p>
    );
  }

  return (
    <>
      <p className="text-[15px] text-ocean-deep">
        <strong className="font-semibold">{especie.iucn_categoria_rotulo}</strong> (
        {especie.iucn_categoria})
      </p>
      <p className="mt-1.5 font-mono text-2xs text-ocean-deep/55">
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

function Bloco({ rotulo, children }) {
  return (
    <div>
      <p className="rotulo-mono border-b border-ocean-deep/15 pb-1.5 text-ocean-deep/50">
        {rotulo}
      </p>
      <div className="mt-2.5">{children}</div>
    </div>
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-ocean-deep/75 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="grid max-h-[90vh] w-full max-w-[1000px] overflow-hidden rounded-2xl bg-sand-lightest shadow-2xl md:grid-cols-2"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="relative hidden bg-sand-light md:block">
          {especie.foto_url ? (
            <>
              <img
                src={especie.foto_url}
                alt={especie.nome_comum}
                className="h-full w-full object-cover"
              />
              {/* ⚠️ A faixa só aparece quando há crédito. Aqui — ao contrário
                  do cartão, que sai da página sozinho num print — a ficha tem
                  o bloco de procedência logo ao lado, sempre visível; repetir
                  "sem credito informado" nos dois lugares diria duas vezes a
                  mesma ausência na mesma tela. */}
              {creditoImagem && (
                <span className="absolute inset-x-0 bottom-0 block bg-ocean-deep/75 px-4 py-2 font-mono text-3xs tracking-[0.06em] text-white/90">
                  {creditoImagem}
                </span>
              )}
            </>
          ) : (
            <span className="flex h-full w-full items-center justify-center">
              <Fish size={96} className="text-ocean-light" />
            </span>
          )}
        </div>

        <div className="overflow-y-auto p-7 sm:p-9">
          <div className="flex items-start justify-between gap-4">
            <span className="olho-terra">{especie.tipo}</span>
            <button
              type="button"
              onClick={onClose}
              className="rotulo-mono shrink-0 text-ocean-deep/55 transition hover:text-ocean-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-deep"
            >
              Fechar ✕
            </button>
          </div>

          <h3 className="mt-3.5 font-serif text-[34px] font-normal leading-[1.1] tracking-[-0.025em] text-ocean-deep">
            {especie.nome_comum || 'Nome nao informado'}
          </h3>
          <p className="mt-1 text-[17px] italic text-ocean-deep/60">{especie.nome_cientifico}</p>

          <div className="mt-7 flex flex-col gap-6">
            <Bloco rotulo="Descricao">
              <p className="text-[15px] leading-relaxed text-ocean-deep/80">
                {especie.descricao || 'Sem descricao detalhada cadastrada.'}
              </p>
            </Bloco>

            <Bloco rotulo="Conservacao">
              <Conservacao especie={especie} />
            </Bloco>

            <div className="bloco-procedencia">
              <p className="rotulo-mono text-terra-dark">Procedencia da imagem</p>
              <p className="mt-2 text-[14.5px] leading-relaxed text-ocean-deep/75">
                {creditoImagem || 'Sem credito informado'}
              </p>
              {especie.local_captura_foto && (
                <p className="mt-1.5 font-mono text-2xs text-ocean-deep/55">
                  Foto tirada em {especie.local_captura_foto}
                </p>
              )}

              <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-[13.5px] font-semibold">
                {linkImagem && (
                  <a
                    href={linkImagem}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-ocean-dark hover:underline"
                  >
                    <ExternalLink size={14} />
                    {rotuloLinkImagem}
                  </a>
                )}
                {especie.fonte_url && (
                  <a
                    href={especie.fonte_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-ocean-dark hover:underline"
                  >
                    <ExternalLink size={14} />
                    Fonte e mais informacoes
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
