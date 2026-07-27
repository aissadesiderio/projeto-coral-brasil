from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import (
    DatasetCatalogo,
    Especie,
    LocalRecife,
    MedicaoAmbiental,
    StatusPredicao,
)
from .paginacao import PaginacaoPadrao
from .neo4j_service import (
    Neo4jServiceError,
    listar_localizacoes_grafo,
    obter_localizacao_grafo,
)
from .serializers import (
    DatasetCatalogoSerializer,
    EspecieSerializer,
    LocalRecifeDetailSerializer,
    LocalRecifeListSerializer,
    MedicaoAmbientalSerializer,
    StatusPredicaoSerializer,
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
    """

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() == 'get' and getattr(settings, 'OFFLINE_MODE', False):
            return JsonResponse(
                {'detail': MENSAGEM_OFFLINE},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return super().dispatch(request, *args, **kwargs)


class EspecieList(OfflineModeMixin, generics.ListAPIView):
    serializer_class = EspecieSerializer

    def get_queryset(self):
        queryset = Especie.objects.all().prefetch_related('locais')
        local_slug = self.request.query_params.get('local')
        if local_slug:
            queryset = queryset.filter(locais__slug=local_slug).distinct()
        return queryset.order_by('nome_comum', 'nome_cientifico')


class EspecieDetail(OfflineModeMixin, generics.RetrieveAPIView):
    queryset = Especie.objects.all().prefetch_related('locais')
    serializer_class = EspecieSerializer


class LocalRecifeList(OfflineModeMixin, generics.ListAPIView):
    serializer_class = LocalRecifeListSerializer

    def get_queryset(self):
        return LocalRecife.objects.filter(ativo=True).prefetch_related('especies', 'monitoramentos')


class LocalRecifeDetail(OfflineModeMixin, generics.RetrieveAPIView):
    serializer_class = LocalRecifeDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return LocalRecife.objects.filter(ativo=True).prefetch_related('especies', 'monitoramentos')


class StatusPredicaoList(OfflineModeMixin, generics.ListAPIView):
    serializer_class = StatusPredicaoSerializer

    def get_queryset(self):
        queryset = StatusPredicao.objects.select_related('local_recife').order_by('-data')
        local_slug = self.request.query_params.get('local')
        if local_slug:
            queryset = queryset.filter(
                Q(local_recife__slug=local_slug) | Q(local_recife__isnull=True)
            )
        return queryset


class DatasetCatalogoList(OfflineModeMixin, generics.ListAPIView):
    serializer_class = DatasetCatalogoSerializer

    def get_queryset(self):
        return DatasetCatalogo.objects.filter(ativo=True)


class LocalRecifeDatasetRelacionadosList(OfflineModeMixin, generics.ListAPIView):
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

    ⚠️ **`valor` pode vir nulo, e isso e informacao.** Significa que a
    validacao fisica reprovou o valor; `observacao` diz por que. Quem consome
    **nao deve** tratar nulo como zero — foi exatamente o defeito do pipeline
    legado, que gravava pH 0 e salinidade 0.
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

    def list(self, request, *args, **kwargs):
        """Recusa data invalida em vez de devolver a serie inteira.

        Sem isto, `?de=ontem` seria ignorado pelo filtro e o cliente receberia
        **tudo**, achando que recebeu o recorte que pediu. Falhar alto e melhor
        que responder o numero errado em silencio.
        """
        from django.core.exceptions import ValidationError

        try:
            return super().list(request, *args, **kwargs)
        except (ValidationError, ValueError) as erro:
            return Response(
                {'detail': f'Parametro de data invalido: {erro}. '
                           'Use o formato AAAA-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
