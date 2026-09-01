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

## El grano es el titular que declara el catálogo

**Las catorce obligaciones que la carpeta acredita son del trabajador.** Su
respaldo son diplomas y exámenes a nombre de una persona identificada por su
RUT: de las 245 constancias, ninguna es del centro de costo. Se cargan **las
245**, cada una atribuida a quien la obtuvo, y se da de alta a las **129
personas** con el cargo que declara el nivel de carpeta que las contiene.

Las únicas obligaciones que sí son de la instalación son las que no tienen
ningún documento —matriz IPER, reglamento interno, comité paritario— más la
vigilancia de sílice, que está en No aplica. Esas siguen colgando del centro
de costo.

> **Antes esto estaba al revés.** La primera siembra atribuyó las dieciocho
> obligaciones al centro de costo y cargó una constancia por obligación, la que
> caduca primero: el sistema afirmaba que una bodega tiene licencia de
> conducir, y no se podía saber quién estaba cubierto ni cuántos faltaban. Si
> tienes esa base sembrada, corrígela con `retractar_obligaciones_por_trabajador`
> (más abajo) en vez de borrarla.

**Atribuir exige la carpeta original.** El resumen versionado es anónimo a
propósito —no lleva nombres ni RUT— y por eso ya no basta para sembrar.
Ejecutar sin `--carpeta` **falla diciendo eso**: no degrada en silencio a la
carga por centro de costo, que es justamente el error que se corrigió.

**Los exámenes ocupacionales y las licencias no traen fecha.** Son escaneos sin
capa de texto: 87 de los 245 archivos. Se cargan igual, para que estén a la
vista, **una por persona**, y quedan **pendientes de validación**: la fecha la
lee Prevención del papel y la escribe con el mecanismo de corrección, que la
registra con su autor y su motivo sin tocar el archivo ni su hash.

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

`--carpeta` es **obligatoria**: sin ella no hay a quién atribuir las
constancias, y el comando se niega a sembrar en vez de colgarlas del centro de
costo. Se guarda el PDF verdadero de cada constancia, con su hash SHA-256.

El archivo se guarda con el nombre de la obligación y el RUT de su titular,
porque la evidencia ahora acredita a esa persona. **Quién puede abrir ese
archivo deja de ser una pregunta teórica**: los cuatro exámenes ocupacionales
son datos de salud de una persona identificada. Hoy solo Prevención y Sysadmin
entran al sistema, así que el riesgo no se materializa; hay que resolverlo
antes de abrir el sistema a los Encargados.

Si la carpeta tiene alguna constancia cuya carpeta de persona no trae un RUT
válido, el comando **se detiene y las enumera** en vez de inventar una
dotación. Hay que corregirlas en el origen.

### Retractar una siembra anterior

La base que se sembró antes de que el trabajador existiera tiene catorce
obligaciones atribuidas al centro de costo que en realidad son de personas. Se
retractan, no se borran:

```powershell
# Ver qué se cerraría, sin escribir nada.
.\.venv\Scripts\python.exe manage.py retractar_obligaciones_por_trabajador `
    --usuario <prevencionista>

# Retractar.
.\.venv\Scripts\python.exe manage.py retractar_obligaciones_por_trabajador `
    --usuario <prevencionista> --confirmar
```

Cada obligación se cierra con una versión nueva cuyo motivo declara el **error
de atribución** —y lo distingue de un cambio normativo—, en el canal de
bitácora «Retractación del piloto». La evidencia cargada bajo ellas sigue
consultable, descargable y verificable por hash. **No se descartaron**:
vuelven al plan cuando existan con su titular correcto. Ejecutarlo dos veces no
duplica cierres.

> **La siembra no se puede deshacer.** El modelo es append-only: lo que se
> escribe no se borra. Por eso el comando exige `--confirmar` y se niega a
> sembrar dos veces sobre el mismo centro de costo. Si no quieres esto en la
> base real, siémbralo en una base aparte.

## Lo que queda en pantalla

Las cuatro obligaciones de la instalación se leen igual que antes: tres en
**Sin evidencia** —matriz IPER, reglamento interno, comité paritario— y la
vigilancia de sílice en **No aplica**.

**Los tres «Sin evidencia» son el hallazgo más útil.** Son obligaciones que a
una bodega de 129 personas le corresponden y de las que la carpeta no tiene
nada. No es una falla de la siembra: es lo que el departamento verá al abrir el
plan.

Las catorce obligaciones de las personas se leen como **estado agregado**: el
peor estado presente y cuántas personas hay en cada uno. «Manejo de extintores:
Vencido — 5 de 52» quiere decir que hay cinco personas vencidas entre las 52 a
las que la obligación aplica, y desde ahí se abre el desglose para saber cuáles
cinco. Una persona a la que la obligación le aplica y no tiene ninguna
constancia aparece en **Sin evidencia**: eso es lo que la siembra anterior no
podía mostrar.

