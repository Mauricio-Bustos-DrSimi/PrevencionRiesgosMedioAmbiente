from django.urls import path

from . import views


app_name = "trabajadores"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nuevo/", views.crear, name="crear"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/validar/", views.validar, name="validar"),
    path("<int:pk>/trasladar/", views.trasladar, name="trasladar"),
    path("<int:pk>/dar-de-baja/", views.dar_de_baja, name="dar_de_baja"),
    path(
        "<int:pk>/sugerencia/confirmar/",
        views.confirmar_sugerencia,
        name="confirmar_sugerencia",
    ),
    path("<int:pk>/agregar/", views.agregar, name="agregar"),
    path("<int:pk>/no-aplica/", views.no_aplica, name="no_aplica"),
]
