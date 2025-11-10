from django.urls import path
from . import views # Importa o views.py que acabamos de fazer

urlpatterns = [
    # Caminho para a lista (ex: /api/especies/)
    path('', views.EspecieList.as_view(), name='especie_list'),

    # Caminho para o detalhe (ex: /api/especies/1/)
    path('<int:pk>/', views.EspecieDetail.as_view(), name='especie_detail'),
]