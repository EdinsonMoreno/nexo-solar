# Configuration Module

This module provides centralized configuration management for the Nexo Solar application.

## Features

- **Singleton Pattern**: Single source of configuration truth throughout the application
- **Multiple Formats**: Supports both YAML and JSON configuration files
- **Schema Validation**: Validates configuration against JSON Schema
- **Dot Notation**: Access nested values using dot notation (e.g., `"modbus.host"`)
- **Default Configuration**: Automatically creates default configuration if missing
- **Type Safety**: Provides typed properties for common configuration sections

## Usage

### Basic Usage

```python
from pathlib import Path
from modbuspython.config import ConfigurationManager

# Get singleton instance
config = ConfigurationManager()

# Load configuration
config.load_config(
    config_path=Path("config.yaml"),
    schema_path=Path("modbuspython/config/config_schema.json")
)

# Access values with dot notation
host = config.get("modbus.host")
port = config.get("modbus.port", 502)  # with default value

# Set values (runtime only, not persisted)
config.set("modbus.timeout", 10.0)

# Access configuration sections
modbus_config = config.modbus_config
database_config = config.database_config
logging_config = config.logging_config
```

### Creating Configuration File

If no configuration file exists, the ConfigurationManager will automatically create one with default values:

```python
config = ConfigurationManager()
config.load_config(Path("config.yaml"), Path("schema.json"))
# If config.yaml doesn't exist, it will be created with defaults
```

You can also manually create a default configuration:

```python
config = ConfigurationManager()
config.create_default_config(Path("my_config.yaml"))
```

### Validation

Validate the current configuration against the schema:

```python
if config.validate():
    print("Configuration is valid")
else:
    print("Configuration has errors")
```

### Reloading Configuration

Reload configuration from file at runtime:

```python
config.reload()
```

## Configuration File Format

### YAML Example

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
  path: "data/nexo_solar.db"
  table_name: "measurements"
  connection_pool_size: 5

logging:
  level: "INFO"
  file_path: "logs/nexo_solar.log"
  max_bytes: 10485760
  backup_count: 5

angles:
  rotation_min: 0
  rotation_max: 360
  elevation_min: 0
  elevation_max: 145
```

### JSON Example

```json
{
  "modbus": {
    "host": "192.168.1.100",
    "port": 502,
    "timeout": 5.0
  },
  "database": {
    "path": "data/nexo_solar.db",
    "table_name": "measurements"
  }
}
```

## Configuration Schema

The configuration is validated against `config_schema.json`, which defines:

- Required fields
- Data types
- Value constraints (min/max, patterns, enums)
- Default values

See `config_schema.json` for the complete schema definition.

## Validators

The `validators` module provides validation functions for configuration values:

```python
from modbuspython.config import validators

# Validate IP address
is_valid, error = validators.validate_ip_address("192.168.1.100")

# Validate port
is_valid, error = validators.validate_port(502)

# Validate angle
is_valid, error = validators.validate_angle(180.0, 0, 360, "rotation")

# Validate SQL identifier
is_valid, error = validators.validate_sql_identifier("measurements")
```

## Files

- `config_manager.py`: Main ConfigurationManager class
- `config_schema.json`: JSON Schema for validation
- `default_config.yaml`: Default configuration template
- `validators.py`: Configuration value validators
- `__init__.py`: Module exports

## Environment-Specific Configuration

For different environments (development, production), you can:

1. Use different configuration files:
   ```python
   config.load_config(Path("config.production.yaml"), schema_path)
   ```

2. Override values programmatically:
   ```python
   config.load_config(Path("config.yaml"), schema_path)
   if os.getenv("ENV") == "production":
       config.set("logging.level", "WARNING")
   ```

3. Use environment variables (implement as needed):
   ```python
   host = os.getenv("MODBUS_HOST", config.get("modbus.host"))
   ```

## Error Handling

The ConfigurationManager handles errors gracefully:

- **Missing config file**: Creates default configuration
- **Invalid format**: Logs error and uses default values
- **Validation failure**: Logs error and uses default values
- **Missing schema**: Raises FileNotFoundError

All errors are logged using Python's logging module.

## Thread Safety

The ConfigurationManager uses the Singleton pattern. While the instance is shared across the application, configuration values should be loaded once at startup and treated as read-only during runtime to avoid race conditions.

For runtime changes, use the `set()` method, but be aware that changes are not persisted to the configuration file.
