"""A cadeia inteira, da aquisicao ao resultado, montada a partir do que existe.

🚨 **Tudo aqui e contado do dado, nunca lido de um agregado gravado.** Este
projeto ja perdeu uma decisao para o defeito oposto: em 27/07 a cobertura dos
datasets estava **gravada** num campo, envelheceu em silencio, e a tabela do
RESULTADOS.md montada a partir dela trocou dois episodios de lugar — o que
acabou decidindo o limiar de alerta do projeto. Um relatorio de auditoria que
le agregado gravado audita o agregado, nao o dado.

Por isso cada numero aqui sai de um `COUNT`/`MIN`/`MAX` sobre a tabela real, na
hora. E mais lento, e e o unico jeito de a resposta ser sobre o presente.

⚠️ **O relatorio declara o que NAO consegue afirmar.** A secao `lacunas` nao e
um apendice: e a parte que impede a auditoria de virar propaganda. Um retrato
que lista so o que esta completo descreve um projeto que nao tem lacuna, e
nenhum projeto e assim — o mesmo raciocinio pelo qual o manifesto de
checkpoints lista tambem o que falhou.
"""

from django.db.models import Count, Max, Min
from django.utils import timezone

from aquaculture.models import (
    Checkpoint,
    Especie,
    ExecucaoIngestao,
    LocalRecife,
    MedicaoAmbiental,
)

from . import codigo

VERSAO_FORMATO = 1

# Quantas execucoes de ingestao entram no retrato. O historico inteiro cresce
# sem limite e o que importa para auditoria e o estado recente mais as falhas -
# estas entram por completo em `lacunas`, independente deste corte.
EXECUCOES_NO_RETRATO = 20


def fontes():
    """Por (fonte, dataset), quanto existe, de quando ate quando, com que flag.

    O `dataset_id` entra na chave, e nao so a fonte, porque uma unica fonte
    emenda produtos diferentes na mesma serie — o Copernicus usa reanalise no
    historico e analise no periodo recente. Agrupar so por fonte apagaria
    justamente a costura que precisa ser citavel.
    """
    base = (
        MedicaoAmbiental.objects
        .values('fonte', 'dataset_id')
        .annotate(
            medicoes=Count('id'),
            inicio=Min('data'),
            fim=Max('data'),
            variaveis=Count('variavel', distinct=True),
            locais=Count('local_recife', distinct=True),
        )
        .order_by('fonte', 'dataset_id')
    )

    qualidade = {}
    for linha in (
        MedicaoAmbiental.objects
        .values('fonte', 'dataset_id', 'quality_flag')
        .annotate(n=Count('id'))
    ):
        chave = (linha['fonte'], linha['dataset_id'])
        qualidade.setdefault(chave, {})[linha['quality_flag']] = linha['n']

    retrato = []
    for linha in base:
        chave = (linha['fonte'], linha['dataset_id'])
        retrato.append({
            'fonte': linha['fonte'],
            'dataset_id': linha['dataset_id'] or None,
            'medicoes': linha['medicoes'],
            'periodo': {
                'inicio': linha['inicio'].isoformat() if linha['inicio'] else None,
                'fim': linha['fim'].isoformat() if linha['fim'] else None,
            },
            'variaveis_distintas': linha['variaveis'],
            'locais_cobertos': linha['locais'],
            'por_qualidade': dict(sorted(qualidade.get(chave, {}).items())),
        })
    return retrato


