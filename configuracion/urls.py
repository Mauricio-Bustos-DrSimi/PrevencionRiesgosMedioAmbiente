from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import path

from acceso.views import inicio


urlpatterns = [
    path("", inicio, name="inicio"),
    path(
        "cuentas/iniciar-sesion/",
        LoginView.as_view(template_name="registration/iniciar_sesion.html"),
        name="iniciar_sesion",
    ),
    path("admin/", admin.site.urls),
]
