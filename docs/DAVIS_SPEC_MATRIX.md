# Davis WeatherLink - Matriz SPEC a implementacion y prueba

Fuente primaria usada en esta fase: archivos locales
`.kiro/specs/davis-weatherlink-reader/requirements.md`,
`.kiro/specs/davis-weatherlink-reader/design.md` y
`.kiro/specs/davis-weatherlink-reader/tasks.md`.

No se uso documentacion externa de Davis ni hardware fisico. Los detalles de
offsets, factores de lluvia y CRC quedan implementados segun el SPEC local y
pendientes de validacion contra manual oficial o estacion real antes de pasar a
QA funcional.

## Resumen de variables expuestas

| Campo tecnico | Etiqueta UI | Unidad | Origen segun SPEC local | Estado |
|---|---|---:|---|---|
| `solar_radiation_wm2` | Radiacion solar | W/m2 | Bytes 44-45, uint16 LE | Implementado y visible |
| `temp_out_c` | Temperatura exterior | degC | Bytes 12-13, int16 LE, F/10 a C | Implementado y visible |
| `temp_in_c` | Temperatura interior | degC | Bytes 9-10, int16 LE, F/10 a C | Implementado y visible |
| `humidity_out` | Humedad exterior | % RH | Byte 33 | Implementado y visible |
| `humidity_in` | Humedad interior | % RH | Byte 11 | Implementado y visible |
| `pressure_hpa` | Presion barometrica | hPa | Bytes 7-8, inHg/1000 a hPa | Implementado y visible |
| `wind_speed_ms` | Velocidad del viento | m/s | Byte 14, mph a m/s | Implementado y visible |
| `wind_speed_avg_ms` | Viento promedio 10 min | m/s | Byte 15, mph a m/s | Implementado y visible |
| `wind_dir_deg` | Direccion del viento | deg | Bytes 16-17, uint16 LE | Implementado y visible |
| `rain_rate_mm` | Tasa de lluvia | mm | Bytes 41-42, clicks a mm | Implementado y visible; factor pendiente de confirmar |
| `rain_storm_mm` | Lluvia de tormenta | mm | Bytes 46-47, pulgadas/100 a mm | Implementado y visible |
| `rain_day_mm` | Lluvia dia | mm | Bytes 50-51, pulgadas/100 a mm | Implementado y visible |
| `rain_month_mm` | Lluvia mes | mm | Bytes 52-53, pulgadas/100 a mm | Implementado y visible |
| `rain_year_mm` | Lluvia ano | mm | Bytes 54-55, pulgadas/100 a mm | Implementado y visible |
| `uv_index` | Indice UV | indice | Byte 43, uint8/10 | Implementado y visible |

## Requisitos

| Req | Criterio SPEC | Implementacion | Prueba | Estado |
|---|---|---|---|---|
| 1 | Configurar transporte `serial` o `ip`, parametros Davis y `poll_interval_ms` | `config_defaults.py`, `default_config.yaml`, `config_schema.json`, `ConfigurationManager.davis_weatherlink_config`, `DavisWeatherLinkReader._build_transport()` | `test_davis_weatherlink_reader.py` cubre factory IP e invalid transport; validacion JSON ejecutada con `json.tool` | Completo local |
| 2 | Wake-up LF y respuesta CR+LF con maximo 3 intentos | `DavisWeatherLinkReader._wake_up()` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6 | Implementado; prueba Qt pendiente en entorno completo |
| 3 | Enviar `LOOP 1\r`, esperar ACK y leer 99 bytes | `DavisWeatherLinkReader._send_loop_command()` y `_read_packet()` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6 | Implementado; prueba Qt pendiente en entorno completo |
| 4 | Calcular y validar CRC-16 CCITT bytes 0-96 contra bytes 97-98 BE | `CRCValidator` | `test_davis_weatherlink_crc.py` | Completo local; algoritmo pendiente contra fuente primaria Davis |
| 5 | Decodificar LOOP a `WeatherData`, validar firma y round-trip texto | `PacketParser`, `WeatherData` | `test_davis_weatherlink_parser.py` | Completo local; offsets pendientes contra fuente primaria Davis |
| 6 | QThread, señales, QTimer, stop limpio | `DavisWeatherLinkReader` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6 | Implementado; prueba Qt pendiente en entorno completo |
| 7 | RetryStrategy con backoff 2.0 y agotamiento de reintentos | `DavisWeatherLinkReader.retry_strategy` y `_execute_with_retry()` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6; `RetryStrategy` ya tiene tests propios | Implementado; prueba Qt pendiente en entorno completo |
| 8 | Logging centralizado para conexion, polling, CRC, lecturas y fallos | `LoggingService` usado en `DavisWeatherLinkReader`, `CRCValidator`, transportes | Validado por inspeccion y pruebas existentes de logging; sin hardware para logs reales | Parcial por falta de prueba funcional con dispositivo |
| 9 | Convertir a SI antes de emitir | `unit_conversion.py`, `PacketParser.parse()` | `test_davis_weatherlink_conversions.py`, `test_davis_weatherlink_parser.py` | Completo local |
| 10 | Transporte IP TCP transparente | `IPTransport` | `test_davis_weatherlink_transport.py` | Completo local; pendiente prueba con adaptador real |
| 11 | Validar rangos antes de emitir | `DavisWeatherLinkReader._validate_ranges()` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6 | Implementado; prueba Qt pendiente en entorno completo |
| 12 | Manejo de errores de puerto serie y cierre en error | `SerialTransport`, `DavisWeatherLinkReader.stop()` | `test_davis_weatherlink_transport.py`; cierre cubierto por test Qt omitido por falta de PyQt6 | Parcial por falta de PyQt6 y puerto real |
| 13 | Integracion con `ConfigurationManager` y `config.yaml` | Defaults, schema, propiedad `davis_weatherlink_config` y acceso por `config.get()` | Validacion JSON y tests de factory con config simulada | Completo local |

## Brechas antes de QA

- Instalar dependencias de entorno (`PyQt6` y `pyserial`) y ejecutar los tests
  Qt del lector.
- Validar offsets, CRC y factores de lluvia contra manual oficial de Davis
  Instruments o contra paquetes capturados de una Davis Vantage Pro2 real.
- Hacer una prueba funcional con serial VCP y otra con transporte IP si el SENA
  usara ese modo.
- Revisar si la lectura Davis debe persistirse en SQLite junto a irradiancia o
  en una tabla meteorologica nueva; el SPEC local no define esquema historico.
