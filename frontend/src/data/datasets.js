import homeCardBanco from '../assets/home/card-banco.webp';
import homeCardPainel from '../assets/home/card-painel.webp';
import homeCardRecifes from '../assets/home/card-recifes.webp';
import homeHeroCoral from '../assets/home/hero-coral.webp';

// Catalogo estatico mantido apenas como fallback transicional do frontend.
export const DADOS_GERAIS = [
  {
    id: 'copernicus_sst_abrolhos_2026_03',
    titulo: 'Temperatura da superficie do mar - Abrolhos',
    tipoDado: 'Climatico',
    recorteTemporal: 'intervalo',
    dataInicio: '2026-03-01',
    dataFim: '2026-03-31',
    dataPublicacao: null,
    periodoRotulo: 'Mar/2026',
    estado: 'Bahia',
    cidade: 'Caravelas',
    localizacao: 'Parque Nacional Marinho de Abrolhos',
    localSlug: 'abrolhos-ba',
    fonte: 'Copernicus',
    tamanho: '1.8 GB',
    formato: 'CSV',
    resumo:
      'Serie mensal de temperatura da superficie do mar usada para acompanhamento termico do recife.',
    downloadUrl: '/dados/sst.csv',
  },
  {
    id: 'noaa_dhw_abrolhos_2026_03',
    titulo: 'Degree Heating Week - Banco dos Abrolhos',
    tipoDado: 'Oceanografico',
    recorteTemporal: 'intervalo',
    dataInicio: '2026-03-01',
    dataFim: '2026-03-31',
    dataPublicacao: null,
    periodoRotulo: 'Mar/2026',
    estado: 'Bahia',
    cidade: 'Caravelas',
    localizacao: 'Parque Nacional Marinho de Abrolhos',
    localSlug: 'abrolhos-ba',
    fonte: 'NOAA',
    tamanho: '420 MB',
    formato: 'NetCDF',
    resumo: 'Camada mensal de aquecimento acumulado para monitoramento de estresse termico.',
    downloadUrl: '/dados/dhw.csv',
  },
  {
    id: 'inventario_biodiversidade_abrolhos_2026_q1',
    titulo: 'Inventario de biodiversidade recifal - Abrolhos',
    tipoDado: 'Biodiversidade',
    recorteTemporal: 'publicacao',
    dataInicio: null,
    dataFim: null,
    dataPublicacao: '2026-04-06',
    periodoRotulo: 'Abr/2026',
    estado: 'Bahia',
    cidade: 'Caravelas',
    localizacao: 'Parque Nacional Marinho de Abrolhos',
    localSlug: 'abrolhos-ba',
    fonte: 'Projeto Coral Brasil',
    tamanho: '48 MB',
    formato: 'JSON',
    resumo: 'Levantamento consolidado de especies associadas ao recife e suas ocorrencias.',
    downloadUrl: '/dados/biodiversidade-abrolhos.json',
  },
  {
    id: 'microbioma_picaozinho_2026_03',
    titulo: 'Microbioma de agua recifal - Picaozinho',
    tipoDado: 'Microbioma',
    recorteTemporal: 'intervalo',
    dataInicio: '2026-03-10',
    dataFim: '2026-03-24',
    dataPublicacao: null,
    periodoRotulo: 'Mar/2026',
    estado: 'Paraiba',
    cidade: 'Joao Pessoa',
    localizacao: 'Recife de Picaozinho',
    localSlug: 'picaozinho-pb',
    fonte: 'NCBI',
    tamanho: '3.1 GB',
    formato: 'FASTQ',
    resumo: 'Sequenciamento metagenomico para avaliacao microbiana do ambiente recifal.',
    downloadUrl: null,
  },
  {
    id: 'genetico_abrolhos_2026_q1',
    titulo: 'Banco genetico de corais brasileiros - Abrolhos',
    tipoDado: 'Genetico',
    recorteTemporal: 'publicacao',
    dataInicio: null,
    dataFim: null,
    dataPublicacao: '2026-04-05',
    periodoRotulo: 'Abr/2026',
    estado: 'Bahia',
    cidade: 'Caravelas',
    localizacao: 'Parque Nacional Marinho de Abrolhos',
    localSlug: 'abrolhos-ba',
    fonte: 'NCBI',
    tamanho: '95 MB',
    formato: 'FASTA',
    resumo: 'Compilado genetico com sequencias de referencia para especies coralineas.',
    downloadUrl: null,
  },
  {
    id: 'imagem_porto_2026_04',
    titulo: 'Mosaico fotografico subaquatico - Porto de Galinhas',
    tipoDado: 'Imagem',
    recorteTemporal: 'intervalo',
    dataInicio: '2026-04-01',
    dataFim: '2026-04-12',
    dataPublicacao: null,
    periodoRotulo: 'Abr/2026',
    estado: 'Pernambuco',
    cidade: 'Ipojuca',
    localizacao: 'Piscinas Naturais de Porto de Galinhas',
    localSlug: 'porto-de-galinhas-pe',
    fonte: 'Projeto Coral Brasil',
    tamanho: '2.4 GB',
    formato: 'GeoTIFF',
    resumo: 'Colecao de imagens georreferenciadas para inspecao visual do recife.',
    downloadUrl: '/dados/mosaico-porto.tif',
  },
  {
    id: 'relatorio_picaozinho_2026_04',
    titulo: 'Relatorio tecnico de campo - Picaozinho',
    tipoDado: 'Relatorio',
    recorteTemporal: 'publicacao',
    dataInicio: null,
    dataFim: null,
    dataPublicacao: '2026-04-18',
    periodoRotulo: 'Abr/2026',
    estado: 'Paraiba',
    cidade: 'Joao Pessoa',
    localizacao: 'Recife de Picaozinho',
    localSlug: 'picaozinho-pb',
    fonte: 'Projeto Coral Brasil',
    tamanho: '12 MB',
    formato: 'PDF',
    resumo: 'Relatorio com observacoes de campo, fotografias e anotacoes de amostragem.',
    downloadUrl: '/dados/relatorio-picaozinho.pdf',
  },
  {
    id: 'modelo_branqueamento_nordeste_2026_q2',
    titulo: 'Modelo preditivo de branqueamento - Costa Nordeste',
    tipoDado: 'Modelo preditivo',
    recorteTemporal: 'publicacao',
    dataInicio: null,
    dataFim: null,
    dataPublicacao: '2026-04-22',
    periodoRotulo: 'Abr/2026',
    estado: 'Regional',
    cidade: 'Costa Nordeste',
    localizacao: 'Costa Nordeste',
    localSlug: null,
    fonte: 'Projeto Coral Brasil',
    tamanho: '680 MB',
    formato: 'Parquet',
    resumo: 'Saida consolidada de um modelo regional para risco de branqueamento coralino.',
    downloadUrl: '/dados/modelo-branqueamento.parquet',
  },
];

