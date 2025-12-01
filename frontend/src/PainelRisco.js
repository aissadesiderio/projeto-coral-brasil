import React, { useState, useEffect } from 'react';
import { AlertTriangle, Thermometer, Sun, Wind, Activity } from 'lucide-react';

export default function PainelRisco() {
  const [dados, setDados] = useState(null);

  useEffect(() => {
    // Pega o dado mais recente (o backend já ordena por data)
    fetch('http://127.0.0.1:8000/api/monitoramento/')
      .then(res => res.json())
      .then(lista => {
        if (lista.length > 0) setDados(lista[0]); // Pega o primeiro (hoje)
      })
      .catch(err => console.error("Erro no monitoramento:", err));
  }, []);

  if (!dados) return null; // Não mostra nada se não tiver dados

  // Configuração das Cores Baseada no Nível
  const config = {
    'SEM_RISCO': { cor: 'bg-emerald-500', texto: 'Sem Risco', icone: <Activity /> },
    'OBSERVACAO': { cor: 'bg-yellow-500', texto: 'Em Observação', icone: <AlertTriangle /> },
    'ALERTA_1': { cor: 'bg-orange-500', texto: 'Alerta Nível 1', icone: <AlertTriangle /> },
    'ALERTA_2': { cor: 'bg-red-600', texto: 'Alerta Nível 2', icone: <AlertTriangle /> },
  };

  const status = config[dados.nivel_alerta] || config['SEM_RISCO'];

  return (
    <div className="w-full max-w-6xl mx-auto px-6 -mt-8 relative z-30">
      <div className="bg-white rounded-3xl shadow-xl overflow-hidden flex flex-col md:flex-row border border-gray-100">
        
        {/* LADO ESQUERDO: O Farol de Risco */}
        <div className={`${status.cor} text-white p-8 md:w-1/3 flex flex-col justify-center items-center text-center`}>
          <div className="bg-white/20 p-4 rounded-full mb-4 animate-pulse">
            {React.cloneElement(status.icone, { size: 48 })}
          </div>
          <h2 className="text-3xl font-bold font-poppins">{status.texto}</h2>
          <p className="text-white/90 mt-2 font-medium">
            Risco Calculado (IA): {dados.risco_integrado?.toFixed(1)}%
          </p>
          <div className="mt-4 text-xs bg-black/20 px-3 py-1 rounded-full">
            Atualizado em: {dados.data}
          </div>
        </div>

        {/* LADO DIREITO: Os Detalhes Técnicos */}
        <div className="p-8 md:w-2/3 grid grid-cols-1 sm:grid-cols-3 gap-6 items-center">
          
          <div className="flex flex-col items-center p-4 bg-sand-light/30 rounded-2xl">
            <Thermometer className="text-terra mb-2" size={32} />
            <span className="text-gray-500 text-sm">Temperatura (SST)</span>
            <span className="text-2xl font-bold text-ocean-dark">
              {dados.sst_atual?.toFixed(1)}°C
            </span>
            <span className="text-xs text-terra font-semibold">
              (+{dados.anomalia?.toFixed(1)}°C acima)
            </span>
          </div>

          <div className="flex flex-col items-center p-4 bg-sand-light/30 rounded-2xl">
            <Sun className="text-yellow-600 mb-2" size={32} />
            <span className="text-gray-500 text-sm">Luz (PAR)</span>
            <span className="text-2xl font-bold text-ocean-dark">
              {dados.irradiancia?.toFixed(0)}
            </span>
            <span className="text-xs text-gray-400">einstein/m²/d</span>
          </div>

          <div className="flex flex-col items-center p-4 bg-sand-light/30 rounded-2xl">
            <Wind className="text-ocean-light mb-2" size={32} />
            <span className="text-gray-500 text-sm">Turbidez</span>
            <span className="text-2xl font-bold text-ocean-dark">
              {dados.turbidez?.toFixed(2)}
            </span>
            <span className="text-xs text-gray-400">KD490</span>
          </div>

        </div>
      </div>
    </div>
  );
}