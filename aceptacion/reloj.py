"""Reloj simulado para recorridos que atraviesan varias fechas."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, tzinfo
from unittest.mock import patch

from django.utils import timezone as utilidades_de_tiempo


@contextmanager
def reloj_en(momento: datetime) -> Iterator[None]:
    """Ejecuta el bloque como si el sistema estuviera en ese instante.

    Sustituye el reloj del proyecto, de modo que las marcas de tiempo que se
    registren y los estados que se deriven correspondan al momento simulado.
    Convertir una fecha ya almacenada sigue usando el cálculo real, para no
    falsear el momento en que ocurrió un acto anterior.
    """
    localdate_real = utilidades_de_tiempo.localdate

    def localdate_simulada(
        value: datetime | None = None,
        timezone: tzinfo | None = None,
    ) -> date:
        if value is None:
            return momento.date()
        return localdate_real(value, timezone)

    with patch(
        "django.utils.timezone.now",
        return_value=momento,
    ), patch(
        "django.utils.timezone.localdate",
        localdate_simulada,
    ):
        yield
