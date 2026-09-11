# Sistema visual base, portada y operación del MVP

Status: ready-for-agent

Documento listo para planificación e implementación futura; no autoriza ejecutar
cambios ahora. Prevalece el corte de entrega solicitado al final de la entrevista
sobre la visión más amplia de pantallas registrada anteriormente.

## Problem Statement

Prevención necesita identificar rápidamente obligaciones vencidas, sin evidencia,
pendientes de validación y próximas a vencer. Hoy la portada ofrece enlaces y la
operación presenta filtros y listas sin una estructura visual compartida. Los
templates repiten el documento HTML; no hay base común ni CSS o JavaScript propio
integrado. Esto dificulta orientación, lectura y comparación de casos.

La información debe conservar el grano titular–obligación, la identidad de cada
centro y las reglas de cumplimiento existentes. El rediseño no puede convertir
documentos cargados en cumplimiento ni esconder personas incumplidas en promedios.

## Solution

Crear un sistema visual de escritorio con CSS propio, una estructura Django
compartida y dos pantallas migradas: portada y operación del piloto. Sidebar azul
petróleo, topbar blanca, fondo gris claro, tarjetas blancas, bordes redondeados,
sombras discretas, tablas compactas y estados con texto, símbolo y color.

La portada muestra cuatro KPI accionables, distribución por estado separada por
titular, filtros por centro y tipo, y accesos rápidos según permisos. Todo funciona
con HTML servido por Django, sin depender de JavaScript ni servicios de terceros.

### Alcance de esta entrega

1. Tokens visuales y estilos base de tipografía, espacios y elementos comunes.
2. Base HTML y layout de aplicación compartido, preparado para futuras pantallas.
3. Sidebar y barra superior con navegación y contexto del usuario.
4. Mensajes globales de Django.
5. Portada con KPI, gráficos accesibles y filtros.
6. Operación con filtros existentes y tabla de casos.
7. Accesibilidad y adaptación a escritorio de esas dos pantallas.

No se migra visualmente el inicio de sesión ni ninguna otra pantalla en este corte.
Los enlaces siguen abriendo sus destinos existentes. La transición temporal de
apariencia al salir de estas dos pantallas se acepta como límite de la entrega.

## User Stories

1. Como Prevencionista, quiero reconocer el nombre y logotipo institucional para identificar el sistema.
2. Como operador, quiero localizar la sección activa para orientarme al navegar.
3. Como operador, quiero un menú estable para acceder a operación y gestión.
4. Como Sysadmin, quiero acceder a administración e importaciones desde el menú para mantener los datos.
5. Como operador, quiero reconocer cuándo estoy en una demostración para no confundirla con operación real.
6. Como Prevencionista, quiero priorizar vencidas y sin evidencia para atender los incumplimientos.
7. Como Prevencionista, quiero contar casos pendientes de validación para conocer su impacto en cumplimiento.
8. Como Prevencionista, quiero ver los casos por vencer para anticipar renovaciones.
9. Como operador, quiero separar instalaciones y trabajadores para no mezclar unidades de conteo.
10. Como operador, quiero que una tarjeta abra sus casos para comprobar el número mostrado.
11. Como operador, quiero filtrar por centro y tipo para acotar mi trabajo.
12. Como operador, quiero que gráficos y enlaces conserven los filtros para mantener el contexto.
13. Como operador, quiero ver cero y una explicación cuando no haya casos para distinguir ausencia de resultados de un error.
14. Como Prevencionista, quiero conocer la distribución por estado para interpretar la situación actual.
15. Como usuario de lector de pantalla, quiero una tabla equivalente al gráfico para consultar los mismos datos.
16. Como Prevencionista, quiero acceder al listado sin evidencia para seleccionar qué caso resolver.
17. Como Prevencionista, quiero acceder a validaciones y alta de trabajador sin buscar esas acciones entre datos maestros.
18. Como operador, quiero ver únicamente acciones compatibles con mis permisos para evitar opciones engañosas.
19. Como operador, quiero distinguir al trabajador del centro en cada fila para saber a quién corresponde la obligación.
20. Como operador, quiero nombres y RUT parcialmente ocultos en operación para reducir exposición al compartir pantalla.
21. Como operador, quiero leer fecha de vigencia y estado con texto para no depender de colores.
22. Como operador, quiero conservar filtros al enviar el formulario para comparar resultados.
23. Como operador, quiero consultar tablas anchas sin desplazar toda la página para mantener visible la navegación.
24. Como usuario de teclado, quiero alcanzar menú, filtros y acciones con foco visible para operar sin ratón.
25. Como operador, quiero trabajar sin JavaScript para que el dashboard no dependa de scripts.
26. Como operador, quiero recibir mensajes accesibles para comprender el resultado de mis acciones.
27. Como operador de notebook, quiero ver el contenido en 1366 × 768 para trabajar sin una versión móvil.
28. Como responsable del piloto, quiero conservar su aviso de composición para no confundir un dashboard atractivo con un piloto validado.

