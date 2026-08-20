import { AlertTriangle, Download, ExternalLink, Lock } from 'lucide-react';
import { Link } from 'react-router-dom';

import { formatarLocal, formatarPeriodo } from '../utils/formatters';
import { ROTAS_APP } from '../utils/navigation';
import { formatarDataBr } from '../utils/painelRisco';

/**
 * Uma entrada do catálogo, como **linha de tabela** (desenho 3a).
 *
 * A linha tem dois andares e os dois são obrigatórios:
 *
 * - **em cima**, as seis colunas comparáveis — conjunto, tipo, formato,
 *   período, tamanho, disponibilidade;
 * - **embaixo**, a proveniência por extenso: resumo, quantas medições a API
 *   confirma, entre que datas, e o link que devolve esse número.
 *
 * 🚨 **O segundo andar não é detalhe opcional.** Medido em 27/07/2026: a página
 * anunciava nove datasets e a API servia três. pH, clorofila, nitrato, thetao,
 * KD490 e o SST do Met Office apareciam com título, formato e período sem uma
 * única medição no banco — e nada na tela distinguia um caso do outro. Uma
 * tabela de seis colunas bonitas repetiria o defeito com mais elegância.
 */

// ⚠️ Declarado uma vez e usado pelo cabeçalho da lista (`ListaDatasets`) e pela
// linha. Duas declarações desalinham em silêncio na primeira edição.
export const COLUNAS_DATASET =
  'md:[grid-template-columns:minmax(0,2.2fr)_120px_88px_minmax(0,150px)_84px_150px]';

/**
 * Diz se o projeto **tem** este dado, ou apenas aponta para ele.
 *
 * ⚠️ Os tres estados sao diferentes e nenhum pode virar os outros:
 *
 * | Estado | Significa |
 * |---|---|
 * | disponivel | o projeto serve este dado, com o link que prova |
 * | referencia externa | existe no provedor; o projeto nao espelha |
 * | nao verificado | o servidor nao informou (catalogo antigo ou fallback) |
 */
function estadoDaCobertura(cobertura) {
  if (!cobertura) {
    return { rotulo: 'Disponibilidade nao verificada', cor: 'text-ocean-deep/45' };
  }
  if (!cobertura.espelhado || cobertura.nMedicoes === 0) {
    return { rotulo: 'Referencia externa', cor: 'text-ocean-deep/60' };
  }
  return { rotulo: 'Disponivel nesta API', cor: 'text-emerald-700' };
}

function DetalheDaCobertura({ cobertura }) {
  if (!cobertura) {
    return (
      <span className="text-ocean-deep/50">
        O servidor nao informou a cobertura deste conjunto.
      </span>
    );
  }

  if (!cobertura.espelhado || cobertura.nMedicoes === 0) {
    return (
      <span className="text-ocean-deep/60">
        O conjunto existe na fonte original. Este projeto{' '}
        <strong className="font-semibold text-ocean-deep">nao o serve pela API</strong>.
      </span>
    );
  }

  return (
    <span className="text-ocean-deep/70">
      {cobertura.nMedicoes.toLocaleString('pt-BR')} medicoes de{' '}
      {formatarDataBr(cobertura.dataInicio)} a {formatarDataBr(cobertura.dataFim)}
      {cobertura.variaveis.length > 0 ? ` (${cobertura.variaveis.join(', ')})` : ''}.
      {cobertura.consulta && (
        <>
          {' '}
          {/* O recibo do numero acima. Sem ele, "14.346 medicoes" e uma
              afirmacao que ninguem consegue conferir. */}
          <a
            href={cobertura.consulta}
            className="inline-flex items-center gap-1 font-semibold text-ocean-dark underline"
          >
            Conferir na API
            <ExternalLink size={11} />
          </a>
        </>
      )}
    </span>
  );
}

/**
 * O fim da linha: baixar, pedir login, ou dizer que nao da.
 *
 * 🚨 **Os tres estados existem porque o catalogo passou a ter dois tipos de
 * link.** Ate 12/08/2026 todo `url_download` apontava para o provedor (NOAA,
 * Copernicus) e um `<a>` simples bastava. Desde que os locais novos entraram,
 * metade dos itens aponta para `/api/medicoes/?formato=csv` — o proprio banco
 * deste projeto —, e esse endpoint **exige conta aprovada**.
 *
 * ⚠️ Sem o estado do meio, o visitante deslogado clicaria em "Baixar conjunto"
 * e receberia um JSON de 401 aberto no navegador.
 *
 * A permissao **nao e adivinhada pela URL**: vem de `download_exige_conta`, que
 * o servidor deriva da mesma regra que a view aplica. Ver
 * `models.DatasetCatalogo.download_exige_conta`.
 */
