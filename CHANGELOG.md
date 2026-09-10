# Historial de cambios

Este archivo resume cambios documentados del repositorio. No implica que una funcionalidad aparezca en una versión publicada.

## No lanzado

- Actualización de la documentación para reflejar `run.py`, la UI PyQt6/WebDashboard, la configuración real y el workflow vigente.
- Aclaración de que Davis WeatherLink solo tiene especificaciones en `.kiro` y no está implementado.

## 1.2.0 — 2026-05-06

- Se incorporaron validación de configuración, cifrado de credenciales, pool SQLite, repositorios, migraciones y filtrado de datos sensibles en logs.
- Se separaron componentes de Modbus, base de datos, configuración y UI.
- Se corrigieron imports circulares, concurrencia y validación de entradas.

## 1.1.0 — 2025-12-15

- Se añadieron cálculos solares, control manual, estado seguro, reintentos, logging y comprobaciones de calidad.

## 1.0.0 — 2025-09-20

- Se incorporaron GUI PyQt6, Modbus TCP, irradiancia, SQLite, mapa Leaflet y seguimiento solar.

Las fechas y funcionalidades anteriores reflejan el historial documentado; consulte siempre el código para el estado actual.
