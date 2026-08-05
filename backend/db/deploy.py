"""Reconstroi tudo que o site precisa e que **nao viaja no `git push`**.

🚨 **Por que este modulo existe, e por que a falta dele nao aparecia.**

O projeto tem tres artefatos derivados — o `.joblib` do modelo, a projecao do
Neo4j e o `.docx` da documentacao. Cada um deles ganhou, no momento em que foi
criado, uma linha dizendo *"o deploy precisa rodar este comando"*. Os avisos
estao certos e estao nos lugares certos.

E somam zero, porque **aviso escrito nao e passo executado**. Um `git clone`
seguido de deploy produzia um site em que:

| Faltando | Sintoma |
|---|---|
| `.joblib` | `/api/painel-risco/` responde 503 nos tres recifes |
| projecao | `/api/grafo/localizacoes/` devolve vazio |
| `.docx` | so a documentacao offline falta |

Nenhum item do checklist de go-live falhava por isso — era o buraco **entre**
os itens, que lista de verificacao nao pega porque cada linha olha uma peca e
ninguem olha a montagem.

**A ordem importa, e nao e arbitraria:**

1. `migrate` — sem o schema, nada mais roda;
2. `treinar_final` — le o banco, entao depende do schema **e dos dados**;
3. `neo4j_projetar` — mesma dependencia, e reconstroi o grafo do zero;
4. `exportar_docs` — independente, fica por ultimo por ser o unico que nao
   afeta o que o site serve;
5. `conferir_persistencia` — valida o resultado, e nao a intencao.

⚠️ **Falha rapido, de proposito.** Um deploy que segue depois de um passo
quebrado entrega um site **meio construido** — pior que um que nao sobe, porque
parece ter funcionado. O primeiro erro interrompe a sequencia.

⚠️ **`treinar_final` falha se o banco estiver vazio, e isso esta certo.** Nao ha
modelo honesto a construir sem serie. A mensagem de erro precisa dizer para
rodar a ingestao — nao ha atalho aqui.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Passo:
    """Um comando da sequencia, com o motivo de estar nela."""

    nome: str
    comando: str
    motivo: str
    argumentos: tuple = ()
    opcoes: dict = field(default_factory=dict)
    # Passos que podem ser dispensados quando a infraestrutura nao esta toda
    # de pe (ex.: reconstruir sem Neo4j, para um ambiente que so serve a API).
    dispensavel: bool = False


PASSOS = (
    Passo(
        nome='schema',
        comando='migrate',
        motivo='Sem o schema aplicado, nenhum passo seguinte tem onde ler.',
        opcoes={'verbosity': 0},
    ),
    Passo(
        nome='modelo',
        comando='treinar_final',
        motivo=(
            'O .joblib nao e versionado. Sem ele o painel de risco responde '
            '503 em todos os recifes.'
        ),
    ),
    Passo(
        nome='grafo',
        comando='neo4j_projetar',
        motivo=(
            'A projecao e derivada do PostgreSQL e reconstruida do zero. Sem '
            'ela os endpoints de grafo devolvem vazio.'
        ),
        dispensavel=True,
    ),
    Passo(
        nome='documentacao',
        comando='exportar_docs',
        motivo='Os .docx sao derivados do Markdown e nao acompanham o repositorio.',
        dispensavel=True,
    ),
    Passo(
        nome='conferencia',
        comando='conferir_persistencia',
        motivo=(
            'Valida o resultado, e nao a intencao: indices, constraints e o '
            'tempo das consultas quentes.'
        ),
    ),
)


class PassoFalhou(RuntimeError):
    """Um passo da sequencia falhou. Interrompe o restante."""

    def __init__(self, passo, erro):
        self.passo = passo
        self.erro = erro
        super().__init__(f'Passo "{passo.nome}" ({passo.comando}) falhou: {erro}')


@dataclass
class Resultado:
    executados: list = field(default_factory=list)
    pulados: list = field(default_factory=list)
    falhou: object = None

    @property
    def ok(self):
        return self.falhou is None


def executar(passos=PASSOS, pular=(), ao_progredir=None, opcoes_extra=None):
    """Roda a sequencia, parando no primeiro erro.

    `pular` recebe nomes de passo. Um passo nao `dispensavel` **nao pode** ser
    pulado: a chamada levanta em vez de seguir. E deliberado — pular o
    `migrate` produziria um erro tres passos adiante, com uma mensagem que nao
    aponta para a causa.
    """
    from django.core.management import call_command

    pular = set(pular)
    opcoes_extra = opcoes_extra or {}
    resultado = Resultado()

    obrigatorios_pulados = [
        p.nome for p in passos if p.nome in pular and not p.dispensavel
    ]
    if obrigatorios_pulados:
        raise ValueError(
            f'Passos obrigatorios nao podem ser pulados: {obrigatorios_pulados}. '
            f'Pular um deles faria a falha aparecer varios passos adiante, '
            f'longe da causa.'
        )

    for passo in passos:
        if passo.nome in pular:
            resultado.pulados.append(passo)
            if ao_progredir:
                ao_progredir(passo, 'pulado')
            continue

        if ao_progredir:
            ao_progredir(passo, 'iniciando')

        try:
            opcoes = {**passo.opcoes, **opcoes_extra.get(passo.nome, {})}
            call_command(passo.comando, *passo.argumentos, **opcoes)
        except Exception as erro:  # noqa: BLE001 - qualquer falha interrompe
            resultado.falhou = PassoFalhou(passo, erro)
            if ao_progredir:
                ao_progredir(passo, 'falhou')
            return resultado

        resultado.executados.append(passo)
        if ao_progredir:
            ao_progredir(passo, 'ok')

    return resultado


def conferir_artefatos(nome_modelo=None):
    """Os artefatos existem **depois** da reconstrucao?

    ⚠️ Nao e redundante com o sucesso dos comandos. Um comando pode terminar
    sem erro e nao ter produzido o arquivo — foi o caso do `treinar_final` com
    `--nome` divergente do que o painel carrega, que grava um artefato correto
    com o nome errado e deixa o site sem modelo mesmo assim.
    """
    from django.conf import settings

    from ml import persistencia

    nome = nome_modelo or getattr(settings, 'PAINEL_MODELO', 'entrega1_baa')
    achados = []

    try:
        metadados = persistencia.ler_metadados(nome)
        achados.append((
            'modelo',
            True,
            f'{nome}: {metadados.get("n_treino")} amostras, '
            f'calibracao {metadados.get("calibracao")}',
        ))
    except Exception as erro:  # noqa: BLE001
        achados.append((
            'modelo', False,
            f'{type(erro).__name__}: o painel carrega "{nome}" e ele nao esta '
            f'utilizavel',
        ))

    return achados
