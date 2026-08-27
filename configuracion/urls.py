from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path

from acceso.views import inicio


urlpatterns = [
    path("", inicio, name="inicio"),
    path(
        "cuentas/iniciar-sesion/",
        LoginView.as_view(template_name="registration/iniciar_sesion.html"),
        name="iniciar_sesion",
    ),
    path("centros-de-costo/", include("centros_costo.urls")),
    path("obligaciones/", include("obligaciones.urls")),
    path("planes-aplicacion/", include("planes_aplicacion.urls")),
    path("importaciones/", include("importaciones.urls")),
    path("evidencias/", include("evidencias.urls")),
    path("admin/", admin.site.urls),
]
