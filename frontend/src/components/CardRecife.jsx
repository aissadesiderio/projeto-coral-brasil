import { Link } from 'react-router-dom';

import { obterQuantidadeEspeciesLocal } from '../utils/recifes';
import { formatarLatitudeCurta, formatarQuantidadeEspecies } from '../utils/formatters';
import { obterRotaLocalizacao } from '../utils/navigation';
import {
  classificarAlerta,
  formatarDataBr,
  formatarProbabilidade,
} from '../utils/painelRisco';
import { montarSparkline } from '../utils/serieResumo';
import AvisoSemSerie from './AvisoSemSerie';

/**
 * Uma localização como **linha de monitor**, e não como cartão.
 *
 * 🚨 **A troca do cartão pela linha (desenho 3a, 13/08/2026) é sobre
 * comparação, não sobre estética.** Três cartões lado a lado, cada um com foto,
 * selo e parágrafo, pedem que o leitor compare 7,3% num cartão com 21,4% em
 * outro atravessando duas fotos e dois parágrafos. Em linha, os mesmos números
 * caem na mesma coluna, com o mesmo tipo mono e a mesma casa decimal — e a
 * pergunta "qual recife está pior hoje" se responde de relance, que é a
 * pergunta que uma lista de localizações monitoradas existe para responder.
 *
 * ⚠️ **Continua sendo um `<Link>` e não uma `<tr>`.** A linha inteira é o alvo
 * do clique, e uma tabela HTML de verdade obrigaria a âncora a viver dentro de
 * uma célula — clique menor, e âncora dentro de âncora se a foto voltasse. O
 * cabeçalho de coluna vem de quem lista (`RecifesPage`, `HomePage`), com o
 * mesmo `grid-template-columns` declarado em `COLUNAS`.
 *
 * As regras herdadas do cartão antigo, que continuam valendo:
 *
 * - **O rótulo e a cor do degrau vêm de `nivel`**, nunca reconstruídos aqui. Um
 *   degrau que o servidor invente e esta versão não conheça cai no visual
 *   neutro em vez de quebrar.
 * - **`predicao` vem de `/api/painel-risco/`**, e não do objeto do local: até
 *   27/07/2026 esta superfície lia `risco_atual` do caminho legado e mostrava,
 *   para o mesmo recife, um número diferente do painel de detalhe.
 * - **A formatação passa pelos helpers de `painelRisco`**, e não por um
 *   `toFixed` local — é o que garante que a regra de nunca escrever "0%" nem
 *   "100%" valha também aqui. Ver docs/RESULTADOS.md secao 22.8.
 */

// As duas variantes têm colunas diferentes porque respondem a perguntas
// diferentes: na faixa escura da home o leitor quer o estado de hoje, no
// catálogo ele quer localizar a costa — e aí a latitude ganha coluna própria.
//
// ⚠️ As colunas só existem a partir de `md`. Abaixo disso a linha empilha: seis
// colunas em 380 px dariam 60 px cada, e um "14,2%" quebrado em duas linhas
// deixa de ser um número comparável — que é a única razão de a tabela existir.
export const COLUNAS = {
  monitor:
    'md:[grid-template-columns:minmax(0,1.5fr)_140px_108px_minmax(0,1fr)_76px]',
  catalogo:
    'md:[grid-template-columns:76px_minmax(0,1.7fr)_150px_108px_minmax(0,1fr)_88px]',
};

