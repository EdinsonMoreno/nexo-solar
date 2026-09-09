# Plan de Implementación: Davis WeatherLink Reader

## Visión General

Implementación bottom-up del módulo `DavisWeatherLinkReader` en Python/PyQt6, siguiendo los mismos patrones arquitectónicos que `ModbusClient`. Las tareas avanzan desde los tipos de datos y utilidades hacia el hilo de lectura principal, garantizando que no haya código huérfano.

## Tareas

- [ ] 1. Añadir excepciones Davis a `modbuspython/exceptions.py`
  - Añadir las clases `DavisConnectionError`, `DavisProtocolError` y `DavisTransportError` heredando de `SolarSenseException`, con sus docstrings y ejemplos
  - _Requisitos: 12.1, 12.2, 12.3, 10.3_

- [ ] 2. Crear el modelo de datos `WeatherData`
  - [ ] 2.1 Implementar `modbuspython/data_access/davis_weatherlink/weather_data.py`
    - Definir la dataclass `WeatherData` con todos los campos en unidades SI según la tabla del diseño
    - _Requisitos: 5.2, 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 3. Implementar `CRCValidator`
  - [ ] 3.1 Implementar `modbuspython/data_access/davis_weatherlink/crc_validator.py`
    - Implementar `_build_table()` con el polinomio CRC-16 CCITT 0x1021
    - Implementar `calculate_crc(data: bytes) -> int` con tabla de lookup de 256 entradas
    - Implementar `validate(packet: bytes) -> bool` comparando bytes 0–96 con CRC en bytes 97–98 Big Endian
    - _Requisitos: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 3.2 Escribir tests de unidad para `CRCValidator` en `tests/test_davis_weatherlink/test_crc_validator.py`
    - Verificar construcción correcta de tabla CRC con valores de referencia del manual Davis
    - Casos: CRC correcto devuelve True, byte modificado devuelve False
    - _Requisitos: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 3.3 Escribir test de propiedad P1 (CRC round-trip) en `tests/test_davis_weatherlink/test_crc_validator.py`
    - **Propiedad 1: Para todo buffer de 97 bytes, construir paquete con CRC correcto → `validate()` devuelve True**
    - `@given(st.binary(min_size=97, max_size=97))`
    - **Valida: Requisitos 4.1, 4.2, 4.3, 4.5**

  - [ ]* 3.4 Escribir test de propiedad P2 (rechazo de CRC modificado) en `tests/test_davis_weatherlink/test_crc_validator.py`
    - **Propiedad 2: Para todo paquete con CRC válido, modificar cualquier byte → `validate()` devuelve False**
    - `@given(st.binary(min_size=99, max_size=99))` con corrupción deliberada de un byte
    - **Valida: Requisito 4.4**

- [ ] 4. Implementar `PacketParser`
  - [ ] 4.1 Implementar `modbuspython/data_access/davis_weatherlink/packet_parser.py`
    - Implementar `parse(packet: bytes) -> WeatherData` con todos los offsets y factores de conversión de la tabla del diseño
    - Verificar firma LOO (bytes 1–3) y lanzar `DavisProtocolError` si no coincide
    - Implementar `format_weather_data(data: WeatherData) -> str` con etiquetas y unidades
    - Implementar `parse_weather_data(text: str) -> WeatherData` para round-trip
    - _Requisitos: 5.1, 5.2, 5.3, 5.4, 5.5, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 4.2 Escribir tests de unidad para `PacketParser` en `tests/test_davis_weatherlink/test_packet_parser.py`
    - Decodificación de LOOP_Packet de referencia con valores conocidos
    - Casos: firma LOO correcta, firma incorrecta (DavisProtocolError), conversiones de unidades
    - _Requisitos: 5.1, 5.2, 5.3_

  - [ ]* 4.3 Escribir test de propiedad P4 (parsing con conversiones correctas) en `tests/test_davis_weatherlink/test_packet_parser.py`
    - **Propiedad 4: Para todo paquete sintético con valores conocidos, `parse()` produce WeatherData con campos SI correctos**
    - `@given(...)` construyendo paquetes con valores raw en rangos del sensor
    - **Valida: Requisitos 5.1, 5.2, 9.1, 9.2, 9.3, 9.4**

  - [ ]* 4.4 Escribir test de propiedad P6 (round-trip WeatherData) en `tests/test_davis_weatherlink/test_packet_parser.py`
    - **Propiedad 6: Para toda WeatherData válida, `format_weather_data()` → `parse_weather_data()` produce estructura equivalente**
    - `@given(builds(WeatherData, ...))` con campos dentro de rangos válidos
    - **Valida: Requisitos 5.4, 5.5**

  - [ ]* 4.5 Escribir test de propiedad P8 (rechazo de firma LOO inválida) en `tests/test_davis_weatherlink/test_packet_parser.py`
    - **Propiedad 8: Para todo paquete de 99 bytes con bytes 1–3 ≠ [0x4C, 0x4F, 0x4F], `parse()` debe rechazarlo**
    - `@given(st.binary(min_size=99, max_size=99))` filtrando firma inválida
    - **Valida: Requisito 5.3**

