from rest_framework import serializers
from .models import Especie, StatusPredicao

# Motivo: Converte os objetos do Python (Models) em JSON para o React ler.
class StatusPredicaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusPredicao
        fields = [
            'id', 'data', 
            'sst_atual', 'limite_termico', 'anomalia', 
            'dhw_calculado', 
            'nivel_alerta', 'risco_integrado',
            'turbidez', 'irradiancia',
            # Novos campos adicionados à lista de permissão da API:
            'salinidade', 
            'ph', 
            'oxigenio', 
            'nitrato', 
            'clorofila'
        ]

class EspecieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especie
        fields = '__all__' # Pega todos os campos automaticamente