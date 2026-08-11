from django.urls import path

from . import views

urlpatterns = [
    path('status/', views.ApiStatusView.as_view(), name='api_status'),
    path('datasets/', views.DatasetCatalogoList.as_view(), name='dataset_catalogo_list'),
    path('locais/', views.LocalRecifeList.as_view(), name='local_recife_list'),
    path('locais/<slug:slug>/', views.LocalRecifeDetail.as_view(), name='local_recife_detail'),
    path(
        'locais/<slug:slug>/datasets/',
        views.LocalRecifeDatasetRelacionadosList.as_view(),
        name='local_recife_datasets_list',
    ),
    path('especies/', views.EspecieList.as_view(), name='especie_list'),
    path('especies/<int:pk>/', views.EspecieDetail.as_view(), name='especie_detail'),
    path('auth/cadastro/', views.CadastroView.as_view(), name='auth_cadastro'),
    path('auth/login/', views.LoginView.as_view(), name='auth_login'),
    path('auth/logout/', views.LogoutView.as_view(), name='auth_logout'),
    path('auth/eu/', views.EuView.as_view(), name='auth_eu'),
    # A serie ambiental. Substituiu o `monitoramento/`, removido em
    # 28/07/2026: aquele devolvia `StatusPredicao`, o modelo legado com 3
    # registros de demonstracao.
    path('medicoes/', views.MedicaoAmbientalList.as_view(), name='medicao_list'),
    # O unico endpoint que faz conta: carrega o modelo persistido e responde
    # probabilidade. Todos os outros servem linha guardada.
    path('painel-risco/', views.PainelRiscoList.as_view(), name='painel_risco_list'),
    path(
        'painel-risco/<slug:slug>/',
        views.PainelRiscoDetail.as_view(),
        name='painel_risco_detail',
    ),
    path('grafo/localizacoes/', views.GrafoLocalizacaoList.as_view(), name='grafo_localizacoes'),
    path(
        'grafo/localizacoes/<slug:slug>/',
        views.GrafoLocalizacaoDetail.as_view(),
        name='grafo_localizacao_detail',
    ),
]
