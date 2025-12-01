from rest_framework import serializers
from .models import Especie, StatusPredicao

class StatusPredicaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusPredicao
        #ADICIONADO: 'risco_integrado', 'turbidez', 'irradiancia'
        fields = [
            'id', 'data', 
            'sst_atual', 'limite_termico', 'anomalia', 
            'dhw_calculado', 
            'nivel_alerta', 'risco_integrado',
            'turbidez', 'irradiancia'
        ]

class EspecieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especie
        fields = '__all__' #'__all__' pega tudo automático e evita esquecer campos