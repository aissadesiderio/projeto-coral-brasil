from django.conf import settings
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html

from .code_sync import sync_project_code_from_db
from .models import DatasetCatalogo, Especie, LocalRecife, PerfilUsuario, SolicitacaoEspecie


class SyncToCodeAdminMixin:
    """Exporta o banco para arquivos de codigo **sob demanda**.

    Antes isto rodava automaticamente em `save_related`, `delete_model` e
    `delete_queryset`: cada edicao no admin reescrevia
    `frontend/src/recifeData.js` e `generated_admin_sync.py`, ou seja, editar
    um dado sujava a arvore do git. Agora e uma acao explicita, e os hooks
    automaticos foram removidos - mante-los, mesmo atras de
    `ENABLE_CODE_SYNC`, reintroduziria o problema assim que a flag ligasse.

    `ENABLE_CODE_SYNC` continua valendo como interruptor de seguranca: em
    producao o admin nao deve escrever no sistema de arquivos de forma alguma.

    Alternativa em linha de comando: `python manage.py sync_admin_code`.
    """

    actions = ['sincronizar_codigo']

    @admin.action(description='Sincronizar banco -> arquivos de codigo (recifeData.js)')
    def sincronizar_codigo(self, request, queryset):
        # A exportacao sempre cobre o banco inteiro; a selecao e ignorada.
        if not getattr(settings, 'ENABLE_CODE_SYNC', False):
            self.message_user(
                request,
                'Sincronizacao desativada (ENABLE_CODE_SYNC=False). Ative no '
                '.env ou use "python manage.py sync_admin_code".',
                level=messages.WARNING,
            )
            return

        try:
            result = sync_project_code_from_db()
        except Exception as exc:
            self.message_user(
                request,
                f'Falha ao sincronizar os arquivos de codigo: {exc}',
                level=messages.ERROR,
            )
            return

        if result['backend_changed'] or result['frontend_changed']:
            self.message_user(
                request,
                'Arquivos de codigo sincronizados a partir do banco.',
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                'Nada a fazer: os arquivos de codigo ja estavam atualizados.',
                level=messages.INFO,
            )


class EspecieLocalInline(admin.TabularInline):
    model = Especie.locais.through
    extra = 1
    verbose_name = 'Especie vinculada'
    verbose_name_plural = 'Especies vinculadas'
    autocomplete_fields = ('especie',)


@admin.register(LocalRecife)
class LocalRecifeAdmin(SyncToCodeAdminMixin, admin.ModelAdmin):
    list_display = (
        'nome',
        'estado',
        'cidade',
        'tem_coordenadas',
        'quantidade_especies',
        'ultima_atualizacao',
        'ativo',
        'mostrar_imagem',
    )
    list_filter = ('estado', 'ativo')
    search_fields = ('nome', 'estado', 'cidade', 'slug')
    prepopulated_fields = {'slug': ('nome', 'estado', 'cidade')}
    readonly_fields = ('mostrar_imagem_grande',)
    inlines = [EspecieLocalInline]
    save_on_top = True

    fieldsets = (
        (
            'Identificacao',
            {
                'fields': ('slug', 'nome', 'estado', 'cidade', 'ativo'),
            },
        ),
        (
            'Geolocalizacao',
            {
                'fields': (
                    'latitude',
                    'longitude',
                    'profundidade_media_m',
                    'fonte_coordenadas',
                ),
                'description': (
                    'Define de onde os conectores de ingestao extraem dados. '
                    'Sem latitude e longitude, o local fica fora do pipeline. '
                    'Registre sempre a origem das coordenadas.'
                ),
            },
        ),
        (
            'Areas',
            {
                'fields': (
                    'area_uc_km2',
                    'fonte_area_uc',
                    'area_recifal_km2',
                    'fonte_area_recifal',
                ),
                'description': (
                    'Duas perguntas diferentes, com ate tres ordens de grandeza '
                    'entre elas: Abrolhos tem 879,43 km2 de parque e ~8 km2 de '
                    'recife mapeado. Preencha a area da UC so quando o local FOR '
                    'uma unidade de conservacao — a area da APA nao e a area do '
                    'recife que ela contem. Nunca derive uma area da outra, e '
                    'nunca grave numero sem preencher a fonte ao lado.'
                ),
            },
        ),
        (
            'Conteudo',
            {
                'fields': ('descricao', 'ultima_atualizacao'),
            },
        ),
        (
            'Imagem do local',
            {
                'fields': (
                    'imagem',
                    'mostrar_imagem_grande',
                    'credito_imagem',
                    'fonte_imagem_url',
                    'local_captura_foto',
                ),
                'description': (
                    'Sem credito, a foto nao entra na copia versionada e a tela '
                    'exibe "sem credito informado" em vez de atribuir a imagem a '
                    'alguem. O credito pode ser um site, uma instituicao ou o nome '
                    'de quem fotografou. O local de captura e opcional e nao e a '
                    'coordenada monitorada.'
                ),
            },
        ),
    )

    @admin.display(boolean=True, description='Geo')
    def tem_coordenadas(self, obj):
        return obj.tem_coordenadas

    def quantidade_especies(self, obj):
        return obj.especies.count()

    quantidade_especies.short_description = 'Especies'

    def mostrar_imagem(self, obj):
        if obj.imagem:
            return format_html(
                '<img src="{}" style="width: 56px; height: 56px; border-radius: 8px; object-fit: cover;" />',
                obj.imagem.url,
            )
        return '-'

    mostrar_imagem.short_description = 'Imagem'

    def mostrar_imagem_grande(self, obj):
        if obj and obj.imagem:
            return format_html(
                '<img src="{}" style="max-width: 360px; width: 100%; border-radius: 12px; object-fit: cover;" />',
                obj.imagem.url,
            )
        return 'Sem imagem cadastrada.'

    mostrar_imagem_grande.short_description = 'Preview da imagem'


