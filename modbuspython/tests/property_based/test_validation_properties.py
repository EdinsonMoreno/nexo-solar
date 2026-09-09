"""Property-based tests for validation service.

This module contains property-based tests using Hypothesis to verify
validation invariants and properties.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from modbuspython.backend.validation_service import AngleValidator, ValidationService

# Property 1: Angle Range Invariant
# **Validates: Requirements 7.1, 7.6, 7.9**


@given(angle=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_rotation_angle_range_invariant(angle: float):
    """
    Property: Rotation angle validation must accept values in [0, 360] and
    reject all values outside this range.

    **Validates: Requirements 7.1, 7.6, 7.9**

    This test verifies that:
    - All angles in [0, 360] are accepted as valid
    - All angles outside [0, 360] are rejected as invalid
    - Validation is consistent and deterministic
    """
    validator = AngleValidator(min_value=0, max_value=360, angle_type="rotation")
    is_valid, error_message = validator.validate(angle)

    # Define expected validity based on range
    expected_valid = 0 <= angle <= 360

    # Verify validation result matches expected
    assert (
        is_valid == expected_valid
    ), f"Rotation angle {angle} validation failed. Expected valid={expected_valid}, got valid={is_valid}"

    # Verify error message consistency
    if expected_valid:
        assert error_message is None, f"Valid rotation angle {angle} should not have error message, got: {error_message}"
    else:
        assert error_message is not None, f"Invalid rotation angle {angle} should have error message"
        assert "rotation" in error_message.lower(), f"Error message should mention 'rotation', got: {error_message}"
        assert (
            str(angle) in error_message or f"{angle:.1f}" in error_message
        ), f"Error message should include the invalid value {angle}, got: {error_message}"


@given(angle=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_elevation_angle_range_invariant(angle: float):
    """
    Property: Elevation angle validation must accept values in [0, 145] and
    reject all values outside this range.

    **Validates: Requirements 7.1, 7.6, 7.9**

    This test verifies that:
    - All angles in [0, 145] are accepted as valid
    - All angles outside [0, 145] are rejected as invalid
    - Validation is consistent and deterministic
    """
    validator = AngleValidator(min_value=0, max_value=145, angle_type="elevation")
    is_valid, error_message = validator.validate(angle)

    # Define expected validity based on range
    expected_valid = 0 <= angle <= 145

    # Verify validation result matches expected
    assert (
        is_valid == expected_valid
    ), f"Elevation angle {angle} validation failed. Expected valid={expected_valid}, got valid={is_valid}"

    # Verify error message consistency
    if expected_valid:
        assert error_message is None, f"Valid elevation angle {angle} should not have error message, got: {error_message}"
    else:
        assert error_message is not None, f"Invalid elevation angle {angle} should have error message"
        assert "elevation" in error_message.lower(), f"Error message should mention 'elevation', got: {error_message}"
        assert (
            str(angle) in error_message or f"{angle:.1f}" in error_message
        ), f"Error message should include the invalid value {angle}, got: {error_message}"


@given(angle=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_validation_service_rotation_invariant(angle: float):
    """
    Property: ValidationService rotation validation must accept values in [0, 360]
    and reject all values outside this range.

    **Validates: Requirements 7.1, 7.6, 7.9**

    This test verifies the ValidationService facade maintains the same invariants
    as the underlying AngleValidator.
    """
    service = ValidationService()
    is_valid, error_message = service.validate_rotation(angle)

    # Define expected validity based on range
    expected_valid = 0 <= angle <= 360

    # Verify validation result matches expected
    assert (
        is_valid == expected_valid
    ), f"ValidationService rotation {angle} validation failed. Expected valid={expected_valid}, got valid={is_valid}"

    # Verify error message consistency
    if expected_valid:
        assert error_message is None, f"Valid rotation angle {angle} should not have error message, got: {error_message}"
    else:
        assert error_message is not None, f"Invalid rotation angle {angle} should have error message"


@given(angle=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_validation_service_elevation_invariant(angle: float):
    """
    Property: ValidationService elevation validation must accept values in [0, 145]
    and reject all values outside this range.

    **Validates: Requirements 7.1, 7.6, 7.9**

    This test verifies the ValidationService facade maintains the same invariants
    as the underlying AngleValidator.
    """
    service = ValidationService()
    is_valid, error_message = service.validate_elevation(angle)

    # Define expected validity based on range
    expected_valid = 0 <= angle <= 145

    # Verify validation result matches expected
    assert (
        is_valid == expected_valid
    ), f"ValidationService elevation {angle} validation failed. Expected valid={expected_valid}, got valid={is_valid}"

    # Verify error message consistency
    if expected_valid:
        assert error_message is None, f"Valid elevation angle {angle} should not have error message, got: {error_message}"
    else:
        assert error_message is not None, f"Invalid elevation angle {angle} should have error message"


@given(
    angle=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    min_val=st.floats(min_value=-500, max_value=500, allow_nan=False, allow_infinity=False),
    max_val=st.floats(min_value=-500, max_value=500, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_angle_validator_general_range_invariant(angle: float, min_val: float, max_val: float):
    """
    Property: AngleValidator must correctly validate any angle against any
    valid range [min, max] where min <= max.

    **Validates: Requirements 7.1, 7.6**

    This test verifies that the angle validator works correctly with arbitrary
    ranges, not just the specific rotation and elevation ranges.
    """
    # Ensure min <= max
    assume(min_val <= max_val)

    validator = AngleValidator(min_value=min_val, max_value=max_val, angle_type="test")
    is_valid, error_message = validator.validate(angle)

    # Define expected validity based on range
    expected_valid = min_val <= angle <= max_val

    # Verify validation result matches expected
    assert is_valid == expected_valid, (
        f"Angle {angle} validation against range [{min_val}, {max_val}] failed. "
        f"Expected valid={expected_valid}, got valid={is_valid}"
    )

    # Verify error message consistency
    if expected_valid:
        assert error_message is None
    else:
        assert error_message is not None


@given(angle=st.integers(min_value=-1000, max_value=1000))
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_angle_validator_accepts_integers(angle: int):
    """
    Property: AngleValidator must accept integer values as valid numeric input.

    **Validates: Requirements 7.1, 7.6**

    This test verifies that integer angles are treated as valid numeric types.
    """
    validator = AngleValidator(min_value=0, max_value=360, angle_type="rotation")
    is_valid, error_message = validator.validate(angle)

    # Integers should be accepted as numeric type
    expected_valid = 0 <= angle <= 360

    assert is_valid == expected_valid, f"Integer angle {angle} should be validated correctly, got valid={is_valid}"

    # Should not have type error for integers
    if error_message:
        assert (
            "numeric" not in error_message.lower() or "int" not in error_message.lower()
        ), f"Integer should not trigger type error, got: {error_message}"


@given(
    value=st.one_of(
        st.text(min_size=1, max_size=10), st.none(), st.lists(st.integers()), st.dictionaries(st.text(), st.integers())
    )
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_angle_validator_rejects_non_numeric(value):
    """
    Property: AngleValidator must reject all non-numeric types.

    **Validates: Requirements 7.1, 7.6**

    This test verifies that only numeric types (int, float) are accepted.
    Note: Booleans are excluded from this test because in Python, bool is a
    subclass of int, so isinstance(False, int) returns True.
    """
    validator = AngleValidator(min_value=0, max_value=360, angle_type="rotation")
    is_valid, error_message = validator.validate(value)

    # Non-numeric types should always be invalid
    assert is_valid is False, f"Non-numeric value {value} (type {type(value)}) should be rejected"

    assert error_message is not None, f"Non-numeric value should have error message"

    assert "numeric" in error_message.lower(), f"Error message should mention 'numeric', got: {error_message}"


# Property 3: Input Validation Idempotence
# **Validates: Requirements 7.5, 7.6**


@given(angle=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_angle_validation_idempotence(angle: float):
    """
    Property: Applying validation twice should produce the same result as
    applying it once. validate(validate(x)) == validate(x)

    **Validates: Requirements 7.5, 7.6**

    This test verifies that:
    - Validation is idempotent (applying it multiple times has the same effect)
    - The validation result is stable and deterministic
    - No state changes occur during validation
    """
    validator = AngleValidator(min_value=0, max_value=360, angle_type="rotation")

    # First validation
    is_valid_1, error_msg_1 = validator.validate(angle)

    # Second validation (should be identical)
    is_valid_2, error_msg_2 = validator.validate(angle)

    # Verify idempotence
    assert is_valid_1 == is_valid_2, (
        f"Validation idempotence failed for angle {angle}. " f"First call: valid={is_valid_1}, Second call: valid={is_valid_2}"
    )

    assert error_msg_1 == error_msg_2, (
        f"Error message idempotence failed for angle {angle}. " f"First call: '{error_msg_1}', Second call: '{error_msg_2}'"
    )


@given(
    ip_str=st.one_of(
        # Valid IPs
        st.from_regex(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", fullmatch=True),
        # Invalid strings
        st.text(min_size=1, max_size=50),
        st.just(""),
        st.integers().map(str),
    )
)
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_ip_validation_idempotence(ip_str):
    """
    Property: IP address validation is idempotent.

    **Validates: Requirements 7.5, 7.6**

    This test verifies that validating an IP address multiple times
    produces the same result.
    """
    from modbuspython.backend.validation_service import IPAddressValidator

    validator = IPAddressValidator()

    # First validation
    is_valid_1, error_msg_1 = validator.validate(ip_str)

    # Second validation (should be identical)
    is_valid_2, error_msg_2 = validator.validate(ip_str)

    # Verify idempotence
    assert is_valid_1 == is_valid_2, (
        f"IP validation idempotence failed for '{ip_str}'. " f"First call: valid={is_valid_1}, Second call: valid={is_valid_2}"
    )

    assert error_msg_1 == error_msg_2, (
        f"IP error message idempotence failed for '{ip_str}'. " f"First call: '{error_msg_1}', Second call: '{error_msg_2}'"
    )


@given(port=st.integers(min_value=-1000, max_value=100000))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_port_validation_idempotence(port: int):
    """
    Property: Port validation is idempotent.

    **Validates: Requirements 7.5, 7.6**

    This test verifies that validating a port number multiple times
    produces the same result.
    """
    from modbuspython.backend.validation_service import PortValidator

    validator = PortValidator()

    # First validation
    is_valid_1, error_msg_1 = validator.validate(port)

    # Second validation (should be identical)
    is_valid_2, error_msg_2 = validator.validate(port)

    # Verify idempotence
    assert is_valid_1 == is_valid_2, (
        f"Port validation idempotence failed for {port}. " f"First call: valid={is_valid_1}, Second call: valid={is_valid_2}"
    )

    assert error_msg_1 == error_msg_2, (
        f"Port error message idempotence failed for {port}. " f"First call: '{error_msg_1}', Second call: '{error_msg_2}'"
    )


@given(
    identifier=st.one_of(
        # Valid identifiers
        st.from_regex(r"^[a-zA-Z_][a-zA-Z0-9_]{0,30}$", fullmatch=True),
        # Invalid identifiers
        st.text(min_size=1, max_size=50),
        st.just(""),
        st.just("SELECT"),
        st.just("DROP"),
        st.just("123invalid"),
    )
)
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_sql_identifier_validation_idempotence(identifier):
    """
    Property: SQL identifier validation is idempotent.

    **Validates: Requirements 7.5, 7.6**

    This test verifies that validating an SQL identifier multiple times
    produces the same result.
    """
    from modbuspython.backend.validation_service import SQLIdentifierValidator

    validator = SQLIdentifierValidator()

    # First validation
    is_valid_1, error_msg_1 = validator.validate(identifier)

    # Second validation (should be identical)
    is_valid_2, error_msg_2 = validator.validate(identifier)

    # Verify idempotence
    assert is_valid_1 == is_valid_2, (
        f"SQL identifier validation idempotence failed for '{identifier}'. "
        f"First call: valid={is_valid_1}, Second call: valid={is_valid_2}"
    )

    assert error_msg_1 == error_msg_2, (
        f"SQL identifier error message idempotence failed for '{identifier}'. "
        f"First call: '{error_msg_1}', Second call: '{error_msg_2}'"
    )


@given(text=st.text(min_size=0, max_size=500))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_string_sanitization_idempotence(text: str):
    """
    Property: String sanitization is idempotent. sanitize(sanitize(x)) == sanitize(x)

    **Validates: Requirements 7.5, 7.6**

    This test verifies that sanitizing a string multiple times produces
    the same result as sanitizing it once. This is a critical property
    for sanitization functions to prevent data corruption.
    """
    service = ValidationService()

    # First sanitization
    sanitized_1 = service.sanitize_string(text)

    # Second sanitization (should be identical)
    sanitized_2 = service.sanitize_string(sanitized_1)

    # Verify idempotence
    assert sanitized_1 == sanitized_2, (
        f"String sanitization idempotence failed. " f"First: '{sanitized_1}', Second: '{sanitized_2}'"
    )


@given(
    rotation=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    elevation=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_validation_service_idempotence(rotation: float, elevation: float):
    """
    Property: ValidationService methods are idempotent across all validators.

    **Validates: Requirements 7.5, 7.6**

    This test verifies that the ValidationService facade maintains idempotence
    for all validation operations.
    """
    service = ValidationService()

    # Test rotation validation idempotence
    rot_valid_1, rot_msg_1 = service.validate_rotation(rotation)
    rot_valid_2, rot_msg_2 = service.validate_rotation(rotation)

    assert rot_valid_1 == rot_valid_2, f"ValidationService rotation idempotence failed for {rotation}"
    assert rot_msg_1 == rot_msg_2, f"ValidationService rotation error message idempotence failed for {rotation}"

    # Test elevation validation idempotence
    elev_valid_1, elev_msg_1 = service.validate_elevation(elevation)
    elev_valid_2, elev_msg_2 = service.validate_elevation(elevation)

    assert elev_valid_1 == elev_valid_2, f"ValidationService elevation idempotence failed for {elevation}"
    assert elev_msg_1 == elev_msg_2, f"ValidationService elevation error message idempotence failed for {elevation}"


# Property 4: IP Address Format Validation
# **Validates: Requirements 7.3, 7.6**


def generate_valid_ipv4():
    """Strategy to generate valid IPv4 addresses."""
    return st.builds(
        lambda a, b, c, d: f"{a}.{b}.{c}.{d}",
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
    )


def generate_invalid_ip_strings():
    """Strategy to generate invalid IP address strings."""
    return st.one_of(
        # Empty string
        st.just(""),
        # Too few octets
        st.just("192.168.1"),
        st.just("10.0"),
        st.just("172"),
        # Too many octets
        st.just("192.168.1.1.1"),
        st.just("10.0.0.0.0"),
        # Out of range octets
        st.just("256.1.1.1"),
        st.just("192.256.1.1"),
        st.just("192.168.256.1"),
        st.just("192.168.1.256"),
        st.just("999.999.999.999"),
        st.just("300.300.300.300"),
        # Negative numbers
        st.just("-1.0.0.0"),
        st.just("192.-1.1.1"),
        st.just("192.168.-1.1"),
        st.just("192.168.1.-1"),
        # Non-numeric characters
        st.just("abc.def.ghi.jkl"),
        st.just("192.168.1.abc"),
        st.just("192.168.x.1"),
        st.just("192.168.1.1x"),
        # Special characters
        st.just("192.168.1.1!"),
        st.just("192.168.1.1;"),
        st.just("192.168.1.1'"),
        st.just('192.168.1.1"'),
        # IPv6 addresses (not supported)
        st.just("::1"),
        st.just("2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
        st.just("fe80::1"),
        # Whitespace
        st.just(" 192.168.1.1"),
        st.just("192.168.1.1 "),
        st.just("192. 168.1.1"),
        # Leading zeros (technically invalid in strict parsing)
        st.just("192.168.001.001"),
        st.just("01.02.03.04"),
        # Random text
        st.text(alphabet=st.characters(blacklist_categories=("Cs",)), min_size=1, max_size=30).filter(
            lambda x: not all(c in "0123456789." for c in x)
        ),
        # Integers as strings
        st.integers().map(str),
        # Floats as strings
        st.floats(allow_nan=False, allow_infinity=False).map(str),
    )


@given(ip_address=generate_valid_ipv4())
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_ip_address_validation_accepts_valid_ipv4(ip_address: str):
    """
    Property: IP address validator must accept all valid IPv4 addresses.

    **Validates: Requirements 7.3, 7.6**

    This test verifies that:
    - All valid IPv4 addresses in format "a.b.c.d" where 0 <= a,b,c,d <= 255 are accepted
    - Validation returns True with no error message for valid IPs
    - Validation is consistent across all valid IPv4 addresses
    """
    from modbuspython.backend.validation_service import IPAddressValidator

    validator = IPAddressValidator()
    is_valid, error_message = validator.validate(ip_address)

    # All valid IPv4 addresses should be accepted
    assert is_valid is True, f"Valid IPv4 address '{ip_address}' was rejected. Error: {error_message}"

    # Valid IPs should not have error messages
    assert error_message is None, f"Valid IPv4 address '{ip_address}' should not have error message, got: {error_message}"


@given(invalid_ip=generate_invalid_ip_strings())
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_ip_address_validation_rejects_invalid_strings(invalid_ip: str):
    """
    Property: IP address validator must reject all invalid IP address strings.

    **Validates: Requirements 7.3, 7.6**

    This test verifies that:
    - Invalid IP formats are rejected
    - Out-of-range octets are rejected
    - Non-numeric strings are rejected
    - IPv6 addresses are rejected (only IPv4 supported)
    - Validation returns False with descriptive error message
    """
    from modbuspython.backend.validation_service import IPAddressValidator

    validator = IPAddressValidator()
    is_valid, error_message = validator.validate(invalid_ip)

    # All invalid IP strings should be rejected
    assert is_valid is False, f"Invalid IP string '{invalid_ip}' was incorrectly accepted as valid"

    # Invalid IPs should have error messages
    assert error_message is not None, f"Invalid IP string '{invalid_ip}' should have error message"

    # Error message should be descriptive
    assert len(error_message) > 0, f"Error message for invalid IP '{invalid_ip}' should not be empty"


@given(ip_address=st.one_of(generate_valid_ipv4(), generate_invalid_ip_strings()))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_ip_address_validation_deterministic(ip_address: str):
    """
    Property: IP address validation must be deterministic and consistent.

    **Validates: Requirements 7.3, 7.6**

    This test verifies that:
    - Validating the same IP multiple times produces identical results
    - Validation result is stable and does not depend on call order
    - Error messages are consistent across calls
    """
    from modbuspython.backend.validation_service import IPAddressValidator

    validator = IPAddressValidator()

    # Validate multiple times
    results = [validator.validate(ip_address) for _ in range(3)]

    # All results should be identical
    first_result = results[0]
    for i, result in enumerate(results[1:], start=2):
        assert result == first_result, (
            f"IP validation for '{ip_address}' is not deterministic. " f"First call: {first_result}, Call {i}: {result}"
        )


@given(
    non_string=st.one_of(
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.none(),
        st.booleans(),
        st.lists(st.integers()),
        st.dictionaries(st.text(), st.integers()),
    )
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_ip_address_validation_rejects_non_strings(non_string):
    """
    Property: IP address validator must reject all non-string types.

    **Validates: Requirements 7.3, 7.6**

    This test verifies that:
    - Only string types are accepted as input
    - Non-string types are rejected with appropriate error message
    - Type checking happens before format validation
    """
    from modbuspython.backend.validation_service import IPAddressValidator

    validator = IPAddressValidator()
    is_valid, error_message = validator.validate(non_string)

    # Non-string types should always be rejected
    assert is_valid is False, f"Non-string value {non_string} (type {type(non_string)}) should be rejected"

    # Should have error message mentioning type
    assert error_message is not None, f"Non-string value should have error message"

    assert (
        "string" in error_message.lower() or "str" in error_message.lower()
    ), f"Error message should mention string type requirement, got: {error_message}"


@given(ip_address=generate_valid_ipv4())
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_validation_service_ip_address_integration(ip_address: str):
    """
    Property: ValidationService IP validation must maintain same invariants as IPAddressValidator.

    **Validates: Requirements 7.3, 7.6**

    This test verifies that the ValidationService facade correctly delegates
    to IPAddressValidator and maintains the same validation behavior.
    """
    from modbuspython.backend.validation_service import ValidationService, IPAddressValidator

    service = ValidationService()
    validator = IPAddressValidator()

    # Both should produce identical results
    service_result = service.validate_ip_address(ip_address)
    validator_result = validator.validate(ip_address)

    assert service_result == validator_result, (
        f"ValidationService and IPAddressValidator produced different results for '{ip_address}'. "
        f"Service: {service_result}, Validator: {validator_result}"
    )


# Property 5: Port Range Validation
# **Validates: Requirements 7.4, 7.6**


@given(port=st.integers(min_value=-10000, max_value=100000))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_port_range_validation(port: int):
    """
    Property: Port validation must accept values in [1, 65535] and
    reject all values outside this range.

    **Validates: Requirements 7.4, 7.6**

    This test verifies that:
    - All ports in [1, 65535] are accepted as valid
    - All ports outside [1, 65535] are rejected as invalid
    - Port 0 is rejected (reserved)
    - Ports > 65535 are rejected (out of range)
    - Negative ports are rejected
    - Validation is consistent and deterministic
    """
    from modbuspython.backend.validation_service import PortValidator

    validator = PortValidator()
    is_valid, error_message = validator.validate(port)

    # Define expected validity based on range
    expected_valid = 1 <= port <= 65535

    # Verify validation result matches expected
    assert is_valid == expected_valid, f"Port {port} validation failed. Expected valid={expected_valid}, got valid={is_valid}"

    # Verify error message consistency
    if expected_valid:
        assert error_message is None, f"Valid port {port} should not have error message, got: {error_message}"
    else:
        assert error_message is not None, f"Invalid port {port} should have error message"
        assert "port" in error_message.lower(), f"Error message should mention 'port', got: {error_message}"
        assert str(port) in error_message, f"Error message should include the invalid value {port}, got: {error_message}"


@given(port=st.integers(min_value=1, max_value=65535))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_port_validation_accepts_valid_ports(port: int):
    """
    Property: Port validator must accept all valid port numbers in range [1, 65535].

    **Validates: Requirements 7.4, 7.6**

    This test verifies that:
    - All standard ports (1-1023) are accepted
    - All registered ports (1024-49151) are accepted
    - All dynamic/private ports (49152-65535) are accepted
    - Validation returns True with no error message for valid ports
    """
    from modbuspython.backend.validation_service import PortValidator

    validator = PortValidator()
    is_valid, error_message = validator.validate(port)

    # All valid ports should be accepted
    assert is_valid is True, f"Valid port {port} was rejected. Error: {error_message}"

    # Valid ports should not have error messages
    assert error_message is None, f"Valid port {port} should not have error message, got: {error_message}"


@given(
    port=st.one_of(
        st.integers(max_value=0),
        st.integers(min_value=65536, max_value=100000),  # Zero and negative  # Above valid range
    )
)
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_port_validation_rejects_invalid_ports(port: int):
    """
    Property: Port validator must reject all invalid port numbers.

    **Validates: Requirements 7.4, 7.6**

    This test verifies that:
    - Port 0 is rejected (reserved)
    - Negative ports are rejected
    - Ports > 65535 are rejected (exceeds 16-bit unsigned integer max)
    - Validation returns False with descriptive error message
    """
    from modbuspython.backend.validation_service import PortValidator

    validator = PortValidator()
    is_valid, error_message = validator.validate(port)

    # All invalid ports should be rejected
    assert is_valid is False, f"Invalid port {port} was incorrectly accepted as valid"

    # Invalid ports should have error messages
    assert error_message is not None, f"Invalid port {port} should have error message"

    # Error message should mention the range
    assert (
        "1" in error_message and "65535" in error_message
    ), f"Error message should mention valid range [1, 65535], got: {error_message}"


@given(
    non_integer=st.one_of(
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(min_size=1, max_size=10),
        st.none(),
        st.lists(st.integers()),
        st.dictionaries(st.text(), st.integers()),
    )
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_port_validation_rejects_non_integers(non_integer):
    """
    Property: Port validator must reject all non-integer types.

    **Validates: Requirements 7.4, 7.6**

    This test verifies that:
    - Only integer types are accepted as input
    - Floats are rejected (even if they represent whole numbers like 80.0)
    - Strings are rejected (even if they contain numbers like "80")
    - Other types are rejected with appropriate error message
    - Type checking happens before range validation

    Note: Booleans are excluded from this test because in Python, bool is a
    subclass of int, so isinstance(False, int) returns True.
    """
    from modbuspython.backend.validation_service import PortValidator

    validator = PortValidator()
    is_valid, error_message = validator.validate(non_integer)

    # Non-integer types should always be rejected
    assert is_valid is False, f"Non-integer value {non_integer} (type {type(non_integer)}) should be rejected"

    # Should have error message
    assert error_message is not None, f"Non-integer value should have error message"

    # Error message should mention either type or range issue
    assert (
        "integer" in error_message.lower() or "int" in error_message.lower() or "between" in error_message.lower()
    ), f"Error message should mention integer type or range requirement, got: {error_message}"


@given(port=st.integers(min_value=-10000, max_value=100000))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_port_validation_deterministic(port: int):
    """
    Property: Port validation must be deterministic and consistent.

    **Validates: Requirements 7.4, 7.6**

    This test verifies that:
    - Validating the same port multiple times produces identical results
    - Validation result is stable and does not depend on call order
    - Error messages are consistent across calls
    """
    from modbuspython.backend.validation_service import PortValidator

    validator = PortValidator()

    # Validate multiple times
    results = [validator.validate(port) for _ in range(3)]

    # All results should be identical
    first_result = results[0]
    for i, result in enumerate(results[1:], start=2):
        assert result == first_result, (
            f"Port validation for {port} is not deterministic. " f"First call: {first_result}, Call {i}: {result}"
        )


@given(port=st.integers(min_value=1, max_value=65535))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_validation_service_port_integration(port: int):
    """
    Property: ValidationService port validation must maintain same invariants as PortValidator.

    **Validates: Requirements 7.4, 7.6**

    This test verifies that the ValidationService facade correctly delegates
    to PortValidator and maintains the same validation behavior.
    """
    from modbuspython.backend.validation_service import ValidationService, PortValidator

    service = ValidationService()
    validator = PortValidator()

    # Both should produce identical results
    service_result = service.validate_port(port)
    validator_result = validator.validate(port)

    assert service_result == validator_result, (
        f"ValidationService and PortValidator produced different results for port {port}. "
        f"Service: {service_result}, Validator: {validator_result}"
    )


@given(port=st.integers(min_value=-10000, max_value=100000), iterations=st.integers(min_value=2, max_value=5))
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_port_validation_stability_over_iterations(port: int, iterations: int):
    """
    Property: Port validation result must remain stable across multiple iterations.

    **Validates: Requirements 7.4, 7.6**

    This test verifies that:
    - Validation result doesn't change over multiple calls
    - No internal state affects validation outcome
    - Validator can be reused safely
    """
    from modbuspython.backend.validation_service import PortValidator

    validator = PortValidator()

    # Collect results from multiple iterations
    results = [validator.validate(port) for _ in range(iterations)]

    # All results must be identical
    assert (
        len(set(results)) == 1
    ), f"Port validation for {port} produced inconsistent results over {iterations} iterations: {results}"


# Property 6: SQL Identifier Injection Prevention
# **Validates: Requirements 7.2, 7.6**


def generate_valid_sql_identifiers():
    """Strategy to generate valid SQL identifiers."""
    return st.one_of(
        # Simple valid identifiers
        st.from_regex(r"^[a-zA-Z_][a-zA-Z0-9_]{0,30}$", fullmatch=True),
        # Common table/column names
        st.sampled_from(
            [
                "users",
                "user_data",
                "measurements",
                "sensor_readings",
                "config",
                "settings",
                "logs",
                "events",
                "data_2024",
                "_private",
                "_internal",
                "temp_table",
                "backup_data",
                "TableName",
                "ColumnName",
                "MyTable",
                "my_column_123",
            ]
        ),
    )


def generate_malicious_sql_identifiers():
    """Strategy to generate malicious SQL injection attempts."""
    return st.sampled_from(
        [
            # SQL keywords (should be rejected)
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
            "JOIN",
            "UNION",
            "ORDER",
            "GROUP",
            "HAVING",
            "LIMIT",
            "INDEX",
            "VIEW",
            # SQL injection attempts with special characters
            "users; DROP TABLE users--",
            "admin'--",
            "admin' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' OR '1' = '1",
            "admin'/*",
            "' OR 1=1--",
            "' UNION SELECT * FROM users--",
            "admin'; DELETE FROM users WHERE '1'='1",
            # Identifiers with invalid characters
            "table-name",  # hyphen not allowed
            "table name",  # space not allowed
            "table.name",  # dot not allowed
            "table;name",  # semicolon not allowed
            "table'name",  # quote not allowed
            'table"name',  # double quote not allowed
            "table(name)",  # parentheses not allowed
            "table[name]",  # brackets not allowed
            "table{name}",  # braces not allowed
            "table*name",  # asterisk not allowed
            "table/name",  # slash not allowed
            "table\\name",  # backslash not allowed
            "table@name",  # at sign not allowed
            "table#name",  # hash not allowed
            "table$name",  # dollar sign not allowed
            "table%name",  # percent not allowed
            "table&name",  # ampersand not allowed
            "table!name",  # exclamation not allowed
            "table?name",  # question mark not allowed
            "table<name>",  # angle brackets not allowed
            "table|name",  # pipe not allowed
            "table~name",  # tilde not allowed
            "table`name",  # backtick not allowed
            # Identifiers starting with invalid characters
            "123table",  # starts with number
            "9users",  # starts with number
            "-table",  # starts with hyphen
            ".table",  # starts with dot
            "'table",  # starts with quote
            ";table",  # starts with semicolon
            " table",  # starts with space
            # Empty or whitespace
            "",
            " ",
            "   ",
            "\t",
            "\n",
            # SQL comments
            "-- comment",
            "/* comment */",
            "table -- comment",
            "table /* comment */",
            # Mixed case keywords
            "Select",
            "select",
            "SeLeCt",
            "Drop",
            "drop",
            "DrOp",
            "Delete",
            "delete",
            "DeLeTe",
        ]
    )


@given(identifier=generate_valid_sql_identifiers())
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_sql_identifier_validation_accepts_valid_identifiers(identifier: str):
    """
    Property: SQL identifier validator must accept all valid SQL identifiers.

    **Validates: Requirements 7.2, 7.6**

    This test verifies that:
    - Valid identifiers starting with letter or underscore are accepted
    - Identifiers containing only letters, numbers, and underscores are accepted
    - Identifiers that are not SQL keywords are accepted
    - Validation returns True with no error message for valid identifiers
    """
    from modbuspython.backend.validation_service import SQLIdentifierValidator

    validator = SQLIdentifierValidator()
    is_valid, error_message = validator.validate(identifier)

    # All valid identifiers should be accepted
    assert is_valid is True, f"Valid SQL identifier '{identifier}' was rejected. Error: {error_message}"

    # Valid identifiers should not have error messages
    assert error_message is None, f"Valid SQL identifier '{identifier}' should not have error message, got: {error_message}"


@given(identifier=generate_malicious_sql_identifiers())
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_sql_identifier_validation_rejects_malicious_identifiers(identifier: str):
    """
    Property: SQL identifier validator must reject all malicious SQL injection attempts.

    **Validates: Requirements 7.2, 7.6**

    This test verifies that:
    - SQL keywords are rejected
    - Identifiers with special characters are rejected
    - SQL injection patterns are rejected
    - Identifiers starting with invalid characters are rejected
    - Empty or whitespace-only identifiers are rejected
    - SQL comments are rejected
    - Validation returns False with descriptive error message
    """
    from modbuspython.backend.validation_service import SQLIdentifierValidator

    validator = SQLIdentifierValidator()
    is_valid, error_message = validator.validate(identifier)

    # All malicious identifiers should be rejected
    assert is_valid is False, f"Malicious SQL identifier '{identifier}' was incorrectly accepted as valid"

    # Invalid identifiers should have error messages
    assert error_message is not None, f"Malicious SQL identifier '{identifier}' should have error message"

    # Error message should be descriptive
    assert len(error_message) > 0, f"Error message for malicious identifier '{identifier}' should not be empty"


@given(identifier=st.text(min_size=1, max_size=100))
@settings(max_examples=300, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_sql_identifier_validation_comprehensive(identifier: str):
    """
    Property: SQL identifier validation must correctly classify all possible strings.

    **Validates: Requirements 7.2, 7.6**

    This test verifies that:
    - Every string is either accepted or rejected (no crashes)
    - Validation is deterministic
    - Error messages are provided for invalid identifiers
    - Valid identifiers match the pattern: start with letter/underscore, contain only alphanumeric/underscore
    - SQL keywords are always rejected regardless of format
    """
    from modbuspython.backend.validation_service import SQLIdentifierValidator
    import re

    validator = SQLIdentifierValidator()
    is_valid, error_message = validator.validate(identifier)

    # Validation should never crash
    assert isinstance(is_valid, bool), f"Validation should return boolean, got {type(is_valid)}"

    # If valid, verify it matches the expected pattern
    if is_valid:
        assert error_message is None, f"Valid identifier '{identifier}' should not have error message"

        # Should match the pattern
        assert re.match(
            r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier
        ), f"Valid identifier '{identifier}' doesn't match expected pattern"

        # Should not be a SQL keyword
        sql_keywords = {
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
        assert identifier.upper() not in sql_keywords, f"Valid identifier '{identifier}' is a SQL keyword"
    else:
        # If invalid, must have error message
        assert error_message is not None, f"Invalid identifier '{identifier}' should have error message"
        assert len(error_message) > 0, f"Error message should not be empty for invalid identifier '{identifier}'"


@given(identifier=st.one_of(generate_valid_sql_identifiers(), generate_malicious_sql_identifiers()))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_sql_identifier_validation_idempotence(identifier: str):
    """
    Property: SQL identifier validation is idempotent.

    **Validates: Requirements 7.2, 7.6**

    This test verifies that validating an SQL identifier multiple times
    produces the same result. This is critical for security - validation
    must be consistent to prevent bypass attacks.
    """
    from modbuspython.backend.validation_service import SQLIdentifierValidator

    validator = SQLIdentifierValidator()

    # First validation
    is_valid_1, error_msg_1 = validator.validate(identifier)

    # Second validation (should be identical)
    is_valid_2, error_msg_2 = validator.validate(identifier)

    # Third validation (should be identical)
    is_valid_3, error_msg_3 = validator.validate(identifier)

    # Verify idempotence
    assert is_valid_1 == is_valid_2 == is_valid_3, (
        f"SQL identifier validation idempotence failed for '{identifier}'. "
        f"Results: {is_valid_1}, {is_valid_2}, {is_valid_3}"
    )

    assert error_msg_1 == error_msg_2 == error_msg_3, (
        f"SQL identifier error message idempotence failed for '{identifier}'. "
        f"Messages: '{error_msg_1}', '{error_msg_2}', '{error_msg_3}'"
    )


@given(
    non_string=st.one_of(
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.none(),
        st.booleans(),
        st.lists(st.text()),
        st.dictionaries(st.text(), st.integers()),
    )
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_sql_identifier_validation_rejects_non_strings(non_string):
    """
    Property: SQL identifier validator must reject all non-string types.

    **Validates: Requirements 7.2, 7.6**

    This test verifies that:
    - Only string types are accepted as input
    - Non-string types are rejected with appropriate error message
    - Type checking happens before format validation
    """
    from modbuspython.backend.validation_service import SQLIdentifierValidator

    validator = SQLIdentifierValidator()
    is_valid, error_message = validator.validate(non_string)

    # Non-string types should always be rejected
    assert is_valid is False, f"Non-string value {non_string} (type {type(non_string)}) should be rejected"

    # Should have error message mentioning type
    assert error_message is not None, f"Non-string value should have error message"

    assert (
        "string" in error_message.lower() or "str" in error_message.lower()
    ), f"Error message should mention string type requirement, got: {error_message}"


@given(identifier=generate_valid_sql_identifiers())
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_validation_service_sql_identifier_integration(identifier: str):
    """
    Property: ValidationService SQL identifier validation must maintain same invariants as SQLIdentifierValidator.

    **Validates: Requirements 7.2, 7.6**

    This test verifies that the ValidationService facade correctly delegates
    to SQLIdentifierValidator and maintains the same validation behavior.
    """
    from modbuspython.backend.validation_service import ValidationService, SQLIdentifierValidator

    service = ValidationService()
    validator = SQLIdentifierValidator()

    # Both should produce identical results
    service_result = service.validate_sql_identifier(identifier)
    validator_result = validator.validate(identifier)

    assert service_result == validator_result, (
        f"ValidationService and SQLIdentifierValidator produced different results for '{identifier}'. "
        f"Service: {service_result}, Validator: {validator_result}"
    )


@given(identifier=st.text(min_size=1, max_size=100), iterations=st.integers(min_value=2, max_value=5))
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_sql_identifier_validation_stability_over_iterations(identifier: str, iterations: int):
    """
    Property: SQL identifier validation result must remain stable across multiple iterations.

    **Validates: Requirements 7.2, 7.6**

    This test verifies that:
    - Validation result doesn't change over multiple calls
    - No internal state affects validation outcome
    - Validator can be reused safely
    - Critical for security: prevents timing-based bypass attacks
    """
    from modbuspython.backend.validation_service import SQLIdentifierValidator

    validator = SQLIdentifierValidator()

    # Collect results from multiple iterations
    results = [validator.validate(identifier) for _ in range(iterations)]

    # All results must be identical
    assert (
        len(set(results)) == 1
    ), f"SQL identifier validation for '{identifier}' produced inconsistent results over {iterations} iterations: {results}"


@given(
    base_identifier=st.from_regex(r"^[a-zA-Z_][a-zA-Z0-9_]{0,20}$", fullmatch=True),
    injection_suffix=st.sampled_from(
        ["'; DROP TABLE users--", "' OR '1'='1", "; DELETE FROM data", "' UNION SELECT", "/**/", "--", "#"]
    ),
)
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.validation
def test_sql_identifier_prevents_injection_via_concatenation(base_identifier: str, injection_suffix: str):
    """
    Property: SQL identifier validator must reject identifiers with injection attempts
    concatenated to valid identifiers.

    **Validates: Requirements 7.2, 7.6**

    This test verifies that:
    - Valid identifier + injection suffix is rejected
    - Concatenation attacks are prevented
    - Special characters in any position cause rejection
    """
    from modbuspython.backend.validation_service import SQLIdentifierValidator

    validator = SQLIdentifierValidator()

    # Valid base should be accepted
    base_valid, _ = validator.validate(base_identifier)
    assert base_valid is True, f"Base identifier '{base_identifier}' should be valid"

    # Concatenated identifier should be rejected
    malicious_identifier = base_identifier + injection_suffix
    is_valid, error_message = validator.validate(malicious_identifier)

    assert is_valid is False, f"Malicious identifier '{malicious_identifier}' (base + injection) should be rejected"

    assert error_message is not None, f"Malicious identifier '{malicious_identifier}' should have error message"
