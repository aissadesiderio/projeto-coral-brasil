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
    tem_coordenadas = serializers.BooleanField(read_only=True)
    motivo_sem_serie = serializers.SerializerMethodField()
    imagem_tem_procedencia = serializers.BooleanField(read_only=True)

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
            'latitude',
            'longitude',
            'tem_coordenadas',
            'fonte_coordenadas',
            'motivo_sem_serie',
            # 🚨 **Existiam no modelo desde a migracao 0014 e nunca sairam do
            # Django admin.** Nao entram em nenhuma conta do modelo — e era
            # justamente por isso que ninguem tinha reparado na ausencia: um
            # campo que a previsao nao usa nao quebra nada quando some. Mas o
            # site se apresenta como banco de dados de recifes, e profundidade
            # e area sao dois dos poucos atributos fisicos que ele tem para dar
            # sobre um recife. Vazio continua vazio; quem le a tela distingue
            # "nao registrado" de "nao existe".
            'profundidade_media_m',
            'area_km2',
            # --- proveniencia da foto (migracao 0030) ----------------------
            # ⚠️ `imagem_url` continua saindo com o que houver no banco, com ou
            # sem credito — a regra de "sem procedencia nao entra" vale para a
            # **copia versionada** (`code_sync`), nao para a API. E a mesma
            # divisao ja escolhida para a foto de especie em docs/FONTES.md
            # §2.1: a API serve o acervo, a tela decide o que afirmar, e
            # `imagem_tem_procedencia` e o que ela usa para decidir.
            'credito_imagem',
            'fonte_imagem_url',
            'local_captura_foto',
            'imagem_tem_procedencia',
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

    def get_motivo_sem_serie(self, obj):
        """A explicacao derivada no modelo — ver `LocalRecife.motivo_sem_serie`.

        ⚠️ O texto nao mora aqui de proposito: `code_sync` grava o mesmo campo
        na copia de fallback do frontend, e duas redacoes da mesma explicacao
        divergiriam no primeiro ajuste.
        """
        return obj.motivo_sem_serie


class LocalRecifeDetailSerializer(LocalRecifeListSerializer):
    especies = serializers.SerializerMethodField()
    acervo = serializers.SerializerMethodField()

    class Meta(LocalRecifeListSerializer.Meta):
        fields = LocalRecifeListSerializer.Meta.fields + ['especies', 'acervo']

    def get_especies(self, obj):
        especies = obj.especies.order_by('nome_comum', 'nome_cientifico')
        return EspecieSerializer(especies, many=True, context=self.context).data

    def get_acervo(self, obj):
        """Toda variavel medida neste local, e nao so as que a previsao usa.

        🚨 O grafico da pagina desenha `sst` e `dhw` por razao medida
        (docs/RESULTADOS.md §7), e ate 12/08/2026 esse recorte era **tudo** o
        que o site dizia ter: as outras seis variaveis ingeridas — ~7.200
        medicoes de cada, por local — nao apareciam em numero nenhum. Escolher
        o que desenhar e uma decisao legitima; nao dizer o que se tem e outra
        coisa.

        ⚠️ So no detalhe, nunca na lista. Na lista seriam N locais chamando a
        mesma agregacao, e o cartao nao tem onde mostrar isso.
        """
        from . import acervo

        return acervo.para_local(obj.slug, self.context.get('medicoes'))


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
            # ⚠️ Viaja no payload porque a tela nao consegue deduzi-lo da URL
            # sem duplicar a regra de permissao da view. Ver o comentario do
            # campo em `models.DatasetCatalogo`.
            'download_exige_conta',
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
