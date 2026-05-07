export default function SectionTitle({ titulo, descricao }) {
  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-xl font-semibold text-ocean-dark sm:text-2xl">{titulo}</h3>
      <p className="text-sm leading-relaxed text-gray-600 sm:text-base">{descricao}</p>
    </div>
  );
}
