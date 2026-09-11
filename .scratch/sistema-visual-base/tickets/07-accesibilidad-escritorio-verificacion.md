# 07: Escritorio, accesibilidad y verificación final

**What to build:** Cerrar la presentación de portada y operación en escritorio y demostrar los criterios de accesibilidad acordados.

**Status:** implemented-awaiting-human-validation

**Blocked by:** Aprobación visual del usuario y validación de claridad por una persona de Prevención

## Archivos a crear o modificar

- Ajustar CSS base, layout y componentes.
- Ampliar pruebas HTTP y accesibilidad de portada y operación.
- Actualizar documentación de resultados si corresponde.

## Criterios de aceptación

- Cumple 1366 × 768 y 1920 × 1080 al 100%, sin versión móvil.
- Sidebar visible; no hay scroll horizontal global; tablas anchas se desplazan dentro del contenedor.
- Navegación por teclado, foco visible, landmarks, labels y estados comprensibles sin color.
- Reflujo usable al 200% de zoom.
- Portada y operación funcionan sin JavaScript.
- Admin de Django, permisos, CSRF, POST, multipart, GET e historial permanecen intactos.

## Pruebas específicas

- `python manage.py check`.
- Pruebas específicas de portada y operación.
- Comprobaciones estáticas de accesibilidad y `findstatic`.
- Ejecutar mypy y las 122 pruebas completas en PostgreSQL aislado únicamente en este ticket.

## Comprobación visual manual

- Revisar ambas resoluciones, zoom 200%, teclado, JavaScript deshabilitado, filtros, estados, mensajes y datos ficticios.
- Aprobación visual del usuario y validación de claridad por una persona de Prevención.

## Riesgos de regresión

- Ajustes globales que afecten pantallas aún no migradas, cambios de permisos o pérdida de parámetros.