Los seis estados salen solos, sin que nadie los teclee. Ninguno se declaró: se
derivan de las fechas, la periodicidad, la validación y la aplicabilidad.

**El estado se mueve solo con el calendario.** Las constancias otorgan tres
años y los ciclos configurados son anuales o bienales, así que buena parte de
lo que la carpeta acredita aparece vencida. Esa diferencia es la conversación
que el piloto viene a abrir: **cuál es el ciclo real**.

## Recorrido sugerido

1. **Plan de aplicación de ADM04.** Las cuatro obligaciones de la instalación y
   las catorce agregadas de las personas, con su recuento. Nadie escribió
   ninguno de esos estados.
2. **Abrir el desglose de extintores.** Quiénes están vigentes, quiénes
   vencidos y quiénes sin ninguna constancia. Aquí se ve la cobertura real.
3. **Abrir una evidencia vencida.** La constancia real, del 8 de abril de 2024,
   a nombre de su titular y con su hash. El certificado dice que vale hasta
   2027; el sistema la da por vencida porque el ciclo configurado es anual.
4. **Validar un examen ocupacional corrigiendo su fecha.** Está pendiente
   porque el escaneo no declara fecha. Prevención la lee del papel y la escribe:
   queda una corrección con autor y motivo, el archivo y su hash no cambian, y
   la vigencia pasa a derivarse del dato confirmado. La pantalla muestra las dos
   fechas, la de la carga y la corregida.
5. **Bandeja de vencimientos.** Cada caso dice **a quién hay que citar**, no
   cuántos faltan, y se puede filtrar por trabajador.
6. **Consultar el plan a una fecha pasada.** El estado se reconstruye a esa
   fecha, con la dotación que existía entonces, sin tocar la historia.
7. **Bitácora.** Todos los actos de la siembra llevan el canal «Siembra del
   piloto», así que se distinguen de los que entren por la aplicación. El alta
   del trabajador, la corrección de fechas y la validación se leen como tres
   actos distintos.

## Cómo se leyó la carpeta

`resumir_respaldo_bodega` recorre
`<grupo de cargo>/<capacitación>[/<subtipo>]/<RUT - Nombre>/<archivo.pdf>` y de
cada PDF extrae la capa de texto. Las constancias de la plataforma traen
`REALIZADO: <fecha>` y `FECHA EXPIRACIÓN: <fecha>`; de ahí salen las fechas.

El resumen que deja en `importaciones/datos/` guarda **solo recuentos y pares
de fechas**: ni un nombre ni un RUT, para que pueda versionarse. La carpeta
original está excluida del repositorio en `.gitignore`. Ese es el motivo de que
la siembra necesite la carpeta: los nombres y los RUT que hacen falta para
atribuir cada constancia no están —ni deben estar— en el repositorio.

De cada carpeta de persona la siembra saca el RUT, que es la llave, y el
nombre, que es solo un atributo. Cuando el mismo RUT aparece con varias
escrituras del nombre —hay 184 carpetas de persona para 129 personas— se queda
con la más larga, porque las otras vienen truncadas. Cuando aparece bajo más de
un nivel de cargo, se queda con el que más constancias suyas contiene.

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

La lectura los tolera —las 245 constancias se reconocen y los 129 RUT se leen
sin excepciones—, pero conviene corregirlos en el origen:

- **49 de los 129 RUT aparecen con más de una grafía del nombre** —hay 184
  carpetas de persona para 129 personas—, casi siempre por truncamiento. El RUT
  es la llave confiable; el nombre no.
- **Separadores irregulares** en dos carpetas: una escribe `<RUT> Apellido...`
  sin el guion que separa, otra `<RUT> -Apellido...` sin el espacio.
- **Un RUT con un espacio antes del dígito verificador**, que rompe el patrón
  `12345678-9`.
- **Tres personas aparecen bajo más de un nivel de cargo.** La siembra se queda
  con el que más constancias suyas contiene, pero el cargo verdadero lo tiene
  que confirmar Prevención.
- **Cuatro archivos nombrados con el nombre de la persona** en vez del patrón
  habitual, dentro de las carpetas de licencia de conducir.
- **Las rutas superan los 260 caracteres** de Windows. Sin el prefijo de ruta
  extendida, `is_file()` devuelve `False` y los archivos desaparecen en
  silencio: el lector lo maneja, pero cualquier otra herramienta que se use
  sobre esta carpeta va a tropezar.
