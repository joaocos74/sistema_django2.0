from django.urls import path
from . import views

app_name = 'denuncias'

urlpatterns = [
    path('', views.denuncias_index, name='index'),
    path('api/buscar_cnpj/', views.buscar_cnpj, name='buscar_cnpj'),
    path('api/listar/', views.listar_denuncias, name='listar'),
    path('api/<int:id>/', views.get_denuncia, name='detalhes'),
]