#atualização sem tecnica/manejo 
from rest_framework import serializers
from .models import Especie, StatusPredicao

class StatusPredicaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusPredicao
        fields = ['id', 'data', 'sst_atual', 'limite_termico', 'anomalia', 'dhw_calculado', 'nivel_alerta']

class EspecieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especie
        fields = [
            'id', 
            'nome_cientifico', 
            'nome_comum', 
            'tipo',          #novo campo
            'descricao', 
            'status_conservacao', 
            'foto_url'
        ]
        fields = ['id', 'data', 'sst_atual', 'limite_termico', 'anomalia', 'dhw_calculado', 'nivel_alerta']