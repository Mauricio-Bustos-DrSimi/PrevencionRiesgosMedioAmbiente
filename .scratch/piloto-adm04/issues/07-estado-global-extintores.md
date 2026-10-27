# 07: Estado global de extintores

**Status:** blocked-by-business

## Objetivo

Representar la formación teórica online y la práctica presencial con simulador
como componentes distinguibles de una obligación y derivar un único estado
global verificable.

## Alcance

- Componentes obligatorios identificados en catálogo y evidencia.
- Carga, validación, vencimiento y renovación independiente por componente.
- Vigencia global hasta la primera fecha de vencimiento.
- Estado global y desglose visible de ambos componentes.

## Dependencias

- 06: Actualización de periodicidades y fuentes de ADM04.
- Decisión de Prevención sobre la precedencia entre Vencido y Sin evidencia.
- Periodicidad oficial de cada componente.

## Archivos afectados

- `obligaciones/models.py`
- `evidencias/models.py`
- `evidencias/forms.py`
- `evidencias/services.py`
- Vistas y plantillas de carga, validación, operación y vencimientos
- Migraciones de obligaciones y evidencias
- Pruebas de cálculo y recorridos HTTP

## Migraciones necesarias

Sí. Se requiere representar componentes de obligación y asociar cada evidencia
al componente que acredita, preservando las evidencias históricas.

## Riesgos de seguridad

- Marcar Vigente con un solo componente.
- Perder una evidencia todavía vigente al renovar la otra.
- Reclasificar documentos históricos sin una atribución comprobable.
- Ocultar el componente faltante en el estado agregado.

## Criterios de aceptación

- [ ] Cada evidencia identifica inequívocamente teoría online o práctica con simulador.
- [ ] La obligación solo queda Vigente cuando ambos componentes están validados y vigentes.
- [ ] Un componente pendiente produce Pendiente de validación según la regla aprobada.
- [ ] La precedencia de Vencido y Sin evidencia coincide con la decisión de Prevención.
- [ ] La vigencia global termina en el primer vencimiento.
- [ ] Renovar un componente conserva el otro y toda la historia.

## Motivo del bloqueo

Faltan la periodicidad oficial de ambos componentes y la regla exacta para
resolver el estado global cuando uno está Vencido y el otro Sin evidencia.
