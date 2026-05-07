import React, { useEffect, useMemo, useState } from 'react';
import {
  CalendarRange,
  Database,
  Download,
  Filter,
  MapPin,
  Search,
} from 'lucide-react';

import CampoFiltro from '../components/CampoFiltro';
import DatasetCard from '../components/DatasetCard';
import { DADOS_GERAIS } from '../data/datasets';
import { buscarCatalogoDatasets } from '../utils/api';
import { criarOpcoesFiltro, normalizarDatasetCatalogo } from '../utils/datasets';

export default function BancoDadosPage() {
  const [datasets, setDatasets] = useState([]);
  const [catalogoCarregado, setCatalogoCarregado] = useState(false);
  const [usandoFallback, setUsandoFallback] = useState(false);
  const [termoBusca, setTermoBusca] = useState('');
  const [fonteSelecionada, setFonteSelecionada] = useState('Todas');
  const [tipoDadoSelecionado, setTipoDadoSelecionado] = useState('Todos');
  const [localizacaoSelecionada, setLocalizacaoSelecionada] = useState('Todas');
  const [formatoSelecionado, setFormatoSelecionado] = useState('Todos');
  const [estadoSelecionado, setEstadoSelecionado] = useState('Todos');
  const [periodoSelecionado, setPeriodoSelecionado] = useState('Todos');

  useEffect(() => {
    let ativo = true;

    async function carregarCatalogo() {
      const payload = await buscarCatalogoDatasets();
      if (!ativo) {
        return;
      }

      const apiDisponivel = Array.isArray(payload);
      const origemDados = apiDisponivel ? payload : DADOS_GERAIS;
      const catalogoNormalizado = origemDados
        .map(normalizarDatasetCatalogo)
        .filter(Boolean);

      setDatasets(catalogoNormalizado);
      setUsandoFallback(!apiDisponivel);
      setCatalogoCarregado(true);
    }

    carregarCatalogo();

    return () => {
      ativo = false;
    };
  }, []);

  const fontes = useMemo(() => criarOpcoesFiltro(datasets, 'fonte', 'Todas'), [datasets]);
  const tiposDado = useMemo(() => criarOpcoesFiltro(datasets, 'tipoDado', 'Todos'), [datasets]);
  const localizacoes = useMemo(
    () => criarOpcoesFiltro(datasets, 'localizacao', 'Todas'),
    [datasets],
  );
  const formatos = useMemo(() => criarOpcoesFiltro(datasets, 'formato', 'Todos'), [datasets]);
  const estados = useMemo(() => criarOpcoesFiltro(datasets, 'estado', 'Todos'), [datasets]);
  const periodos = useMemo(() => criarOpcoesFiltro(datasets, 'periodoRotulo', 'Todos'), [datasets]);

  const resultados = useMemo(() => {
    const termoNormalizado = termoBusca.trim().toLowerCase();

    return datasets.filter((item) => {
      const bateBusca =
        !termoNormalizado ||
        item.titulo.toLowerCase().includes(termoNormalizado) ||
        item.cidade.toLowerCase().includes(termoNormalizado) ||
        item.estado.toLowerCase().includes(termoNormalizado) ||
        item.resumo.toLowerCase().includes(termoNormalizado);

      const bateFonte = fonteSelecionada === 'Todas' || item.fonte === fonteSelecionada;
      const bateTipo = tipoDadoSelecionado === 'Todos' || item.tipoDado === tipoDadoSelecionado;
      const bateLocalizacao =
        localizacaoSelecionada === 'Todas' || item.localizacao === localizacaoSelecionada;
      const bateFormato = formatoSelecionado === 'Todos' || item.formato === formatoSelecionado;
      const bateEstado = estadoSelecionado === 'Todos' || item.estado === estadoSelecionado;
      const batePeriodo = periodoSelecionado === 'Todos' || item.periodoRotulo === periodoSelecionado;

      return (
        bateBusca &&
        bateFonte &&
        bateTipo &&
        bateLocalizacao &&
        bateFormato &&
        bateEstado &&
        batePeriodo
      );
    });
  }, [
    estadoSelecionado,
    formatoSelecionado,
    fonteSelecionada,
    localizacaoSelecionada,
    periodoSelecionado,
    termoBusca,
    tipoDadoSelecionado,
    datasets,
  ]);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <div className="rounded-3xl border border-sand-dark/20 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <Database className="mt-1 text-ocean-dark" />
            <div>
              <h2 className="text-2xl font-bold text-ocean-dark">Banco de dados geral</h2>
              <p className="mt-1 max-w-3xl text-sm leading-relaxed text-gray-600 sm:text-base">
                Catalogo amplo de datasets climaticos, oceanograficos, biologicos,
                geneticos, imagens, relatorios e modelos preditivos associados ao projeto.
              </p>
            </div>
          </div>

          <span className="rounded-full bg-sand-light px-4 py-2 text-sm font-semibold text-ocean-dark">
            {catalogoCarregado ? `${resultados.length} dataset(s)` : 'Carregando...'}
          </span>
        </div>
      </div>

      {usandoFallback && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Nao foi possivel carregar o catalogo pela API agora. Exibindo o catalogo local
          de referencia como fallback temporario.
        </div>
      )}

      <div className="grid gap-4 rounded-3xl border border-sand-dark/20 bg-white p-5 shadow-sm md:grid-cols-2 xl:grid-cols-4">
        <CampoFiltro label="Buscar" icon={Search}>
          <input
            value={termoBusca}
            onChange={(event) => setTermoBusca(event.target.value)}
            placeholder="Titulo, resumo, cidade ou estado"
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          />
        </CampoFiltro>

        <CampoFiltro label="Fonte" icon={Filter}>
          <select
            value={fonteSelecionada}
            onChange={(event) => setFonteSelecionada(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {fontes.map((fonte) => (
              <option key={fonte} value={fonte}>
                {fonte}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Tipo de dado" icon={Database}>
          <select
            value={tipoDadoSelecionado}
            onChange={(event) => setTipoDadoSelecionado(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {tiposDado.map((tipo) => (
              <option key={tipo} value={tipo}>
                {tipo}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Localizacao" icon={MapPin}>
          <select
            value={localizacaoSelecionada}
            onChange={(event) => setLocalizacaoSelecionada(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {localizacoes.map((localizacao) => (
              <option key={localizacao} value={localizacao}>
                {localizacao}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Formato" icon={Download}>
          <select
            value={formatoSelecionado}
            onChange={(event) => setFormatoSelecionado(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {formatos.map((formato) => (
              <option key={formato} value={formato}>
                {formato}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Estado" icon={MapPin}>
          <select
            value={estadoSelecionado}
            onChange={(event) => setEstadoSelecionado(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {estados.map((estado) => (
              <option key={estado} value={estado}>
                {estado}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Periodo" icon={CalendarRange}>
          <select
            value={periodoSelecionado}
            onChange={(event) => setPeriodoSelecionado(event.target.value)}
            className="w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light"
          >
            {periodos.map((periodo) => (
              <option key={periodo} value={periodo}>
                {periodo}
              </option>
            ))}
          </select>
        </CampoFiltro>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {!catalogoCarregado && (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500 lg:col-span-2">
            Carregando o catalogo geral de datasets...
          </div>
        )}

        {catalogoCarregado && resultados.length === 0 && (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500 lg:col-span-2">
            Nenhum conjunto de dados corresponde aos filtros atuais.
          </div>
        )}

        {catalogoCarregado &&
          resultados.map((item) => <DatasetCard key={item.id} item={item} />)}
      </div>
    </section>
  );
}
