import { MapPinOff } from 'lucide-react';

/**
 * O recife existe no cadastro e nao tem serie — dito com o motivo junto.
 *
 * 🚨 **Nasceu de uma ausencia que se lia como defeito.** Quando os sete locais
 * da tabela de referencia entraram (12/08/2026), dois deles ficaram sem
 * latitude/longitude de proposito: a APA Costa dos Corais e uma area de 12
 * municipios e nao um ponto, e o Recife de Fora nao tem coordenada exata
 * publicada. Inventar um par de numeros para qualquer um dos dois seria
 * fabricar a posicao de onde o satelite mediu.
 *
 * A decisao esta certa e o **efeito dela na tela estava errado**: as paginas
 * dos dois mostravam "Nao calculado", "Ainda nao ha medicoes ingeridas" e
 * "Ainda nao ha datasets relacionados" — tres frases que descrevem
 * exatamente o mesmo estado de um recife cuja ingestao quebrou. O visitante
 * nao tinha como distinguir uma escolha registrada de um pipeline com defeito,
 * e a escolha e justamente o que o projeto tem de mais cuidadoso.
 *
 * ⚠️ **O texto vem do servidor, nao daqui.** `motivo_sem_serie` e derivado em
 * `LocalRecife.motivo_sem_serie` e viaja tanto na API quanto na copia de
 * fallback de `recifeData.js`. Reescrever a explicacao neste componente criaria
 * uma segunda redacao para divergir da primeira — e o `detalhe` e especifico de
 * cada local, entao nem daria para acertar com texto fixo.
 */
export default function AvisoSemSerie({ motivo, compact = false, escuro = false }) {
  if (!motivo) {
    return null;
  }

  if (compact) {
    return (
      <p
        className={`inline-flex items-start gap-2 text-2xs leading-5 ${
          escuro ? 'text-white/60' : 'text-ocean-deep/55'
        }`}
      >
        <MapPinOff size={14} className="mt-0.5 shrink-0" />
        <span>Sem serie de satelite: local cadastrado sem coordenadas.</span>
      </p>
    );
  }

  return (
    <div className="rounded-xl border border-ocean-deep/12 bg-white p-5 shadow-superficie">
      <p className="rotulo-mono inline-flex items-center gap-2 text-ocean-deep/55">
        <MapPinOff size={14} />
        Este local nao tem serie de satelite
      </p>
      <p className="mt-3 text-[15px] leading-relaxed text-ocean-deep/80">{motivo.resumo}</p>
      {motivo.detalhe && (
        // A razao especifica deste local, gravada junto com o cadastro. E o
        // que separa "decidimos nao inventar a coordenada" de "esquecemos de
        // preencher" — duas coisas que o resumo acima sozinho nao distingue.
        <p className="mt-4 border-l-2 border-terra pl-3 text-sm leading-relaxed text-ocean-deep/65">
          <strong className="font-semibold text-ocean-deep">Por que:</strong> {motivo.detalhe}
        </p>
      )}
    </div>
  );
}
