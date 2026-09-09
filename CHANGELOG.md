# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Versionado Semántico](https://semver.org/spec/v2.0.0.html).

## [No Lanzado]

### Agregado
- Documentación completa de arquitectura, configuración, solución de problemas y contribución
- Referencia de API interna para módulos principales
- Guía de despliegue para entornos de producción
- Guía detallada de pruebas

### Cambiado
- Refactorización de módulos grandes (>500 líneas) en componentes modulares
- Migración a patrón Repository para acceso a base de datos
- Mejora en estructura de configuración con validación JSON Schema

## [1.2.0] - 2026-05-06

### Agregado
- Sistema de migraciones de base de datos (`MigrationManager`)
- Validación de configuración con JSON Schema
- Cifrado de credenciales con Fernet
- Pool de conexiones SQLite thread-safe
- Patrón Repository para acceso a datos (`IrradianceRepository`, `SchemaVersionRepository`)
- Filtros de datos sensibles en logs (`SensitiveDataFilter`)
- 30 nuevos tests para widgets de UI refactorizados

### Cambiado
- `ModbusClient` dividido en `ModbusConnection`, `ModbusReader`, `ModbusWriter`
- `DatabaseManager` reducido de 811 a 167 líneas
- `ConfigManager` dividido en componentes modulares
- `LocationTab` dividido en sub-componentes especializados
- Todos los archivos fuente ahora <500 líneas

### Corregido
- Imports circulares entre módulos
- Fugas de memoria en conexiones de base de datos
- Validación de entrada en controles de usuario

### Seguridad
- Eliminación de credenciales hardcodeadas
- Enmascaramiento de datos sensibles en logs
- Validación de identificadores SQL para prevenir inyección

## [1.1.0] - 2025-12-15

### Agregado
- Calculadora de posición solar (HRA, declinación, altitud, azimut)
- Control manual de ángulos con validación
- Estado seguro (safe-state) para operaciones Modbus
- Estrategia de reintentos con backoff exponencial
- Servicio de logging centralizado con rotación
- 18 hooks de pre-commit para calidad de código
- Pipeline CI/CD con GitHub Actions

### Cambiado
- Mejora en manejo de errores con jerarquía de excepciones personalizada
- Refactorización de backend para separación de responsabilidades
- Actualización de imports a formato relativo

### Corregido
- Problemas de concurrencia en lectura Modbus
- Actualización de UI durante operaciones bloqueantes

## [1.0.0] - 2025-09-20

### Agregado
- Interfaz gráfica con PyQt6 (Monitor, Ubicación, Diagnóstico)
- Comunicación Modbus TCP con ESP8266
- Medición de irradiación en tiempo real
- Visualización de datos con gauges circulares
- Mapa interactivo con Leaflet.js
- Rastreo solar automático
- Persistencia de datos con SQLite
- Configuración externalizada (YAML/JSON)
- Sistema de traducción (español/inglés)

---

## Convenciones

- **Agregado**: Nuevas funcionalidades
- **Cambiado**: Cambios en funcionalidades existentes
- **Corregido**: Corrección de errores
- **Seguridad**: Mejoras relacionadas con seguridad
