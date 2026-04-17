from django.contrib import admin, messages
from django.utils.html import format_html

from .code_sync import sync_project_code_from_db
from .models import Especie, LocalRecife, StatusPredicao


class SyncToCodeAdminMixin:
    sync_success_message = 'Banco salvo e arquivos de codigo sincronizados.'
    sync_error_message = 'O banco foi salvo, mas a sincronizacao de arquivos falhou.'

    def _sync_code(self, request):
        try:
            result = sync_project_code_from_db()
            changed = result['backend_changed'] or result['frontend_changed']
            if changed:
                self.message_user(request, self.sync_success_message, level=messages.SUCCESS)
            else:
                self.message_user(
                    request,
                    'Banco salvo. Os arquivos de codigo ja estavam atualizados.',
                    level=messages.INFO,
                )
        except Exception as exc:
            self.message_user(
                request,
                f'{self.sync_error_message} Detalhe: {exc}',
                level=messages.WARNING,
            )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        self._sync_code(request)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        self._sync_code(request)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        self._sync_code(request)


class EspecieLocalInline(admin.TabularInline):
    model = Especie.locais.through
    extra = 1
    verbose_name = 'Especie vinculada'
    verbose_name_plural = 'Especies vinculadas'
    autocomplete_fields = ('especie',)


class StatusPredicaoInline(admin.TabularInline):
    model = StatusPredicao
    extra = 0
    fields = (
        'data',
        'nivel_alerta',
        'risco_integrado',
        'sst_atual',
        'dhw_calculado',
    )
    show_change_link = True
    ordering = ('-data',)


@admin.register(LocalRecife)
class LocalRecifeAdmin(SyncToCodeAdminMixin, admin.ModelAdmin):
    list_display = (
        'nome',
        'estado',
        'cidade',
        'quantidade_especies',
        'quantidade_monitoramentos',
        'ultima_atualizacao',
        'ativo',
        'mostrar_imagem',
    )
    list_filter = ('estado', 'ativo')
    search_fields = ('nome', 'estado', 'cidade', 'slug')
    prepopulated_fields = {'slug': ('nome', 'estado', 'cidade')}
    readonly_fields = ('mostrar_imagem_grande',)
    inlines = [EspecieLocalInline, StatusPredicaoInline]
    save_on_top = True

    fieldsets = (
        (
            'Identificacao',
            {
                'fields': ('slug', 'nome', 'estado', 'cidade', 'ativo'),
            },
        ),
        (
            'Conteudo',
            {
                'fields': ('descricao', 'imagem', 'mostrar_imagem_grande', 'ultima_atualizacao'),
            },
        ),
    )

    def quantidade_especies(self, obj):
        return obj.especies.count()

    quantidade_especies.short_description = 'Especies'

    def quantidade_monitoramentos(self, obj):
        return obj.monitoramentos.count()

    quantidade_monitoramentos.short_description = 'Monitoramentos'

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


@admin.register(StatusPredicao)
class StatusPredicaoAdmin(SyncToCodeAdminMixin, admin.ModelAdmin):
    list_display = (
        'data',
        'local_recife',
        'nivel_alerta',
        'risco_integrado',
        'sst_atual',
        'dhw_calculado',
    )
    list_filter = ('nivel_alerta', 'local_recife')
    search_fields = ('local_recife__nome',)
    date_hierarchy = 'data'
    autocomplete_fields = ('local_recife',)
    save_on_top = True
