"""
Unit tests for custom exception hierarchy.

Tests the Nexo Solar custom exception classes to ensure proper inheritance,
initialization, and string representation.

Requirements: 4.6, 4.7
"""

import pytest
from modbuspython.exceptions import (
    NexoSolarException,
    ConfigurationError,
    ValidationError,
    ModbusConnectionError,
    ModbusOperationError,
    DatabaseError,
    MigrationError,
)


class TestNexoSolarException:
    """Tests for the base NexoSolarException class."""

    def test_basic_initialization(self):
        """Test basic exception initialization with message only."""
        exc = NexoSolarException("Test error")
        assert exc.message == "Test error"
        assert exc.details == {}
        assert str(exc) == "Test error"

    def test_initialization_with_details(self):
        """Test exception initialization with message and details."""
        details = {"key": "value", "code": 123}
        exc = NexoSolarException("Test error", details)
        assert exc.message == "Test error"
        assert exc.details == details
        assert "key=value" in str(exc)
        assert "code=123" in str(exc)

    def test_is_exception(self):
        """Test that NexoSolarException inherits from Exception."""
        exc = NexoSolarException("Test")
        assert isinstance(exc, Exception)

    def test_can_be_raised(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(NexoSolarException) as exc_info:
            raise NexoSolarException("Test error")
        assert exc_info.value.message == "Test error"


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_inheritance(self):
        """Test that ConfigurationError inherits from NexoSolarException."""
        exc = ConfigurationError("Config error")
        assert isinstance(exc, NexoSolarException)
        assert isinstance(exc, Exception)

    def test_with_details(self):
        """Test ConfigurationError with details."""
        exc = ConfigurationError("Invalid config", {"file": "config.yaml"})
        assert "Invalid config" in str(exc)
        assert "file=config.yaml" in str(exc)

    def test_can_be_caught_as_base(self):
        """Test that ConfigurationError can be caught as NexoSolarException."""
        with pytest.raises(NexoSolarException):
            raise ConfigurationError("Test")


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_inheritance(self):
        """Test that ValidationError inherits from NexoSolarException."""
        exc = ValidationError("Validation failed")
        assert isinstance(exc, NexoSolarException)
        assert isinstance(exc, Exception)

    def test_with_validation_details(self):
        """Test ValidationError with validation details."""
        exc = ValidationError("Invalid angle", {"value": 400, "max": 360})
        assert "Invalid angle" in str(exc)
        assert "value=400" in str(exc)
        assert "max=360" in str(exc)


class TestModbusConnectionError:
    """Tests for ModbusConnectionError exception."""

    def test_inheritance(self):
        """Test that ModbusConnectionError inherits from NexoSolarException."""
        exc = ModbusConnectionError("Connection failed")
        assert isinstance(exc, NexoSolarException)
        assert isinstance(exc, Exception)

    def test_with_connection_details(self):
        """Test ModbusConnectionError with connection details."""
        exc = ModbusConnectionError("Cannot connect", {"ip": "192.168.1.100", "port": 502})
        assert "Cannot connect" in str(exc)
        assert "ip=192.168.1.100" in str(exc)
        assert "port=502" in str(exc)


class TestModbusOperationError:
    """Tests for ModbusOperationError exception."""

    def test_inheritance(self):
        """Test that ModbusOperationError inherits from NexoSolarException."""
        exc = ModbusOperationError("Read failed")
        assert isinstance(exc, NexoSolarException)
        assert isinstance(exc, Exception)

    def test_with_operation_details(self):
        """Test ModbusOperationError with operation details."""
        exc = ModbusOperationError("Read failed", {"register": 100, "operation": "read"})
        assert "Read failed" in str(exc)
        assert "register=100" in str(exc)
        assert "operation=read" in str(exc)


class TestDatabaseError:
    """Tests for DatabaseError exception."""

    def test_inheritance(self):
        """Test that DatabaseError inherits from NexoSolarException."""
        exc = DatabaseError("Query failed")
        assert isinstance(exc, NexoSolarException)
        assert isinstance(exc, Exception)

    def test_with_database_details(self):
        """Test DatabaseError with database details."""
        exc = DatabaseError("Cannot open database", {"path": "/path/to/db.sqlite"})
        assert "Cannot open database" in str(exc)
        assert "path=/path/to/db.sqlite" in str(exc)


class TestMigrationError:
    """Tests for MigrationError exception."""

    def test_inheritance(self):
        """Test that MigrationError inherits from NexoSolarException."""
        exc = MigrationError("Migration failed")
        assert isinstance(exc, NexoSolarException)
        assert isinstance(exc, Exception)

    def test_with_migration_details(self):
        """Test MigrationError with migration details."""
        exc = MigrationError("Cannot apply migration", {"version": "v2", "error": "syntax error"})
        assert "Cannot apply migration" in str(exc)
        assert "version=v2" in str(exc)
        assert "error=syntax error" in str(exc)


class TestExceptionHierarchy:
    """Tests for the overall exception hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from NexoSolarException."""
        exceptions = [
            ConfigurationError("test"),
            ValidationError("test"),
            ModbusConnectionError("test"),
            ModbusOperationError("test"),
            DatabaseError("test"),
            MigrationError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, NexoSolarException)
            assert isinstance(exc, Exception)

    def test_can_catch_all_with_base(self):
        """Test that all custom exceptions can be caught with base class."""
        exceptions = [
            ConfigurationError,
            ValidationError,
            ModbusConnectionError,
            ModbusOperationError,
            DatabaseError,
            MigrationError,
        ]

        for exc_class in exceptions:
            with pytest.raises(NexoSolarException):
                raise exc_class("Test error")

    def test_specific_exception_types_are_distinct(self):
        """Test that different exception types can be distinguished."""
        config_exc = ConfigurationError("test")
        validation_exc = ValidationError("test")

        assert type(config_exc) != type(validation_exc)
        assert isinstance(config_exc, ConfigurationError)
        assert not isinstance(config_exc, ValidationError)
        assert isinstance(validation_exc, ValidationError)
        assert not isinstance(validation_exc, ConfigurationError)
