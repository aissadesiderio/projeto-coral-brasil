import { ImageOff } from 'lucide-react';

export default function ImagemRecife({
  nome,
  imagem,
  className = 'h-48 w-full object-cover',
}) {
  const fallbackClassName = className.replace('object-cover', '').trim();

  if (imagem) {
    return <img src={imagem} alt={nome} className={className} />;
  }

  return (
    <div
      className={`flex items-end bg-gradient-to-br from-ocean-dark via-ocean-light to-cyan-400 p-4 text-white ${fallbackClassName}`}
    >
      <div>
        <ImageOff size={18} className="mb-2 opacity-80" />
        <p className="text-sm font-semibold">{nome}</p>
      </div>
    </div>
  );
}
