import { useEffect, useState } from 'react';
import { AlertTriangle, CircleHelp, TrendingDown, TrendingUp } from 'lucide-react';

import {
  buscarPredicao,
  classificarAlerta,
  descreverAtraso,
  descreverEntrada,
  formatarDataBr,
  formatarPercentual,
  formatarProbabilidade,
} from '../utils/painelRisco';

/**
 * O painel que exibe a predicao do modelo treinado.
 *
 * Substitui o `PainelRisco`, que lia `/api/monitoramento/` — os **3 registros**
 * do `StatusPredicao` legado. Ou seja: ate 27/07/2026 o que a tela mostrava
 * nao vinha do modelo deste projeto.
 *
 * Tres coisas aqui sao requisito, e nao estilo:
 *
 * **1. 🚨 Nunca escrever "0%" nem "100%".** A probabilidade e recalibrada por
 * regressao isotonica, que devolve extremos exatos por construcao. A API avisa
 * com `no_extremo`, e nesse caso o painel mostra a **faixa** com a explicacao,
 * nao um numero. Ver `utils/painelRisco.js` e docs/RESULTADOS.md secao 22.8.
 *
 * **2. A data-base fica visivel.** A serie tem latencia variavel. Um risco sem
 * a data sobre a qual foi calculado e lido como "agora".
 *
 * **3. O nome diz estresse termico, nao branqueamento.** O alvo do modelo e
 * `BAA >= 3` em t+7, que e a regua termica da NOAA — e ela **perde 78 dos 88**
 * branqueamentos brasileiros observados (docs/RESULTADOS.md secao 11).
 * Chamar de "previsao de branqueamento" prometeria o que nao se entrega.
 *
 * **4. 🚨 O degrau vem com a acao esperada, e nao so com a cor.** A escala tem
 * quatro degraus desde 30/07/2026, cada um com precisao medida e uma frase
 * dizendo o que fazer (docs/RESULTADOS.md secao 22.9.7). Um selo colorido sem
 * instrucao devolve ao leitor a decisao que o projeto tomou por ele — que e
 * exatamente o que ter quatro degraus em vez de um liga-desliga existe para
 * evitar.
 *
 * ⚠️ **A metade colorida é a única superfície de cor cheia do site.** No
 * desenho 3a tudo o mais é areia, chrome petróleo e um acento terra; o degrau
 * ganha o painel inteiro porque é a única informação da página que muda de
 * significado com a cor. Espalhar a mesma paleta por selos e cartões diluiria
 * justamente o sinal que ela existe para carregar.
 */

// Texto legível sobre cada cor cheia da escala. ⚠️ É só aparência — o slug, o
// rótulo, o corte e a ação continuam vindo do servidor.
const TEXTO_SOBRE_DEGRAU = {
  'bg-amber-400': 'text-[#3f2d05]',
};

function Aviso({ icone: Icone, titulo, children }) {
  return (
    <div className="bloco-procedencia">
      <p className="rotulo-mono flex items-center gap-2 text-terra-dark">
        <Icone size={14} />
        {titulo}
      </p>
      {children && (
        <div className="mt-2.5 text-sm leading-relaxed text-ocean-deep/75">{children}</div>
      )}
    </div>
  );
}

/**
 * A escala inteira, com o degrau de hoje marcado.
 *
 * ⚠️ Existe para dar **regua** ao degrau atual. "Observacao" sozinho nao diz se
 * e o primeiro ou o ultimo aviso da escala; ao lado dos outros tres, diz. Sem
 * isso, quem le um degrau intermediario nao tem como saber se o projeto ainda
 * tem algo pior a dizer.
 *
 * 🚨 **A escala vem do servidor**, no bloco `modelo`, e nao e reconstruida
 * aqui — repetir os cortes no frontend criaria uma segunda escala livre para
 * divergir da primeira em silencio. Se o servidor nao mandar, o bloco some.
 */