function BadgeAlerta({ alerta, escuro }) {
  if (!alerta) {
    return (
      <span
        className={`inline-flex w-fit items-center rounded-full border px-3 py-1 text-2xs font-semibold ${
          escuro
            ? 'border-white/20 bg-white/5 text-white/60'
            : 'border-slate-200 bg-slate-50 text-slate-600'
        }`}
      >
        Sem previsao
      </span>
    );
  }

  // Degrau que exige ação vem preenchido; os outros, contornados. É a distinção
  // que muda a leitura de uma lista inteira de relance.
  const classes = alerta.exigeAcao
    ? `${alerta.cor} border-transparent text-white`
    : escuro
      ? 'border-white/20 bg-white/10 text-white'
      : `${alerta.corBorda} ${alerta.corFundo} ${alerta.corTexto}`;

  return (
    <span
      className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-2xs font-semibold ${classes}`}
      title={alerta.acao || undefined}
    >
      <span
        aria-hidden="true"
        className={`block h-1.5 w-1.5 rounded-full ${alerta.cor}`}
      />
      {alerta.rotulo}
    </span>
  );
}

function CurvaDhw({ pontos, escuro }) {
  const curva = montarSparkline(pontos);

  if (!curva) {
    return (
      <span className={`font-mono text-3xs ${escuro ? 'text-white/40' : 'text-ocean-deep/40'}`}>
        sem serie ingerida
      </span>
    );
  }

  return (
    <svg
      viewBox="0 0 240 34"
      className="h-[34px] w-full"
      role="img"
      aria-label={`Calor acumulado dos ultimos meses, ultimo valor ${curva.ultimo
        .toFixed(1)
        .replace('.', ',')} grau-semana`}
    >
      {/* A régua da NOAA acompanha a curva: sem ela a miniatura seria um
          desenho, e não uma medida. */}
      {curva.corteY !== null && (
        <line
          x1="0"
          y1={curva.corteY}
          x2="240"
          y2={curva.corteY}
          stroke="rgba(220,38,38,0.5)"
          strokeWidth="1"
          strokeDasharray="3 3"
        />
      )}
      <path d={curva.d} fill="none" stroke="#D47046" strokeWidth="1.5" />
    </svg>
  );
}

export default function CardRecife({
  local,
  predicao = null,
  pontosDhw = null,
  variante = 'catalogo',
}) {
  const escuro = variante === 'monitor';
  const quantidadeEspecies = obterQuantidadeEspeciesLocal(local);
  const alerta = classificarAlerta(predicao);
  const probabilidade = formatarProbabilidade(predicao);
  const dataBase = predicao?.disponivel ? formatarDataBr(predicao.data_base) : null;
  const latitude = formatarLatitudeCurta(local.latitude);

  // ⚠️ "Nao calculado" é a resposta certa para um recife cuja janela de 7 dias
  // não fechou hoje, e a resposta **errada** para um que nunca vai ter série
  // porque não tem coordenada. As duas frases eram a mesma até 12/08/2026.
  const motivoSemSerie = local.motivo_sem_serie || null;

  const legendaProb = motivoSemSerie
    ? null
    : `Estresse termico em 7 dias${dataBase ? ` · dados ate ${dataBase}` : ''}`;

  return (
    <Link
      to={obterRotaLocalizacao(local.slug)}
      className={`grid grid-cols-1 items-start gap-x-5 gap-y-2 border-b px-5 py-4 transition sm:px-6 md:items-center ${
        COLUNAS[variante]
      } ${
        escuro
          ? 'border-white/12 text-white hover:bg-white/5'
          : 'border-ocean-deep/8 text-ocean-deep hover:bg-sand-nota'
      }`}
    >
      {variante === 'catalogo' && (
        <span className="font-mono text-2xs text-ocean-deep/45">{latitude || '—'}</span>
      )}

      <div className="min-w-0">
        {/* ⚠️ Corta só a partir de `md`, onde o nome divide a linha com cinco
            colunas. Empilhado no celular a linha é inteira dele, e "Parque
            Estadual Marinho de Areia Ver…" esconde qual recife é justamente na
            tela onde não há mais nada em volta para deduzir. */}
        <h3
          className={`font-serif font-normal tracking-[-0.015em] md:truncate ${
            escuro ? 'text-[23px]' : 'text-xl'
          }`}
        >
          {local.nome}
        </h3>
        <p className={`mt-0.5 text-2xs ${escuro ? 'text-white/60' : 'text-ocean-deep/55'}`}>
          {local.estado} - {local.cidade}
          {escuro && latitude && <span className="font-mono"> · {latitude}</span>}
        </p>
      </div>

      {motivoSemSerie ? (
        // Sem série não há degrau nem número a mostrar, e "Sem previsao" ao lado
        // da explicação repetiria em tom de falha o que ela acabou de dizer que
        // é decisão. As duas colunas viram uma só.
        <div className="md:col-span-2">
          <AvisoSemSerie motivo={motivoSemSerie} compact escuro={escuro} />
        </div>
      ) : (
        <>
          <BadgeAlerta alerta={alerta} escuro={escuro} />

          <div className="min-w-0">
            <span
              className={`block font-mono font-medium tracking-[-0.02em] ${
                probabilidade?.tipo === 'faixa' ? 'text-[13px] leading-tight' : 'text-[22px]'
              } ${escuro ? 'text-white' : 'text-ocean-deep'}`}
            >
              {probabilidade ? probabilidade.texto : 'Nao calculado'}
            </span>
            <span
              className={`mt-0.5 block text-[10.5px] leading-snug ${
                escuro ? 'text-white/50' : 'text-ocean-deep/50'
              }`}
            >
              {legendaProb}
            </span>
          </div>
        </>
      )}

      <CurvaDhw pontos={pontosDhw} escuro={escuro} />

      <span
        className={`font-mono text-[13px] md:text-right ${
          escuro ? 'text-white/65' : 'text-ocean-deep/60'
        }`}
        title={formatarQuantidadeEspecies(quantidadeEspecies)}
      >
        {quantidadeEspecies}
        {/* Empilhado, o número perde o cabeçalho de coluna que o rotula.
            ⚠️ O espaço é texto, e não só a margem: sem ele um leitor de tela
            anuncia "0especies". */}
        <span className="ml-1.5 font-sans text-3xs md:hidden">{' especies'}</span>
      </span>
    </Link>
  );
}
