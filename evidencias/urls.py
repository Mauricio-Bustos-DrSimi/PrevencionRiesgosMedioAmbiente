from django.urls import path

from . import views


app_name = "evidencias"

urlpatterns = [
    path("pendientes/", views.pendientes, name="pendientes"),
    path("vencimientos/", views.vencimientos, name="vencimientos"),
    path("<int:evidencia_pk>/validar/", views.validar, name="validar"),
    path(
        "<int:centro_pk>/<int:obligacion_pk>/cargar/",
        views.cargar,
        name="cargar",
    ),
]
