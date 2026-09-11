# Decisiones del sistema visual

Estado: decisiones cerradas para especificación. No autoriza implementación.

## Alcance de esta conversación

Registrar decisiones de diseño antes de modificar templates, CSS, JavaScript,
vistas o lógica de negocio. Separar primera versión y mejoras posteriores.
No cambiar permisos mediante decisiones de presentación.

## Base visual acordada

Confirmada en la ronda 6, con la exclusión de versión móvil acordada:

- Sidebar azul petróleo oscuro, barra superior blanca y fondo gris muy claro.
- Tarjetas blancas, bordes redondeados y sombras discretas.
- Vigente verde; Por vencer ámbar; Vencido rojo; Pendiente de validación azul;
  Sin evidencia violeta; No aplica gris. Mantener texto además del color.
- CSS propio, sin framework visual. Sin versión móvil; adaptación entre
  pantallas de escritorio con sidebar visible y tablas desplazables.
- Mantener el diseño del admin de Django.
- Operación disponible sin JavaScript.
- No añadir búsqueda global ni notificaciones sin funcionalidad real.
- Usar la referencia únicamente como lenguaje visual, sin copiar marcas,
  textos ni contenido.

## Hechos comprobados

- `acceso/permisos.py` limita la operación actual a Prevencionista y Sysadmin.
  Los actos de validación requieren pertenencia al grupo Prevencionista.
- `CONTEXT.md` también describe Encargado y Lector; su apertura operativa
  está postergada según `CLAUDE.md`.
- ADR 0004 exige preservar el titular, la dotación histórica y el peor estado
  en el agregado del centro. Un indicador no debe ocultar incumplimientos.
- El usuario indicó `image/`; contiene `LOGO SIMI LETREROS.png`, recurso
  institucional elegido para el diseño. No se ha copiado ni modificado.
- La documentación identifica los exámenes ocupacionales como información
  sensible; el diseño no sustituye controles de acceso.

## Decisiones pendientes

- Identificar a la persona de Prevención que validará la claridad operativa
  antes de realizar esa revisión; no bloquea el cierre del diseño.

## Acuerdos cerrados

### Ronda 1: identidad, audiencias y prioridad

- Nombre visible: **Prevención de Riesgos y Medio Ambiente**.
- Logotipo: `image/LOGO SIMI LETREROS.png`, indicado por el usuario.
- Primera versión: Prevencionista y Sysadmin comparten indicadores y distribución;
  las acciones se muestran según los permisos existentes. Sysadmin tendrá además
  acceso a administración e importaciones. No se amplían permisos por el rediseño.
- Mejora posterior: portadas para Encargado y Lector cuando se habiliten sus flujos.
- Prioridad: obligaciones vencidas y sin evidencia; después documentos pendientes
  de validación y próximos vencimientos. Los indicadores generales son contexto.

### Ronda 2: navegación e indicadores

- Menú: Inicio; Operación (cumplimiento, vencimientos, pendientes de validación);
  Gestión (centros de costo, trabajadores, catálogo de obligaciones);
  Administración (admin Django e importaciones, según permisos existentes).
- Planes y trazabilidad se abren desde el centro, trabajador u obligación;
  no se agregan accesos globales sin contexto.
- Barra superior: logotipo, título de pantalla, usuario y rol; etiqueta visible
  cuando el entorno sea de demostración. Nombre completo de la aplicación en
  la cabecera del menú.
- KPI principales: Vencidas, Sin evidencia, Pendientes de validación y Por vencer.
- Unidad: casos titular–obligación, con recuentos separados de instalaciones
  y trabajadores. Una persona con tres obligaciones vencidas cuenta como tres casos.
  No contar documentos ni sumar el agregado del centro a sus casos individuales.
- Cada tarjeta abre el listado filtrado correspondiente. Centros y trabajadores
  totales son información secundaria.

### Ronda 3: gráficos, acciones rápidas y privacidad

- Primera versión: distribución por estado mediante barras horizontales,
  separando instalaciones y trabajadores. Mostrar cantidades y etiquetas visibles,
  acompañadas de una tabla accesible.
