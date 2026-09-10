# Davis WeatherLink - Plan de pruebas de laboratorio

Fecha objetivo: 2026-09-11
Rama objetivo: `dev`

Este plan deja lista la prueba con una Davis Vantage Pro2 conectada por
WeatherLink USB/serial o por WeatherLinkIP. El objetivo es validar con equipo
real lo que ya esta implementado en Nexo Solar y separar rapido si un fallo es
de cableado, permisos, protocolo, configuracion o parsing.

## Fuentes oficiales revisadas

- Davis Instruments Support: `(SDK) Vantage Pro, Pro2, and Vue Communications Reference 2.6.1 Any OS`.
  Referencia oficial para programadores que describe protocolo serial,
  comandos, paquetes LOOP, CRC y formatos de datos.
  https://support.davisinstruments.com/article/rbzgl0rh6k-vantage-pro-pro-2-and-vue-communications-reference-2-6-1-any-os
- Davis Instruments Support: `How do I communicate directly with my WeatherLinkIP data logger?`.
  Confirma TCP crudo en puerto `22222` y envio de comandos seriales sobre IP.
  https://support.davisinstruments.com/article/ohno6ugc5x-how-do-i-communicate-directly-with-my-weather-link-ip-data-logger
- Davis Instruments Support: `How can I change what units I want to use?`.
  Confirma que WeatherLink permite preferencia de unidades desde la app.
  https://support.davisinstruments.com/article/3pawa7qbqo-how-can-i-change-what-units-i-want-to-use
- Davis Instruments Support: `What features are available on WeatherLink.com 2.0?`.
  Confirma vistas Bulletin, Chart, Data y Map; personalizacion de sensores y
  graficas en el ecosistema WeatherLink.
  https://support.davisinstruments.com/article/sw2l25wv50-what-features-are-available-on-weather-link-com-2-0

## Verificacion contra referencia Davis

| Punto | Estado en Nexo Solar | Evidencia |
|---|---|---|
| Wake-up | Envia `LF` (`0x0A`) y espera `LF+CR` (`0x0A 0x0D`) | Alineado con Communications Reference |
| Comando LOOP | Envia `LOOP 1` terminado en `LF` (`0x0A`) | Alineado con ejemplos oficiales `LOOP <n><LF>` |
| ACK | Espera `0x06` antes de leer datos | Alineado con respuesta oficial de comandos reconocidos |
| Paquete LOOP | Lee exactamente 99 bytes | Alineado con formato oficial LOOP |
| CRC | CRC-CCITT, inicial `0x0000`, MSB primero en bytes de CRC | Test local con ejemplo oficial `C6 CE A2 03 -> E2 B4` |
| Offsets LOOP | Campos principales en offsets oficiales: barometro 7, temperatura interior 9, humedad interior 11, temperatura exterior 12, viento 14/15/16, humedad exterior 33, lluvia 41, UV 43, solar 44, acumulados lluvia 46/50/52/54 | Pendiente capturar paquete real y comparar contra consola |
| Lluvia | Implementado con `0.01 in` por click por defecto | Pendiente confirmar tipo de colector: `0.01 in` o `0.2 mm` |
| WeatherLinkIP | TCP crudo `ip_host:22222` con los mismos bytes del protocolo | Alineado con soporte oficial; liberar socket si el logger sube a WeatherLink.com |
| Unidades | Backend emite SI; UI futura podra mostrar preferencias | Alineado con requerimiento interno; preferencia UI pendiente del rediseño |

## Prerrequisitos

- Consola Davis Vantage Pro2 o Weather Envoy encendida.
- WeatherLink USB/serial data logger o WeatherLinkIP.
- Cable USB/serial funcional o IP del logger en la red local.
- Nexo Solar en rama `dev`.
- Dependencias Python del proyecto instaladas en el entorno local.
- Para tests Qt completos: `PyQt6` disponible en el entorno.
- Para serial: `pyserial` disponible.

## Preparacion en Fedora

Detectar el puerto:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
dmesg | tail -n 40
```

Revisar permisos del usuario:

```bash
id
groups
```

Si el puerto pertenece a `dialout`, `uucp` o grupo similar y el usuario no esta
incluido, agregarlo y cerrar sesion antes de probar:

```bash
sudo usermod -aG dialout $USER
sudo usermod -aG uucp $USER
```

Verificar que otro programa no tenga tomado el puerto:

```bash
fuser /dev/ttyUSB0
```

## Configuracion esperada

Archivo: `config.yaml` o `modbuspython/config/default_config.yaml`, segun el
flujo que se use para arrancar la aplicacion.

Serial USB/VCP:

```yaml
davis_weatherlink:
  transport: serial
  serial_port: /dev/ttyUSB0
  baud_rate: 19200
  ip_host: 192.168.1.50
  ip_port: 22222
  poll_interval_ms: 5000
  timeout: 5.0
  retry_attempts: 3
  retry_backoff: 1.0
