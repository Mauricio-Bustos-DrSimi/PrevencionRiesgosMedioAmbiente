from datetime import date, datetime, time

from django.db.models import QuerySet
from django.utils import timezone

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion

from .models import CambioAplicabilidad


def obligaciones_sugeridas(centro: CentroCosto) -> list[Obligacion]:
    """Devuelve el catálogo vigente como sugerencia inicial del piloto."""
    return [
        obligacion
        for obligacion in Obligacion.objects.prefetch_related("versiones").all()
        if obligacion.esta_vigente
        and obligacion.version_actual.titular == "centro_costo"
        and (
            not obligacion.version_actual.tipos_centro
            or centro.tipo in obligacion.version_actual.tipos_centro
        )
    ]


def cambios_del_plan(
    centro: CentroCosto,
    *,
    hasta: date | None = None,
) -> QuerySet[CambioAplicabilidad]:
    cambios = CambioAplicabilidad.objects.filter(centro_costo=centro).select_related(
        "obligacion",
        "autor",
    )
    if hasta is not None:
        limite = timezone.make_aware(datetime.combine(hasta, time.max))
        cambios = cambios.filter(ocurrido_en__lte=limite)
    return cambios


def estado_actual(
    centro: CentroCosto,
    obligacion: Obligacion,
    *,
    hasta: date | None = None,
) -> CambioAplicabilidad | None:
    return (
        cambios_del_plan(centro, hasta=hasta)
        .filter(obligacion=obligacion)
        .order_by("-ocurrido_en", "-pk")
        .first()
    )
