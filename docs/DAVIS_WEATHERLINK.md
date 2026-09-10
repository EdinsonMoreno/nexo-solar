# Davis WeatherLink

Esta carpeta documenta la integracion Davis WeatherLink para Nexo Solar.

## Estado actual

- `modbuspython/data_access/davis_weatherlink/weather_data.py` define el modelo `WeatherData` con unidades de ingenieria listas para UI o persistencia.
- `unit_conversion.py` centraliza conversiones para evitar formulas repetidas.
- `crc_validator.py` calcula y valida el CRC-CCITT del paquete LOOP segun la especificacion local del cambio.
- `packet_parser.py` decodifica paquetes LOOP de 99 bytes en `WeatherData`.
- `transport.py` separa el I/O serial VCP y TCP/IP detras de una interfaz comun.
- `davis_reader.py` orquesta wake-up, comando LOOP, CRC, parsing, validacion de rangos, reintentos y senales Qt.
- `DavisWeatherRepository` persiste cada lectura valida en la tabla SQLite
  `davis_weather_readings`.
- `WebBridge` traduce las senales Davis hacia la pestana "Estacion Davis" sin meter logica de protocolo en JavaScript.
- La interfaz muestra Davis USB separado de Modbus/ESP8266 y usa el historico
  persistido para graficas cuando esta disponible.
- La pestaña de configuracion puede detectar puertos USB/serial visibles para
  pyserial, elegir el candidato Davis y actualizar `davis_weatherlink.serial_port`
  en la configuracion activa.
- La matriz de trazabilidad esta en `docs/DAVIS_SPEC_MATRIX.md`.
- El plan de pruebas con equipo real esta en `docs/DAVIS_LAB_TEST_PLAN.md`.

## Autoconfiguracion USB/Serial

En **Configuracion > Conexion Davis**, el boton **Detectar puertos** lista los
puertos visibles para pyserial sin ejecutar comandos del sistema.

- En Windows se muestran los puertos `COMx` asignados por el Administrador de
  dispositivos, por ejemplo `COM3` o `COM7`.
- En Fedora/Linux se muestran dispositivos como `/dev/ttyUSB0` y `/dev/ttyACM0`.
- La app marca como candidato Davis los puertos con metadatos tipicos de
  WeatherLink, Silicon Labs/CP210x, FTDI o USB serial.
- Al presionar **Usar este puerto**, la app cambia el transporte a `serial`,
  actualiza `davis_weatherlink.serial_port` en la configuracion activa y deja el
  lector Davis listo para conectar o reconectar con ese puerto.

Si Fedora muestra el puerto pero la prueba corta devuelve permiso denegado,
agrega el usuario al grupo serial correspondiente y volve a iniciar sesion:

```bash
sudo usermod -aG dialout,uucp $USER
```

Si el mensaje indica puerto ocupado, cerra cualquier monitor serial, IDE o
instancia anterior de Nexo Solar que este usando el mismo puerto. En Windows,
confirma el COM asignado desde el Administrador de dispositivos si hay mas de un
adaptador conectado.

## Reglas de mantenimiento

- Mantener backend y frontend separados: el parser no debe importar PyQt ni tocar DOM.
- No leer hardware desde la UI: la futura lectura serial/IP debe vivir en `data_access`.
- Mantener funciones pequenas y nombres explicitos.
- Probar cada regla de conversion y parsing con paquetes sinteticos antes de conectar la estacion real.
- Cuando exista diferencia entre el SPEC local y la referencia oficial Davis,
  priorizar la referencia oficial y actualizar SPEC, pruebas y documentacion en
  el mismo cambio.

## Pendiente

- Verificar con documentacion primaria de Davis cualquier offset o factor que no este confirmado por hardware.
- Ejecutar las pruebas Qt del lector en un entorno con PyQt6 instalado.
- Probar serial VCP e IP con equipo real o adaptador disponible.
- Confirmar en laboratorio el tipo de colector de lluvia para fijar el factor
  `rain_click_inches`.
