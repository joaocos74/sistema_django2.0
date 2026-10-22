from django.urls import path

from . import views, agenda_views

app_name = 'home'

urlpatterns = [
    path('', views.home_view, name='index'),
    path('lembretes/novo/', views.lembrete_criar, name='lembrete_criar'),
    path('lembretes/<int:pk>/concluir/', views.lembrete_concluir, name='lembrete_concluir'),
    path('agenda/', agenda_views.agenda_view, name='agenda'),
    path('api/usuarios/', agenda_views.api_usuarios, name='api_usuarios'),
    path('api/agenda/semana-atual/', agenda_views.api_agenda_semana, name='api_agenda_semana_atual'),
    path('api/agenda/semana-atual/minha/', agenda_views.api_agenda_semana, {'minha': True}, name='api_agenda_minha'),
    path('api/agenda/', agenda_views.api_agenda_criar, name='api_agenda_criar'),
    path('api/agenda/<int:pk>/', agenda_views.api_agenda_detalhe, name='api_agenda_detalhe'),
    path('api/agenda/dia/<str:dia_iso>/', agenda_views.api_agenda_apagar_dia, name='api_agenda_apagar_dia'),
]
