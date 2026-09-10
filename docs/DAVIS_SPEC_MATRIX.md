# Davis WeatherLink - Matriz SPEC a implementacion y prueba

Fuentes primarias usadas en esta fase: archivos locales
`.kiro/specs/davis-weatherlink-reader/requirements.md`,
`.kiro/specs/davis-weatherlink-reader/design.md`,
`.kiro/specs/davis-weatherlink-reader/tasks.md` y documentacion oficial Davis
disponible publicamente.

No se uso hardware fisico. Los puntos que dependen de la configuracion real del
equipo, especialmente colector de lluvia, puerto serial y firmware, quedan
pendientes de validacion en laboratorio antes de pasar a QA funcional.

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
| 2 | Wake-up LF y respuesta LF+CR con maximo 3 intentos | `DavisWeatherLinkReader._wake_up()` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6 | Alineado con referencia Davis; prueba Qt pendiente en entorno completo |
| 3 | Enviar `LOOP 1\n`, esperar ACK y leer 99 bytes | `DavisWeatherLinkReader._send_loop_command()` y `_read_packet()` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6 | Alineado con referencia Davis; prueba Qt pendiente en entorno completo |
| 4 | Calcular y validar CRC-16 CCITT bytes 0-96 contra bytes 97-98 BE | `CRCValidator` | `test_davis_weatherlink_crc.py` incluye ejemplo Davis `C6 CE A2 03 -> E2 B4` | Algoritmo cubierto contra referencia oficial; validar LOOP real manana |
| 5 | Decodificar LOOP a `WeatherData`, validar firma `LOO` en bytes 0-2 y round-trip texto | `PacketParser`, `WeatherData` | `test_davis_weatherlink_parser.py` | Offsets principales coinciden con referencia Davis; factores de lluvia dependen del colector y se validan con equipo |
| 6 | QThread, señales, QTimer, stop limpio | `DavisWeatherLinkReader` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6 | Implementado; prueba Qt pendiente en entorno completo |
| 7 | RetryStrategy con backoff 2.0 y agotamiento de reintentos | `DavisWeatherLinkReader.retry_strategy` y `_execute_with_retry()` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6; `RetryStrategy` ya tiene tests propios | Implementado; prueba Qt pendiente en entorno completo |
| 8 | Logging centralizado para conexion, polling, CRC, lecturas y fallos | `LoggingService` usado en `DavisWeatherLinkReader`, `CRCValidator`, transportes | Validado por inspeccion y pruebas existentes de logging; sin hardware para logs reales | Parcial por falta de prueba funcional con dispositivo |
| 9 | Convertir a SI antes de emitir | `unit_conversion.py`, `PacketParser.parse()` | `test_davis_weatherlink_conversions.py`, `test_davis_weatherlink_parser.py` | Completo local |
| 10 | Transporte IP TCP transparente | `IPTransport` | `test_davis_weatherlink_transport.py` | Completo local; pendiente prueba con adaptador real |
| 11 | Validar rangos antes de emitir | `DavisWeatherLinkReader._validate_ranges()` | Cubierto por test Qt de lector, omitido en este entorno por falta de PyQt6 | Implementado; prueba Qt pendiente en entorno completo |
| 12 | Manejo de errores de puerto serie y cierre en error | `SerialTransport`, `DavisWeatherLinkReader.stop()` | `test_davis_weatherlink_transport.py`; cierre cubierto por test Qt omitido por falta de PyQt6 | Parcial por falta de PyQt6 y puerto real |
| 13 | Integracion con `ConfigurationManager` y `config.yaml` | Defaults, schema, propiedad `davis_weatherlink_config` y acceso por `config.get()` | Validacion JSON y tests de factory con config simulada | Completo local |
| 14 | Persistir lecturas meteorologicas para analisis historico | `DavisWeatherRepository` crea `davis_weather_readings` y `DavisWeatherLinkReader` guarda cada lectura valida desde backend | `test_davis_weather_repository.py` cubre creacion, insercion y consulta reciente | Completo local |
| 15 | Mostrar estado Davis separado de Modbus/ESP8266 | `WebBridge.getDavisStatus()`, `davisStatusUpdated` y diagnostico Davis USB en `Mockup` | `node --check`, `git diff --check` y prueba funcional pendiente en UI real | Implementado; validar visualmente en laboratorio |
| 16 | Graficar variables Davis con rango y zoom | Pestaña `Graficas` con rangos 1 h, 6 h, 24 h, 7 dias, 30 dias, Todo y escala +/- | `node --check`; usa historico SQLite cuando existe | Implementado; validar con datos acumulados |

## Brechas antes de QA

- Instalar dependencias de entorno (`PyQt6` y `pyserial`) y ejecutar los tests
  Qt del lector.
- Validar con equipo real que el orden de bytes recibido por el adaptador USB/IP
  coincide con la referencia Davis y que la configuracion del colector de lluvia
  corresponde a 0.01 in o 0.2 mm por click.
- Hacer una prueba funcional con serial VCP y otra con transporte IP si el SENA
  usara ese modo.
- Probar visualmente el diagnostico Davis USB y las graficas con el equipo
  conectado durante varias horas para confirmar rangos, zoom y persistencia.
