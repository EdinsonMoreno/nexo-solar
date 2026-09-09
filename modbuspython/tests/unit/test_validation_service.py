"""Unit tests for validation service.

Tests the validator classes in backend/validation_service.py.

Test Coverage Summary:
- AngleValidator: Valid/invalid angles, boundary values, type checking
- IPAddressValidator: Valid/invalid IPs, IPv6 rejection, edge cases
- PortValidator: Valid/invalid ports, boundary values, common ports
- SQLIdentifierValidator: Valid identifiers, SQL keywords, injection attempts, format validation
- ValidationService: Initialization with/without config, sanitize_string with dangerous characters,
  XSS prevention, integration tests for all validators

Requirements validated: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import pytest
from modbuspython.backend.validation_service import (
    AngleValidator,
    IPAddressValidator,
    PortValidator,
    SQLIdentifierValidator,
    ValidationService,
)


class TestAngleValidator:
    """Tests for AngleValidator class."""

    def test_valid_rotation_angle(self):
        """Test validation of valid rotation angles."""
        validator = AngleValidator(0, 360, "rotation")

        assert validator.validate(0) == (True, None)
        assert validator.validate(180.0) == (True, None)
        assert validator.validate(360) == (True, None)

    def test_valid_elevation_angle(self):
        """Test validation of valid elevation angles."""
        validator = AngleValidator(0, 145, "elevation")

        assert validator.validate(0) == (True, None)
        assert validator.validate(72.5) == (True, None)
        assert validator.validate(145) == (True, None)

    def test_invalid_angle_out_of_range(self):
        """Test validation rejects angles outside range."""
        validator = AngleValidator(0, 360, "rotation")

        is_valid, error = validator.validate(400.0)
        assert is_valid is False
        assert "must be between 0 and 360" in error

        is_valid, error = validator.validate(-10)
        assert is_valid is False
        assert "must be between 0 and 360" in error

    def test_invalid_angle_non_numeric(self):
        """Test validation rejects non-numeric values."""
        validator = AngleValidator(0, 360, "rotation")

        is_valid, error = validator.validate("180")
        assert is_valid is False
        assert "must be numeric" in error

        is_valid, error = validator.validate(None)
        assert is_valid is False
        assert "must be numeric" in error

        is_valid, error = validator.validate([180])
        assert is_valid is False
        assert "must be numeric" in error

    def test_angle_boundary_values(self):
        """Test validation at exact boundary values."""
        validator = AngleValidator(0, 360, "rotation")

        # Exact boundaries should be valid
        assert validator.validate(0.0) == (True, None)
        assert validator.validate(360.0) == (True, None)

        # Just outside boundaries should be invalid
        is_valid, error = validator.validate(-0.001)
        assert is_valid is False

        is_valid, error = validator.validate(360.001)
        assert is_valid is False


class TestIPAddressValidator:
    """Tests for IPAddressValidator class."""

    def test_valid_ip_addresses(self):
        """Test validation of valid IPv4 addresses."""
        validator = IPAddressValidator()

        assert validator.validate("192.168.1.100") == (True, None)
        assert validator.validate("10.0.0.1") == (True, None)
        assert validator.validate("172.16.0.1") == (True, None)
        assert validator.validate("127.0.0.1") == (True, None)

    def test_invalid_ip_format(self):
        """Test validation rejects invalid IP formats."""
        validator = IPAddressValidator()

        is_valid, error = validator.validate("invalid")
        assert is_valid is False
        assert "Invalid IP address format" in error

        is_valid, error = validator.validate("999.999.999.999")
        assert is_valid is False
        assert "Invalid IP address format" in error

        is_valid, error = validator.validate("192.168.1")
        assert is_valid is False
        assert "Invalid IP address format" in error

    def test_invalid_ip_non_string(self):
        """Test validation rejects non-string values."""
        validator = IPAddressValidator()

        is_valid, error = validator.validate(192168)
        assert is_valid is False
        assert "must be string" in error

        is_valid, error = validator.validate(None)
        assert is_valid is False
        assert "must be string" in error

    def test_ipv6_rejection(self):
        """Test validation rejects IPv6 addresses."""
        validator = IPAddressValidator()

        is_valid, error = validator.validate("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert is_valid is False
        assert "IPv6" in error or "IPv4" in error

    def test_edge_case_ip_addresses(self):
        """Test validation of edge case IP addresses."""
        validator = IPAddressValidator()

        # Broadcast address
        assert validator.validate("255.255.255.255") == (True, None)

        # Network address
        assert validator.validate("0.0.0.0") == (True, None)

        # Loopback
        assert validator.validate("127.0.0.1") == (True, None)


class TestPortValidator:
    """Tests for PortValidator class."""

    def test_valid_ports(self):
        """Test validation of valid port numbers."""
        validator = PortValidator()

        assert validator.validate(1) == (True, None)
        assert validator.validate(502) == (True, None)
        assert validator.validate(8080) == (True, None)
        assert validator.validate(65535) == (True, None)

    def test_invalid_port_out_of_range(self):
        """Test validation rejects ports outside valid range."""
        validator = PortValidator()

        is_valid, error = validator.validate(0)
        assert is_valid is False
        assert "must be between 1 and 65535" in error

        is_valid, error = validator.validate(70000)
        assert is_valid is False
        assert "must be between 1 and 65535" in error

        is_valid, error = validator.validate(-1)
        assert is_valid is False
        assert "must be between 1 and 65535" in error

    def test_invalid_port_non_integer(self):
        """Test validation rejects non-integer values."""
        validator = PortValidator()

        is_valid, error = validator.validate(502.5)
        assert is_valid is False
        assert "must be integer" in error

        is_valid, error = validator.validate("502")
        assert is_valid is False
        assert "must be integer" in error

        is_valid, error = validator.validate(None)
        assert is_valid is False
        assert "must be integer" in error

    def test_port_boundary_values(self):
        """Test validation at exact port boundaries."""
        validator = PortValidator()

        # Exact boundaries
        assert validator.validate(1) == (True, None)
        assert validator.validate(65535) == (True, None)

        # Just outside boundaries
        is_valid, error = validator.validate(0)
        assert is_valid is False

        is_valid, error = validator.validate(65536)
        assert is_valid is False

    def test_common_ports(self):
        """Test validation of common port numbers."""
        validator = PortValidator()

        # Common ports
        assert validator.validate(80) == (True, None)  # HTTP
        assert validator.validate(443) == (True, None)  # HTTPS
        assert validator.validate(502) == (True, None)  # Modbus
        assert validator.validate(3306) == (True, None)  # MySQL
        assert validator.validate(5432) == (True, None)  # PostgreSQL


class TestSQLIdentifierValidator:
    """Tests for SQLIdentifierValidator class."""

    def test_valid_identifiers(self):
        """Test validation of valid SQL identifiers."""
        validator = SQLIdentifierValidator()

        assert validator.validate("measurements") == (True, None)
        assert validator.validate("user_data") == (True, None)
        assert validator.validate("table_2024") == (True, None)
        assert validator.validate("_private") == (True, None)
        assert validator.validate("CamelCase") == (True, None)

    def test_invalid_identifier_keyword(self):
        """Test validation rejects SQL keywords."""
        validator = SQLIdentifierValidator()

        is_valid, error = validator.validate("SELECT")
        assert is_valid is False
        assert "cannot be a keyword" in error

        is_valid, error = validator.validate("select")
        assert is_valid is False
        assert "cannot be a keyword" in error

        is_valid, error = validator.validate("DROP")
        assert is_valid is False
        assert "cannot be a keyword" in error

    def test_invalid_identifier_format(self):
        """Test validation rejects invalid identifier formats."""
        validator = SQLIdentifierValidator()

        # Starts with number
        is_valid, error = validator.validate("123invalid")
        assert is_valid is False
        assert "Invalid SQL identifier format" in error

        # Contains hyphen
        is_valid, error = validator.validate("table-name")
        assert is_valid is False
        assert "Invalid SQL identifier format" in error

        # Contains space
        is_valid, error = validator.validate("table name")
        assert is_valid is False
        assert "Invalid SQL identifier format" in error

        # Contains special characters
        is_valid, error = validator.validate("table@name")
        assert is_valid is False
        assert "Invalid SQL identifier format" in error

    def test_invalid_identifier_empty(self):
        """Test validation rejects empty identifiers."""
        validator = SQLIdentifierValidator()

        is_valid, error = validator.validate("")
        assert is_valid is False
        assert "cannot be empty" in error

        is_valid, error = validator.validate("   ")
        assert is_valid is False
        assert "cannot be empty" in error

    def test_invalid_identifier_non_string(self):
        """Test validation rejects non-string values."""
        validator = SQLIdentifierValidator()

        is_valid, error = validator.validate(123)
        assert is_valid is False
        assert "must be string" in error

    def test_sql_injection_attempts(self):
        """Test validation prevents SQL injection attempts."""
        validator = SQLIdentifierValidator()

        # SQL injection with semicolon
        is_valid, error = validator.validate("table; DROP TABLE users--")
        assert is_valid is False
        assert "Invalid SQL identifier format" in error

        # SQL injection with quotes
        is_valid, error = validator.validate("table' OR '1'='1")
        assert is_valid is False
        assert "Invalid SQL identifier format" in error

        # SQL injection with comment
        is_valid, error = validator.validate("table--comment")
        assert is_valid is False
        assert "Invalid SQL identifier format" in error

        # SQL injection with union
        is_valid, error = validator.validate("table UNION SELECT")
        assert is_valid is False
        assert "Invalid SQL identifier format" in error


class TestValidationService:
    """Tests for ValidationService facade class."""

    def test_initialization_with_config_manager(self):
        """Test ValidationService initialization with custom config manager."""

        # Mock config manager
        class MockConfigManager:
            def get(self, key, default=None):
                config = {
                    "angles.rotation_min": -180,
                    "angles.rotation_max": 180,
                    "angles.elevation_min": -90,
                    "angles.elevation_max": 90,
                }
                return config.get(key, default)

        service = ValidationService(MockConfigManager())

        # Test with custom ranges
        assert service.validate_rotation(-180) == (True, None)
        assert service.validate_rotation(180) == (True, None)

        is_valid, error = service.validate_rotation(200)
        assert is_valid is False

        assert service.validate_elevation(-90) == (True, None)
        assert service.validate_elevation(90) == (True, None)

        is_valid, error = service.validate_elevation(100)
        assert is_valid is False

    def test_initialization_without_config_manager(self):
        """Test ValidationService initialization with default values."""
        service = ValidationService(None)

        # Should use default ranges
        assert service.validate_rotation(0) == (True, None)
        assert service.validate_rotation(360) == (True, None)
        assert service.validate_elevation(0) == (True, None)
        assert service.validate_elevation(145) == (True, None)

    def test_sanitize_string_normal_text(self):
        """Test sanitization of normal text."""
        service = ValidationService()

        assert service.sanitize_string("normal text") == "normal text"
        assert service.sanitize_string("text with spaces") == "text with spaces"
        assert service.sanitize_string("text123") == "text123"

    def test_sanitize_string_dangerous_characters(self):
        """Test sanitization removes dangerous characters."""
        service = ValidationService()

        # HTML/XML tags
        result = service.sanitize_string("text with <script>alert('xss')</script>")
        assert "<script>" not in result
        assert "</script>" not in result
        assert "alert" in result  # Content remains but tags removed

        result = service.sanitize_string("<b>bold</b> text")
        assert "<b>" not in result
        assert "</b>" not in result
        assert "bold text" in result

        # Null bytes
        result = service.sanitize_string("text\x00with\x00nulls")
        assert "\x00" not in result
        assert "text" in result
        assert "with" in result
        assert "nulls" in result

    def test_sanitize_string_control_characters(self):
        """Test sanitization removes control characters."""
        service = ValidationService()

        # Control characters (except newline, tab, carriage return)
        result = service.sanitize_string("text\x01\x02\x03")
        assert "\x01" not in result
        assert "\x02" not in result
        assert "\x03" not in result
        assert "text" in result

        # Allowed control characters should remain
        result = service.sanitize_string("text\nwith\nnewlines")
        assert "\n" in result

        result = service.sanitize_string("text\twith\ttabs")
        assert "\t" in result

    def test_sanitize_string_max_length(self):
        """Test sanitization respects max length."""
        service = ValidationService()

        # Default max length (255)
        long_text = "a" * 300
        result = service.sanitize_string(long_text)
        assert len(result) == 255

        # Custom max length
        result = service.sanitize_string(long_text, max_length=10)
        assert len(result) == 10
        assert result == "aaaaaaaaaa"

    def test_sanitize_string_whitespace_trimming(self):
        """Test sanitization trims leading/trailing whitespace."""
        service = ValidationService()

        assert service.sanitize_string("  text  ") == "text"
        assert service.sanitize_string("\n\ntext\n\n") == "text"
        assert service.sanitize_string("\t\ttext\t\t") == "text"

    def test_sanitize_string_non_string_input(self):
        """Test sanitization handles non-string input."""
        service = ValidationService()

        # Should convert to string
        assert service.sanitize_string(123) == "123"
        assert service.sanitize_string(45.67) == "45.67"
        assert service.sanitize_string(True) == "True"

    def test_sanitize_string_xss_attempts(self):
        """Test sanitization prevents XSS attacks."""
        service = ValidationService()

        # Various XSS attempts
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "<<SCRIPT>alert('XSS');//<</SCRIPT>",
        ]

        for xss in xss_attempts:
            result = service.sanitize_string(xss)
            # Ensure no HTML tags remain
            assert "<" not in result or ">" not in result
            # Ensure script tags are removed
            assert "<script>" not in result.lower()
            assert "</script>" not in result.lower()

    def test_validate_rotation_integration(self):
        """Test ValidationService rotation validation."""
        service = ValidationService()

        # Valid rotations
        assert service.validate_rotation(0) == (True, None)
        assert service.validate_rotation(180.0) == (True, None)
        assert service.validate_rotation(360) == (True, None)

        # Invalid rotations
        is_valid, error = service.validate_rotation(400)
        assert is_valid is False
        assert "rotation" in error.lower()

    def test_validate_elevation_integration(self):
        """Test ValidationService elevation validation."""
        service = ValidationService()

        # Valid elevations
        assert service.validate_elevation(0) == (True, None)
        assert service.validate_elevation(72.5) == (True, None)
        assert service.validate_elevation(145) == (True, None)

        # Invalid elevations
        is_valid, error = service.validate_elevation(200)
        assert is_valid is False
        assert "elevation" in error.lower()

    def test_validate_ip_address_integration(self):
        """Test ValidationService IP address validation."""
        service = ValidationService()

        # Valid IPs
        assert service.validate_ip_address("192.168.1.100") == (True, None)
        assert service.validate_ip_address("10.0.0.1") == (True, None)

        # Invalid IPs
        is_valid, error = service.validate_ip_address("invalid")
        assert is_valid is False

    def test_validate_port_integration(self):
        """Test ValidationService port validation."""
        service = ValidationService()

        # Valid ports
        assert service.validate_port(502) == (True, None)
        assert service.validate_port(8080) == (True, None)

        # Invalid ports
        is_valid, error = service.validate_port(0)
        assert is_valid is False

        is_valid, error = service.validate_port(70000)
        assert is_valid is False

    def test_validate_sql_identifier_integration(self):
        """Test ValidationService SQL identifier validation."""
        service = ValidationService()

        # Valid identifiers
        assert service.validate_sql_identifier("measurements") == (True, None)
        assert service.validate_sql_identifier("user_data_2024") == (True, None)

        # Invalid identifiers
        is_valid, error = service.validate_sql_identifier("SELECT")
        assert is_valid is False

        is_valid, error = service.validate_sql_identifier("table-name")
        assert is_valid is False
