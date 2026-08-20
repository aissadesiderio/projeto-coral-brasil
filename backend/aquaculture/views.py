from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from . import cobertura
from .models import (
    DatasetCatalogo,
    Especie,
    LocalRecife,
    MedicaoAmbiental,
    SolicitacaoEspecie,
    aprovado_para_contribuir,
)
from .paginacao import PaginacaoPadrao
from .permissions import PodeContribuir
from .neo4j_service import (
    Neo4jServiceError,
    listar_localizacoes_grafo,
    obter_localizacao_grafo,
)
from .serializers import (
    DatasetCatalogoSerializer,
    EspecieContribuicaoSerializer,
    EspecieSerializer,
    LocalRecifeDetailSerializer,
    LocalRecifeListSerializer,
    MedicaoAmbientalSerializer,
)

MENSAGEM_OFFLINE = (
    'Site temporariamente offline para reestruturacao de backend e banco de dados.'
)


class OfflineModeMixin:
    """Bloqueia endpoints publicos quando o site esta em manutencao/offline.

    Usa `JsonResponse` e nao `rest_framework.Response`: o dispatch acontece
    antes de `finalize_response`, entao um Response do DRF sairia daqui sem
    `accepted_renderer` e estouraria um AssertionError (HTTP 500) em vez de
    devolver o 503 pretendido.

    🚨 Bloqueia **qualquer** metodo, nao so GET. Ate a funcionalidade de
    contribuicao de especie, todo uso deste mixin era GET-only, entao a
    checagem nunca precisou olhar o metodo — mas cadastro de conta e envio de
    especie sao POST, e nao faz sentido aceitar escrita enquanto o site se
    declara offline.
    """

    def dispatch(self, request, *args, **kwargs):
        if getattr(settings, 'OFFLINE_MODE', False):
            return JsonResponse(
                {'detail': MENSAGEM_OFFLINE},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return super().dispatch(request, *args, **kwargs)


def _montar_dados_propostos(validated_data):
    """`validated_data` de `EspecieContribuicaoSerializer`, pronto para JSON.

    🚨 So existe por causa de `locais`: o `SlugRelatedField` com `queryset`
    resolve para instancias de `LocalRecife`, que `JSONField` nao aceita.
    Guardar o slug em vez da instancia tambem e o que permite `aprovar()`
    detectar um recife que sumiu entre o pedido e a revisao.
    """
    dados = dict(validated_data)
    locais = dados.pop('locais', None)
    if locais is not None:
        dados['locais'] = [local.slug for local in locais]
    return dados


class EspecieList(OfflineModeMixin, generics.ListCreateAPIView):
    permission_classes = [PodeContribuir]

    def get_queryset(self):
        queryset = Especie.objects.all().prefetch_related('locais')
        local_slug = self.request.query_params.get('local')
        if local_slug:
            queryset = queryset.filter(locais__slug=local_slug).distinct()
        return queryset.order_by('nome_comum', 'nome_cientifico')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EspecieContribuicaoSerializer
        return EspecieSerializer

    def create(self, request, *args, **kwargs):
        """Master cria na hora; qualquer outra conta aprovada vira pedido.

        🚨 O `serializer` aqui e sempre `EspecieContribuicaoSerializer` — a
        lista branca vale para master tambem. Categoria IUCN, taxonomia e
        foto continuam so pelo Django admin, para quem quer que seja.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user.is_superuser:
            especie = serializer.save(criado_por=request.user)
            saida = EspecieSerializer(especie, context=self.get_serializer_context())
            return Response(saida.data, status=status.HTTP_201_CREATED)

        SolicitacaoEspecie.objects.create(
            tipo='CRIAR',
            solicitante=request.user,
            dados_propostos=_montar_dados_propostos(serializer.validated_data),
        )
        return Response(
            {'detail': 'Enviado para revisao.'}, status=status.HTTP_202_ACCEPTED,
        )


class EspecieDetail(OfflineModeMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Especie.objects.all().prefetch_related('locais')
    permission_classes = [PodeContribuir]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return EspecieContribuicaoSerializer
        return EspecieSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        if request.user.is_superuser:
            especie = serializer.save(editado_por=request.user, editado_em=timezone.now())
            saida = EspecieSerializer(especie, context=self.get_serializer_context())
            return Response(saida.data)

        SolicitacaoEspecie.objects.create(
            tipo='EDITAR',
            especie=instance,
            solicitante=request.user,
            dados_propostos=_montar_dados_propostos(serializer.validated_data),
        )
        return Response(
            {'detail': 'Enviado para revisao.'}, status=status.HTTP_202_ACCEPTED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if request.user.is_superuser:
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        SolicitacaoEspecie.objects.create(
            tipo='EXCLUIR', especie=instance, solicitante=request.user,
        )
        return Response(
            {'detail': 'Enviado para revisao.'}, status=status.HTTP_202_ACCEPTED,
        )


def _dados_da_sessao(usuario):
    if not usuario or not usuario.is_authenticated:
        return {'autenticado': False, 'username': None, 'master': False, 'aprovado': False}
    return {
        'autenticado': True,
        'username': usuario.username,
        'master': usuario.is_superuser,
        'aprovado': aprovado_para_contribuir(usuario),
    }


class CadastroView(APIView):
    """Cadastro aberto — qualquer visitante pode criar conta.

    ⚠️ A conta comeca logada, mas **sem** poder contribuir nem baixar dado:
    o sinal em `signals.py` cria o `PerfilUsuario` com `aprovado=False`.
    Aprovar e acao de master, feita no Django admin — devolver a sessao ja
    logada aqui e o que permite a tela mostrar "aguardando aprovacao" em vez
    de mandar logar de novo depois de um cadastro que acabou de funcionar.
    """

    permission_classes = []

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        email = (request.data.get('email') or '').strip()
        senha = request.data.get('password') or ''

        if not username or not senha:
            return Response(
                {'detail': 'Usuario e senha sao obrigatorios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {'detail': 'Este nome de usuario ja existe.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(senha)
        except DjangoValidationError as erro:
            return Response({'detail': ' '.join(erro.messages)}, status=status.HTTP_400_BAD_REQUEST)

        usuario = User.objects.create_user(username=username, email=email, password=senha)
        django_login(request._request, usuario)
        return Response(_dados_da_sessao(usuario), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get('username') or ''
        senha = request.data.get('password') or ''
        usuario = authenticate(request, username=username, password=senha)
        if usuario is None:
            return Response(
                {'detail': 'Usuario ou senha invalidos.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        django_login(request._request, usuario)
        return Response(_dados_da_sessao(usuario))


class LogoutView(APIView):
    permission_classes = []

    def post(self, request):
        django_logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EuView(APIView):
    """Estado da sessao — tambem funciona deslogado (autenticado: false).

    `ensure_csrf_cookie` garante que o cookie `csrftoken` exista assim que o
    site carrega, mesmo antes de qualquer login: sem ele, a primeira escrita
    autenticada (cadastro nao precisa, mas editar/logout precisam) nao teria
    de onde ler o token para o cabecalho `X-CSRFToken`.
    """

    permission_classes = []

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response(_dados_da_sessao(request.user))


class CoberturaNoContextoMixin:
    """Injeta a cobertura real das medicoes da pagina de uma vez.

    🚨 Sem isto o catalogo anunciaria periodo e volume gravados a mao. Medido
    em 27/07/2026: seis dos nove datasets nao tinham **nenhuma** medicao no
    banco, e os tres reais declaravam fim em 2025 com a serie ja em 2026.

    Uma consulta agrupada serve a lista inteira; calcular por item daria uma
    consulta por linha.

    ⚠️ O que viaja no contexto e o **resumo das medicoes**, e nao o mapa ja
    montado por dataset. A diferenca custava uma consulta: montar o mapa aqui
    obrigava a avaliar o queryset uma segunda vez, so para saber quais datasets
    descrever. O resumo nao depende disso.

    ⚠️ Usado por dois consumidores desde 12/08/2026, e por isso mora acima de
    ambos: o catalogo (`cobertura.para`) e a pagina do recife
    (`acervo.para_local`). Sao duas leituras do mesmo agregado — "quanto deste
    dataset o projeto tem" e "o que o projeto tem deste local".
    """

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto['medicoes'] = cobertura.resumo()
        return contexto


class LocaisDoModeloNoContextoMixin:
    """Injeta os slugs que o artefato do modelo cobre.

    Mesmo padrao de `CoberturaNoContextoMixin`: uma leitura serve a resposta
    inteira, e o serializer nao vai ao disco por item.

    ⚠️ Le **so o JSON de metadados**, nunca o `.joblib`. A pergunta e "quais
    recifes o modelo viu", e carregar o pipeline para respondê-la poria o custo
    de uma inferencia numa listagem que nao infere nada.

    Artefato ausente devolve tupla vazia em vez de levantar: o catalogo de
    recifes nao depende do modelo existir, e derrubar `/api/locais/` porque
    `treinar_final` nao rodou trocaria um campo errado por uma pagina em
    branco.
    """

    def locais_do_modelo(self):
        from ml import persistencia

        nome = getattr(settings, 'PAINEL_MODELO', 'entrega1_baa')
        try:
            metadados = persistencia.ler_metadados(nome)
        except (persistencia.ArtefatoAusente, persistencia.ArtefatoIncompativel):
            return ()
        return tuple(metadados.get('locais') or ())

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto['locais_do_modelo'] = self.locais_do_modelo()
        return contexto


class LocalRecifeList(LocaisDoModeloNoContextoMixin, OfflineModeMixin,
                      generics.ListAPIView):
    serializer_class = LocalRecifeListSerializer

    def get_queryset(self):
        return LocalRecife.objects.filter(ativo=True).prefetch_related('especies')


class LocalRecifeDetail(CoberturaNoContextoMixin, LocaisDoModeloNoContextoMixin,
                        OfflineModeMixin, generics.RetrieveAPIView):
    """O recife inteiro: ficha, especies e **o acervo completo de medicoes**.

    ⚠️ `CoberturaNoContextoMixin` entra aqui pelo mesmo motivo que entra no
    catalogo — o serializer precisa do resumo agregado das medicoes, e sem ele
    `acervo.get_acervo` faria a propria agregacao a cada resposta. E a mesma
    consulta; a diferenca e quem paga por ela.

    ⚠️ **So no detalhe.** `LocalRecifeList` continua sem o acervo: o cartao da
    lista nao o mostra, e injeta-lo ali seria uma agregacao por requisicao de
    uma pagina que nao a usa.
    """

    serializer_class = LocalRecifeDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return LocalRecife.objects.filter(ativo=True).prefetch_related('especies')


class DatasetCatalogoList(CoberturaNoContextoMixin, OfflineModeMixin,
                          generics.ListAPIView):
    serializer_class = DatasetCatalogoSerializer

    def get_queryset(self):
        return DatasetCatalogo.objects.filter(ativo=True)


class LocalRecifeDatasetRelacionadosList(CoberturaNoContextoMixin,
                                         OfflineModeMixin,
                                         generics.ListAPIView):
    serializer_class = DatasetCatalogoSerializer

    def get_local(self):
        if not hasattr(self, '_local'):
            self._local = get_object_or_404(
                LocalRecife.objects.filter(ativo=True),
                slug=self.kwargs['slug'],
            )
        return self._local

    def get_queryset(self):
        local = self.get_local()
        filtros = Q(local_slug=local.slug)

        if local.nome:
            filtros |= Q(localizacao__iexact=local.nome)

        if local.estado and local.cidade:
            filtros |= (
                Q(local_slug='')
                & Q(estado__iexact=local.estado)
                & Q(cidade__iexact=local.cidade)
            )

        return DatasetCatalogo.objects.filter(ativo=True).filter(filtros).distinct()


class ApiStatusView(generics.GenericAPIView):
    """Status simples para frontend identificar modo offline."""

    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(
            {
                'offline_mode': getattr(settings, 'OFFLINE_MODE', False),
                'message': (
                    'Site em manutencao para reestruturacao de backend e banco de dados.'
                    if getattr(settings, 'OFFLINE_MODE', False)
                    else 'Servico online.'
                )
            }
        )


class GrafoLocalizacaoList(OfflineModeMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        try:
            payload = listar_localizacoes_grafo()
        except Neo4jServiceError:
            return Response(
                {'detail': 'Neo4j indisponivel no momento.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(payload)


class GrafoLocalizacaoDetail(OfflineModeMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, slug, *args, **kwargs):
        try:
            payload = obter_localizacao_grafo(slug)
        except Neo4jServiceError:
            return Response(
                {'detail': 'Neo4j indisponivel no momento.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if payload is None:
            return Response(
                {'detail': 'Localizacao nao encontrada no grafo.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(payload)


class MedicaoAmbientalList(OfflineModeMixin, generics.ListAPIView):
    """A serie ambiental — 57.420 medicoes, com proveniencia por valor.

    Ate 27/07/2026 **este endpoint nao existia**. As medicoes que a ingestao
    grava desde 25/07 nao eram servidas por nada: o `monitoramento/` devolve
    `StatusPredicao`, o modelo legado, com 3 registros. Mesmo padrao que o grafo
    tinha — o dado novo no PostgreSQL e ninguem lendo.

    **Filtros** (todos opcionais, todos combinaveis):

    | Parametro | Exemplo | O que faz |
    |---|---|---|
    | `local` | `abrolhos-ba` | so um recife |
    | `variavel` | `sst` | pode repetir: `?variavel=sst&variavel=dhw` |
    | `fonte` | `noaa_crw` | so uma fonte |
    | `de` / `ate` | `2026-01-01` | recorte de periodo, inclusivo |
    | `qualidade` | `ok` | filtra pelo flag |
    | `formato` | `csv` | baixa o recorte inteiro, sem paginacao |

    ⚠️ **`valor` pode vir nulo, e isso e informacao.** Significa que a
    validacao fisica reprovou o valor; `observacao` diz por que. Quem consome
    **nao deve** tratar nulo como zero — foi exatamente o defeito do pipeline
    legado, que gravava pH 0 e salinidade 0.

    🚨 **`formato=csv` existe para o site ser citavel.** Ate 31/07/2026 o
    unico download oferecido pelo projeto era o `url_download` do catalogo, que
    aponta para o **provedor** — ou seja, um banco de dados publico sem
    nenhuma forma de baixar o que ele mesmo guarda. O CSV sai com as colunas de
    proveniencia junto, e nao so com data e valor: sem `fonte` e
    `quality_flag`, o arquivo baixado perde exatamente o que distingue esta
    serie de uma planilha qualquer.
    """

    serializer_class = MedicaoAmbientalSerializer
    # Declarada na view, e nao em `DEFAULT_PAGINATION_CLASS`: liga-la
    # globalmente trocaria a resposta de toda lista de array para envelope, e
    # quatro endpoints ja sao consumidos como array. Ver settings.py.
    pagination_class = PaginacaoPadrao

    # A ordem e explicita e nao herdada do Meta do modelo: paginacao sobre
    # queryset sem ordem determinista repete e pula linhas entre paginas, e o
    # Django avisa isso com UnorderedObjectListWarning.
    ORDEM = ('-data', 'local_recife__slug', 'variavel', 'fonte')

    def get_queryset(self):
        parametros = self.request.query_params
        queryset = (
            MedicaoAmbiental.objects
            .select_related('local_recife')
            .order_by(*self.ORDEM)
        )

        local = parametros.get('local')
        if local:
            queryset = queryset.filter(local_recife__slug=local)

        variaveis = parametros.getlist('variavel')
        if variaveis:
            queryset = queryset.filter(variavel__in=variaveis)

        fonte = parametros.get('fonte')
        if fonte:
            queryset = queryset.filter(fonte=fonte)

        qualidade = parametros.get('qualidade')
        if qualidade:
            queryset = queryset.filter(quality_flag=qualidade)

        de = parametros.get('de')
        if de:
            queryset = queryset.filter(data__gte=de)

        ate = parametros.get('ate')
        if ate:
            queryset = queryset.filter(data__lte=ate)

        return queryset

    # A ordem das colunas do CSV e contrato: quem escreve um script contra
    # este arquivo depende dela. As quatro ultimas sao a proveniencia, e vem
    # junto de proposito — ver a nota em `formato=csv` acima.
    COLUNAS_CSV = (
        'local', 'data', 'variavel', 'valor', 'unidade',
        'fonte', 'dataset_id', 'quality_flag', 'observacao',
    )

    def list(self, request, *args, **kwargs):
        """Recusa data invalida em vez de devolver a serie inteira.

        Sem isto, `?de=ontem` seria ignorado pelo filtro e o cliente receberia
        **tudo**, achando que recebeu o recorte que pediu. Falhar alto e melhor
        que responder o numero errado em silencio.
        """
        from django.core.exceptions import ValidationError

        try:
            if request.query_params.get('formato') == 'csv':
                # 🚨 O bloqueio mora **so** aqui dentro, e nao em
                # `permission_classes` da view — as duas saidas de `list()`
                # compartilham o mesmo metodo, e um `permission_classes`
                # travaria tambem o JSON que alimenta o grafico publico do
                # recife. Ver PLANEJAMENTO.md sobre baixar dados exigir conta
                # aprovada.
                if not aprovado_para_contribuir(request.user):
                    codigo = (
                        status.HTTP_401_UNAUTHORIZED
                        if not request.user.is_authenticated
                        else status.HTTP_403_FORBIDDEN
                    )
                    return Response(
                        {'detail': 'Faca login com uma conta aprovada para baixar dados.'},
                        status=codigo,
                    )
                return self._csv(self.get_queryset())
            return super().list(request, *args, **kwargs)
        except (ValidationError, ValueError) as erro:
            return Response(
                {'detail': f'Parametro de data invalido: {erro}. '
                           'Use o formato AAAA-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def _csv(self, queryset):
        """O recorte inteiro, em streaming.

        ⚠️ **Sem paginacao, de proposito.** Um download paginado obrigaria
        quem baixa a costurar 575 arquivos para ter a serie, e a primeira
        pagina passaria por "os dados" com facilidade demais.

        `StreamingHttpResponse` porque o recorte sem filtro sao 57 mil linhas:
        montar a lista inteira em memoria antes de responder e desnecessario
        quando o cliente ja consegue consumir enquanto o servidor escreve.

        🚨 **Valor nulo sai como celula vazia, nunca como 0.** Zero e leitura
        valida de varias destas variaveis, e escreve-lo no lugar de "reprovado
        na validacao" e o defeito do pipeline legado, agora em formato de
        arquivo que o leitor abre no Excel sem nenhum aviso por perto.
        """
        import csv

        from django.http import StreamingHttpResponse

        class _Eco:
            def write(self, valor):
                return valor

        escritor = csv.writer(_Eco())
        campos = ('local_recife__slug', 'data', 'variavel', 'valor', 'unidade',
                  'fonte', 'dataset_id', 'quality_flag', 'observacao')

        def linhas():
            yield escritor.writerow(self.COLUNAS_CSV)
            for linha in queryset.values_list(*campos).iterator(chunk_size=2000):
                yield escritor.writerow(
                    ['' if valor is None else valor for valor in linha]
                )

        resposta = StreamingHttpResponse(linhas(), content_type='text/csv')
        resposta['Content-Disposition'] = (
            f'attachment; filename="{self._nome_do_arquivo()}"'
        )
        return resposta

    def _nome_do_arquivo(self):
        """Nome que descreve o recorte, e nao so o endpoint.

        Tres arquivos chamados `medicoes.csv` na pasta de downloads sao tres
        arquivos indistinguiveis. O nome carrega os filtros que os separam.
        """
        parametros = self.request.query_params
        partes = ['medicoes']
        for chave in ('local', 'fonte', 'de', 'ate'):
            valor = parametros.get(chave)
            if valor:
                partes.append(slugify(valor))
        partes += [slugify(v) for v in parametros.getlist('variavel')]
        return '-'.join(partes) + '.csv'


class ModeloIndisponivel(Exception):
    """O artefato do modelo nao esta utilizavel. Vira 503."""


class PainelRiscoBase(OfflineModeMixin, APIView):
    """O primeiro endpoint do projeto que **faz conta** em vez de servir dado.

    Todos os outros devolvem linha guardada. Este carrega o modelo persistido,
    monta a janela de 7 dias a partir da serie do PostgreSQL e responde uma
    probabilidade — e por isso e o unico ponto onde o artefato, a serie e o
    limiar declarado se encontram.

    **O contrato nao e escolhido aqui.** As colunas, o horizonte, o alvo e os
    locais vem dos metadados gravados por `treinar_final`. A view obedece ao
    artefato; nao ha lista de features duplicada neste arquivo.

    Tres comportamentos que sao decisao, e nao acidente:

    | Situacao | Resposta | Por que |
    |---|---|---|
    | artefato ausente | **503** | derivado e regeravel; servir predicao de origem desconhecida seria pior |
    | janela incompleta | item com `disponivel: false` | zero e valor legitimo de variacao; preencher mentiria |
    | local fora do treino | **404** com motivo | o modelo viu tres recifes; o quarto seria extrapolacao |
    """

    def modelo(self):
        """Carrega artefato e metadados, ou levanta com recado acionavel."""
        from ml import persistencia, predicao

        nome = getattr(settings, 'PAINEL_MODELO', 'entrega1_baa')
        try:
            return predicao.carregar_modelo(nome)
        except (persistencia.ArtefatoAusente, persistencia.ArtefatoIncompativel) as erro:
            raise ModeloIndisponivel(str(erro)) from erro

    def limiar(self):
        return float(getattr(settings, 'PAINEL_LIMIAR', 0.20))

    def escala(self):
        """A escala de aviso configurada, ou a canonica de `ml/niveis.py`."""
        from ml import niveis

        return niveis.de_configuracao(getattr(settings, 'PAINEL_NIVEIS', None))

    def nivel_como_payload(self, risco):
        nivel = risco.nivel(self.escala())
        return {
            'slug': nivel.slug,
            'rotulo': nivel.rotulo,
            'corte': nivel.corte,
            'acao': nivel.acao,
            'exige_acao': nivel.exige_acao,
        }

    def cabecalho(self, metadados):
        """O bloco `modelo`: o que a probabilidade quer dizer.

        ⚠️ `alvo` e `calibracao` nao sao metadado decorativo. O primeiro diz
        que a previsao e de **estresse termico** e nao de branqueamento
        observado — a regua da NOAA perde 78 dos 88 branqueamentos brasileiros
        (docs/RESULTADOS.md secao 11). O segundo diz se o numero exibido e cru
        ou recalibrado, diferenca que vale 0,081 de ECE.
        """
        return {
            'nome': metadados.get('nome'),
            'algoritmo': metadados.get('modelo'),
            'alvo': metadados.get('alvo'),
            'horizonte_dias': metadados.get('horizonte_dias'),
            'calibracao': metadados.get('calibracao'),
            # A isotonica e funcao escada: dois recifes com entradas diferentes
            # podem sair com a mesma probabilidade, e isso parece defeito sem
            # este aviso. Sao 313 valores distintos sobre 7.095 amostras.
            'probabilidade_em_degraus': metadados.get('calibracao') == 'isotonic',
            'colunas': metadados.get('colunas', []),
            'treinado_em': metadados.get('gerado_em'),
            'n_treino': metadados.get('n_treino'),
            'limiar': self.limiar(),
            # A escala inteira viaja junto: sem ela, quem consome ve o nome do
            # nivel e nao tem como saber de que corte ele veio. Mesma razao
            # pela qual `limiar` acompanha `probabilidade` desde 27/07.
            'escala': self.escala_como_payload(),
        }

    def escala_como_payload(self):
        from ml import niveis

        return niveis.como_payload(self.escala())

    def avaliar(self, local, ajuste, assinatura=None):
        """Um item da resposta. Nunca levanta por falta de dado.

        Com `assinatura` (o par `(ultima_data, quantas)` da serie do local), o
        resultado e memorizado — ver `backend/memoria/`. Sem ela, calcula
        sempre: e o que os testes e qualquer chamador antigo continuam fazendo.
        """
        if assinatura is None:
            return self._avaliar_sem_memoria(local, ajuste)

        import memoria
        from ml import predicao

        nome_da_chave = memoria.chave(
            'painel',
            local.slug,
            assinatura,
            # 🚨 A identidade do artefato. Sem isto, retreinar o modelo nao
            # mudaria o painel ate a proxima ingestao - o cache serviria a
            # probabilidade do modelo anterior com cara de atual.
            predicao.marca_do_modelo(
                getattr(settings, 'PAINEL_MODELO', 'entrega1_baa')
            ),
            self.limiar(),
            self.escala_como_payload(),
            # 🚨 `dias_de_atraso` e `hoje - data_base`. Sem a data na chave, a
            # virada do dia congelaria o atraso, e o campo que existe para nao
            # deixar dado velho parecer novo passaria a mentir por causa do
            # cache.
            timezone.localdate().isoformat(),
        )
        return memoria.lembrar(
            nome_da_chave, lambda: self._avaliar_sem_memoria(local, ajuste)
        )

    def _avaliar_sem_memoria(self, local, ajuste):
        from ml import predicao

        base = {'local': local.slug, 'nome': local.nome}
        try:
            risco = predicao.calcular(local, ajuste, self.limiar())
        except predicao.SemDadoSuficiente as erro:
            # Falta de dado e estado normal de um recife, nao erro da
            # requisicao: o local existe, a serie e que nao fecha. Devolver 500
            # aqui derrubaria os outros dois recifes junto.
            return {
                **base,
                'disponivel': False,
                'motivo': str(erro),
                'faltando': [
                    {'variavel': v, 'data': d.isoformat()} for v, d in erro.faltando
                ],
            }

        return {
            **base,
            'disponivel': True,
            'data_base': risco.data_base.isoformat(),
            'data_alvo': risco.data_alvo.isoformat(),
            # ⚠️ Vai no payload de proposito. A serie tem latencia, e ela
            # varia; sem isto um risco calculado sobre dado de tres semanas
            # atras se apresenta igualzinho a um calculado sobre ontem.
            'dias_de_atraso': risco.dias_de_atraso,
            # ⚠️ Quais variaveis seguram a `data_base` — vazio quando a borda
            # da serie e reta. Desde 30/07/2026 a borda irregular deixou de
            # bloquear a resposta (ml/predicao.py::_borda_completa), e este
            # campo e o que impede a troca sair de graca: sem ele, uma fonte
            # que quebre de vez apareceria so como "dado um pouco mais velho".
            'limitado_por': list(risco.limitado_por),
            'probabilidade': round(risco.probabilidade, 4),
            'limiar': risco.limiar,
            'alerta': risco.alerta,
            # 🚨 O degrau da escala, desde 30/07/2026. Um corte unico obrigava
            # a escolher entre cobrir tudo (0,05, com metade dos avisos falsos)
            # e ser levado a serio (0,20, descartando episodios que o modelo
            # pegava). Com tres degraus os dois objetivos deixam de competir.
            # `alerta` continua ao lado, porque e contrato desde 27/07.
            # Ver ml/niveis.py.
            'nivel': self.nivel_como_payload(risco),
            # 🚨 A probabilidade saiu 0 ou 1 exatos. A recalibracao isotonica
            # e funcao escada: 12,2% das amostras de treino caem em p = 0,000.
            # Isso significa "nenhum alerta neste degrau", e nao "impossivel".
            # A interface **nao deve** exibir "0%" nem "100%" quando for true.
            # Ver ml/predicao.py::Risco.no_extremo.
            'no_extremo': risco.no_extremo,
            'entradas': {k: round(v, 4) for k, v in risco.entradas.items()},
        }


class PainelRiscoList(PainelRiscoBase):
    """Risco dos recifes que o modelo viu no treino."""

    def get(self, request):
        try:
            ajuste, metadados = self.modelo()
        except ModeloIndisponivel as erro:
            return Response(
                {'detail': str(erro)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        slugs = metadados.get('locais') or []
        locais = {
            local.slug: local
            for local in LocalRecife.objects.filter(slug__in=slugs)
        }

        # Uma consulta agrupada para todos os locais, e nao uma por local: o
        # ganho do cache seria comido de volta por N agregacoes. Ver
        # `memoria.assinatura_das_series`.
        import memoria

        assinaturas = memoria.assinatura_das_series(slugs)

        # A ordem segue os metadados, e nao o banco: e a lista que o modelo
        # declara ter visto, e ela e o contrato.
        resultados = [
            self.avaliar(locais[slug], ajuste, assinaturas.get(slug))
            for slug in slugs if slug in locais
        ]

        return Response({
            'modelo': self.cabecalho(metadados),
            'results': resultados,
        })


class PainelRiscoDetail(PainelRiscoBase):
    """Risco de um recife. 404 com motivo quando o modelo nao o viu."""

    def get(self, request, slug):
        try:
            ajuste, metadados = self.modelo()
        except ModeloIndisponivel as erro:
            return Response(
                {'detail': str(erro)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        treinados = metadados.get('locais') or []
        if slug not in treinados:
            # 🚨 Nao extrapolar e o ponto. O modelo viu tres pontos do litoral
            # brasileiro; responder sobre um quarto seria inventar cobertura
            # que nenhuma medicao sustenta.
            return Response(
                {'detail': f'O modelo nao foi treinado em "{slug}". '
                           f'Locais disponiveis: {treinados}.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        local = get_object_or_404(LocalRecife, slug=slug)

        import memoria

        assinatura = memoria.assinatura_das_series([slug]).get(slug)
        return Response({
            'modelo': self.cabecalho(metadados),
            **self.avaliar(local, ajuste, assinatura),
        })
