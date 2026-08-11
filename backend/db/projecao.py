"""Projeta o PostgreSQL no Neo4j. Sentido unico, sempre.

**O grafo nunca recebe escrita direta.** Ele e reconstruido a partir do
relacional, e se divergir, corromper ou for perdido, basta reconstruir - nao ha
dado exclusivo dele. A justificativa esta em docs/arquitetura.md: nao existe
transacao distribuida entre Postgres e Neo4j, entao escrita paralela deixaria os
dois bancos divergentes **sem forma de saber qual esta certo**.

⚠️ **Isto substitui o `neo4j_seed`, nao o estende.** Aquele deriva os nos de
`StatusPredicao`, o modelo legado com 3 registros - o mesmo caminho que produziu
os defeitos de docs/FONTES.md secao 6. As 57.420 medicoes reais nunca estiveram
no grafo.

---

**A escolha de escopo, medida em 27/07/2026** (docs/arquitetura.md exigia
"medir antes de projetar"):

| Opcao | Elementos | Proveniencia por valor? |
|---|---|---|
| A. um no por (local, data, variavel, fonte) | **172.277** | ✅ sim |
| B. um no por (local, data) | 21.590 | ❌ nao |
| C. agregado mensal | 5.705 | ❌ nao |

**Adotada a A.** As opcoes B e C sao 8x e 30x menores, e **as duas destroem a
razao de o grafo existir**: um no que junta a SST do NOAA com a salinidade do
Copernicus so pode apontar para uma fonte. Proveniencia por valor e a
contribuicao central do projeto (docs/VISAO_GERAL.md secao 8); um grafo que a
perde nao vale o que economiza.

O custo foi conferido contra a instancia real: Neo4j **5.26 Community**, que nao
tem teto de nos - o limite que a arquitetura temia era do Neo4j 3.x. 172 mil
elementos e volume pequeno, e cresce **72 por dia**.

---

**Por que o id canonico da medicao mudou.** O schema anterior usava
`localizacao_slug:data_iso`, herdado de `StatusPredicao`, onde uma linha era um
dia. Em `MedicaoAmbiental` uma linha e **uma variavel, de uma fonte, num dia** -
oito por local por dia. O id antigo colidiria oito vezes e o `MERGE` sobrescreveria
em silencio, deixando uma variavel de cada dia.

O id passa a ser `slug:data:variavel:fonte`, que e exatamente a constraint de
unicidade que o PostgreSQL ja usa.
"""

import logging
from dataclasses import dataclass, field

from db.connection import Neo4jConnection

logger = logging.getLogger(__name__)

# Lote de escrita. O driver monta uma transacao por chamada; 1.000 e o ponto em
# que o custo por linha para de cair sem que a transacao fique grande demais.
LOTE = 1000

ORIGEM = 'projecao-postgres'


def _slug_fonte(fonte, dataset_id):
    """Id canonico de `FonteDados`: quem publicou, e de qual produto.

    Os dois juntos, e nao so a fonte: o Copernicus publica quatro datasets
    diferentes nesta serie, e a emenda entre reanalise e analise so e auditavel
    se cada valor souber de qual deles veio.
    """
    return f'{fonte}:{dataset_id}' if dataset_id else fonte


@dataclass
class Resultado:
    localizacoes: int = 0
    especies: int = 0
    fontes: int = 0
    medicoes: int = 0
    rel_abriga: int = 0
    rel_tem_medicao: int = 0
    rel_proveniente: int = 0
    apagados: int = 0
    avisos: list = field(default_factory=list)

    @property
    def nos(self):
        return self.localizacoes + self.especies + self.fontes + self.medicoes

    @property
    def relacoes(self):
        return self.rel_abriga + self.rel_tem_medicao + self.rel_proveniente

    def resumo(self):
        return (
            f'{self.nos:,} nos e {self.relacoes:,} relacoes '
            f'({self.nos + self.relacoes:,} elementos)'
        )


