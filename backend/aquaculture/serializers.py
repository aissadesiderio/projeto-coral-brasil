from rest_framework import serializers

from .models import (
    DatasetCatalogo,
    Especie,
    LocalRecife,
    MedicaoAmbiental,
)


class EspecieSerializer(serializers.ModelSerializer):
    """A especie, com a proveniencia da categoria de conservacao junto.

    🚨 `iucn_tem_procedencia` viaja no payload de proposito, e nao e derivavel
    com seguranca por quem consome: ele diz que a categoria **pode ser exibida
    como afirmacao**. Deixar cada cliente inventar essa regra e como deixar cada
    um inventar o limiar do alerta — dois lugares decidindo a mesma coisa, com
    liberdade para divergirem em silencio.
    """

    foto_url = serializers.SerializerMethodField()
    locais = serializers.SlugRelatedField(many=True, read_only=True, slug_field='slug')
    iucn_tem_procedencia = serializers.BooleanField(read_only=True)
    iucn_categoria_rotulo = serializers.CharField(
        source='get_iucn_categoria_display', read_only=True,
    )

    class Meta:
        model = Especie
        fields = [
            'id',
            'nome_cientifico',
            'nome_comum',
            'tipo',
            'descricao',
            'iucn_origem',
            'iucn_categoria',
            'iucn_categoria_rotulo',
            'iucn_avaliado_em',
            'iucn_versao',
            'iucn_consultado_em',
            'iucn_taxon_id',
            'fonte_iucn_url',
            'iucn_tem_procedencia',
            'aphia_id',
            'gbif_key',
            'status_taxonomico',
            'nome_aceito',
            'foto',
            'foto_url',
            'credito_imagem',
            'fonte_imagem_url',
            'local_captura_foto',
            'fonte_url',
            'locais',
        ]

    def get_foto_url(self, obj):
        if not obj.foto:
            return ''

        request = self.context.get('request')
        url = obj.foto.url
        return request.build_absolute_uri(url) if request else url

    def to_representation(self, instance):
        """Acrescenta `autor` — mas so para quem pode ver.

        🚨 A chave **some** para quem nao e master, em vez de sair como
        `null`. Nulo aqui teria dois significados possiveis ("ninguem
        registrado" e "escondido de voce"), e essa e exatamente a ambiguidade
        que o bug do "Nao avaliado" na migracao 0022 ja ensinou a evitar.

        Reaproveitado nos tres lugares que usam este serializer
        (`/api/especies/`, `/api/especies/<id>/` e
        `LocalRecifeDetailSerializer.get_especies`), porque a checagem mora
        aqui, nao em cada view.
        """
        dados = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user and request.user.is_superuser:
            dados['autor'] = {
                'criado_por': instance.criado_por.username if instance.criado_por else None,
                'editado_por': instance.editado_por.username if instance.editado_por else None,
                'editado_em': instance.editado_em,
            }
        return dados


class EspecieContribuicaoSerializer(serializers.ModelSerializer):
    """A lista branca do que uma conta aprovada pode propor por API.

    🚨 **Lista branca por construcao, nao filtro depois do fato.** E por
    isso que categoria IUCN, taxonomia e foto nunca aparecem aqui — nem para
    master, que ja tem o Django admin com esses campos. A alternativa
    ("aceitar tudo e remover os sensiveis antes de salvar") regride sozinha
    toda vez que alguem acrescenta um campo a `Especie` e esquece de
    bloquea-lo aqui; esta lista so cresce por decisao explicita.

    Uma tentativa de mandar `iucn_categoria` ou `foto` no corpo nao e
    ignorada em silencio — `to_internal_value` recusa com 400 nomeando o
    campo, para quem estiver testando a API direto perceber que e regra, nao
    bug.
    """

    locais = serializers.SlugRelatedField(
        many=True, slug_field='slug', queryset=LocalRecife.objects.all(), required=False,
    )

    class Meta:
        model = Especie
        fields = [
            'id',
            'nome_cientifico',
            'nome_comum',
            'tipo',
            'descricao',
            'credito_imagem',
            'fonte_imagem_url',
            'local_captura_foto',
            'fonte_url',
            'locais',
        ]
        read_only_fields = ['id']

    def to_internal_value(self, data):
        campos_aceitos = set(self.fields) - set(self.Meta.read_only_fields)
        campos_recusados = set(data.keys()) - campos_aceitos
        if campos_recusados:
            raise serializers.ValidationError({
                campo: 'Campo nao aceito em contribuicoes publicas.'
                for campo in campos_recusados
            })
        return super().to_internal_value(data)


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
        """O recife esta entre os que o modelo servido viu no treino?

        🚨 **Ate 30/07/2026 este campo respondia outra pergunta**, e a resposta
        era falsa: `bool(StatusPredicao)`, com queda para o registro global
        quando o recife nao tinha o seu. Como a migracao 0011 semeou tres
        registros de demonstracao e um global, o campo dizia `true` para
        **qualquer** recife cadastrado — inclusive um recem-criado, sobre o
        qual o painel devolve 404.

        Agora ele sai da mesma fonte que decide o 404: a lista `locais` dos
        metadados do artefato, injetada no contexto pela view. Sem artefato o
        campo e `false`, que e a resposta certa — sem modelo nao ha painel.
        """
        return obj.slug in (self.context.get('locais_do_modelo') or ())


