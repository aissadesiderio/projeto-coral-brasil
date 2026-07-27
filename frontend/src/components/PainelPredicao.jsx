import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CalendarClock,
  CircleHelp,
  Info,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';

import {
  buscarPredicao,
  classificarAlerta,
  descreverAtraso,
  descreverEntrada,
  formatarDataBr,
  formatarProbabilidade,
} from '../utils/painelRisco';

/**
 * O painel que exibe a predicao do modelo treinado.
 *
 * Substitui o `PainelRisco`, que lia `/api/monitoramento/` — os **3 registros**
 * do `StatusPredicao` legado. Ou seja: ate 27/07/2026 o que a tela mostrava
 * nao vinha do modelo deste projeto.
 *
 * Tres coisas aqui sao requisito, e nao estilo:
 *
 * **1. 🚨 Nunca escrever "0%" nem "100%".** A probabilidade e recalibrada por
 * regressao isotonica, que devolve extremos exatos por construcao. A API avisa
 * com `no_extremo`, e nesse caso o painel mostra a **faixa** com a explicacao,
 * nao um numero. Ver `utils/painelRisco.js` e docs/RESULTADOS.md secao 22.8.
 *
 * **2. A data-base fica visivel.** A serie tem latencia variavel. Um risco sem
 * a data sobre a qual foi calculado e lido como "agora".
 *
 * **3. O nome diz estresse termico, nao branqueamento.** O alvo do modelo e
 * `BAA >= 3` em t+7, que e a regua termica da NOAA — e ela **perde 78 dos 88**
 * branqueamentos brasileiros observados (docs/RESULTADOS.md secao 11).
 * Chamar de "previsao de branqueamento" prometeria o que nao se entrega.
 */

const Aviso = ({ icone: Icone, titulo, children, tom = 'ambar' }) => {
  const cores = {
    ambar: 'border-amber-300 bg-amber-50 text-amber-900',
    cinza: 'border-sand-dark/30 bg-sand-light/40 text-slate-700',
  };

  return (
    <div className={`rounded-2xl border p-4 text-sm ${cores[tom]}`}>
      <p className="flex items-center gap-2 font-semibold">
        <Icone size={16} />
        {titulo}
      </p>
      {children && <div className="mt-2 leading-relaxed">{children}</div>}
    </div>
  );
};

const CartaoEntrada = ({ entrada }) => {
  const Seta = entrada.subiu ? TrendingUp : TrendingDown;

  return (
    <div className="flex min-w-0 flex-col rounded-2xl border border-sand-dark/10 bg-sand-light/30 p-3 sm:p-4">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">
        {entrada.rotulo}
      </span>
      <span className="mt-1 flex items-baseline gap-1.5">
        <Seta
          size={16}
          className={entrada.subiu ? 'text-orange-500' : 'text-blue-500'}
          aria-hidden="true"
        />
        <span className="text-lg font-bold text-ocean-dark">{entrada.valor}</span>
      </span>
      <span className="mt-1 text-[10px] font-medium text-gray-400">
        {entrada.periodo}
      </span>
    </div>
  );
};

