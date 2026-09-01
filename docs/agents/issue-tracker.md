# Issue tracker: Markdown local

Las especificaciones e issues de este proyecto se almacenan como archivos Markdown bajo `.scratch/`.

## Convenciones

- Una carpeta por iniciativa: `.scratch/<slug-de-iniciativa>/`
- La especificación vive en `.scratch/<slug-de-iniciativa>/spec.md`
- Los issues de implementación viven en `.scratch/<slug-de-iniciativa>/issues/<NN>-<slug>.md`
- Los issues se numeran desde `01`
- El estado de triage se registra mediante una línea `Status:` cerca del comienzo
- Los comentarios se agregan al final bajo un encabezado `## Comments`

## Publicar en el issue tracker

Cuando una skill solicite publicar una especificación o issue, crea el archivo correspondiente bajo `.scratch/<slug-de-iniciativa>/`.

Las especificaciones listas para implementación deben incluir:

`Status: ready-for-agent`

## Obtener un ticket

Lee el archivo indicado por el usuario. La referencia puede ser una ruta o el número del issue dentro de la iniciativa.

## Operaciones de wayfinding

- Mapa: `.scratch/<iniciativa>/map.md`
- Ticket hijo: `.scratch/<iniciativa>/issues/<NN>-<slug>.md`
- Tipo: una línea `Type:` con `research`, `prototype`, `grilling` o `task`
- Estado operativo: una línea `Status:` con `claimed` o `resolved`
- Bloqueos: una línea `Blocked by: NN, NN`
- Frontera: primer ticket abierto, no bloqueado y no asignado, ordenado por número
- Reclamar: cambia `Status:` a `claimed` antes de comenzar el trabajo
- Resolver: agrega la respuesta bajo `## Answer`, cambia `Status:` a `resolved` y registra el resultado en `map.md`
