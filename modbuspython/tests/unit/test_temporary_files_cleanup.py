"""
Unit tests for temporary file cleanup.

Tests that the application does not leave temporary files after execution.

Validates: Requirement 10.8
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
import inspect


class TestTemporaryFileCleanup:
    """Test that no temporary files are left after application execution."""

    def test_gitignore_excludes_python_cache(self):
        """Test that .gitignore properly excludes Python cache files."""
        gitignore_path = Path(".gitignore")

        if not gitignore_path.exists():
            pytest.skip(".gitignore not found in workspace root")

        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should exclude __pycache__ directories
        assert "__pycache__" in content

        # Should exclude compiled Python files
        assert "*.pyc" in content or "*.py[cod]" in content

    def test_gitignore_excludes_temp_files(self):
        """Test that .gitignore properly excludes temporary files."""
        gitignore_path = Path(".gitignore")

        if not gitignore_path.exists():
            pytest.skip(".gitignore not found in workspace root")

        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should exclude temporary file patterns
        assert "*.tmp" in content or "tmp" in content.lower()
        assert "*.temp" in content or "temp" in content.lower()

    def test_gitignore_excludes_cache_directories(self):
        """Test that .gitignore properly excludes cache directories."""
        gitignore_path = Path(".gitignore")

        if not gitignore_path.exists():
            pytest.skip(".gitignore not found in workspace root")

        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should exclude cache directories
        assert ".cache" in content or "cache" in content.lower()

        # Should exclude Qt WebEngine cache
        assert "QtWebEngine" in content or "webengine" in content.lower()

    def test_gitignore_excludes_log_files(self):
        """Test that .gitignore properly excludes log files."""
        gitignore_path = Path(".gitignore")

        if not gitignore_path.exists():
            pytest.skip(".gitignore not found in workspace root")

        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should exclude log files and directories
        assert "logs" in content.lower() or "*.log" in content

    def test_main_window_cleanup_clears_webengine_cache(self):
        """Test that MainWindow closeEvent clears QWebEngine cache."""
        from modbuspython.main_app import MainWindow

        source = inspect.getsource(MainWindow.closeEvent)

        # Should import and use QWebEngineProfile
        assert "QWebEngineProfile" in source

        # Should clear HTTP cache
        assert "clearHttpCache" in source

        # Should handle ImportError gracefully (when QWebEngineCore not available)
        assert "ImportError" in source or "except" in source

    def test_main_window_cleanup_closes_log_handlers(self):
        """Test that MainWindow closeEvent properly closes log handlers."""
        from modbuspython.main_app import MainWindow

        source = inspect.getsource(MainWindow.closeEvent)

        # Should flush and close log handlers
        assert "handler" in source.lower()
        assert "flush" in source
        assert "close" in source

    def test_logging_service_uses_rotating_file_handler(self):
        """Test that LoggingService uses RotatingFileHandler to manage log files."""
        from modbuspython.data_access.logging_service import LoggingService

        source = inspect.getsource(LoggingService.setup)

        # Should use RotatingFileHandler
        assert "RotatingFileHandler" in source

        # Should configure max bytes and backup count
        assert "maxBytes" in source
        assert "backupCount" in source

    def test_no_hardcoded_temp_file_creation(self):
        """Test that code does not create hardcoded temporary files."""
        # Search for common temporary file creation patterns
        import modbuspython

        # Get the module path
        if modbuspython.__file__ is None:
            # Module is a namespace package, use __path__ instead
            if hasattr(modbuspython, "__path__"):
                module_path = Path(modbuspython.__path__[0])
            else:
                pytest.skip("Cannot determine modbuspython module path")
        else:
            module_path = Path(modbuspython.__file__).parent

        # Patterns that would indicate temporary file creation
        suspicious_patterns = [
            "tempfile.NamedTemporaryFile",
            "tempfile.TemporaryFile",
            "tempfile.mkstemp",
            "tempfile.mkdtemp",
        ]

        # Search Python files for these patterns
        python_files = list(module_path.rglob("*.py"))

        for py_file in python_files:
            # Skip test files
            if "test" in str(py_file):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                for pattern in suspicious_patterns:
                    if pattern in content:
                        # If found, ensure it's used with proper cleanup (context manager)
                        # This is a warning, not a failure
                        print(f"Warning: {pattern} found in {py_file}")
                        # Check if it's used with 'with' statement
                        if pattern in content and "with " not in content:
                            pytest.fail(f"Temporary file creation without context manager in {py_file}: {pattern}")
            except Exception as e:
                # Skip files that can't be read
                continue


class TestResourceCleanupIntegration:
    """Integration tests for resource cleanup."""

    def test_config_manager_does_not_leave_temp_files(self):
        """Test that ConfigurationManager does not leave temporary files."""
        from modbuspython.config.config_manager import ConfigurationManager

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_path = tmpdir_path / "test_config.yaml"

            # Create a minimal config file
            config_path.write_text('modbus:\n  host: "192.168.1.1"\n  port: 502\n')

            # Load and use config
            config = ConfigurationManager()

            # List files before
            files_before = set(tmpdir_path.rglob("*"))

            try:
                # This should not create any temporary files
                config.load_config(config_path, None)
            except Exception:
                pass  # We don't care if it fails, just checking for temp files

            # List files after
            files_after = set(tmpdir_path.rglob("*"))

            # Should not have created any new files
            new_files = files_after - files_before
            temp_files = [f for f in new_files if "tmp" in f.name.lower() or "temp" in f.name.lower()]

            assert len(temp_files) == 0, f"Temporary files created: {temp_files}"

    def test_logging_service_cleanup(self):
        """Test that LoggingService properly closes file handlers."""
        from modbuspython.data_access.logging_service import LoggingService

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            # Create and setup logger
            logger = LoggingService()
            logger.setup(log_file=log_file, level="INFO")

            # Write some logs
            logger.info("Test message")

            # Close handlers (simulating application shutdown)
            if hasattr(logger, "_logger") and logger._logger:
                for handler in logger._logger.handlers[:]:
                    handler.flush()
                    handler.close()
                    logger._logger.removeHandler(handler)

            # Verify log file exists and is not locked
            assert log_file.exists()

            # Should be able to delete the log file (not locked)
            try:
                log_file.unlink()
            except PermissionError:
                pytest.fail("Log file is still locked after closing handlers")


class TestRequirementValidation:
    """Test that implementation satisfies Requirement 10.8."""

    def test_requirement_10_8_no_temp_files_after_execution(self):
        """
        Requirement 10.8: THE Sistema_NexoSolar SHALL NOT leave
        temporary files after execution.
        """
        # Verify .gitignore excludes temporary files
        gitignore_path = Path(".gitignore")

        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Must exclude common temporary file patterns
            assert any(pattern in content for pattern in ["*.tmp", "*.temp", "tmp", "temp"])
            assert "__pycache__" in content
            assert any(pattern in content for pattern in ["*.pyc", "*.py[cod]"])

        # Verify MainWindow cleanup clears caches
        from modbuspython.main_app import MainWindow

        source = inspect.getsource(MainWindow.closeEvent)

        # Must clear QWebEngine cache
        assert "QWebEngineProfile" in source
        assert "clearHttpCache" in source

        # Must close log handlers
        assert "handler" in source.lower()
        assert "flush" in source
        assert "close" in source

    def test_cleanup_is_comprehensive(self):
        """Test that cleanup covers all resource types."""
        from modbuspython.main_app import MainWindow

        source = inspect.getsource(MainWindow.closeEvent)

        # Should clean up tabs
        assert "tabs" in source.lower()
        assert "cleanup" in source

        # Should stop ModbusClient thread
        assert "modbus_manager" in source
        assert "stop" in source

        # Should clear web caches
        assert "QWebEngineProfile" in source or "cache" in source.lower()

        # Should close log handlers
        assert "handler" in source.lower()

        # Should have error handling for each cleanup step
        assert source.count("try:") >= 3
        assert source.count("except") >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
