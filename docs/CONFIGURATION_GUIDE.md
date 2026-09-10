# Guía de configuración

La configuración local se carga desde `config.yaml` en la raíz. Use `modbuspython/config.example.yaml` como plantilla:

```bash
cp modbuspython/config.example.yaml config.yaml
```

`ConfigurationManager` usa los valores predeterminados definidos en `modbuspython/config/config_defaults.py` cuando falta el archivo o no supera la validación, y valida la estructura con `modbuspython/config/config_schema.json`. `modbuspython/config/default_config.yaml` sirve como plantilla mantenida junto al código, pero la carga de la aplicación se realiza desde `config.yaml` en la raíz.

## Secciones disponibles

| Sección | Claves principales | Uso |
|---|---|---|
| `modbus` | `host`, `port`, `timeout`, `retry_attempts`, `retry_backoff`, `registers` | Conexión TCP y registros |
| `database` | `path`, `table_name`, `connection_pool_size` | SQLite local |
| `logging` | `level`, `file_path`, `max_bytes`, `backup_count` | Logs y rotación |
| `angles` | `rotation_min/max`, `elevation_min/max` | Límites del seguidor |
| `ui` | `update_interval_ms`, `chart_history_points`, `language` | Presentación |
| `performance` | `startup_timeout_s`, `shutdown_timeout_s`, `max_memory_mb` | Parámetros de rendimiento |

Ejemplo mínimo:

```yaml
modbus:
  host: "192.168.1.100"
  port: 502
  timeout: 5.0
  retry_attempts: 3
  retry_backoff: 1.0
  registers:
    rotation_setpoint: 0
    elevation_setpoint: 1
    rotation_actual: 2
    elevation_actual: 3
    irradiance: 4
database:
  path: "data/solarsense.db"
  table_name: "measurements"
  connection_pool_size: 5
```

Use rutas relativas a la raíz. Mantenga `.env`, `config.yaml`, `data/` y `logs/` fuera de Git. Las claves y rangos deben cumplir el esquema. No existe `requirements-dev.txt`; las herramientas de desarrollo se instalan según `docs/CONTRIBUTING.md` y `.github/workflows/test.yml`.
