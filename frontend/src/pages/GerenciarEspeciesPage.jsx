import { useEffect, useState } from 'react';
import { Fish, Pencil, Plus, Trash2, X } from 'lucide-react';
import { Link } from 'react-router-dom';

import SectionTitle from '../components/SectionTitle';
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

const CAMPO_CLASSNAME =
  'w-full rounded-xl border border-sand-dark/30 px-4 py-3 text-sm outline-none transition focus:border-ocean-light';

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
      <section className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <div className="rounded-3xl border border-sand-dark/20 bg-white p-8 text-center shadow-sm">
          <p className="text-gray-700">Faca login para contribuir com o catalogo de especies.</p>
          <Link
            to={ROTAS_APP.login}
            className="mt-4 inline-block rounded-xl bg-ocean-dark px-4 py-2 font-semibold text-white"
          >
            Entrar
          </Link>
        </div>
      </section>
    );
  }

  if (!podeContribuir) {
    return (
      <section className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <div className="rounded-3xl border border-amber-300 bg-amber-50 p-8 text-center text-amber-900">
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
    erro: 'border-red-300 bg-red-50 text-red-800',
    sucesso: 'border-emerald-300 bg-emerald-50 text-emerald-800',
    info: 'border-sky-300 bg-sky-50 text-sky-800',
  };

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6">
      <SectionTitle
        titulo="Minhas especies"
        descricao={
          usuario.master
            ? 'Como master, suas alteracoes aplicam na hora.'
            : 'Suas alteracoes ficam pendentes ate um master aprovar.'
        }
      />

      {mensagem && (
        <div className={`rounded-2xl border p-4 text-sm ${corMensagem[mensagem.tipo]}`}>
          {mensagem.texto}
        </div>
      )}

      <form
        onSubmit={enviar}
        className="grid gap-4 rounded-3xl border border-sand-dark/20 bg-white p-5 shadow-sm sm:grid-cols-2"
      >
        <div className="sm:col-span-2">
          <h3 className="text-lg font-semibold text-ocean-dark">
            {editandoId ? 'Editar especie' : 'Adicionar especie'}
          </h3>
        </div>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">
            Nome cientifico
          </span>
          <input
            value={formulario.nome_cientifico}
            onChange={(event) =>
              setFormulario({ ...formulario, nome_cientifico: event.target.value })
            }
            className={CAMPO_CLASSNAME}
            required
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">Nome comum</span>
          <input
            value={formulario.nome_comum}
            onChange={(event) => setFormulario({ ...formulario, nome_comum: event.target.value })}
            className={CAMPO_CLASSNAME}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">Tipo</span>
          <select
            value={formulario.tipo}
            onChange={(event) => setFormulario({ ...formulario, tipo: event.target.value })}
            className={CAMPO_CLASSNAME}
          >
            {TIPOS.map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">
            Credito da imagem
          </span>
          <input
            value={formulario.credito_imagem}
            onChange={(event) =>
              setFormulario({ ...formulario, credito_imagem: event.target.value })
            }
            className={CAMPO_CLASSNAME}
          />
        </label>

        <label className="block sm:col-span-2">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">Descricao</span>
          <textarea
            value={formulario.descricao}
            onChange={(event) => setFormulario({ ...formulario, descricao: event.target.value })}
            className={`${CAMPO_CLASSNAME} min-h-[6rem]`}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">
            Link da fonte da imagem
          </span>
          <input
            type="url"
            value={formulario.fonte_imagem_url}
            onChange={(event) =>
              setFormulario({ ...formulario, fonte_imagem_url: event.target.value })
            }
            className={CAMPO_CLASSNAME}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">
            Local de captura da foto
          </span>
          <input
            value={formulario.local_captura_foto}
            onChange={(event) =>
              setFormulario({ ...formulario, local_captura_foto: event.target.value })
            }
            placeholder="Onde a foto foi tirada, ex: Caravelas, BA"
            className={CAMPO_CLASSNAME}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ocean-dark">
            Link com mais informacoes
          </span>
          <input
            type="url"
            value={formulario.fonte_url}
            onChange={(event) => setFormulario({ ...formulario, fonte_url: event.target.value })}
            className={CAMPO_CLASSNAME}
          />
        </label>

        <div className="flex items-center gap-3 sm:col-span-2">
          <button
            type="submit"
            disabled={enviando}
            className="inline-flex items-center gap-2 rounded-xl bg-ocean-dark px-4 py-3 font-semibold text-white transition hover:bg-ocean-light disabled:opacity-60"
          >
            <Plus size={18} />
            {enviando ? 'Enviando...' : editandoId ? 'Salvar edicao' : 'Adicionar especie'}
          </button>

          {editandoId && (
            <button
              type="button"
              onClick={cancelarEdicao}
              className="inline-flex items-center gap-2 rounded-xl border border-sand-dark/30 px-4 py-3 font-semibold text-ocean-dark"
            >
              <X size={18} />
              Cancelar
            </button>
          )}
        </div>

        {/* ⚠️ Categoria IUCN, taxonomia e foto ficam de fora deste
            formulario de proposito — sao campos que o projeto trata com
            cuidado de procedencia, e continuam so pelo Django admin. */}
      </form>

      <div className="flex flex-col gap-3">
        {carregando && (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500">
            Carregando especies...
          </div>
        )}

        {!carregando && especies.length === 0 && (
          <div className="rounded-2xl border border-dashed border-sand-dark/40 bg-white p-8 text-center text-gray-500">
            Nenhuma especie cadastrada ainda.
          </div>
        )}

        {!carregando &&
          especies.map((especie) => (
            <div
              key={especie.id}
              className="flex flex-col gap-2 rounded-2xl border border-sand-dark/20 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex items-start gap-3">
                <Fish className="mt-1 shrink-0 text-ocean-light" size={20} />
                <div>
                  <p className="font-semibold text-ocean-dark">
                    {especie.nome_comum || especie.nome_cientifico}
                  </p>
                  <p className="text-sm italic text-gray-500">{especie.nome_cientifico}</p>
                  {usuario.master && especie.autor && (
                    <p className="mt-1 text-xs text-gray-400">
                      criado por {especie.autor.criado_por || 'desconhecido'}
                      {especie.autor.editado_por &&
                        ` · editado por ${especie.autor.editado_por}`}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  onClick={() => iniciarEdicao(especie)}
                  className="inline-flex items-center gap-1 rounded-xl border border-sand-dark/30 px-3 py-2 text-sm font-semibold text-ocean-dark"
                >
                  <Pencil size={14} />
                  Editar
                </button>
                <button
                  type="button"
                  onClick={() => excluir(especie)}
                  className="inline-flex items-center gap-1 rounded-xl border border-red-300 px-3 py-2 text-sm font-semibold text-red-700"
                >
                  <Trash2 size={14} />
                  Excluir
                </button>
              </div>
            </div>
          ))}
      </div>
    </section>
  );
}
