import { useEffect, useMemo, useState } from 'react';

import CampoFiltro from '../components/CampoFiltro';
import DatasetCard, { COLUNAS_DATASET } from '../components/DatasetCard';
import { DADOS_GERAIS } from '../data/datasets';
import { buscarCatalogoDatasets } from '../utils/api';
import { criarOpcoesFiltro, normalizarDatasetCatalogo } from '../utils/datasets';

const COLUNAS = ['conjunto', 'tipo', 'formato', 'periodo', 'tamanho', 'disponibilidade'];

const NOTA_CATALOGO =
  'Baixar exige conta aprovada por um master. Onde a API nao confirma o arquivo, a linha diz '
  + 'que o download esta indisponivel em vez de oferecer um botao que falha.';

export default function BancoDadosPage({ usuario = null }) {
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
    <section className="faixa py-12">
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
        <div>
          <span className="olho-terra">Dados abertos</span>
          <h1 className="mt-3.5 font-serif text-[36px] font-normal leading-[1.05] tracking-[-0.025em] text-ocean-deep sm:text-[44px]">
            Catalogo de dados
          </h1>
          <p className="mt-3 max-w-[66ch] text-base leading-relaxed text-ocean-deep/70">
            Dados climaticos, oceanograficos, biologicos, geneticos, imagens, relatorios e
            saidas de modelo. A coluna de disponibilidade diz o que a API confirma neste
            ambiente — o resto fica marcado como nao verificado.
          </p>
        </div>

        <span className="shrink-0 font-mono text-2xs text-ocean-deep/55">
          {catalogoCarregado ? `${resultados.length} dataset(s)` : 'Carregando...'}
        </span>
      </div>

      {usandoFallback && (
        <div className="bloco-procedencia mt-7 text-sm leading-relaxed text-ocean-deep/80">
          Nao foi possivel carregar o catalogo pela API agora. Exibindo o catalogo local
          de referencia como fallback temporario.
        </div>
      )}

      <div className="superficie mt-7 grid gap-x-7 gap-y-5 p-6 sm:grid-cols-2 lg:grid-cols-4">
        <CampoFiltro label="Buscar">
          <input
            value={termoBusca}
            onChange={(event) => setTermoBusca(event.target.value)}
            placeholder="Titulo, resumo, cidade ou estado"
            className="campo-sublinhado"
          />
        </CampoFiltro>

        <CampoFiltro label="Fonte">
          <select
            value={fonteSelecionada}
            onChange={(event) => setFonteSelecionada(event.target.value)}
            className="campo-sublinhado"
          >
            {fontes.map((fonte) => (
              <option key={fonte} value={fonte}>
                {fonte}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Tipo de dado">
          <select
            value={tipoDadoSelecionado}
            onChange={(event) => setTipoDadoSelecionado(event.target.value)}
            className="campo-sublinhado"
          >
            {tiposDado.map((tipo) => (
              <option key={tipo} value={tipo}>
                {tipo}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Localizacao">
          <select
            value={localizacaoSelecionada}
            onChange={(event) => setLocalizacaoSelecionada(event.target.value)}
            className="campo-sublinhado"
          >
            {localizacoes.map((localizacao) => (
              <option key={localizacao} value={localizacao}>
                {localizacao}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Formato">
          <select
            value={formatoSelecionado}
            onChange={(event) => setFormatoSelecionado(event.target.value)}
            className="campo-sublinhado"
          >
            {formatos.map((formato) => (
              <option key={formato} value={formato}>
                {formato}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Estado">
          <select
            value={estadoSelecionado}
            onChange={(event) => setEstadoSelecionado(event.target.value)}
            className="campo-sublinhado"
          >
            {estados.map((estado) => (
              <option key={estado} value={estado}>
                {estado}
              </option>
            ))}
          </select>
        </CampoFiltro>

        <CampoFiltro label="Periodo">
          <select
            value={periodoSelecionado}
            onChange={(event) => setPeriodoSelecionado(event.target.value)}
            className="campo-sublinhado"
          >
            {periodos.map((periodo) => (
              <option key={periodo} value={periodo}>
                {periodo}
              </option>
            ))}
          </select>
        </CampoFiltro>
      </div>

      <div className="superficie mt-6 overflow-hidden">
        <div className={`hidden gap-x-4 px-5 sm:px-6 md:grid ${COLUNAS_DATASET} rotulo-mono cabecalho-tabela`}>
          {COLUNAS.map((coluna) => (
            <span key={coluna}>{coluna}</span>
          ))}
        </div>

        {!catalogoCarregado && (
          <p className="px-6 py-10 text-center text-sm text-ocean-deep/55">
            Carregando o catalogo geral de datasets...
          </p>
        )}

        {catalogoCarregado && resultados.length === 0 && (
          <p className="px-6 py-10 text-center text-sm text-ocean-deep/55">
            Nenhum conjunto de dados corresponde aos filtros atuais.
          </p>
        )}

        {catalogoCarregado &&
          resultados.map((item) => (
            <DatasetCard key={item.id} item={item} usuario={usuario} />
          ))}

        {catalogoCarregado && resultados.length > 0 && (
          <p className="nota-tabela m-0">{NOTA_CATALOGO}</p>
        )}
      </div>
    </section>
  );
}
