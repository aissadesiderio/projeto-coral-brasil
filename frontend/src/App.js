import React, { useState, useEffect } from 'react';
import { Search, Info, Droplets, Fish, Anchor, Bug, Activity, ExternalLink } from 'lucide-react';

// COMPONENTE DO CARD (A miniatura na lista)
const CardEspecie = ({ especie, onClick }) => {
  return (
    <div
      onClick={() => onClick(especie)}
      className="bg-white rounded-xl shadow-lg hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 cursor-pointer overflow-hidden border border-sand-dark/30 group"
    >
      {/* Área da Imagem */}
      <div className="h-56 w-full bg-sand-light relative overflow-hidden flex items-center justify-center">
        {especie.foto ? (
          <img
            src={especie.foto}
            alt={especie.nome_comum}
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
            onError={(e) => {
              e.target.onerror = null;
              e.target.style.display = 'none'; // Esconde se der erro
              e.target.nextSibling.style.display = 'flex'; // Mostra o ícone de backup
            }}
          />
        ) : null}

        {/* Ícone de reserva (aparece se não tiver foto ou se ela falhar) */}
        <div className={`absolute inset-0 flex items-center justify-center text-ocean-light/50 ${especie.foto ? 'hidden' : 'flex'}`}>
          <Fish size={64} />
        </div>

        {/* Etiqueta do Tipo (Coral, Peixe...) */}
        <div className="absolute top-3 right-3">
          <span className="bg-white/90 backdrop-blur-sm text-ocean-dark text-xs font-bold px-3 py-1 rounded-full shadow-sm uppercase tracking-wider border border-ocean-light/20">
            {especie.tipo}
          </span>
        </div>
      </div>

      {/* Informações do Card */}
      <div className="p-5">
        <h3 className="text-xl font-bold text-ocean-dark font-poppins mb-1 truncate">
          {especie.nome_comum || "Nome Desconhecido"}
        </h3>
        <p className="text-sm text-gray-500 italic mb-4 border-b border-gray-100 pb-2">
          {especie.nome_cientifico}
        </p>

        <div className="flex justify-between items-center">
          {especie.status_conservacao ? (
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-terra bg-sand-dark/20 px-2 py-1 rounded-md">
              <Activity size={12} />
              {especie.status_conservacao}
            </span>
          ) : (
            <span className="text-xs text-gray-400">Status não avaliado</span>
          )}
          <span className="text-ocean-light hover:text-ocean-dark transition-colors">
            <Info size={20} />
          </span>
        </div>
      </div>
    </div>
  );
};

