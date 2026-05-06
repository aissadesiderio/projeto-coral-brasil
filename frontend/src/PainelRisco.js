import React, { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';

import {
  MONITORAMENTO_VARIAVEIS,
  RISCO_STATUS,
} from './monitoramentoConfig';

const ItemIndicador = ({
  icon: Icon,
  label,
  valor,
  unidade,
  corIcone = 'text-ocean-dark',
}) => (
  <div className="flex min-w-0 flex-col items-center rounded-2xl border border-sand-dark/10 bg-sand-light/30 p-3 text-center transition-colors duration-300 hover:bg-sand-light/50 sm:p-4">
    <Icon className={`${corIcone} mb-2`} size={24} />
    <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 sm:text-xs">
      {label}
    </span>
    <div className="mt-1 flex items-baseline gap-1">
      <span className="text-lg font-bold text-ocean-dark sm:text-xl">
        {valor !== null && valor !== undefined ? Number(valor).toFixed(2) : '--'}
      </span>
      <span className="text-[10px] font-medium text-gray-400">{unidade}</span>
    </div>
  </div>
);

export default function PainelRisco({
  dados: dadosRecebidos = null,
  publicOffline = false,
  floating = false,
}) {
  const [dados, setDados] = useState(dadosRecebidos);

  useEffect(() => {
    setDados(dadosRecebidos);
  }, [dadosRecebidos]);

  useEffect(() => {
    if (publicOffline || dadosRecebidos || typeof fetch !== 'function') {
      return;
    }

    fetch('/api/monitoramento/')
      .then((res) => (res.ok ? res.json() : []))
      .then((lista) => {
        if (Array.isArray(lista) && lista.length > 0) {
          setDados(lista[0]);
        }
      })
      .catch((err) => console.error('Erro no monitoramento:', err));
  }, [dadosRecebidos, publicOffline]);

  if (publicOffline || !dados) {
    return null;
  }

  const status = RISCO_STATUS[dados.nivel_alerta] || RISCO_STATUS.SEM_RISCO;
  const StatusIcon = status.icone;
  const rootClasses = floating
    ? 'relative z-30 mx-auto -mt-8 w-full max-w-6xl px-2 sm:px-4 lg:px-6'
    : 'w-full';

  return (
    <div className={rootClasses}>
      <div className="flex flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-xl lg:flex-row">
        <div
          className={`${status.cor} flex items-center justify-center p-6 text-center text-white sm:p-8 lg:w-[28%] lg:flex-col`}
        >
          <div className="mb-4 rounded-full bg-white/20 p-4">
            <StatusIcon size={42} />
          </div>
          <div>
            <h2 className="text-2xl font-bold leading-tight">{status.texto}</h2>
            <p className="mt-4 text-sm font-medium text-white/90">
              Risco Integrado (IA):
              <span className="mt-1 block text-3xl font-bold">
                {dados.risco_integrado?.toFixed(1)}%
              </span>
            </p>
            <div className="mt-5 inline-flex rounded-full bg-black/20 px-3 py-1 text-[10px] text-white/80">
              Atualizado: {dados.data}
            </div>
          </div>
        </div>

        <div className="min-w-0 p-5 sm:p-8 lg:w-[72%]">
          <h3 className="mb-5 flex items-center gap-2 font-bold text-ocean-dark">
            <Activity size={20} className="text-terra" />
            Monitoramento Ambiental
          </h3>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {MONITORAMENTO_VARIAVEIS.map((variavel) => (
              <ItemIndicador
                key={variavel.campo}
                icon={variavel.icone}
                label={variavel.rotuloPainel}
                valor={dados[variavel.campo]}
                unidade={variavel.unidade}
                corIcone={variavel.corIcone}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
