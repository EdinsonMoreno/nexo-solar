# Arquitectura

El punto de entrada real es `run.py`, que invoca `modbuspython.main_app.main`. La aplicación es una GUI PyQt6; no existe un servidor web separado.

```text
modbuspython/ui/          presentación (widgets, WebDashboard, Leaflet)
        ↓
modbuspython/backend/     cálculos solares, estado y validación
        ↓
modbuspython/data_access/ Modbus TCP, SQLite, logging y reintentos
        ↑
modbuspython/config/      carga, valores predeterminados y validación
```

`ModbusClient` (QThread) conecta al dispositivo, lee irradiancia y emite señales Qt. La UI actualiza sus widgets y el acceso a datos persiste mediciones en SQLite. `Mockup/` es una maqueta HTML/CSS/JavaScript; `WebDashboard` es una vista embebida, no un servicio desplegable.

Los módulos antiguos de `backend` se conservan por compatibilidad. Davis WeatherLink no está implementado: solo está especificado en `.kiro/specs/davis-weatherlink-reader/`.
