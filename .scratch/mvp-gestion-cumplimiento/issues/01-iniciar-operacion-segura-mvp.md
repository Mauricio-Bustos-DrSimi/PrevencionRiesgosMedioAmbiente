# 01: Iniciar la operación segura del MVP

**What to build:** Una aplicación Django conectada a PostgreSQL donde un Prevencionista pueda iniciar sesión y acceder a una portada protegida, y un Sysadmin pueda administrar las cuentas y grupos mínimos del piloto. Esta primera capacidad debe establecer el seam de pruebas HTTP que usarán los tickets posteriores.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] La aplicación arranca contra PostgreSQL y responde mediante una interfaz server-rendered.
- [x] Un usuario sin sesión es dirigido al inicio de sesión al intentar acceder a la portada protegida.
- [x] Un Prevencionista autenticado puede abrir la portada del MVP.
- [x] Un Sysadmin puede crear una cuenta local y asignarla al grupo Prevencionista mediante el panel administrativo.
- [x] Un usuario autenticado sin los permisos necesarios no obtiene acceso a funciones protegidas.
- [x] Una prueba de integración mediante el cliente HTTP de Django demuestra el recorrido de autenticación y autorización observable.


## Answer

Implementado en el commit `e4baa41`.

Django sobre PostgreSQL con plantillas server-rendered, inicio de sesión con
cuentas locales y portada protegida. La migración crea el grupo `Prevencionista`;
un Sysadmin administra cuentas y grupos desde el panel administrativo. Queda
establecido el seam de pruebas HTTP mediante el cliente de Django que usan los
tickets posteriores.
