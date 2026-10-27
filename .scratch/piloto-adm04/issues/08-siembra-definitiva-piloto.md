# 08: Siembra definitiva del piloto

**Status:** blocked-by-business

## Objetivo

Crear de forma reproducible ADM04 con exactamente 18 obligaciones aprobadas para
demostración y datos ficticios, sin evidencias reales ni promoción a producción.

## Alcance

- Previsualización obligatoria antes de escribir.
- Catálogo definitivo de 18 filas con titulares correctos.
- Datos ficticios que ejerciten los estados y recorridos aprobados.
- Idempotencia o rechazo seguro de una segunda ejecución.
- Etiqueta y trazabilidad de demostración.

## Dependencias

- 06: Periodicidades y fuentes de ADM04.
- 07: Estado global de extintores.
- 12: Gobierno del catálogo y actas.
- 13: Áreas y responsables históricos.
- 14: No aplica revisable.
- 15: Versiones con fecha efectiva.
- 16: Aislamiento de demostración.
- Confirmación de los datos pendientes de las 18 obligaciones.

## Archivos afectados

- `importaciones/catalogo_demo.py`
- `importaciones/management/commands/sembrar_demo_bodega.py`
- `scripts/sembrar-demo-local.py`
- `importaciones/datos/catalogo_bodega_distribucion.json`
- Pruebas de siembra y recorrido de aceptación
- `docs/demo-bodega-distribucion.md`

## Migraciones necesarias

No debería crear migraciones propias; utiliza los esquemas aportados por sus
dependencias. Cualquier migración adicional debe justificarse antes de sembrar.

## Riesgos de seguridad

- Leer o copiar documentos reales del respaldo histórico.
- Ejecutar contra una base o directorio de medios no aislados.
- Duplicar registros en un modelo append-only.
- Presentar datos preliminares como operativos.

## Criterios de aceptación

- [ ] La previsualización no escribe en base ni medios.
- [ ] La ejecución se niega fuera de un entorno de demostración aislado.
- [ ] Se crean exactamente 18 obligaciones y solo datos ficticios.
- [ ] No se accede a la carpeta histórica ni se copian evidencias reales.
- [ ] Titulares, componentes, responsables y No aplica coinciden con la especificación.
- [ ] Una segunda ejecución no duplica información.
- [ ] Todo registro queda marcado Validada para demostración y fuera de indicadores operativos.

## Motivo del bloqueo

El catálogo no tiene fuentes, periodicidades, responsables ni reglas completas;
extintores tampoco tiene precedencia global. Sembrar antes consolidaría supuestos
que Prevención prohibió tratar como definitivos.
