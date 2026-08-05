import { Download } from 'lucide-react';
import { useEffect, useState } from 'react';

import GraficoSerie from './GraficoSerie';
import {
  CORTE_ALERTA_DHW,
  DIAS_EXIBIDOS,
  ROTULOS,
  VARIAVEIS_DA_SERIE,
  buscarSerie,
  urlDeDownload,
} from '../utils/serie';

/**
 * A serie ambiental do recife — o dado que o projeto guarda, na tela.
 *
 * 🚨 **Ate 31/07/2026 este componente nao existia, e a lacuna era grande.** O
 * endpoint `/api/medicoes/` servia 57.426 medicoes com proveniencia por valor
 * desde 27/07, e **nenhuma tela do site o chamava**. Um site que se apresenta
 * como banco de dados de corais mostrava a previsao e escondia a serie de onde
 * ela sai.
 *
 * ⚠️ **Isto e observacao, nao previsao.** O painel logo acima fala do futuro e
 * sai do modelo; este bloco fala do passado e sai do satelite. A distincao esta
 * escrita na tela, e nao so aqui no comentario, porque foi ela que as figuras
 * do TCC precisaram tornar explicita para o publico.
 */
const CORES = { sst: '#0369a1', dhw: '#c2410c' };

export default function SerieAmbiental({ slug, publicOffline = false }) {
  const [resultado, setResultado] = useState({ estado: 'carregando' });

  useEffect(() => {
    let ativo = true;

    if (publicOffline) {
      setResultado({ estado: 'offline' });
      return undefined;
    }

    setResultado({ estado: 'carregando' });
    buscarSerie(slug).then((resposta) => {
      if (ativo) {
        setResultado(resposta);
      }
    });

    return () => {
      ativo = false;
    };
  }, [slug, publicOffline]);

  if (resultado.estado === 'carregando') {
    return (
      <div className="rounded-2xl border border-sand-dark/20 bg-white p-6 text-sm text-gray-600">
        Carregando a serie medida deste recife...
      </div>
    );
  }

  if (resultado.estado === 'offline') {
    return (
      <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
        A serie nao e exibida em modo manutencao.
      </div>
    );
  }

  if (resultado.estado === 'sem-serie') {
    return (
      <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-6 text-center text-sm text-gray-500">
        Ainda nao ha medicoes ingeridas para este recife no periodo exibido.
      </div>
    );
  }

  if (resultado.estado !== 'ok') {
    return (
      <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
        Nao foi possivel carregar a serie agora.
      </div>
    );
  }

  const { series, periodo, fontes, total, reprovadas, truncada } = resultado;

  return (
    <div className="space-y-3">
      <p className="rounded-xl border border-ocean-light/30 bg-ocean-light/5 p-3 text-sm text-ocean-dark">
        <strong>Isto e medicao, nao previsao.</strong> Sao os valores que o
        satelite registrou neste recife nos ultimos {DIAS_EXIBIDOS} dias. A
        probabilidade de alerta que aparece acima e o que o modelo{' '}
        <em>calcula</em> a partir deles.
      </p>

      <div className="grid gap-3 lg:grid-cols-2">
        {VARIAVEIS_DA_SERIE.map((variavel) => {
          const rotulo = ROTULOS[variavel];
          return (
            <GraficoSerie
              key={variavel}
              pontos={series[variavel] || []}
              rotulo={rotulo.nome}
              unidade={rotulo.unidade}
              casas={rotulo.casas}
              cor={CORES[variavel]}
              linhaDeCorte={variavel === 'dhw' ? CORTE_ALERTA_DHW : null}
              rotuloDoCorte={
                variavel === 'dhw' ? 'Alerta Nivel 1 da NOAA (DHW 4)' : null
              }
            />
          );
        })}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sand-dark/20 bg-white p-3 text-xs text-gray-600">
        <span>
          {total.toLocaleString('pt-BR')} medicoes
          {periodo && ` de ${periodo.inicio} a ${periodo.fim}`}
          {fontes.length > 0 && ` — fonte: ${fontes.join(', ')}`}
          {reprovadas > 0 && ` — ${reprovadas} reprovada(s) na validacao fisica`}
        </span>

        {/* O download existe para o site ser citavel. Sai com as colunas de
            proveniencia junto, e cobre a serie inteira do recife — nao so o
            periodo desenhado acima. */}
        <a
          href={urlDeDownload(slug)}
          className="inline-flex items-center gap-2 rounded-full bg-ocean-dark px-3 py-1.5 font-semibold text-white transition hover:bg-ocean-light"
          download
        >
          <Download size={14} />
          Baixar a serie completa (CSV)
        </a>
      </div>

      {truncada && (
        // 🚨 Sem este aviso o grafico desenharia PARTE do recorte pedido
        // anunciando o recorte inteiro, e a curva nao denunciaria nada.
        <p className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
          O periodo pedido tem mais pontos do que uma pagina da API devolve. O
          grafico mostra os mais recentes; o CSV traz tudo.
        </p>
      )}
    </div>
  );
}
