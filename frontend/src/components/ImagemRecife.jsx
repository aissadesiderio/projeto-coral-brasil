import { ExternalLink, ImageOff } from 'lucide-react';

/**
 * A foto do recife — **e de quem ela e**.
 *
 * 🚨 **Ate 12/08/2026 esta imagem aparecia sem uma palavra sobre a origem.** A
 * correcao de 11/08 (docs/FONTES.md §2.1) alcancou as fotos de *especie*: nove
 * delas vinham creditadas ao "Acervo local do projeto" sendo de terceiros, uma
 * sem licenca nenhuma. A foto do **local** nao entrou naquela conta porque nao
 * havia nem campo para credito — e o que nao tem campo nao aparece em auditoria
 * de campo errado. Ela ocupa a faixa mais visivel do site, no topo da pagina do
 * recife e no cartao da lista.
 *
 * ⚠️ **Sem credito, nada e afirmado — e a ausencia e dita.** O caminho que o
 * projeto ja rejeitou uma vez foi preencher com um padrao calculado na leitura
 * (`credito or 'Acervo local do projeto'`), que vira indistinguivel de dado
 * real. Aqui "Sem credito informado" e texto de interface: nasce e morre na
 * tela, nunca no dado.
 *
 * ⚠️ `fonteUrl` so e usado quando quem chama pode conter um link. O cartao da
 * lista inteiro e um `<Link>`, e ancora dentro de ancora e HTML invalido — por
 * isso `CardRecife` passa o credito e **nao** a URL.
 */
export default function ImagemRecife({
  nome,
  imagem,
  credito = '',
  fonteUrl = '',
  localCaptura = '',
  mostrarCredito = true,
  className = 'h-48 w-full object-cover',
}) {
  const fallbackClassName = className.replace('object-cover', '').trim();

  const legenda = mostrarCredito ? (
    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-sand-dark/10 bg-sand-lightest/70 px-4 py-2 text-xs text-slate-500">
      <span>
        {credito ? `Foto: ${credito}` : 'Foto sem credito informado'}
        {localCaptura && (
          <span className="text-slate-400"> — tirada em {localCaptura}</span>
        )}
      </span>

      {fonteUrl && (
        <a
          href={fonteUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-semibold text-ocean-dark hover:underline"
        >
          <ExternalLink size={12} />
          Ver fonte da imagem
        </a>
      )}
    </div>
  ) : null;

  if (imagem) {
    return (
      <figure className="m-0">
        <img src={imagem} alt={nome} className={className} />
        {legenda}
      </figure>
    );
  }

  // Sem arquivo nao ha o que creditar, e uma legenda dizendo "sem credito"
  // debaixo de um gradiente desenhado pelo proprio site seria falsa: o
  // gradiente e do site. A legenda so acompanha uma foto de verdade.
  return (
    <div
      className={`flex items-end bg-gradient-to-br from-ocean-dark via-ocean-light to-cyan-400 p-4 text-white ${fallbackClassName}`}
    >
      <div>
        <ImageOff size={18} className="mb-2 opacity-80" />
        <p className="text-sm font-semibold">{nome}</p>
      </div>
    </div>
  );
}
