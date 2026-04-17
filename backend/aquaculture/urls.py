from django.urls import path

from . import views

urlpatterns = [
    path('status/', views.ApiStatusView.as_view(), name='api_status'),
    path('locais/', views.LocalRecifeList.as_view(), name='local_recife_list'),
    path('locais/<slug:slug>/', views.LocalRecifeDetail.as_view(), name='local_recife_detail'),
    path('especies/', views.EspecieList.as_view(), name='especie_list'),
    path('especies/<int:pk>/', views.EspecieDetail.as_view(), name='especie_detail'),
    path('monitoramento/', views.StatusPredicaoList.as_view(), name='monitoramento_list'),
]