## Implementation Decisions

### Invariantes y evidencia actual

- `acceso/views.py:inicio` no prepara KPI hoy. Preservar su redirección de anónimos
  y rechazo de usuarios sin rol operativo.
- `evidencias/views.py:operacion` usa `FiltroOperativo`, `ESTADOS_POR_FILTRO` y
  `casos_de_cumplimiento(en_fecha=timezone.localdate())`.
- `evidencias/services.py:casos_de_cumplimiento` produce casos de instalaciones y
  personas; reutilizarlo sin alterar cómo determina estado, titular o vigencia.
- `acceso/permisos.py`: operador es Prevencionista o superusuario. Validar exige
  grupo Prevencionista; ser superusuario por sí solo no concede esa validación.
- Mantener vocabulario de `CONTEXT.md` y reglas de ADR 0001 y 0004.
- Sin migraciones, cambios de modelos, dependencias o motor de base de datos.
- La petición explícita de mapa de archivos y tokens requiere rutas y valores
  concretos en esta especificación; representan la propuesta implementable.

### Mapa de templates y archivos

```text
templates/base.html
└── templates/layouts/aplicacion.html
    ├── templates/acceso/inicio.html
    └── templates/evidencias/operacion.html
```

`base.html` contiene doctype, `lang="es"`, UTF-8, viewport, título, CSS mediante
`{% static %}` y enlace para saltar al contenido. Bloques: `title`, `body` y
`extra_css`; sin dependencias de scripts. `aplicacion.html` contiene sidebar,
topbar, mensajes y un solo `main`; bloques `page_title`, `page_actions`, `content`.
Los includes no emiten un segundo `html`, `body` o `main`.

| Crear | Responsabilidad |
| --- | --- |
| `templates/base.html` | Documento y carga de recursos compartidos. |
| `templates/layouts/aplicacion.html` | Estructura de aplicación. |
| `templates/includes/sidebar.html` | Navegación y sección activa. |
| `templates/includes/topbar.html` | Logo, título, usuario, rol y entorno. |
| `templates/includes/mensajes.html` | Mensajes globales escapados. |
| `templates/includes/tarjeta_kpi.html` | Etiqueta, dos recuentos por titular y enlaces. |
| `templates/includes/estado_cumplimiento.html` | Estado semántico, texto y símbolo. |
| `templates/includes/estado_vacio.html` | Ausencia de resultados o configuración. |
| `templates/evidencias/includes/filtros_operacion.html` | Campos de filtros de operación. |
| `templates/acceso/includes/distribucion_estados.html` | Barras y tabla equivalente. |
| `static/prevencion/css/tokens.css` | Variables visuales. |
| `static/prevencion/css/base.css` | Texto, foco y elementos nativos. |
| `static/prevencion/css/layout.css` | Distribución y adaptación de escritorio. |
| `static/prevencion/css/componentes.css` | Botones, cards, mensajes, tablas y formularios. |
| `static/prevencion/css/dashboard.css` | KPI y gráficos. |
| `static/prevencion/img/logo-institucional.png` | Copia sin alterar de `image/LOGO SIMI LETREROS.png`. |
| `acceso/context_processors.py` | Contexto visual de rol y etiqueta de entorno. |
| `acceso/dashboard.py` | Resumen de presentación derivado de una lista de casos. |
| `evidencias/filtros.py` | Extracción del filtro compartido sin cambiar comportamiento previo. |
| `acceso/templatetags/__init__.py`, `acceso/templatetags/presentacion.py` | Formato de RUT oculto; sin consultas. |
| `acceso/tests/test_dashboard_http.py` | Contrato HTTP, datos, filtros y permisos. |
| `acceso/tests/test_presentacion.py` | Casos puros de ocultación de RUT. |

