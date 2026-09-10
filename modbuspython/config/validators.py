"""Configuration validators for Nexo Solar.

This module provides validation functions for configuration values
to ensure they meet the required constraints before being used.
"""

from typing import Tuple, Optional
import re
import ipaddress


def validate_ip_address(ip: str) -> Tuple[bool, Optional[str]]:
    """Validate IP address format.

    Args:
        ip: IP address string to validate

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_ip_address("192.168.1.100")
        (True, None)
        >>> validate_ip_address("invalid")
        (False, "Invalid IP address format: invalid")
    """
    try:
        ipaddress.ip_address(ip)
        return True, None
    except ValueError:
        return False, f"Invalid IP address format: {ip}"


def validate_port(port: int) -> Tuple[bool, Optional[str]]:
    """Validate port number.

    Args:
        port: Port number to validate

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_port(502)
        (True, None)
        >>> validate_port(70000)
        (False, "Port must be between 1 and 65535, got 70000")
    """
    if not isinstance(port, int):
        return False, f"Port must be integer, got {type(port).__name__}"  # type: ignore[unreachable]

    if not (1 <= port <= 65535):
        return False, f"Port must be between 1 and 65535, got {port}"

    return True, None


def validate_angle(angle: float, min_value: float, max_value: float, angle_type: str = "angle") -> Tuple[bool, Optional[str]]:
    """Validate angle value within specified range.

    Args:
        angle: Angle value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        angle_type: Type of angle for error messages (e.g., "rotation", "elevation")

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_angle(180.0, 0, 360, "rotation")
        (True, None)
        >>> validate_angle(400.0, 0, 360, "rotation")
        (False, "Rotation angle must be between 0 and 360, got 400.0")
    """
    if not isinstance(angle, (int, float)):
        return False, f"{angle_type.capitalize()} angle must be numeric, got {type(angle).__name__}"  # type: ignore[unreachable]

    if not (min_value <= angle <= max_value):
        return False, f"{angle_type.capitalize()} angle must be between {min_value} and {max_value}, got {angle}"

    return True, None


def validate_sql_identifier(identifier: str) -> Tuple[bool, Optional[str]]:
    """Validate SQL identifier (table name, column name).

    Ensures the identifier follows SQL naming rules and is not a SQL keyword.

    Args:
        identifier: SQL identifier to validate

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_sql_identifier("measurements")
        (True, None)
        >>> validate_sql_identifier("SELECT")
        (False, "SQL identifier cannot be a keyword: SELECT")
    """
    SQL_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
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
    }

    if not isinstance(identifier, str):
        return False, f"SQL identifier must be string, got {type(identifier).__name__}"  # type: ignore[unreachable]

    if not SQL_IDENTIFIER_PATTERN.match(identifier):
        return False, f"Invalid SQL identifier format: {identifier}"

    if identifier.upper() in SQL_KEYWORDS:
        return False, f"SQL identifier cannot be a keyword: {identifier}"

    return True, None


def validate_file_path(path: str) -> Tuple[bool, Optional[str]]:
    """Validate file path format.

    Args:
        path: File path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(path, str):
        return False, f"File path must be string, got {type(path).__name__}"  # type: ignore[unreachable]

    if not path.strip():
        return False, "File path cannot be empty"

    # Check for invalid characters (basic validation)
    invalid_chars = ["<", ">", "|", "\0"]
    for char in invalid_chars:
        if char in path:
            return False, f"File path contains invalid character: {char}"

    return True, None


def validate_timeout(timeout: float) -> Tuple[bool, Optional[str]]:
    """Validate timeout value.

    Args:
        timeout: Timeout value in seconds

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(timeout, (int, float)):
        return False, f"Timeout must be numeric, got {type(timeout).__name__}"  # type: ignore[unreachable]

    if timeout <= 0:
        return False, f"Timeout must be positive, got {timeout}"

    if timeout > 300:  # 5 minutes max
        return False, f"Timeout too large (max 300s), got {timeout}"

    return True, None


def validate_log_level(level: str) -> Tuple[bool, Optional[str]]:
    """Validate logging level.

    Args:
        level: Logging level string

    Returns:
        Tuple of (is_valid, error_message)
    """
    VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    if not isinstance(level, str):
        return False, f"Log level must be string, got {type(level).__name__}"  # type: ignore[unreachable]

    if level.upper() not in VALID_LEVELS:
        return False, f"Invalid log level: {level}. Must be one of {VALID_LEVELS}"

    return True, None
