/**
 * Um campo de filtro do desenho 3a: rótulo mono em caixa alta, campo
 * sublinhado.
 *
 * ⚠️ Continua sendo um `<label>` envolvendo o controle. É o que dá nome
 * acessível ao `<select>` sem `id`/`for` espalhados pela página — e é por esse
 * nome que os testes do catálogo alcançam cada filtro.
 */
export default function CampoFiltro({ label, children }) {
  return (
    <label className="block min-w-0">
      <span className="rotulo-mono mb-1.5 block text-ocean-deep/50">{label}</span>
      {children}
    </label>
  );
}
