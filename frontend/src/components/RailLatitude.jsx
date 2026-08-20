import { formatarLatitudeCurta, numeroOuNulo } from '../utils/formatters';
import { classificarAlerta } from '../utils/painelRisco';

/**
 * A costa como régua vertical: cada localização no seu paralelo.
 *
 * 🚨 **A régua existe porque a tabela ao lado não consegue dizer onde as coisas
 * ficam.** Uma lista ordenada por latitude comunica a ordem e esconde a
 * distância: Noronha e Abrolhos aparecem como duas linhas vizinhas quando são
 * 1.600 km de costa. Aqui a posição vertical é o próprio número, e o intervalo
 * entre dois pontos é a distância entre dois recifes.
 *
 * ⚠️ **Só entra quem tem coordenada, e quem não tem é contado por extenso.**
 * Colocar a APA Costa dos Corais num paralelo qualquer seria inventar a
 * posição que o cadastro se recusou a inventar — o mesmo motivo pelo qual ela
 * não tem série. Some da régua, aparece na contagem embaixo.
 *
 * ⚠️ **A cor do ponto é o degrau, e cinza é ausência de dado — não risco
 * baixo.** É a mesma regra da tabela: um recife sem previsão hoje não pode
 * ganhar a cor de um recife tranquilo.
 */

const CINZA = 'bg-white/25';

function posicoes(locais, altura) {
  const latitudes = locais.map((local) => numeroOuNulo(local.latitude));
  const norte = Math.max(...latitudes);
  const sul = Math.min(...latitudes);
  const amplitude = norte - sul || 1;

  return locais.map((local, indice) => {
    const dotTop = ((norte - numeroOuNulo(local.latitude)) / amplitude) * altura;
    // Os rótulos são distribuídos por igual e ligados ao ponto por um filete.
    // Ancorá-los na própria latitude empilharia os nomes de Picãozinho e Porto
    // de Galinhas um sobre o outro — 1,5° de distância, 12 px na régua.
    const labelTop = ((indice + 0.5) / locais.length) * altura;
    return { local, dotTop, labelTop };
  });
}

export default function RailLatitude({
  locais = [],
  predicoes = {},
  altura = 420,
  titulo = 'Costa',
}) {
  // 🚨 `numeroOuNulo`, e não `Number.isFinite(Number(...))`: `Number(null)` é
  // `0`, e com o teste ingênuo os dois locais cadastrados sem coordenada
  // apareciam plotados no equador — exatamente a posição inventada que o
  // cadastro se recusou a inventar. Ver `formatters.numeroOuNulo`.
  const comCoordenada = locais
    .filter((local) => numeroOuNulo(local.latitude) !== null)
    .sort((a, b) => numeroOuNulo(b.latitude) - numeroOuNulo(a.latitude));

  const semCoordenada = locais.length - comCoordenada.length;

  if (comCoordenada.length === 0) {
    return null;
  }

  const pontos = posicoes(comCoordenada, altura);
  const escala = `${formatarLatitudeCurta(comCoordenada[0].latitude)} a ${formatarLatitudeCurta(
    comCoordenada[comCoordenada.length - 1].latitude,
  )}`;

  return (
    <div className="rounded-xl bg-ocean-deep p-5 text-white">
      <p className="rotulo-mono mb-4 text-white/50">
        {titulo} · {escala}
      </p>

      <div className="relative" style={{ height: `${altura}px` }}>
        <span
          aria-hidden="true"
          className="absolute bottom-0 left-1.5 top-0 w-px bg-gradient-to-b from-ocean-light to-white/20"
        />

        {pontos.map(({ local, dotTop, labelTop }) => {
          const alerta = classificarAlerta(predicoes[local.slug] || null);
          const ligacaoTopo = Math.min(dotTop, labelTop);
          const ligacaoAltura = Math.abs(labelTop - dotTop);

          return (
            <div key={local.slug} className="absolute inset-x-0 top-0 h-0">
              <span
                aria-hidden="true"
                className={`absolute left-0 block h-3 w-3 -translate-y-1/2 rounded-full border-[3px] border-ocean-deep ${
                  alerta ? alerta.cor : CINZA
                }`}
                style={{ top: `${dotTop}px` }}
              />
              <span
                aria-hidden="true"
                className="absolute left-1.5 block w-px bg-white/25"
                style={{ top: `${ligacaoTopo}px`, height: `${ligacaoAltura}px` }}
              />
              <span
                aria-hidden="true"
                className="absolute left-1.5 block h-px w-3.5 bg-white/25"
                style={{ top: `${labelTop}px` }}
              />
              <span
                className="absolute left-6 right-0 flex -translate-y-1/2 items-baseline gap-1.5 overflow-hidden text-2xs font-semibold"
                style={{ top: `${labelTop}px` }}
              >
                <span className="truncate">{local.nome}</span>
                <span className="shrink-0 font-mono text-3xs font-normal text-white/55">
                  {formatarLatitudeCurta(local.latitude)}
                </span>
              </span>
            </div>
          );
        })}
      </div>

      {semCoordenada > 0 && (
        <p className="mt-4 border-t border-white/15 pt-3 text-2xs leading-relaxed text-white/55">
          {semCoordenada} {semCoordenada === 1 ? 'localizacao fica' : 'localizacoes ficam'} fora da
          regua: {semCoordenada === 1 ? 'esta cadastrada' : 'estao cadastradas'} sem
          latitude/longitude, e um paralelo inventado seria pior que a ausencia.
        </p>
      )}
    </div>
  );
}
