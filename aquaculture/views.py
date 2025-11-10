from rest_framework import generics
from .models import Especie
from .serializers import EspecieSerializer

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
