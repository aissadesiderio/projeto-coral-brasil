import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Droplets,
  Flame,
  FlaskConical,
  Leaf,
  Sprout,
  Sun,
  Thermometer,
  Waves,
  Wind,
} from 'lucide-react';

const ItemIndicador = ({
  icon: Icon,
  label,
  valor,
  unidade,
  corIcone = 'text-ocean-dark',
}) => (
  <div className="flex flex-col items-center rounded-2xl border border-sand-dark/5 bg-sand-light/30 p-4 transition-colors duration-300 hover:bg-sand-light/50">
    <Icon className={`${corIcone} mb-2`} size={28} />
    <span className="text-center text-xs font-semibold uppercase tracking-wider text-gray-500">
      {label}
    </span>
    <div className="mt-1 flex items-baseline gap-1">
      <span className="text-xl font-bold text-ocean-dark">
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

  const config = {
    SEM_RISCO: { cor: 'bg-emerald-500', texto: 'Sem Risco', icone: <Activity /> },
    OBSERVACAO: { cor: 'bg-yellow-500', texto: 'Em Observacao', icone: <AlertTriangle /> },
    ALERTA_1: { cor: 'bg-orange-500', texto: 'Alerta Nivel 1', icone: <AlertTriangle /> },
    ALERTA_2: { cor: 'bg-red-600', texto: 'Alerta Nivel 2', icone: <AlertTriangle /> },
  };

  const status = config[dados.nivel_alerta] || config.SEM_RISCO;
  const rootClasses = floating
    ? 'relative z-30 mx-auto -mt-8 w-full max-w-6xl px-6'
    : 'w-full';

  return (
    <div className={rootClasses}>
      <div className="flex flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-xl lg:flex-row">
        <div
          className={`${status.cor} flex items-center justify-center p-8 text-center text-white lg:w-1/4 lg:flex-col`}
        >
          <div className="bg-white/20 mb-4 rounded-full p-4 animate-pulse">
            {React.cloneElement(status.icone, { size: 48 })}
          </div>
          <div>
            <h2 className="text-2xl font-bold leading-tight">{status.texto}</h2>
            <p className="mt-4 text-sm font-medium text-white/90">
              Risco Integrado (IA):
              <span className="mt-1 block text-3xl font-bold">
                {dados.risco_integrado?.toFixed(1)}%
              </span>
            </p>
            <div className="mt-6 rounded-full bg-black/20 px-3 py-1 text-[10px] text-white/80">
              Atualizado: {dados.data}
            </div>
          </div>
        </div>

        <div className="p-8 lg:w-3/4">
          <h3 className="mb-6 flex items-center gap-2 font-bold text-ocean-dark">
            <Activity size={20} className="text-terra" />
            Monitoramento Ambiental
          </h3>

          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <ItemIndicador
              icon={Thermometer}
              label="Temp. (SST)"
              valor={dados.sst_atual}
              unidade="C"
              corIcone="text-terra"
            />
            <ItemIndicador
              icon={Flame}
              label="Calor (DHW)"
              valor={dados.dhw_calculado}
              unidade="C-sem"
              corIcone="text-red-500"
            />
            <ItemIndicador
              icon={Sun}
              label="Luz (PAR)"
              valor={dados.irradiancia}
              unidade="E/m2/d"
              corIcone="text-yellow-500"
            />
            <ItemIndicador
              icon={Waves}
              label="Salinidade"
              valor={dados.salinidade}
              unidade="PSU"
              corIcone="text-blue-500"
            />
            <ItemIndicador
              icon={FlaskConical}
              label="pH"
              valor={dados.ph}
              unidade="pH"
              corIcone="text-purple-500"
            />
            <ItemIndicador
              icon={Droplets}
              label="Oxigenio"
              valor={dados.oxigenio}
              unidade="mg/L"
              corIcone="text-cyan-500"
            />
            <ItemIndicador
              icon={Sprout}
              label="Nitrato"
              valor={dados.nitrato}
              unidade="umol/L"
              corIcone="text-emerald-600"
            />
            <ItemIndicador
              icon={Leaf}
              label="Clorofila"
              valor={dados.clorofila}
              unidade="mg/m3"
              corIcone="text-green-500"
            />
            <ItemIndicador
              icon={Wind}
              label="Turbidez"
              valor={dados.turbidez}
              unidade="KD490"
              corIcone="text-gray-400"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
