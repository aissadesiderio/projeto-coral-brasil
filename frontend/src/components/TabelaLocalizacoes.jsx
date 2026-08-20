import CardRecife, { COLUNAS } from './CardRecife';

/**
 * O monitor: cabeçalho de coluna, linhas e a nota de proveniência no pé.
 *
 * ⚠️ O `grid-template-columns` do cabeçalho e o da linha saem da **mesma**
 * constante (`CardRecife.COLUNAS`). Declará-los em dois lugares é o defeito
 * clássico de tabela montada com grid: as colunas desalinham em silêncio na
 * primeira vez que alguém mexe num dos dois, e nenhum teste pega.
 */

const ROTULOS = {
  monitor: ['localizacao', 'degrau', 'prob.', 'DHW · 12 meses', 'especies'],
  catalogo: ['lat', 'localizacao', 'degrau', 'prob.', 'DHW · 12 meses', 'especies'],
};

export default function TabelaLocalizacoes({
  locais = [],
  predicoes = {},
  pontosDhwPorSlug = {},
  variante = 'catalogo',
  nota = null,
}) {
  const escuro = variante === 'monitor';

  return (
    <div className={escuro ? '' : 'overflow-hidden rounded-xl bg-white shadow-superficie'}>
      <div
        className={`hidden gap-x-5 px-5 sm:px-6 md:grid ${COLUNAS[variante]} ${
          escuro
            ? 'rotulo-mono border-b border-white/18 pb-2.5 text-white/45'
            : 'rotulo-mono cabecalho-tabela'
        }`}
      >
        {ROTULOS[variante].map((rotulo, indice) => (
          <span
            key={rotulo}
            className={indice === ROTULOS[variante].length - 1 ? 'text-right' : undefined}
          >
            {rotulo}
          </span>
        ))}
      </div>

      {locais.map((local) => (
        <CardRecife
          key={local.slug}
          local={local}
          predicao={predicoes[local.slug] || null}
          pontosDhw={pontosDhwPorSlug[local.slug] || null}
          variante={variante}
        />
      ))}

      {nota && (
        <p
          className={
            escuro
              ? 'mt-4 max-w-[80ch] text-[13px] leading-relaxed text-white/60'
              : 'nota-tabela m-0'
          }
        >
          {nota}
        </p>
      )}
    </div>
  );
}
