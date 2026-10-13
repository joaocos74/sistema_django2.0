from django.urls import path
from . import views

app_name = 'arquivos'
urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/baixar/', views.baixar, name='baixar'),
]
