# Documento de Requisitos

## Introducción

Esta feature integra la lectura directa de una estación meteorológica **Davis Vantage Pro2** dentro del software **Nexo Solar** (Python/PyQt6). La estación se conecta mediante un WeatherLink Data Logger USB en modo VCP (Virtual COM Port) usando el protocolo serie nativo de Davis Instruments. Adicionalmente, se contempla una vía alternativa de conectividad mediante red IP (WeatherLink IP o adaptador compatible), coherente con la arquitectura TCP/IP ya presente en Nexo Solar.

El módulo resultante (`DavisWeatherLinkReader`) debe seguir los mismos patrones arquitectónicos que el `ModbusClient` existente: hilo `QThread` para I/O no bloqueante, señales Qt para comunicación con la UI, `LoggingService` para logging centralizado, `ConfigurationManager` para configuración, y `RetryStrategy` para reintentos con backoff exponencial.

---

## Glosario

- **Davis_Reader**: El componente de software responsable de comunicarse con la estación meteorológica Davis Vantage Pro2.
- **LOOP_Packet**: Paquete binario de 99 bytes devuelto por la consola Davis en respuesta al comando LOOP, que contiene todas las variables meteorológicas.
- **CRC_Validator**: Componente encargado de calcular y verificar el CRC-16 CCITT sobre los bytes del LOOP_Packet.
- **Packet_Parser**: Componente encargado de decodificar los campos del LOOP_Packet en una estructura de datos meteorológicos legible.
- **Serial_Transport**: Capa de transporte que gestiona la comunicación sobre el puerto serie VCP (Virtual COM Port).
- **IP_Transport**: Capa de transporte alternativa que gestiona la comunicación sobre TCP/IP (WeatherLink IP o adaptador de red compatible).
- **Transport**: Término genérico que engloba tanto Serial_Transport como IP_Transport.
- **Wake_Up_Sequence**: Protocolo de activación de la consola Davis que consiste en enviar LF (0x0A) y esperar la respuesta LF+CR (0x0A 0x0D), según la referencia de comunicaciones Davis.
- **WeatherData**: Estructura de datos que contiene todas las variables meteorológicas decodificadas de un LOOP_Packet.
- **ConfigurationManager**: Singleton existente en Nexo Solar que gestiona la configuración mediante config.yaml.
- **LoggingService**: Singleton existente en Nexo Solar para logging centralizado con rotación de ficheros.
- **RetryStrategy**: Clase existente en Nexo Solar que implementa reintentos con backoff exponencial.
- **VCP**: Virtual COM Port — modo de operación del WeatherLink USB que lo presenta al sistema operativo como un puerto serie.

---

## Requisitos

---

### Requisito 1: Configuración del transporte de comunicación

**User Story:** Como administrador del sistema, quiero configurar el tipo de conexión con la estación Davis (serie o red), para poder adaptar la integración a la infraestructura disponible en cada instalación.

#### Criterios de Aceptación

1. THE `ConfigurationManager` SHALL soportar una sección `davis_weatherlink` en `config.yaml` que incluya los parámetros: `transport` (valores: `serial` o `ip`), `serial_port`, `baud_rate`, `ip_host`, `ip_port`, `poll_interval_ms`, `retry_attempts`, `retry_backoff` y `timeout`.
2. WHEN el parámetro `transport` tiene el valor `serial`, THE `Davis_Reader` SHALL inicializar el `Serial_Transport` con los parámetros UART: 19200 bps, 8 bits de datos, sin paridad, 1 bit de stop, sin control de flujo.
3. WHEN el parámetro `transport` tiene el valor `ip`, THE `Davis_Reader` SHALL inicializar el `IP_Transport` con el `ip_host` y `ip_port` configurados, estableciendo una conexión TCP hacia la dirección especificada.
4. IF el parámetro `transport` contiene un valor distinto de `serial` o `ip`, THEN THE `ConfigurationManager` SHALL registrar un error de configuración mediante `LoggingService` y THE `Davis_Reader` SHALL no inicializarse.
5. THE `Davis_Reader` SHALL leer el valor de `poll_interval_ms` desde `ConfigurationManager` para determinar el intervalo entre lecturas periódicas, con un valor por defecto de 5000 ms si el parámetro no está presente.

---

### Requisito 2: Protocolo de activación (Wake-Up)

**User Story:** Como desarrollador, quiero que el sistema active correctamente la consola Davis antes de enviar comandos, para garantizar que la estación esté lista para responder.

#### Criterios de Aceptación

