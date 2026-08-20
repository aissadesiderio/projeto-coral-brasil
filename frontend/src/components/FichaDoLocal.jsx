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
    <div className="border-t border-ocean-deep/10 py-3.5 first:border-t-0 first:pt-0">
      <dt className="rotulo-mono text-ocean-deep/45">{rotulo}</dt>
      {/* O valor sai em mono porque é medida: coordenada, metro, km². Quando
          falta, sai em itálico na fonte de texto — a diferença tipográfica é o
          que separa "este é o número" de "ninguém mediu". */}
      <dd
        className={`mt-1.5 ${
          vazio ? 'text-sm italic text-ocean-deep/40' : 'font-mono text-[15px] text-ocean-deep'
        }`}
      >
        {valor}
      </dd>
      {detalhe && <p className="mt-1.5 text-2xs leading-relaxed text-ocean-deep/55">{detalhe}</p>}
    </div>
  );
}

export default function FichaDoLocal({ local }) {
  const coordenadas = formatarCoordenadas(local);

  return (
    <div className="superficie p-6 sm:p-7">
      <p className="mb-5 flex items-center gap-2 text-sm text-ocean-deep/65">
        <MapPin size={16} className="text-terra" />
        Dados cadastrados sobre o lugar. Nenhum deles entra na previsao — estao
        aqui porque sao o que o projeto sabe deste recife.
      </p>

      <dl className="grid gap-x-10 sm:grid-cols-2">
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

        {/* 🚨 **Duas linhas, e nao uma.** Ate 13/08/2026 havia um campo so,
            rotulado "area da zona recifal", nulo em todos os locais. As fontes
            existiam — o que nao existia era uma resposta unica: Abrolhos tem
            879,43 km² de **parque** e ~8 km² de **recife mapeado**, 110 vezes
            menos. Mostrar um dos dois sob o rotulo do outro seria o erro de
            categoria da §6.3 do FONTES (alcalinidade exibida como pH).

            ⚠️ Cada uma vem com a **sua** fonte embaixo. Area de UC sem o
            decreto e area recifal sem o mapeamento sao numeros que ninguem
            consegue conferir — e o campo existe justamente para ser citavel. */}
        <Linha
          rotulo="Area da unidade de conservacao"
          valor={formatarNumero(local.area_uc_km2, 'km²', 2)}
          detalhe={local.fonte_area_uc || undefined}
        />
        <Linha
          rotulo="Area recifal mapeada"
          valor={formatarNumero(local.area_recifal_km2, 'km²', 2)}
          detalhe={local.fonte_area_recifal || undefined}
        />
      </dl>

      {/* ⚠️ Sem esta frase, um visitante que veja 879,43 km² na linha de cima e
          "Nao registrado" na de baixo conclui que o recife tem 879 km². A
          distincao entre as duas linhas e o dado; deixa-la implicita seria
          confiar em que o leitor conheca a diferenca entre uma UC e um recife. */}
      <p className="mt-5 border-t border-ocean-deep/10 pt-4 text-2xs leading-relaxed text-ocean-deep/55">
        As duas areas respondem perguntas diferentes: a primeira e o poligono
        legal da unidade de conservacao, a segunda e quanto de recife foi
        mapeado dentro dele. Podem diferir por ordens de grandeza, e uma nao se
        deduz da outra.
      </p>
    </div>
  );
}
