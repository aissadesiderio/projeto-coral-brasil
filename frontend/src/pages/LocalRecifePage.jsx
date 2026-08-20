import { Link } from 'react-router-dom';

import AcervoDoLocal from '../components/AcervoDoLocal';
import AvisoSemSerie from '../components/AvisoSemSerie';
import CardEspecie from '../components/CardEspecie';
import DatasetCard from '../components/DatasetCard';
import FichaDoLocal from '../components/FichaDoLocal';
import ImagemRecife from '../components/ImagemRecife';
import PainelPredicao from '../components/PainelPredicao';
import SectionTitle from '../components/SectionTitle';
import SerieAmbiental from '../components/SerieAmbiental';
import {
  formatarData,
  formatarLatitudeCurta,
  formatarLocal,
  formatarQuantidadeEspecies,
} from '../utils/formatters';
import { ROTAS_APP } from '../utils/navigation';

/**
 * A linha mono do topo: onde fica, e de quando é o que a página vai dizer.
 *
 * ⚠️ A data é a da última atualização do **cadastro**, e não a data-base da
 * previsão — as duas aparecem na mesma tela e não podem trocar de lugar. A
 * data-base fica junto do número que ela data, dentro do painel.
 */
function metaDoLocal(recife) {
  return [
    formatarLatitudeCurta(recife.latitude),
    recife.estado,
    recife.ultima_atualizacao ? `atualizado ${formatarData(recife.ultima_atualizacao)}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

export default function LocalRecifePage({
  recife,
  siteOffline,
  offlineMessage,
  onOpenEspecie,
  usuario,
  carregandoDetalhe = false,
  erroDetalhe = false,
  datasetsRelacionados = [],
  carregandoDatasetsRelacionados = false,
  erroDatasetsRelacionados = false,
  usandoFallbackDatasets = false,
}) {
  const especiesAssociadas = recife.especies || [];

  // Um recife sem coordenada nao tem serie, e sem serie nao tem previsao nem
  // dataset. Em vez de tres blocos vazios com tres frases diferentes, uma
  // explicacao no lugar dos dois primeiros. Ver AvisoSemSerie.
  const motivoSemSerie = recife.motivo_sem_serie || null;

  return (
    <>
      {/* O chrome escuro carrega a identidade do lugar; a areia abaixo carrega
          os dados. É a mesma divisão da home, e ela é o que permite ao título
          ser grande sem competir com nenhum número. */}
      <header className="bg-ocean-deep text-white">
        <div className="faixa py-6">
          <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 pb-6">
            <Link
              to={ROTAS_APP.recifes}
              className="text-sm text-white/70 transition hover:text-white"
            >
              ← Localizacoes
            </Link>
            <span className="rotulo-mono text-white/50">{metaDoLocal(recife)}</span>
          </div>

          <div className="grid items-end gap-8 lg:grid-cols-[1.25fr_1fr] lg:gap-12">
            <div>
              <h1 className="font-serif text-[38px] font-normal leading-[1.05] tracking-[-0.025em] sm:text-[46px] lg:text-[50px]">
                {recife.nome}
              </h1>
              <p className="mt-3.5 max-w-[60ch] text-base leading-relaxed text-white/70">
                {recife.descricao}
              </p>
            </div>

            <p className="font-mono text-2xs leading-relaxed text-white/50 lg:pb-2">
              {formatarLocal(recife)}
              <br />
              {formatarQuantidadeEspecies(
                recife.quantidade_especies || especiesAssociadas.length || 0,
              )}
            </p>
          </div>
        </div>
      </header>

      <section className="faixa flex flex-col gap-14 py-12">
        {carregandoDetalhe && (
          <p className="font-mono text-2xs text-ocean-deep/50">
            Atualizando os dados mais recentes desta localizacao...
          </p>
        )}

        {erroDetalhe && !carregandoDetalhe && (
          <div className="bloco-procedencia text-sm leading-relaxed text-ocean-deep/80">
            Nao foi possivel atualizar este detalhe agora. Exibindo os dados disponiveis na
            aplicacao.
          </div>
        )}

        {siteOffline && (
          <div className="bloco-procedencia text-sm leading-relaxed text-ocean-deep/80">
            <strong className="text-terra-dark">Modo manutencao:</strong>{' '}
            {offlineMessage || 'Exibindo dados locais de referencia.'}
          </div>
        )}

        {recife.imagem_url && (
          <div className="superficie overflow-hidden">
            <ImagemRecife
              nome={recife.nome}
              imagem={recife.imagem_url}
              credito={recife.credito_imagem}
              fonteUrl={recife.fonte_imagem_url}
              localCaptura={recife.local_captura_foto}
              className="h-64 w-full object-cover sm:h-80"
            />
          </div>
        )}

        {motivoSemSerie ? (
          <section className="space-y-5">
            <SectionTitle
              titulo="Previsao e serie medida"
              descricao={`Nao ha serie de satelite para ${recife.nome}, e por isso nao ha previsao de estresse termico.`}
            />

            <AvisoSemSerie motivo={motivoSemSerie} />
          </section>
        ) : (
          <>
            <section className="space-y-5">
              {/* ⚠️ O título da seção **não** repete "Degrau de hoje": esse é o
                  rótulo dentro do painel, a dois centímetros daqui, e o eco
                  faria a página parecer dizer a mesma coisa duas vezes com
                  tamanhos diferentes. Aqui o título nomeia o que se prevê; lá
                  dentro, o rótulo nomeia o valor de hoje. */}
              <SectionTitle
                titulo="Previsao de estresse termico"
                descricao={`Probabilidade de alerta termico em ${recife.nome} nos proximos 7 dias, calculada a partir da serie do satelite.`}
              />

              {/* O proprio painel decide o que mostrar em cada estado — inclusive
                  quando falta dado. O portao anterior exigia sete campos do modelo
                  legado, dois deles de variaveis que o projeto nem coleta (`par` e
                  `kd490`), e por isso nunca liberava com dado real. Aquela funcao
                  (`possuiPainelCompleto`) foi removida em 28/07/2026 junto com o
                  resto da camada legada. */}
              <PainelPredicao slug={recife.slug} publicOffline={siteOffline} />
            </section>

            <section className="space-y-5">
              <SectionTitle
                titulo="A serie medida"
                descricao={`O que o satelite registrou em ${recife.nome}, com a proveniencia de cada valor. E a entrada da previsao acima — nao a previsao.`}
              />

              <SerieAmbiental slug={recife.slug} publicOffline={siteOffline} usuario={usuario} />
            </section>

            {/* 🚨 O grafico acima mostra duas variaveis; o projeto guarda oito
                deste recife. Ate 12/08/2026 as outras seis nao apareciam em
                numero nenhum do site. Ver AcervoDoLocal. */}
            <section className="space-y-5">
              <SectionTitle
                titulo="Tudo o que o projeto mede aqui"
                descricao={`Todas as variaveis ingeridas para ${recife.nome}, e nao so as que a previsao usa. O CSV da serie acima baixa todas elas.`}
              />

              <AcervoDoLocal acervo={recife.acervo} />
            </section>
          </>
        )}

        {/* ⚠️ A ficha descreve **o lugar** e continua valendo mesmo quando nao
            ha serie nenhuma — nos locais sem coordenada ela e, junto com o
            aviso, a unica coisa concreta que a pagina tem a dizer. */}
        <section className="space-y-5">
          <SectionTitle
            titulo="Ficha do local"
            descricao={`O que esta cadastrado sobre ${recife.nome} como lugar, com a origem das coordenadas.`}
          />

          <FichaDoLocal local={recife} />
        </section>

        <section className="space-y-5">
          <SectionTitle
            titulo="Especies associadas"
            descricao={`Especies vinculadas a ${recife.nome} na camada biologica da plataforma.`}
            meta={`${especiesAssociadas.length} registro(s) · credito na propria imagem`}
          />

          {especiesAssociadas.length > 0 ? (
            <div className="grid gap-7 sm:grid-cols-2 lg:grid-cols-3">
              {especiesAssociadas.map((especie) => (
                <CardEspecie key={especie.id} especie={especie} onOpen={onOpenEspecie} />
              ))}
            </div>
          ) : (
            <p className="superficie px-6 py-10 text-center text-sm text-ocean-deep/55">
              Nenhuma especie foi associada a esta localizacao ainda no painel administrativo.
            </p>
          )}
        </section>

        <section className="space-y-5">
          <SectionTitle
            titulo="Datasets relacionados"
            descricao={`Datasets do catalogo geral que fazem referencia direta a ${recife.nome}.`}
          />

          {erroDatasetsRelacionados && (
            <div className="bloco-procedencia text-sm leading-relaxed text-ocean-deep/80">
              Nao foi possivel atualizar os datasets relacionados por API agora.
              {usandoFallbackDatasets
                ? ' Exibindo uma referencia local transitoria quando disponivel.'
                : ''}
            </div>
          )}

          {carregandoDatasetsRelacionados && datasetsRelacionados.length === 0 ? (
            <p className="superficie px-6 py-10 text-center text-sm text-ocean-deep/55">
              Carregando datasets relacionados desta localizacao...
            </p>
          ) : datasetsRelacionados.length > 0 ? (
            // A mesma linha do catálogo, e não um cartão paralelo: um dataset
            // descrito de duas formas em duas telas é a receita para as duas
            // divergirem — foi assim que "Arquivo:" e período da API chegaram a
            // significar a mesma coisa numa delas.
            <div className="superficie overflow-hidden">
              {datasetsRelacionados.map((dataset) => (
                <DatasetCard key={dataset.id} item={dataset} compact usuario={usuario} />
              ))}
            </div>
          ) : (
            <p className="superficie px-6 py-10 text-center text-sm text-ocean-deep/55">
              {erroDatasetsRelacionados
                ? 'Nao foi possivel carregar datasets relacionados no momento e nenhuma referencia local estava disponivel.'
                : motivoSemSerie
                  ? // ⚠️ "Ainda nao ha" promete que um dia havera, e aqui isso
                    // seria falso: sem coordenada nao ha ingestao, e sem ingestao
                    // o catalogo nao tem o que registrar. O motivo ja esta dito
                    // por extenso acima, entao esta linha so faz a ligacao.
                    'Sem serie ingerida nao ha dataset a oferecer para esta localizacao - ver o motivo acima.'
                  : 'Ainda nao ha datasets relacionados diretamente a esta localizacao.'}
            </p>
          )}
        </section>
      </section>
    </>
  );
}
