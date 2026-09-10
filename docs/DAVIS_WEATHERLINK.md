# Davis WeatherLink

Esta carpeta documenta la integracion Davis WeatherLink para Nexo Solar.

## Estado actual

- `modbuspython/data_access/davis_weatherlink/weather_data.py` define el modelo `WeatherData` con unidades de ingenieria listas para UI o persistencia.
- `unit_conversion.py` centraliza conversiones para evitar formulas repetidas.
- `crc_validator.py` calcula y valida el CRC-CCITT del paquete LOOP segun la especificacion local del cambio.
- `packet_parser.py` decodifica paquetes LOOP de 99 bytes en `WeatherData`.
- `transport.py` separa el I/O serial VCP y TCP/IP detras de una interfaz comun.
- `davis_reader.py` orquesta wake-up, comando LOOP, CRC, parsing, validacion de rangos, reintentos y senales Qt.
- `WebBridge` traduce las senales Davis hacia la pestana "Estacion Davis" sin meter logica de protocolo en JavaScript.
- La matriz de trazabilidad esta en `docs/DAVIS_SPEC_MATRIX.md`.
- El plan de pruebas con equipo real esta en `docs/DAVIS_LAB_TEST_PLAN.md`.

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
- Definir persistencia historica meteorologica si se requiere para analisis.
- Confirmar en laboratorio el tipo de colector de lluvia para fijar el factor
  `rain_click_inches`.
