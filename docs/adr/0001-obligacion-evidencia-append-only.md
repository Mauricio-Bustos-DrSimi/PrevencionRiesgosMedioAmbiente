# Obligación y Evidencia como entidades separadas, con registro append-only

El sistema debe sostener trazabilidad comprobable ante fiscalización (Ley 16.744, DS 594, DS 44 y normativa ambiental), lo que exige responder no solo "¿está cumplido hoy?" sino "¿qué se cumplió, quién lo cargó, cómo y cuándo?". Por eso separamos la **Obligación** (exigencia normativa permanente sobre un centro de costo, un trabajador o un externo) de la **Evidencia** (documento con vigencia que la prueba en un periodo dado), y derivamos el **estado de cumplimiento** en vez de almacenarlo.

Ningún registro se edita ni se borra: una evidencia nueva supersede a la anterior, la evidencia histórica se conserva aunque la obligación deje de aplicar, y cada cambio de aplicabilidad queda con autor, fecha y motivo.

## Consequences

- Una tabla única de "cumplimiento" editable habría sido mucho más simple, pero no permite probar el estado de cumplimiento en una fecha pasada — que es exactamente lo que se discute en una fiscalización o un juicio laboral.
- "Sin evidencia" y "Vencido" son estados distintos y no se colapsan: uno significa que nunca se hizo, el otro que se dejó caer.
- El volumen de filas crece de forma monótona; se asume como costo del modelo.
