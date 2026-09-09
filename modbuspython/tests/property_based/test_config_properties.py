"""Property-based tests for configuration management.

This module contains property-based tests using Hypothesis to verify
configuration serialization and parsing properties.
"""

import pytest
from hypothesis import given, strategies as st, settings
from pathlib import Path
import yaml
import json
import tempfile
from typing import Dict, Any


# Custom strategies for generating valid configuration values
@st.composite
def valid_ip_address(draw):
    """Generate valid IPv4 addresses."""
    octets = [draw(st.integers(min_value=0, max_value=255)) for _ in range(4)]
    return ".".join(map(str, octets))


@st.composite
def valid_port(draw):
    """Generate valid port numbers."""
    return draw(st.integers(min_value=1, max_value=65535))


@st.composite
def valid_timeout(draw):
    """Generate valid timeout values."""
    return draw(st.floats(min_value=0.1, max_value=30.0, allow_nan=False, allow_infinity=False))


@st.composite
def valid_angle_range(draw):
    """Generate valid angle range (min, max) where min < max."""
    min_val = draw(st.floats(min_value=0, max_value=180, allow_nan=False, allow_infinity=False))
    max_val = draw(st.floats(min_value=min_val, max_value=360, allow_nan=False, allow_infinity=False))
    return min_val, max_val


@st.composite
def valid_elevation_range(draw):
    """Generate valid elevation range (min, max) where min < max."""
    min_val = draw(st.floats(min_value=0, max_value=72.5, allow_nan=False, allow_infinity=False))
    max_val = draw(st.floats(min_value=min_val, max_value=145, allow_nan=False, allow_infinity=False))
    return min_val, max_val


@st.composite
def valid_sql_identifier(draw):
    """Generate valid SQL identifiers."""
    # Start with letter or underscore
    first_char = draw(st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"))
    # Rest can be letters, digits, or underscores
    rest = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_", min_size=0, max_size=20))
    return first_char + rest


@st.composite
def valid_configuration(draw):
    """Generate a valid configuration object."""
    rotation_min, rotation_max = draw(valid_angle_range())
    elevation_min, elevation_max = draw(valid_elevation_range())

    config = {
        "modbus": {
            "host": draw(valid_ip_address()),
            "port": draw(valid_port()),
            "timeout": draw(valid_timeout()),
            "retry_attempts": draw(st.integers(min_value=0, max_value=10)),
            "retry_backoff": draw(st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)),
            "registers": {
                "rotation_setpoint": draw(st.integers(min_value=0, max_value=100)),
                "elevation_setpoint": draw(st.integers(min_value=0, max_value=100)),
                "rotation_actual": draw(st.integers(min_value=0, max_value=100)),
                "elevation_actual": draw(st.integers(min_value=0, max_value=100)),
                "irradiance": draw(st.integers(min_value=0, max_value=100)),
            },
        },
        "database": {
            "path": draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_/.", min_size=5, max_size=50)),
            "table_name": draw(valid_sql_identifier()),
            "connection_pool_size": draw(st.integers(min_value=1, max_value=20)),
        },
        "logging": {
            "level": draw(st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])),
            "file_path": draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_/.", min_size=5, max_size=50)),
            "max_bytes": draw(st.integers(min_value=1048576, max_value=104857600)),
            "backup_count": draw(st.integers(min_value=1, max_value=10)),
        },
        "angles": {
            "rotation_min": rotation_min,
            "rotation_max": rotation_max,
            "elevation_min": elevation_min,
            "elevation_max": elevation_max,
        },
    }

    return config


def normalize_floats(obj: Any, tolerance: float = 1e-9) -> Any:
    """Normalize floating point values for comparison.

    Handles floating point precision issues by rounding to a reasonable precision.
    """
    if isinstance(obj, float):
        # Round to 10 decimal places to handle floating point precision
        return round(obj, 10)
    elif isinstance(obj, dict):
        return {k: normalize_floats(v, tolerance) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_floats(item, tolerance) for item in obj]
    else:
        return obj


# Property 2: Configuration Round-Trip Preservation
# **Validates: Requirements 9.1, 9.3, 9.4, 9.5**


@given(config=valid_configuration())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config
def test_config_round_trip_json(config: Dict[str, Any]):
    """
    Property: For any valid configuration, serializing to JSON and parsing back
    must preserve all values.

    **Validates: Requirements 9.1, 9.3, 9.4, 9.5**

    This test verifies that:
    - Configuration can be serialized to valid JSON
    - JSON can be parsed back to a configuration object
    - All values are preserved through the round-trip
    """
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        # Serialize to JSON
        json.dump(config, f, indent=2)
        f.flush()

    try:
        # Parse back from JSON (file is now closed)
        with open(temp_path, "r") as read_f:
            parsed_config = json.load(read_f)

        # Normalize both configs for comparison (handle float precision)
        normalized_original = normalize_floats(config)
        normalized_parsed = normalize_floats(parsed_config)

        # Verify equivalence
        assert (
            normalized_parsed == normalized_original
        ), f"Round-trip failed for JSON. Original: {normalized_original}, Parsed: {normalized_parsed}"

    finally:
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()


