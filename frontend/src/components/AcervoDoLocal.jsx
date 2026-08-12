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
  feature: 'border-ocean-dark/30 bg-ocean-light/10 text-ocean-dark',
  alvo: 'border-terra/40 bg-terra/10 text-terra',
  contexto: 'border-slate-200 bg-slate-50 text-slate-600',
  opcional: 'border-slate-200 bg-slate-50 text-slate-600',
};

function SeloPapel({ papel, rotulo }) {
  const classes = CLASSES_DO_PAPEL[papel] || CLASSES_DO_PAPEL.opcional;
  return (
    <span
      className={`inline-flex w-fit items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${classes}`}
    >
      {rotulo}
    </span>
  );
}

export default function AcervoDoLocal({ acervo = [] }) {
  if (!Array.isArray(acervo) || acervo.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-6 text-center text-sm text-gray-500">
        Nenhuma medicao ingerida para esta localizacao ate agora.
      </div>
    );
  }

  const total = acervo.reduce((soma, item) => soma + (item.n_medicoes || 0), 0);
  const noModelo = acervo.filter((item) => item.entra_no_modelo).length;

  return (
    <div className="space-y-3">
      <p className="flex flex-wrap items-center gap-2 rounded-xl border border-ocean-light/30 bg-ocean-light/5 p-3 text-sm text-ocean-dark">
        <Database size={16} />
        <span>
          <strong>{total.toLocaleString('pt-BR')} medicoes</strong> em{' '}
          {acervo.length} variavel(is). {noModelo} delas entra(m) na previsao; as
          demais o projeto guarda e serve mesmo sem usar.
        </span>
      </p>

      <div className="overflow-x-auto rounded-2xl border border-sand-dark/20 bg-white shadow-sm">
        <table className="w-full min-w-[44rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-sand-dark/20 text-xs uppercase tracking-[0.12em] text-slate-500">
              <th scope="col" className="px-4 py-3 font-semibold">Variavel</th>
              <th scope="col" className="px-4 py-3 font-semibold">Medicoes</th>
              <th scope="col" className="px-4 py-3 font-semibold">Periodo</th>
              <th scope="col" className="px-4 py-3 font-semibold">Fonte</th>
              <th scope="col" className="px-4 py-3 font-semibold">No modelo</th>
            </tr>
          </thead>
          <tbody>
            {acervo.map((item) => (
              <tr key={item.variavel} className="border-b border-sand-dark/10 last:border-b-0">
                <th scope="row" className="px-4 py-3 align-top font-semibold text-ocean-dark">
                  {item.nome}
                  {item.unidade && (
                    <span className="ml-1 font-normal text-slate-500">({item.unidade})</span>
                  )}
                  <span className="mt-0.5 block font-mono text-xs font-normal text-slate-400">
                    {item.variavel}
                  </span>
                </th>
                <td className="whitespace-nowrap px-4 py-3 align-top text-slate-700">
                  {/* O numero vem com o link que o devolve. Sem isso, "7.173
                      medicoes" e uma afirmacao sem recibo — mesmo criterio de
                      `cobertura._consulta_de_medicoes`. */}
                  <a
                    href={item.consulta}
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold text-ocean-dark hover:underline"
                  >
                    {(item.n_medicoes || 0).toLocaleString('pt-BR')}
                  </a>
                </td>
                <td className="whitespace-nowrap px-4 py-3 align-top text-slate-600">
                  {formatarData(item.data_inicio)} a {formatarData(item.data_fim)}
                </td>
                <td className="px-4 py-3 align-top font-mono text-xs text-slate-500">
                  {(item.fontes || []).join(', ')}
                </td>
                <td className="px-4 py-3 align-top">
                  <SeloPapel papel={item.papel} rotulo={item.papel_rotulo} />
                  {item.motivo && (
                    <p className="mt-1.5 max-w-xs text-xs leading-relaxed text-slate-500">
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
