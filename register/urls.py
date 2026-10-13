from django.urls import path
from . import views
from .exportacao_excel import exportar_consolidado
from termos.views import documento

app_name = 'register'

urlpatterns = [
    path('estatisticas/consolidado.xlsx', exportar_consolidado, name='exportar_consolidado'),
    path('analisar/<int:pk>/notificacao/', documento, {'tipo': 'notificacao'}, name='notificacao'),
    path('analisar/<int:pk>/auto-termo/', documento, name='auto_termo'),
    path('', views.cadastrar_estabelecimento_view, name='register_view'),
    path('novo/', views.cadastrar_estabelecimento_view, name='cadastrar'),
    path('pesquisar/', views.pesquisar_estabelecimentos_view, name='pesquisar'),
    path('analisar/<int:pk>/', views.analisar_estabelecimento_view, name='analisar'),
    path('cronograma/', views.cronograma_view, name='cronograma'),
    path('cronograma/atualizar-mes/', views.atualizar_mes_previsto_ajax, name='atualizar_mes_previsto'),
    path('estatisticas/', views.estatisticas_view, name='estatisticas'),
    path('documentos/<int:pk>/baixar/', views.baixar_documento_view, name='baixar_documento'),
]
