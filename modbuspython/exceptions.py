"""
Custom exception hierarchy for SolarSense SCADA application.

This module defines a comprehensive exception hierarchy that enables better error
handling, logging, and recovery strategies throughout the application.

Exception Hierarchy:
    SolarSenseException (base)
    ├── ConfigurationError
    ├── ValidationError
    ├── ModbusConnectionError
    ├── ModbusOperationError
    ├── DavisConnectionError
    ├── DavisProtocolError
    ├── DavisTransportError
    ├── DatabaseError
    └── MigrationError

Requirements: 4.6, 4.7
"""


class SolarSenseException(Exception):
    """
    Base exception class for all SolarSense SCADA exceptions.

    All custom exceptions in the application should inherit from this class
    to enable centralized exception handling and logging.

    Attributes:
        message: Human-readable error message
        details: Optional dictionary with additional error context
    """

    def __init__(self, message: str, details: dict = None):  # type: ignore[assignment]
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ConfigurationError(SolarSenseException):
    """
    Exception raised for configuration-related errors.

    This includes errors in loading, parsing, or validating configuration files,
    as well as missing required configuration values.

    Examples:
        - Configuration file not found
        - Invalid YAML/JSON syntax
        - Schema validation failure
        - Missing required configuration keys
    """

    pass


class ValidationError(SolarSenseException):
    """
    Exception raised for input validation errors.

    This includes validation failures for user inputs, configuration values,
    or any data that doesn't meet expected constraints.

    Examples:
        - Angle values out of valid range
        - Invalid IP address format
        - Invalid port number
        - SQL injection attempt detected
    """

    pass


class ModbusConnectionError(SolarSenseException):
    """
    Exception raised for Modbus connection failures.

    This includes errors establishing or maintaining a connection to the
    Modbus device (ESP8266).

    Examples:
        - Cannot connect to device IP
        - Connection timeout
        - Connection lost during operation
        - Device not responding
    """

    pass


class ModbusOperationError(SolarSenseException):
    """
    Exception raised for Modbus operation failures.

    This includes errors during read/write operations on Modbus registers,
    after a connection has been successfully established.

    Examples:
        - Failed to read holding register
        - Failed to write holding register
        - Invalid register address
        - Device returned error response
    """

    pass


class DavisConnectionError(SolarSenseException):
    """Raised when the Davis weather station cannot be reached or configured."""

    pass


class DavisProtocolError(SolarSenseException):
    """Raised when a Davis packet does not match the expected protocol format."""

    pass


class DavisTransportError(SolarSenseException):
    """Raised when a Davis serial or TCP transport fails while reading or writing."""

    pass


class DatabaseError(SolarSenseException):
    """
    Exception raised for database operation failures.

    This includes errors in SQLite operations such as connection, queries,
    transactions, or data integrity issues.

    Examples:
        - Cannot open database file
        - SQL query execution failure
        - Transaction commit/rollback failure
        - Database file corruption
        - Permission denied on database file
    """

    pass


class MigrationError(SolarSenseException):
    """
    Exception raised for database migration failures.

    This includes errors during schema migrations, version tracking,
    or migration rollback operations.

    Examples:
        - Migration script execution failure
        - Cannot determine current schema version
        - Migration rollback failure
        - Incompatible schema version
    """

    pass
