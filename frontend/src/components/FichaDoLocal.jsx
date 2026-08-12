import { MapPin } from 'lucide-react';

/**
 * A ficha fisica do recife — tudo o que o projeto sabe do **lugar**.
 *
 * 🚨 **Ate 12/08/2026 profundidade e area existiam no banco e nao saiam do
 * Django admin.** Estavam no modelo desde a migracao `0014`, nunca entraram no
 * serializer, nunca apareceram numa tela. O motivo de ninguem ter reparado e
 * exatamente o que torna o caso interessante: **nenhuma previsao usa esses dois
 * campos**, entao a ausencia deles nao quebrava nada — nem teste, nem grafico,
 * nem numero. Um site que se apresenta como banco de dados de recifes guardava
 * dois dos poucos atributos fisicos que tem de um recife e nao os mostrava.
 *
 * ⚠️ **"Nao registrado" e escrito, nao omitido.** Esconder a linha vazia faria
 * o visitante ler a ficha como completa — e a diferenca entre "este recife tem
 * 10 m" e "ninguem mediu a profundidade deste recife" e informacao, nao
 * formatacao. Mesmo principio de `iucn_categoria` sem ano e de
 * `motivo_sem_serie`: a lacuna se declara.
 *
 * ⚠️ A coordenada vem sempre acompanhada de `fonte_coordenadas`. Numero de
 * latitude sem origem e o que `fonte_coordenadas` existe para impedir — ver
 * docs/FONTES.md §2.3, onde metade dos locais ainda esta com origem aproximada
 * ou pendente de conferencia, e isso precisa aparecer para quem le.
 */

const NAO_REGISTRADO = 'Nao registrado';

function formatarCoordenadas(local) {
  if (local.latitude === null || local.latitude === undefined) {
    return NAO_REGISTRADO;
  }
  if (local.longitude === null || local.longitude === undefined) {
    return NAO_REGISTRADO;
  }
  // Quatro casas ~ 11 m. Mais casas que isso anunciariam precisao que a
  // origem das coordenadas nao sustenta — metade dos locais tem origem
  // aproximada ou pendente de conferencia (docs/FONTES.md §2.3).
  //
  // ⚠️ Ponto decimal, e nao virgula, apesar do resto da tela ser pt-BR: este
  // par existe para ser **colado num mapa**, e "-17,9720, -38,6880" tem quatro
  // separadores iguais e nenhuma forma de saber onde um numero acaba. E o
  // mesmo formato do `help_text` do modelo.
  return `${Number(local.latitude).toFixed(4)}, ${Number(local.longitude).toFixed(4)}`;
}

function formatarNumero(valor, unidade, casas = 1) {
  if (valor === null || valor === undefined || !Number.isFinite(Number(valor))) {
    return NAO_REGISTRADO;
  }
  return `${Number(valor).toLocaleString('pt-BR', {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  })} ${unidade}`;
}

function Linha({ rotulo, valor, detalhe }) {
  const vazio = valor === NAO_REGISTRADO;

  return (
    <div className="border-t border-sand-dark/10 py-3 first:border-t-0 first:pt-0">
      <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-ocean-light">
        {rotulo}
      </dt>
      <dd className={`mt-1 text-sm ${vazio ? 'italic text-slate-400' : 'text-slate-700'}`}>
        {valor}
      </dd>
      {detalhe && <p className="mt-1 text-xs text-slate-500">{detalhe}</p>}
    </div>
  );
}

export default function FichaDoLocal({ local }) {
  const coordenadas = formatarCoordenadas(local);

  return (
    <div className="rounded-2xl border border-sand-dark/20 bg-white p-5 shadow-sm">
      <p className="mb-4 flex items-center gap-2 text-sm text-slate-600">
        <MapPin size={16} className="text-ocean-dark" />
        Dados cadastrados sobre o lugar. Nenhum deles entra na previsao — estao
        aqui porque sao o que o projeto sabe deste recife.
      </p>

      <dl className="grid gap-x-8 sm:grid-cols-2">
        <Linha
          rotulo="Estado e cidade"
          valor={[local.estado, local.cidade].filter(Boolean).join(' - ') || NAO_REGISTRADO}
        />
        {/* ⚠️ "Origem" so aparece quando ha coordenada. Nos dois locais sem
            lat/lon, `fonte_coordenadas` guarda **o motivo da ausencia**, nao a
            procedencia de um numero — rotula-lo "Origem: ..." afirmaria que ha
            uma coordenada de algum lugar. O motivo ja e dito por extenso pelo
            AvisoSemSerie, logo abaixo, e repeti-lo aqui com o rotulo errado
            seria duas cópias, uma delas mentindo. */}
        <Linha
          rotulo="Coordenadas"
          valor={coordenadas}
          detalhe={
            coordenadas === NAO_REGISTRADO
              ? undefined
              : local.fonte_coordenadas
                ? `Origem: ${local.fonte_coordenadas}`
                : 'Origem nao registrada.'
          }
        />
        <Linha
          rotulo="Profundidade media"
          valor={formatarNumero(local.profundidade_media_m, 'm')}
        />
        <Linha
          rotulo="Area da zona recifal"
          valor={formatarNumero(local.area_km2, 'km²')}
        />
      </dl>
    </div>
  );
}
