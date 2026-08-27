from django.urls import path

from .views import detalle_centro_costo, lista_centros_costo


app_name = "centros_costo"

urlpatterns = [
    path("", lista_centros_costo, name="lista"),
    path("<int:pk>/", detalle_centro_costo, name="detalle"),
]