@given(config=valid_configuration())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config
def test_config_round_trip_yaml(config: Dict[str, Any]):
    """
    Property: For any valid configuration, serializing to YAML and parsing back
    must preserve all values.

    **Validates: Requirements 9.1, 9.3, 9.4, 9.5**

    This test verifies that:
    - Configuration can be serialized to valid YAML
    - YAML can be parsed back to a configuration object
    - All values are preserved through the round-trip
    """
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
        # Serialize to YAML
        yaml.dump(config, f, default_flow_style=False, indent=2)
        f.flush()

    try:
        # Parse back from YAML (file is now closed)
        with open(temp_path, "r") as read_f:
            parsed_config = yaml.safe_load(read_f)

        # Normalize both configs for comparison (handle float precision)
        normalized_original = normalize_floats(config)
        normalized_parsed = normalize_floats(parsed_config)

        # Verify equivalence
        assert (
            normalized_parsed == normalized_original
        ), f"Round-trip failed for YAML. Original: {normalized_original}, Parsed: {normalized_parsed}"

    finally:
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()


@given(config=valid_configuration())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config
def test_config_serialization_produces_valid_format(config: Dict[str, Any]):
    """
    Property: For any valid configuration, serialization must produce valid
    JSON/YAML that can be parsed by standard parsers.

    **Validates: Requirements 9.6, 9.7**

    This test verifies that:
    - Serialized JSON is valid and parseable
    - Serialized YAML is valid and parseable
    - Output is properly formatted with indentation
    """
    # Test JSON serialization
    json_str = json.dumps(config, indent=2)
    assert json_str is not None
    assert len(json_str) > 0

    # Verify JSON is parseable
    parsed_json = json.loads(json_str)
    assert parsed_json is not None

    # Verify indentation (should contain newlines for readability)
    assert "\n" in json_str, "JSON should be formatted with newlines"

    # Test YAML serialization
    yaml_str = yaml.dump(config, default_flow_style=False, indent=2)
    assert yaml_str is not None
    assert len(yaml_str) > 0

    # Verify YAML is parseable
    parsed_yaml = yaml.safe_load(yaml_str)
    assert parsed_yaml is not None

    # Verify indentation (should contain newlines for readability)
    assert "\n" in yaml_str, "YAML should be formatted with newlines"


@given(config=valid_configuration())
@settings(max_examples=50, deadline=None)
@pytest.mark.property
@pytest.mark.config
def test_config_round_trip_json_to_yaml_equivalence(config: Dict[str, Any]):
    """
    Property: For any valid configuration, round-trip through JSON should be
    equivalent to round-trip through YAML.

    **Validates: Requirements 9.5**

    This test verifies that both JSON and YAML formats preserve the same data.
    """
    # Round-trip through JSON
    json_str = json.dumps(config, indent=2)
    json_parsed = json.loads(json_str)

    # Round-trip through YAML
    yaml_str = yaml.dump(config, default_flow_style=False, indent=2)
    yaml_parsed = yaml.safe_load(yaml_str)

    # Normalize both for comparison
    normalized_json = normalize_floats(json_parsed)
    normalized_yaml = normalize_floats(yaml_parsed)

    # Both should be equivalent
    assert (
        normalized_json == normalized_yaml
    ), f"JSON and YAML round-trips produced different results. JSON: {normalized_json}, YAML: {normalized_yaml}"


# Property 12: Configuration Format Validity
# **Validates: Requirements 9.1, 9.3, 9.4**


@given(config=valid_configuration())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_format
def test_config_format_validity_json(config: Dict[str, Any]):
    """
    Property: All valid configurations must serialize to valid JSON format.

    **Validates: Requirements 9.1, 9.3, 9.4**

    This test verifies that:
    - Configuration serializes to syntactically valid JSON
    - JSON can be parsed by standard JSON parser
    - No encoding or formatting errors occur
    - Output is properly formatted with indentation
    """
    # Serialize to JSON
    try:
        json_str = json.dumps(config, indent=2)
        serialization_succeeded = True
    except (TypeError, ValueError) as e:
        serialization_succeeded = False
        pytest.fail(f"Configuration serialization to JSON failed: {e}")

    assert serialization_succeeded, "Valid configuration must serialize to JSON without errors"

    # Verify JSON is valid by parsing it
    try:
        parsed = json.loads(json_str)
        parsing_succeeded = True
    except json.JSONDecodeError as e:
        parsing_succeeded = False
        pytest.fail(f"Serialized JSON is not valid: {e}")

    assert parsing_succeeded, "Serialized JSON must be parseable"

    # Verify formatting (should contain newlines for readability)
    assert "\n" in json_str, "JSON should be formatted with newlines for readability"

    # Verify indentation (should contain spaces for indentation)
    assert "  " in json_str or "\t" in json_str, "JSON should be indented for readability"


