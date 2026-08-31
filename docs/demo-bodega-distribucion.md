# Demostración: Bodega de Distribución

Siembra el centro de costo **ADM04 — Bodega de Distribución** con las
obligaciones que acredita la carpeta de respaldo del departamento, y con
evidencia de demostración elegida para que los seis estados de cumplimiento se
deriven solos.

## Qué es y qué no es

La carpeta de respaldo (`docs/1. Adm 04  - Bodega de Distribucion`) contiene
**245 constancias en PDF de 129 trabajadores**, organizadas por grupo de cargo y
por curso. Dos cosas impiden cargarla tal cual:

1. **El MVP no modela trabajadores.** `Evidencia` cuelga del centro de costo;
   las obligaciones por persona son el paso 5 de la secuencia de construcción.
   Lo que se siembra son los 14 cursos elevados al grano que el MVP sí maneja:
   obligaciones del centro de costo.
2. **Los PDF originales no están en disco.** Los 245 archivos son marcadores en
   línea de OneDrive; ninguno se puede leer. Sin bytes no hay SHA-256 ni archivo
   que guardar.

Por eso cada evidencia sembrada queda con el emisor
`Demostración — no es evidencia real`, y su archivo es un PDF de una página cuya
primera línea dice `ARCHIVO DE DEMOSTRACION - NO ES EVIDENCIA REAL`. **Nada de
esto sirve ante fiscalización.**

Las normas de origen del catálogo son **preliminares**. Antes de usar este
catálogo para algo que no sea una demostración, Prevención debe confirmarlas.

## Cómo sembrar

El comando escribe registros append-only: **lo que siembra no se puede borrar**.
Por eso exige `--confirmar` y se niega a correr dos veces sobre el mismo centro
de costo. Si te equivocas, la salida limpia es recrear la base.

Primero, sin escribir nada, para revisar qué haría:

```powershell
.\.venv\Scripts\python.exe manage.py sembrar_demo_bodega --usuario <prevencionista>
```

Y luego, para sembrar de verdad:

```powershell
.\.venv\Scripts\python.exe manage.py sembrar_demo_bodega --usuario <prevencionista> --confirmar
```

El usuario debe existir y pertenecer al grupo `Prevencionista`: la siembra valida
evidencia, y solo un Prevencionista puede hacerlo.

## Qué se ve en la demostración

Las fechas del catálogo están puestas para que, alrededor del **31 de agosto de
2026** y con `DIAS_POR_VENCER=30`, el plan de aplicación exhiba los seis estados
sin que nadie los teclee:

| Estado | Obligaciones |
| --- | --- |
| Vigente | Uso y manejo de extintores; Examen ocupacional de altura física; Liderazgo en SST |
| Por vencer | Fortalecimiento de competencias psicosociales; Examen de conductor clase D; Licencia de conducir |
| Vencido | Factores de riesgo TMERT; Orientación en prevención de riesgos laborales |
| Pendiente de validación | Gestión del riesgo de desastre; Examen de operadores de maquinaria |
| Sin evidencia | Análisis del DS 44; Factores de riesgo MMC; Prevención del consumo de alcohol y drogas |
| No aplica | Examen ocupacional de conductor de vehículo liviano |

El recorrido que conviene mostrar:

1. **Plan de aplicación del centro** — los seis estados juntos, y el motivo de
   cada aplicabilidad, que cita cuántas constancias respaldan el curso y en qué
   grupos de cargo (`101 constancias en Auxiliares de bodegas Nivel operativo
   (71), Jefaturas de bodegas (8)…`).
2. **Bandeja de vencimientos** — filtra por Por vencer y por Vencido; son las
   cinco que exigen acción.
3. **Validar** una de las pendientes y ver cómo el estado se deriva solo.
4. **Consulta histórica** a una fecha anterior, que reproduce el estado que
   correspondía entonces.
5. **Bitácora** — todos los actos de la siembra quedan con el canal
   `Siembra de demostración`, de modo que se distinguen de la operación real.

## Si se quiere repetir con los PDF reales

Hay que descargar la carpeta primero: en el Explorador, botón derecho sobre
`docs/1. Adm 04  - Bodega de Distribucion` → **Conservar siempre en este
dispositivo**, y esperar a que OneDrive termine (~15 MB). Aun así seguirían
cargándose al grano del centro de costo, no por trabajador: eso necesita el
paso 5.

## De dónde sale el catálogo

`importaciones/datos/catalogo_bodega_distribucion.json` se derivó recorriendo la
estructura de carpetas. Guarda **solo recuentos** —cursos, constancias y grupos
de cargo—, nunca nombres ni RUT, para que pueda versionarse sin incorporar datos
personales al repositorio.

La periodicidad, la norma de origen y la situación que cada obligación exhibe
viven en `importaciones/catalogo_demo.py`, porque son decisiones del dominio y
no datos de la carpeta.

## Calidad de los datos de origen

Al interpretar la carpeta aparecieron inconsistencias que conviene corregir en
el origen antes de construir el paso 5:

- **47 RUT con más de una grafía del nombre**, casi siempre por truncamiento
  (`Abarca Francisco` / `Abarca Medina Francisco Miguel`). El RUT es la llave
  confiable; el nombre no.
- **Separadores irregulares** en los nombres de carpeta: conviven
  `RUT - Nombre`, `RUT -Nombre` y `RUT Nombre`.
- **Un RUT mal escrito**: `15601801 -5`, con un espacio antes del dígito
  verificador, para un trabajador que en otras carpetas aparece correcto.
- **Rutas demasiado largas para Windows**: varias superan el límite de 260
  caracteres, de modo que el Explorador y `git` no pueden abrirlas.