// COMPONENTE PRINCIPAL (A Galeria inteira) 
export default function GaleriaSeresVivos() {
  const [especies, setEspecies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState('TODOS');
  const [especieSelecionada, setEspecieSelecionada] = useState(null);

  // Busca os dados do Django ao carregar a página
  useEffect(() => {
    const fetchEspecies = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/especies/');
        const data = await response.json();
        setEspecies(data);
        setLoading(false);
      } catch (error) {
        console.error("Erro ao buscar espécies:", error);
        setLoading(false);
      }
    };
    fetchEspecies();
  }, []);

  // Lógica dos Filtros
  const especiesFiltradas = filtro === 'TODOS'
    ? especies
    : especies.filter(e => e.tipo === filtro);

  const filtros = [
    { id: 'TODOS', label: 'Todos', icon: <Search size={16} /> },
    { id: 'CORAL', label: 'Corais', icon: <Anchor size={16} /> },
    { id: 'PEIXE', label: 'Peixes', icon: <Fish size={16} /> },
    { id: 'INVERTEBRADO', label: 'Invertebrados', icon: <Bug size={16} /> },
    { id: 'MAMIFERO', label: 'Mamíferos', icon: <Droplets size={16} /> }
  ];

  return (
    <div className="min-h-screen bg-sand-light font-sans text-gray-800 pb-20">

      {/* Cabeçalho */}
      <header className="bg-ocean-dark text-white pt-12 pb-20 px-6 shadow-md relative overflow-hidden">
        <div className="container mx-auto max-w-6xl relative z-10 text-center">
          <h1 className="text-4xl md:text-5xl font-bold font-poppins tracking-tight mb-3">
            Projeto Coral Brasil <span className="text-terra">.</span>
          </h1>
          <p className="text-ocean-light text-lg max-w-2xl mx-auto font-light">
            Mergulhe na biodiversidade de Abrolhos e conheça as espécies que monitoramos.
          </p>
        </div>
        {/* Detalhe decorativo no fundo do header */}
        <div className="absolute bottom-0 left-0 w-full h-24 bg-gradient-to-t from-sand-light to-transparent opacity-10"></div>
      </header>

      <main className="container mx-auto px-6 max-w-6xl -mt-10 relative z-20">

        {/* Barra de Filtros Flutuante */}
        <div className="bg-white p-2 rounded-full shadow-xl mb-12 flex flex-wrap justify-center gap-2 max-w-4xl mx-auto border border-gray-100">
          {filtros.map(f => (
            <button
              key={f.id}
              onClick={() => setFiltro(f.id)}
              className={`flex items-center gap-2 px-6 py-3 rounded-full font-semibold transition-all duration-300 ${filtro === f.id
                ? 'bg-ocean-dark text-white shadow-md transform scale-105'
                : 'bg-transparent text-gray-500 hover:bg-sand-light hover:text-ocean-dark'
                }`}
            >
              {f.icon}
              {f.label}
            </button>
          ))}
        </div>

        {/* Grid de Cards */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-ocean-dark opacity-60 animate-pulse">
            <Anchor size={48} className="mb-4 animate-bounce" />
            <p className="text-xl font-medium">Carregando ecossistema...</p>
          </div>
        ) : (
          <>
            <p className="text-gray-500 mb-6 text-center text-sm uppercase tracking-widest">
              {especiesFiltradas.length} {especiesFiltradas.length === 1 ? 'espécie encontrada' : 'espécies encontradas'}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
              {especiesFiltradas.map(especie => (
                <CardEspecie
                  key={especie.id}
                  especie={especie}
                  onClick={setEspecieSelecionada}
                />
              ))}
            </div>

            {especiesFiltradas.length === 0 && (
              <div className="text-center py-20 bg-white/50 rounded-3xl border-2 border-dashed border-gray-300">
                <p className="text-gray-500 text-lg">Nenhuma espécie encontrada nesta categoria.</p>
                <button
                  onClick={() => setFiltro('TODOS')}
                  className="mt-4 text-terra font-bold hover:underline"
                >
                  Ver todas as espécies
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {/* MODAL DE DETALHES*/}
      {especieSelecionada && (
        <div
          className="fixed inset-0 bg-ocean-dark/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 transition-opacity duration-300"
          onClick={() => setEspecieSelecionada(null)}
        >
          <div
            className="bg-white rounded-3xl shadow-2xl w-full max-w-4xl overflow-hidden relative animate-fadeIn flex flex-col md:flex-row max-h-[90vh]"
            onClick={e => e.stopPropagation()}
          >
            {/* Botão Fechar */}
            <button
              onClick={() => setEspecieSelecionada(null)}
              className="absolute top-4 right-4 z-10 bg-white/20 hover:bg-terra hover:text-white text-white md:text-gray-500 md:hover:text-white w-10 h-10 rounded-full flex items-center justify-center transition-all backdrop-blur-md"
            >
              ✕
            </button>

            {/* Imagem Grande (Esquerda) */}
            <div className="md:w-1/2 h-64 md:h-auto bg-gray-100 relative flex items-center justify-center bg-sand-light">
              {especieSelecionada.foto ? (
                <img
                  src={especieSelecionada.foto}
                  alt={especieSelecionada.nome_comum}
                  className="w-full h-full object-cover"
                />
              ) : (
                <Fish size={100} className="text-ocean-light opacity-50" />
              )}

              {/* Título sobre a imagem (apenas mobile) */}
              <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-black/60 to-transparent p-6 md:hidden">
                <h2 className="text-3xl font-bold text-white font-poppins">{especieSelecionada.nome_comum}</h2>
              </div>
            </div>

            {/* Conteúdo (Direita) */}
            <div className="md:w-1/2 p-8 md:p-10 overflow-y-auto bg-white">

              {/* Cabeçalho Desktop */}
              <div className="hidden md:block mb-6">
                <span className="text-terra font-bold text-sm tracking-widest uppercase mb-2 block">
                  {especieSelecionada.tipo}
                </span>
                <h2 className="text-4xl font-bold text-ocean-dark mb-1 font-poppins leading-tight">
                  {especieSelecionada.nome_comum}
                </h2>
                <p className="text-lg text-gray-400 italic font-serif">
                  {especieSelecionada.nome_cientifico}
                </p>
              </div>

              <div className="space-y-8">
                {/* Bloco de Descrição */}
                <div className="bg-sand-light/30 p-6 rounded-2xl border border-sand-dark/10">
                  <h4 className="font-bold text-ocean-dark flex items-center gap-2 mb-3 text-lg">
                    <Activity className="text-terra" size={20} /> Sobre a Espécie
                  </h4>
                  <p className="text-gray-600 leading-relaxed text-justify mb-4">
                    {especieSelecionada.descricao || "Nenhuma descrição detalhada disponível para esta espécie no momento."}
                  </p>

                  {/*  BOTÃO DE FONTE (só aparece se tiver link)  */}
                  {especieSelecionada.fonte_url && (
                    <a
                      href={especieSelecionada.fonte_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-sm text-ocean-dark font-bold bg-white px-4 py-2 rounded-full border border-ocean-light/30 hover:bg-ocean-dark hover:text-white hover:border-transparent transition-all duration-300 shadow-sm group"
                    >
                      <ExternalLink size={16} />
                      Fonte e mais informações
                      <span className="group-hover:translate-x-1 transition-transform">→</span>
                    </a>
                  )}
                </div>

                {/* Status de Conservação */}
                <div>
                  <h4 className="font-bold text-ocean-dark mb-2 text-sm uppercase tracking-wider text-gray-400">
                    Status de Conservação
                  </h4>
                  <div className={`inline-block px-4 py-2 rounded-lg font-semibold shadow-sm text-white ${!especieSelecionada.status_conservacao ? 'bg-gray-400' : 'bg-ocean-dark'
                    }`}>
                    {especieSelecionada.status_conservacao || "Não avaliado"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}