| Modificar | Cambio permitido |
| --- | --- |
| `templates/acceso/inicio.html` | Heredar layout y renderizar dashboard. |
| `templates/evidencias/operacion.html` | Heredar layout y mostrar tabla/filtros. |
| `acceso/views.py` | Preparar casos y contexto de portada. |
| `evidencias/views.py` | Importar filtro extraído y filtro visual adicional de titular. |
| `configuracion/settings.py` | `STATICFILES_DIRS`, context processor y etiqueta de entorno. |
| `scripts/demo-local.ps1` | Variable de sesión `DJANGO_ENTORNO=demo`, con restauración. |
| `evidencias/tests/test_operacion_piloto_http.py` | Cobertura de tabla, enlaces, filtros y privacidad. |
| `evidencias/tests/test_escala_bandejas.py` | Solo ampliación de cobertura si hace falta; conservar pruebas actuales. |
| `docs/recuperacion-entorno.md` | Comandos y resultados de verificación de la entrega. |

No crear carpetas CSS por pantalla sin necesidad ni un sistema genérico de tablas
con decenas de opciones. El layout resuelve estructura común; cada pantalla
conserva columnas y significado propios. No generar archivos JavaScript en V1.

### Tokens CSS propuestos

Valores iniciales concretos, sujetos únicamente a ajustes para cumplir contraste
y las dos resoluciones aprobadas; mantener la semántica de color acordada.

| Variable | Valor |
| --- | --- |
| `--color-sidebar` | `#12343B` |
| `--color-sidebar-text` | `#F8FAFC` |
| `--color-sidebar-active` | `#245563` |
| `--color-page` | `#F4F6F8` |
| `--color-surface` | `#FFFFFF` |
| `--color-text` | `#182A32` |
| `--color-muted` | `#52636D` |
| `--color-border` | `#D7E0E5` |
| `--color-control-border` | `#647782` |
| `--color-primary` | `#155E75` |
| `--color-primary-hover` | `#164E63` |
| `--color-focus` | `#1D4ED8` |
| `--color-vigente`, `--bg-vigente` | `#166534`, `#DCFCE7` |
| `--color-por-vencer`, `--bg-por-vencer` | `#854D0E`, `#FEF3C7` |
| `--color-vencido`, `--bg-vencido` | `#B91C1C`, `#FEE2E2` |
| `--color-pendiente`, `--bg-pendiente` | `#1E40AF`, `#DBEAFE` |
| `--color-sin-evidencia`, `--bg-sin-evidencia` | `#6B21A8`, `#F3E8FF` |
| `--color-no-aplica`, `--bg-no-aplica` | `#475569`, `#F1F5F9` |
| `--space-1` a `--space-8` | `4px`, `8px`, `12px`, `16px`, `24px`, `32px`, `40px`, `48px` |
| `--radius-control`, `--radius-card`, `--radius-pill` | `6px`, `12px`, `999px` |
| `--shadow-card` | `0 2px 8px rgb(15 23 42 / 6%)` |
| `--sidebar-width`, `--topbar-min-height` | `240px`, `80px` |
| `--font-body` | `system-ui, -apple-system, "Segoe UI", sans-serif` |
| `--font-size-body`, `--font-size-table`, `--font-size-small` | `16px`, `14px`, `13px` |
| `--font-size-h1`, `--font-size-h2`, `--font-size-kpi` | `28px`, `20px`, `32px` |
| `--line-height-body` | `1.5` |

No cargar tipografías, iconos o CSS desde CDN. Encabezados con peso 600–700;
recuentos tabulares con `font-variant-numeric: tabular-nums`. Mensajes, etiquetas
y fechas legibles sin usar mayúsculas sostenidas para textos largos.

### Sidebar, topbar y mensajes

