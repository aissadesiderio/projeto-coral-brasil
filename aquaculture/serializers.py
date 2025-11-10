from rest_framework import serializers
# 1. Importe TecnicaManejo
from .models import Especie, Parametro, TecnicaManejo 

# (Mini-tradutor Parametro... já estava aqui)
class ParametroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parametro
        fields = ['id', 'nome', 'valor', 'unidade']

# 2. Crie o "mini-tradutor" para as técnicas
class TecnicaManejoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TecnicaManejo
        fields = ['id', 'nome', 'descricao'] # O que queremos mostrar

# 3. Atualize o "tradutor-chefe"
class EspecieSerializer(serializers.ModelSerializer):
    # ... (O 'parametros' já estava aqui)
    parametros = ParametroSerializer(many=True, read_only=True)

    # 4. Esta é a mágica para as técnicas!
    # (related_name='tecnicas')
    tecnicas = TecnicaManejoSerializer(many=True, read_only=True)

    class Meta:
        model = Especie
        # 5. Adicione 'tecnicas' na lista de campos
        fields = [
            'id', 
            'nome_cientifico', 
            'nome_comum', 
            'descricao', 
            'status_conservacao', 
            'foto_url',
            'parametros',
            'tecnicas'  # <-- O campo novo!
        ]