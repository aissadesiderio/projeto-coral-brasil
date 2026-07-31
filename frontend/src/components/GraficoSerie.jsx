/**
 * Um painel do grafico: uma variavel, um eixo proprio.
 *
 * 🚨 **Um painel por variavel, e nao duas curvas no mesmo eixo.** Isso foi
 * medido, nao escolhido por gosto: nas figuras do TCC, DHW e temperatura no
 * mesmo eixo produziram um grafico correto e ilegivel, porque o DHW varia numa
 * escala 30x maior. A versao de eixo compartilhado so foi percebida como
 * quebrada ao abrir o PNG — nenhum teste pega isso.
 *
 * ⚠️ **SVG a mao, sem biblioteca de grafico.** Sao duas linhas e uma regua; uma
 * dependencia nova custaria mais em auditoria de cadeia do que economiza em
 * codigo, e daria menos controle justamente sobre o que aqui e delicado: buraco
 * na linha onde o valor e nulo.
 */

const LARGURA = 640;
const ALTURA = 150;
const MARGEM = { topo: 12, direita: 12, base: 22, esquerda: 44 };

const AREA_L = LARGURA - MARGEM.esquerda - MARGEM.direita;
const AREA_A = ALTURA - MARGEM.topo - MARGEM.base;

function extremos(pontos) {
  const valores = pontos.map((p) => p.valor).filter((v) => v !== null);
  if (!valores.length) {
    return null;
  }
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  // Faixa nula (serie constante) achataria tudo numa linha no topo do painel.
  const folga = maximo === minimo ? Math.abs(maximo) * 0.1 || 1 : (maximo - minimo) * 0.1;

  // 🚨 A folga nao pode empurrar o eixo para baixo de zero numa serie que
  // nunca e negativa. Visto na primeira versao ao abrir a pagina: o painel do
  // DHW anunciava **-1,0** no rodape do eixo, e DHW e calor **acumulado** —
  // nao existe acumulo negativo. Um rotulo desses convida a ler que o recife
  // "perdeu calor", que nao e o que a variavel mede.
  //
  // A regra sai do proprio dado, e nao de uma lista de variaveis: se nenhum
  // valor do periodo e negativo, zero e o piso do eixo. Nenhum teste pegaria
  // isso — so aparece olhando a tela, igual as figuras do TCC.
  const piso = minimo - folga;
  return {
    minimo: minimo >= 0 && piso < 0 ? 0 : piso,
    maximo: maximo + folga,
  };
}

/**
 * Pontos -> comandos de path, quebrando a linha em cada valor nulo.
 *
 * 🚨 O `M` depois de um buraco e o ponto todo desta funcao. Ligar os dois lados
 * de uma lacuna desenharia uma reta atravessando dias sem medida, e o leitor
 * nao teria como distinguir isso de dado real.
 */
export function montarCaminho(pontos, escalaX, escalaY) {
  let caminho = '';
  let recomecar = true;

  pontos.forEach((ponto, indice) => {
    if (ponto.valor === null) {
      recomecar = true;
      return;
    }
    const comando = recomecar ? 'M' : 'L';
    caminho += `${comando}${escalaX(indice).toFixed(1)} ${escalaY(ponto.valor).toFixed(1)} `;
    recomecar = false;
  });

  return caminho.trim();
}

export default function GraficoSerie({
  pontos = [],
  rotulo,
  unidade,
  casas = 1,
  cor = '#0369a1',
  linhaDeCorte = null,
  rotuloDoCorte = null,
}) {
  const faixa = extremos(pontos);

  if (!faixa || pontos.length < 2) {
    return (
      <p className="rounded-xl border border-dashed border-sand-dark/40 bg-white p-4 text-sm text-gray-500">
        Sem pontos suficientes de {rotulo} para desenhar uma linha.
      </p>
    );
  }

  // A linha de corte precisa caber no eixo, senao ela e desenhada fora da area
  // e o leitor conclui que a serie nunca chegou perto dela.
  const minimo = linhaDeCorte === null ? faixa.minimo : Math.min(faixa.minimo, linhaDeCorte);
  const maximo = linhaDeCorte === null ? faixa.maximo : Math.max(faixa.maximo, linhaDeCorte);

  const escalaX = (i) => MARGEM.esquerda + (i / (pontos.length - 1)) * AREA_L;
  const escalaY = (v) =>
    MARGEM.topo + AREA_A - ((v - minimo) / (maximo - minimo || 1)) * AREA_A;

  const caminho = montarCaminho(pontos, escalaX, escalaY);
  const ultimo = [...pontos].reverse().find((p) => p.valor !== null);
  const nulos = pontos.filter((p) => p.valor === null).length;

  return (
    <figure className="rounded-xl border border-sand-dark/20 bg-white p-3">
      <figcaption className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-sm font-semibold text-ocean-dark">{rotulo}</span>
        {ultimo && (
          <span className="text-sm text-gray-600">
            ultimo: <strong>{ultimo.valor.toFixed(casas).replace('.', ',')}</strong> {unidade}
          </span>
        )}
      </figcaption>

      <svg
        viewBox={`0 0 ${LARGURA} ${ALTURA}`}
        className="h-auto w-full"
        role="img"
        aria-label={`${rotulo} ao longo do periodo, em ${unidade}`}
      >
        <line
          x1={MARGEM.esquerda} y1={MARGEM.topo}
          x2={MARGEM.esquerda} y2={MARGEM.topo + AREA_A}
          stroke="#cbd5e1" strokeWidth="1"
        />
        <line
          x1={MARGEM.esquerda} y1={MARGEM.topo + AREA_A}
          x2={MARGEM.esquerda + AREA_L} y2={MARGEM.topo + AREA_A}
          stroke="#cbd5e1" strokeWidth="1"
        />

        {[maximo, minimo].map((valor) => (
          <text
            key={valor}
            x={MARGEM.esquerda - 6}
            y={escalaY(valor) + 4}
            textAnchor="end"
            fontSize="11"
            fill="#64748b"
          >
            {valor.toFixed(casas).replace('.', ',')}
          </text>
        ))}

        {linhaDeCorte !== null && (
          <>
            <line
              x1={MARGEM.esquerda} y1={escalaY(linhaDeCorte)}
              x2={MARGEM.esquerda + AREA_L} y2={escalaY(linhaDeCorte)}
              stroke="#dc2626" strokeWidth="1" strokeDasharray="4 3"
            />
            <text
              x={MARGEM.esquerda + AREA_L}
              y={escalaY(linhaDeCorte) - 4}
              textAnchor="end"
              fontSize="10"
              fill="#dc2626"
            >
              {rotuloDoCorte}
            </text>
          </>
        )}

        <path d={caminho} fill="none" stroke={cor} strokeWidth="1.6" />

        <text x={MARGEM.esquerda} y={ALTURA - 6} fontSize="10" fill="#64748b">
          {pontos[0].data}
        </text>
        <text
          x={MARGEM.esquerda + AREA_L}
          y={ALTURA - 6}
          textAnchor="end"
          fontSize="10"
          fill="#64748b"
        >
          {pontos[pontos.length - 1].data}
        </text>
      </svg>

      {nulos > 0 && (
        // ⚠️ A lacuna aparece como buraco na linha, e buraco nao se conta
        // olhando. Sem esta frase, uma serie meio vazia se parece com uma
        // serie inteira.
        <p className="mt-1 text-xs text-amber-700">
          {nulos} dia(s) sem medida valida no periodo — a linha fica interrompida
          ali, e nao em zero.
        </p>
      )}
    </figure>
  );
}
