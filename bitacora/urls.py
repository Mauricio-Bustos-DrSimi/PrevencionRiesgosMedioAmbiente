from django.urls import path

from . import views


app_name = "bitacora"

urlpatterns = [
    path(
        "centros-de-costo/<int:centro_pk>/obligaciones/<int:obligacion_pk>/",
        views.recorrido,
        name="recorrido",
    ),
]
