import { useEffect, useState } from 'react';
import { Fish } from 'lucide-react';
import { Link } from 'react-router-dom';

import { buscarJson, enviarFormulario } from '../utils/api';
import { ROTAS_APP } from '../utils/navigation';

const CAMPOS_VAZIOS = {
  nome_cientifico: '',
  nome_comum: '',
  tipo: 'CORAL',
  descricao: '',
  credito_imagem: '',
  fonte_imagem_url: '',
  local_captura_foto: '',
  fonte_url: '',
};

const TIPOS = [
  ['CORAL', 'Coral'],
  ['PEIXE', 'Peixe'],
  ['INVERTEBRADO', 'Invertebrado'],
  ['MAMIFERO', 'Mamifero'],
  ['OUTRO', 'Outro'],
];

// ⚠️ As colunas saem de uma constante só, como no resto das tabelas do 3a —
// cabeçalho e linha desalinham em silêncio quando cada um declara as suas.
const COLUNAS_TABELA =
  'md:[grid-template-columns:64px_minmax(0,1fr)_200px_150px_130px]';

function Rotulo({ children }) {
  return <span className="rotulo-mono mb-1.5 block text-ocean-deep/50">{children}</span>;
}

function mensagemDeErro(resposta) {
  if (!resposta.dados) {
    return 'Nao foi possivel completar a acao.';
  }
  if (resposta.dados.detail) {
    return resposta.dados.detail;
  }
  return Object.entries(resposta.dados)
    .map(([campo, erros]) => `${campo}: ${Array.isArray(erros) ? erros.join(' ') : erros}`)
    .join(' ');
}