class LocalRecifeDetailSerializer(LocalRecifeListSerializer):
    especies = serializers.SerializerMethodField()

    class Meta(LocalRecifeListSerializer.Meta):
        fields = LocalRecifeListSerializer.Meta.fields + ['especies']

    def get_especies(self, obj):
        especies = obj.especies.order_by('nome_comum', 'nome_cientifico')
        return EspecieSerializer(especies, many=True, context=self.context).data


class DatasetCatalogoSerializer(serializers.ModelSerializer):
    """Um item do catalogo, **com a cobertura real medida ao lado**.

    ⚠️ `data_inicio`/`data_fim` descrevem o produto **no provedor**;
    `cobertura` descreve o que **este projeto** tem. Sao perguntas diferentes,
    e antes de 27/07/2026 so a primeira era respondida — o que fazia a pagina
    anunciar seis datasets sem uma unica medicao no banco.

    A view coloca o resumo das medicoes em `context['medicoes']`, numa consulta
    so para a lista inteira. Sem ele, cada item mede sozinho.
    """

    tamanho_mb = serializers.FloatField(allow_null=True)
    cobertura = serializers.SerializerMethodField()

    class Meta:
        model = DatasetCatalogo
        fields = [
            'id',
            'titulo',
            'resumo',
            'fonte',
            'tipo_dado',
            'localizacao',
            'local_slug',
            'estado',
            'cidade',
            'formato',
            'recorte_temporal',
            'data_inicio',
            'data_fim',
            'data_publicacao',
            'periodo_rotulo',
            'tamanho_mb',
            'url_download',
            'cobertura',
        ]

    def get_cobertura(self, obj):
        from . import cobertura

        # Sem contexto, mede este item sozinho. Custa uma consulta, e e melhor
        # que devolver `null` — campo ausente seria lido como "sem cobertura",
        # que e uma afirmacao diferente de "nao medido".
        return cobertura.para(obj, self.context.get('medicoes'))


class MedicaoAmbientalSerializer(serializers.ModelSerializer):
    """Uma medicao, **com a proveniencia junto**.

    ⚠️ `fonte`, `dataset_id` e `quality_flag` nao sao campos opcionais nem
    ficam atras de um parametro. Proveniencia por valor e a contribuicao central
    do projeto (docs/VISAO_GERAL.md secao 8); servir o numero sem dizer de onde
    ele veio entregaria exatamente o que este projeto existe para nao fazer.

    `valor` pode ser **nulo**, e o nulo e informacao: significa que a validacao
    fisica reprovou o valor, e `observacao` diz por que. O codigo legado
    preenchia essas lacunas com zero — gravando pH 0 e salinidade 0, que sao
    fisicamente impossiveis. Aqui o nulo sai como nulo.
    """

    local = serializers.SlugField(source='local_recife.slug', read_only=True)

    class Meta:
        model = MedicaoAmbiental
        fields = [
            'id',
            'local',
            'data',
            'variavel',
            'valor',
            'unidade',
            # --- proveniencia ---
            'fonte',
            'dataset_id',
            'quality_flag',
            'observacao',
        ]
