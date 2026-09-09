"""Property-based tests for configuration validation completeness.

This module contains property-based tests using Hypothesis to verify
that configuration validation is complete and catches all invalid configurations.

Property 7: Configuration Validation Completeness
**Validates: Requirements 2.9, 9.7**
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Dict, Any
import tempfile
from pathlib import Path
import json
import yaml

# Property 7: Configuration Validation Completeness
# **Validates: Requirements 2.9, 9.7**


@st.composite
def invalid_modbus_config(draw):
    """Generate invalid Modbus configurations."""
    return draw(
        st.one_of(
            # Missing required fields
            st.just({}),
            st.just({"host": "192.168.1.100"}),  # Missing port
            st.just({"port": 502}),  # Missing host
            # Invalid types
            st.builds(dict, host=st.integers(), port=st.integers(min_value=1, max_value=65535)),
            st.builds(dict, host=st.text(min_size=7, max_size=15), port=st.text()),
            # Invalid values
            st.builds(dict, host=st.just("999.999.999.999"), port=st.just(502)),
            st.builds(dict, host=st.just("192.168.1.100"), port=st.just(0)),
            st.builds(dict, host=st.just("192.168.1.100"), port=st.just(70000)),
        )
    )


@st.composite
def invalid_database_config(draw):
    """Generate invalid database configurations."""
    return draw(
        st.one_of(
            # Missing required fields
            st.just({}),
            st.just({"path": "data.db"}),  # Missing table_name
            st.just({"table_name": "measurements"}),  # Missing path
            # Invalid types
            st.builds(dict, path=st.integers(), table_name=st.text()),
            st.builds(dict, path=st.text(), table_name=st.integers()),
            # Invalid SQL identifiers
            st.builds(dict, path=st.just("data.db"), table_name=st.just("DROP TABLE")),
            st.builds(dict, path=st.just("data.db"), table_name=st.just("table; DROP")),
            st.builds(dict, path=st.just("data.db"), table_name=st.just("123invalid")),
        )
    )


@st.composite
def invalid_logging_config(draw):
    """Generate invalid logging configurations."""
    return draw(
        st.one_of(
            # Missing required fields
            st.just({}),
            st.just({"level": "INFO"}),  # Missing file_path
            # Invalid types
            st.builds(dict, level=st.integers(), file_path=st.text()),
            st.builds(dict, level=st.text(), file_path=st.integers()),
            # Invalid values
            st.builds(dict, level=st.just("INVALID_LEVEL"), file_path=st.just("app.log")),
            st.builds(dict, level=st.just("INFO"), file_path=st.just(""), max_bytes=st.just(-1)),
        )
    )


@st.composite
def invalid_angles_config(draw):
    """Generate invalid angles configurations."""
    return draw(
        st.one_of(
            # Missing required fields
            st.just({}),
            st.just({"rotation_min": 0}),  # Missing other fields
            # Invalid types
            st.builds(
                dict,
                rotation_min=st.text(),
                rotation_max=st.floats(min_value=0, max_value=360, allow_nan=False, allow_infinity=False),
                elevation_min=st.floats(min_value=0, max_value=145, allow_nan=False, allow_infinity=False),
                elevation_max=st.floats(min_value=0, max_value=145, allow_nan=False, allow_infinity=False),
            ),
            # Invalid ranges (min > max)
            st.builds(
                dict,
                rotation_min=st.just(360),
                rotation_max=st.just(0),
                elevation_min=st.just(0),
                elevation_max=st.just(145),
            ),
            st.builds(
                dict,
                rotation_min=st.just(0),
                rotation_max=st.just(360),
                elevation_min=st.just(145),
                elevation_max=st.just(0),
            ),
            # Out of range values
            st.builds(
                dict,
                rotation_min=st.just(-10),
                rotation_max=st.just(360),
                elevation_min=st.just(0),
                elevation_max=st.just(145),
            ),
            st.builds(
                dict,
                rotation_min=st.just(0),
                rotation_max=st.just(400),
                elevation_min=st.just(0),
                elevation_max=st.just(145),
            ),
            st.builds(
                dict,
                rotation_min=st.just(0),
                rotation_max=st.just(360),
                elevation_min=st.just(-10),
                elevation_max=st.just(145),
            ),
            st.builds(
                dict,
                rotation_min=st.just(0),
                rotation_max=st.just(360),
                elevation_min=st.just(0),
                elevation_max=st.just(200),
            ),
        )
    )


@given(modbus_config=invalid_modbus_config())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_validation
def test_invalid_modbus_config_rejected(modbus_config: Dict[str, Any]):
    """
    Property: Configuration validation must reject all invalid Modbus configurations.

    **Validates: Requirements 2.9, 9.7**

    This test verifies that:
    - Missing required fields are detected
    - Invalid types are rejected
    - Invalid values are rejected
    - Validation provides descriptive error messages
    """
    from modbuspython.config.config_manager import ConfigurationManager

    # Create a minimal config with invalid modbus section
    config = {
        "modbus": modbus_config,
        "database": {"path": "data.db", "table_name": "measurements"},
        "logging": {"level": "INFO", "file_path": "app.log"},
        "angles": {"rotation_min": 0, "rotation_max": 360, "elevation_min": 0, "elevation_max": 145},
    }

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
        yaml.dump(config, f)

    try:
        # Attempt to load configuration
        config_manager = ConfigurationManager()

        # Validation should either raise exception or return error
        try:
            config_manager.load_from_file(str(temp_path))
            # If it loads, check if validation detected the error
            is_valid = config_manager.validate()
            assert is_valid is False, f"Invalid Modbus config should be rejected: {modbus_config}"
        except (ValueError, KeyError, TypeError) as e:
            # Exception is expected for invalid config
            assert len(str(e)) > 0, "Error message should be descriptive"

    finally:
        if temp_path.exists():
            temp_path.unlink()


@given(database_config=invalid_database_config())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_validation
def test_invalid_database_config_rejected(database_config: Dict[str, Any]):
    """
    Property: Configuration validation must reject all invalid database configurations.

    **Validates: Requirements 2.9, 9.7**

    This test verifies that:
    - Missing required fields are detected
    - Invalid SQL identifiers are rejected
    - Invalid types are rejected
    - Validation provides descriptive error messages
    """
    from modbuspython.config.config_manager import ConfigurationManager

    # Create a minimal config with invalid database section
    config = {
        "modbus": {"host": "192.168.1.100", "port": 502},
        "database": database_config,
        "logging": {"level": "INFO", "file_path": "app.log"},
        "angles": {"rotation_min": 0, "rotation_max": 360, "elevation_min": 0, "elevation_max": 145},
    }

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
        yaml.dump(config, f)

    try:
        # Attempt to load configuration
        config_manager = ConfigurationManager()

        # Validation should either raise exception or return error
        try:
            config_manager.load_from_file(str(temp_path))
            # If it loads, check if validation detected the error
            is_valid = config_manager.validate()
            assert is_valid is False, f"Invalid database config should be rejected: {database_config}"
        except (ValueError, KeyError, TypeError) as e:
            # Exception is expected for invalid config
            assert len(str(e)) > 0, "Error message should be descriptive"

    finally:
        if temp_path.exists():
            temp_path.unlink()


@given(logging_config=invalid_logging_config())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_validation
def test_invalid_logging_config_rejected(logging_config: Dict[str, Any]):
    """
    Property: Configuration validation must reject all invalid logging configurations.

    **Validates: Requirements 2.9, 9.7**

    This test verifies that:
    - Missing required fields are detected
    - Invalid log levels are rejected
    - Invalid types are rejected
    - Validation provides descriptive error messages
    """
    from modbuspython.config.config_manager import ConfigurationManager

    # Create a minimal config with invalid logging section
    config = {
        "modbus": {"host": "192.168.1.100", "port": 502},
        "database": {"path": "data.db", "table_name": "measurements"},
        "logging": logging_config,
        "angles": {"rotation_min": 0, "rotation_max": 360, "elevation_min": 0, "elevation_max": 145},
    }

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
        yaml.dump(config, f)

    try:
        # Attempt to load configuration
        config_manager = ConfigurationManager()

        # Validation should either raise exception or return error
        try:
            config_manager.load_from_file(str(temp_path))
            # If it loads, check if validation detected the error
            is_valid = config_manager.validate()
            assert is_valid is False, f"Invalid logging config should be rejected: {logging_config}"
        except (ValueError, KeyError, TypeError) as e:
            # Exception is expected for invalid config
            assert len(str(e)) > 0, "Error message should be descriptive"

    finally:
        if temp_path.exists():
            temp_path.unlink()


@given(angles_config=invalid_angles_config())
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_validation
def test_invalid_angles_config_rejected(angles_config: Dict[str, Any]):
    """
    Property: Configuration validation must reject all invalid angles configurations.

    **Validates: Requirements 2.9, 9.7**

    This test verifies that:
    - Missing required fields are detected
    - Invalid ranges (min > max) are rejected
    - Out of range values are rejected
    - Invalid types are rejected
    - Validation provides descriptive error messages
    """
    from modbuspython.config.config_manager import ConfigurationManager

    # Create a minimal config with invalid angles section
    config = {
        "modbus": {"host": "192.168.1.100", "port": 502},
        "database": {"path": "data.db", "table_name": "measurements"},
        "logging": {"level": "INFO", "file_path": "app.log"},
        "angles": angles_config,
    }

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
        yaml.dump(config, f)

    try:
        # Attempt to load configuration
        config_manager = ConfigurationManager()

        # Validation should either raise exception or return error
        try:
            config_manager.load_from_file(str(temp_path))
            # If it loads, check if validation detected the error
            is_valid = config_manager.validate()
            assert is_valid is False, f"Invalid angles config should be rejected: {angles_config}"
        except (ValueError, KeyError, TypeError) as e:
            # Exception is expected for invalid config
            assert len(str(e)) > 0, "Error message should be descriptive"

    finally:
        if temp_path.exists():
            temp_path.unlink()


@given(
    config_section=st.sampled_from(["modbus", "database", "logging", "angles"]),
    iterations=st.integers(min_value=2, max_value=3),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.config_validation
def test_config_validation_is_deterministic(config_section: str, iterations: int):
    """
    Property: Configuration validation must be deterministic and consistent.

    **Validates: Requirements 2.9, 9.7**

    This test verifies that:
    - Validating the same configuration multiple times produces identical results
    - Validation result is stable and does not depend on call order
    - No internal state affects validation outcome
    """
    from modbuspython.config.config_manager import ConfigurationManager

    # Create a valid config
    config = {
        "modbus": {"host": "192.168.1.100", "port": 502},
        "database": {"path": "data.db", "table_name": "measurements"},
        "logging": {"level": "INFO", "file_path": "app.log"},
        "angles": {"rotation_min": 0, "rotation_max": 360, "elevation_min": 0, "elevation_max": 145},
    }

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
        yaml.dump(config, f)

    try:
        # Validate multiple times
        results = []
        for _ in range(iterations):
            config_manager = ConfigurationManager()
            config_manager.load_from_file(str(temp_path))
            is_valid = config_manager.validate()
            results.append(is_valid)

        # All results should be identical
        assert (
            len(set(results)) == 1
        ), f"Configuration validation for {config_section} is not deterministic. Results: {results}"

        # Valid config should always be valid
        assert all(results), f"Valid configuration should always pass validation"

    finally:
        if temp_path.exists():
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
