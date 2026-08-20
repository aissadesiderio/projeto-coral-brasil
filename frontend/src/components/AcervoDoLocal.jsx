import { Database } from 'lucide-react';

import { formatarData } from '../utils/formatters';

/**
 * Todas as variaveis que o projeto guarda deste recife — inclusive as que a
 * previsao ignora.
 *
 * 🚨 **O site media oito variaveis por recife e mostrava duas.** A ingestao
 * grava `sst`, `dhw`, `baa`, `baa_area_alerta`, `hotspot` e `sst_anomalia` do
 * NOAA CRW, mais `salinidade` e `oxigenio` do Copernicus — cerca de 7.200
 * medicoes de **cada uma**, por local, desde 2020. O grafico desenhava duas, e
 * as outras seis nao apareciam em lugar nenhum do site: nem numa lista, nem num
 * numero, nem numa frase dizendo que existiam. Quem visitasse concluiria,
 * corretamente pelo que via, que o projeto so tem SST e DHW.
 *
 * ⚠️ **O grafico continua com duas, e esta certo.** `sst` e `dhw` sao as que a
 * permutacao mostrou pesarem (docs/RESULTADOS.md §7), e seis curvas no mesmo
 * bloco dariam peso visual igual a variaveis que nao pesam. Escolher o que
 * desenhar e uma decisao; nao dizer o que se tem e outra. Esta tabela responde
 * a segunda pergunta.
 *
 * 🚨 **A coluna do papel evita o mal-entendido oposto.** Listar `hotspot` e
 * `baa` ao lado de `sst` sugeriria que as oito alimentam a previsao. O modelo
 * servido usa quatro janelas derivadas de `sst`, `dhw`, `salinidade` e
 * `oxigenio` — e `baa` nao e entrada nenhuma: e o **alvo**, o que ele tenta
 * prever. Confundir alvo com entrada e o erro mais caro que um painel destes
 * pode induzir, entao o papel vem escrito em cada linha.
 */

const CLASSES_DO_PAPEL = {
  feature: 'border-ocean-dark/30 bg-ocean-light/15 text-ocean-dark',
  alvo: 'border-terra/40 bg-terra/10 text-terra-dark',
  contexto: 'border-ocean-deep/12 bg-sand-lightest text-ocean-deep/60',
  opcional: 'border-ocean-deep/12 bg-sand-lightest text-ocean-deep/60',
};

function SeloPapel({ papel, rotulo }) {
  const classes = CLASSES_DO_PAPEL[papel] || CLASSES_DO_PAPEL.opcional;
  return (
    <span
      className={`inline-flex w-fit items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-2xs font-semibold ${classes}`}
    >
      {rotulo}
    </span>
  );
}

export default function AcervoDoLocal({ acervo = [] }) {
  if (!Array.isArray(acervo) || acervo.length === 0) {
    return (
      <p className="superficie px-6 py-8 text-center text-sm text-ocean-deep/55">
        Nenhuma medicao ingerida para esta localizacao ate agora.
      </p>
    );
  }

  const total = acervo.reduce((soma, item) => soma + (item.n_medicoes || 0), 0);
  const noModelo = acervo.filter((item) => item.entra_no_modelo).length;

  return (
    <div className="space-y-4">
      <p className="flex flex-wrap items-center gap-2 text-[15px] leading-relaxed text-ocean-deep/70">
        <Database size={16} className="text-terra" />
        <span>
          <strong className="font-semibold text-ocean-deep">
            {total.toLocaleString('pt-BR')} medicoes
          </strong>{' '}
          em {acervo.length} variavel(is). {noModelo} delas entra(m) na previsao; as
          demais o projeto guarda e serve mesmo sem usar.
        </span>
      </p>

      <div className="overflow-x-auto rounded-xl bg-white shadow-superficie">
        <table className="w-full min-w-[46rem] border-collapse text-left text-sm">
          <thead>
            <tr className="cabecalho-tabela">
              <th scope="col" className="rotulo-mono px-5 py-3 font-normal sm:px-6">variavel</th>
              <th scope="col" className="rotulo-mono px-5 py-3 font-normal">medicoes</th>
              <th scope="col" className="rotulo-mono px-5 py-3 font-normal">periodo</th>
              <th scope="col" className="rotulo-mono px-5 py-3 font-normal">fonte</th>
              <th scope="col" className="rotulo-mono px-5 py-3 font-normal">no modelo</th>
            </tr>
          </thead>
          <tbody>
            {acervo.map((item) => (
              <tr key={item.variavel} className="border-b border-ocean-deep/8 last:border-b-0">
                <th
                  scope="row"
                  className="px-5 py-3.5 align-top font-serif text-lg font-normal text-ocean-deep sm:px-6"
                >
                  {item.nome}
                  {item.unidade && (
                    <span className="ml-1 text-sm text-ocean-deep/55">({item.unidade})</span>
                  )}
                  <span className="mt-0.5 block font-mono text-3xs font-normal text-ocean-deep/40">
                    {item.variavel}
                  </span>
                </th>
                <td className="whitespace-nowrap px-5 py-3.5 align-top">
                  {/* O numero vem com o link que o devolve. Sem isso, "7.173
                      medicoes" e uma afirmacao sem recibo — mesmo criterio de
                      `cobertura._consulta_de_medicoes`. */}
                  <a
                    href={item.consulta}
                    target="_blank"
                    rel="noreferrer"
                    className="font-mono text-[15px] font-medium text-ocean-dark hover:underline"
                  >
                    {(item.n_medicoes || 0).toLocaleString('pt-BR')}
                  </a>
                </td>
                <td className="whitespace-nowrap px-5 py-3.5 align-top font-mono text-2xs text-ocean-deep/60">
                  {formatarData(item.data_inicio)} a {formatarData(item.data_fim)}
                </td>
                <td className="px-5 py-3.5 align-top font-mono text-2xs text-ocean-deep/50">
                  {(item.fontes || []).join(', ')}
                </td>
                <td className="px-5 py-3.5 align-top">
                  <SeloPapel papel={item.papel} rotulo={item.papel_rotulo} />
                  {item.motivo && (
                    <p className="mt-2 max-w-xs text-2xs leading-relaxed text-ocean-deep/55">
                      {item.motivo}
                    </p>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