```

WeatherLinkIP:

```yaml
davis_weatherlink:
  transport: ip
  serial_port: /dev/ttyUSB0
  baud_rate: 19200
  ip_host: 192.168.1.50
  ip_port: 22222
  poll_interval_ms: 5000
  timeout: 5.0
  retry_attempts: 3
  retry_backoff: 1.0
```

## Pruebas previas sin hardware

Ejecutar desde la raiz del repo:

```bash
python -m json.tool modbuspython/config/config_schema.json >/dev/null
python -m pytest -o addopts='' modbuspython/tests/unit/test_davis_weatherlink_conversions.py modbuspython/tests/unit/test_davis_weatherlink_crc.py modbuspython/tests/unit/test_davis_weatherlink_parser.py modbuspython/tests/unit/test_davis_weatherlink_transport.py modbuspython/tests/unit/test_davis_weatherlink_reader.py -q
node --check Mockup/app.js
```

Si `test_davis_weatherlink_reader.py` queda omitido por falta de PyQt6, instalar
dependencias o correrlo en el entorno donde se ejecuta la app de escritorio.

## Casos de prueba con equipo real

### Caso 1: deteccion del transporte serial

1. Conectar WeatherLink USB/serial.
2. Confirmar puerto `/dev/ttyUSB0` o equivalente.
3. Configurar `davis_weatherlink.transport: serial`.
4. Abrir Nexo Solar.

Criterio de exito: la UI muestra Davis conectado y registra conexion en log.

Criterio de fallo: error de permiso, puerto inexistente o timeout de apertura.
Registrar salida de `ls -l`, `groups` y log de Nexo Solar.

### Caso 2: wake-up

1. Ejecutar lectura manual o iniciar lectura automatica.
2. Observar logs Davis.

Criterio de exito: se envia `0x0A` y se recibe `0x0A 0x0D` en menos de 1.2 s.

Criterio de fallo: sin respuesta despues de 3 intentos. Revisar cable, consola
en pantalla de configuracion, puerto ocupado y alimentacion.

### Caso 3: comando LOOP

1. Despues del wake-up, solicitar `LOOP 1`.
2. Confirmar ACK y lectura binaria.

Criterio de exito: ACK `0x06` y paquete de 99 bytes.

Criterio de fallo: NAK `0x21`, timeout o menos de 99 bytes. Capturar bytes
hexadecimales si se puede y repetir una vez con timeout mayor.

### Caso 4: CRC

1. Procesar el paquete recibido.
2. Comparar CRC calculado contra bytes 97 y 98.

Criterio de exito: CRC valido.

Criterio de fallo: CRC invalido repetido. Capturar paquete completo en hex, no
ajustar offsets a ciegas.

### Caso 5: parsing y comparacion contra consola

1. Anotar valores visibles en consola Davis: temperatura, humedad, presion,
   viento, direccion, lluvia, radiacion solar e indice UV si existen sensores.
2. Comparar contra Nexo Solar.

Criterio de exito: valores razonables y unidades correctas despues de conversion
a SI.

Criterio de fallo: un campo desviado apunta a offset/factor/unidad; capturar
paquete y valor esperado.

### Caso 6: lluvia y tipo de colector

1. Revisar configuracion fisica o consola del colector de lluvia.
2. Confirmar si el click representa `0.01 in` o `0.2 mm`.

Criterio de exito: factor documentado y configurado.

Criterio de fallo: acumulados de lluvia no cuadran. No corregir desde intuicion:
registrar factor real del equipo.

### Caso 7: WeatherLinkIP, si aplica

1. Configurar `transport: ip`, `ip_host` y `ip_port: 22222`.
2. Probar conexion en la misma red.

Criterio de exito: socket TCP crudo abre, responde a wake-up y LOOP igual que
serial.

Criterio de fallo: conexion rechazada temporalmente. Segun Davis, el logger IP
puede rechazar mientras sube a WeatherLink.com; esperar unos segundos y repetir.
Si tambien se usa subida cloud, liberar socket periodicamente.

## Evidencias a capturar

- Modelo exacto de consola/logger y firmware si se puede consultar.
- Puerto serial o IP usada.
- Fragmento de `config.yaml` sin secretos.
- Logs de conexion, wake-up, ACK, longitud de paquete, CRC y parsing.
- Paquete LOOP completo en hex si hay fallo de CRC o campo incorrecto.
- Captura de la UI con las 15 variables y hora de ultima lectura.
- Comparacion manual de valores consola Davis vs Nexo Solar.

## Decision para pasar a QA

Pasa a QA si:

- La app no se bloquea durante lectura automatica.
- La conexion se establece por el transporte disponible.
- Hay wake-up correcto.
- `LOOP 1` recibe ACK.
- El paquete recibido mide 99 bytes.
- CRC valida al menos 10 lecturas consecutivas.
- Las variables principales coinciden razonablemente con la consola.
- Los fallos quedan en logs claros sin cerrar la aplicacion.

No pasa a QA si:

- El puerto requiere permisos no resueltos.
- No hay ACK con comandos oficiales.
- La UI se congela durante lectura.
- Hay CRC invalido recurrente.
- Una variable critica queda en offset/factor dudoso sin evidencia.
