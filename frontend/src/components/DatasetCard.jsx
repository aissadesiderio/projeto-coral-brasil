import {
  AlertTriangle,
  CalendarRange,
  Database,
  Download,
  ExternalLink,
  HelpCircle,
  Lock,
  MapPin,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { formatarLocal, formatarPeriodo } from '../utils/formatters';
import { ROTAS_APP } from '../utils/navigation';
import { formatarDataBr } from '../utils/painelRisco';

/**
 * Diz se o projeto **tem** este dado, ou apenas aponta para ele.
 *
 * 🚨 Medido em 27/07/2026: a pagina anunciava nove datasets e a API servia
 * tres. pH, clorofila, nitrato, thetao, KD490 e o SST do Met Office apareciam
 * com titulo, formato e periodo sem uma unica medicao no banco — e nada na
 * tela distinguia um caso do outro.
 *
 * ⚠️ Os tres estados sao diferentes e nenhum pode virar os outros:
 *
 * | Estado | Significa |
 * |---|---|
 * | disponivel | o projeto serve este dado, com o link que prova |
 * | referencia externa | existe no provedor; o projeto nao espelha |
 * | nao verificado | o servidor nao informou (catalogo antigo ou fallback) |
 */
function Cobertura({ cobertura }) {
  if (!cobertura) {
    return (
      <p className="inline-flex items-center gap-2 text-sm text-slate-500">
        <HelpCircle size={15} />
        Disponibilidade nao verificada
      </p>
    );
  }

  if (!cobertura.espelhado || cobertura.nMedicoes === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <p className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
          <ExternalLink size={15} />
          Referencia externa
        </p>
        <p className="mt-1 text-xs leading-relaxed text-slate-600">
          O conjunto existe na fonte original. Este projeto{' '}
          <strong>nao o serve pela API</strong>.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
      <p className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-800">
        <Database size={15} />
        Disponivel nesta API
      </p>
      <p className="mt-1 text-xs leading-relaxed text-emerald-900">
        {cobertura.nMedicoes.toLocaleString('pt-BR')} medicoes de{' '}
        {formatarDataBr(cobertura.dataInicio)} a{' '}
        {formatarDataBr(cobertura.dataFim)}
        {cobertura.variaveis.length > 0
          ? ` (${cobertura.variaveis.join(', ')})`
          : ''}
        .
      </p>
      {cobertura.consulta && (
        // O recibo do numero acima. Sem ele, "14.346 medicoes" e uma
        // afirmacao que ninguem consegue conferir.
        <a
          href={cobertura.consulta}
          className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-800 underline"
        >
          Conferir na API
          <ExternalLink size={12} />
        </a>
      )}
    </div>
  );
}

/**
 * O rodape do cartao: baixar, pedir login, ou dizer que nao da.
 *
 * 🚨 **Os tres estados existem porque o catalogo passou a ter dois tipos de
 * link.** Ate 12/08/2026 todo `url_download` apontava para o provedor (NOAA,
 * Copernicus) e um `<a>` simples bastava. Desde que os locais novos entraram,
 * metade dos itens aponta para `/api/medicoes/?formato=csv` — o proprio banco
 * deste projeto —, e esse endpoint **exige conta aprovada**.
 *
 * ⚠️ Sem o estado do meio, o visitante deslogado clicaria em "Baixar conjunto"
 * e receberia um JSON de 401 aberto no navegador. `SerieAmbiental` ja tinha
 * resolvido isso do lado do recife, trocando o botao por um convite ao login;
 * o cartao do catalogo faz o mesmo, com a mesma redacao.
 *
 * A permissao **nao e adivinhada pela URL**: vem de `download_exige_conta`, que
 * o servidor deriva da mesma regra que a view aplica. Ver
 * `models.DatasetCatalogo.download_exige_conta`.
 */
function AcaoDeDownload({ item, usuario }) {
  if (!item.downloadUrl) {
    return (
      <span className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900 sm:w-auto">
        <AlertTriangle size={16} />
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
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-ocean-dark/30 px-4 py-2 text-sm font-semibold text-ocean-dark transition hover:bg-ocean-dark hover:text-white sm:w-auto"
      >
        <Lock size={16} />
        Faca login e aguarde aprovacao para baixar
      </Link>
    );
  }

  return (
    <a
      href={item.downloadUrl}
      className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-ocean-dark px-4 py-2 text-sm font-semibold text-white transition hover:bg-ocean-light sm:w-auto"
    >
      <Download size={16} />
      Baixar conjunto
    </a>
  );
}

export default function DatasetCard({ item, compact = false, usuario = null }) {
  const padding = compact ? 'p-4' : 'p-5';

  // ⚠️ Metade do catalogo descreve **arquivo** e a outra metade descreve
  // **serie no banco** (ver `inventario_datasets.py`). As linhas de arquivo so
  // aparecem quando ha arquivo: numa serie elas sairiam como "Arquivo: Nao
  // informado / Tamanho: Nao informado", tres palavras que se leem como falta
  // de cadastro quando na verdade nao ha arquivo nenhum a descrever. O periodo
  // e o volume da serie ja vem logo abaixo, no bloco de cobertura, derivados
  // do banco.
  const temArquivo = Boolean(item.dataInicio || item.dataFim || item.dataPublicacao);

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
        {temArquivo && (
          <>
            <p className="inline-flex items-center gap-2">
              <CalendarRange size={15} />
              {/* ⚠️ Este periodo e o do ARQUIVO inventariado, nao o da API. Sao
                  coisas diferentes, e apresentar so um deles como "o periodo do
                  dataset" foi exatamente o defeito corrigido em 27/07/2026. */}
              Arquivo: {formatarPeriodo(item)}
            </p>
            <p>
              <strong>Tamanho:</strong> {item.tamanho}
            </p>
          </>
        )}
      </div>

      <div className="mt-4">
        <Cobertura cobertura={item.cobertura} />
      </div>

      <div className="mt-5 flex flex-1 items-end">
        <AcaoDeDownload item={item} usuario={usuario} />
      </div>
    </article>
  );
}
