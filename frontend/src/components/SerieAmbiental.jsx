import { Download, Lock } from 'lucide-react';
import { Suspense, lazy, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ROTAS_APP } from '../utils/navigation';
import {
  DIAS_EXIBIDOS,
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
// 🚨 **O Plotly entra por `lazy`, e nao no bundle principal.** Ele custa
// ~354 kB gzip — mais que triplicava o `main.js` do site inteiro — e so e
// usado aqui, na pagina de um recife. Importado no topo, a home e a lista de
// especies pagariam por um grafico que nao desenham.
const GraficoSerieInterativo = lazy(() => import('./GraficoSerieInterativo'));

function Estado({ children, tom = 'neutro' }) {
  if (tom === 'aviso') {
    return (
      <div className="bloco-procedencia text-sm leading-relaxed text-ocean-deep/80">
        {children}
      </div>
    );
  }

  return (
    <p className="superficie px-6 py-8 text-center text-sm text-ocean-deep/55">{children}</p>
  );
}

export default function SerieAmbiental({ slug, publicOffline = false, usuario }) {
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
    return <Estado>Carregando a serie medida deste recife...</Estado>;
  }

  if (resultado.estado === 'offline') {
    return <Estado tom="aviso">A serie nao e exibida em modo manutencao.</Estado>;
  }

  if (resultado.estado === 'sem-serie') {
    return <Estado>Ainda nao ha medicoes ingeridas para este recife no periodo exibido.</Estado>;
  }

  if (resultado.estado !== 'ok') {
    return <Estado tom="aviso">Nao foi possivel carregar a serie agora.</Estado>;
  }

  const { series, periodo, fontes, total, reprovadas, truncada, alertas = [] } = resultado;

  return (
    <div className="space-y-5">
      <p className="max-w-[82ch] text-[15px] leading-relaxed text-ocean-deep/70">
        <strong className="font-semibold text-ocean-deep">Isto e medicao, nao previsao.</strong>{' '}
        Sao os valores que o satelite registrou neste recife nos ultimos {DIAS_EXIBIDOS} dias. A
        probabilidade de alerta que aparece acima e o que o modelo <em>calcula</em> a partir
        deles.
      </p>

      <p className="max-w-[82ch] font-mono text-2xs leading-relaxed text-ocean-deep/60">
        Passe o cursor para ler as quatro variaveis na mesma data; arraste para dar zoom, e
        clique duas vezes para voltar. Falha na linha e medida reprovada pela validacao
        fisica — nao e zero.
      </p>

      <Suspense fallback={<Estado>Carregando o grafico...</Estado>}>
        <GraficoSerieInterativo series={series} alertas={alertas} />
      </Suspense>

      {/* A faixa rosa so ganha legenda quando existe faixa: explicar uma cor
          que nao esta na tela e ruido, e some junto com ela. */}
      {alertas.length > 0 && (
        <p className="flex items-start gap-2 font-mono text-2xs leading-relaxed text-ocean-deep/70">
          <span
            aria-hidden="true"
            className="mt-0.5 inline-block h-3 w-6 shrink-0 rounded-sm"
            style={{ backgroundColor: 'rgba(212,112,70,0.18)' }}
          />
          <span>
            As faixas marcam os dias em que a NOAA manteve alerta termico neste recife
            (<span className="whitespace-nowrap">BAA ≥ 3</span>) — o que{' '}
            <strong className="font-semibold">aconteceu</strong>, medido, e nao o que o modelo
            previu.
          </span>
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-ocean-deep/12 pt-4">
        <span className="font-mono text-2xs leading-relaxed text-ocean-deep/60">
          {total.toLocaleString('pt-BR')} medicoes
          {periodo && ` de ${periodo.inicio} a ${periodo.fim}`}
          {fontes.length > 0 && ` — fonte: ${fontes.join(', ')}`}
          {reprovadas > 0 && ` — ${reprovadas} reprovada(s) na validacao fisica`}
        </span>

        {/* O download existe para o site ser citavel. Sai com as colunas de
            proveniencia junto, e cobre a serie inteira do recife — nao so o
            periodo desenhado acima.

            ⚠️ O mecanismo do link **nao muda** quando aprovado: e sessao do
            Django, e o cookie viaja sozinho no clique do `<a>` — nada de
            fetch+blob, que so seria necessario com token em cabecalho. */}
        {usuario?.aprovado || usuario?.master ? (
          <a
            href={urlDeDownload(slug)}
            className="inline-flex items-center gap-2 border-b-2 border-terra pb-0.5 text-[13px] font-semibold text-ocean-deep transition hover:text-ocean-dark"
            download
          >
            <Download size={14} />
            Baixar a serie completa (CSV)
          </a>
        ) : (
          <Link
            to={ROTAS_APP.login}
            className="inline-flex items-center gap-2 border-b-2 border-ocean-deep/20 pb-0.5 text-[13px] font-semibold text-ocean-deep transition hover:border-terra"
          >
            <Lock size={14} />
            Faca login e aguarde aprovacao para baixar
          </Link>
        )}
      </div>

      {truncada && (
        // 🚨 Sem este aviso o grafico desenharia PARTE do recorte pedido
        // anunciando o recorte inteiro, e a curva nao denunciaria nada.
        <p className="bloco-procedencia text-2xs leading-relaxed text-ocean-deep/75">
          O periodo pedido tem mais pontos do que uma pagina da API devolve. O grafico mostra os
          mais recentes; o CSV traz tudo.
        </p>
      )}
    </div>
  );
}
