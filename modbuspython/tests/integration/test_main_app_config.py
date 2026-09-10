"""Integration tests for main_app.py configuration loading.

Tests that the application properly loads configuration at startup
and passes it to components.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modbuspython.config.config_manager import ConfigurationManager
from modbuspython.data_access.logging_service import LoggingService


class TestMainAppConfigurationLoading:
    """Test configuration loading in main_app.py startup."""

    def test_config_loads_successfully_with_valid_file(self, tmp_path):
        """Test that configuration loads successfully when valid config file exists."""
        # Create a valid config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
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
""")

        # Load schema
        schema_path = Path("modbuspython/config/config_schema.json")

        # Create config manager and load
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Verify configuration loaded correctly
        assert config.get("modbus.host") == "192.168.1.100"
        assert config.get("modbus.port") == 502
        assert config.get("logging.level") == "INFO"
        assert config.get("database.table_name") == "measurements"

    def test_config_creates_default_when_missing(self, tmp_path):
        """Test that default configuration is created when config file is missing."""
        config_file = tmp_path / "config.yaml"
        schema_path = Path("modbuspython/config/config_schema.json")

        # Ensure config file doesn't exist
        assert not config_file.exists()

        # Create config manager and load (should create default)
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Verify default configuration was created
        assert config_file.exists()
        assert config.get("modbus.host") == "192.168.1.100"
        assert config.get("modbus.port") == 502

    def test_config_uses_defaults_on_invalid_file(self, tmp_path):
        """Test that default values are used when config file is invalid."""
        # Create an invalid config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [[[")

        schema_path = Path("modbuspython/config/config_schema.json")

        # Create config manager and load (should fall back to defaults)
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Verify default configuration is used
        assert config.get("modbus.host") == "192.168.1.100"
        assert config.get("modbus.port") == 502

    def test_logging_service_uses_config_values(self, tmp_path):
        """Test that LoggingService is initialized with values from configuration."""
        # Create a valid config file with custom logging settings
        config_file = tmp_path / "config.yaml"
        log_file = tmp_path / "custom.log"
        # Use forward slashes for cross-platform compatibility
        log_file_str = str(log_file).replace("\\", "/")
        config_file.write_text(f"""
modbus:
  host: "192.168.1.100"
  port: 502
  timeout: 5.0
database:
  path: "data/nexo_solar.db"
  table_name: "measurements"
logging:
  level: "DEBUG"
  file_path: "{log_file_str}"
  max_bytes: 5242880
  backup_count: 3
angles:
  rotation_min: 0
  rotation_max: 360
  elevation_min: 0
  elevation_max: 145
""")

        schema_path = Path("modbuspython/config/config_schema.json")

        # Load configuration
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Initialize logging service with config
        logger = LoggingService()
        logging_config = config.logging_config
        logger.setup(
            log_file=Path(logging_config.get("file_path", "logs/nexo_solar.log")),
            level=logging_config.get("level", "INFO"),
            max_bytes=logging_config.get("max_bytes", 10485760),
            backup_count=logging_config.get("backup_count", 5),
        )

        # Verify logger was configured
        logger.info("Test message")
        assert log_file.exists()

    def test_modbus_config_passed_to_client(self, tmp_path):
        """Test that Modbus configuration is correctly extracted and can be passed to ModbusClient."""
        # Create a valid config file with custom Modbus settings
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
modbus:
  host: "10.0.0.50"
  port: 5020
  timeout: 3.0
database:
  path: "data/nexo_solar.db"
  table_name: "measurements"
logging:
  level: "INFO"
  file_path: "logs/nexo_solar.log"
angles:
  rotation_min: 0
  rotation_max: 360
  elevation_min: 0
  elevation_max: 145
""")

        schema_path = Path("modbuspython/config/config_schema.json")

        # Load configuration
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Extract Modbus configuration
        modbus_config = config.modbus_config
        modbus_host = modbus_config.get("host", "192.168.1.100")
        modbus_port = modbus_config.get("port", 502)

        # Verify correct values extracted
        assert modbus_host == "10.0.0.50"
        assert modbus_port == 5020

    def test_schema_not_found_raises_error(self, tmp_path):
        """Test that missing schema file raises FileNotFoundError."""
        config_file = tmp_path / "config.yaml"
        schema_path = tmp_path / "nonexistent_schema.json"

        config = ConfigurationManager()

        with pytest.raises(FileNotFoundError):
            config.load_config(config_file, schema_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
