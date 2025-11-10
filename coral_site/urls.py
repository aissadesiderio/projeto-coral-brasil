"""
URL configuration for coral_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView # 1. Importe o RedirectView

urlpatterns = [
    # 2. Adicione esta linha:
    # (Redireciona a rota raiz '' para '/api/especies/')
    path('', RedirectView.as_view(url='/api/especies/', permanent=False)), 

    path('admin/', admin.site.urls),
    # Você provavelmente já tem uma linha parecida com esta:
    path('api/especies/', include('aquaculture.urls')), # (ou o nome do seu app)
]