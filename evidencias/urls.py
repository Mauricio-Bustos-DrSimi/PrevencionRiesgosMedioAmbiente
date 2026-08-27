from django.urls import path

from . import views


app_name = "evidencias"

urlpatterns = [
    path(
        "<int:centro_pk>/<int:obligacion_pk>/cargar/",
        views.cargar,
        name="cargar",
    ),
]