- Sidebar visible a ambas resoluciones, ancho 240px. Nombre completo de aplicación
  admite varias líneas. Inicio; Operación (cumplimiento, vencimientos, pendientes);
  Gestión (centros, trabajadores, catálogo); Administración (admin, importaciones).
- Enlaces por nombres de URL existentes. Marcar sección actual con `aria-current`;
  ocultar el grupo Administración si no corresponde a Sysadmin. No cambiar el
  acceso real de otras vistas ni revocar permisos actuales del admin.
- No crear enlaces globales a planes o bitácora que requieren contexto.
- Topbar blanca: logo completo sin recolorear o recortar, título de pantalla,
  usuario y rol. Logo `object-fit: contain`, ancho orientativo 220px; nombre de la
  aplicación permanece en sidebar. Sin avatar, buscador o campana ficticios.
- Si usuario pertenece a ambos roles, mostrar ambos. Las capacidades se calculan
  una vez por petición y se reutilizan, sin consultar grupos desde cada include.
- Etiqueta `DEMOSTRACIÓN` solo cuando `DJANGO_ENTORNO=demo`. Predeterminado vacío;
  no inferir entorno desde DEBUG, usuario o contenido de la base. Leer variable
  de proceso, sin introducir carga automática de `.env`.
- Mensajes del framework: éxito, información, aviso y error, con estilos distintos,
  texto escapado y sin cierre que requiera JavaScript. `role=status` para mensajes
  informativos y `role=alert` para errores importantes; evitar anuncios duplicados.

### Controles compartidos y operación

- Botón primario petróleo, texto blanco; secundario blanco con borde; enlace para
  navegación. Altura mínima 36px en escritorio. No usar enlaces para acciones POST.
- Tarjetas blancas con borde/radio/sombra; acento de estado, etiqueta y cantidades.
  No hacer clicable todo el contenedor si contiene dos enlaces por titular.
- Formularios con label explícito, ayudas y errores asociados; hasta dos columnas
  cuando proceda. No reemplazar nombres de campos ni validación de Django.
- Filtros GET con botón Filtrar y enlace Limpiar; selección persistente, sin envío
  automático. Portada: `centro` y `tipo_centro`. Operación conserva `estado`,
  `tipo_centro`, `obligacion`, `centro`, `trabajador`; añade `titular` como filtro
  de presentación para enlazar recuentos separados.
- `titular` admite vacío, `centro_costo`, `trabajador`; no crea nuevos titulares.
  Parámetro desconocido se normaliza a vacío. Conservar tratamiento actual de
  IDs/valores inválidos. Filtros válidos incompatibles producen cero resultados.
- Tabla de operación: centro (código y nombre), obligación, titular, trabajador
  cuando corresponda, estado, vigencia hasta y acción. No exponer documentos de
  salud ni miniaturas. Mostrar guion explicado cuando no hay fecha.
- Texto de trabajador con RUT parcialmente oculto en filas y opciones del select.
  No dejar RUT completo en HTML oculto, atributos title/data, etiquetas o scripts;
  los valores de selección utilizan PK, nunca RUT. Patrón: solo últimos tres
  dígitos del cuerpo y verificador, como `••.•••.678-5`. No modificar el dato guardado.
- Conservar enlaces por caso: plan si No aplica; evidencia si existe; carga si no.
  Mantener selección de trabajador en la carga cuando el flujo lo soporte; no
  agregar una acción genérica que omita titular, centro u obligación.
- Conservar cantidad y aviso de composición del piloto. `piloto_conforme` no
  significa aceptación operativa, calidad normativa ni validación de documentos.
  Los filtros de la tabla no deben redefinir esa condición global existente.

### KPI y contrato de datos

Fecha de referencia: capturar una sola vez `timezone.localdate()` por petición y
mostrarla en portada. No inyectar un reloj fijo de demo en producción.

1. Resolver permisos y filtros una vez.
2. Obtener una única lista materializada desde `casos_de_cumplimiento(en_fecha)`.
3. Aplicar filtros de centro/tipo a esa lista con el criterio compartido de operación.
4. Recorrerla una vez y agrupar por estado y tipo de titular. El resumen no ejecuta SQL.
5. Reutilizar esos mismos grupos para tarjetas, barras, tabla accesible y enlaces.

