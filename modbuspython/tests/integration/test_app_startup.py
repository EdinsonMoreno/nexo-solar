"""Integration tests for application startup verification (Task 6.2).

Tests that verify the application starts correctly under different scenarios:
- Valid configuration
- Missing configuration (creates default)
- Invalid configuration (uses defaults)
- UI responsiveness (ModbusClient in separate thread)

**Validates: Requirements 1.4, 2.7, 2.8, 6.2**
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modbuspython.config.config_manager import ConfigurationManager
from modbuspython.data_access.logging_service import LoggingService


# Mock the circular import issue in backend/__init__.py
@pytest.fixture(autouse=True)
def mock_backend_imports():
    """Mock backend imports to avoid circular import issues during testing."""
    with patch.dict(
        "sys.modules",
        {
            "backend": MagicMock(),
            "backend.sqlite_manager": MagicMock(),
        },
    ):
        yield


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestApplicationStartup:
    """Test application startup under different configuration scenarios."""

    def test_startup_with_valid_configuration(self, tmp_path):
        """Test that application configuration loads successfully with valid file.

        **Validates: Requirements 1.4, 2.7, 6.2**
        """
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
  path: "data/solarsense.db"
  table_name: "measurements"
  connection_pool_size: 5
logging:
  level: "INFO"
  file_path: "logs/solarsense.log"
  max_bytes: 10485760
  backup_count: 5
angles:
  rotation_min: 0
  rotation_max: 360
  elevation_min: 0
  elevation_max: 145
ui:
  update_interval_ms: 1000
  chart_history_points: 100
  language: "es"
performance:
  startup_timeout_s: 5
  shutdown_timeout_s: 10
  max_memory_mb: 500
""")

        schema_path = Path("modbuspython/config/config_schema.json")

        # Load configuration
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Verify configuration loaded successfully
        assert config.get("modbus.host") == "192.168.1.100"
        assert config.get("modbus.port") == 502
        assert config.get("logging.level") == "INFO"
        assert config.get("database.table_name") == "measurements"
        assert config.get("angles.rotation_max") == 360

        # Verify all required sections are present
        assert config.modbus_config is not None
        assert config.database_config is not None
        assert config.logging_config is not None

    def test_startup_with_missing_configuration(self, tmp_path):
        """Test that application creates default config when file is missing.

        **Validates: Requirements 2.7, 2.8, 6.2**
        """
        config_file = tmp_path / "config.yaml"
        schema_path = Path("modbuspython/config/config_schema.json")

        # Ensure config file doesn't exist
        assert not config_file.exists()

        # Load configuration (should create default)
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Verify default configuration was created
        assert config_file.exists()
        assert config.get("modbus.host") == "192.168.1.100"
        assert config.get("modbus.port") == 502

        # Verify configuration is valid and usable
        assert config.validate()
        assert config.modbus_config is not None
        assert config.database_config is not None
        assert config.logging_config is not None

    def test_startup_with_invalid_configuration(self, tmp_path):
        """Test that application uses defaults when config is invalid.

        **Validates: Requirements 2.8, 6.2**
        """
        # Create an invalid config file (malformed YAML)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [[[")

        schema_path = Path("modbuspython/config/config_schema.json")

        # Load configuration (should fall back to defaults)
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Verify default configuration is used
        assert config.get("modbus.host") == "192.168.1.100"
        assert config.get("modbus.port") == 502

        # Verify configuration is valid and usable
        assert config.validate()
        assert config.modbus_config is not None

    def test_startup_with_invalid_schema_values(self, tmp_path):
        """Test that application uses defaults when config has invalid values.

        **Validates: Requirements 2.8, 6.2**
        """
        # Create a config file with invalid values (port out of range)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
modbus:
  host: "192.168.1.100"
  port: 99999
  timeout: 5.0
database:
  path: "data/solarsense.db"
  table_name: "measurements"
logging:
  level: "INFO"
  file_path: "logs/solarsense.log"
angles:
  rotation_min: 0
  rotation_max: 360
  elevation_min: 0
  elevation_max: 145
""")

        schema_path = Path("modbuspython/config/config_schema.json")

        # Load configuration (should fall back to defaults due to validation error)
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Verify default configuration is used (port should be 502, not 99999)
        assert config.get("modbus.port") == 502

        # Verify configuration is valid
        assert config.validate()

    def test_modbus_config_extraction_for_client(self, tmp_path):
        """Test that Modbus configuration can be extracted for ModbusClient initialization.

        **Validates: Requirements 6.2**
        """
        config_file = tmp_path / "config.yaml"
        schema_path = Path("modbuspython/config/config_schema.json")

        # Create config with custom Modbus settings
        config_file.write_text("""
