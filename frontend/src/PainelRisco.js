import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, Thermometer, Sun, Wind, Activity, 
  Droplets, Waves, FlaskConical, Leaf, Flame, Sprout 
} from 'lucide-react';

// Componente para cada "cartãozinho" de dados
const ItemIndicador = ({ icon: Icon, label, valor, unidade, corIcone = "text-ocean-dark" }) => (
  <div className="flex flex-col items-center p-4 bg-sand-light/30 rounded-2xl border border-sand-dark/5 hover:bg-sand-light/50 transition-colors duration-300">
    <Icon className={`${corIcone} mb-2`} size={28} />
    <span className="text-gray-500 text-xs uppercase tracking-wider font-semibold">{label}</span>
    <div className="flex items-baseline gap-1 mt-1">
      <span className="text-xl font-bold text-ocean-dark">
        {valor !== null && valor !== undefined ? Number(valor).toFixed(2) : '--'}
      </span>
      <span className="text-[10px] text-gray-400 font-medium">{unidade}</span>
    </div>
  </div>
);

export default function PainelRisco() {
  const [dados, setDados] = useState(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/monitoramento/')
      .then(res => res.json())
      .then(lista => {
        if (lista.length > 0) setDados(lista[0]); 
      })
      .catch(err => console.error("Erro no monitoramento:", err));
  }, []);

  if (!dados) return null;

  const config = {
    'SEM_RISCO': { cor: 'bg-emerald-500', texto: 'Sem Risco', icone: <Activity /> },
    'OBSERVACAO': { cor: 'bg-yellow-500', texto: 'Em Observação', icone: <AlertTriangle /> },
    'ALERTA_1': { cor: 'bg-orange-500', texto: 'Alerta Nível 1', icone: <AlertTriangle /> },
    'ALERTA_2': { cor: 'bg-red-600', texto: 'Alerta Nível 2', icone: <AlertTriangle /> },
  };

  const status = config[dados.nivel_alerta] || config['SEM_RISCO'];

  return (
    <div className="w-full max-w-6xl mx-auto px-6 -mt-8 relative z-30">
      <div className="bg-white rounded-3xl shadow-xl overflow-hidden flex flex-col lg:flex-row border border-gray-100">
        
        {/* LADO ESQUERDO: Farol de Risco */}
        <div className={`${status.cor} text-white p-8 lg:w-1/4 flex flex-col justify-center items-center text-center`}>
          <div className="bg-white/20 p-4 rounded-full mb-4 animate-pulse">
            {React.cloneElement(status.icone, { size: 48 })}
          </div>
          <h2 className="text-2xl font-bold font-poppins leading-tight">{status.texto}</h2>
          <p className="text-white/90 mt-4 font-medium text-sm">
            Risco Integrado (IA):
            <span className="block text-3xl font-bold mt-1">{dados.risco_integrado?.toFixed(1)}%</span>
          </p>
          <div className="mt-6 text-[10px] bg-black/20 px-3 py-1 rounded-full text-white/80">
            Atualizado: {dados.data}
          </div>
        </div>

        {/* LADO DIREITO: Grid de 9 Parâmetros */}
        <div className="p-8 lg:w-3/4">
          <h3 className="text-ocean-dark font-bold mb-6 flex items-center gap-2">
            <Activity size={20} className="text-terra"/> Monitoramento Ambiental
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {/* Linha 1 */}
            <ItemIndicador icon={Thermometer} label="Temp. (SST)" valor={dados.sst_atual} unidade="°C" corIcone="text-terra"/>
            <ItemIndicador icon={Flame} label="Calor (DHW)" valor={dados.dhw_calculado} unidade="°C-sem" corIcone="text-red-500"/>
            <ItemIndicador icon={Sun} label="Luz (PAR)" valor={dados.irradiancia} unidade="E/m²/d" corIcone="text-yellow-500"/>

            {/* Linha 2 */}
            <ItemIndicador icon={Waves} label="Salinidade" valor={dados.salinidade} unidade="PSU" corIcone="text-blue-500"/>
            <ItemIndicador icon={FlaskConical} label="pH" valor={dados.ph} unidade="pH" corIcone="text-purple-500"/>
            <ItemIndicador icon={Droplets} label="Oxigênio" valor={dados.oxigenio} unidade="mg/L" corIcone="text-cyan-500"/>

            {/* Linha 3 */}
            <ItemIndicador icon={Sprout} label="Nitrato" valor={dados.nitrato} unidade="µmol/L" corIcone="text-emerald-600"/>
            <ItemIndicador icon={Leaf} label="Clorofila" valor={dados.clorofila} unidade="mg/m³" corIcone="text-green-500"/>
            <ItemIndicador icon={Wind} label="Turbidez" valor={dados.turbidez} unidade="KD490" corIcone="text-gray-400"/>
          </div>
        </div>
      </div>
    </div>
  );
}