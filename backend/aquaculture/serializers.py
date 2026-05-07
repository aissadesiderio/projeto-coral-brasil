from rest_framework import serializers

from .models import Especie, LocalRecife, StatusPredicao


class StatusPredicaoSerializer(serializers.ModelSerializer):
    local_recife_slug = serializers.SlugRelatedField(
        source='local_recife',
        read_only=True,
        slug_field='slug',
    )

    class Meta:
        model = StatusPredicao
        fields = [
            'id',
            'local_recife_slug',
            'data',
            'sst_atual',
            'limite_termico',
            'anomalia',
            'dhw_calculado',
            'nivel_alerta',
            'risco_integrado',
            'turbidez',
            'irradiancia',
            'salinidade',
            'ph',
            'oxigenio',
            'nitrato',
            'clorofila',
        ]


class EspecieSerializer(serializers.ModelSerializer):
    foto_url = serializers.SerializerMethodField()
    locais = serializers.SlugRelatedField(many=True, read_only=True, slug_field='slug')

    class Meta:
        model = Especie
        fields = [
            'id',
            'nome_cientifico',
            'nome_comum',
            'tipo',
            'descricao',
            'status_conservacao',
            'foto',
            'foto_url',
            'credito_imagem',
            'fonte_imagem_url',
            'fonte_url',
            'locais',
        ]

    def get_foto_url(self, obj):
        if not obj.foto:
            return ''

        request = self.context.get('request')
        url = obj.foto.url
        return request.build_absolute_uri(url) if request else url


class LocalRecifeListSerializer(serializers.ModelSerializer):
    imagem_url = serializers.SerializerMethodField()
    informacoes_disponiveis = serializers.SerializerMethodField()
    possui_painel_risco = serializers.SerializerMethodField()

    class Meta:
        model = LocalRecife
        fields = [
            'id',
            'slug',
            'nome',
            'estado',
            'cidade',
            'descricao',
            'imagem_url',
            'ultima_atualizacao',
            'informacoes_disponiveis',
            'possui_painel_risco',
        ]

    def get_imagem_url(self, obj):
        if not obj.imagem:
            return ''

        request = self.context.get('request')
        url = obj.imagem.url
        return request.build_absolute_uri(url) if request else url

    def get_informacoes_disponiveis(self, obj):
        return obj.especies.count()

    def get_possui_painel_risco(self, obj):
        return bool(self._get_monitoramento(obj))

    def _get_monitoramento(self, obj):
        return (
            obj.monitoramentos.order_by('-data').first()
            or StatusPredicao.objects.filter(local_recife__isnull=True).order_by('-data').first()
        )


class LocalRecifeDetailSerializer(LocalRecifeListSerializer):
    especies = serializers.SerializerMethodField()
    monitoramento_recente = serializers.SerializerMethodField()

    class Meta(LocalRecifeListSerializer.Meta):
        fields = LocalRecifeListSerializer.Meta.fields + [
            'especies',
            'monitoramento_recente',
        ]

    def get_especies(self, obj):
        especies = obj.especies.order_by('nome_comum', 'nome_cientifico')
        return EspecieSerializer(especies, many=True, context=self.context).data

    def get_monitoramento_recente(self, obj):
        monitoramento = self._get_monitoramento(obj)
        if not monitoramento:
            return None

        return StatusPredicaoSerializer(monitoramento, context=self.context).data