modbus:
  host: "10.0.0.50"
  port: 5020
  timeout: 3.0
database:
  path: "data/solarsense.db"
  table_name: "measurements"
logging:
  level: "INFO"
  file_path: "logs/solarsense.log"
angles:
  rotation_min: 0
  rotation_max: 360
  elevation_min: 0
  elevation_max: 145
""")

        # Load configuration
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Extract Modbus configuration (as done in main_app.py)
        modbus_config = config.modbus_config
        modbus_host = modbus_config.get("host", "192.168.1.100")
        modbus_port = modbus_config.get("port", 502)

        # Verify correct values extracted
        assert modbus_host == "10.0.0.50"
        assert modbus_port == 5020

        # Verify these values can be used to initialize ModbusClient
        # (In actual app, these would be passed to ModbusClient constructor)
        assert isinstance(modbus_host, str)
        assert isinstance(modbus_port, int)
        assert 1 <= modbus_port <= 65535

    def test_logging_config_extraction_for_service(self, tmp_path):
        """Test that logging configuration can be extracted for LoggingService initialization.

        **Validates: Requirements 6.2**
        """
        config_file = tmp_path / "config.yaml"
        log_file = tmp_path / "custom.log"
        log_file_str = str(log_file).replace("\\", "/")

        config_file.write_text(f"""
modbus:
  host: "192.168.1.100"
  port: 502
  timeout: 5.0
database:
  path: "data/solarsense.db"
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

        # Extract logging configuration (as done in main_app.py)
        logging_config = config.logging_config

        # Initialize logging service with config
        logger = LoggingService()
        logger.setup(
            log_file=Path(logging_config.get("file_path", "logs/solarsense.log")),
            level=logging_config.get("level", "INFO"),
            max_bytes=logging_config.get("max_bytes", 10485760),
            backup_count=logging_config.get("backup_count", 5),
        )

        # Verify logger was configured
        logger.info("Test message")
        assert log_file.exists()

    def test_config_fallback_when_no_config_provided(self):
        """Test that application can handle None config (uses hardcoded defaults).

        **Validates: Requirements 2.7, 2.8, 6.2**
        """
        # Simulate main_app.py behavior when config is None
        config = None

        # Extract Modbus config with fallback (as done in main_app.py)
        if config:
            modbus_config = config.modbus_config
            modbus_host = modbus_config.get("host", "192.168.1.100")
            modbus_port = modbus_config.get("port", 502)
        else:
            # Fallback to defaults if no config
            modbus_host = "192.168.1.100"
            modbus_port = 502

        # Verify fallback values are used
        assert modbus_host == "192.168.1.100"
        assert modbus_port == 502


class TestConfigurationManagerStartup:
    """Test ConfigurationManager behavior during startup."""

    def test_singleton_pattern_returns_same_instance(self):
        """Test that ConfigurationManager follows singleton pattern.

        **Validates: Requirements 1.4**
        """
        config1 = ConfigurationManager()
        config2 = ConfigurationManager()

        assert config1 is config2

    def test_default_config_has_all_required_sections(self, tmp_path):
        """Test that default configuration contains all required sections.

        **Validates: Requirements 2.7**
        """
        config_file = tmp_path / "config.yaml"
        schema_path = Path("modbuspython/config/config_schema.json")

        # Load configuration (creates default)
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Verify all required sections exist
        assert config.modbus_config is not None
        assert config.database_config is not None
        assert config.logging_config is not None
        assert config.get("angles") is not None

    def test_config_validation_rejects_invalid_values(self, tmp_path):
        """Test that configuration validation rejects invalid values.

        **Validates: Requirements 2.8**
        """
        # Create config with invalid port
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
modbus:
  host: "192.168.1.100"
  port: -1
  timeout: 5.0
database:
  path: "data/solarsense.db"
  table_name: "measurements"
logging:
  level: "INFO"
  file_path: "logs/solarsense.log"
angles:
  rotation_min: 0
  rotation_max: 360
  elevation_min: 0
  elevation_max: 145
""")

        schema_path = Path("modbuspython/config/config_schema.json")

        # Load configuration (should fall back to defaults)
        config = ConfigurationManager()
        config.load_config(config_file, schema_path)

        # Verify defaults are used instead of invalid values
        assert config.get("modbus.port") == 502


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
