# Piloto de la Bodega de Distribución (ADM04)

Cómo cargar el centro de costo ADM04 con lo que el departamento ya tiene
guardado, para mostrar el MVP funcionando sobre datos verdaderos.

## Qué es y qué no es

**Es** el respaldo real del departamento leído y traducido al modelo. Las
obligaciones son los cursos que la carpeta acredita, y las fechas son las que
las propias constancias declaran: cuándo se realizó el curso y cuándo expira.
Nada de eso está inventado.

**No es** un plan de aplicación aprobado. Dos cosas las decidió el sistema y no
el departamento, y hay que confirmarlas antes de que esto rija:

- **La periodicidad de cada obligación.** Las constancias otorgan tres años.
  Si el ciclo real es anual, buena parte de lo que la carpeta acredita está
  vencida; si es trienal, está vigente. El sistema solo deriva la consecuencia
  de la regla que se le dé, y la regla la fija la matriz legal.
- **La norma de origen.** Está puesta de forma plausible, no verificada contra
  las matrices del departamento.

Ambas cosas quedan escritas en el motivo de cada obligación sembrada, para que
nadie las lea como si estuvieran confirmadas.

## Los dos límites que no se pudieron levantar

**El grano es el centro de costo, no la persona.** La carpeta tiene 245
constancias de 129 trabajadores, pero el MVP todavía no modela trabajadores
—es el paso 5 de la secuencia de construcción—. De cada obligación se carga
**la constancia que caduca primero**, porque el centro deja de estar cubierto
cuando vence la primera. Las otras 244 quedan en la carpeta.

**Los exámenes ocupacionales y las licencias no traen fecha.** Son escaneos sin
capa de texto: 87 de los 245 archivos. Se cargan igual, para que estén a la
vista, y quedan **pendientes de validación**: la fecha la tiene que leer y
confirmar Prevención. Es exactamente lo que ese estado significa.

## Cómo se ejecuta

Con la carpeta de respaldo presente y sincronizada (si los archivos aparecen
como «solo en línea» en OneDrive, hay que marcarlos *Conservar siempre en este
dispositivo* antes de empezar):

```powershell
# 1. Traducir la carpeta al resumen versionable. Solo hace falta si la
#    carpeta cambió: el resumen ya está en el repositorio.
.\.venv\Scripts\python.exe manage.py resumir_respaldo_bodega `
    --carpeta "docs\1. Adm 04  - Bodega de Distribucion" --escribir

# 2. Ver qué haría la siembra, sin escribir nada.
.\.venv\Scripts\python.exe manage.py sembrar_demo_bodega `
    --usuario <prevencionista> `
    --carpeta "docs\1. Adm 04  - Bodega de Distribucion"

# 3. Sembrar.
.\.venv\Scripts\python.exe manage.py sembrar_demo_bodega `
    --usuario <prevencionista> `
    --carpeta "docs\1. Adm 04  - Bodega de Distribucion" `
    --confirmar
```

`--carpeta` es opcional. Sin ella las fechas siguen siendo las reales —salen
del resumen versionado— pero se guarda un marcador en vez de la constancia
original. Con ella se guarda el PDF verdadero, con su hash SHA-256.

El archivo se guarda con un nombre que no identifica a nadie: los escaneos de
la clínica se llaman `Informe_<RUT>_<marca de tiempo>`, y la evidencia se está
cargando al centro de costo, no a la persona.

> **La siembra no se puede deshacer.** El modelo es append-only: lo que se
> escribe no se borra. Por eso el comando exige `--confirmar` y se niega a
> sembrar dos veces sobre el mismo centro de costo. Si no quieres esto en la
> base real, siémbralo en una base aparte.

## Lo que queda en pantalla

Al 31 de agosto de 2026, con `DIAS_POR_VENCER=30`:

| Estado | Obligaciones |
| --- | --- |
| Vigente | Análisis del Decreto Supremo 44; Factores de riesgo TMERT; Gestión del riesgo de desastre; Liderazgo en seguridad y salud para supervisores; Prevención del consumo de alcohol y drogas |
| Por vencer | Factores de riesgo MMC |
| Vencido | Fortalecimiento de competencias psicosociales; Manejo de extintores con simulador; Orientación en prevención de riesgos laborales |
| Pendiente de validación | Los cuatro exámenes ocupacionales y la licencia de conducir |
| Sin evidencia | Matriz IPER vigente; Reglamento Interno de Higiene y Seguridad entregado; Comité Paritario de Higiene y Seguridad constituido |
| No aplica | Vigilancia de exposición ocupacional a sílice |

