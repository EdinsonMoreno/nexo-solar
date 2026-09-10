"""Validation service for Nexo Solar.

This module provides input validation and sanitization for all user inputs
across the application. It implements an abstract base class pattern with
specific validators for different types of inputs.

Requirements validated: 7.1, 7.2, 7.3, 7.4
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
import re
import ipaddress


class Validator(ABC):
    """Abstract base class for all validators.

    All validators must implement the validate() method which returns
    a tuple of (is_valid, error_message).
    """

    @abstractmethod
    def validate(self, value) -> Tuple[bool, Optional[str]]:
        """Validate the given value.

        Args:
            value: The value to validate

        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is None.
        """
        pass


class AngleValidator(Validator):
    """Validator for angle values with configurable range constraints.

    Validates that angle values are numeric and within the specified range.
    Commonly used for rotation angles [0, 360] and elevation angles [0, 145].
    """

    def __init__(self, min_value: float, max_value: float, angle_type: str = "angle"):
        """Initialize the angle validator.

        Args:
            min_value: Minimum allowed angle value (inclusive)
            max_value: Maximum allowed angle value (inclusive)
            angle_type: Type of angle for error messages (e.g., "rotation", "elevation")
        """
        self.min_value = min_value
        self.max_value = max_value
        self.angle_type = angle_type

    def validate(self, value) -> Tuple[bool, Optional[str]]:
        """Validate angle value is numeric and within range.

        Args:
            value: The angle value to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> validator = AngleValidator(0, 360, "rotation")
            >>> validator.validate(180.0)
            (True, None)
            >>> validator.validate(400.0)
            (False, "Rotation angle must be between 0 and 360, got 400.0")
        """
        if not isinstance(value, (int, float)):
            return False, f"{self.angle_type.capitalize()} angle must be numeric, got {type(value).__name__}"

        if not (self.min_value <= value <= self.max_value):
            return False, (
                f"{self.angle_type.capitalize()} angle must be between " f"{self.min_value} and {self.max_value}, got {value}"
            )

        return True, None


class IPAddressValidator(Validator):
    """Validator for IPv4 address format.

    Validates that a string is a valid IPv4 address using Python's ipaddress module.
    """

    def validate(self, value) -> Tuple[bool, Optional[str]]:
        """Validate IPv4 address format.

        Args:
            value: The IP address string to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> validator = IPAddressValidator()
            >>> validator.validate("192.168.1.100")
            (True, None)
            >>> validator.validate("invalid")
            (False, "Invalid IP address format: invalid")
            >>> validator.validate("999.999.999.999")
            (False, "Invalid IP address format: 999.999.999.999")
        """
        if not isinstance(value, str):
            return False, f"IP address must be string, got {type(value).__name__}"

        try:
            # Validate as IPv4 address
            ip = ipaddress.ip_address(value)
            # Ensure it's IPv4, not IPv6
            if not isinstance(ip, ipaddress.IPv4Address):
                return False, f"Only IPv4 addresses are supported, got IPv6: {value}"
            return True, None
        except ValueError:
            return False, f"Invalid IP address format: {value}"


class PortValidator(Validator):
    """Validator for network port numbers.

    Validates that a port number is an integer within the valid range [1, 65535].
    """

    def validate(self, value) -> Tuple[bool, Optional[str]]:
        """Validate port number is integer and within valid range.

        Args:
            value: The port number to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> validator = PortValidator()
            >>> validator.validate(502)
            (True, None)
            >>> validator.validate(0)
            (False, "Port must be between 1 and 65535, got 0")
            >>> validator.validate(70000)
            (False, "Port must be between 1 and 65535, got 70000")
        """
        if not isinstance(value, int):
            return False, f"Port must be integer, got {type(value).__name__}"

        if not (1 <= value <= 65535):
            return False, f"Port must be between 1 and 65535, got {value}"

        return True, None


class SQLIdentifierValidator(Validator):
    """Validator for SQL identifiers with injection prevention.

    Validates that SQL identifiers (table names, column names) follow SQL naming
    rules and are not SQL keywords. This helps prevent SQL injection attacks.

    Rules:
    - Must start with letter or underscore
    - Can contain letters, numbers, and underscores
    - Cannot be a SQL keyword
    """

    # Pattern for valid SQL identifiers
    SQL_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    # Common SQL keywords that should not be used as identifiers
    SQL_KEYWORDS = {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TABLE",
        "FROM",
        "WHERE",
        "AND",
        "OR",
        "NOT",
        "NULL",
        "TRUE",
        "FALSE",
        "JOIN",
        "INNER",
        "OUTER",
        "LEFT",
        "RIGHT",
        "ON",
        "AS",
        "ORDER",
        "BY",
        "GROUP",
        "HAVING",
        "LIMIT",
        "OFFSET",
        "UNION",
        "INTERSECT",
        "EXCEPT",
        "INDEX",
        "VIEW",
        "TRIGGER",
        "PROCEDURE",
        "FUNCTION",
        "DATABASE",
        "SCHEMA",
    }

    def validate(self, value) -> Tuple[bool, Optional[str]]:
        """Validate SQL identifier format and prevent injection.

        Args:
            value: The SQL identifier to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> validator = SQLIdentifierValidator()
            >>> validator.validate("measurements")
            (True, None)
            >>> validator.validate("user_data_2024")
            (True, None)
            >>> validator.validate("SELECT")
            (False, "SQL identifier cannot be a keyword: SELECT")
            >>> validator.validate("table-name")
            (False, "Invalid SQL identifier format: table-name")
            >>> validator.validate("123invalid")
            (False, "Invalid SQL identifier format: 123invalid")
        """
        if not isinstance(value, str):
            return False, f"SQL identifier must be string, got {type(value).__name__}"

        if not value.strip():
            return False, "SQL identifier cannot be empty"

        # Check format
        if not self.SQL_IDENTIFIER_PATTERN.match(value):
            return False, f"Invalid SQL identifier format: {value}"

        # Check against keywords
        if value.upper() in self.SQL_KEYWORDS:
            return False, f"SQL identifier cannot be a keyword: {value}"

        return True, None


class ValidationService:
    """Facade for all validation operations in Nexo Solar.

    This service aggregates all validators and provides a unified interface
    for validating different types of inputs. It loads angle limits from
    configuration and provides methods for common validation tasks.

    Requirements validated: 7.5, 7.6
    """

    def __init__(self, config_manager=None):
        """Initialize the validation service.

        Args:
            config_manager: Optional ConfigurationManager instance. If None,
                           will use default angle limits.
        """
        # Load angle limits from configuration
        if config_manager:
            rotation_min = config_manager.get("angles.rotation_min", 0)
            rotation_max = config_manager.get("angles.rotation_max", 360)
            elevation_min = config_manager.get("angles.elevation_min", 0)
            elevation_max = config_manager.get("angles.elevation_max", 145)
        else:
            # Default values if no config manager provided
            rotation_min = 0
            rotation_max = 360
            elevation_min = 0
            elevation_max = 145

        # Initialize validators
        self._rotation_validator = AngleValidator(rotation_min, rotation_max, "rotation")
        self._elevation_validator = AngleValidator(elevation_min, elevation_max, "elevation")
        self._ip_validator = IPAddressValidator()
        self._port_validator = PortValidator()
        self._sql_validator = SQLIdentifierValidator()

    def validate_rotation(self, value: float) -> Tuple[bool, Optional[str]]:
        """Validate rotation angle value.

        Args:
            value: The rotation angle to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> service = ValidationService()
            >>> service.validate_rotation(180.0)
            (True, None)
            >>> service.validate_rotation(400.0)
            (False, "Rotation angle must be between 0 and 360, got 400.0")
        """
        return self._rotation_validator.validate(value)

    def validate_elevation(self, value: float) -> Tuple[bool, Optional[str]]:
        """Validate elevation angle value.

        Args:
            value: The elevation angle to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> service = ValidationService()
            >>> service.validate_elevation(45.0)
            (True, None)
            >>> service.validate_elevation(200.0)
            (False, "Elevation angle must be between 0 and 145, got 200.0")
        """
        return self._elevation_validator.validate(value)

    def validate_ip_address(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate IPv4 address format.

        Args:
            value: The IP address string to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> service = ValidationService()
            >>> service.validate_ip_address("192.168.1.100")
            (True, None)
            >>> service.validate_ip_address("invalid")
            (False, "Invalid IP address format: invalid")
        """
        return self._ip_validator.validate(value)

    def validate_port(self, value: int) -> Tuple[bool, Optional[str]]:
        """Validate network port number.

        Args:
            value: The port number to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> service = ValidationService()
            >>> service.validate_port(502)
            (True, None)
            >>> service.validate_port(70000)
            (False, "Port must be between 1 and 65535, got 70000")
        """
        return self._port_validator.validate(value)

    def validate_sql_identifier(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate SQL identifier and prevent injection.

        Args:
            value: The SQL identifier to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> service = ValidationService()
            >>> service.validate_sql_identifier("measurements")
            (True, None)
            >>> service.validate_sql_identifier("SELECT")
            (False, "SQL identifier cannot be a keyword: SELECT")
        """
        return self._sql_validator.validate(value)

    def sanitize_string(self, value: str, max_length: int = 255) -> str:
        """Sanitize string input by removing dangerous characters.

        This method removes or escapes potentially dangerous characters from
        user input strings to prevent injection attacks and ensure data safety.

        Args:
            value: The string to sanitize
            max_length: Maximum allowed length (default: 255)

        Returns:
            Sanitized string

        Example:
            >>> service = ValidationService()
            >>> service.sanitize_string("normal text")
            'normal text'
            >>> service.sanitize_string("text with <script>alert('xss')</script>")
            'text with scriptalert(xss)/script'
            >>> service.sanitize_string("a" * 300, max_length=10)
            'aaaaaaaaaa'
        """
        if not isinstance(value, str):
            return str(value)  # type: ignore[unreachable]

        # Truncate to max length
        sanitized = value[:max_length]

        # Remove potentially dangerous characters
        # Remove HTML/XML tags
        sanitized = re.sub(r"<[^>]*>", "", sanitized)

        # Remove null bytes
        sanitized = sanitized.replace("\x00", "")

        # Remove control characters except newline, tab, and carriage return
        sanitized = "".join(char for char in sanitized if char in "\n\r\t" or not (0 <= ord(char) < 32))

        # Strip leading/trailing whitespace
        sanitized = sanitized.strip()

        return sanitized
