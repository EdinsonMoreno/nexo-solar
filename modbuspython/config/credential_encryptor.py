"""Credential encryption utilities for SolarSense SCADA.

Provides Fernet symmetric encryption for sensitive configuration values
such as passwords, API keys, and tokens.
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
import logging

logger = logging.getLogger(__name__)


class CredentialEncryptor:
    """Handles encryption and decryption of sensitive configuration values.

    Uses Fernet symmetric encryption from the cryptography library.
    The encryption key should be stored securely (e.g., environment variable).

    Example:
        >>> encryptor = CredentialEncryptor()
        >>> encrypted = encryptor.encrypt("my_secret_password")
        >>> decrypted = encryptor.decrypt(encrypted)
    """

    def __init__(self, key: Optional[bytes] = None):
        """Initialize encryptor with encryption key.

        Args:
            key: Fernet encryption key (32 url-safe base64-encoded bytes).
                 If None, tries to load from SOLARSENSE_ENCRYPTION_KEY env var.
        """
        if key is None:
            key = self._load_key_from_env()

        if key is None:
            logger.warning("No encryption key provided. Encryption disabled.")
            self._fernet = None
        else:
            try:
                self._fernet = Fernet(key)
                logger.info("CredentialEncryptor initialized successfully")
            except Exception as e:
                logger.error(f"Invalid encryption key: {e}")
                self._fernet = None

    @staticmethod
    def generate_key() -> bytes:
        """Generate a new Fernet encryption key.

        Returns:
            Bytes containing the new encryption key
        """
        key: bytes = Fernet.generate_key()
        return key

    @staticmethod
    def _load_key_from_env() -> Optional[bytes]:
        """Load encryption key from environment variable.

        Returns:
            Encryption key bytes or None if not set
        """
        key_str = os.environ.get("SOLARSENSE_ENCRYPTION_KEY")
        if key_str:
            return key_str.encode("utf-8")
        return None

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a sensitive value.

        Args:
            plaintext: String value to encrypt

        Returns:
            Encrypted value as base64-encoded string prefixed with 'ENC:'

        Raises:
            ValueError: If encryption is not configured
        """
        if self._fernet is None:
            raise ValueError("Encryption not configured. Set SOLARSENSE_ENCRYPTION_KEY environment variable.")

        encrypted = self._fernet.encrypt(plaintext.encode("utf-8"))
        return f"ENC:{base64.urlsafe_b64encode(encrypted).decode('utf-8')}"

    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt an encrypted value.

        Args:
            encrypted_value: Encrypted string (with or without 'ENC:' prefix)

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If encryption is not configured or decryption fails
        """
        if self._fernet is None:
            raise ValueError("Encryption not configured. Set SOLARSENSE_ENCRYPTION_KEY environment variable.")

        try:
            if encrypted_value.startswith("ENC:"):
                encoded = encrypted_value[4:]
            else:
                encoded = encrypted_value

            encrypted_bytes = base64.urlsafe_b64decode(encoded)
            decrypted = self._fernet.decrypt(encrypted_bytes)
            result: str = decrypted.decode("utf-8")
            return result
        except InvalidToken:
            logger.error("Failed to decrypt value: invalid token")
            raise ValueError("Failed to decrypt value: invalid or corrupted encrypted data")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt value: {e}")

    def is_encrypted(self, value: str) -> bool:
        """Check if a value appears to be encrypted.

        Args:
            value: String value to check

        Returns:
            True if value starts with 'ENC:' prefix
        """
        return value.startswith("ENC:")
