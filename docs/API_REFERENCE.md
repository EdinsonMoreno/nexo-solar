# Referencia interna

Esta es una referencia breve de los módulos existentes. Las firmas definitivas son las del código fuente.

## Acceso a datos

- `modbuspython.data_access.modbus_connection.ModbusConnection`: conecta, desconecta y comprueba el cliente Modbus.
- `modbuspython.data_access.modbus_reader.ModbusReader`: lee registros y convierte la irradiancia.
- `modbuspython.data_access.modbus_writer.ModbusWriter`: escribe consignas y administra el estado seguro.
- `modbuspython.data_access.modbus_client.ModbusClient`: `QThread` que coordina I/O y emite `radiacion_actualizada`, `conexion_cambiada`, `log` y `retry_exhausted`.
- `connection_pool.ConnectionPool` y `database_manager.DatabaseManager`: conexiones SQLite.
- `retry_strategy.RetryStrategy`: reintentos con backoff.
- `logging_service.LoggingService`: logging centralizado y filtro de datos sensibles.

## Backend

- `angle_state_manager.AngleStateManager`: modo y ángulos del seguidor.
- `solar_calcs`: cálculos de hora angular, declinación, altitud y azimut.
- `validation_service.ValidationService`: validación de IP, puertos, ángulos, coordenadas y cadenas.

## Configuración y UI

`config.config_manager.ConfigurationManager` carga YAML/JSON, valores anidados y validación; `credential_encryptor` implementa Fernet. La UI contiene `MonitorTab`, configuración de ubicación, seguimiento solar, control manual, diagnóstico, mapa y `web_dashboard.WebDashboard`.

Ejemplo de importación:

```python
from modbuspython.config import ConfigurationManager
from modbuspython.data_access.modbus_client import ModbusClient
```

No hay API HTTP pública. Davis WeatherLink no está implementado; su documentación está únicamente en `.kiro`.
