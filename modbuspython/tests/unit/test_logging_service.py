"""
Unit tests for LoggingService.

Tests the centralized logging service including singleton behavior,
file rotation, and logging methods.
"""

import pytest
import logging
from pathlib import Path
from modbuspython.data_access.logging_service import LoggingService


class TestLoggingService:
    """Unit tests for LoggingService."""

    def test_singleton_pattern(self):
        """Test that LoggingService implements singleton pattern."""
        logger1 = LoggingService()
        logger2 = LoggingService()

        assert logger1 is logger2, "LoggingService should return the same instance"

    def test_setup_creates_log_file(self, tmp_path):
        """Test that setup creates log file and directory."""
        log_file = tmp_path / "logs" / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="INFO")

        # Log a message to ensure file is created
        logger.info("Test message")

        assert log_file.exists(), "Log file should be created"
        assert log_file.parent.exists(), "Log directory should be created"

    def test_setup_with_different_levels(self, tmp_path):
        """Test setup with different logging levels."""
        log_file = tmp_path / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="DEBUG")

        # Verify logger level is set correctly
        assert logger._logger.level == logging.DEBUG

    def test_debug_logging(self, tmp_path):
        """Test debug level logging."""
        log_file = tmp_path / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="DEBUG")
        logger.debug("Debug message")

        # Read log file and verify message
        log_content = log_file.read_text()
        assert "DEBUG" in log_content
        assert "Debug message" in log_content

    def test_info_logging(self, tmp_path):
        """Test info level logging."""
        log_file = tmp_path / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="INFO")
        logger.info("Info message")

        log_content = log_file.read_text()
        assert "INFO" in log_content
        assert "Info message" in log_content

    def test_warning_logging(self, tmp_path):
        """Test warning level logging."""
        log_file = tmp_path / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="WARNING")
        logger.warning("Warning message")

        log_content = log_file.read_text()
        assert "WARNING" in log_content
        assert "Warning message" in log_content

    def test_error_logging(self, tmp_path):
        """Test error level logging."""
        log_file = tmp_path / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="ERROR")
        logger.error("Error message", exc_info=False)

        log_content = log_file.read_text()
        assert "ERROR" in log_content
        assert "Error message" in log_content

    def test_critical_logging(self, tmp_path):
        """Test critical level logging."""
        log_file = tmp_path / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="CRITICAL")
        logger.critical("Critical message", exc_info=False)

        log_content = log_file.read_text()
        assert "CRITICAL" in log_content
        assert "Critical message" in log_content

    def test_log_format_includes_required_fields(self, tmp_path):
        """Test that log format includes timestamp, level, module, function, line."""
        log_file = tmp_path / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="INFO")
        logger.info("Test message")

        log_content = log_file.read_text()

        # Check for timestamp (YYYY-MM-DD HH:MM:SS format)
        assert any(char.isdigit() for char in log_content), "Should contain timestamp"

        # Check for level
        assert "INFO" in log_content

        # Check for module name (logging_service is the module where the log method is)
        assert "logging_service" in log_content

        # Check for function name (info is the function that logs)
        assert "info" in log_content

        # Check for line number (should be a number after colon)
        assert any(f":{i}" in log_content for i in range(1, 200)), "Should contain line number"

    def test_rotating_file_handler_configuration(self, tmp_path):
        """Test that RotatingFileHandler is configured correctly."""
        log_file = tmp_path / "test.log"
        max_bytes = 1024  # 1 KB for testing
        backup_count = 3

        logger = LoggingService()
        logger.setup(log_file=log_file, level="INFO", max_bytes=max_bytes, backup_count=backup_count)

        # Find the RotatingFileHandler
        rotating_handler = None
        for handler in logger._logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                rotating_handler = handler
                break

        assert rotating_handler is not None, "Should have RotatingFileHandler"
        assert rotating_handler.maxBytes == max_bytes
        assert rotating_handler.backupCount == backup_count

    def test_logging_with_extra_context(self, tmp_path):
        """Test logging with additional context kwargs."""
        log_file = tmp_path / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="INFO")
        logger.info("Connection established", host="192.168.1.100", port=502)

        log_content = log_file.read_text()
        assert "Connection established" in log_content

    def test_multiple_setup_calls_clear_handlers(self, tmp_path):
        """Test that calling setup multiple times doesn't duplicate handlers."""
        log_file = tmp_path / "test.log"

        logger = LoggingService()
        logger.setup(log_file=log_file, level="INFO")
        initial_handler_count = len(logger._logger.handlers)

        # Call setup again
        logger.setup(log_file=log_file, level="DEBUG")
        final_handler_count = len(logger._logger.handlers)

        assert final_handler_count == initial_handler_count, "Handler count should remain the same"