def locais():
    """Cobertura por local, incluindo os que nao tem serie nenhuma.

    ⚠️ Os locais **sem** medicao precisam aparecer. Listar so quem tem dado
    responde "o que temos" e esconde "o que falta" — e sao dez locais
    cadastrados contra menos que isso com serie.
    """
    medidos = {
        linha['local_recife__slug']: linha
        for linha in (
            MedicaoAmbiental.objects
            .values('local_recife__slug')
            .annotate(
                medicoes=Count('id'), inicio=Min('data'), fim=Max('data'),
            )
        )
    }

    retrato = []
    for local in LocalRecife.objects.order_by('slug'):
        linha = medidos.get(local.slug)
        retrato.append({
            'slug': local.slug,
            'nome': local.nome,
            'tem_coordenadas': local.tem_coordenadas,
            'fonte_coordenadas': local.fonte_coordenadas or None,
            'medicoes': linha['medicoes'] if linha else 0,
            'periodo': {
                'inicio': linha['inicio'].isoformat() if linha and linha['inicio'] else None,
                'fim': linha['fim'].isoformat() if linha and linha['fim'] else None,
            } if linha else None,
        })
    return retrato


def execucoes(limite=EXECUCOES_NO_RETRATO):
    """As ingestoes recentes, com o id que leva ao rastro no log."""
    return [
        {
            'fonte': registro.fonte,
            'local': registro.local_recife.slug if registro.local_recife else None,
            'status': registro.status,
            'periodo': {
                'inicio': registro.inicio_periodo.isoformat() if registro.inicio_periodo else None,
                'fim': registro.fim_periodo.isoformat() if registro.fim_periodo else None,
            },
            'gravados': registro.registros_gravados,
            'rejeitados': registro.registros_rejeitados,
            'iniciado_em': registro.iniciado_em.isoformat(),
            'correlacao': registro.correlacao or None,
        }
        for registro in (
            ExecucaoIngestao.objects
            .select_related('local_recife')
            .order_by('-iniciado_em')[:limite]
        )
    ]


def retomada():
    """Resumo dos checkpoints por tarefa."""
    linhas = (
        Checkpoint.objects
        .values('tarefa', 'status')
        .annotate(n=Count('id'))
        .order_by('tarefa')
    )
    por_tarefa = {}
    for linha in linhas:
        por_tarefa.setdefault(linha['tarefa'], {})[linha['status']] = linha['n']
    return por_tarefa


def modelos():
    """Os artefatos treinados que estao no disco, com o que os descreve.

    Le o JSON ao lado, e nao o `.joblib`: carregar um pickle so para listar
    metadado executaria codigo sem necessidade (ver `ml.persistencia`).
    """
    from ml import persistencia

    try:
        return persistencia.listar()
    except Exception as exc:  # pragma: no cover - depende do disco
        # Ausencia de modelo nao e erro de auditoria: e um fato sobre o estado,
        # e vira lacuna em vez de derrubar o relatorio.
        return {'erro': f'{type(exc).__name__}: {exc}'}