@admin.register(Especie)
class EspecieAdmin(SyncToCodeAdminMixin, admin.ModelAdmin):
    list_display = (
        'nome_cientifico',
        'mostrar_foto',
        'nome_comum',
        'tipo',
        'conservacao_com_procedencia',
        'credito_imagem',
        'tem_fonte_imagem',
    )
    list_filter = ('tipo', 'iucn_categoria', 'locais')
    search_fields = ('nome_cientifico', 'nome_comum', 'credito_imagem')
    filter_horizontal = ('locais',)
    readonly_fields = (
        'mostrar_foto_grande', 'link_imagem', 'link_fonte_imagem', 'link_fonte_info',
        'criado_por', 'editado_por', 'editado_em',
    )
    save_on_top = True

    fieldsets = (
        (
            'Identificacao',
            {
                'fields': ('nome_cientifico', 'nome_comum', 'tipo'),
            },
        ),
        (
            'Taxonomia',
            {
                'fields': (
                    'aphia_id', 'gbif_key', 'status_taxonomico', 'nome_aceito',
                    'taxonomia_conferida_em',
                ),
                'description': (
                    'Identificadores estaveis. Preenchidos por '
                    '"manage.py resolver_taxonomia" — sinonimo e '
                    'reclassificacao quebram o nome cientifico como chave.'
                ),
            },
        ),
        (
            'Conservacao (IUCN)',
            {
                'fields': (
                    'iucn_origem', 'iucn_categoria', 'iucn_avaliado_em',
                    'iucn_versao', 'iucn_consultado_em', 'iucn_taxon_id',
                    'fonte_iucn_url',
                ),
                'description': (
                    'O ANO DA AVALIACAO nao e opcional: sem ele o site nao '
                    'exibe a categoria, e mostra "sem procedencia registrada". '
                    'Dendrogyra cylindrus foi Vulneravel de 2008 a 2022 e hoje '
                    'e Criticamente Ameacada — a categoria sozinha nao diz de '
                    'quando e a afirmacao.'
                ),
            },
        ),
        (
            'Associacoes',
            {
                'fields': ('locais',),
            },
        ),
        (
            'Imagem',
            {
                'fields': (
                    'foto',
                    'mostrar_foto_grande',
                    'credito_imagem',
                    'fonte_imagem_url',
                    'local_captura_foto',
                    'link_imagem',
                    'link_fonte_imagem',
                ),
            },
        ),
        (
            'Conteudo',
            {
                'fields': ('descricao', 'fonte_url', 'link_fonte_info'),
            },
        ),
        (
            'Autoria (so leitura)',
            {
                'fields': ('criado_por', 'editado_por', 'editado_em'),
                'description': (
                    'Preenchido quando a especie chega por contribuicao no '
                    'site (criacao/edicao direta de master, ou solicitacao '
                    'aprovada de conta comum). Em branco = nunca passou por '
                    'esse caminho, o que inclui as 9 especies de antes desta '
                    'funcionalidade.'
                ),
            },
        ),
    )

    @admin.display(description='Conservacao', ordering='iucn_categoria')
    def conservacao_com_procedencia(self, obj):
        """A categoria so aparece com o ano. Sem ele, o admin diz o que falta.

        O admin e onde alguem preenche isso, entao e onde a falta precisa
        aparecer — nao so na tela publica.
        """
        if not obj.iucn_categoria:
            return '—'
        if not obj.iucn_avaliado_em:
            return format_html(
                '<span style="color:#b45309">{} (sem ano)</span>',
                obj.get_iucn_categoria_display(),
            )
        return f'{obj.get_iucn_categoria_display()} ({obj.iucn_avaliado_em})'

    def mostrar_foto(self, obj):
        if obj.foto:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 5px; object-fit: cover;" />',
                obj.foto.url,
            )
        return '-'

    mostrar_foto.short_description = 'Foto'

    def mostrar_foto_grande(self, obj):
        if obj and obj.foto:
            return format_html(
                '<img src="{}" style="max-width: 360px; width: 100%; border-radius: 12px; object-fit: cover;" />',
                obj.foto.url,
            )
        return 'Sem foto cadastrada.'

    mostrar_foto_grande.short_description = 'Preview da foto'

    def link_imagem(self, obj):
        if obj and obj.foto:
            return format_html('<a href="{}" target="_blank">Abrir imagem atual</a>', obj.foto.url)
        return '-'

    link_imagem.short_description = 'Arquivo da imagem'

    def link_fonte_imagem(self, obj):
        if obj and obj.fonte_imagem_url:
            return format_html(
                '<a href="{}" target="_blank">Abrir fonte da imagem</a>',
                obj.fonte_imagem_url,
            )
        return 'Sem fonte externa cadastrada.'

    link_fonte_imagem.short_description = 'Fonte da imagem'

    def link_fonte_info(self, obj):
        if obj and obj.fonte_url:
            return format_html('<a href="{}" target="_blank">Abrir referencia</a>', obj.fonte_url)
        return '-'

    link_fonte_info.short_description = 'Referencia da especie'

    def tem_fonte_imagem(self, obj):
        return bool(obj.fonte_imagem_url)

    tem_fonte_imagem.boolean = True
    tem_fonte_imagem.short_description = 'Fonte imagem'