Cuatro tarjetas, en orden: Vencidas, Sin evidencia, Pendientes de validación,
Por vencer. Cada tarjeta contiene recuento de instalaciones y recuento de
trabajadores; no una suma ambigua. No sumar el agregado del centro a sus personas.
Unidad: un caso titular–obligación emitido por el servicio; nunca cantidad de PDF,
versiones, renovaciones o personas distintas. Tres obligaciones vencidas de una
persona cuentan como tres casos.

La tarjeta de pendientes cuenta casos cuyo estado derivado es Pendiente de
validación. No equivale a la cantidad de documentos en la bandeja de validación:
una evidencia pendiente puede coexistir con otra vigente. El enlace del KPI lleva
a operación filtrada por estado/titular; el acceso rápido Validar evidencias lleva
a la bandeja documental existente, con su semántica propia.

Enlaces KPI: URL de operación con `estado`, `titular`, `centro` y `tipo_centro`
cuando correspondan. No incluir parámetros vacíos o perder el filtro de origen.
La portada no ofrece filtros de persona u obligación ni emite sus identidades.

Gráficos: dos distribuciones horizontales por los seis estados, una por titular,
con cantidades absolutas, etiquetas y tabla equivalente. Escala común para ambos
gráficos basada en el máximo de las series filtradas; máximo cero produce barras
vacías, sin divisiones por cero. Representar únicamente los casos realmente
devueltos; no inventar combinaciones No aplica ni incluir obligaciones cerradas.
Sin porcentajes ni tendencias en V1. Usar SVG generado en servidor sin scripts,
oculto a tecnología asistiva si la tabla adyacente ya aporta toda la información.

Totales secundarios: centros operables no franquicia que cumplen filtros de centro
y tipo, incluidos aquellos sin casos; trabajadores validados con asignación vigente
en esos centros a la fecha de referencia. Reutilizar lectura de dotación existente,
sin consultar por trabajador. Rotular exactamente qué se cuenta.

Accesos rápidos: Revisar vencidas y Resolver sin evidencia llevan a operación con
el estado y filtros de centro/tipo. Validar evidencias conserva esos filtros solo
si la bandeja los soporta; no prometer aplicar filtros que actualmente ignora.
Registrar trabajador abre su formulario actual, sin introducir cambios en él.

Contexto propuesto: `fecha_referencia`, `filtros`, `kpis`, `distribuciones`,
`total_centros`, `total_trabajadores`, `navegacion`, `capacidades`. Los includes
reciben datos listos para presentar; no llaman servicios ni cuentan querysets.
La agrupación debe ser una función pura sobre casos, no una nueva regla de negocio.

### Consultas y rendimiento

- Prohibido volver a ejecutar el servicio por tarjeta, estado o gráfico.
- Centralizar filtro extraído en `evidencias/filtros.py` para evitar que portada
  importe una vista o copie reglas. Mantener comportamiento de vistas consumidoras.
- Los casos por persona ya usan carga en bloque. Preservar sus pruebas de escala.
- El camino de instalaciones conserva consultas por caso en el código actual;
  no prometer coste constante global sin medirlo ni reescribirlo en esta entrega.
- Medir número de consultas del listado de casos como línea base. El coste añadido
  del dashboard debe ser constante respecto del número de tarjetas y personas;
  registrar medición concreta en validación. Sin consultas desde templates por fila.
- Cero caché de datos sensibles entre usuarios, cero endpoints de gráficos y cero
  peticiones periódicas en V1. Una petición HTTP prepara toda la pantalla.

### Permisos y ausencia de JavaScript

Misma distribución para Prevencionista y Sysadmin. Sidebar y acciones derivan de
capacidades existentes, nunca de texto visible del rol. Validar evidencias solo
se ofrece a quien tenga grupo Prevencionista. Registrar trabajador conserva el
acceso operativo que tiene hoy. Admin/importación son accesos de Sysadmin en el
menú acordado. El servidor sigue comprobando cada petición y cada acción.

No añadir logout, búsquedas, notificaciones o selección de roles ficticios.
Operación completa mediante enlaces y formularios nativos; mensajes y gráficos
renderizados en servidor. Mantener CSRF, POST y multipart en cualquier estructura
compartida, sin migrar formularios de carga/validación en esta entrega.

