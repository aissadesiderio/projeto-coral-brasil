export default function CampoFiltro({ label, icon: Icon, children }) {
  return (
    <label className="block min-w-0">
      <span className="mb-2 inline-flex items-center gap-2 text-sm font-semibold text-ocean-dark">
        <Icon size={16} />
        {label}
      </span>
      {children}
    </label>
  );
}
