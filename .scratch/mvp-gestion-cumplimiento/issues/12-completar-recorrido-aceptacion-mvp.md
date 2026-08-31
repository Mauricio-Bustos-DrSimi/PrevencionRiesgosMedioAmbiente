# 12: Completar el recorrido de aceptación del MVP

**What to build:** Un recorrido de aceptación reproducible demuestra sobre PostgreSQL que el piloto puede configurar aplicabilidad, cargar y validar evidencia, transitar por vencimiento, renovar y exhibir la bitácora sin perder evidencia ni trazabilidad.

**Blocked by:** 10: Demostrar trazabilidad append-only de extremo a extremo; 11: Operar el conjunto de centros de costo del piloto.

**Status:** resolved

- [x] El recorrido usa el cliente HTTP de Django y atraviesa las interfaces públicas desde la autenticación hasta la consulta final de la bitácora.
- [x] El recorrido configura un centro de costo y su plan de aplicación, carga una evidencia, observa Pendiente de validación y luego la valida.
- [x] El tiempo controlado demuestra Vigente, Por vencer y Vencido sin editar manualmente el estado de cumplimiento.
- [x] La renovación conserva la evidencia anterior y restablece el estado derivado correspondiente.
- [x] La consulta de una fecha pasada reproduce el estado de cumplimiento y la aplicabilidad que correspondían a ese momento.
- [x] La bitácora permite explicar cada acto del recorrido y la verificación SHA-256 confirma la integridad de los archivos.
- [x] El recorrido se ejecuta contra PostgreSQL y usa almacenamiento temporal aislado para los archivos de prueba.
- [x] La suite completa queda verde y documenta cómo repetir la demostración antes de ampliar el piloto.

## Comments

El recorrido está construido en `aceptacion/tests/test_recorrido_mvp_http.py` y
el procedimiento en `docs/recorrido-aceptacion-mvp.md`.

Las dos casillas abiertas dependen de una ejecución contra PostgreSQL que
todavía no se ha hecho:

- El recorrido está marcado `@skipUnless(connection.vendor == "postgresql")`, así
  que sobre SQLite se **omite** en lugar de pasar, e informa el motivo. El
  almacenamiento temporal aislado sí está resuelto.
- La suite completa queda verde sobre SQLite (84 pruebas, 1 omitida: este
  recorrido). No cuenta como la demostración hasta que el recorrido corra sobre
  PostgreSQL.

Durante el desarrollo el recorrido se verificó relajando temporalmente esa
condición, y su lógica quedó comprobada con mutaciones dirigidas (correr la
fecha de *Por vencer*, la fecha histórica de *Vencido* y apuntar el rechazo de
carga a una obligación que sí aplica): las tres hicieron fallar la prueba.

## Answer

El recorrido corre verde sobre PostgreSQL. Cerrarlo exigió dos cosas:

**1. Credenciales.** Se reinició la contraseña del superusuario `postgres` y la
del rol `prevencion`, y se escribió el `.env` local. El rol necesitó además
`CREATEDB` para que Django pudiera crear `test_prevencion`.

**2. Un defecto que solo PostgreSQL revela.** La primera ejecución real falló en
`bitacora/views.py`:

    ProgrammingError: el operador no existe: character varying = bigint

`EventoBitacora.identificador` es un `CharField` y todas las escrituras guardan
`str(evidencia.pk)`, pero la consulta del recorrido pasaba los pks como enteros
al `identificador__in`. SQLite, de tipado laxo, comparaba igual y la prueba
pasaba; PostgreSQL rechaza la comparación. Corregido convirtiendo los
identificadores a texto, igual que hacen las ramas hermanas de la misma
consulta.

Esto justifica en retrospectiva la condición `@skipUnless(postgresql)`: el
recorrido sobre SQLite no habría detectado nunca este defecto.

**Verificación final (2026-08-31):**

- `manage.py test aceptacion` sobre PostgreSQL: verde.
- Suite completa sobre PostgreSQL: 85 pruebas, OK, ninguna omitida.
- Suite completa sobre SQLite: 84 pruebas, OK, 1 omitida (este recorrido).
- `mypy` sobre los nueve paquetes y `manage.py`: sin hallazgos en 99 archivos.
- `manage.py migrate --check`: sin migraciones pendientes.

El procedimiento para repetir la demostración está en
`docs/recorrido-aceptacion-mvp.md`.
