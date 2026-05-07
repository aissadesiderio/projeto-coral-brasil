from django.conf import settings
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Especie, LocalRecife, StatusPredicao
from .neo4j_service import (
    Neo4jServiceError,
    listar_localizacoes_grafo,
    obter_localizacao_grafo,
)
from .serializers import (
    EspecieSerializer,
    LocalRecifeDetailSerializer,
    LocalRecifeListSerializer,
    StatusPredicaoSerializer,
)


class OfflineModeMixin:
    """Bloqueia endpoints publicos quando o site esta em manutencao/offline."""

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() == 'get' and getattr(settings, 'OFFLINE_MODE', False):
            return Response(
                {
                    'detail': (
                        'Site temporariamente offline para reestruturacao de backend '
                        'e banco de dados.'
                    )
                },
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


class EspecieDetail(generics.RetrieveAPIView):
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
