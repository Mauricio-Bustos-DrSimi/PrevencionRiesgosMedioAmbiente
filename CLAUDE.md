# Prevención de Riesgos y Medio Ambiente — Contexto del proyecto

Sistema integral de gestión de prevención de riesgos y medio ambiente para **Farmacias de Similares (Chile)**, con **trazabilidad comprobable** ante fiscalización. Cubre SSO (Ley 16.744, DS 594, DS 44) y medio ambiente (incluida Ley REP 20.920). Usuario primario: **Departamento de Prevención de Riesgos**, uso diario.

## Agent skills

### Issue tracker

Las especificaciones e issues se almacenan como Markdown local bajo `.scratch/`. Consulta `docs/agents/issue-tracker.md`.

### Triage labels

Usa las cinco etiquetas canónicas de triage. Consulta `docs/agents/triage-labels.md`.

### Domain docs

El proyecto usa un único contexto de dominio, definido en `CONTEXT.md`, con decisiones en `docs/adr/`. Consulta `docs/agents/domain.md`.

Vocabulario canónico en [CONTEXT.md](./CONTEXT.md). Decisiones en [docs/adr/](./docs/adr/).

## Decisiones tomadas
- **Núcleo del modelo:** Obligación + Evidencia + Vigencia. El estado de cumplimiento se **deriva**, nunca se teclea. Todo append-only (ADR 0001).
- **Titulares de obligación:** centro de costo, trabajador, externo (contratista, Ley 20.123, en dos niveles: empresa y faena) y empresa (REP). Franquicias **fuera de alcance** por exclusión declarada.
- **El trabajador es titular efectivo (ADR 0004).** La evidencia se carga contra un titular explícito: el centro de costo sigue estando siempre, pero como **contexto**, no como titular único. Para una obligación de titular trabajador el centro muestra un **estado agregado** —el peor estado presente y el recuento por estado—, con desglose por persona. La identidad del trabajador es su RUT y su pertenencia a un centro de costo es histórica y append-only.
- **Grano:** centro de costo individual, identificado por **código contable oficial** (`CveUnidad` solo como referencia cruzada). ~350 centros de costo, ~2.500 trabajadores.
- **Plan de aplicación:** individual por centro de costo, partiendo de sugerencia por tipo; cada cambio con autor, fecha y motivo.
- **Estados:** Vigente / Por vencer / Vencido / Pendiente de validación / Sin evidencia / No aplica. Periodicidad vive en la obligación.
- **Flujo:** el Encargado carga evidencia y crea trabajadores (en estado no validado); **Prevención valida** y administra datos maestros; solo Prevención traslada o elimina trabajadores.
- **Roles:** Encargado, Prevencionista, Sysadmin, Lector. Cuentas **locales** (no Entra ID). Jerarquía zonal postergada.
- **Stack:** **Django** + plantillas server-rendered + HTMX sobre PostgreSQL, servidor **172.23.1.128**, BD dedicada. Sin SPA (ADR 0003). Nomenclatura de esquema y código **en español**.
- **Admin de Django:** en el MVP, Prevención y Sysadmin lo usan para todos los datos maestros; las pantallas propias cubren solo la operación diaria (carga, validación, bandeja de vencimientos). Destino a mediano plazo: pantalla propia para armar planes de aplicación (es flujo de dominio, no CRUD). Los Encargados **nunca** acceden al admin.
- **Archivos:** en disco del servidor, con **hash SHA-256** en la BD. Retención **indefinida** por defecto.
- **Catálogo de obligaciones:** hoy en Excel (matrices legales del departamento); pasa a vivir **dentro del sistema**, versionado.
- **IPER:** por ahora es una obligación más ("tener matriz IPER vigente", se guarda el documento). Modelarla completa es fase posterior.
- **Notificaciones:** correo semanal al Encargado (lo suyo por vencer), diario al Prevencionista (vencidos y pendientes de validación).
- **Cálculo REP:** sigue viviendo donde está hoy (`../Prevencion/LeyREPAnual.sql`, `Reciclaje.pbix`). El sistema guarda la obligación y la evidencia de la declaración, no reimplementa el cómputo.

## Secuencia de construcción
1. Modelo de datos + catálogo de obligaciones + centros de costo
2. Planes de aplicación + carga por Prevención en **piloto de 8-10 centros de costo heterogéneos** (varias farmacias + un centro administrativo + una bodega)
3. Vigencias, estados y bandeja de vencimientos
4. Apertura a Encargados, por lotes
5. Trabajadores y obligaciones por persona
6. Externos y verificaciones por faena
7. Obligaciones de empresa (REP) y notificaciones por correo

**MVP = pasos 1 a 3**, a producción el **primer trimestre de 2027**, usado solo por el departamento. Regla: no se abre a los 350 Encargados hasta que el piloto complete un ciclo de vencimiento y renovación.

El **paso 5 se adelantó al paso 4**: el paso 4 estaba bloqueado por esa regla, y el piloto no podía completar un ciclo real porque el 100 % de su material probatorio es por persona y el modelo no tenía personas. Falta todavía **ampliar el piloto a 8-10 centros con respaldo real** (paso 2), que se pospuso a propósito para no replicar el error de atribución a ocho centros más.

## Riesgos y pendientes
- **Los exámenes ocupacionales son datos de salud de una persona identificada.** Desde ADR 0004 la evidencia se atribuye al trabajador, así que quién puede abrir ese archivo dejó de ser una pregunta teórica. Hoy solo Prevención y Sysadmin entran al sistema, de modo que el riesgo no se materializa; **hay que resolverlo antes del paso 4**: un Encargado no debería poder abrir el examen ocupacional de su subordinado.
- **Ciclo de vida de cuentas locales sin definir** (caducidad, recuperación, revisión de cuentas activas, desactivación al egreso). Cerrar antes de implementar autenticación. Sin integración con RRHH, nadie avisa cuando alguien se va.
- **Respaldo de `.128` no confirmado**; se verificará después del MVP. Con retención indefinida, el respaldo *es* la trazabilidad: BD y directorio de archivos deben respaldarse como una sola unidad.
- **Soporte en producción sin dueño**; se definirá según la carga. Es prerrequisito real del paso 4.
- **Dotación sin fuente automática:** 2.500 trabajadores mantenidos a mano. Hoy se trabaja con información vencida.
- **La bitácora del dominio hay que construirla igual**: Django resuelve auth, roles y mantención de datos maestros, pero su `LogEntry` no es el registro append-only que exige ADR 0001.

## Notas de entorno
- Las farmacias **sí están en la red interna**: no se requiere publicar la aplicación hacia afuera.
- Referencia de convenciones del área: `../DashboardHS/CLAUDE.md` (PostgreSQL en 172.23.1.30, esquema `dw`).

### Response Style
- When reporting information to me, be extremely concise and scrifice grammar for the sake of concision.