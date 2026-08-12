import { ExternalLink, MapPin } from 'lucide-react';
import { Link } from 'react-router-dom';

import { obterQuantidadeEspeciesLocal } from '../utils/recifes';
import { formatarQuantidadeEspecies } from '../utils/formatters';
import { obterRotaLocalizacao } from '../utils/navigation';
import {
  classificarAlerta,
  formatarDataBr,
  formatarProbabilidade,
} from '../utils/painelRisco';
import AvisoSemSerie from './AvisoSemSerie';
import ImagemRecife from './ImagemRecife';

/**
 * O selo mostra o **degrau da escala**, com o nome que o servidor deu.
 *
 * 🚨 **Ele foi binario ate 31/07/2026, e o comentario que justificava isso
 * envelheceu sem que ninguem notasse.** Estava escrito aqui que *"o modelo
 * atual nao produz nivel: ele produz uma probabilidade e um limiar declarado"*
 * — verdade quando foi escrito, falsa desde 30/07, quando a escala de quatro
 * degraus entrou. O argumento continuava convincente e tinha deixado de ser
 * verdadeiro, que e a forma mais cara de comentario errado.
 *
 * A regra que fica: **o rotulo e a cor vem de `nivel`**, nunca reconstruidos
 * aqui. Um degrau que o servidor invente e este cartao nao conheca cai no
 * visual neutro em vez de quebrar.
 *
 * ⚠️ O cartao **nao** repete a acao esperada. Ele e resumo numa lista de tres;
 * a instrucao inteira fica no painel do recife, a um clique. O que ele carrega
 * e a distincao que muda a leitura da lista: degrau que **exige acao** vem
 * preenchido, os outros vem so contornados.
 */
function BadgeAlerta({ alerta }) {
  if (!alerta) {
    return (
      <span className="inline-flex w-fit items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
        Sem previsao
      </span>
    );
  }

  const classes = alerta.exigeAcao
    ? `${alerta.cor} border-transparent text-white`
    : `${alerta.corBorda} ${alerta.corFundo} ${alerta.corTexto}`;

  return (
    <span
      className={`inline-flex w-fit items-center rounded-full border px-3 py-1 text-xs font-semibold ${classes}`}
      title={alerta.acao || undefined}
    >
      {alerta.rotulo}
    </span>
  );
}

/**
 * `predicao` vem de `/api/painel-risco/`, e nao do objeto do local.
 *
 * ⚠️ Ate 27/07/2026 este cartao lia `risco_atual` do caminho legado — os 3
 * registros do `StatusPredicao`. Com o painel de detalhe ja no modelo novo,
 * manter aquele numero aqui daria **dois valores diferentes para o mesmo
 * recife**, cada um de um modelo, sem nada indicando qual vale.
 *
 * 🚨 A formatacao passa pelos mesmos helpers do painel de detalhe, e nao por
 * um `toFixed` local: e o que garante que a regra de nunca exibir "0%" nem
 * "100%" valha tambem aqui. Ver docs/RESULTADOS.md secao 22.8.
 */
export default function CardRecife({ local, predicao = null }) {
  const quantidadeEspecies = obterQuantidadeEspeciesLocal(local);
  const alerta = classificarAlerta(predicao);
  const probabilidade = formatarProbabilidade(predicao);
  const dataBase = predicao?.disponivel ? formatarDataBr(predicao.data_base) : null;

  // ⚠️ "Nao calculado" e a resposta certa para um recife cuja janela de 7 dias
  // nao fechou hoje, e a resposta **errada** para um que nunca vai ter serie
  // porque nao tem coordenada. As duas frases eram a mesma ate 12/08/2026.
  // Ver AvisoSemSerie.
  const motivoSemSerie = local.motivo_sem_serie || null;

  return (
    <Link
      to={obterRotaLocalizacao(local.slug)}
      className="group flex h-full flex-col text-left transition duration-300 hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ocean-dark focus-visible:ring-offset-4 focus-visible:ring-offset-sand-lightest"
    >
      <div className="overflow-hidden rounded-[22px] bg-white shadow-[0_18px_45px_rgba(43,105,120,0.12)]">
        {/* ⚠️ Passa o credito e **nao** a URL da fonte: o cartao inteiro e um
            `<Link>`, e uma ancora dentro de outra e HTML invalido. O link para
            a fonte fica na pagina do recife, a um clique. */}
        <ImagemRecife
          nome={local.nome}
          imagem={local.imagem_url}
          credito={local.credito_imagem}
          localCaptura={local.local_captura_foto}
          className="h-56 w-full object-cover transition duration-500 group-hover:scale-[1.03]"
        />
      </div>

      <div className="flex flex-1 flex-col px-1 pb-1 pt-5">
        <h3 className="text-card-title font-bold leading-[1.15] tracking-[-0.025em] text-ocean-dark">
          {local.nome}
        </h3>

        <p className="mt-5 inline-flex items-center gap-2 text-sm text-slate-500">
          <MapPin size={16} className="text-ocean-dark" />
          {local.estado} - {local.cidade}
        </p>

        <div className="mt-5 space-y-1.5 text-sm leading-6 text-slate-700">
          <p>{formatarQuantidadeEspecies(quantidadeEspecies)}</p>
          {motivoSemSerie ? (
            <AvisoSemSerie motivo={motivoSemSerie} compact />
          ) : (
            <>
              <p>
                Estresse termico em 7 dias:{' '}
                <span
                  className={`font-semibold ${alerta ? alerta.corTexto : 'text-slate-500'}`}
                >
                  {probabilidade ? probabilidade.texto : 'Nao calculado'}
                </span>
              </p>
              <p>
                {dataBase
                  ? `Calculado sobre dados ate ${dataBase}`
                  : 'Sem previsao disponivel para esta localizacao'}
              </p>
            </>
          )}
        </div>

        <div className="mt-5 inline-flex items-center gap-3">
          {/* Sem serie nao ha degrau a mostrar, e "Sem previsao" ao lado da
              explicacao repetiria em tom de falha o que a explicacao acabou de
              dizer que e decisao. */}
          {!motivoSemSerie && <BadgeAlerta alerta={alerta} />}
          <span className="inline-flex items-center gap-1 text-sm font-semibold text-ocean-dark">
            Abrir
            <ExternalLink
              size={15}
              className="transition duration-300 group-hover:translate-x-0.5"
            />
          </span>
        </div>
      </div>
    </Link>
  );
}
