"""Lo mínimo de PDF que el proyecto necesita, sin dependencias nuevas.

Se usa en dos direcciones: leer la capa de texto de las constancias de la
carpeta de respaldo, y escribir un marcador legible cuando hay que guardar un
archivo que no proviene de una constancia real.

No pretende ser un lector de PDF: reconoce los flujos de contenido de página y
extrae lo que los operadores de texto dibujan, que es todo lo que hace falta
para leer la fecha de una constancia.
"""

import re
import zlib

_INICIO_FLUJO = re.compile(rb"stream\r?\n")
_TEXTO_DIBUJADO = re.compile(rb"\((?:\\.|[^\\()])*\)\s*(?:Tj|TJ)")
_LITERAL = re.compile(rb"\((?:\\.|[^\\()])*\)")
_ESCAPE = re.compile(rb"\\([()\\])")


def _flujos(bruto: bytes) -> list[bytes]:
    """Devuelve los flujos de contenido de página, ya descomprimidos.

    Descarta las imágenes: sin filtrar, los bytes de un escaneo producen
    paréntesis por azar y se leerían como si fueran texto.
    """
    salida: list[bytes] = []
    for marca in _INICIO_FLUJO.finditer(bruto):
        inicio = marca.end()
        fin = bruto.find(b"endstream", inicio)
        if fin == -1:
            continue
        crudo = bruto[inicio:fin]
        try:
            flujo = zlib.decompress(crudo)
        except zlib.error:
            flujo = crudo
        if b"BT" in flujo and (b"Tj" in flujo or b"TJ" in flujo):
            salida.append(flujo)
    return salida


def texto_de_pdf(bruto: bytes) -> str:
    """Extrae el texto dibujado, con los espacios normalizados.

    Devuelve una cadena vacía si el PDF es solo imagen, que es el caso de los
    exámenes ocupacionales escaneados.
    """
    partes: list[str] = []
    for flujo in _flujos(bruto):
        for dibujado in _TEXTO_DIBUJADO.finditer(flujo):
            for literal in _LITERAL.finditer(dibujado.group()):
                crudo = _ESCAPE.sub(rb"\1", literal.group()[1:-1])
                partes.append(crudo.decode("cp1252", errors="replace"))
    return re.sub(r"\s+", " ", "".join(partes)).strip()


def marcador_pdf(lineas: list[str]) -> bytes:
    """Arma un PDF de una página que se abre y dice qué es.

    Se genera aquí, sin dependencias nuevas, para las obligaciones cuyo
    respaldo real no está disponible al sembrar.
    """
    instrucciones = ["BT", "/F1 11 Tf", "40 780 Td", "16 TL"]
    for linea in lineas:
        escapada = linea.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        instrucciones.append(f"({escapada}) Tj T*")
    instrucciones.append("ET")
    flujo = "\n".join(instrucciones).encode("cp1252", "replace")

    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]"
        b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length "
        + str(len(flujo)).encode("ascii")
        + b" >>\nstream\n"
        + flujo
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica"
        b" /Encoding /WinAnsiEncoding >>",
    ]

    salida = bytearray(b"%PDF-1.4\n")
    posiciones: list[int] = []
    for numero, cuerpo in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += f"{numero} 0 obj\n".encode("ascii") + cuerpo + b"\nendobj\n"

    inicio_xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n".encode("ascii")
    salida += b"0000000000 65535 f \n"
    for posicion in posiciones:
        salida += f"{posicion:010d} 00000 n \n".encode("ascii")
    salida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{inicio_xref}\n%%EOF\n"
    ).encode("ascii")
    return bytes(salida)
