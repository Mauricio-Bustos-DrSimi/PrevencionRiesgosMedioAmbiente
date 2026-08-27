from django.urls import path

from . import views


app_name = "importaciones"

urlpatterns = [path("", views.importar, name="importar")]
