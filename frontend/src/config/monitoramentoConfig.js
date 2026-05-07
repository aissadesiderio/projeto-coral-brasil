import {
  Activity,
  AlertTriangle,
  Droplets,
  Flame,
  Leaf,
  Sun,
  Thermometer,
  Waves,
  Wind,
} from 'lucide-react';

export const RISCO_STATUS = {
  SEM_RISCO: {
    cor: 'bg-emerald-500',
    texto: 'Baixo risco',
    textoCurto: 'Baixo risco',
    textoClasse: 'text-emerald-700',
    fundoClasse: 'bg-emerald-50',
    bordaClasse: 'border-emerald-200',
    icone: Activity,
  },
  OBSERVACAO: {
    cor: 'bg-amber-500',
    texto: 'Risco moderado',
    textoCurto: 'Risco moderado',
    textoClasse: 'text-amber-700',
    fundoClasse: 'bg-amber-50',
    bordaClasse: 'border-amber-200',
    icone: AlertTriangle,
  },
  ALERTA_1: {
    cor: 'bg-orange-500',
    texto: 'Alerta nivel 1',
    textoCurto: 'Alerta nivel 1',
    textoClasse: 'text-orange-700',
    fundoClasse: 'bg-orange-50',
    bordaClasse: 'border-orange-200',
    icone: AlertTriangle,
  },
  ALERTA_2: {
    cor: 'bg-red-600',
    texto: 'Alerta nivel 2',
    textoCurto: 'Alerta nivel 2',
    textoClasse: 'text-red-700',
    fundoClasse: 'bg-red-50',
    bordaClasse: 'border-red-200',
    icone: AlertTriangle,
  },
};

export const MONITORAMENTO_VARIAVEIS = [
  {
    campo: 'sst_atual',
    label: 'Temperatura',
    rotuloPainel: 'Temp. (SST)',
    unidade: 'C',
    corIcone: 'text-terra',
    icone: Thermometer,
  },
  {
    campo: 'dhw_calculado',
    label: 'DHW',
    rotuloPainel: 'Calor (DHW)',
    unidade: 'C-sem',
    corIcone: 'text-red-500',
    icone: Flame,
  },
  {
    campo: 'irradiancia',
    label: 'PAR',
    rotuloPainel: 'Luz (PAR)',
    unidade: 'E/m2/d',
    corIcone: 'text-yellow-500',
    icone: Sun,
  },
  {
    campo: 'salinidade',
    label: 'Salinidade',
    rotuloPainel: 'Salinidade',
    unidade: 'PSU',
    corIcone: 'text-blue-500',
    icone: Waves,
  },
  {
    campo: 'oxigenio',
    label: 'Oxigenio',
    rotuloPainel: 'Oxigenio',
    unidade: 'mg/L',
    corIcone: 'text-cyan-500',
    icone: Droplets,
  },
  {
    campo: 'clorofila',
    label: 'Clorofila',
    rotuloPainel: 'Clorofila',
    unidade: 'mg/m3',
    corIcone: 'text-green-500',
    icone: Leaf,
  },
  {
    campo: 'turbidez',
    label: 'Turbidez / KD490',
    rotuloPainel: 'Turbidez',
    unidade: 'KD490',
    corIcone: 'text-gray-400',
    icone: Wind,
  },
];

export const CAMPOS_MONITORAMENTO_OBRIGATORIOS = MONITORAMENTO_VARIAVEIS.map(
  (variavel) => variavel.campo,
);