def lacunas():
    """O que este acervo NAO consegue sustentar hoje.

    🚨 A secao que impede o relatorio de virar propaganda. Cada item aqui e uma
    afirmacao que **nao** pode ser feita num artigo sem ressalva.
    """
    achados = []

    sem_coordenada = [
        local.slug for local in LocalRecife.objects.order_by('slug')
        if not local.tem_coordenadas
    ]
    if sem_coordenada:
        achados.append({
            'tipo': 'local_sem_coordenada',
            'quantos': len(sem_coordenada),
            'quais': sem_coordenada,
            'consequencia': (
                'Nao entram no pipeline de ingestao: ficam cadastrados sem '
                'serie ambiental.'
            ),
        })

    # ⚠️ `iucn_tem_procedencia` e propriedade do modelo, nao coluna - por isso
    # a varredura em Python. Sao dezenas de especies, nao milhoes; trocar a
    # regra por um filtro SQL equivalente criaria duas definicoes da mesma
    # coisa, livres para divergir.
    sem_iucn = [
        especie.nome_cientifico
        for especie in Especie.objects.order_by('nome_cientifico')
        if not especie.iucn_tem_procedencia
    ]
    if sem_iucn:
        achados.append({
            'tipo': 'especie_sem_procedencia_iucn',
            'quantos': len(sem_iucn),
            'quais': sem_iucn,
            'consequencia': (
                'A categoria de conservacao nao e exibida nem citavel. Ver '
                'docs/FONTES.md secao 2.4.'
            ),
        })

    vencidas = [
        especie.nome_cientifico
        for especie in Especie.objects.order_by('nome_cientifico')
        if especie.iucn_conferencia_vencida
    ]
    if vencidas:
        achados.append({
            'tipo': 'conferencia_iucn_vencida',
            'quantos': len(vencidas),
            'quais': vencidas,
            'consequencia': (
                'Ha categoria e ano, mas ninguem confere ha tempo demais - a '
                'IUCN pode ter publicado outra avaliacao.'
            ),
        })

    degradadas = (
        MedicaoAmbiental.objects
        .exclude(quality_flag='ok')
        .values('quality_flag')
        .annotate(n=Count('id'))
    )
    for linha in degradadas:
        achados.append({
            'tipo': f'medicao_{linha["quality_flag"]}',
            'quantos': linha['n'],
            'consequencia': (
                'Aprovada com ressalva - o motivo esta em `observacao`, valor '
                'a valor.'
                if linha['quality_flag'] == 'degradado' else
                'Reprovada na validacao fisica: valor nulo, nao zero.'
            ),
        })

    esgotados = list(
        Checkpoint.objects
        .filter(tentativas__gte=5)
        .exclude(status=Checkpoint.CONCLUIDO)
        .values_list('tarefa', 'unidade')
    )
    if esgotados:
        achados.append({
            'tipo': 'checkpoint_esgotado',
            'quantos': len(esgotados),
            'quais': [f'{tarefa} / {unidade}' for tarefa, unidade in esgotados],
            'consequencia': (
                'Estas unidades pararam de ser tentadas: ha buraco de dado que '
                'nao se fecha sozinho.'
            ),
        })

    falhas = (
        ExecucaoIngestao.objects
        .filter(status='falha')
        .order_by('-iniciado_em')[:10]
    )
    if falhas:
        achados.append({
            'tipo': 'ingestao_falhou',
            'quantos': ExecucaoIngestao.objects.filter(status='falha').count(),
            'quais': [
                f'{r.fonte}/{r.local_recife.slug if r.local_recife else "global"} '
                f'em {r.iniciado_em:%Y-%m-%d}'
                for r in falhas
            ],
            'consequencia': 'Periodo pedido e nao obtido.',
        })

    estado_do_codigo = codigo.versao()
    if not codigo.reproduzivel():
        achados.append({
            'tipo': 'codigo_nao_reproduzivel',
            'quantos': 1,
            'consequencia': (
                'A arvore tem alteracao nao commitada, ou nao ha git: um '
                'resultado gerado agora nao pode ser reconstruido a partir do '
                'repositorio. O numero continua valido como medicao; o que '
                'nao da e reproduzi-lo.'
            ),
            'detalhe': estado_do_codigo,
        })

    return achados


def montar(incluir_modelos=True):
    """O retrato inteiro, pronto para virar JSON ou texto."""
    retrato = {
        'versao_formato': VERSAO_FORMATO,
        'gerado_em': timezone.now().isoformat(),
        'codigo': codigo.versao(),
        'fontes': fontes(),
        'locais': locais(),
        'execucoes_recentes': execucoes(),
        'retomada': retomada(),
        'lacunas': lacunas(),
    }
    if incluir_modelos:
        retrato['modelos'] = modelos()

    total = sum(item['medicoes'] for item in retrato['fontes'])
    retrato['resumo'] = {
        'medicoes': total,
        'fontes': len(retrato['fontes']),
        'locais_cadastrados': len(retrato['locais']),
        'locais_com_serie': sum(
            1 for item in retrato['locais'] if item['medicoes']
        ),
        'lacunas': len(retrato['lacunas']),
        'reproduzivel': codigo.reproduzivel(),
    }
    return retrato