### Adaptación de escritorio y accesibilidad

- Objetivos: 1366 × 768 y 1920 × 1080 a escala de navegador 100%. Sin versión móvil.
- Sidebar siempre visible, contenido con `min-width: 0`; cuatro KPI a ancho
  suficiente, dos columnas si el espacio efectivo se reduce. Filtros se envuelven.
- Topbar usa altura mínima, no altura fija que recorte contenido al ampliar texto.
- Tablas con contenedor `overflow-x: auto`, nombre accesible y foco de teclado;
  ninguna anchura mínima de tabla debe forzar scroll horizontal de toda la página.
- No ocultar columnas esenciales para simular adaptación. Evitar cabeceras fijas
  que tapen elementos enfocados; sidebar puede tener scroll vertical propio.
- Validar ampliación de texto al 200%: permitir reflujo y scroll vertical; sin
  implementar menú móvil ni desactivar zoom. No garantizar presentación de teléfono.
- Un h1 por pantalla; jerarquía h2 para secciones; landmarks y enlace Saltar al contenido.
- `label for/id`, ayuda y error con `aria-describedby`; preservar input y valor.
- Tablas con caption y encabezados `scope`; no usar tablas para distribuir tarjetas.
- Foco visible con contorno de 3px y separación de 2px, variante clara sobre sidebar.
  Contraste mínimo objetivo: 4,5:1 para texto normal, 3:1 texto grande y controles.
- Estados siempre escritos; iconos decorativos sin anuncios redundantes. Sin
  parpadeos, animación indispensable ni información dependiente de hover.
- Logo con texto alternativo institucional. Números visibles aunque falle el SVG.
- Portada solo contiene información agregada de titulares; usuario de sesión y rol
  en topbar son la excepción acordada. Sin nombres de trabajadores ni RUT en portada.

## Testing Decisions

### Interfaces de prueba

Usar principalmente GET HTTP de `/` y `/evidencias/operacion/`, siguiendo las pruebas
existentes de portada y operación. Esta especificación propone esas interfaces para
la implementación futura, sin abrir una entrevista adicional. Las pruebas de formato
de RUT son puras. No probar nombres internos de funciones ni detalles de CSS por snapshot.

### Pruebas automatizadas necesarias

1. Anónimo redirigido; usuario sin rol obtiene 403; Prevencionista y Sysadmin acceden.
2. Superusuario sin grupo Prevencionista no recibe acción Validar; el rechazo POST
   existente sigue protegido. Roles combinados conservan capacidades correctas.
3. Portada y operación usan layout compartido; links existentes y sección activa.
4. Mensajes globales escapados y accesibles, incluidos mensaje con caracteres HTML.
5. Fixture sintética con ambos titulares y seis estados; cifras esperadas literales.
6. Varias evidencias/renovaciones del mismo caso no multiplican KPI. Distinguir
   documentos pendientes de casos con estado Pendiente de validación.
7. Dos filtros simultáneos, filtro incompatible, parámetros inválidos y cero datos.
8. Seguir cada enlace KPI y comparar sus filas con el recuento y titular de origen.
9. Cero datos personales de trabajadores en portada. RUT completo ausente de HTML
   de operación, incluidos select, title y atributos; ejemplo de RUT corto y DV K.
10. Totales secundarios no confunden casos con personas; centros sin casos se cuentan.
11. Preservar composición del piloto y enlaces al historial sin cambiar sus parámetros.
12. Tabla y gráficos muestran mismos seis estados y cantidades; sin cero dividido.
13. Comparar consultas con fixture de pequeña y mayor dotación: agrupación/tarjetas
    no añaden crecimiento por persona. Respetar línea base de servicio existente.
14. Mantener intactas las 122 pruebas aprobadas, incluidas las correcciones temporales.
    Toda fixture temporal nueva controla fecha/hora con `reloj_en` y zona Django.

No reemplazar expectativas correctas para acomodar markup; cambios en aserciones
puramente estructurales deben conservar la regla de negocio que verificaban.

### Validación técnica y visual

- Django check, mypy y suite completa en PostgreSQL aislado mediante
  `scripts/pruebas-locales.ps1`; 122 pruebas actuales más las nuevas, sin omitir aceptación.
