# 01: Fundaciones visuales y recursos estáticos

**What to build:** Un sistema visual base que pueda consumir el layout de la aplicación, con tokens, tipografía, espaciado, estados, foco y superficies coherentes.

**Status:** completed

**Blocked by:** None (can start immediately)

La implementación técnica y la validación visual están completas. El layout de
Django creado en el ticket 2 permitió comprobar los estilos en una página real
a 1366 × 768 y 1920 × 1080, además del foco visible a 1366 × 768. Las capturas
locales se conservan bajo `.desarrollo-local/` y están excluidas de Git.

## Archivos a crear o modificar

- Crear `static/prevencion/css/tokens.css`, `base.css`, `layout.css`, `componentes.css` y `dashboard.css`.
- Registrar estáticos en `configuracion/settings.py` si es necesario.
- No copiar ni recrear el logotipo todavía. Si el original institucional no está localizado, dejar el espacio textual accesible documentado para el ticket 3.

## Criterios de aceptación

- Tokens de color, estado, espaciado, radios, sombras, tipografía y foco coinciden con `spec.md`.
- La paleta usa azul petróleo, blanco y gris claro; los seis estados conservan texto y señal visual.
- No se incorporan frameworks, CDN, fuentes externas ni JavaScript.
- No se modifica el admin de Django ni la lógica de negocio.
- `findstatic` resuelve cada CSS creado.

## Pruebas específicas

- `python manage.py check`.
- Comprobación estática de tokens, rutas y ausencia de recursos externos.
- Prueba de contraste de colores y foco.
- No ejecutar la suite completa de 122 pruebas en este ticket.

## Comprobación visual manual

- Aplicar los estilos a una página mínima temporal.
- Revisar tipografía, superficies, bordes, sombras, estados y foco a 1366 × 768 y 1920 × 1080.

## Riesgos de regresión

- Configuración incorrecta de estáticos.
- Contraste insuficiente.
- Estilos globales que afecten el admin o pantallas no migradas.
