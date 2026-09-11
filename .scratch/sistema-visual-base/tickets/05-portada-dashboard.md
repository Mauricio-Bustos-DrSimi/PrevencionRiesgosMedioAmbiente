# 05: Portada con KPI y distribución

**What to build:** Una portada accionable que muestre el estado actual de los casos y conduzca a sus listados.

**Status:** blocked

**Blocked by:** 04: Mensajes y controles compartidos

## Archivos a crear o modificar

- Crear `acceso/dashboard.py` y `templates/acceso/includes/distribucion_estados.html`.
- Modificar `acceso/views.py`, `templates/acceso/inicio.html` y configuración de contexto si procede.
- Crear o ampliar `acceso/tests/test_dashboard_http.py`.

## Criterios de aceptación

- KPI: Vencidas, Sin evidencia, Pendientes de validación y Por vencer, en ese orden.
- Cada KPI separa instalaciones y trabajadores y cuenta casos titular–obligación.
- Una única lista materializada alimenta KPI, gráficos, tabla y enlaces.
- Filtros por centro y tipo aplican al mismo alcance en todos esos elementos.
- Distribuciones con cantidades, etiquetas y tabla equivalente; sin tendencias ni porcentajes ambiguos.
- Portada solo muestra información agregada y acciones según permisos.
- Funciona sin JavaScript.

## Pruebas específicas

- `python manage.py check`.
- Fixture sintética con seis estados, ambos titulares, renovaciones y cero resultados.
- Pruebas de filtros, enlaces KPI, permisos, privacidad y número de consultas.

## Comprobación visual manual

- Revisar tarjetas, barras, tabla, acciones y aviso de piloto con datos ficticios y vacíos a ambas resoluciones.

## Riesgos de regresión

- Duplicar casos, mezclar documentos con estados, exponer personas o alterar filtros/fecha.
