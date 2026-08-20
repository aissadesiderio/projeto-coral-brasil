/**
 * A curva de DHW reduzida ao tamanho de uma célula de tabela.
 *
 * 🚨 **A miniatura obedece às mesmas duas regras do gráfico grande**, e não é
 * uma simplificação dele:
 *
 * 1. **Valor nulo vira buraco, nunca zero.** É a regra de
 *    `GraficoSerieInterativo` (que em 16/08/2026 substituiu o `GraficoSerie`
 *    feito à mão, mas não mudou esta regra — lá ela virou `connectgaps:
 *    false`), e
 *    numa curva de 34 px de altura ela importa mais, não menos: ninguém
 *    consegue distinguir "não mediu" de "mediu zero" olhando um traço de dois
 *    milímetros, então o traço precisa sumir ali.
 * 2. **O corte da NOAA acompanha a curva.** Sem a linha vermelha do DHW 4, a
 *    miniatura é decoração — um desenho subindo e descendo sem régua. Com ela,
 *    a mesma célula responde a pergunta que a tabela existe para responder.
 *
 * ⚠️ O eixo vertical começa em zero, e não no mínimo da série. Numa coluna de
 * várias localizações, cada uma com o seu próprio piso, as curvas ficariam
 * incomparáveis entre linhas vizinhas — que é exatamente o uso da coluna.
 */

import { useEffect, useState } from 'react';

import { CORTE_ALERTA_DHW, buscarSerie } from './serie';

export function montarSparkline(pontos, { largura = 240, altura = 34, corte = CORTE_ALERTA_DHW } = {}) {
  const validos = (Array.isArray(pontos) ? pontos : []).filter((p) => p && p.valor !== null);

  if (validos.length < 2) {
    return null;
  }

  const maximo = Math.max(corte ?? 0, ...validos.map((p) => p.valor));
  const teto = maximo > 0 ? maximo * 1.08 : 1;

  const x = (i) => (i / (pontos.length - 1)) * largura;
  const y = (v) => altura - (v / teto) * altura;

  let d = '';
  let recomecar = true;
  pontos.forEach((ponto, indice) => {
    if (!ponto || ponto.valor === null) {
      recomecar = true;
      return;
    }
    d += `${recomecar ? 'M' : 'L'}${x(indice).toFixed(1)} ${y(ponto.valor).toFixed(1)} `;
    recomecar = false;
  });

  return {
    d: d.trim(),
    corteY: corte === null ? null : Number(y(corte).toFixed(1)),
    ultimo: validos[validos.length - 1].valor,
  };
}

/**
 * Busca a série de DHW de vários locais de uma vez, para a coluna da tabela.
 *
 * ⚠️ Só pede para quem tem coordenada. Um local cadastrado sem lat/lon nunca
 * teve ingestão, e pedir a série dele geraria uma requisição cujo resultado já
 * se sabe — além de transformar uma decisão registrada em erro de rede na aba
 * de rede do navegador.
 */
export function useResumoDhw(locais = [], { ativo = true } = {}) {
  const [porSlug, setPorSlug] = useState({});

  const slugs = locais
    .filter((local) => local && local.slug && !local.motivo_sem_serie)
    .map((local) => local.slug);
  const chave = slugs.join('|');

  useEffect(() => {
    if (!ativo || !chave) {
      return undefined;
    }

    let vivo = true;

    Promise.all(
      chave.split('|').map(async (slug) => {
        const resposta = await buscarSerie(slug);
        return [slug, resposta.estado === 'ok' ? resposta.series.dhw || [] : null];
      }),
    ).then((pares) => {
      if (vivo) {
        setPorSlug(Object.fromEntries(pares));
      }
    });

    return () => {
      vivo = false;
    };
  }, [chave, ativo]);

  return porSlug;
}