export const HOME_HERO_IMAGE = homeHeroCoral;

// ⚠️ O `olho` numerado entrou com o desenho 3a: as tres entradas sao um
// percurso (onde estao os recifes -> o que ha de dado -> como o numero e feito),
// e nao tres atalhos equivalentes. Sem a numeracao elas se leem como um menu.
//
// 🚨 A descricao do "Painel de Risco" prometia PAR e clorofila, duas variaveis
// que o projeto **nao coleta** — o portao legado do painel chegou a exigi-las e
// por isso nunca liberava com dado real (ver LocalRecifePage). Ficaram de fora
// da redacao nova, junto com o resto da camada legada.
export const HOME_DESTAQUES = [
  {
    id: 'recifes',
    pagina: 'recifes',
    imagem: homeCardRecifes,
    olho: '01 · Localizacoes',
    titulo: 'Pagina por localizacao',
    descricao:
      'Degrau de hoje, entradas do modelo, serie medida e especies associadas em uma tela.',
  },
  {
    id: 'banco',
    pagina: 'banco',
    imagem: homeCardBanco,
    olho: '02 · Dados',
    titulo: 'Catalogo com cobertura declarada',
    descricao:
      'O que a API serve, o que e referencia externa e o que nao foi verificado — separado, nao misturado.',
  },
  {
    id: 'painel',
    pagina: 'recifes',
    imagem: homeCardPainel,
    olho: '03 · Metodo',
    titulo: 'Escala, calibracao e limites',
    descricao:
      'Por que quatro degraus, por que estresse termico e o que a regua da NOAA nao capta — no painel de cada recife.',
  },
];

export function obterDatasetsRelacionadosFallback(localSlug) {
  return DADOS_GERAIS.filter((item) => item.localSlug === localSlug);
}

export function obterDatasetsRelacionados(localSlug) {
  return obterDatasetsRelacionadosFallback(localSlug);
}
