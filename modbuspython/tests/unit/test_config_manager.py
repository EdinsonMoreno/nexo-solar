"""Unit tests for ConfigurationManager.

Tests cover:
- Loading valid YAML configuration
- Loading valid JSON configuration
- Creating default configuration when file is missing
- Fallback to defaults when configuration is invalid
- Schema validation
- Dot notation access for nested values
"""

import pytest
import json
import yaml
from pathlib import Path
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modbuspython.config.config_manager import ConfigurationManager


class TestConfigurationManager:
    """Unit tests for ConfigurationManager class."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton instance before each test."""
        ConfigurationManager._instance = None
        yield
        ConfigurationManager._instance = None

    @pytest.fixture
    def schema_path(self, tmp_path):
        """Create a temporary schema file for testing."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["modbus", "database", "logging", "angles"],
            "properties": {
                "modbus": {
                    "type": "object",
                    "required": ["host", "port", "timeout"],
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                        "timeout": {"type": "number", "minimum": 0.1, "maximum": 30.0},
                    },
                },
                "database": {
                    "type": "object",
                    "required": ["path", "table_name"],
                    "properties": {"path": {"type": "string"}, "table_name": {"type": "string"}},
                },
                "logging": {
                    "type": "object",
                    "properties": {"level": {"type": "string"}, "file_path": {"type": "string"}},
                },
                "angles": {
                    "type": "object",
                    "properties": {
                        "rotation_min": {"type": "number"},
                        "rotation_max": {"type": "number"},
                        "elevation_min": {"type": "number"},
                        "elevation_max": {"type": "number"},
                    },
                },
            },
        }

        schema_file = tmp_path / "test_schema.json"
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(schema, f)

        return schema_file

    # Test: Loading valid YAML configuration
    def test_load_valid_yaml_config(self, tmp_path, schema_path):
        """Test loading valid YAML configuration file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": 502, "timeout": 5.0},
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {"level": "INFO", "file_path": "logs/test.log"},
            "angles": {"rotation_min": 0, "rotation_max": 360, "elevation_min": 0, "elevation_max": 145},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        assert manager.get("modbus.host") == "192.168.1.100"
        assert manager.get("modbus.port") == 502
        assert manager.get("modbus.timeout") == 5.0
        assert manager.get("database.path") == "data/test.db"
        assert manager.get("database.table_name") == "measurements"

    # Test: Loading valid JSON configuration
    def test_load_valid_json_config(self, tmp_path, schema_path):
        """Test loading valid JSON configuration file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "modbus": {"host": "10.0.0.50", "port": 5020, "timeout": 3.5},
            "database": {"path": "data/production.db", "table_name": "sensor_data"},
            "logging": {"level": "DEBUG", "file_path": "logs/production.log"},
            "angles": {"rotation_min": 10, "rotation_max": 350, "elevation_min": 5, "elevation_max": 140},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        assert manager.get("modbus.host") == "10.0.0.50"
        assert manager.get("modbus.port") == 5020
        assert manager.get("modbus.timeout") == 3.5
        assert manager.get("database.path") == "data/production.db"
        assert manager.get("logging.level") == "DEBUG"

    # Test: Creating default configuration when file is missing
    def test_load_missing_config_creates_default(self, tmp_path, schema_path):
        """Test that missing config file triggers default creation."""
        config_file = tmp_path / "missing.yaml"

        # Ensure file doesn't exist
        assert not config_file.exists()

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # File should now exist
        assert config_file.exists()

        # Should have default values
        assert manager.get("modbus.host") is not None
        assert manager.get("modbus.port") is not None
        assert manager.get("database.path") is not None
        assert manager.get("logging.level") is not None

    # Test: Fallback to defaults when configuration is invalid (malformed YAML)
    def test_load_invalid_yaml_uses_defaults(self, tmp_path, schema_path):
        """Test that invalid YAML falls back to defaults."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should have loaded defaults
        assert manager.get("modbus.host") == "192.168.1.100"
        assert manager.get("modbus.port") == 502
        assert manager.get("database.table_name") == "measurements"

    # Test: Fallback to defaults when configuration is invalid (malformed JSON)
    def test_load_invalid_json_uses_defaults(self, tmp_path, schema_path):
        """Test that invalid JSON falls back to defaults."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text('{"modbus": {"host": "192.168.1.1", "port": }')

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should have loaded defaults
        assert manager.get("modbus.host") == "192.168.1.100"
        assert manager.get("database.path") == "data/solarsense.db"

    # Test: Schema validation - missing required fields
    def test_validation_missing_required_fields(self, tmp_path, schema_path):
        """Test that configuration with missing required fields fails validation."""
        config_file = tmp_path / "incomplete.yaml"
        config_data = {
            "modbus": {
                "host": "192.168.1.100"
                # Missing required 'port' and 'timeout'
            },
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should fall back to defaults due to validation failure
        assert manager.get("modbus.port") == 502
        assert manager.get("modbus.timeout") == 5.0

    # Test: Schema validation - invalid value types
    def test_validation_invalid_value_types(self, tmp_path, schema_path):
        """Test that configuration with invalid value types fails validation."""
        config_file = tmp_path / "wrong_types.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": "not_a_number", "timeout": 5.0},  # Should be integer
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should fall back to defaults
        assert manager.get("modbus.port") == 502

    # Test: Schema validation - out of range values
    def test_validation_out_of_range_values(self, tmp_path, schema_path):
        """Test that configuration with out-of-range values fails validation."""
        config_file = tmp_path / "out_of_range.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": 70000, "timeout": 5.0},  # Exceeds maximum of 65535
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should fall back to defaults
        assert manager.get("modbus.port") == 502

    # Test: Dot notation access - simple nested values
    def test_get_with_dot_notation_simple(self, tmp_path, schema_path):
        """Test getting nested values with dot notation."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": 502, "timeout": 5.0},
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        assert manager.get("modbus.host") == "192.168.1.100"
        assert manager.get("modbus.port") == 502
        assert manager.get("database.table_name") == "measurements"

    # Test: Dot notation access - deeply nested values
    def test_get_with_dot_notation_deep(self, tmp_path, schema_path):
        """Test getting deeply nested values with dot notation."""
        manager = ConfigurationManager()
        manager._config = {"level1": {"level2": {"level3": {"value": "deep_value"}}}}

        assert manager.get("level1.level2.level3.value") == "deep_value"

    # Test: Dot notation access - nonexistent keys with default
    def test_get_with_dot_notation_default(self, tmp_path, schema_path):
        """Test getting nonexistent keys returns default value."""
        manager = ConfigurationManager()
        manager._config = {"modbus": {"host": "192.168.1.100"}}

        assert manager.get("nonexistent.key", "default_value") == "default_value"
        assert manager.get("modbus.nonexistent", 999) == 999
        assert manager.get("modbus.host.invalid") is None

    # Test: Set method with dot notation
    def test_set_with_dot_notation(self):
        """Test setting values with dot notation."""
        manager = ConfigurationManager()
        manager._config = {}

        manager.set("modbus.host", "10.0.0.1")
        manager.set("modbus.port", 5020)
        manager.set("database.path", "custom.db")

        assert manager.get("modbus.host") == "10.0.0.1"
        assert manager.get("modbus.port") == 5020
        assert manager.get("database.path") == "custom.db"

    # Test: Validate method
    def test_validate_method(self, tmp_path, schema_path):
        """Test the validate method returns correct boolean."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": 502, "timeout": 5.0},
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should be valid
        assert manager.validate() is True

        # Make it invalid
        manager.set("modbus.port", "not_a_number")
        assert manager.validate() is False

    # Test: Property accessors
    def test_property_accessors(self, tmp_path, schema_path):
        """Test modbus_config, database_config, and logging_config properties."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": 502, "timeout": 5.0},
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {"level": "DEBUG", "file_path": "logs/test.log"},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        modbus_cfg = manager.modbus_config
        assert modbus_cfg["host"] == "192.168.1.100"
        assert modbus_cfg["port"] == 502

        db_cfg = manager.database_config
        assert db_cfg["path"] == "data/test.db"
        assert db_cfg["table_name"] == "measurements"

        log_cfg = manager.logging_config
        assert log_cfg["level"] == "DEBUG"
        assert log_cfg["file_path"] == "logs/test.log"

    # Test: Singleton pattern
    def test_singleton_pattern(self):
        """Test that ConfigurationManager follows singleton pattern."""
        manager1 = ConfigurationManager()
        manager2 = ConfigurationManager()

        assert manager1 is manager2

        # Setting value in one should affect the other
        manager1._config = {"test": "value"}
        assert manager2._config == {"test": "value"}

    # Test: Create default config with YAML format
    def test_create_default_config_yaml(self, tmp_path):
        """Test creating default configuration in YAML format."""
        output_file = tmp_path / "default.yaml"

        manager = ConfigurationManager()
        manager.create_default_config(output_file)

        assert output_file.exists()

        # Verify it's valid YAML
        with open(output_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert "modbus" in config
        assert "database" in config
        assert "logging" in config
        assert "angles" in config
        assert config["modbus"]["host"] == "192.168.1.100"

    # Test: Create default config with JSON format
    def test_create_default_config_json(self, tmp_path):
        """Test creating default configuration in JSON format."""
        output_file = tmp_path / "default.json"

        manager = ConfigurationManager()
        manager.create_default_config(output_file)

        assert output_file.exists()

        # Verify it's valid JSON
        with open(output_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "modbus" in config
        assert "database" in config
        assert config["database"]["table_name"] == "measurements"

    # Test: Reload method
    def test_reload_config(self, tmp_path, schema_path):
        """Test reloading configuration from file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": 502, "timeout": 5.0},
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # Copy schema to same directory
        schema_copy = tmp_path / "config_schema.json"
        with open(schema_path, "r") as src:
            with open(schema_copy, "w") as dst:
                dst.write(src.read())

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_copy)

        assert manager.get("modbus.host") == "192.168.1.100"

        # Modify the file
        config_data["modbus"]["host"] = "10.0.0.50"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # Reload
        manager.reload()

        assert manager.get("modbus.host") == "10.0.0.50"

    # Test: Reload without prior load raises error
    def test_reload_without_load_raises_error(self):
        """Test that reload without prior load raises ConfigurationError."""
        from modbuspython.exceptions import ConfigurationError

        manager = ConfigurationManager()

        with pytest.raises(ConfigurationError, match="No configuration file loaded"):
            manager.reload()

    # Test: Unsupported file format
    def test_unsupported_file_format(self, tmp_path, schema_path):
        """Test that unsupported file format falls back to defaults."""
        config_file = tmp_path / "config.txt"
        config_file.write_text("some text content")

        manager = ConfigurationManager()

        # Should fall back to defaults for unsupported format
        manager.load_config(config_file, schema_path)

        # Verify defaults were loaded
        assert manager.get("modbus.host") == "192.168.1.100"
        assert manager.get("modbus.port") == 502

    # Test: Schema file not found
    def test_schema_file_not_found(self, tmp_path):
        """Test that missing schema file raises ConfigurationError."""
        from modbuspython.exceptions import ConfigurationError

        config_file = tmp_path / "config.yaml"
        schema_file = tmp_path / "nonexistent_schema.json"

        manager = ConfigurationManager()

        with pytest.raises(ConfigurationError, match="Schema file not found"):
            manager.load_config(config_file, schema_file)

    # Test: Validation of IP address in configuration
    def test_validation_invalid_ip_address(self, tmp_path, schema_path):
        """Test that invalid IP address in configuration triggers fallback to defaults."""
        config_file = tmp_path / "invalid_ip.yaml"
        config_data = {
            "modbus": {"host": "999.999.999.999", "port": 502, "timeout": 5.0},  # Invalid IP
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should fall back to defaults due to invalid IP
        assert manager.get("modbus.host") == "192.168.1.100"
        assert manager.get("modbus.port") == 502

    # Test: Validation of port number in configuration
    def test_validation_invalid_port_number(self, tmp_path, schema_path):
        """Test that invalid port number in configuration triggers fallback to defaults."""
        config_file = tmp_path / "invalid_port.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": 0, "timeout": 5.0},  # Invalid port (must be 1-65535)
            "database": {"path": "data/test.db", "table_name": "measurements"},
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should fall back to defaults due to invalid port
        assert manager.get("modbus.port") == 502

    # Test: Validation of SQL table name in configuration
    def test_validation_invalid_sql_identifier(self, tmp_path, schema_path):
        """Test that invalid SQL identifier in configuration triggers fallback to defaults."""
        config_file = tmp_path / "invalid_sql.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": 502, "timeout": 5.0},
            "database": {"path": "data/test.db", "table_name": "SELECT"},  # SQL keyword - invalid identifier
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should fall back to defaults due to invalid SQL identifier
        assert manager.get("database.table_name") == "measurements"

    # Test: Validation of SQL table name with special characters
    def test_validation_sql_identifier_with_special_chars(self, tmp_path, schema_path):
        """Test that SQL identifier with special characters triggers fallback to defaults."""
        config_file = tmp_path / "invalid_sql_chars.yaml"
        config_data = {
            "modbus": {"host": "192.168.1.100", "port": 502, "timeout": 5.0},
            "database": {"path": "data/test.db", "table_name": "table-name"},  # Hyphen not allowed in SQL identifiers
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should fall back to defaults due to invalid SQL identifier
        assert manager.get("database.table_name") == "measurements"

    # Test: Valid configuration passes all validations
    def test_validation_all_valid_values(self, tmp_path, schema_path):
        """Test that valid configuration passes all semantic validations."""
        config_file = tmp_path / "all_valid.yaml"
        config_data = {
            "modbus": {"host": "10.20.30.40", "port": 5020, "timeout": 5.0},  # Valid IP  # Valid port
            "database": {"path": "data/test.db", "table_name": "sensor_readings_2024"},  # Valid SQL identifier
            "logging": {},
            "angles": {},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        manager.load_config(config_file, schema_path)

        # Should keep the configured values (not fall back to defaults)
        assert manager.get("modbus.host") == "10.20.30.40"
        assert manager.get("modbus.port") == 5020
        assert manager.get("database.table_name") == "sensor_readings_2024"