export default function PainelPredicao({ slug, publicOffline = false }) {
  const [resultado, setResultado] = useState(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (publicOffline || !slug) {
      setCarregando(false);
      return undefined;
    }

    let ativo = true;
    setCarregando(true);

    buscarPredicao(slug).then((resposta) => {
      if (ativo) {
        setResultado(resposta);
        setCarregando(false);
      }
    });

    return () => {
      ativo = false;
    };
  }, [slug, publicOffline]);

  if (publicOffline) {
    return null;
  }

  if (carregando) {
    return (
      <Aviso icone={CircleHelp} titulo="Calculando o risco desta localizacao..." tom="cinza" />
    );
  }

  if (!resultado || resultado.estado === 'indisponivel') {
    return (
      <Aviso icone={AlertTriangle} titulo="Nao foi possivel calcular o risco agora">
        O servico de predicao nao respondeu. Nenhum valor e exibido no lugar.
      </Aviso>
    );
  }

  if (resultado.estado === 'sem-modelo') {
    return (
      <Aviso icone={AlertTriangle} titulo="O modelo ainda nao esta disponivel neste servidor">
        O arquivo do modelo e gerado por comando e nao acompanha o codigo. Sem
        ele, nenhuma probabilidade e calculada — e nenhuma e inventada.
      </Aviso>
    );
  }

  if (resultado.estado === 'fora-do-treino') {
    return (
      <Aviso icone={AlertTriangle} titulo="O modelo nao foi treinado nesta localizacao">
        Responder aqui seria estender a previsao a um lugar que o modelo nunca
        viu. Preferimos nao responder.
      </Aviso>
    );
  }

  const item = resultado.dados;
  const modelo = item.modelo || {};

  if (item.disponivel !== true) {
    return (
      <Aviso icone={AlertTriangle} titulo="Dados insuficientes para calcular o risco">
        <p>
          A previsao usa a variacao dos ultimos 7 dias, e a serie deste recife
          esta incompleta. <strong>Nenhum valor foi estimado no lugar do que
          falta.</strong>
        </p>
        {item.motivo && (
          <p className="mt-2 text-xs opacity-90">{item.motivo}</p>
        )}
      </Aviso>
    );
  }

  const probabilidade = formatarProbabilidade(item);
  const alerta = classificarAlerta(item);
  const atraso = descreverAtraso(item.dias_de_atraso);
  const entradas = Object.entries(item.entradas || {}).map(([coluna, valor]) =>
    descreverEntrada(coluna, valor),
  );

  return (
    <div className="w-full">
      <div className="flex flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-xl lg:flex-row">
        <div
          className={`${alerta.cor} flex flex-col justify-center p-6 text-center text-white sm:p-8 lg:w-[34%]`}
        >
          <div className="mx-auto mb-4 w-fit rounded-full bg-white/20 p-4">
            {alerta.emAlerta ? <AlertTriangle size={42} /> : <ShieldCheck size={42} />}
          </div>

          <h2 className="text-xl font-bold leading-tight sm:text-2xl">
            {alerta.rotulo}
          </h2>

          <p className="mt-4 text-sm font-medium text-white/90">
            Risco de estresse termico em 7 dias:
            {probabilidade?.tipo === 'numero' ? (
              <span className="mt-1 block text-3xl font-bold">{probabilidade.texto}</span>
            ) : (
              <span className="mt-1 block text-lg font-bold">{probabilidade?.texto}</span>
            )}
          </p>

          {probabilidade?.explicacao && (
            <p className="mt-3 rounded-xl bg-black/20 p-2.5 text-left text-[11px] leading-relaxed text-white/85">
              {probabilidade.explicacao}
            </p>
          )}

          {alerta.limiarTexto && (
            <p className="mt-4 text-[11px] text-white/80">
              Aviso emitido a partir de {alerta.limiarTexto}
            </p>
          )}
        </div>

        <div className="min-w-0 p-5 sm:p-8 lg:w-[66%]">
          <h3 className="flex flex-wrap items-center gap-2 font-bold text-ocean-dark">
            <CalendarClock size={20} className="text-terra" />
            Calculado sobre dados ate {formatarDataBr(item.data_base)}
            {atraso && (
              <span className="rounded-full bg-sand-light px-2.5 py-0.5 text-[11px] font-semibold text-ocean-dark">
                {atraso}
              </span>
            )}
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            A previsao fala sobre {formatarDataBr(item.data_alvo)}.
          </p>

          <h4 className="mb-3 mt-5 text-sm font-semibold text-ocean-dark">
            O que o modelo olhou
          </h4>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {entradas.map((entrada) => (
              <CartaoEntrada key={entrada.coluna} entrada={entrada} />
            ))}
          </div>

          <div className="mt-5 flex gap-2 rounded-2xl border border-sand-dark/20 bg-sand-light/30 p-3 text-xs leading-relaxed text-slate-600">
            <Info size={16} className="mt-0.5 shrink-0 text-ocean-dark" />
            <p>
              O modelo preve <strong>estresse termico</strong> — o mesmo alerta
              que a NOAA calcula a partir de calor acumulado. Nao e o mesmo que
              branqueamento observado: nem todo branqueamento vem acompanhado de
              anomalia termica registrada.
              {modelo.calibracao && (
                <>
                  {' '}A probabilidade e <strong>calibrada</strong>, o que
                  significa que ela foi conferida contra a frequencia real dos
                  eventos.
                </>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
