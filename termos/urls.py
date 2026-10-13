from django.urls import path
from . import views

app_name = 'termos'
urlpatterns = [
    path('<int:pk>/auto-termo/', views.documento, name='auto_termo'),
    path('<int:pk>/notificacao/', views.documento, {'tipo': 'notificacao'}, name='notificacao'),
    path('<int:pk>/notificacoes/', views.historico, name='historico'),
    path('notificacoes/<int:pk>/', views.emitida, name='emitida'),
]
