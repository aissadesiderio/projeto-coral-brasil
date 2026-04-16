from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Especie, StatusPredicao 
from .serializers import EspecieSerializer, StatusPredicaoSerializer


class OfflineModeMixin:
    """Bloqueia endpoints públicos quando o site está em manutenção/offline."""

    def list(self, request, *args, **kwargs):
        if getattr(settings, 'OFFLINE_MODE', False):
            return Response(
                {
                    'detail': (
                        'Site temporariamente offline para reestruturação de backend '
                        'e banco de dados.'
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return super().list(request, *args, **kwargs)

# Esta view vai controlar a "lista" de todos os corais
# Ex: /api/especies/
class EspecieList(OfflineModeMixin, generics.ListAPIView):
    queryset = Especie.objects.all() # Pega todos os objetos Especie
    serializer_class = EspecieSerializer # Usa o tradutor que criamos

# Esta view vai controlar um "item único"
# Ex: /api/especies/1/
class EspecieDetail(generics.RetrieveAPIView):
    queryset = Especie.objects.all()
    serializer_class = EspecieSerializer

class StatusPredicaoList(OfflineModeMixin, generics.ListAPIView):
    # Pega todos os alertas e ordena do mais recente para o mais antigo
    queryset = StatusPredicao.objects.all().order_by('-data')
    serializer_class = StatusPredicaoSerializer


class ApiStatusView(generics.GenericAPIView):
    """Status simples para frontend identificar modo offline."""

    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(
            {
                'offline_mode': getattr(settings, 'OFFLINE_MODE', False),
                'message': (
                    'Site em manutenção para reestruturação de backend e banco de dados.'
                    if getattr(settings, 'OFFLINE_MODE', False)
                    else 'Serviço online.'
                )
            }
        )
