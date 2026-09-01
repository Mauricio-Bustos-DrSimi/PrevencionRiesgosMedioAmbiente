# App web propia sobre PostgreSQL, no el patrón Postgres + Power BI

El resto de los proyectos de BI del área entrega tableros de Power BI sobre un modelo dimensional en PostgreSQL (ver `../DashboardHS`). Aquí no aplica: este sistema es operacional y de uso diario, la carga de evidencia documental es su función central, y requiere autoría, versionado e integridad de archivos que un tablero de lectura no puede dar.

Decisión: aplicación web propia sobre PostgreSQL en el servidor `172.23.1.128`, con base de datos dedicada. Los archivos de evidencia se guardan con su hash SHA-256 registrado, de modo que se pueda probar que el documento exhibido es exactamente el que se cargó.

## Consequences

- Se asume mantención de una aplicación, no solo de un modelo de datos: autenticación, permisos y respaldo pasan a ser responsabilidad del proyecto.
- Power BI sigue siendo válido más adelante como capa de reporte gerencial *sobre* esta base, pero nunca como vía de carga.
