from django.urls import path

from . import views


app_name = "planes_aplicacion"

urlpatterns = [
    path("<int:centro_pk>/", views.plan, name="plan"),
    path(
        "<int:centro_pk>/obligaciones/<int:obligacion_pk>/desglose/",
        views.desglose,
        name="desglose",
    ),
    path(
        "<int:centro_pk>/sugerencia/confirmar/",
        views.confirmar_sugerencia,
        name="confirmar_sugerencia",
    ),
    path("<int:centro_pk>/agregar/", views.agregar, name="agregar"),
    path("<int:centro_pk>/no-aplica/", views.no_aplica, name="no_aplica"),
]
