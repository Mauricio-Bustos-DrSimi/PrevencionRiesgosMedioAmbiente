import re

from django import template


register = template.Library()


@register.filter
def rut_oculto(valor: object) -> str:
    """Muestra solo los tres últimos dígitos y el verificador de un RUT."""
    limpio = re.sub(r"[^0-9Kk]", "", str(valor))
    if len(limpio) < 2:
        return "RUT reservado"

    cuerpo, verificador = limpio[:-1], limpio[-1].upper()
    ultimos = cuerpo[-3:] if len(cuerpo) > 3 else "•••"
    return f"••.•••.{ultimos}-{verificador}"
