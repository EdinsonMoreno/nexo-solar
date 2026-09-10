"""Configuration Manager for SolarSense SCADA application.

This module provides centralized configuration management with:
- Singleton pattern for single source of truth
- YAML/JSON configuration file support
- JSON Schema validation
- Dot notation for nested value access
- Default configuration creation
- Environment variable expansion (${VAR_NAME} syntax)
- Secure loading of .env files via python-dotenv
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import yaml
import json
from jsonschema import validate, ValidationError

from modbuspython.config.env_expander import EnvExpander
from modbuspython.config.credential_handler import CredentialHandler
from modbuspython.config.config_defaults import ConfigDefaults


class ConfigurationManager:
    """Singleton manager for application configuration.

    Provides centralized access to configuration values loaded from
    YAML or JSON files, with validation against a JSON schema.

    Example:
        >>> config = ConfigurationManager()
        >>> config.load_config(Path("config.yaml"), Path("schema.json"))
        >>> host = config.get("modbus.host")
        >>> port = config.get("modbus.port", 502)
    """

    _instance: Optional["ConfigurationManager"] = None

    def __new__(cls) -> "ConfigurationManager":
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        if not hasattr(self, "_initialized"):
            self._config: Dict[str, Any] = {}
            self._schema: Dict[str, Any] = {}
            self._config_path: Optional[Path] = None
            self._logger = logging.getLogger(__name__)
            self._initialized = True

            self._env_expander = EnvExpander()
            self._credential_handler = CredentialHandler()
            self._config_defaults = ConfigDefaults()

    def load_config(self, config_path: Path, schema_path: Path) -> None:
        """Load and validate configuration from file.

        If the configuration file doesn't exist, creates a default one.
        If the configuration is invalid, falls back to default values.

        Args:
            config_path: Path to configuration file (YAML or JSON)
            schema_path: Path to JSON schema file for validation

        Raises:
            ConfigurationError: If schema file doesn't exist or cannot be loaded
        """
        self._config_path = config_path
        self._load_schema(schema_path)

        if not config_path.exists():
            self._handle_missing_config(config_path)
            return

        self._load_and_validate_config(config_path)

    def _load_schema(self, schema_path: Path) -> None:
        """Load JSON schema file with error handling.

        Args:
            schema_path: Path to JSON schema file

        Raises:
            ConfigurationError: If schema cannot be loaded
        """
        from modbuspython.exceptions import ConfigurationError

        try:
            if not schema_path.exists():
                error_msg = f"Schema file not found: {schema_path}"
                self._logger.error(error_msg)
                raise ConfigurationError(error_msg, details={"schema_path": str(schema_path)})

            with open(schema_path, "r", encoding="utf-8") as f:
                self._schema = json.load(f)

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse schema file: {e}"
            self._logger.error(f"{error_msg} at line {e.lineno}, column {e.colno}")
            raise ConfigurationError(
                error_msg,
                details={"schema_path": str(schema_path), "line": e.lineno, "column": e.colno, "error": str(e.msg)},
            )
        except (OSError, IOError) as e:
            error_msg = f"Failed to read schema file: {e}"
            self._logger.error(error_msg)
            raise ConfigurationError(error_msg, details={"schema_path": str(schema_path), "error": str(e)})

    def _handle_missing_config(self, config_path: Path) -> None:
        """Handle missing configuration file by creating default.

        Args:
            config_path: Path where config file should be created
        """
        self._logger.warning(f"Configuration file not found: {config_path}. Creating default configuration.")
        try:
            self._config_defaults.create_default_file(config_path)
        except Exception as e:
            error_msg = f"Failed to create default configuration: {e}"
            self._logger.error(error_msg, exc_info=True)
            self._logger.warning("Loading default configuration in memory only")
            self._load_defaults()

    def _load_and_validate_config(self, config_path: Path) -> None:
        """Load configuration file and validate it.

        Args:
            config_path: Path to configuration file
        """
        try:
            self._config_defaults.check_permissions(config_path)
            parsed = self._parse_config_file(config_path)

            if parsed is None:
                self._logger.warning("Configuration file is empty. Using default configuration.")
                self._load_defaults()
                return

            self._config = self._env_expander.expand(parsed)

            if self._credential_handler._encryptor is not None:
                self._config = self._credential_handler.decrypt_values(self._config)

            missing_vars = self._env_expander.find_missing_vars(self._config)
            if missing_vars:
                self._logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")

            if not self._validate_against_schema():
                return

            if not self._perform_semantic_validation():
                return

            self._logger.info(f"Configuration loaded and validated successfully from {config_path}")

        except (yaml.YAMLError, json.JSONDecodeError, OSError, IOError) as e:
            self._handle_config_load_error(e, config_path)
        except Exception as e:
            self._logger.error(f"Unexpected error loading configuration: {e}", exc_info=True)
            self._logger.warning("Falling back to default configuration")
            self._load_defaults()

    def _parse_config_file(self, config_path: Path) -> Optional[dict]:
        """Parse configuration file based on extension.

        Args:
            config_path: Path to configuration file

        Returns:
            dict: Parsed configuration, or None if unsupported format

        Raises:
            yaml.YAMLError: If YAML parsing fails
            json.JSONDecodeError: If JSON parsing fails
            OSError: If file cannot be read
        """
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix in [".yaml", ".yml"]:
                return yaml.safe_load(f)  # type: ignore[no-any-return]
            elif config_path.suffix == ".json":
                return json.load(f)  # type: ignore[no-any-return]
            else:
                error_msg = f"Unsupported config file format: {config_path.suffix}"
                self._logger.error(error_msg)
                self._logger.warning("Falling back to default configuration")
                self._load_defaults()
                return None

    def _validate_against_schema(self) -> bool:
        """Validate configuration against JSON schema.

        Returns:
            bool: True if validation passed, False otherwise
        """
        try:
            validate(instance=self._config, schema=self._schema)
            return True
        except ValidationError as e:
            self._logger.error(
                f"Configuration schema validation failed: {e.message}\n"
                f"  Path: {' -> '.join(str(p) for p in e.path) if e.path else 'root'}\n"
                f"  Schema path: {' -> '.join(str(p) for p in e.schema_path) if e.schema_path else 'root'}"
            )
            self._logger.warning("Falling back to default configuration due to schema validation errors")
            self._load_defaults()
            return False

    def _perform_semantic_validation(self) -> bool:
        """Perform semantic validation of configuration values.

        Returns:
            bool: True if validation passed, False otherwise
        """
        try:
            validation_errors = self._validate_config_values()
            if validation_errors:
                error_msg = "Configuration semantic validation errors:\n" + "\n".join(
                    f"  - {err}" for err in validation_errors
                )
                self._logger.error(error_msg)
                self._logger.warning("Falling back to default configuration due to semantic validation errors")
                self._load_defaults()
                return False
            return True
        except Exception as e:
            self._logger.error(f"Error during semantic validation: {e}", exc_info=True)
            self._logger.warning("Falling back to default configuration due to validation error")
            self._load_defaults()
            return False

    def _handle_config_load_error(self, error: Exception, config_path: Path) -> None:
        """Handle errors during configuration file loading.

        Args:
            error: The exception that occurred
            config_path: Path to the configuration file
        """
        if isinstance(error, yaml.YAMLError):
            error_details = {"config_path": str(config_path), "error_type": "YAML parsing error"}
            if hasattr(error, "problem_mark"):
                mark = error.problem_mark
                error_details.update({"line": mark.line + 1, "column": mark.column + 1})
                self._logger.error(
                    f"Failed to parse YAML configuration file: {error}\n"
                    f"  Error at line {mark.line + 1}, column {mark.column + 1}"
                )
            else:
                self._logger.error(f"Failed to parse YAML configuration file: {error}")
        elif isinstance(error, json.JSONDecodeError):
            self._logger.error(
                f"Failed to parse JSON configuration file: {error}\n"
                f"  Error at line {error.lineno}, column {error.colno}: {error.msg}"
            )
        elif isinstance(error, (OSError, IOError)):
            self._logger.error(
                f"Failed to read configuration file: {error}\n"
                f"  Path: {config_path}\n"
                f"  Error: {type(error).__name__}: {str(error)}"
            )

        self._logger.warning("Falling back to default configuration")
        self._load_defaults()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key with dot notation support.

        Supports nested keys using dot notation (e.g., "modbus.host").

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key not found

        Returns:
            Configuration value or default if not found
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value (runtime only, not persisted).

        Supports nested keys using dot notation (e.g., "modbus.host").
        Changes are not saved to the configuration file.

        Args:
            key: Configuration key (supports dot notation for nested values)
            value: Value to set
        """
        keys = key.split(".")
        target = self._config

        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value
        log_value = self._credential_handler.mask_value(key, value)
        self._logger.debug(f"Configuration value set: {key} = {log_value}")

    def validate(self) -> bool:
        """Validate current configuration against schema.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            validate(instance=self._config, schema=self._schema)
            return True
        except ValidationError as e:
            self._logger.error(f"Configuration validation failed: {e.message}")
            return False

    def create_default_config(self, output_path: Path) -> None:
        """Create default configuration file.

        Args:
            output_path: Path where to create the default configuration file

        Raises:
            ConfigurationError: If unable to create configuration file
        """
        self._config_defaults.create_default_file(output_path)
        self._config = self._config_defaults.get_defaults()

    def reload(self) -> None:
        """Reload configuration from file.

        Raises:
            ConfigurationError: If no configuration file has been loaded yet or reload fails
        """
        from modbuspython.exceptions import ConfigurationError

        if self._config_path is None:
            error_msg = "No configuration file loaded. Call load_config() first."
            self._logger.error(error_msg)
            raise ConfigurationError(error_msg)

        try:
            schema_path = self._config_path.parent / "config_schema.json"
            self._logger.info(f"Reloading configuration from {self._config_path}")
            self.load_config(self._config_path, schema_path)
        except Exception as e:
            error_msg = f"Failed to reload configuration: {e}"
            self._logger.error(error_msg, exc_info=True)
            raise ConfigurationError(error_msg, details={"config_path": str(self._config_path), "error": str(e)})

    def _validate_config_values(self) -> List[str]:
        """Validate configuration values using ValidationService.

        Validates:
        - Modbus host IP address format
        - Modbus port number range
        - Database table name (SQL identifier)

        Returns:
            List of validation error messages (empty if all valid)
        """
        from modbuspython.backend.validation_service import ValidationService

        validator = ValidationService(config_manager=None)
        errors = []

        modbus_host = self.get("modbus.host")
        if modbus_host:
            is_valid, error_msg = validator.validate_ip_address(modbus_host)
            if not is_valid:
                errors.append(f"modbus.host: {error_msg}")

        modbus_port = self.get("modbus.port")
        if modbus_port is not None:
            is_valid, error_msg = validator.validate_port(modbus_port)
            if not is_valid:
                errors.append(f"modbus.port: {error_msg}")

        table_name = self.get("database.table_name")
        if table_name:
            is_valid, error_msg = validator.validate_sql_identifier(table_name)
            if not is_valid:
                errors.append(f"database.table_name: {error_msg}")

        davis_transport = self.get("davis_weatherlink.transport")
        if davis_transport and davis_transport not in ("serial", "ip"):
            errors.append("davis_weatherlink.transport: must be 'serial' or 'ip'")

        davis_baud_rate = self.get("davis_weatherlink.baud_rate")
        if davis_baud_rate is not None and int(davis_baud_rate) != 19200:
            errors.append("davis_weatherlink.baud_rate: Davis WeatherLink VCP requires 19200")

        return errors

    def _load_defaults(self) -> None:
        """Load default configuration values internally."""
        self._config = {
            "modbus": {
                "host": "192.168.1.100",
                "port": 502,
                "timeout": 5.0,
                "retry_attempts": 3,
                "retry_backoff": 1.0,
                "registers": {
                    "rotation_setpoint": 0,
                    "elevation_setpoint": 1,
                    "rotation_actual": 2,
                    "elevation_actual": 3,
                    "irradiance": 4,
                },
            },
            "database": {
                "path": "data/solarsense.db",
                "table_name": "measurements",
                "connection_pool_size": 5,
            },
            "davis_weatherlink": {
                "transport": "serial",
                "serial_port": "/dev/ttyUSB0",
                "baud_rate": 19200,
                "ip_host": "192.168.1.50",
                "ip_port": 22222,
                "poll_interval_ms": 5000,
                "timeout": 5.0,
                "retry_attempts": 3,
                "retry_backoff": 1.0,
            },
            "logging": {
                "level": "INFO",
                "file_path": "logs/solarsense.log",
                "max_bytes": 10485760,
                "backup_count": 5,
            },
            "angles": {
                "rotation_min": 0,
                "rotation_max": 360,
                "elevation_min": 0,
                "elevation_max": 145,
            },
        }

    @property
    def modbus_config(self) -> Dict[str, Any]:
        """Get Modbus-specific configuration."""
        result = self._config.get("modbus", {})
        return result if isinstance(result, dict) else {}

    @property
    def database_config(self) -> Dict[str, Any]:
        """Get database-specific configuration."""
        result = self._config.get("database", {})
        return result if isinstance(result, dict) else {}

    @property
    def logging_config(self) -> Dict[str, Any]:
        """Get logging-specific configuration."""
        result = self._config.get("logging", {})
        return result if isinstance(result, dict) else {}

    @property
    def davis_weatherlink_config(self) -> Dict[str, Any]:
        """Get Davis WeatherLink-specific configuration."""
        result = self._config.get("davis_weatherlink", {})
        return result if isinstance(result, dict) else {}
