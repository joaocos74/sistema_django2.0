from django.urls import path
from . import views

app_name = 'resolucoes'
urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/visualizar/', views.visualizar, name='visualizar'),
]
