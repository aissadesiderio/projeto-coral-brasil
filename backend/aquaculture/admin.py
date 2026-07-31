from django.conf import settings
from django.contrib import admin, messages
from django.utils.html import format_html

from .code_sync import sync_project_code_from_db
from .models import DatasetCatalogo, Especie, LocalRecife


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
                    'area_km2',
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
            'Conteudo',
            {
                'fields': ('descricao', 'imagem', 'mostrar_imagem_grande', 'ultima_atualizacao'),
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
        'status_conservacao',
        'credito_imagem',
        'tem_fonte_imagem',
    )
    list_filter = ('tipo', 'status_conservacao', 'locais')
    search_fields = ('nome_cientifico', 'nome_comum', 'credito_imagem')
    filter_horizontal = ('locais',)
    readonly_fields = ('mostrar_foto_grande', 'link_imagem', 'link_fonte_imagem', 'link_fonte_info')
    save_on_top = True

    fieldsets = (
        (
            'Identificacao',
            {
                'fields': ('nome_cientifico', 'nome_comum', 'tipo', 'status_conservacao'),
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
    )

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
