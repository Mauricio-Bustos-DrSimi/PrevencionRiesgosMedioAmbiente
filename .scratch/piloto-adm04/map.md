# Mapa de tickets del piloto ADM04

Fuente: [spec.md](./spec.md)

| N.º | Ticket | Estado | Dependencias principales |
|---:|---|---|---|
| 01 | [Descarga autenticada de evidencias](./issues/01-descarga-autenticada-evidencias.md) | ready-for-agent | Ninguna |
| 02 | [Protección de exámenes ocupacionales](./issues/02-proteccion-examenes-ocupacionales.md) | ready-for-agent | 01 |
| 03 | [Cierre de sesión](./issues/03-cierre-sesion.md) | ready-for-agent | Ninguna |
| 04 | [Integridad mediante POST con CSRF](./issues/04-integridad-post-csrf.md) | ready-for-agent | Ninguna |
| 05 | [Permisos de Administrador, Prevencionista y Encargado](./issues/05-permisos-encargado-lector.md) | completed | 01, 02 y decisiones confirmadas del MVP |
| 06 | [Periodicidades y fuentes de ADM04](./issues/06-periodicidades-normas-adm04.md) | blocked-by-business | Fuentes oficiales de las 18 obligaciones |
| 07 | [Estado global de extintores](./issues/07-estado-global-extintores.md) | blocked-by-business | 06 y precedencia de estados |
| 08 | [Siembra definitiva del piloto](./issues/08-siembra-definitiva-piloto.md) | blocked-by-business | 06, 07, 12, 13, 14, 15 y 16 |
| 09 | [PostgreSQL productivo](./issues/09-postgresql-productivo.md) | blocked-by-infrastructure | Infraestructura productiva |
| 10 | [Respaldo conjunto de base y evidencias](./issues/10-respaldo-base-evidencias.md) | blocked-by-infrastructure | 09 y almacenamiento de evidencias |
| 11 | [Despliegue productivo](./issues/11-despliegue-productivo.md) | blocked-by-infrastructure | 01–04, 09, 10 y 12–16 |
| 12 | [Gobierno del catálogo y actas](./issues/12-gobierno-catalogo-actas.md) | ready-for-agent | Ninguna |
| 13 | [Áreas y responsables históricos](./issues/13-areas-responsables-historicos.md) | ready-for-agent | 12 |
| 14 | [No aplica revisable](./issues/14-no-aplica-revisable.md) | ready-for-agent | 12 |
| 15 | [Versiones con fecha efectiva](./issues/15-versiones-fecha-efectiva.md) | ready-for-agent | 12 |
| 16 | [Aislamiento de demostración](./issues/16-aislamiento-demostracion.md) | blocked-by-infrastructure | Definición de barreras y recursos separados |

Los tickets 01–11 corresponden a la lista solicitada. Los tickets 12–16 son
prerrequisitos independientes exigidos por la especificación y evitan incluir
cambios de gobierno, trazabilidad y aislamiento dentro de la siembra.