@admin.register(DatasetCatalogo)
class DatasetCatalogoAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'fonte',
        'tipo_dado',
        'localizacao',
        'estado',
        'formato',
        'periodo_rotulo',
        'ativo',
    )
    list_filter = ('fonte', 'tipo_dado', 'formato', 'estado', 'ativo')
    search_fields = ('id', 'titulo', 'resumo', 'localizacao', 'cidade', 'estado', 'fonte')
    ordering = ('ordem_exibicao', 'titulo')
    list_editable = ('ativo',)
    save_on_top = True


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    """Aprovar conta e marcar uma caixa numa lista — nada mais que isso.

    Sem tela nova, sem endpoint novo: master ja loga como superusuario, e
    aprovar uma conta e exatamente o tipo de acao que `list_editable` resolve
    sem nenhum codigo de fluxo.
    """

    list_display = ('usuario', 'aprovado', 'aprovado_por', 'aprovado_em', 'criado_em')
    list_filter = ('aprovado',)
    list_editable = ('aprovado',)
    search_fields = ('usuario__username', 'usuario__email')
    readonly_fields = ('aprovado_por', 'aprovado_em', 'criado_em')
    autocomplete_fields = ('usuario',)

    def save_model(self, request, obj, form, change):
        # 🚨 So grava quem aprovou/quando se `aprovado` de fato mudou nesta
        # edicao — senão salvar o registro por qualquer outro motivo (ou
        # desaprovar) reescreveria "aprovado por" com o nome de quem so
        # passou por aqui, inclusive na hora de reverter uma aprovacao.
        if 'aprovado' in form.changed_data:
            if obj.aprovado:
                obj.aprovado_por = request.user
                obj.aprovado_em = timezone.now()
            else:
                obj.aprovado_por = None
                obj.aprovado_em = None
        super().save_model(request, obj, form, change)


@admin.register(SolicitacaoEspecie)
class SolicitacaoEspecieAdmin(admin.ModelAdmin):
    """A fila de moderacao. `dados_propostos` e so leitura de proposito —
    revisar e decidir aprovar/rejeitar, nao editar a proposta por cima.
    """

    list_display = ('tipo', 'especie', 'solicitante', 'status', 'criado_em', 'revisado_por')
    list_filter = ('tipo', 'status')
    search_fields = ('solicitante__username', 'especie__nome_cientifico')
    readonly_fields = (
        'tipo', 'especie', 'dados_propostos', 'solicitante', 'criado_em',
        'status', 'revisado_por', 'revisado_em', 'motivo_rejeicao',
    )
    actions = ['aprovar_selecionadas', 'rejeitar_selecionadas']

    def has_add_permission(self, request):
        # So nasce por contribuicao via API — criar direto no admin não faz
        # sentido (não existiria conta solicitante de verdade por tras).
        return False

    @admin.action(description='Aprovar selecionadas')
    def aprovar_selecionadas(self, request, queryset):
        aprovadas, falhas = 0, []
        for solicitacao in queryset.filter(status='PENDENTE'):
            try:
                # 🚨 Savepoint proprio por item: sem isto, um IntegrityError
                # (duas solicitacoes de CRIAR aprovadas com o mesmo nome
                # cientifico) deixaria a transacao inteira do lote imprestavel
                # para os itens seguintes, nao so para este.
                with transaction.atomic():
                    solicitacao.aprovar(request.user)
                aprovadas += 1
            except Exception as exc:
                falhas.append(f'#{solicitacao.pk}: {exc}')

        if aprovadas:
            self.message_user(request, f'{aprovadas} solicitacao(oes) aprovada(s).', level=messages.SUCCESS)
        for falha in falhas:
            self.message_user(request, f'Falha ao aprovar {falha}', level=messages.ERROR)

    @admin.action(description='Rejeitar selecionadas')
    def rejeitar_selecionadas(self, request, queryset):
        total = 0
        for solicitacao in queryset.filter(status='PENDENTE'):
            solicitacao.rejeitar(request.user, motivo='Rejeitada em lote pelo admin.')
            total += 1
        self.message_user(request, f'{total} solicitacao(oes) rejeitada(s).', level=messages.INFO)
