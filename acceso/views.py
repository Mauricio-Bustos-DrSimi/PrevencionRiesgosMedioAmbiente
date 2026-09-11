from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from centros_costo.models import CentroCosto
from evidencias.services import casos_de_cumplimiento
from trabajadores.services import leer_dotacion

from .dashboard import FiltrosPortada, enlazar_kpis, resumir_casos, url_accion
from .permisos import es_operador_mvp


def inicio(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login

        return redirect_to_login(request.get_full_path())
    if not es_operador_mvp(request.user):
        raise PermissionDenied

    fecha_referencia = timezone.localdate()
    filtros = FiltrosPortada.desde_parametros(
        request.GET.get("centro", ""),
        request.GET.get("tipo_centro", ""),
    )
    centros = list(CentroCosto.objects.filter(es_franquicia=False))
    centros_filtrados = [centro for centro in centros if filtros.admite_centro(centro)]
    centros_ids = {centro.pk for centro in centros_filtrados}
    casos = [
        caso
        for caso in casos_de_cumplimiento(en_fecha=fecha_referencia)
        if caso.centro.pk in centros_ids
    ]
    resumen = enlazar_kpis(resumir_casos(casos), filtros)
    dotacion = leer_dotacion(en_fecha=fecha_referencia)
    total_trabajadores = sum(
        1
        for trabajador_id in dotacion.personas
        if trabajador_id in dotacion.validados
        and trabajador_id in dotacion.centros
        and dotacion.centros[trabajador_id].pk in centros_ids
    )
    return render(
        request,
        "acceso/inicio.html",
        {
            "titulo_pagina": "Resumen de cumplimiento",
            "fecha_referencia": fecha_referencia,
            "filtros": filtros,
            "centros": centros,
            "tipos_centro": CentroCosto.Tipo.choices,
            "kpis": resumen.kpis,
            "distribuciones": resumen.distribuciones,
            "total_casos": len(casos),
            "total_centros": len(centros_filtrados),
            "total_trabajadores": total_trabajadores,
            "url_vencidas": url_accion(filtros, estado="vencido"),
            "url_sin_evidencia": url_accion(filtros, estado="sin_evidencia"),
        },
    )