- [ ] 5. Implementar conversiones de unidades
  - [ ] 5.1 Añadir funciones de conversión en `modbuspython/data_access/davis_weatherlink/packet_parser.py` o módulo auxiliar
    - `fahrenheit_to_celsius`, `mph_to_ms`, `inhg_to_hpa`, `inches_to_mm`
    - _Requisitos: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 5.2 Escribir tests de unidad de conversiones en `tests/test_davis_weatherlink/test_unit_conversion.py`
    - Casos concretos: 32°F = 0°C, 212°F = 100°C, 0 mph = 0 m/s, 29.921 inHg ≈ 1013.25 hPa
    - _Requisitos: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 5.3 Escribir test de propiedad P3 (round-trip temperatura) en `tests/test_davis_weatherlink/test_unit_conversion.py`
    - **Propiedad 3: Para todo °F en [−200, 300], °F → °C → °F produce valor original con tolerancia ±0.01°F**
    - `@given(st.floats(min_value=-200, max_value=300, allow_nan=False))`
    - **Valida: Requisitos 9.1, 9.6**

- [ ] 6. Checkpoint — Asegurar que todos los tests pasan hasta aquí
  - Asegurar que todos los tests pasan, preguntar al usuario si surge alguna duda.

- [ ] 7. Implementar la capa de transporte
  - [ ] 7.1 Implementar `modbuspython/data_access/davis_weatherlink/transport.py`
    - Definir `BaseTransport` (ABC) con métodos abstractos `connect`, `disconnect`, `send`, `receive`, `is_open`
    - Implementar `SerialTransport(BaseTransport)` con `pyserial`, parámetros 19200/8N1
    - Implementar `IPTransport(BaseTransport)` con `socket.SOCK_STREAM` y `settimeout()`
    - Lanzar `DavisTransportError` en todos los caminos de error
    - _Requisitos: 1.2, 1.3, 10.1, 10.2, 10.3, 10.4, 12.1, 12.2_

  - [ ]* 7.2 Escribir tests de unidad de transporte en `tests/test_davis_weatherlink/test_transport.py`
    - Verificar `connect`/`disconnect`/`is_open` con mocks de `serial.Serial` y `socket.socket`
    - Verificar que `DavisTransportError` se lanza ante fallos de apertura
    - _Requisitos: 1.2, 1.3, 10.1, 12.1_

  - [ ]* 7.3 Escribir test de propiedad P7 (transparencia del transporte) en `tests/test_davis_weatherlink/test_transport.py`
    - **Propiedad 7: Para todo payload Davis, `DavisWeatherLinkReader` emite el mismo WeatherData con SerialTransport o IPTransport**
    - Mock serial + mock IP con los mismos bytes → mismo WeatherData emitido
    - **Valida: Requisitos 10.2, 10.5**

