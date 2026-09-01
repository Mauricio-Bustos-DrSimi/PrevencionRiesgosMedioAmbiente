"""El RUT es la identidad del trabajador, y el nombre solo un atributo.

La carpeta de respaldo escribe el mismo RUT de varias maneras --con puntos, sin
puntos, con el dígito verificador en minúscula, con un espacio antes del
guion-- y escribe el nombre de 184 formas distintas para 129 personas. Por eso
la identidad se normaliza a una sola forma canónica y se comprueba con su
dígito verificador: reconocer a la misma persona entre dos cargas es lo que
impide que la dotación se duplique.
"""

import re


FORMA_CANONICA = "sin puntos, con guion y con el dígito verificador en mayúscula"

_ESCRITURA = re.compile(r"^0*(\d{7,8})-?([\dK])$")


class RutInvalido(ValueError):
    """El texto no es un RUT chileno bien formado."""


def digito_verificador(cuerpo: str) -> str:
    """Calcula el dígito verificador por módulo 11."""
    suma = 0
    factor = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def normalizar_rut(texto: str) -> str:
    """Devuelve el RUT en su forma canónica, o falla explicando por qué no.

    Acepta cualquiera de las escrituras que aparecen en el respaldo y devuelve
    siempre la misma cadena, de modo que dos cargas del mismo RUT identifiquen
    a una sola persona.
    """
    limpio = re.sub(r"[.\s]", "", texto or "").upper()
    escritura = _ESCRITURA.match(limpio)
    if escritura is None:
        raise RutInvalido(
            f"«{texto}» no es un RUT válido. Escríbelo {FORMA_CANONICA}."
        )
    cuerpo, verificador = escritura.group(1), escritura.group(2)
    cuerpo = cuerpo.lstrip("0") or "0"
    esperado = digito_verificador(cuerpo)
    if verificador != esperado:
        raise RutInvalido(
            f"El dígito verificador de «{texto}» no corresponde: debería ser "
            f"{esperado}."
        )
    return f"{cuerpo}-{verificador}"