function EscalaDeAviso({ escala, atual }) {
  if (!Array.isArray(escala) || escala.length === 0) {
    return null;
  }

  return (
    <>
      <h4 className="rotulo-mono mb-3 mt-7 text-ocean-deep/55">A escala de aviso</h4>
      <ul className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {escala.map((nivel) => {
          const eOAtual = nivel.slug === atual;
          return (
            <li
              key={nivel.slug}
              className={`rounded-lg border p-3 ${
                eOAtual ? 'border-ocean-deep/40 bg-sand-lightest' : 'border-ocean-deep/12 bg-white'
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`text-[13px] font-semibold ${
                    eOAtual ? 'text-ocean-deep' : 'text-ocean-deep/70'
                  }`}
                >
                  {nivel.rotulo}
                </span>
                {eOAtual && (
                  <span className="rounded-full bg-terra px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.1em] text-white">
                    hoje
                  </span>
                )}
              </div>
              {nivel.corte > 0 && (
                <p className="mt-1.5 font-mono text-2xs text-ocean-deep/50">
                  a partir de {formatarPercentual(nivel.corte)}
                </p>
              )}
              <p className="mt-1.5 text-2xs leading-relaxed text-ocean-deep/60">{nivel.acao}</p>
            </li>
          );
        })}
      </ul>
    </>
  );
}

/**
 * As entradas do modelo, em faixa de instrumento.
 *
 * ⚠️ São **variações**, e não níveis — por isso o período vem escrito debaixo
 * de cada uma. "Temperatura: 0,09" sem o "variacao em 7 dias" se leria como
 * 0,09 °C de água.
 */
function FaixaDeEntradas({ entradas }) {
  if (entradas.length === 0) {
    return null;
  }

  return (
    <>
      <h4 className="rotulo-mono mb-3 text-ocean-deep/55">O que o modelo olhou</h4>
      <div className="grid gap-px border border-ocean-deep/12 bg-ocean-deep/12 sm:grid-cols-2 xl:grid-cols-4">
        {entradas.map((entrada) => {
          const Seta = entrada.subiu ? TrendingUp : TrendingDown;
          return (
            <div key={entrada.coluna} className="bg-white px-4 py-3">
              <p className="rotulo-mono text-ocean-deep/45">{entrada.rotulo}</p>
              <p className="mt-2 flex items-baseline gap-1.5 font-mono text-xl font-medium text-ocean-deep">
                <Seta
                  size={14}
                  className={entrada.subiu ? 'text-terra' : 'text-ocean-dark'}
                  aria-hidden="true"
                />
                {entrada.valor}
              </p>
              <p className="mt-1 text-[10.5px] text-ocean-deep/45">{entrada.periodo}</p>
            </div>
          );
        })}
      </div>
    </>
  );
}

export default function PainelPredicao({ slug, publicOffline = false }) {
  const [resultado, setResultado] = useState(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (publicOffline || !slug) {
      setCarregando(false);
      return undefined;
    }

    let ativo = true;
    setCarregando(true);

    buscarPredicao(slug).then((resposta) => {
      if (ativo) {
        setResultado(resposta);
        setCarregando(false);
      }
    });

    return () => {
      ativo = false;
    };
  }, [slug, publicOffline]);

  if (publicOffline) {
    return null;
  }

  if (carregando) {
    return (
      <p className="font-mono text-2xs text-ocean-deep/50">
        Calculando o risco desta localizacao...
      </p>
    );
  }

  if (!resultado || resultado.estado === 'indisponivel') {
    return (
      <Aviso icone={AlertTriangle} titulo="Nao foi possivel calcular o risco agora">
        O servico de predicao nao respondeu. Nenhum valor e exibido no lugar.
      </Aviso>
    );
  }

  if (resultado.estado === 'sem-modelo') {
    return (
      <Aviso icone={AlertTriangle} titulo="O modelo ainda nao esta disponivel neste servidor">
        O arquivo do modelo e gerado por comando e nao acompanha o codigo. Sem ele, nenhuma
        probabilidade e calculada — e nenhuma e inventada.
      </Aviso>
    );
  }

  if (resultado.estado === 'fora-do-treino') {
    return (
      <Aviso icone={AlertTriangle} titulo="O modelo nao foi treinado nesta localizacao">
        Responder aqui seria estender a previsao a um lugar que o modelo nunca viu. Preferimos
        nao responder.
      </Aviso>
    );
  }

  const item = resultado.dados;
  const modelo = item.modelo || {};

  if (item.disponivel !== true) {
    return (
      <Aviso icone={CircleHelp} titulo="Dados insuficientes para calcular o risco">
        <p>
          A previsao usa a variacao dos ultimos 7 dias, e a serie deste recife esta incompleta.{' '}
          <strong className="font-semibold text-ocean-deep">
            Nenhum valor foi estimado no lugar do que falta.
          </strong>
        </p>
        {item.motivo && <p className="mt-2 text-2xs opacity-90">{item.motivo}</p>}
      </Aviso>
    );
  }

  const probabilidade = formatarProbabilidade(item);
  const alerta = classificarAlerta(item);
  const atraso = descreverAtraso(item.dias_de_atraso);
  const entradas = Object.entries(item.entradas || {}).map(([coluna, valor]) =>
    descreverEntrada(coluna, valor),
  );
  const textoSobreDegrau = TEXTO_SOBRE_DEGRAU[alerta.cor] || 'text-white';

  return (
    <div className="grid overflow-hidden rounded-2xl bg-white shadow-superficie lg:grid-cols-[320px_minmax(0,1fr)]">
      <div className={`flex flex-col justify-between p-8 ${alerta.cor} ${textoSobreDegrau}`}>
        <div>
          <p className="rotulo-mono opacity-70">Degrau de hoje</p>
          <h2 className="mt-2.5 font-serif text-[34px] font-normal leading-[1.05]">
            {alerta.rotulo}
          </h2>

          <p
            className={`mt-5 font-mono font-medium leading-none tracking-[-0.03em] ${
              probabilidade?.tipo === 'numero' ? 'text-[50px]' : 'text-[22px] leading-tight'
            }`}
          >
            {probabilidade?.texto}
          </p>
          <p className="mt-2 text-2xs leading-relaxed opacity-75">
            probabilidade de estresse termico em 7 dias
            {/* ⚠️ Dois textos porque ha dois contratos. Com `nivel`, o corte que
                interessa e o **deste degrau**; sem ele — resposta de uma versao
                anterior da API — resta o limiar unico. */}
            {alerta.slug
              ? alerta.corteTexto
                && alerta.slug !== 'sem_aviso'
                && ` · este degrau comeca em ${alerta.corteTexto}`
              : alerta.limiarTexto && ` · Aviso emitido a partir de ${alerta.limiarTexto}`}
          </p>

          {probabilidade?.explicacao && (
            <p className="mt-4 rounded-lg bg-black/15 p-3 text-2xs leading-relaxed opacity-90">
              {probabilidade.explicacao}
            </p>
          )}
        </div>

        {/* 🚨 A instrucao, e nao so a cor. E o que faz quatro degraus valerem
            mais que um liga-desliga: "Observacao" e "Alerta alto" pedem coisas
            diferentes de quem le, e a diferenca esta escrita aqui em vez de
            ficar por conta da intuicao sobre a cor. */}
        {alerta.acao && (
          <div className="mt-7">
            {/* O filete acompanha a cor do degrau em vez de ser branco ou
                preto fixo: sobre o âmbar um filete branco some, sobre o
                vermelho um filete preto vira sujeira. */}
            <span aria-hidden="true" className="mb-4 block h-px bg-current opacity-25" />
            <p className="rotulo-mono opacity-70">O que fazer</p>
            <p className="mt-1.5 text-[13.5px] leading-relaxed">{alerta.acao}</p>
          </div>
        )}
      </div>

      <div className="p-8">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-ocean-deep/10 pb-3.5">
          <h3 className="font-serif text-2xl font-normal text-ocean-deep">
            Como esse numero foi feito
          </h3>
          <span className="font-mono text-2xs text-ocean-deep/55">
            dados ate {formatarDataBr(item.data_base)}
            {/* ⚠️ O separador fica **fora** do span do atraso. Dentro, o texto
                do elemento passaria a ser "· dado de 3 dias atras", e a frase
                deixaria de casar sozinha — o teste que a fixa existe porque um
                risco calculado sobre dado de tres semanas se apresenta igual a
                um calculado sobre ontem quando ninguem diz a idade. */}
            {atraso && (
              <>
                {' · '}
                <span>{atraso}</span>
              </>
            )}
          </span>
        </div>
        <p className="mb-6 mt-2.5 text-sm text-ocean-deep/60">
          A previsao fala sobre {formatarDataBr(item.data_alvo)}.
        </p>

        <FaixaDeEntradas entradas={entradas} />

        <EscalaDeAviso escala={modelo.escala} atual={alerta.slug} />

        <p className="mt-7 border-t border-ocean-deep/10 pt-4 text-[13px] leading-relaxed text-ocean-deep/65">
          O modelo preve <strong className="font-semibold text-ocean-deep">estresse termico</strong>{' '}
          — o mesmo alerta que a NOAA calcula a partir de calor acumulado. Nao e o mesmo que
          branqueamento observado: nem todo branqueamento vem acompanhado de anomalia termica
          registrada.
          {modelo.calibracao && (
            <>
              {' '}A probabilidade e <strong className="font-semibold text-ocean-deep">
                calibrada
              </strong>, o que significa que ela foi conferida contra a frequencia real dos
              eventos.
            </>
          )}
        </p>
      </div>
    </div>
  );
}