- [ ] 8. Implementar `DavisWeatherLinkReader` (QThread principal)
  - [ ] 8.1 Implementar `modbuspython/data_access/davis_weatherlink/davis_reader.py`
    - Heredar de `QThread`, declarar señales `weather_data_updated`, `connection_changed`, `log`, `retry_exhausted`
    - Implementar `_build_transport()` con factory según `ConfigurationManager`
    - Implementar `_wake_up()`: enviar 0x0A, esperar CR+LF en 1200 ms
    - Implementar `_send_loop_command()`: enviar bytes `LOOP 1\r`, esperar ACK 0x06
    - Implementar `_read_packet()`: leer 99 bytes del transport
    - Implementar `_read_cycle()`: orchestrar wake-up → comando → lectura → CRC → parse → validación rangos → emit
    - Implementar `_validate_ranges(data: WeatherData) -> bool` con los rangos de requisito 11
    - Implementar `run()` con QTimer, `iniciar(intervalo_ms)`, `detener_lectura()`, `stop()`
    - Integrar `RetryStrategy` en `_wake_up`, `_send_loop_command`, `_read_packet`
    - _Requisitos: 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 8.5, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 12.4_

  - [ ]* 8.2 Escribir tests de unidad de `DavisWeatherLinkReader` en `tests/test_davis_weatherlink/test_weather_data.py`
    - Comportamiento de `stop()` en estado de error (sin transporte activo)
    - Configuración correcta con `transport: serial` y `transport: ip`
    - Verificar que un WeatherData con campo fuera de rango no emite `weather_data_updated`
    - _Requisitos: 6.6, 11.6, 12.4_

  - [ ]* 8.3 Escribir test de propiedad P5 (validación de rangos) en `tests/test_davis_weatherlink/test_weather_data.py`
    - **Propiedad 5: Para todo WeatherData con un campo supervisado fuera de rango, no se emite `weather_data_updated`**
    - `@given(builds(WeatherData, ...))` con un campo deliberadamente fuera de rango
    - **Valida: Requisitos 11.1, 11.2, 11.3, 11.4, 11.5, 11.6**

- [ ] 9. Crear el paquete `davis_weatherlink` y exponer la API pública
  - Implementar `modbuspython/data_access/davis_weatherlink/__init__.py`
  - Exportar `DavisWeatherLinkReader`, `WeatherData`, `BaseTransport`, `SerialTransport`, `IPTransport`
  - _Requisitos: 6.1, 6.2_

- [ ] 10. Extender `config.yaml` con la sección `davis_weatherlink`
  - Añadir la sección `davis_weatherlink` al final de `config.yaml` con todos los parámetros y valores por defecto del diseño
  - Verificar que `ConfigurationManager` valida `baud_rate == 19200` y `transport` en `{serial, ip}`
  - _Requisitos: 1.1, 13.1, 13.2, 13.3, 13.4_

- [ ] 11. Checkpoint final — Asegurar que todos los tests pasan
  - Asegurar que todos los tests pasan, preguntar al usuario si surge alguna duda.

- [ ]* 12. Integración opcional en `MainWindow`
  - [ ]* 12.1 Instanciar `DavisWeatherLinkReader` en `MainWindow.__init__` igual que `ModbusClient`
    - Conectar señales `weather_data_updated`, `connection_changed`, `log`, `retry_exhausted` a slots de la UI
    - Arrancar con `start()` y detener con `stop()` en el ciclo de vida de la ventana principal
    - _Requisitos: 6.2, 6.3, 6.4_

## Notas

- Las tareas marcadas con `*` son opcionales y se pueden omitir para un MVP más rápido
- Cada tarea referencia los sub-requisitos específicos para trazabilidad
- Los checkpoints garantizan validación incremental
- Los tests de propiedad usan Hypothesis (`@settings(max_examples=100)`)
- Cada test de propiedad incluye el comentario `# Feature: davis-weatherlink-reader, Property N: <texto>`
- La tarea 12 es completamente opcional; la integración en MainWindow puede hacerse en un sprint posterior