export default function GerenciarEspeciesPage({ usuario }) {
  const [especies, setEspecies] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [formulario, setFormulario] = useState(CAMPOS_VAZIOS);
  const [editandoId, setEditandoId] = useState(null);
  const [mensagem, setMensagem] = useState(null);
  const [enviando, setEnviando] = useState(false);

  const podeContribuir = Boolean(usuario?.autenticado && (usuario.aprovado || usuario.master));

  useEffect(() => {
    if (!podeContribuir) {
      return;
    }

    let ativo = true;

    async function carregar() {
      setCarregando(true);
      const dados = await buscarJson('/api/especies/');
      if (ativo) {
        setEspecies(Array.isArray(dados) ? dados : []);
        setCarregando(false);
      }
    }

    carregar();

    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [podeContribuir]);

  if (!usuario?.autenticado) {
    return (
      <section className="faixa max-w-3xl py-14">
        <div className="superficie p-9 text-center">
          <p className="text-[15px] text-ocean-deep/75">
            Faca login para contribuir com o catalogo de especies.
          </p>
          <Link to={ROTAS_APP.login} className="botao-primario mx-auto mt-5">
            Entrar
          </Link>
        </div>
      </section>
    );
  }

  if (!podeContribuir) {
    return (
      <section className="faixa max-w-3xl py-14">
        <div className="bloco-procedencia text-center text-[15px] leading-relaxed text-ocean-deep/80">
          Sua conta ainda nao foi aprovada. Peca para um master aprovar antes de
          contribuir especie ou baixar dados.
        </div>
      </section>
    );
  }

  function iniciarEdicao(especie) {
    setEditandoId(especie.id);
    setFormulario({
      nome_cientifico: especie.nome_cientifico,
      nome_comum: especie.nome_comum || '',
      tipo: especie.tipo,
      descricao: especie.descricao || '',
      credito_imagem: especie.credito_imagem || '',
      fonte_imagem_url: especie.fonte_imagem_url || '',
      local_captura_foto: especie.local_captura_foto || '',
      fonte_url: especie.fonte_url || '',
    });
    setMensagem(null);
  }

  function cancelarEdicao() {
    setEditandoId(null);
    setFormulario(CAMPOS_VAZIOS);
  }

  async function recarregar() {
    const dados = await buscarJson('/api/especies/');
    setEspecies(Array.isArray(dados) ? dados : []);
  }

  async function enviar(event) {
    event.preventDefault();
    setEnviando(true);
    setMensagem(null);

    const url = editandoId ? `/api/especies/${editandoId}/` : '/api/especies/';
    const method = editandoId ? 'PATCH' : 'POST';
    const resposta = await enviarFormulario(url, { method, body: formulario });

    setEnviando(false);

    if (!resposta.ok) {
      setMensagem({ tipo: 'erro', texto: mensagemDeErro(resposta) });
      return;
    }

    if (resposta.status === 202) {
      setMensagem({
        tipo: 'info',
        texto: resposta.dados?.detail || 'Enviado para revisao de um master.',
      });
    } else {
      setMensagem({
        tipo: 'sucesso',
        texto: editandoId ? 'Especie atualizada.' : 'Especie criada.',
      });
      await recarregar();
    }
    cancelarEdicao();
  }

  async function excluir(especie) {
    if (!window.confirm(`Remover ${especie.nome_cientifico}?`)) {
      return;
    }

    const resposta = await enviarFormulario(`/api/especies/${especie.id}/`, { method: 'DELETE' });

    if (!resposta.ok) {
      setMensagem({ tipo: 'erro', texto: mensagemDeErro(resposta) });
      return;
    }

    if (resposta.status === 202) {
      setMensagem({
        tipo: 'info',
        texto: resposta.dados?.detail || 'Enviado para revisao de um master.',
      });
    } else {
      setMensagem({ tipo: 'sucesso', texto: 'Especie removida.' });
      await recarregar();
    }
  }

  const corMensagem = {
    erro: 'border-red-500 bg-red-50 text-red-800',
    sucesso: 'border-emerald-600 bg-emerald-50 text-emerald-900',
    info: 'border-terra bg-sand-aviso text-ocean-deep/80',
  };

  return (
    <section className="faixa py-12">
      <span className="olho-terra">Contribuicao · fila de revisao</span>
      <h1 className="mt-3.5 font-serif text-[36px] font-normal leading-[1.05] tracking-[-0.025em] text-ocean-deep sm:text-[44px]">
        Minhas especies
      </h1>
      <p className="mt-3 max-w-[68ch] text-base leading-relaxed text-ocean-deep/70">
        {usuario.master
          ? 'Como master, suas alteracoes aplicam na hora.'
          : 'Suas alteracoes ficam pendentes ate um master aprovar.'}{' '}
        Como as fotos hoje vem de terceiros, os campos de credito e licenca sao o que
        garante que a procedencia viaje junto com a imagem.
      </p>

      {mensagem && (
        <p
          className={`mt-6 rounded-lg border-l-[3px] p-4 text-sm leading-relaxed ${corMensagem[mensagem.tipo]}`}
        >
          {mensagem.texto}
        </p>
      )}

      <div className="superficie mt-7 p-7 sm:p-8">
        <p className="rotulo-mono border-b border-ocean-deep/15 pb-2.5 text-ocean-deep/55">
          {editandoId ? 'Editar especie' : 'Adicionar especie'}
        </p>

        <form onSubmit={enviar} className="mt-6 grid gap-x-8 gap-y-6 sm:grid-cols-2">
          <label className="block">
            <Rotulo>Nome cientifico</Rotulo>
            <input
              value={formulario.nome_cientifico}
              onChange={(event) =>
                setFormulario({ ...formulario, nome_cientifico: event.target.value })
              }
              className="campo-sublinhado"
              required
            />
          </label>

          <label className="block">
            <Rotulo>Nome comum</Rotulo>
            <input
              value={formulario.nome_comum}
              onChange={(event) => setFormulario({ ...formulario, nome_comum: event.target.value })}
              className="campo-sublinhado"
            />
          </label>

          <label className="block">
            <Rotulo>Tipo</Rotulo>
            <select
              value={formulario.tipo}
              onChange={(event) => setFormulario({ ...formulario, tipo: event.target.value })}
              className="campo-sublinhado"
            >
              {TIPOS.map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <Rotulo>Link com mais informacoes</Rotulo>
            <input
              type="url"
              value={formulario.fonte_url}
              onChange={(event) => setFormulario({ ...formulario, fonte_url: event.target.value })}
              className="campo-sublinhado"
            />
          </label>

          <label className="block sm:col-span-2">
            <Rotulo>Descricao</Rotulo>
            <textarea
              value={formulario.descricao}
              onChange={(event) => setFormulario({ ...formulario, descricao: event.target.value })}
              className="min-h-[5rem] w-full resize-y rounded-lg border border-ocean-deep/20 bg-transparent px-3 py-2.5 text-[15px] leading-relaxed text-ocean-deep outline-none transition focus:border-terra"
            />
          </label>

          {/* 🚨 Os campos de procedência ficam num bloco próprio, com o filete
              terra, e não misturados aos demais. Não é hierarquia visual por
              gosto: a correção de 11/08/2026 (docs/FONTES.md §2.1) achou nove
              espécies creditadas ao "Acervo local do projeto" sendo de
              terceiros, uma sem licença nenhuma. O que estava errado não era o
              dado — era o formulário tratar crédito como campo opcional entre
              outros. */}
          <div className="bloco-procedencia grid gap-x-6 gap-y-5 sm:col-span-2 sm:grid-cols-3">
            <div className="sm:col-span-3">
              <p className="rotulo-mono text-terra-dark">Procedencia da imagem</p>
              <p className="mt-1.5 text-[13px] leading-relaxed text-ocean-deep/65">
                Nenhuma foto do acervo proprio ainda: tudo vem de terceiros, e o credito precisa
                viajar junto com a imagem.
              </p>
            </div>

            <label className="block">
              <Rotulo>Credito da imagem</Rotulo>
              <input
                value={formulario.credito_imagem}
                onChange={(event) =>
                  setFormulario({ ...formulario, credito_imagem: event.target.value })
                }
                placeholder="ex.: nome do autor · CC BY-NC"
                className="campo-sublinhado"
              />
            </label>

            <label className="block">
              <Rotulo>Link da fonte da imagem</Rotulo>
              <input
                type="url"
                value={formulario.fonte_imagem_url}
                onChange={(event) =>
                  setFormulario({ ...formulario, fonte_imagem_url: event.target.value })
                }
                className="campo-sublinhado"
              />
            </label>

            <label className="block">
              <Rotulo>Local de captura da foto</Rotulo>
              <input
                value={formulario.local_captura_foto}
                onChange={(event) =>
                  setFormulario({ ...formulario, local_captura_foto: event.target.value })
                }
                placeholder="Onde a foto foi tirada, ex: Caravelas, BA"
                className="campo-sublinhado"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-3 sm:col-span-2">
            <button type="submit" disabled={enviando} className="botao-primario">
              {enviando ? 'Enviando...' : editandoId ? 'Salvar edicao' : 'Adicionar especie'}
            </button>

            {editandoId && (
              <button type="button" onClick={cancelarEdicao} className="botao-secundario">
                Cancelar
              </button>
            )}

            {!usuario.master && (
              <span className="text-[13px] text-ocean-deep/55">
                O registro entra como{' '}
                <strong className="font-semibold text-ocean-deep">pendente</strong> e so aparece
                na lista depois da aprovacao.
              </span>
            )}
          </div>

          {/* ⚠️ Categoria IUCN, taxonomia e foto ficam de fora deste
              formulario de proposito — sao campos que o projeto trata com
              cuidado de procedencia, e continuam so pelo Django admin. */}
        </form>
      </div>

      <div className="superficie mt-7 overflow-hidden">
        <div className={`hidden gap-x-5 px-5 sm:px-6 md:grid ${COLUNAS_TABELA} rotulo-mono cabecalho-tabela`}>
          <span>foto</span>
          <span>especie</span>
          <span>procedencia</span>
          <span>autoria</span>
          <span className="text-right">acoes</span>
        </div>

        {carregando && (
          <p className="px-6 py-10 text-center text-sm text-ocean-deep/55">
            Carregando especies...
          </p>
        )}

        {!carregando && especies.length === 0 && (
          <p className="px-6 py-10 text-center text-sm text-ocean-deep/55">
            Nenhuma especie cadastrada ainda.
          </p>
        )}

        {!carregando &&
          especies.map((especie) => (
            <div
              key={especie.id}
              className={`grid grid-cols-1 items-center gap-x-5 gap-y-2 border-b border-ocean-deep/8 px-5 py-3.5 last:border-b-0 sm:px-6 ${COLUNAS_TABELA}`}
            >
              <span className="flex h-12 w-16 items-center justify-center overflow-hidden rounded-md bg-sand-light">
                {especie.foto_url ? (
                  <img
                    src={especie.foto_url}
                    alt={especie.nome_comum || especie.nome_cientifico}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <Fish size={18} className="text-ocean-light" />
                )}
              </span>

              <div className="min-w-0">
                <p className="font-serif text-lg font-normal text-ocean-deep">
                  {especie.nome_comum || especie.nome_cientifico}
                </p>
                <p className="text-[13px] italic text-ocean-deep/60">{especie.nome_cientifico}</p>
              </div>

              {/* Sem crédito, a coluna diz que falta — não fica vazia. Coluna
                  vazia se lê como "não se aplica"; a frase se lê como pendência. */}
              <span className="font-mono text-3xs leading-relaxed text-ocean-deep/60">
                {especie.credito_imagem || 'sem credito registrado'}
                {especie.local_captura_foto && (
                  <>
                    <br />
                    {especie.local_captura_foto}
                  </>
                )}
              </span>

              <span className="font-mono text-3xs leading-relaxed text-ocean-deep/50">
                {usuario.master && especie.autor ? (
                  <>
                    criado por {especie.autor.criado_por || 'desconhecido'}
                    {especie.autor.editado_por && (
                      <>
                        <br />
                        editado por {especie.autor.editado_por}
                      </>
                    )}
                  </>
                ) : (
                  'publicada'
                )}
              </span>

              <div className="flex gap-4 text-[13px] font-semibold md:justify-end">
                <button
                  type="button"
                  onClick={() => iniciarEdicao(especie)}
                  className="text-ocean-dark transition hover:underline"
                >
                  Editar
                </button>
                <button
                  type="button"
                  onClick={() => excluir(especie)}
                  className="text-terra-dark transition hover:underline"
                >
                  Excluir
                </button>
              </div>
            </div>
          ))}
      </div>
    </section>
  );
}
