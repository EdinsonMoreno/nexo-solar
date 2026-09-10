# Módulo de configuración

`ConfigurationManager` centraliza la configuración de la aplicación. Carga YAML/JSON, permite claves con notación de punto, aplica valores predeterminados y valida contra `config_schema.json`.

```python
from pathlib import Path
from modbuspython.config import ConfigurationManager

config = ConfigurationManager()
config.load_config(
    config_path=Path("config.yaml"),
    schema_path=Path("modbuspython/config/config_schema.json"),
)
host = config.get("modbus.host")
port = config.get("modbus.port", 502)
```

Use `modbuspython/config.example.yaml` como plantilla. `set()` cambia la instancia en memoria y no persiste el archivo. Consulte [CONFIGURATION_GUIDE.md](../../docs/CONFIGURATION_GUIDE.md).
