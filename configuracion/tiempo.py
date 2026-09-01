"""Cómo este proyecto corta el tiempo al reconstruir el pasado.

La reconstrucción histórica —de la dotación, del plan de aplicación y del
estado de cumplimiento— pregunta siempre lo mismo: qué regía *hasta esa fecha
inclusive*. Los tres tienen que cortar en el mismo instante, o el estado que
muestran para una misma fecha no coincide entre sí.
"""

from datetime import date, datetime, time

from django.utils import timezone


def fin_del_dia(fecha: date) -> datetime:
    """El último instante de ese día, en la zona horaria del proyecto."""
    return timezone.make_aware(datetime.combine(fecha, time.max))
