# Cómo Ejecutar SolarSense SCADA

## Método Recomendado (desde la raíz del proyecto)

```bash
python run.py
```

Este es el método recomendado porque:
- Configura correctamente el Python path
- Maneja los imports del paquete apropiadamente
- Funciona consistentemente en todos los entornos

## Método Alternativo (como módulo)

Desde la raíz del proyecto:

```bash
python -m modbuspython.main_app
```

## ⚠️ NO Ejecutar Directamente

**NO ejecutes:**
```bash
python modbuspython/main_app.py  # ❌ Esto causará errores de import
```

Ejecutar el archivo directamente causa `ModuleNotFoundError` porque Python no reconoce `modbuspython` como un paquete cuando se ejecuta de esta manera.

## Requisitos

Asegúrate de tener el entorno virtual activado:

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

## Estructura de Imports

El proyecto usa imports relativos dentro del paquete `modbuspython`:
- `from .ui.monitor_tab import MonitorTab`
- `from .data_access.modbus_client import ModbusClient`
- `from .config.config_manager import ConfigurationManager`

Esto requiere que el proyecto se ejecute como un paquete, no como un script independiente.

## Troubleshooting

Si encuentras errores de import:
1. Verifica que estás en la raíz del proyecto (donde está `run.py`)
2. Verifica que el entorno virtual está activado
3. Usa `python run.py` en lugar de ejecutar `main_app.py` directamente
