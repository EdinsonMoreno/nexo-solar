"""Default configuration management.

Provides default configuration values and creation of default
configuration files.
"""

import os
from typing import Any, Dict
from pathlib import Path
import logging
import yaml
import json

from modbuspython.exceptions import ConfigurationError

DEFAULT_CONFIG: Dict[str, Any] = {
    "modbus": {
        "enabled": False,
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
    "database": {
        "path": "data/nexo_solar.db",
        "table_name": "mediciones",
        "analysis_path": "data/nexo_solar.db",
        "analysis_table": "davis_weather_readings",
        "connection_pool_size": 5,
    },
    "logging": {
        "level": "INFO",
        "file_path": "logs/nexo_solar.log",
        "max_bytes": 10485760,
        "backup_count": 5,
    },
    "angles": {
        "rotation_min": 0,
        "rotation_max": 360,
        "elevation_min": 0,
        "elevation_max": 145,
    },
    "ui": {
        "update_interval_ms": 1000,
        "chart_history_points": 100,
        "language": "es",
    },
    "performance": {
        "startup_timeout_s": 5,
        "shutdown_timeout_s": 10,
        "max_memory_mb": 500,
    },
}


class ConfigDefaults:
    """Manages default configuration values and file creation."""

    def __init__(self) -> None:
        """Initialize config defaults."""
        self._logger = logging.getLogger(__name__)

    def get_defaults(self) -> Dict[str, Any]:
        """Get default configuration dictionary.

        Returns:
            Default configuration dictionary
        """
        import copy

        return copy.deepcopy(DEFAULT_CONFIG)

    def create_default_file(self, output_path: Path) -> None:
        """Create default configuration file.

        Args:
            output_path: Path where to create the default configuration file

        Raises:
            ConfigurationError: If unable to create configuration file
        """
        default_config = self.get_defaults()

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                if output_path.suffix in [".yaml", ".yml"]:
                    yaml.dump(default_config, f, default_flow_style=False, indent=2)
                elif output_path.suffix == ".json":
                    json.dump(default_config, f, indent=2)
                else:
                    error_msg = f"Unsupported config file format: {output_path.suffix}"
                    self._logger.error(error_msg)
                    raise ConfigurationError(
                        error_msg,
                        details={"output_path": str(output_path), "suffix": output_path.suffix},
                    )

            self._logger.info(f"Default configuration created at: {output_path}")
            self._set_secure_permissions(output_path)

        except (OSError, IOError) as e:
            error_msg = f"Failed to create default configuration file: {e}"
            self._logger.error(f"{error_msg}\n  Path: {output_path}\n  Error: {type(e).__name__}: {str(e)}")
            raise ConfigurationError(error_msg, details={"output_path": str(output_path), "error": str(e)})
        except yaml.YAMLError as e:
            error_msg = f"Failed to serialize default configuration to YAML: {e}"
            self._logger.error(error_msg)
            raise ConfigurationError(error_msg, details={"output_path": str(output_path), "error": str(e)})
        except Exception as e:
            error_msg = f"Unexpected error creating default configuration: {e}"
            self._logger.error(error_msg, exc_info=True)
            raise ConfigurationError(error_msg, details={"output_path": str(output_path), "error": str(e)})

    def _set_secure_permissions(self, file_path: Path) -> None:
        """Set restrictive file permissions (owner read/write only).

        On Unix: sets 0o600 permissions.
        On Windows: logs a warning since Windows ACLs are more complex.

        Args:
            file_path: Path to the file
        """
        if os.name == "posix":
            try:
                os.chmod(file_path, 0o600)
                self._logger.info(f"Set restrictive permissions (600) on {file_path}")
            except OSError as e:
                self._logger.warning(f"Failed to set file permissions on {file_path}: {e}")
        else:
            self._logger.debug(f"File permission setting skipped on Windows. " f"Ensure {file_path} has restricted access.")

    def check_permissions(self, config_path: Path) -> bool:
        """Check if configuration file has appropriate permissions.

        Args:
            config_path: Path to configuration file

        Returns:
            True if permissions are appropriate, False otherwise
        """
        if not config_path.exists():
            return True

        if os.name == "posix":
            try:
                stat_info = os.stat(config_path)
                mode = stat_info.st_mode & 0o777
                if mode & 0o077:
                    self._logger.warning(
                        f"Configuration file {config_path} has insecure permissions: {oct(mode)}. " f"Recommended: 0o600"
                    )
                    return False
                return True
            except OSError as e:
                self._logger.warning(f"Failed to check file permissions: {e}")
                return False
        else:
            self._logger.debug(
                f"Permission check skipped on Windows for {config_path}. " f"Manually verify file access is restricted."
            )
            return True
