from django.urls import path

from obligaciones import views


app_name = "obligaciones"

urlpatterns = [
    path("", views.catalogo, name="catalogo"),
    path("nueva/", views.crear, name="crear"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/corregir/", views.corregir, name="corregir"),
    path("<int:pk>/cerrar/", views.cerrar, name="cerrar"),
]