Los seis estados salen solos, sin que nadie los teclee. Ninguno se declaró: se
derivan de las fechas, la periodicidad y la aplicabilidad.

**Los tres «Sin evidencia» son el hallazgo más útil.** Son obligaciones que a
una bodega de 129 personas le corresponden y de las que la carpeta no tiene
nada. No es una falla de la siembra: es lo que el departamento verá al abrir el
plan.

**«Por vencer» se mueve.** Hoy lo ocupa MMC, cuyo ciclo anual termina justo
hoy; desde mañana pasa a Vencido y lo reemplaza Prevención del consumo de
alcohol y drogas, que queda Por vencer hasta el 1 de octubre. Entre el 2 de
octubre y el 16 de noviembre no hay ninguna en ese estado, hasta que entra
TMERT. Si la demostración cae en esa ventana, conviene mostrar Por vencer
consultando una fecha pasada en el plan.

## Recorrido sugerido

1. **Plan de aplicación de ADM04.** Las 18 obligaciones con su estado. Nadie
   escribió ninguno de esos estados.
2. **Abrir una evidencia vencida** (extintores). La constancia real, del 8 de
   abril de 2024, con su hash. El certificado dice que vale hasta 2027; el
   sistema la da por vencida porque el ciclo configurado es anual. Ahí está la
   conversación: **cuál es el ciclo real**.
3. **Validar un examen ocupacional.** Está pendiente porque el escaneo no
   declara fecha. Prevención la lee del documento y la confirma.
4. **Bandeja de vencimientos.** Lo mismo, ordenado por urgencia y sin filtrar
   por centro.
5. **Consultar el plan a una fecha pasada.** El estado se reconstruye a esa
   fecha, sin tocar la historia.
6. **Bitácora.** Todos los actos de la siembra llevan el canal «Siembra del
   piloto», así que se distinguen de los que entren por la aplicación.

## Cómo se leyó la carpeta

`resumir_respaldo_bodega` recorre
`<grupo de cargo>/<capacitación>[/<subtipo>]/<RUT - Nombre>/<archivo.pdf>` y de
cada PDF extrae la capa de texto. Las constancias de la plataforma traen
`REALIZADO: <fecha>` y `FECHA EXPIRACIÓN: <fecha>`; de ahí salen las fechas.

El resumen que deja en `importaciones/datos/` guarda **solo recuentos y pares
de fechas**: ni un nombre ni un RUT, para que pueda versionarse. La carpeta
original está excluida del repositorio en `.gitignore`.

### Lo que la lectura corrigió

- **Las dos carpetas de extintores son un solo curso.** «Uso y manejo de
  extintores» (81) y «Manejo de extintores con simulador» (20) tienen las 101
  constancias con el mismo título impreso. Manda el certificado, no la carpeta.
  Vale la pena que Prevención lo confirme.
- **El curso de psicosociales está escrito de seis maneras** en distintas
  carpetas; es uno solo, con 37 constancias.
- **La numeración de las carpetas es local a cada grupo de cargo**, así que el
  mismo curso lleva números distintos según el grupo.

### Problemas de datos en la carpeta

Hay que corregirlos en el origen antes del paso 5, cuando las obligaciones
pasen a ser por trabajador:

- **49 de los 129 RUT aparecen con más de una grafía del nombre** —hay 184
  carpetas de persona para 129 personas—, casi siempre por truncamiento. El RUT
  es la llave confiable; el nombre no.
- **Separadores irregulares** en dos carpetas: una escribe `<RUT> Apellido...`
  sin el guion que separa, otra `<RUT> -Apellido...` sin el espacio.
- **Un RUT con un espacio antes del dígito verificador**, que rompe el patrón
  `12345678-9`.
- **Cuatro archivos nombrados con el nombre de la persona** en vez del patrón
  habitual, dentro de las carpetas de licencia de conducir.
- **Las rutas superan los 260 caracteres** de Windows. Sin el prefijo de ruta
  extendida, `is_file()` devuelve `False` y los archivos desaparecen en
  silencio: el lector lo maneja, pero cualquier otra herramienta que se use
  sobre esta carpeta va a tropezar.
