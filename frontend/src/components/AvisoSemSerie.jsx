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
export default function AvisoSemSerie({ motivo, compact = false }) {
  if (!motivo) {
    return null;
  }

  if (compact) {
    return (
      <p className="inline-flex items-start gap-2 text-sm leading-6 text-slate-600">
        <MapPinOff size={16} className="mt-0.5 shrink-0 text-slate-500" />
        <span>Sem serie de satelite: local cadastrado sem coordenadas.</span>
      </p>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
      <p className="inline-flex items-center gap-2 text-sm font-semibold text-slate-800">
        <MapPinOff size={16} />
        Este local nao tem serie de satelite
      </p>
      <p className="mt-2 text-sm leading-relaxed text-slate-700">{motivo.resumo}</p>
      {motivo.detalhe && (
        // A razao especifica deste local, gravada junto com o cadastro. E o
        // que separa "decidimos nao inventar a coordenada" de "esquecemos de
        // preencher" — duas coisas que o resumo acima sozinho nao distingue.
        <p className="mt-3 border-l-2 border-slate-300 pl-3 text-sm leading-relaxed text-slate-600">
          <strong className="font-semibold">Por que:</strong> {motivo.detalhe}
        </p>
      )}
    </div>
  );
}
