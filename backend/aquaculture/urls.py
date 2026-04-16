from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.ApiStatusView.as_view(), name='api_status'),

    # Caminho para a lista (ex: /api/especies/)
    path('especies/', views.EspecieList.as_view(), name='especie_list'),

    # O endereço final fica: /api/ + especies/1/
    path('especies/<int:pk>/', views.EspecieDetail.as_view(), name='especie_detail'),
    
    #o endereço final fica: /api/ + monitoramento/
    path('monitoramento/', views.StatusPredicaoList.as_view(), name='monitoramento_list'),
]
