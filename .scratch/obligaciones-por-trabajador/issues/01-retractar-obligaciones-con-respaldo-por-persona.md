# 01: Retractar las obligaciones de ADM04 que tienen respaldo por persona

**What to build:** Que el plan de la Bodega de Distribución deje de exigirle al centro de costo catorce obligaciones cuyo respaldo es un diploma o un examen a nombre de una persona. Se cierran con motivo explícito; nada se borra y la evidencia sigue consultable.

De las 18 obligaciones del plan de ADM04, **14 tienen respaldo por persona**: nueve capacitaciones (manejo de extintores con simulador, fortalecimiento de competencias psicosociales, orientación en prevención de riesgos laborales, prevención del consumo de alcohol y drogas, análisis del Decreto Supremo 44, liderazgo en seguridad y salud para supervisores, factores de riesgo TMERT, factores de riesgo MMC, gestión del riesgo de desastre), cuatro exámenes ocupacionales (altura física, conductor clase D, conductor de vehículo liviano, operadores de maquinaria) y la licencia de conducir. Las 245 constancias de la carpeta de respaldo pertenecen las 245 a un trabajador identificado por su RUT: ninguna es del centro de costo.

Al terminar, ADM04 muestra únicamente las cuatro obligaciones que sí son suyas —matriz IPER, reglamento interno, comité paritario y la vigilancia de sílice en No aplica—, que es el estado honesto: la bodega no tiene acreditado nada en el grano de la instalación.

**Blocked by:** None (can start immediately)

**Type:** task

**Status:** resolved

- [x] Las catorce obligaciones quedan cerradas mediante una versión de obligación de tipo cierre, con autor, fecha y motivo.
- [x] El motivo declara el error de atribución y lo distingue de un cambio normativo, para que quien lea la historia no los confunda.
- [x] La evidencia cargada bajo esas obligaciones sigue siendo consultable, descargable y verificable por hash después del cierre.
- [x] El plan de aplicación de ADM04 deja de exigirle esas obligaciones al centro de costo.
- [x] El plan de ADM04 queda mostrando solo las obligaciones cuyo titular es el centro de costo.
- [x] Se verifica si el cierre basta por sí solo o si además hace falta un cambio de aplicabilidad, y el resultado queda cubierto por una prueba.
- [x] La retractación exige confirmación explícita y no escribe nada sin ella.
- [x] Ejecutarla dos veces no produce cierres duplicados ni falla.
- [x] Cada cierre queda en la bitácora, con un canal propio que lo distingue de la operación normal.
- [x] La documentación del piloto explica que estas obligaciones vuelven cuando exista el titular correcto, y no que se hayan descartado.
