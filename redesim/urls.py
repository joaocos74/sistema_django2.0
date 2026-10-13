from django.urls import path

from . import views


app_name = "redesim"


urlpatterns = [
    path(
        "",
        views.redesim_index,
        name="index",
    ),

    path(
        "api/buscar_cnpj/",
        views.buscar_cnpj,
        name="buscar_cnpj",
    ),

    path(
        "api/listar/",
        views.listar_redesim,
        name="listar",
    ),
]