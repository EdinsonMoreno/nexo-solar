# Solución de problemas

## La aplicación no inicia

1. Ejecute desde la raíz: `python run.py`.
2. Active el entorno virtual e instale `requirements.txt`.
3. Compruebe Python 3.10 o posterior y las bibliotecas Qt/XCB de Linux.
4. Revise la excepción en la terminal y `logs/nexo_solar.log`.

No ejecute `modbuspython/main_app.py` directamente.

Durante el arranque se muestra una pantalla de carga con barra de progreso.
Si la aplicación se queda en esa pantalla, revise la terminal y el log para
identificar si falló la configuración, la base de datos o la interfaz web.

## No hay datos Modbus

Verifique `modbus.host`, `port` y los registros de `config.yaml`; compruebe que el dispositivo esté encendido, sea accesible y exponga Modbus TCP. Revise timeout, reintentos y logs.

## SQLite no se crea o está bloqueada

Compruebe que `database.path` apunte a una carpeta escribible y que ningún proceso externo mantenga abierta la base. Detenga la aplicación antes de copiarla o inspeccionarla y conserve un respaldo.

## Mapa o WebDashboard en blanco

Confirme que PyQt6-WebEngine esté instalado. El mapa puede requerir conectividad para teselas. `Mockup/` solo es una maqueta estática.

## Configuración inválida

Valide YAML y compare con `modbuspython/config/config_schema.json`. Use [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md); no agregue claves no soportadas.

## Reportar un problema

Abra un issue privado o contacte al mantenedor. Incluya sistema operativo, Python, comando, error y configuración sin secretos.