- Mejora posterior: tendencias históricas, una vez definidos períodos y comparaciones.
- Accesos rápidos: Revisar vencidas, Resolver sin evidencia, Validar evidencias
  y Registrar trabajador, según permisos existentes. Resolver sin evidencia abre
  el listado para seleccionar el caso; no carga sin centro y obligación concretos.
- Acciones administrativas en el menú de Sysadmin.
- Portada: solo cantidades agregadas, sin nombres, RUT ni detalles de exámenes
  ocupacionales.
- Listados operativos: nombre y RUT parcialmente oculto. RUT completo solo en
  el detalle autorizado. El patrón está definido en la ronda 5.
- Esta presentación reduce exposición al compartir pantalla; no sustituye
  los controles de acceso a documentos.

### Ronda 4: densidad y primera versión

- Tablas compactas, texto legible y acciones claras.
- Formularios más espaciosos, agrupados por tema; en escritorio, hasta dos
  columnas de campos relacionados.
- No habrá versión móvil. Esta decisión sustituye la propuesta de menú móvil
  y la parte móvil del diseño responsive inicial. No se implementará una
  distribución específica para teléfonos. La operación sin JavaScript se conserva.
- Primera versión: inicio de sesión, portada, operación, vencimientos,
  pendientes, consulta de centros y trabajadores, planes, carga y validación
  de evidencia.
- Catálogo, bitácora e importación reciben el tratamiento compartido acordado
  posteriormente en la ronda 6.

### Ronda 5: escritorio, filtros y RUT

- Sidebar siempre visible en escritorio. Las tablas anchas tendrán desplazamiento
  horizontal dentro de su contenedor, sin desarrollar menú móvil.
- Portada: todos los centros operables inicialmente, con filtros por centro y
  tipo de centro. Fecha actual como referencia; tarjetas, gráficos y enlaces
  comparten el mismo alcance filtrado.
- Primera versión: la consulta histórica permanece en los planes.
- Listados: mostrar nombre y RUT ocultando todo salvo los tres últimos dígitos
  del cuerpo y el dígito verificador; ejemplo `••.•••.678-5`.
- El RUT completo se conserva únicamente en el detalle autorizado.
- Resoluciones de revisión confirmadas al cierre: 1366 × 768 y 1920 × 1080.

### Ronda 6: consistencia, identidad y revisión

- Catálogo, bitácora e importación reciben menú, barra superior y estilos comunes
  en la primera versión, conservando su organización. Reorganización detallada
  reservada para una segunda etapa.
- Se confirma la paleta de la base visual y los colores por estado.
- Logotipo completo sobre blanco, sin deformar ni recolorear.
- CSS propio, admin sin rediseñar y aplicación utilizable sin JavaScript.
- Reparto de revisión aceptado según la recomendación presentada: presentación
  para aprobación del usuario y claridad del trabajo diario validada por una
  persona de Prevención. La revisión técnica de Codex acompaña esas aprobaciones.
- Muestra inicial: portada, operación y validación de evidencia.

### Criterios de aceptación confirmados

- Revisar escritorio a 1366 × 768 y 1920 × 1080.
- Sin contenido cortado ni desplazamiento horizontal de toda la página;
  las tablas anchas se desplazan dentro de su contenedor.
- Texto legible, navegación por teclado y estados reconocibles además del color.
- KPI, gráficos y listados coherentes bajo los mismos filtros.
- Datos ficticios, ocultación de RUT y permisos respetados.
- Recorrido operativo completo utilizable sin JavaScript.

### Corte de la primera entrega técnica

El usuario acotó posteriormente la primera entrega a sistema visual base,
layouts compartidos, sidebar, topbar, mensajes globales, portada y operación,
con accesibilidad y adaptación a escritorio. Las demás pantallas de la visión
acordada quedan para entregas posteriores, incluido aplicarles la estructura común.
No se modifica el admin. La muestra inicial de validación de evidencia se pospone
hasta la entrega que incluya esa pantalla.

Especificación implementable: `../.scratch/sistema-visual-base/spec.md`.
