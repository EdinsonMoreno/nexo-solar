# Davis WeatherLink

Esta carpeta documenta la primera base backend de la integracion Davis WeatherLink para Nexo Solar.

## Estado actual

- `modbuspython/data_access/davis_weatherlink/weather_data.py` define el modelo `WeatherData` con unidades de ingenieria listas para UI o persistencia.
- `unit_conversion.py` centraliza conversiones para evitar formulas repetidas.
- `crc_validator.py` calcula y valida el CRC-CCITT del paquete LOOP segun la especificacion local del cambio.
- `packet_parser.py` decodifica paquetes LOOP de 99 bytes en `WeatherData`.
- La interfaz web ya tiene una pestana base "Estacion Davis", pero todavia no esta conectada a un lector `QThread`.

## Reglas de mantenimiento

- Mantener backend y frontend separados: el parser no debe importar PyQt ni tocar DOM.
- No leer hardware desde la UI: la futura lectura serial/IP debe vivir en `data_access`.
- Mantener funciones pequenas y nombres explicitos.
- Probar cada regla de conversion y parsing con paquetes sinteticos antes de conectar la estacion real.

## Pendiente

- Verificar con documentacion primaria de Davis cualquier offset o factor que no este confirmado por hardware.
- Implementar transportes serial/IP y `DavisWeatherLinkReader`.
- Conectar `weather_data_updated` al `WebBridge` y actualizar la pestana "Estacion Davis" con datos reales.
