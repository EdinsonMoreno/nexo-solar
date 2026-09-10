"""
Centralized logging service for Nexo Solar application.

This module provides a singleton logging service with structured logging,
file rotation, and multiple output handlers (file and console).
Includes automatic masking of sensitive data in log messages.
"""

import re
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive data in log records.

    Automatically masks values that appear to be passwords, tokens, or keys
    in log messages and extra kwargs.
    """

    SENSITIVE_PATTERNS = [
        re.compile(r'(password["\s:=]+)["\']?([^"\'\s,}]+)', re.IGNORECASE),
        re.compile(r'(secret["\s:=]+)["\']?([^"\'\s,}]+)', re.IGNORECASE),
        re.compile(r'(token["\s:=]+)["\']?([^"\'\s,}]+)', re.IGNORECASE),
        re.compile(r'(api[_-]?key["\s:=]+)["\']?([^"\'\s,}]+)', re.IGNORECASE),
        re.compile(r'(authorization["\s:=]+)["\']?([^"\'\s,}]+)', re.IGNORECASE),
        re.compile(r"(ENC:)[A-Za-z0-9_./+=-]+", re.IGNORECASE),
    ]

    SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "apikey", "authorization", "credential"}

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record to mask sensitive data.

        Args:
            record: The log record to filter

        Returns:
            True to allow the record to be logged
        """
        record.msg = self._mask_string(str(record.msg))

        if hasattr(record, "args"):
            if isinstance(record.args, dict):
                record.args = {k: self._mask_value(k, v) for k, v in record.args.items()}

        for attr in ["exc_text", "stack_info"]:
            if hasattr(record, attr):
                val = getattr(record, attr)
                if val:
                    setattr(record, attr, self._mask_string(str(val)))

        return True

    def _mask_string(self, text: str) -> str:
        """Mask sensitive patterns in a string.

        Args:
            text: String to mask

        Returns:
            String with sensitive values masked
        """
        for pattern in self.SENSITIVE_PATTERNS:
            text = pattern.sub(r"\1****", text)
        return text

    def _mask_value(self, key: str, value: object) -> object:
        """Mask a value if its key is sensitive.

        Args:
            key: The key name
            value: The value to potentially mask

        Returns:
            Masked value or original
        """
        if isinstance(key, str) and any(s in key.lower() for s in self.SENSITIVE_KEYS):
            return "****"
        if isinstance(value, str):
            return self._mask_string(value)
        return value


class LoggingService:
    """Centralized logging service with rotation.

    This class implements the Singleton pattern to ensure a single logging
    configuration across the entire application. It provides structured logging
    with rotating file handlers and console output.

    Attributes:
        _instance: Singleton instance of LoggingService
        _logger: Python logging.Logger instance
        _initialized: Flag to prevent re-initialization
    """

    _instance: Optional["LoggingService"] = None

    def __new__(cls) -> "LoggingService":
        """Create or return the singleton instance.

        Returns:
            LoggingService: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logging service (only once)."""
        if not hasattr(self, "_initialized"):
            self._logger: Optional[logging.Logger] = None
            self._initialized = True

    def setup(self, log_file: Path, level: str = "INFO", max_bytes: int = 10485760, backup_count: int = 5) -> None:
        """Setup logging configuration with file rotation.

        Configures the logging system with:
        - Rotating file handler (rotates when file exceeds max_bytes)
        - Console handler for real-time output
        - Structured format with timestamp, level, module, function, and line number

        Args:
            log_file: Path to the log file
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Maximum size of log file before rotation (default: 10MB)
            backup_count: Number of backup log files to keep (default: 5)

        Example:
            >>> logger = LoggingService()
            >>> logger.setup(
            ...     log_file=Path("logs/nexo_solar.log"),
            ...     level="INFO",
            ...     max_bytes=10485760,
            ...     backup_count=5
            ... )
        """
        # Create logger instance
        self._logger = logging.getLogger("nexo-solar")
        self._logger.setLevel(getattr(logging, level.upper()))

        # Remove existing handlers to avoid duplicates
        self._logger.handlers.clear()

        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # File handler with rotation
        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        file_handler.setLevel(getattr(logging, level.upper()))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter with timestamp, level, module, function, line
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        sensitive_filter = SensitiveDataFilter()
        file_handler.addFilter(sensitive_filter)
        console_handler.addFilter(sensitive_filter)

        # Add handlers to logger
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message.

        Debug level is used for detailed diagnostic information useful during
        development and troubleshooting.

        Args:
            message: The log message
            **kwargs: Additional context to include in the log entry

        Example:
            >>> logger = LoggingService()
            >>> logger.debug("Modbus register read", address=0, value=180)
        """
        if self._logger:
            self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message.

        Info level is used for general informational messages that highlight
        the progress of the application.

        Args:
            message: The log message
            **kwargs: Additional context to include in the log entry

        Example:
            >>> logger = LoggingService()
            >>> logger.info("Application started successfully")
        """
        if self._logger:
            self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message.

        Warning level indicates something unexpected happened, but the application
        can continue to function normally.

        Args:
            message: The log message
            **kwargs: Additional context to include in the log entry

        Example:
            >>> logger = LoggingService()
            >>> logger.warning("Connection timeout, retrying...", attempt=2)
        """
        if self._logger:
            self._logger.warning(message, extra=kwargs)

    def error(self, message: str, exc_info: bool = True, **kwargs) -> None:
        """Log error message with optional exception info.

        Error level indicates a serious problem that prevented the application
        from performing a specific function.

        Args:
            message: The log message
            exc_info: Whether to include exception traceback (default: True)
            **kwargs: Additional context to include in the log entry

        Example:
            >>> logger = LoggingService()
            >>> try:
            ...     # some operation
            ...     pass
            ... except Exception as e:
            ...     logger.error("Failed to connect to Modbus device", host="192.168.1.100")
        """
        if self._logger:
            self._logger.error(message, exc_info=exc_info, extra=kwargs)

    def critical(self, message: str, exc_info: bool = True, **kwargs) -> None:
        """Log critical message with optional exception info.

        Critical level indicates a very serious error that may prevent the
        application from continuing to run.

        Args:
            message: The log message
            exc_info: Whether to include exception traceback (default: True)
            **kwargs: Additional context to include in the log entry

        Example:
            >>> logger = LoggingService()
            >>> logger.critical("Database corruption detected", db_path="/path/to/db")
        """
        if self._logger:
            self._logger.critical(message, exc_info=exc_info, extra=kwargs)