@given(config=valid_configuration())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_format
def test_config_format_validity_yaml(config: Dict[str, Any]):
    """
    Property: All valid configurations must serialize to valid YAML format.

    **Validates: Requirements 9.1, 9.3, 9.4**

    This test verifies that:
    - Configuration serializes to syntactically valid YAML
    - YAML can be parsed by standard YAML parser
    - No encoding or formatting errors occur
    - Output is properly formatted with indentation
    """
    # Serialize to YAML
    try:
        yaml_str = yaml.dump(config, default_flow_style=False, indent=2)
        serialization_succeeded = True
    except (TypeError, ValueError, yaml.YAMLError) as e:
        serialization_succeeded = False
        pytest.fail(f"Configuration serialization to YAML failed: {e}")

    assert serialization_succeeded, "Valid configuration must serialize to YAML without errors"

    # Verify YAML is valid by parsing it
    try:
        parsed = yaml.safe_load(yaml_str)
        parsing_succeeded = True
    except yaml.YAMLError as e:
        parsing_succeeded = False
        pytest.fail(f"Serialized YAML is not valid: {e}")

    assert parsing_succeeded, "Serialized YAML must be parseable"

    # Verify formatting (should contain newlines for readability)
    assert "\n" in yaml_str, "YAML should be formatted with newlines for readability"


@given(config=valid_configuration(), format_type=st.sampled_from(["json", "yaml"]))
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_format
def test_config_format_produces_valid_syntax(config: Dict[str, Any], format_type: str):
    """
    Property: Configuration serialization must always produce syntactically valid output.

    **Validates: Requirements 9.1, 9.3, 9.4**

    This test verifies that:
    - Both JSON and YAML formats are syntactically valid
    - No syntax errors in serialized output
    - Standard parsers can read the output
    - Format validity is independent of configuration content
    """
    if format_type == "json":
        # Serialize to JSON
        serialized = json.dumps(config, indent=2)

        # Verify it's valid JSON
        try:
            json.loads(serialized)
            is_valid = True
        except json.JSONDecodeError:
            is_valid = False
    else:  # yaml
        # Serialize to YAML
        serialized = yaml.dump(config, default_flow_style=False, indent=2)

        # Verify it's valid YAML
        try:
            yaml.safe_load(serialized)
            is_valid = True
        except yaml.YAMLError:
            is_valid = False

    assert is_valid, f"Serialized {format_type.upper()} must be syntactically valid"

    # Verify output is not empty
    assert len(serialized) > 0, f"Serialized {format_type.upper()} should not be empty"


@given(config=valid_configuration())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_format
def test_config_format_consistency_across_serializations(config: Dict[str, Any]):
    """
    Property: Multiple serializations of the same configuration must produce equivalent results.

    **Validates: Requirements 9.1, 9.3, 9.4**

    This test verifies that:
    - Serialization is deterministic
    - Multiple serializations produce equivalent output
    - No randomness or state affects serialization
    """
    # Serialize to JSON multiple times
    json_str_1 = json.dumps(config, indent=2, sort_keys=True)
    json_str_2 = json.dumps(config, indent=2, sort_keys=True)
    json_str_3 = json.dumps(config, indent=2, sort_keys=True)

    # All JSON serializations should be identical
    assert json_str_1 == json_str_2 == json_str_3, "JSON serialization should be deterministic"

    # Serialize to YAML multiple times
    yaml_str_1 = yaml.dump(config, default_flow_style=False, indent=2, sort_keys=True)
    yaml_str_2 = yaml.dump(config, default_flow_style=False, indent=2, sort_keys=True)
    yaml_str_3 = yaml.dump(config, default_flow_style=False, indent=2, sort_keys=True)

    # All YAML serializations should be identical
    assert yaml_str_1 == yaml_str_2 == yaml_str_3, "YAML serialization should be deterministic"


@given(config=valid_configuration(), iterations=st.integers(min_value=2, max_value=5))
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_format
def test_config_format_validity_stable_over_iterations(config: Dict[str, Any], iterations: int):
    """
    Property: Configuration format validity must remain stable across multiple serializations.

    **Validates: Requirements 9.1, 9.3, 9.4**

    This test verifies that:
    - Format validity doesn't degrade over multiple operations
    - No state corruption occurs
    - Serialization can be repeated safely
    """
    # Perform multiple serialization-deserialization cycles
    for i in range(iterations):
        # JSON cycle
        json_str = json.dumps(config, indent=2)
        json_parsed = json.loads(json_str)

        # Verify JSON remains valid
        assert json_parsed is not None, f"JSON parsing failed on iteration {i+1}"

        # YAML cycle
        yaml_str = yaml.dump(config, default_flow_style=False, indent=2)
        yaml_parsed = yaml.safe_load(yaml_str)

        # Verify YAML remains valid
        assert yaml_parsed is not None, f"YAML parsing failed on iteration {i+1}"