1. WHEN el `Davis_Reader` inicia la comunicación con la consola, THE `Davis_Reader` SHALL enviar el byte LF (0x0A) al Transport activo para iniciar la Wake_Up_Sequence.
2. WHEN se envía el byte LF (0x0A), THE `Davis_Reader` SHALL esperar una respuesta de exactamente los bytes LF+CR (0x0A 0x0D) en un plazo máximo de 1200 ms.
3. IF la respuesta LF+CR no se recibe en 1200 ms, THEN THE `Davis_Reader` SHALL reintentar la Wake_Up_Sequence hasta un máximo de 3 intentos antes de declarar el transporte no disponible.
4. IF la consola no responde después de 3 intentos de Wake_Up_Sequence, THEN THE `Davis_Reader` SHALL emitir la señal `connection_lost` con un mensaje descriptivo del fallo y registrar el evento en `LoggingService`.
5. WHEN la Wake_Up_Sequence se completa con éxito, THE `Davis_Reader` SHALL registrar el evento en `LoggingService` con nivel DEBUG y proceder al envío del comando LOOP.

---

### Requisito 3: Solicitud y recepción del paquete LOOP

**User Story:** Como desarrollador, quiero que el sistema solicite y reciba correctamente el paquete LOOP de la consola Davis, para obtener las lecturas meteorológicas actuales.

#### Criterios de Aceptación

1. WHEN la Wake_Up_Sequence se ha completado con éxito, THE `Davis_Reader` SHALL enviar al Transport la secuencia de bytes `[0x4C, 0x4F, 0x4F, 0x50, 0x20, 0x31, 0x0A]` (correspondiente al comando `LOOP 1` + LF).
2. WHEN se envía el comando LOOP, THE `Davis_Reader` SHALL esperar la recepción del byte ACK (0x06) como confirmación de la consola en un plazo máximo definido por el parámetro `timeout`.
3. AFTER recibir el ACK, THE `Davis_Reader` SHALL leer exactamente 99 bytes del Transport como el LOOP_Packet.
4. IF el byte ACK no se recibe en el plazo de `timeout`, THEN THE `Davis_Reader` SHALL registrar el fallo en `LoggingService` con nivel WARNING y delegar el reintento a `RetryStrategy`.
5. IF se reciben menos de 99 bytes o se produce un error de lectura, THEN THE `Davis_Reader` SHALL descartar los datos recibidos, registrar el evento en `LoggingService` y delegar el reintento a `RetryStrategy`.

---

### Requisito 4: Validación CRC-16 del paquete LOOP

**User Story:** Como desarrollador, quiero que todos los paquetes LOOP sean validados mediante CRC-16 antes de ser procesados, para garantizar la integridad de los datos meteorológicos.

#### Criterios de Aceptación

1. WHEN se recibe un LOOP_Packet de 99 bytes, THE `CRC_Validator` SHALL calcular el CRC-16 CCITT (polinomio 0x1021) sobre los bytes 0 a 96 inclusive del paquete.
2. WHEN el CRC se ha calculado, THE `CRC_Validator` SHALL compararlo con el valor de 16 bits almacenado en los bytes 97 y 98 del paquete en formato Big Endian.
3. WHEN el CRC calculado coincide con el CRC del paquete, THE `CRC_Validator` SHALL devolver el paquete como válido para su decodificación por el `Packet_Parser`.
4. IF el CRC calculado no coincide con el CRC del paquete, THEN THE `CRC_Validator` SHALL descartar el paquete, registrar el evento en `LoggingService` con nivel WARNING, y THE `Davis_Reader` SHALL esperar 500 ms antes de reenviar el comando LOOP.
5. FOR ALL LOOP_Packets válidos, el CRC calculado por `CRC_Validator` sobre los bytes 0–96 SHALL ser siempre idéntico al extraído de los bytes 97–98 en Big Endian (propiedad de corrección del algoritmo CRC-16 CCITT).

---

### Requisito 5: Decodificación (parsing) del paquete LOOP

**User Story:** Como desarrollador, quiero que el sistema decodifique correctamente todos los campos del paquete binario LOOP en unidades de ingeniería comprensibles, para que los datos meteorológicos sean utilizables por el resto de la aplicación.

#### Criterios de Aceptación

