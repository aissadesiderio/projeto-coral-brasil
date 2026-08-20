/**
 * O título de seção do desenho 3a: serifa grande, filete embaixo e a medida à
 * direita.
 *
 * ⚠️ `meta` é reservado ao que **data ou dimensiona** a seção — "3 registros",
 * "dados ate 08/08/2026", "8 conjuntos". Sai em mono, do outro lado do filete,
 * porque é a mesma informação que um cabeçalho de coluna carrega: diz sobre
 * quanto e sobre quando é o que vem abaixo, antes de o leitor começar a ler.
 */
export default function SectionTitle({ titulo, descricao, meta = null, acao = null }) {
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 border-b border-ocean-deep/15 pb-3.5">
        <h3 className="font-serif text-[26px] font-normal tracking-[-0.02em] text-ocean-deep sm:text-[30px]">
          {titulo}
        </h3>
        {meta && <span className="font-mono text-2xs text-ocean-deep/55">{meta}</span>}
        {acao}
      </div>
      {descricao && (
        <p className="mt-3.5 max-w-[82ch] text-[15px] leading-relaxed text-ocean-deep/65">
          {descricao}
        </p>
      )}
    </div>
  );
}
