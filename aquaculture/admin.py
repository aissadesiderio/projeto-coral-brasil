from django.contrib import admin
from .models import Especie, Parametro, TecnicaManejo  # Importa o modelo que criamos

# "Registra" o modelo Especie no painel de admin
admin.site.register(Especie)
admin.site.register(Parametro)
admin.site.register(TecnicaManejo)
