# 06: Pantalla de operación

**What to build:** La operación del piloto dentro del layout común, con tabla compacta, filtros existentes y privacidad del RUT.

**Status:** blocked

**Blocked by:** 05: Portada con KPI y distribución

## Archivos a crear o modificar

- Crear `evidencias/filtros.py` y los templatetags de presentación si son necesarios.
- Modificar `evidencias/views.py` y `templates/evidencias/operacion.html`.
- Ampliar `evidencias/tests/test_operacion_piloto_http.py`.

## Criterios de aceptación

- Conserva `estado`, `tipo_centro`, `obligacion`, `centro` y `trabajador`; el filtro de titular solo admite valores definidos.
- Tabla con centro, obligación, titular, trabajador cuando corresponda, estado, vigencia y acción.
- RUT en filas y selects como `••.•••.678-5`; nunca completo en HTML, atributos o scripts.
- Conserva enlaces a plan, evidencia o carga, el aviso de composición y estados textuales.
- No cambia la semántica de `casos_de_cumplimiento` y funciona sin JavaScript.

## Pruebas específicas

- `python manage.py check`.
- Pruebas HTTP de filtros, privacidad, enlaces, estados, cero resultados y RUT con DV K.
- Regresión específica de la prueba de escala de bandejas.

## Comprobación visual manual

- Revisar tabla compacta, nombres largos, filtros activos y desplazamiento interno a ambas resoluciones.

## Riesgos de regresión

- Alterar titular, historial, parámetros, enlaces o exponer el RUT completo.