def limpar(conexao=Neo4jConnection):
    """Apaga o que a projecao criou. **So o que ela criou.**

    Filtra por `origem_registro` de proposito: um `MATCH (n) DETACH DELETE n`
    levaria junto qualquer no criado a mao para experimento, e a projecao nao
    tem autoridade sobre o que nao produziu.
    """
    total = 0
    while True:
        # Em lotes, senao uma transacao unica com 172 mil elementos estoura a
        # memoria da instancia.
        apagados = conexao.run(
            'MATCH (n) WHERE n.origem_registro = $origem '
            'WITH n LIMIT $lote DETACH DELETE n RETURN count(n) AS n',
            {'origem': ORIGEM, 'lote': LOTE},
        )[0]['n']
        total += apagados
        if apagados < LOTE:
            return total


def garantir_constraints(conexao=Neo4jConnection):
    """Constraints de unicidade. Idempotente.

    Nao e enfeite: elas sao o que faz o `MERGE` desta projecao ser reexecutavel.
    Sem a constraint, o `MERGE` casa por varredura e duas execucoes seguidas
    podem duplicar.
    """
    comandos = [
        'CREATE CONSTRAINT localizacao_id IF NOT EXISTS '
        'FOR (n:Localizacao) REQUIRE n.id IS UNIQUE',
        'CREATE CONSTRAINT localizacao_slug IF NOT EXISTS '
        'FOR (n:Localizacao) REQUIRE n.slug IS UNIQUE',
        'CREATE CONSTRAINT especie_id IF NOT EXISTS '
        'FOR (n:Especie) REQUIRE n.id IS UNIQUE',
        'CREATE CONSTRAINT medicao_id IF NOT EXISTS '
        'FOR (n:MedicaoAmbiental) REQUIRE n.id IS UNIQUE',
        'CREATE CONSTRAINT fonte_id IF NOT EXISTS '
        'FOR (n:FonteDados) REQUIRE n.id IS UNIQUE',
    ]
    for comando in comandos:
        conexao.run(comando)
    return len(comandos)


def projetar_localizacoes(conexao=Neo4jConnection):
    from aquaculture.models import LocalRecife

    registros = [
        {
            'id': l.slug,
            'slug': l.slug,
            'nome': l.nome,
            'estado': l.estado,
            'cidade': l.cidade,
            'latitude': l.latitude,
            'longitude': l.longitude,
            'ativo': l.ativo,
            'django_pk': l.pk,
            'origem_registro': ORIGEM,
        }
        for l in LocalRecife.objects.all()
    ]
    if registros:
        conexao.run(
            'UNWIND $linhas AS linha '
            'MERGE (n:Localizacao {id: linha.id}) SET n += linha',
            {'linhas': registros},
        )
    return len(registros)


def projetar_especies(conexao=Neo4jConnection):
    """Especies e o vinculo com os locais que as abrigam."""
    from django.utils.text import slugify

    from aquaculture.models import Especie

    registros, vinculos = [], []
    for e in Especie.objects.prefetch_related('locais'):
        identificador = slugify(e.nome_cientifico)
        registros.append({
            'id': identificador,
            'nome_cientifico': e.nome_cientifico,
            'nome_comum': e.nome_comum,
            'tipo': e.tipo,
            'descricao': e.descricao,
            # 🚨 `status_conservacao` foi removido do modelo pela migracao 0022
            # (docs/FONTES.md secao 2.4) e nunca deveria ter sido escrito de
            # novo aqui. `iucn_tem_procedencia` e `iucn_categoria_rotulo` sao
            # derivados no Django (Especie.iucn_tem_procedencia,
            # get_iucn_categoria_display) e gravados ja calculados: e a mesma
            # razao pela qual EspecieSerializer os manda no payload em vez de
            # deixar quem consome reinventar a regra — ver serializers.py.
            'iucn_categoria': e.iucn_categoria,
            'iucn_categoria_rotulo': e.get_iucn_categoria_display(),
            'iucn_avaliado_em': e.iucn_avaliado_em,
            'iucn_versao': e.iucn_versao,
            'fonte_iucn_url': e.fonte_iucn_url,
            'iucn_tem_procedencia': e.iucn_tem_procedencia,
            'aphia_id': e.aphia_id,
            'credito_imagem': e.credito_imagem,
            'fonte_imagem_url': e.fonte_imagem_url,
            'fonte_url': e.fonte_url,
            'django_pk': e.pk,
            'origem_registro': ORIGEM,
        })
        vinculos += [
            {'local': l.slug, 'especie': identificador} for l in e.locais.all()
        ]

    if registros:
        conexao.run(
            'UNWIND $linhas AS linha '
            'MERGE (n:Especie {id: linha.id}) '
            'SET n += linha '
            # Remove a propriedade legada de nos projetados antes desta
            # correcao — sem isto ela ficaria orfa e nula para sempre, porque
            # `SET n += linha` so adiciona/sobrescreve chaves, nunca apaga as
            # que o dicionario novo nao tem.
            'REMOVE n.status_conservacao',
            {'linhas': registros},
        )
    if vinculos:
        conexao.run(
            'UNWIND $linhas AS linha '
            'MATCH (l:Localizacao {id: linha.local}) '
            'MATCH (e:Especie {id: linha.especie}) '
            'MERGE (l)-[:ABRIGA_ESPECIE]->(e)',
            {'linhas': vinculos},
        )
    return len(registros), len(vinculos)