1. WHEN un LOOP_Packet supera la validación CRC, THE `Packet_Parser` SHALL decodificar los campos del paquete según la siguiente tabla de offsets (índice base 0):
   - Bytes 0–2: firma (`LOO`), verificar que los valores sean `0x4C`, `0x4F`, `0x4F`
   - Bytes 7–8: presión barométrica (uint16 Little Endian, dividir entre 1000 → inHg)
   - Bytes 9–10: temperatura interior (int16 Little Endian, dividir entre 10 → °F)
   - Byte 11: humedad interior (uint8 → % RH)
   - Bytes 12–13: temperatura exterior (int16 Little Endian, dividir entre 10 → °F)
   - Byte 14: velocidad de viento actual (uint8 → mph)
   - Byte 15: velocidad de viento promedio 10 min (uint8 → mph)
   - Bytes 16–17: dirección del viento (uint16 Little Endian → grados 0–360)
   - Byte 33: humedad exterior (uint8 → % RH)
   - Bytes 41–42: tasa de lluvia (uint16 Little Endian → clicks)
   - Byte 43: índice UV (uint8, dividir entre 10 → índice UV)
   - Bytes 44–45: radiación solar (uint16 Little Endian → W/m²)
   - Bytes 46–47: lluvia de tormenta (uint16 Little Endian, dividir entre 100 → pulgadas)
   - Bytes 50–51: lluvia del día (uint16 Little Endian, dividir entre 100 → pulgadas)
   - Bytes 52–53: lluvia del mes (uint16 Little Endian, dividir entre 100 → pulgadas)
   - Bytes 54–55: lluvia del año (uint16 Little Endian, dividir entre 100 → pulgadas)
2. WHEN el `Packet_Parser` decodifica un LOOP_Packet, THE `Packet_Parser` SHALL producir una estructura `WeatherData` con todos los campos anteriores con sus unidades y factores de conversión aplicados.
3. IF los bytes 0–2 del LOOP_Packet no contienen los valores `0x4C`, `0x4F`, `0x4F` (firma `LOO`), THEN THE `Packet_Parser` SHALL descartar el paquete y registrar el evento en `LoggingService` con nivel WARNING.
4. THE `Packet_Parser` SHALL exponer un método `format_weather_data` que convierta una estructura `WeatherData` de vuelta a una representación de texto estructurada con etiquetas y unidades legibles por humanos.
5. FOR ALL estructuras `WeatherData` válidas, aplicar `format_weather_data` seguido de `parse_weather_data` SHALL producir una estructura `WeatherData` equivalente a la original (propiedad de round-trip).

---

### Requisito 6: Hilo de lectura no bloqueante (QThread)

**User Story:** Como desarrollador, quiero que la lectura de la estación Davis se ejecute en un hilo separado, para que la interfaz de usuario de Nexo Solar no se bloquee durante las operaciones de I/O.

#### Criterios de Aceptación

1. THE `Davis_Reader` SHALL heredar de `QThread` e implementar el método `run()` para ejecutar todas las operaciones de I/O (Wake_Up_Sequence, comando LOOP, lectura, validación CRC y decodificación) en el contexto del hilo secundario.
2. WHEN el `Davis_Reader` decodifica correctamente un LOOP_Packet, THE `Davis_Reader` SHALL emitir la señal Qt `weather_data_updated(WeatherData)` desde el hilo secundario hacia la UI principal.
3. WHEN la conexión con la estación se establece o se pierde, THE `Davis_Reader` SHALL emitir la señal Qt `connection_changed(bool)` con el estado actualizado.
4. WHEN se agota el número máximo de reintentos configurados sin éxito, THE `Davis_Reader` SHALL emitir la señal Qt `retry_exhausted(str, str)` con el nombre de la operación y el mensaje de error, siguiendo el mismo contrato que `ModbusClient.retry_exhausted`.
5. WHILE el `Davis_Reader` está en ejecución, THE `Davis_Reader` SHALL utilizar un `QTimer` interno para disparar la lectura periódica con el intervalo configurado en `poll_interval_ms`.
6. WHEN el método `stop()` es invocado, THE `Davis_Reader` SHALL detener el `QTimer`, cerrar el Transport activo y liberar todos los recursos antes de finalizar el hilo, en un plazo máximo de 10 segundos.

---

### Requisito 7: Integración con RetryStrategy

**User Story:** Como desarrollador, quiero que los fallos transitorios de comunicación con la estación Davis se gestionen automáticamente mediante la misma estrategia de reintentos que usa el resto de Nexo Solar, para mantener la coherencia del sistema.

#### Criterios de Aceptación

