import { Activity } from 'lucide-react';
import { Link } from 'react-router-dom';

import CardEspecie from '../components/CardEspecie';
import DatasetCard from '../components/DatasetCard';
import ImagemRecife from '../components/ImagemRecife';
import PainelPredicao from '../components/PainelPredicao';
import SectionTitle from '../components/SectionTitle';
import { formatarData, formatarLocal } from '../utils/formatters';
import { ROTAS_APP } from '../utils/navigation';

export default function LocalRecifePage({
  recife,
  siteOffline,
  offlineMessage,
  onOpenEspecie,
  carregandoDetalhe = false,
  erroDetalhe = false,
  datasetsRelacionados = [],
  carregandoDatasetsRelacionados = false,
  erroDatasetsRelacionados = false,
  usandoFallbackDatasets = false,
}) {
  const especiesAssociadas = recife.especies || [];

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <Link to={ROTAS_APP.recifes} className="w-fit font-medium text-ocean-dark transition hover:underline">
        Voltar para localizacoes
      </Link>

      {carregandoDetalhe && (
        <div className="rounded-2xl border border-sand-dark/20 bg-white p-4 text-sm text-slate-600 shadow-sm">
          Atualizando os dados mais recentes desta localizacao...
        </div>
      )}

      {erroDetalhe && !carregandoDetalhe && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Nao foi possivel atualizar este detalhe agora. Exibindo os dados disponiveis na
          aplicacao.
        </div>
      )}

      <div className="overflow-hidden rounded-3xl border border-sand-dark/20 bg-white shadow-sm">
        <ImagemRecife
          nome={recife.nome}
          imagem={recife.imagem_url}
          className="h-56 w-full object-cover sm:h-72"
        />

        <div className="p-5 sm:p-6 lg:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-ocean-light">
            Localizacao monitorada
          </p>
          <h2 className="mt-2 text-3xl font-bold text-ocean-dark sm:text-4xl">{recife.nome}</h2>
          <p className="mt-2 text-base text-gray-600">{formatarLocal(recife)}</p>
          <p className="mt-4 max-w-4xl leading-relaxed text-gray-600">{recife.descricao}</p>
          <p className="mt-4 text-sm text-gray-500">
            Ultima atualizacao: {formatarData(recife.ultima_atualizacao)}
          </p>
        </div>
      </div>

      {siteOffline && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          <strong>Modo manutencao:</strong>{' '}
          {offlineMessage || 'Exibindo dados locais de referencia.'}
        </div>
      )}

      <section className="space-y-4">
        <SectionTitle
          titulo="Previsao de estresse termico"
          descricao={`Probabilidade de alerta termico em ${recife.nome} nos proximos 7 dias, calculada a partir da serie do satelite.`}
        />

        {/* O proprio painel decide o que mostrar em cada estado — inclusive
            quando falta dado. O portao anterior (`possuiPainelCompleto`) exigia
            sete campos do modelo legado, dois deles de variaveis que o projeto
            nem coleta mais, e por isso nunca liberava com dado real. */}
        <PainelPredicao slug={recife.slug} publicOffline={siteOffline} />
      </section>

      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <SectionTitle
            titulo="Especies associadas"
            descricao={`Especies vinculadas a ${recife.nome} na camada biologica da plataforma.`}
          />
          <span className="inline-flex w-fit items-center gap-2 rounded-full bg-sand-light px-3 py-1 text-xs font-semibold text-ocean-dark">
            <Activity size={14} />
            {especiesAssociadas.length} especie(s)
          </span>
        </div>

        {especiesAssociadas.length > 0 ? (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {especiesAssociadas.map((especie) => (
              <CardEspecie key={especie.id} especie={especie} onOpen={onOpenEspecie} />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500">
            Nenhuma especie foi associada a esta localizacao ainda no painel administrativo.
          </div>
        )}
      </section>

      <section className="space-y-4">
        <SectionTitle
          titulo="Datasets relacionados"
          descricao={`Datasets do catalogo geral que fazem referencia direta a ${recife.nome}.`}
        />

        {erroDatasetsRelacionados && (
          <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            Nao foi possivel atualizar os datasets relacionados por API agora.
            {usandoFallbackDatasets
              ? ' Exibindo uma referencia local transitoria quando disponivel.'
              : ''}
          </div>
        )}

        {carregandoDatasetsRelacionados && datasetsRelacionados.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500">
            Carregando datasets relacionados desta localizacao...
          </div>
        ) : datasetsRelacionados.length > 0 ? (
          <div className="grid gap-5 lg:grid-cols-2">
            {datasetsRelacionados.map((dataset) => (
              <DatasetCard key={dataset.id} item={dataset} compact />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500">
            {erroDatasetsRelacionados
              ? 'Nao foi possivel carregar datasets relacionados no momento e nenhuma referencia local estava disponivel.'
              : 'Ainda nao ha datasets relacionados diretamente a esta localizacao.'}
          </div>
        )}
      </section>
    </section>
  );
}
