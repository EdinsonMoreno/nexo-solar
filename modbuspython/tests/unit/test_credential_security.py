"""Security tests for SolarSense SCADA credential management.

Tests for:
- Environment variable loading
- Credential encryption/decryption
- Sensitive data masking in logs
- File permission checks
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from modbuspython.config.config_manager import ConfigurationManager
from modbuspython.config.credential_encryptor import CredentialEncryptor
from modbuspython.data_access.logging_service import SensitiveDataFilter


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def config_schema_path(temp_dir):
    """Create a minimal config schema for tests."""
    schema = {
        "type": "object",
        "properties": {
            "modbus": {
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
            "database": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
            },
        },
    }
    schema_path = temp_dir / "schema.json"
    schema_path.write_text(json.dumps(schema))
    return schema_path


class TestEnvironmentVariableLoading:
    """Tests for environment variable loading and expansion."""

    def test_load_env_file(self, temp_dir):
        """Test that .env file is loaded."""
        env_file = temp_dir / ".env"
        env_file.write_text("TEST_VAR=test_value\n")

        with patch.dict(os.environ, {}, clear=False):
            with patch.object(ConfigurationManager, "_load_env_variables", return_value=None):
                manager = ConfigurationManager()
                manager._load_env_variables = lambda: None

    def test_expand_env_vars_in_config(self):
        """Test environment variable expansion in config values."""
        with patch.dict(os.environ, {"TEST_HOST": "10.0.0.1", "TEST_PORT": "5020"}):
            manager = ConfigurationManager()
            config = {
                "modbus": {"host": "${TEST_HOST}", "port": "${TEST_PORT}"},
            }
            expanded = manager._expand_env_vars(config)
            assert expanded["modbus"]["host"] == "10.0.0.1"
            assert expanded["modbus"]["port"] == "5020"

    def test_expand_env_vars_keeps_unset(self):
        """Test that unset env vars keep their original reference."""
        manager = ConfigurationManager()
        config = {"modbus": {"host": "${UNSET_VAR_XYZ}"}}
        expanded = manager._expand_env_vars(config)
        assert expanded["modbus"]["host"] == "${UNSET_VAR_XYZ}"

    def test_detect_missing_env_vars(self):
        """Test detection of missing environment variables."""
        manager = ConfigurationManager()
        config = {"modbus": {"host": "${MISSING_VAR_ABC}"}}
        missing = []
        manager._check_for_unexpanded_vars(config, missing, "")
        assert "MISSING_VAR_ABC" in missing


class TestCredentialEncryptor:
    """Tests for credential encryption/decryption."""

    def test_generate_key(self):
        """Test key generation produces valid Fernet key."""
        key = CredentialEncryptor.generate_key()
        assert isinstance(key, bytes)
        assert len(key) == 44

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypted values can be decrypted."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(key=key)
        plaintext = "super_secret_password"

        encrypted = encryptor.encrypt(plaintext)
        assert encrypted.startswith("ENC:")

        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == plaintext

    def test_is_encrypted(self):
        """Test encrypted value detection."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(key=key)

        encrypted = encryptor.encrypt("secret")
        assert encryptor.is_encrypted(encrypted)
        assert not encryptor.is_encrypted("plain_text")
        assert not encryptor.is_encrypted("some_other_value")

    def test_decrypt_invalid_token(self):
        """Test that invalid tokens raise ValueError."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(key=key)

        with pytest.raises(ValueError):
            encryptor.decrypt("ENC:invalid_token_data")

    def test_encrypt_without_key_raises(self):
        """Test that encryption without key raises ValueError."""
        with patch.object(CredentialEncryptor, "_load_key_from_env", return_value=None):
            encryptor = CredentialEncryptor()
            with pytest.raises(ValueError, match="not configured"):
                encryptor.encrypt("secret")

    def test_decrypt_without_key_raises(self):
        """Test that decryption without key raises ValueError."""
        with patch.object(CredentialEncryptor, "_load_key_from_env", return_value=None):
            encryptor = CredentialEncryptor()
            with pytest.raises(ValueError, match="not configured"):
                encryptor.decrypt("ENC:some_data")


class TestSensitiveDataMasking:
    """Tests for sensitive data masking in configuration."""

    def test_mask_sensitive_key_in_set(self):
        """Test that sensitive keys are masked when set."""
        ConfigurationManager._instance = None
        manager = ConfigurationManager()
        manager._config = {}

        manager.set("database.password", "secret123")
        assert manager._config["database"]["password"] == "secret123"

    def test_mask_value_helper(self):
        """Test the _mask_sensitive_value helper."""
        ConfigurationManager._instance = None
        manager = ConfigurationManager()

        assert manager._mask_sensitive_value("password", "secret") == "****"
        assert manager._mask_sensitive_value("api_key", "key123") == "****"
        assert manager._mask_sensitive_value("modbus.host", "10.0.0.1") == "10.0.0.1"


class TestSensitiveDataFilter:
    """Tests for the SensitiveDataFilter logging filter."""

    def test_mask_password_in_message(self):
        """Test that passwords are masked in log messages."""
        log_filter = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='password="secret123"',
            args=(),
            exc_info=None,
        )
        log_filter.filter(record)
        assert "secret123" not in record.msg
        assert "****" in record.msg

    def test_mask_token_in_message(self):
        """Test that tokens are masked in log messages."""
        log_filter = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="token: abc123xyz",
            args=(),
            exc_info=None,
        )
        log_filter.filter(record)
        assert "abc123xyz" not in record.msg

    def test_mask_sensitive_key_in_kwargs(self):
        """Test that sensitive keys in kwargs are masked."""
        log_filter = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.args = {"password": "secret", "host": "10.0.0.1"}
        log_filter.filter(record)
        assert record.args["password"] == "****"
        assert record.args["host"] == "10.0.0.1"

    def test_mask_encrypted_values(self):
        """Test that ENC: prefixed values are masked."""
        log_filter = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="config: ENC:gAAAAAB",
            args=(),
            exc_info=None,
        )
        log_filter.filter(record)
        assert "gAAAAAB" not in record.msg
        assert "ENC:****" in record.msg


class TestFilePermissions:
    """Tests for file permission checks."""

    @pytest.mark.skipif(os.name != "posix", reason="Unix-specific permission test")
    def test_set_secure_permissions_unix(self, temp_dir):
        """Test setting restrictive permissions on Unix."""
        ConfigurationManager._instance = None
        manager = ConfigurationManager()

        test_file = temp_dir / "test_config.yaml"
        test_file.touch()

        manager._set_secure_permissions(test_file)

        mode = os.stat(test_file).st_mode & 0o777
        assert mode == 0o600

    @pytest.mark.skipif(os.name != "posix", reason="Unix-specific permission test")
    def test_check_insecure_permissions(self, temp_dir):
        """Test detection of insecure file permissions."""
        ConfigurationManager._instance = None
        manager = ConfigurationManager()

        test_file = temp_dir / "insecure_config.yaml"
        test_file.touch()
        os.chmod(test_file, 0o644)

        assert manager.check_config_permissions(test_file) is False

    @pytest.mark.skipif(os.name != "posix", reason="Unix-specific permission test")
    def test_check_secure_permissions(self, temp_dir):
        """Test acceptance of secure file permissions."""
        ConfigurationManager._instance = None
        manager = ConfigurationManager()

        test_file = temp_dir / "secure_config.yaml"
        test_file.touch()
        os.chmod(test_file, 0o600)

        assert manager.check_config_permissions(test_file) is True