1. THE `Davis_Reader` SHALL instanciar `RetryStrategy` con los parámetros `retry_attempts`, `retry_backoff` y un `backoff_factor` de 2.0, leídos desde `ConfigurationManager`.
2. WHEN una operación de lectura falla por timeout, error de puerto o CRC inválido, THE `Davis_Reader` SHALL delegar el reintento a `RetryStrategy.execute_with_retry`, respetando el backoff exponencial configurado.
3. IF `RetryStrategy` agota todos los intentos sin éxito, THEN THE `Davis_Reader` SHALL emitir la señal `retry_exhausted` y entrar en un estado de espera seguro hasta que el operador resuelva el problema o se solicite una reconexión manual.
4. WHEN `RetryStrategy` logra completar una operación con éxito en un intento posterior al primero, THE `LoggingService` SHALL registrar el evento con nivel INFO indicando el intento en que tuvo éxito.

---

### Requisito 8: Logging centralizado

**User Story:** Como operador, quiero que todas las operaciones relevantes del lector Davis queden registradas en el sistema de logging existente de Nexo Solar, para poder diagnosticar problemas de comunicación con la estación.

#### Criterios de Aceptación

1. THE `Davis_Reader` SHALL utilizar el singleton `LoggingService` para todos los mensajes de log, sin instanciar loggers alternativos.
2. WHEN el `Davis_Reader` establece o pierde la conexión con la estación, THE `LoggingService` SHALL registrar el evento con nivel INFO.
3. WHEN el `CRC_Validator` descarta un paquete por CRC inválido, THE `LoggingService` SHALL registrar el evento con nivel WARNING incluyendo los valores CRC esperado y calculado.
4. WHEN el `Davis_Reader` inicia o detiene la lectura periódica, THE `LoggingService` SHALL registrar el evento con nivel INFO incluyendo el intervalo de polling configurado.
5. WHEN se decodifica correctamente un LOOP_Packet, THE `LoggingService` SHALL registrar los valores clave de `WeatherData` (temperatura exterior, humedad exterior, radiación solar, dirección de viento) con nivel DEBUG.

---

### Requisito 9: Conversión de unidades

**User Story:** Como usuario, quiero que las variables meteorológicas se presenten en el sistema internacional de unidades (°C, m/s, hPa, mm), para que sean coherentes con el resto del sistema SCADA.

#### Criterios de Aceptación

1. THE `Davis_Reader` SHALL convertir la temperatura exterior e interior de °F a °C mediante la fórmula `°C = (°F − 32) × 5/9` antes de emitir `weather_data_updated`.
2. THE `Davis_Reader` SHALL convertir la velocidad del viento de mph a m/s multiplicando por 0.44704 antes de emitir `weather_data_updated`.
3. THE `Davis_Reader` SHALL convertir la presión barométrica de inHg a hPa multiplicando por 33.8639 antes de emitir `weather_data_updated`.
4. THE `Davis_Reader` SHALL convertir la lluvia (tasa, tormenta, día, mes, año) de pulgadas a milímetros multiplicando por 25.4 antes de emitir `weather_data_updated`.
5. THE `Davis_Reader` SHALL mantener sin conversión la radiación solar (W/m²), la humedad (% RH), el índice UV y la dirección del viento (grados), ya que estas unidades son compatibles con el SI.
6. FOR ALL conversiones de temperatura, aplicar la conversión °F → °C y luego la conversión inversa °C → °F SHALL producir el valor original en °F con una tolerancia máxima de ±0.01 °F (propiedad de round-trip de conversión de unidades).

---

### Requisito 10: Transporte alternativo por red IP (WeatherLink IP)

**User Story:** Como administrador del sistema, quiero poder conectar la estación Davis a través de la red local usando el protocolo WeatherLink IP o un adaptador de red compatible, para aprovechar la infraestructura TCP/IP existente en instalaciones donde el acceso USB/serie no sea conveniente.

#### Criterios de Aceptación

1. WHEN el parámetro `transport` está configurado como `ip`, THE `IP_Transport` SHALL establecer una conexión TCP hacia `ip_host`:`ip_port` con el `timeout` configurado, de forma equivalente a como `ModbusConnector` gestiona conexiones TCP.
2. WHILE la conexión IP está activa, THE `IP_Transport` SHALL enviar y recibir los mismos bytes del protocolo Davis (Wake_Up_Sequence, comando LOOP, LOOP_Packet) de forma transparente, sin que `Davis_Reader` deba distinguir el tipo de transporte.
3. IF la conexión TCP se pierde durante una lectura, THEN THE `IP_Transport` SHALL notificar al `Davis_Reader` con una excepción de transporte, y THE `Davis_Reader` SHALL delegar la reconexión a `RetryStrategy`.
4. THE `IP_Transport` SHALL soportar la dirección IP y el puerto configurados en `ConfigurationManager` bajo las claves `davis_weatherlink.ip_host` y `davis_weatherlink.ip_port`.
5. WHERE el transporte IP está disponible, THE `Davis_Reader` SHALL comportarse de forma funcionalmente idéntica al caso del transporte serie, emitiendo las mismas señales Qt con los mismos tipos de datos.

