from datetime import date, datetime, time

from django.db.models import QuerySet
from django.utils import timezone

from centros_costo.models import CentroCosto
from obligaciones.models import Obligacion, TitularObligacion
from trabajadores.models import Trabajador
from trabajadores.services import dotacion_del_centro

from .models import CambioAplicabilidad


def _catalogo_vigente() -> list[Obligacion]:
    return [
        obligacion
        for obligacion in Obligacion.objects.prefetch_related("versiones").all()
        if obligacion.esta_vigente
    ]


def obligaciones_sugeridas(centro: CentroCosto) -> list[Obligacion]:
    """Devuelve el catálogo vigente como sugerencia inicial del piloto."""
    return [
        obligacion
        for obligacion in _catalogo_vigente()
        if obligacion.version_actual.titular == TitularObligacion.CENTRO_COSTO
        and (
            not obligacion.version_actual.tipos_centro
            or centro.tipo in obligacion.version_actual.tipos_centro
        )
    ]


def obligaciones_sugeridas_trabajador(trabajador: Trabajador) -> list[Obligacion]:
    """El espejo de la sugerencia del centro, filtrada por el cargo.

    La sugerencia acelera; no decide. La aplicabilidad se sigue confirmando
    persona por persona, con autor, fecha y motivo.
    """
    return [
        obligacion
        for obligacion in _catalogo_vigente()
        if obligacion.version_actual.titular == TitularObligacion.TRABAJADOR
        and (
            not obligacion.version_actual.cargos_sugeridos
            or trabajador.cargo in obligacion.version_actual.cargos_sugeridos
        )
    ]


def _hasta(
    cambios: QuerySet[CambioAplicabilidad],
    hasta: date | None,
) -> QuerySet[CambioAplicabilidad]:
    if hasta is None:
        return cambios
    limite = timezone.make_aware(datetime.combine(hasta, time.max))
    return cambios.filter(ocurrido_en__lte=limite)


def cambios_del_plan(
    centro: CentroCosto,
    *,
    hasta: date | None = None,
) -> QuerySet[CambioAplicabilidad]:
    return _hasta(
        CambioAplicabilidad.objects.filter(centro_costo=centro).select_related(
            "obligacion",
            "autor",
        ),
        hasta,
    )


def cambios_del_plan_trabajador(
    trabajador: Trabajador,
    *,
    hasta: date | None = None,
) -> QuerySet[CambioAplicabilidad]:
    return _hasta(
        CambioAplicabilidad.objects.filter(trabajador=trabajador).select_related(
            "obligacion",
            "autor",
        ),
        hasta,
    )


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


def estado_actual_trabajador(
    trabajador: Trabajador,
    obligacion: Obligacion,
    *,
    hasta: date | None = None,
) -> CambioAplicabilidad | None:
    return (
        cambios_del_plan_trabajador(trabajador, hasta=hasta)
        .filter(obligacion=obligacion)
        .order_by("-ocurrido_en", "-pk")
        .first()
    )


def obligaciones_de_la_dotacion(
    centro: CentroCosto,
    *,
    en_fecha: date | None = None,
) -> list[Obligacion]:
    """Las obligaciones de titular trabajador que el centro tiene que mirar.

    Son las que aparecen en el plan de alguien de su dotación. Una obligación
    que nadie del centro tiene en su plan no le compete al centro; una que
    todos declararon No aplica sí, y el centro la ve como No aplica.
    """
    dotacion = dotacion_del_centro(centro, en_fecha=en_fecha)
    if not dotacion:
        return []
    obligaciones: dict[int, Obligacion] = {}
    cambios = _hasta(
        CambioAplicabilidad.objects.filter(
            trabajador__in=dotacion,
        ).select_related("obligacion"),
        en_fecha,
    )
    for cambio in cambios:
        obligacion = cambio.obligacion
        if not obligacion.esta_vigente:
            continue
        obligaciones.setdefault(obligacion.pk, obligacion)
    return sorted(
        obligaciones.values(),
        key=lambda obligacion: obligacion.version_actual.nombre,
    )
