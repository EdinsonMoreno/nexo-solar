"""Integration tests for input validation verification.


This test suite verifies that input validation is properly integrated into the UI

and that invalid inputs are rejected with clear error messages.


Task: 12.3 Verificar validación de entradas

Requirements validated: 7.1, 7.2, 7.3, 7.4, 7.6


Test Coverage:

- Angle validation in UI components (rotation and elevation)

- SQL identifier validation

- IP address validation

- Port number validation

- Error message clarity

- Invalid value rejection
"""

import pytest

from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QApplication, QMessageBox

from PyQt6.QtCore import Qt

import sys


from modbuspython.backend.validation_service import ValidationService

from modbuspython.ui.location_tab_fixed import LocationTab

from modbuspython.ui.diagnostic_tab import DiagnosticTab


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for Qt tests."""

    app = QApplication.instance()

    if app is None:

        app = QApplication(sys.argv)

    yield app


class TestAngleValidationInLocationTab:
    """Test angle validation in LocationTab UI component.


    Validates Requirements 7.1, 7.6
    """

    def test_valid_rotation_angle_accepted(self, qapp):
        """Test that valid rotation angles are accepted."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager"):

            tab = LocationTab()

            # Set valid rotation angle (QSpinBox expects int)

            tab.rot_spin.setValue(180)

            # Validate

            is_valid, error = tab.validation_service.validate_rotation(180.0)

            assert is_valid is True

            assert error is None

    def test_invalid_rotation_angle_rejected(self, qapp):
        """Test that invalid rotation angles are rejected with clear error message."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager"):

            tab = LocationTab()

            # Test rotation angle above maximum

            is_valid, error = tab.validation_service.validate_rotation(400.0)

            assert is_valid is False

            assert error is not None

            assert "rotation" in error.lower()

            assert "360" in error

            assert "400" in error

    def test_rotation_angle_boundary_values(self, qapp):
        """Test rotation angle validation at boundary values."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager"):

            tab = LocationTab()

            # Test minimum boundary

            is_valid, error = tab.validation_service.validate_rotation(0.0)

            assert is_valid is True

            # Test maximum boundary

            is_valid, error = tab.validation_service.validate_rotation(360.0)

            assert is_valid is True

            # Test below minimum

            is_valid, error = tab.validation_service.validate_rotation(-0.1)

            assert is_valid is False

            assert error is not None

            # Test above maximum

            is_valid, error = tab.validation_service.validate_rotation(360.1)

            assert is_valid is False

            assert error is not None

    def test_valid_elevation_angle_accepted(self, qapp):
        """Test that valid elevation angles are accepted."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager"):

            tab = LocationTab()

            # Set valid elevation angle (QSpinBox expects int)

            tab.elev_spin.setValue(72)

            # Validate

            is_valid, error = tab.validation_service.validate_elevation(72.5)

            assert is_valid is True

            assert error is None

    def test_invalid_elevation_angle_rejected(self, qapp):
        """Test that invalid elevation angles are rejected with clear error message."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager"):

            tab = LocationTab()

            # Test elevation angle above maximum

            is_valid, error = tab.validation_service.validate_elevation(200.0)

            assert is_valid is False

            assert error is not None

            assert "elevation" in error.lower()

            assert "145" in error

            assert "200" in error

    def test_elevation_angle_boundary_values(self, qapp):
        """Test elevation angle validation at boundary values."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager"):

            tab = LocationTab()

            # Test minimum boundary

            is_valid, error = tab.validation_service.validate_elevation(0.0)

            assert is_valid is True

            # Test maximum boundary

            is_valid, error = tab.validation_service.validate_elevation(145.0)

            assert is_valid is True

            # Test below minimum

            is_valid, error = tab.validation_service.validate_elevation(-0.1)

            assert is_valid is False

            assert error is not None

            # Test above maximum

            is_valid, error = tab.validation_service.validate_elevation(145.1)

            assert is_valid is False

            assert error is not None

    @patch("PyQt6.QtWidgets.QMessageBox.critical")
    def test_send_manual_angles_rejects_invalid_rotation(self, mock_critical, qapp):
        """Test that sending manual angles shows error dialog for invalid rotation."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager"):

            tab = LocationTab()

            # Set invalid rotation angle (above maximum)

            tab.rot_spin.setValue(400)

            tab.elev_spin.setValue(45)

            # Try to send manual angles

            tab.send_manual_setpoint()

            # Verify error dialog was shown

            mock_critical.assert_called_once()

            call_args = mock_critical.call_args

            # Check that error message contains validation details

            assert "rotación" in call_args[0][1].lower() or "rotation" in call_args[0][1].lower()

            assert "360" in call_args[0][2]

    @patch("PyQt6.QtWidgets.QMessageBox.critical")
    def test_send_manual_angles_rejects_invalid_elevation(self, mock_critical, qapp):
        """Test that sending manual angles shows error dialog for invalid elevation."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager"):

            tab = LocationTab()

            # Set invalid elevation angle (above maximum)

            tab.rot_spin.setValue(180)

            tab.elev_spin.setValue(200)

            # Try to send manual angles

            tab.send_manual_setpoint()

            # Verify error dialog was shown

            mock_critical.assert_called_once()

            call_args = mock_critical.call_args

            # Check that error message contains validation details

            assert "elevación" in call_args[0][1].lower() or "elevation" in call_args[0][1].lower()

            assert "145" in call_args[0][2]


class TestAngleValidationInDiagnosticTab:
    """Test angle validation in DiagnosticTab UI component.


    Validates Requirements 7.1, 7.6
    """

    def test_valid_angles_accepted(self, qapp):
        """Test that valid angles are accepted in diagnostic tab."""

        with patch("modbuspython.ui.diagnostic_tab.ModbusManager"):

            tab = DiagnosticTab()

            # Validate rotation

            is_valid, error = tab.validation_service.validate_rotation(180.0)

            assert is_valid is True

            assert error is None

            # Validate elevation

            is_valid, error = tab.validation_service.validate_elevation(72.5)

            assert is_valid is True

            assert error is None

    def test_invalid_angles_rejected(self, qapp):
        """Test that invalid angles are rejected in diagnostic tab."""

        with patch("modbuspython.ui.diagnostic_tab.ModbusManager"):

            tab = DiagnosticTab()

            # Test invalid rotation

            is_valid, error = tab.validation_service.validate_rotation(400.0)

            assert is_valid is False

            assert error is not None

            assert "rotation" in error.lower()

            # Test invalid elevation

            is_valid, error = tab.validation_service.validate_elevation(200.0)

            assert is_valid is False

            assert error is not None

            assert "elevation" in error.lower()

    def test_validation_service_exists_in_diagnostic_tab(self, qapp):
        """Test that DiagnosticTab has validation service available."""

        with patch("modbuspython.ui.diagnostic_tab.ModbusManager"):

            tab = DiagnosticTab()

            assert hasattr(tab, "validation_service")

            assert isinstance(tab.validation_service, ValidationService)


class TestIPAddressValidation:
    """Test IP address validation.


    Validates Requirements 7.3, 7.6
    """

    def test_valid_ip_addresses_accepted(self):
        """Test that valid IP addresses are accepted."""

        service = ValidationService()

        valid_ips = ["192.168.1.100", "10.0.0.1", "172.16.0.1", "127.0.0.1", "255.255.255.255"]

        for ip in valid_ips:

            is_valid, error = service.validate_ip_address(ip)

            assert is_valid is True, f"IP {ip} should be valid"

            assert error is None

    def test_invalid_ip_addresses_rejected_with_clear_message(self):
        """Test that invalid IP addresses are rejected with clear error messages."""

        service = ValidationService()

        invalid_ips = [
            ("invalid", "Invalid IP address format"),
            ("999.999.999.999", "Invalid IP address format"),
            ("192.168.1", "Invalid IP address format"),
            ("192.168.1.1.1", "Invalid IP address format"),
        ]

        for ip, expected_msg_part in invalid_ips:

            is_valid, error = service.validate_ip_address(ip)

            assert is_valid is False, f"IP {ip} should be invalid"

            assert error is not None

            assert expected_msg_part.lower() in error.lower()

            assert ip in error  # Error message should include the invalid value

    def test_non_string_ip_rejected(self):
        """Test that non-string IP values are rejected."""

        service = ValidationService()

        is_valid, error = service.validate_ip_address(192168)

        assert is_valid is False

        assert error is not None

        assert "must be string" in error.lower()


class TestPortValidation:
    """Test port number validation.


    Validates Requirements 7.4, 7.6
    """

    def test_valid_ports_accepted(self):
        """Test that valid port numbers are accepted."""

        service = ValidationService()

        valid_ports = [1, 80, 443, 502, 8080, 65535]

        for port in valid_ports:

            is_valid, error = service.validate_port(port)

            assert is_valid is True, f"Port {port} should be valid"

            assert error is None

    def test_invalid_ports_rejected_with_clear_message(self):
        """Test that invalid port numbers are rejected with clear error messages."""

        service = ValidationService()

        invalid_ports = [
            (0, "must be between 1 and 65535"),
            (-1, "must be between 1 and 65535"),
            (70000, "must be between 1 and 65535"),
            (65536, "must be between 1 and 65535"),
        ]

        for port, expected_msg_part in invalid_ports:

            is_valid, error = service.validate_port(port)

            assert is_valid is False, f"Port {port} should be invalid"

            assert error is not None

            assert expected_msg_part.lower() in error.lower()

            assert str(port) in error  # Error message should include the invalid value

    def test_non_integer_port_rejected(self):
        """Test that non-integer port values are rejected."""

        service = ValidationService()

        is_valid, error = service.validate_port(502.5)

        assert is_valid is False

        assert error is not None

        assert "must be integer" in error.lower()

        is_valid, error = service.validate_port("502")

        assert is_valid is False

        assert error is not None

        assert "must be integer" in error.lower()


class TestSQLIdentifierValidation:
    """Test SQL identifier validation and injection prevention.


    Validates Requirements 7.2, 7.6
    """

    def test_valid_identifiers_accepted(self):
        """Test that valid SQL identifiers are accepted."""

        service = ValidationService()

        valid_identifiers = ["measurements", "user_data", "table_2024", "_private", "CamelCase"]

        for identifier in valid_identifiers:

            is_valid, error = service.validate_sql_identifier(identifier)

            assert is_valid is True, f"Identifier {identifier} should be valid"

            assert error is None

    def test_sql_keywords_rejected_with_clear_message(self):
        """Test that SQL keywords are rejected with clear error messages."""

        service = ValidationService()

        sql_keywords = ["SELECT", "DROP", "DELETE", "INSERT", "UPDATE", "TABLE"]

        for keyword in sql_keywords:

            is_valid, error = service.validate_sql_identifier(keyword)

            assert is_valid is False, f"Keyword {keyword} should be rejected"

            assert error is not None

            assert "cannot be a keyword" in error.lower()

            assert keyword in error

    def test_sql_injection_attempts_rejected(self):
        """Test that SQL injection attempts are rejected."""

        service = ValidationService()

        injection_attempts = [
            "table; DROP TABLE users--",
            "table' OR '1'='1",
            "table--comment",
            "table UNION SELECT",
            "123invalid",  # Starts with number
            "table-name",  # Contains hyphen
            "table name",  # Contains space
            "table@name",  # Contains special character
        ]

        for attempt in injection_attempts:

            is_valid, error = service.validate_sql_identifier(attempt)

            assert is_valid is False, f"Injection attempt '{attempt}' should be rejected"

            assert error is not None

            assert "invalid" in error.lower() or "keyword" in error.lower()

    def test_empty_identifier_rejected(self):
        """Test that empty identifiers are rejected."""

        service = ValidationService()

        is_valid, error = service.validate_sql_identifier("")

        assert is_valid is False

        assert error is not None

        assert "cannot be empty" in error.lower()


class TestErrorMessageClarity:
    """Test that error messages are clear and informative.


    Validates Requirement 7.6
    """

    def test_angle_error_messages_include_range_and_value(self):
        """Test that angle validation errors include expected range and actual value."""

        service = ValidationService()

        # Test rotation error message

        is_valid, error = service.validate_rotation(400.0)

        assert is_valid is False

        assert "rotation" in error.lower()

        assert "0" in error  # Minimum value

        assert "360" in error  # Maximum value

        assert "400" in error  # Actual value

        # Test elevation error message

        is_valid, error = service.validate_elevation(200.0)

        assert is_valid is False

        assert "elevation" in error.lower()

        assert "0" in error  # Minimum value

        assert "145" in error  # Maximum value

        assert "200" in error  # Actual value

    def test_ip_error_messages_include_invalid_value(self):
        """Test that IP validation errors include the invalid value."""

        service = ValidationService()

        is_valid, error = service.validate_ip_address("invalid_ip")

        assert is_valid is False
        assert "invalid_ip" in error

        assert "invalid" in error.lower() or "format" in error.lower()

    def test_port_error_messages_include_range_and_value(self):
        """Test that port validation errors include expected range and actual value."""

        service = ValidationService()

        is_valid, error = service.validate_port(70000)

        assert is_valid is False

        assert "1" in error  # Minimum value

        assert "65535" in error  # Maximum value

        assert "70000" in error  # Actual value

    def test_sql_error_messages_are_descriptive(self):
        """Test that SQL identifier validation errors are descriptive."""

        service = ValidationService()

        # Test keyword rejection

        is_valid, error = service.validate_sql_identifier("SELECT")

        assert is_valid is False

        assert "keyword" in error.lower()

        assert "SELECT" in error

        # Test format rejection

        is_valid, error = service.validate_sql_identifier("123invalid")

        assert is_valid is False

        assert "format" in error.lower()

        assert "123invalid" in error


class TestValidationIntegration:
    """Test that validation is properly integrated and prevents invalid values.


    Validates Requirements 7.1, 7.2, 7.3, 7.4, 7.6
    """

    def test_validation_service_available_in_ui_components(self, qapp):
        """Test that ValidationService is available in UI components."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager"):

            location_tab = LocationTab()

            assert hasattr(location_tab, "validation_service")

            assert isinstance(location_tab.validation_service, ValidationService)

        with patch("modbuspython.ui.diagnostic_tab.ModbusManager"):

            diagnostic_tab = DiagnosticTab()

            assert hasattr(diagnostic_tab, "validation_service")

            assert isinstance(diagnostic_tab.validation_service, ValidationService)

    def test_all_validators_accessible_through_service(self):
        """Test that all validators are accessible through ValidationService."""

        service = ValidationService()

        # Test that all validation methods exist

        assert hasattr(service, "validate_rotation")

        assert hasattr(service, "validate_elevation")

        assert hasattr(service, "validate_ip_address")

        assert hasattr(service, "validate_port")

        assert hasattr(service, "validate_sql_identifier")

        assert hasattr(service, "sanitize_string")

    def test_validation_prevents_backend_calls_with_invalid_data(self, qapp):
        """Test that validation prevents backend calls when data is invalid."""

        with patch("modbuspython.ui.location_tab_fixed.ModbusManager") as mock_modbus:

            tab = LocationTab()

            # Set invalid angles

            tab.rot_spin.setValue(400)

            tab.elev_spin.setValue(45)

            # Mock QMessageBox to prevent actual dialog

            with patch("PyQt6.QtWidgets.QMessageBox.critical"):

                # Try to send manual angles

                tab.send_manual_setpoint()

            # Verify that no backend call was made (validation prevented it)

            # The method should return early after validation fails

            # We can verify this by checking that the success message was not shown

            with patch("PyQt6.QtWidgets.QMessageBox.information") as mock_info:

                tab.rot_spin.setValue(400)

                with patch("PyQt6.QtWidgets.QMessageBox.critical"):

                    tab.send_manual_setpoint()

                # Success message should not be shown

                mock_info.assert_not_called()


if __name__ == "__main__":

    pytest.main([__file__, "-v"])