function AcaoDeDownload({ item, usuario }) {
  if (!item.downloadUrl) {
    return (
      <span className="inline-flex items-center gap-1.5 font-semibold text-terra-dark">
        <AlertTriangle size={13} />
        Download indisponivel no momento
      </span>
    );
  }

  const liberado =
    !item.exigeContaAprovada || usuario?.aprovado === true || usuario?.master === true;

  if (!liberado) {
    return (
      <Link
        to={ROTAS_APP.login}
        className="inline-flex items-center gap-1.5 border-b border-ocean-deep/25 pb-0.5 font-semibold text-ocean-deep transition hover:border-terra"
      >
        <Lock size={13} />
        Faca login e aguarde aprovacao para baixar
      </Link>
    );
  }

  return (
    <a
      href={item.downloadUrl}
      className="inline-flex items-center gap-1.5 border-b-2 border-terra pb-0.5 font-semibold text-ocean-deep transition hover:text-ocean-dark"
    >
      <Download size={13} />
      Baixar conjunto
    </a>
  );
}

export default function DatasetCard({ item, compact = false, usuario = null }) {
  const cobertura = estadoDaCobertura(item.cobertura);

  // ⚠️ Metade do catalogo descreve **arquivo** e a outra metade descreve
  // **serie no banco** (ver `inventario_datasets.py`). As colunas de arquivo so
  // se preenchem quando ha arquivo: numa serie elas sairiam como "Nao
  // informado", duas palavras que se leem como falta de cadastro quando na
  // verdade nao ha arquivo nenhum a descrever. O periodo e o volume da serie
  // vem do segundo andar, derivados do banco.
  const temArquivo = Boolean(item.dataInicio || item.dataFim || item.dataPublicacao);

  return (
    <article
      className={`grid grid-cols-1 items-start gap-x-4 gap-y-2 border-b border-ocean-deep/8 px-5 sm:px-6 ${COLUNAS_DATASET} ${
        compact ? 'py-3.5' : 'py-4'
      }`}
    >
      <div className="min-w-0">
        <p className="font-serif text-[19px] font-normal leading-tight tracking-[-0.01em] text-ocean-deep">
          {item.titulo}
        </p>
        <p className="mt-1 font-mono text-3xs tracking-[0.06em] text-ocean-deep/50">
          {item.fonte} · {item.localizacao}
        </p>
      </div>

      <span className="text-[13px] text-ocean-deep/70">{item.tipoDado}</span>
      <span className="font-mono text-2xs text-ocean-deep/70">{item.formato}</span>
      <span className="font-mono text-2xs text-ocean-deep/60">
        {/* ⚠️ Este periodo e o do ARQUIVO inventariado, nao o da API. Sao coisas
            diferentes, e apresentar so um deles como "o periodo do dataset" foi
            exatamente o defeito corrigido em 27/07/2026 — por isso o rotulo
            viaja junto com o valor, e nao so no cabecalho da coluna. */}
        {temArquivo ? `Arquivo: ${formatarPeriodo(item)}` : '—'}
      </span>
      <span className="font-mono text-2xs text-ocean-deep/70">
        {temArquivo ? item.tamanho : '—'}
      </span>
      <span className={`text-[12.5px] font-semibold ${cobertura.cor}`}>{cobertura.rotulo}</span>

      <div className="mt-1 md:col-span-6">
        {/* ⚠️ O resumo é aparado em duas linhas e a proveniência **não**. Alguns
            resumos do catálogo trazem parágrafo inteiro com URL da fonte
            dentro, e um deles solto na linha empurra a cobertura para fora do
            campo de visão — que é justamente o dado pelo qual esta tabela
            existe. Prosa descritiva cabe em duas linhas; medição não se corta. */}
        <p className="line-clamp-2 text-2xs leading-relaxed text-ocean-deep/60">{item.resumo}</p>
        <div className="mt-1.5 flex flex-wrap items-baseline gap-x-4 gap-y-1.5 text-2xs leading-relaxed">
          <span className="font-mono text-ocean-deep/45">{formatarLocal(item)}</span>
          <DetalheDaCobertura cobertura={item.cobertura} />
          <AcaoDeDownload item={item} usuario={usuario} />
        </div>
      </div>
    </article>
  );
}