- Comprobar `findstatic` para cada CSS/logo; no confundir static con MEDIA_ROOT.
- Revisión de escritorio en ambas resoluciones, con datos sintéticos abundantes,
  nombres largos, filtros activos, cero resultados, mensajes y los seis estados.
- Recorrido con teclado: saltar contenido, sidebar, filtros, cards, tabla y acciones;
  foco siempre visible, orden coherente, sin trampas.
- Deshabilitar JavaScript y repetir filtros, navegación, gráficos y mensajes.
- Comprobar visualmente texto ampliado y contraste de todas las combinaciones.
- Capturas de portada y operación con usuarios Prevencionista, Sysadmin y ambos roles.
  No capturar datos reales. El usuario aprueba presentación; Prevención, claridad operativa.

### Criterios de aceptación verificables

| ID | Condición de aprobación |
| --- | --- |
| AC01 | Solo portada y operación adoptan el nuevo layout en esta entrega; admin intacto. |
| AC02 | Paleta, logo completo sobre blanco, sidebar y topbar coinciden con los acuerdos. |
| AC03 | Ningún corte ni scroll horizontal global a 1366 × 768 y 1920 × 1080. |
| AC04 | Tablas anchas desplazables con teclado dentro de su contenedor. |
| AC05 | Cuatro KPI con recuentos separados por titular verificables contra sus enlaces. |
| AC06 | Filtros de portada se conservan en KPI/gráficos/listado de destino. |
| AC07 | No hay KPI estimados, porcentajes ambiguos o consultas independientes por tarjeta. |
| AC08 | Cifras, gráficos, tablas y estados vacíos funcionan sin JavaScript. |
| AC09 | Controles y permisos del servidor mantienen su comportamiento previo. |
| AC10 | Portada no expone trabajadores; operación no emite su RUT completo. |
| AC11 | Estados tienen texto y señal visual; navegación por teclado y contraste verificados. |
| AC12 | Fecha de referencia y DEMOSTRACIÓN, cuando procede, aparecen claramente. |
| AC13 | CSRF, POST, multipart, GET e historial no sufren regresiones. |
| AC14 | Django check y mypy correctos; 122 pruebas originales y nuevas pasan sobre PostgreSQL. |
| AC15 | No hay recursos externos, secretos ni rutas personales en código/configuración añadidos. |
| AC16 | Resultados y límites observados se documentan antes de solicitar aprobación visual. |

## Out of Scope

- Cambiar estados, periodicidad, cálculo de vigencia, agregación, titular o permisos.
- Rediseñar login, vencimientos, pendientes, trabajador, planes, evidencia, catálogo,
  bitácora, importación o admin. Sus enlaces siguen disponibles sin migración visual.
- Aplicar RUT oculto a listados fuera de operación en este corte; registrar esta
  limitación, sin afirmar privacidad global ya implementada.
- Crear nuevas reglas para acceso a archivos de salud o nuevos roles.
- Logout nuevo, búsqueda global, notificaciones, tendencias históricas, exportaciones,
  paginación nueva, SPA, framework visual, librerías de gráficos o pipeline frontend.
- Versión móvil, menú plegable móvil, instalación en producción y uso de datos reales.
- Refactorizar consultas productivas para resolver problemas ajenos a presentación.

## Further Notes

Fuente de decisiones: `docs/decisiones-sistema-visual.md`; primera entrega acotada
por la última instrucción del usuario. Criterios de escritorio y revisión aprobados.

Riesgos principales: duplicar casos al agregar; confundir pendientes documentales
con estado de cumplimiento; perder filtros al navegar; emitir RUT completo en
selects aunque la fila esté ocultada; cargar grupos/querysets repetidamente en
includes; alterar acceso al mover lógica de filtros; romper aserciones de texto
útiles al sustituir listas por tablas; interpretar la etiqueta de demo como permiso.

La enumeración actual es la autoridad para el conjunto de casos. Si se detecta una
incoherencia de negocio o de consulta histórica, registrarla como trabajo separado;
no corregirla silenciosamente durante el rediseño ni inventar una serie de datos.

No hay implementación, instalación, cambios de datos, commit ni push asociados
a la publicación de esta especificación.
