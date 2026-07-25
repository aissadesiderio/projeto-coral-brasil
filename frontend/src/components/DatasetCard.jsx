import { AlertTriangle, CalendarRange, Download, MapPin } from 'lucide-react';

import { formatarLocal, formatarPeriodo } from '../utils/formatters';

export default function DatasetCard({ item, compact = false }) {
  const padding = compact ? 'p-4' : 'p-5';

  return (
    <article
      className={`flex h-full flex-col rounded-2xl border border-sand-dark/20 bg-white ${padding} shadow-sm`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-ocean-light">
            {item.fonte}
          </p>
          <h3 className="mt-1 text-lg font-bold text-ocean-dark">{item.titulo}</h3>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-gray-700">
            {item.tipoDado}
          </span>
          <span className="rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-gray-700">
            {item.formato}
          </span>
        </div>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-gray-600">{item.resumo}</p>

      <div className="mt-4 space-y-2 text-sm text-gray-600">
        <p className="inline-flex items-center gap-2">
          <MapPin size={15} />
          {item.localizacao} - {formatarLocal(item)}
        </p>
        <p className="inline-flex items-center gap-2">
          <CalendarRange size={15} />
          {formatarPeriodo(item)}
        </p>
        <p>
          <strong>Tamanho:</strong> {item.tamanho}
        </p>
      </div>

      <div className="mt-5 flex flex-1 items-end">
        {item.downloadUrl ? (
          <a
            href={item.downloadUrl}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-ocean-dark px-4 py-2 text-sm font-semibold text-white transition hover:bg-ocean-light sm:w-auto"
          >
            <Download size={16} />
            Baixar conjunto
          </a>
        ) : (
          <span className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900 sm:w-auto">
            <AlertTriangle size={16} />
            Download indisponivel no momento
          </span>
        )}
      </div>
    </article>
  );
}
