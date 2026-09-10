# Documentación de prácticas del sistema

Este documento describe actividades que pueden realizarse con el código actual.

## 1. Medición de irradiancia

1. Configure el dispositivo Modbus TCP en `config.yaml`.
2. Ejecute `python run.py`.
3. En el monitor, observe la lectura en condiciones despejadas, sombreadas y cubiertas.
4. Registre hora, condición y valor mostrado.

## 2. Control manual

Configure coordenadas y use los controles de ángulo dentro de los límites de `angles`. Verifique el efecto solo cuando el dispositivo conectado sea seguro para recibir consignas.

## 3. Seguimiento solar

Introduzca una ubicación válida y revise los ángulos calculados por `solar_calcs`. La precisión depende de la hora, coordenadas y dispositivo.

## 4. Historial SQLite

Las mediciones se almacenan en la ruta configurada. Detenga la aplicación antes de copiar la base y use herramientas SQLite para consultar el esquema real.

## Nota de alcance

La UI actual es PyQt6 y usa widgets, `Mockup/` y `WebDashboard`; las referencias históricas a LabVIEW, Arduino o tablas no presentes no describen esta aplicación. Davis WeatherLink no está implementado: solo existe la especificación en `.kiro/specs/davis-weatherlink-reader/`.
