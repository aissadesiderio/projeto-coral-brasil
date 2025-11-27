from rest_framework import generics
from .models import Especie, StatusPredicao 
from .serializers import EspecieSerializer, StatusPredicaoSerializer

# Esta view vai controlar a "lista" de todos os corais
# Ex: /api/especies/
class EspecieList(generics.ListAPIView):
    queryset = Especie.objects.all() # Pega todos os objetos Especie
    serializer_class = EspecieSerializer # Usa o tradutor que criamos

# Esta view vai controlar um "item único"
# Ex: /api/especies/1/
class EspecieDetail(generics.RetrieveAPIView):
    queryset = Especie.objects.all()
    serializer_class = EspecieSerializer

class StatusPredicaoList(generics.ListAPIView):
    # Pega todos os alertas e ordena do mais recente para o mais antigo
    queryset = StatusPredicao.objects.all().order_by('-data')
    serializer_class = StatusPredicaoSerializer