def projetar_fontes(conexao=Neo4jConnection):
    """Um no por (fonte, dataset_id) efetivamente usado.

    Derivado do dado, e nao de uma lista fixa: se amanha a ingestao passar a
    usar outro produto, a fonte aparece sozinha. Uma lista escrita a mao
    envelheceria em silencio.
    """
    from aquaculture.models import MedicaoAmbiental

    pares = (
        MedicaoAmbiental.objects.order_by()
        .values_list('fonte', 'dataset_id')
        .distinct()
    )
    registros = [
        {
            'id': _slug_fonte(fonte, dataset_id),
            'slug': fonte,
            'dataset_id': dataset_id or '',
            'origem_registro': ORIGEM,
        }
        for fonte, dataset_id in sorted(set(pares))
    ]
    if registros:
        conexao.run(
            'UNWIND $linhas AS linha '
            'MERGE (n:FonteDados {id: linha.id}) SET n += linha',
            {'linhas': registros},
        )
    return len(registros)


def projetar_medicoes(conexao=Neo4jConnection, lote=LOTE, ao_progredir=None):
    """As medições, com a proveniência de cada valor.

    Percorre em lotes com `iterator()`: carregar 57 mil objetos Django de uma
    vez custa memória à toa, e o gargalo aqui é a escrita, não a leitura.
    """
    from aquaculture.models import MedicaoAmbiental

    total = MedicaoAmbiental.objects.count()
    campos = ('local_recife__slug', 'data', 'variavel', 'valor', 'unidade',
              'fonte', 'dataset_id', 'quality_flag', 'observacao')

    escritos = 0
    pendentes = []

    def descarregar():
        nonlocal escritos
        if not pendentes:
            return
        conexao.run(
            'UNWIND $linhas AS linha '
            'MATCH (l:Localizacao {id: linha.local}) '
            'MATCH (f:FonteDados {id: linha.fonte_id}) '
            'MERGE (m:MedicaoAmbiental {id: linha.id}) '
            'SET m += linha.props '
            'MERGE (l)-[:TEM_MEDICAO]->(m) '
            'MERGE (m)-[:PROVENIENTE_DE]->(f)',
            # ⚠️ `list(...)` e copia, e ela e necessaria.
            #
            # Passar `pendentes` direto entrega a **mesma lista** que o
            # `clear()` abaixo esvazia. Com o driver real isso passa
            # despercebido, porque a consulta ja executou; mas qualquer coisa
            # que guarde o parametro - uma retentativa, um log, um duble de
            # teste - fica com uma lista vazia. Foi assim que um teste flagrou:
            # a projecao gravava 57.420 linhas e o parametro registrado
            # aparecia vazio.
            {'linhas': list(pendentes)},
        )
        escritos += len(pendentes)
        if ao_progredir:
            ao_progredir(escritos, total)
        pendentes.clear()

    for linha in MedicaoAmbiental.objects.order_by('pk').values(*campos).iterator(
        chunk_size=lote
    ):
        slug = linha['local_recife__slug']
        data = linha['data'].isoformat()
        variavel = linha['variavel']
        fonte = linha['fonte']
        pendentes.append({
            # ⚠️ Os quatro campos, e nao so local+data: uma linha aqui e uma
            # VARIAVEL de uma FONTE num dia. Ver a docstring do modulo.
            'id': f'{slug}:{data}:{variavel}:{fonte}',
            'local': slug,
            'fonte_id': _slug_fonte(fonte, linha['dataset_id']),
            'props': {
                'local_slug': slug,
                'data': data,
                'variavel': variavel,
                'valor': linha['valor'],
                'unidade': linha['unidade'],
                'fonte': fonte,
                'dataset_id': linha['dataset_id'] or '',
                'quality_flag': linha['quality_flag'],
                'observacao': linha['observacao'] or '',
                'origem_registro': ORIGEM,
            },
        })
        if len(pendentes) >= lote:
            descarregar()

    descarregar()
    return escritos


