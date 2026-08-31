"""Traduce la carpeta de respaldo del departamento al resumen que se versiona.

La carpeta tiene un PDF por trabajador, con nombre y RUT en la ruta: no puede
entrar al repositorio. Este comando la lee, extrae de cada constancia la fecha
en que se realizó el curso y la fecha en que expira, y deja un resumen con
recuentos y fechas —sin una sola identificación— que sí se puede versionar.

Se ejecuta a mano cuando la carpeta cambia. El resultado es el archivo que
`sembrar_demo_bodega` consume.
"""

import json
import re
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from importaciones.lectura_constancias import (
    RUTA_RESUMEN,
    CarpetaIlegible,
    a_diccionario,
    leer_carpeta,
    resumir,
    ruta_sin_limite,
)


# Un RUT chileno en cualquiera de sus escrituras. Se usa para comprobar que el
# resumen no arrastró ninguno antes de escribirlo.
_RUT_EN_TEXTO = re.compile(r"\b\d{7,8}\s*-\s*[\dkK]\b")


class Command(BaseCommand):
    help = (
        "Lee la carpeta de respaldo de un centro de costo y escribe el resumen "
        "anónimo por curso que consume la siembra de demostración."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--carpeta",
            required=True,
            help="Ruta de la carpeta de respaldo del centro de costo.",
        )
        parser.add_argument("--codigo", default="ADM04", help="Código contable.")
        parser.add_argument(
            "--nombre",
            default="Bodega de Distribución",
            help="Nombre del centro de costo.",
        )
        parser.add_argument("--tipo", default="bodega", help="Tipo de centro de costo.")
        parser.add_argument(
            "--salida",
            default=str(RUTA_RESUMEN),
            help="Archivo JSON a escribir.",
        )
        parser.add_argument(
            "--escribir",
            action="store_true",
            help="Escribe el archivo; sin esta opción solo se muestra el resumen.",
        )

    def handle(self, *args: Any, **opciones: Any) -> None:
        del args
        carpeta = Path(opciones["carpeta"])
        try:
            constancias = leer_carpeta(carpeta)
        except CarpetaIlegible as exc:
            raise CommandError(str(exc)) from exc

        if not constancias:
            raise CommandError(
                f"No se reconoció ninguna constancia bajo {carpeta}. Revisa que "
                "la estructura sea grupo/curso[/subtipo]/persona/archivo.pdf."
            )

        respaldo = resumir(
            constancias,
            codigo_contable=opciones["codigo"],
            nombre=opciones["nombre"],
            tipo=opciones["tipo"],
        )
        texto = json.dumps(
            a_diccionario(respaldo),
            ensure_ascii=False,
            indent=2,
        )

        rut_filtrado = _RUT_EN_TEXTO.search(texto)
        if rut_filtrado is not None:
            raise CommandError(
                "El resumen contiene lo que parece un RUT y no se escribió. "
                "Esto es un defecto del resumen, no de la carpeta."
            )

        self._informar(respaldo, carpeta, constancias)

        if not opciones["escribir"]:
            self.stdout.write(
                self.style.WARNING(
                    "\nNo se escribió nada. Repite con --escribir para guardar "
                    f"en {opciones['salida']}."
                )
            )
            return

        destino = Path(opciones["salida"])
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"\nEscrito {destino}."))

    def _informar(
        self,
        respaldo: Any,
        carpeta: Path,
        constancias: list[Any],
    ) -> None:
        self.stdout.write(f"Carpeta: {carpeta}")
        self.stdout.write(
            f"{respaldo.constancias_totales} constancias de "
            f"{respaldo.trabajadores_distintos} trabajadores en "
            f"{len(respaldo.cursos)} obligaciones."
        )
        omitidas = len(
            [
                archivo
                for archivo in ruta_sin_limite(carpeta).rglob("*")
                if archivo.is_file()
            ]
        ) - len(constancias)
        if omitidas:
            self.stdout.write(
                self.style.WARNING(
                    f"{omitidas} archivos no se reconocieron y quedaron fuera."
                )
            )
        self.stdout.write("")
        for curso in respaldo.cursos:
            if curso.fechadas:
                emision, vencimiento = curso.fechadas[0]
                fechas = (
                    f"la más antigua se realizó {emision.isoformat()} "
                    f"y expira {vencimiento.isoformat()}"
                )
            else:
                fechas = "ninguna trae fecha legible"
            self.stdout.write(
                f"  {curso.nombre}: {curso.constancias} constancias, "
                f"{len(curso.fechadas)} fechadas; {fechas}."
            )
