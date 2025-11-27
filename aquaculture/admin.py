from django.contrib import admin
from django.utils.html import format_html
from .models import Especie, StatusPredicao

class EspecieAdmin(admin.ModelAdmin):
    # Aqui definimos as colunas que aparecem na lista
    list_display = ('nome_cientifico', 'mostrar_foto', 'nome_comum', 'tipo', 'status_conservacao')
    list_filter = ('tipo', 'status_conservacao')
    
    def mostrar_foto(self, obj):
        #verificr se o campo foto tem algum arquivo
        if obj.foto:
            #se tiver pega a url dele para mostrar
            return format_html('<img src="{}" style="width: 50px; height: 50px; border-radius: 5px; object-fit: cover;" />', obj.foto.url)
        return "-"
    mostrar_foto.short_description = 'Foto'

admin.site.register(Especie, EspecieAdmin)
admin.site.register(StatusPredicao)