# 06: Actualización de periodicidades y fuentes de ADM04

**Status:** blocked-by-business

## Objetivo

Sustituir las normas y periodicidades preliminares de las 18 obligaciones por
las fuentes oficiales y reglas temporales aprobadas por Prevención.

## Alcance

- Nombre oficial, fuente versionada, periodicidad o evento y aplicabilidad por obligación.
- Jerarquía de fuentes y referencia al acta de aprobación.
- Conservación visible del carácter preliminar hasta completar la validación.
- Nueva versión de obligación; nunca edición de la versión histórica.

## Dependencias

- 12: Gobierno del catálogo y actas.
- 15: Versiones con fecha efectiva.
- Entrega formal de las fuentes y decisiones pendientes enumeradas en la especificación.

## Archivos afectados

- `importaciones/catalogo_demo.py`
- `importaciones/management/commands/sembrar_demo_bodega.py`
- `importaciones/datos/catalogo_bodega_distribucion.json`
- `obligaciones/models.py` y formularios, si la regla confirmada no cabe en el modelo actual
- Pruebas de catálogo, importación y siembra
- Documentación del piloto

## Migraciones necesarias

Por determinar. Si todas las reglas caben en la estructura final de versiones,
bastará cargar datos. Nuevos tipos de periodicidad o eventos exigirán migración.

## Riesgos de seguridad

- Presentar una regla preliminar como operativa.
- Alterar versiones históricas o recalcular el pasado.
- Cargar una fuente sin versión, acta o responsable titular.

## Criterios de aceptación

- [ ] Las 18 filas tienen nombre oficial, fuente identificada y versionada.
- [ ] Cada fila tiene periodicidad o eventos de renovación explícitos.
- [ ] Aplicabilidad, área, responsables, fecha efectiva y acta están completos.
- [ ] Ningún valor se obtiene de las constantes preliminares actuales.
- [ ] Las versiones anteriores permanecen consultables.
- [ ] ADM04 continúa etiquetado y aislado como demostración.

## Motivo del bloqueo

Prevención aún debe entregar fuentes, periodicidades, nombres y aplicabilidad
para varias obligaciones. Sin esos datos el sistema no puede calcular vigencias
con validez de negocio.