def projetar(conexao=Neo4jConnection, limpar_antes=True, lote=LOTE,
             ao_progredir=None):
    """Reconstrói o grafo inteiro a partir do PostgreSQL."""
    resultado = Resultado()

    garantir_constraints(conexao)
    if limpar_antes:
        resultado.apagados = limpar(conexao)

    resultado.localizacoes = projetar_localizacoes(conexao)
    resultado.especies, resultado.rel_abriga = projetar_especies(conexao)
    resultado.fontes = projetar_fontes(conexao)

    if resultado.localizacoes == 0:
        resultado.avisos.append(
            'Nenhuma Localizacao projetada: as medicoes ficariam orfas e '
            'foram puladas.'
        )
        return resultado

    resultado.medicoes = projetar_medicoes(conexao, lote, ao_progredir)
    # Cada medicao gera exatamente uma de cada.
    resultado.rel_tem_medicao = resultado.medicoes
    resultado.rel_proveniente = resultado.medicoes
    return resultado


def conferir(conexao=Neo4jConnection):
    """Compara o grafo com o PostgreSQL. **Projetar sem conferir nao vale.**

    Uma projecao que falha no meio deixa o grafo parcial e silencioso — e a
    consulta seguinte responde com dado incompleto sem avisar. Esta funcao e o
    que transforma "rodou" em "esta certo".
    """
    from aquaculture.models import Especie, LocalRecife, MedicaoAmbiental

    def contar(cypher):
        return conexao.run(cypher)[0]['n']

    esperado_fontes = len(set(
        MedicaoAmbiental.objects.order_by()
        .values_list('fonte', 'dataset_id').distinct()
    ))

    conferencias = [
        ('Localizacao', LocalRecife.objects.count(),
         contar('MATCH (n:Localizacao) RETURN count(n) AS n')),
        ('Especie', Especie.objects.count(),
         contar('MATCH (n:Especie) RETURN count(n) AS n')),
        ('FonteDados', esperado_fontes,
         contar('MATCH (n:FonteDados) RETURN count(n) AS n')),
        ('MedicaoAmbiental', MedicaoAmbiental.objects.count(),
         contar('MATCH (n:MedicaoAmbiental) RETURN count(n) AS n')),
        ('TEM_MEDICAO', MedicaoAmbiental.objects.count(),
         contar('MATCH ()-[r:TEM_MEDICAO]->() RETURN count(r) AS n')),
        ('PROVENIENTE_DE', MedicaoAmbiental.objects.count(),
         contar('MATCH ()-[r:PROVENIENTE_DE]->() RETURN count(r) AS n')),
    ]

    orfas = contar(
        'MATCH (m:MedicaoAmbiental) WHERE NOT (m)-[:PROVENIENTE_DE]->() '
        'RETURN count(m) AS n'
    )
    return conferencias, orfas
