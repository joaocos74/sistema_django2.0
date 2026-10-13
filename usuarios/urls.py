from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('entrar/', views.EntrarView.as_view(), name='login'),
    path('sair/', LogoutView.as_view(), name='logout'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('alterar-senha/', views.AlterarSenhaView.as_view(), name='alterar_senha'),
    path('', views.listar_view, name='listar'),
    path('novo/', views.cadastrar_view, name='cadastrar'),
]
