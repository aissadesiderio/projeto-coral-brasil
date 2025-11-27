from django.urls import path
from . import views

urlpatterns = [

    # Caminho para a lista (ex: /api/especies/)
    path('especies/', views.EspecieList.as_view(), name='especie_list'),

    # O endereço final fica: /api/ + especies/1/
    path('especies/<int:pk>/', views.EspecieDetail.as_view(), name='especie_detail'),
    
    #o endereço final fica: /api/ + monitoramento/
    path('monitoramento/', views.StatusPredicaoList.as_view(), name='monitoramento_list'),
]