# Documentación del dominio

## Antes de explorar o modificar el sistema

- Lee `CONTEXT.md`.
- Lee los ADR de `docs/adr/` relacionados con el área que vas a modificar.
- Si alguno de estos recursos no existe, continúa sin interrumpir el trabajo.

## Estructura

Este proyecto usa un único contexto de dominio:

- `CONTEXT.md`: vocabulario canónico y conceptos del dominio
- `docs/adr/`: decisiones arquitectónicas y de producto aplicables al sistema

## Vocabulario

Usa en issues, especificaciones, pruebas y código los términos definidos en `CONTEXT.md`. Respeta también los sinónimos marcados para evitar.

Si falta un concepto necesario, registra la brecha para tratarla mediante `domain-modeling`.

## Conflictos con decisiones

Si una propuesta contradice un ADR existente, señala el conflicto explícitamente y referencia el ADR afectado antes de continuar.