---

### Requisito 11: Validación de la estructura WeatherData

**User Story:** Como desarrollador, quiero que los datos meteorológicos decodificados sean validados antes de ser emitidos a la UI, para evitar que valores fuera de rango contaminen el sistema SCADA.

#### Criterios de Aceptación

1. WHEN el `Packet_Parser` produce una estructura `WeatherData`, THE `Davis_Reader` SHALL verificar que la presión barométrica en hPa esté en el rango [800, 1100] hPa.
2. WHEN el `Packet_Parser` produce una estructura `WeatherData`, THE `Davis_Reader` SHALL verificar que la temperatura exterior en °C esté en el rango [−50, 60] °C.
3. WHEN el `Packet_Parser` produce una estructura `WeatherData`, THE `Davis_Reader` SHALL verificar que la humedad exterior esté en el rango [0, 100] % RH.
4. WHEN el `Packet_Parser` produce una estructura `WeatherData`, THE `Davis_Reader` SHALL verificar que la velocidad del viento en m/s esté en el rango [0, 90] m/s.
5. WHEN el `Packet_Parser` produce una estructura `WeatherData`, THE `Davis_Reader` SHALL verificar que la dirección del viento esté en el rango [0, 360] grados.
6. IF cualquier campo de `WeatherData` está fuera del rango válido definido en los criterios anteriores, THEN THE `Davis_Reader` SHALL descartar la estructura completa, registrar el campo y valor inválido en `LoggingService` con nivel WARNING, y no emitir la señal `weather_data_updated`.

---

### Requisito 12: Manejo de errores del puerto serie

**User Story:** Como operador, quiero que el sistema gestione correctamente los errores del puerto serie (dispositivo no disponible, desconexión inesperada), para que Nexo Solar no quede en un estado inconsistente si la estación Davis se desconecta.

#### Criterios de Aceptación

1. IF el `Serial_Transport` no puede abrir el puerto serie configurado al inicio, THEN THE `Davis_Reader` SHALL registrar el error en `LoggingService` con nivel ERROR y emitir la señal `connection_changed(False)`.
2. IF el puerto serie se cierra inesperadamente durante una operación de lectura, THEN THE `Serial_Transport` SHALL notificar al `Davis_Reader` con una excepción de transporte, y THE `Davis_Reader` SHALL delegar la reconexión a `RetryStrategy`.
3. IF `RetryStrategy` agota todos los intentos de reconexión al puerto serie, THEN THE `Davis_Reader` SHALL emitir la señal `retry_exhausted` con el nombre de operación `"Serial Connection"` y el mensaje de error detallado.
4. WHILE el `Davis_Reader` está en estado de error (sin transporte activo), THE `Davis_Reader` SHALL seguir respondiendo a la señal `stop()` para permitir un cierre limpio de la aplicación.

---

### Requisito 13: Integración con ConfigurationManager y config.yaml

**User Story:** Como administrador, quiero que toda la configuración del lector Davis esté centralizada en el `config.yaml` existente, para mantener un único punto de configuración coherente con el resto de Nexo Solar.

#### Criterios de Aceptación

1. THE `ConfigurationManager` SHALL exponer los parámetros de configuración Davis bajo la clave raíz `davis_weatherlink` con los sub-parámetros: `transport`, `serial_port`, `baud_rate`, `ip_host`, `ip_port`, `poll_interval_ms`, `timeout`, `retry_attempts` y `retry_backoff`.
2. THE `ConfigurationManager` SHALL aplicar los siguientes valores por defecto si los parámetros no están presentes en `config.yaml`: `transport: serial`, `baud_rate: 19200`, `poll_interval_ms: 5000`, `timeout: 5.0`, `retry_attempts: 3`, `retry_backoff: 1.0`.
3. WHEN `ConfigurationManager` carga la configuración, THE `ConfigurationManager` SHALL validar que `baud_rate` sea exactamente 19200 y que `transport` sea `serial` o `ip`; IF alguna validación falla, THEN THE `ConfigurationManager` SHALL registrar un error de configuración y usar el valor por defecto correspondiente.
4. THE `Davis_Reader` SHALL NO acceder directamente al fichero `config.yaml` sino únicamente a través de la interfaz pública de `ConfigurationManager`.
