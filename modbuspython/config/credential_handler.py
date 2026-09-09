"""Credential handling for configuration values.

Handles encryption/decryption of sensitive configuration values
and masking for safe logging.
"""

from typing import Any, Dict, Optional, Set
import logging

from modbuspython.config.credential_encryptor import CredentialEncryptor


class CredentialHandler:
    """Handles sensitive configuration values.

    Provides encryption/decryption of sensitive values and
    masking for safe logging.
    """

    def __init__(self) -> None:
        """Initialize credential handler."""
        self._logger = logging.getLogger(__name__)
        self._sensitive_keys: Set[str] = {
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "api_key",
            "apikey",
            "auth",
        }
        self._encryptor: Optional[CredentialEncryptor] = None
        self._init_encryptor()

    def _init_encryptor(self) -> None:
        """Initialize credential encryptor if encryption key is available."""
        try:
            self._encryptor = CredentialEncryptor()
        except Exception as e:
            self._logger.warning(f"Failed to initialize credential encryptor: {e}")
            self._encryptor = None

    def decrypt_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively decrypt sensitive configuration values.

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with sensitive values decrypted
        """
        if self._encryptor is None:
            return config
        return self._decrypt_dict(config)

    def _decrypt_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive values in a dictionary.

        Args:
            d: Dictionary to process

        Returns:
            Dictionary with sensitive values decrypted
        """
        result: Dict[str, Any] = {}
        for k, v in d.items():
            if isinstance(v, dict):
                result[k] = self._decrypt_dict(v)
            elif isinstance(v, list):
                result[k] = [self._decrypt_value(k, item) for item in v]
            else:
                result[k] = self._decrypt_value(k, v)
        return result

    def _decrypt_value(self, key: str, value: Any) -> Any:
        """Decrypt a single value if it's sensitive and encrypted.

        Args:
            key: Configuration key
            value: Value to potentially decrypt

        Returns:
            Decrypted value or original if not encrypted
        """
        if not isinstance(value, str):
            return value
        if not any(sensitive in key.lower() for sensitive in self._sensitive_keys):
            return value
        if self._encryptor is None:
            return value
        if not self._encryptor.is_encrypted(value):
            return value
        try:
            return self._encryptor.decrypt(value)
        except ValueError:
            self._logger.warning(f"Failed to decrypt sensitive value for key: {key}")
            return value

    def mask_value(self, key: str, value: Any) -> str:
        """Mask sensitive values for safe logging.

        Args:
            key: Configuration key
            value: Configuration value

        Returns:
            Masked string representation safe for logging
        """
        if any(sensitive in key.lower() for sensitive in self._sensitive_keys):
            return "****"
        return str(value)
