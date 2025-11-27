from django.contrib import admin
from django.utils.html import format_html
from .models import Especie, StatusPredicao

class EspecieAdmin(admin.ModelAdmin):
    list_display = ('nome_cientifico', 'mostrar_foto', 'nome_comum', 'tipo', 'status_conservacao')
    list_filter = ('tipo', 'status_conservacao') # Filtros laterais úteis
    
    def mostrar_foto(self, obj):
        if obj.foto_url:
            return format_html('<img src="{}" style="width: 50px; height: 50px; border-radius: 5px;" />', obj.foto_url)
        return "-"
    mostrar_foto.short_description = 'Foto'

admin.site.register(Especie, EspecieAdmin)
admin.site.register(StatusPredicao)