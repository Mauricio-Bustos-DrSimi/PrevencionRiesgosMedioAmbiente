# Django con plantillas server-rendered + HTMX, no FastAPI ni SPA

La aplicación se construye con **Django** sobre PostgreSQL, sirviendo **plantillas server-rendered con HTMX** para la interactividad puntual. No hay SPA ni frontend separado: el sistema son formularios, listados y carga de archivos, y un segundo cuerpo de código en React/Vue agregaría build y mantención sin beneficio funcional.

Se evaluó **FastAPI + frontend propio** y se descartó: obligaba a construir a mano la autenticación con cuentas locales, la gestión de los cuatro roles, y las pantallas de mantención de catálogo, centros de costo, planes de aplicación y usuarios. Django trae todo eso de fábrica, y el esfuerzo del equipo (TI + Inteligencia de Negocios) queda disponible para lo que sí es específico del dominio: vigencias, validación y bitácora.

## Consequences

- Los cuatro roles (Encargado, Prevencionista, Sysadmin, Lector) se apoyan en el sistema de usuarios, grupos y permisos de Django, con cuentas locales.
- El panel de administración de Django cubre la mantención de datos maestros sin escribir pantallas.
- **La bitácora del dominio se construye igual**: el `LogEntry` del admin registra cambios hechos por el admin, no el "qué, quién, cómo y cuándo" append-only que exige ADR 0001. No confundir uno con el otro.
- Nadie debería "modernizar" esto agregando un frontend SPA más adelante: la ausencia de SPA es deliberada.
