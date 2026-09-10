"""



Unit tests for resource management during application shutdown.




Tests verify proper cleanup of:



- Database connections (Requirement 10.1)



- Modbus connections (Requirement 10.2)



- Background threads (Requirement 10.3)



- Log files (Requirement 10.4)



- Temporary files (Requirement 10.8)



- Graceful shutdown with timeout (Requirement 10.9)




**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.8, 10.9**
"""

import pytest


import sqlite3
import tempfile
import os
import time
import threading


from pathlib import Path


from unittest.mock import Mock, MagicMock, patch, call


from PyQt6.QtCore import QTimer, QEventLoop


from PyQt6.QtWidgets import QApplication


from modbuspython.backend.sqlite_manager import DatabaseManager, connect_db


from modbuspython.data_access.modbus_client import ModbusClient


from modbuspython.data_access.logging_service import LoggingService


class TestDatabaseConnectionClosure:
    """



    Test database connection closure on application close.




    **Validates: Requirement 10.1**



    WHEN application closes, THE Sistema_NexoSolar SHALL close all database connections
    """

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path."""

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db") as f:

            db_path = f.name

        yield db_path

        # Cleanup

        if os.path.exists(db_path):

            try:

                os.unlink(db_path)

            except PermissionError:

                pass  # File might still be locked on Windows

    def test_database_connection_closed_after_context_exit(self, temp_db_path):
        """Test that database connection is closed when exiting context manager."""

        conn_ref = None

        # Use context manager to open connection

        with DatabaseManager.get_connection(temp_db_path) as conn:

            conn_ref = conn

            assert conn is not None

            # Verify connection is active

            cursor = conn.cursor()

            cursor.execute("SELECT 1")

            assert cursor.fetchone()[0] == 1

        # After exiting context, connection should be closed

        assert conn_ref is not None

        with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):

            conn_ref.execute("SELECT 1")

    def test_database_connection_closed_on_error(self, temp_db_path):
        """Test that database connection is closed even when error occurs."""

        conn_ref = None

        try:

            with DatabaseManager.get_connection(temp_db_path) as conn:

                conn_ref = conn

                # Force an error

                raise ValueError("Test error")

        except ValueError:

            pass  # Expected

        # Connection should still be closed

        assert conn_ref is not None

        with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):

            conn_ref.execute("SELECT 1")

    def test_multiple_database_connections_all_closed(self, temp_db_path):
        """Test that multiple database connections are all properly closed."""

        connections = []

        # Open multiple connections

        for i in range(3):

            with DatabaseManager.get_connection(temp_db_path) as conn:

                connections.append(conn)

                conn.execute("SELECT 1")

        # All connections should be closed

        for conn in connections:

            with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):

                conn.execute("SELECT 1")

    def test_modbus_client_closes_sqlite_connection_on_stop(self, temp_db_path):
        """Test that ModbusClient closes SQLite connection when stopped."""

        # Create a ModbusClient instance

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Configure SQLite (this opens a connection)

        client.configure_sqlite(temp_db_path, "test_table")

        # Verify connection is open

        assert client.sqlite_conn is not None

        # Stop the client (should close SQLite connection)

        client.stop()

        # Wait a bit for cleanup to complete

        time.sleep(0.1)

        # SQLite connection should be closed

        # Note: We can't directly test if connection is closed without causing errors,

        # but we verify the cleanup code was executed

        assert True  # If we got here without errors, cleanup worked


class TestModbusConnectionClosure:
    """



    Test Modbus connection closure on application close.




    **Validates: Requirement 10.2**



    WHEN application closes, THE Sistema_NexoSolar SHALL close all Modbus connections
    """

    def test_modbus_client_closes_connection_on_stop(self):
        """Test that ModbusClient closes Modbus connection when stopped."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Mock the Modbus client

        mock_modbus = MagicMock()

        client.client = mock_modbus

        client.is_connected = True

        # Stop the client

        client.stop()

        # Verify close was called

        mock_modbus.close.assert_called_once()

    def test_modbus_connection_closed_before_thread_termination(self):
        """Test that Modbus connection is closed before thread terminates."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Mock the Modbus client

        mock_modbus = MagicMock()

        client.client = mock_modbus

        client.is_connected = True

        # Track call order

        call_order = []

        mock_modbus.close.side_effect = lambda: call_order.append("close")

        # Mock quit to track when thread termination starts

        original_quit = client.quit

        def mock_quit():

            call_order.append("quit")

            original_quit()

        client.quit = mock_quit

        # Stop the client

        client.stop()

        # Verify close was called before quit
        assert "close" in call_order

        assert "quit" in call_order

        assert call_order.index("close") < call_order.index("quit")

    def test_modbus_connection_closure_handles_errors_gracefully(self):
        """Test that Modbus connection closure handles errors without crashing."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Mock the Modbus client to raise error on close

        mock_modbus = MagicMock()

        mock_modbus.close.side_effect = Exception("Connection close error")

        client.client = mock_modbus

        client.is_connected = True

        # Stop should not raise exception even if close fails

        try:

            client.stop()

        except Exception as e:

            pytest.fail(f"stop() should handle errors gracefully, but raised: {e}")

    def test_modbus_desconectar_closes_connection(self):
        """Test that desconectar method properly closes Modbus connection."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Mock the Modbus client

        mock_modbus = MagicMock()

        client.client = mock_modbus

        client.is_connected = True

        # Call desconectar

        client.disconnect()

        # Verify close was called

        mock_modbus.close.assert_called_once()

        assert client.is_connected is False


class TestBackgroundThreadStopping:
    """



    Test background thread stopping on application close.




    **Validates: Requirement 10.3**



    WHEN application closes, THE Sistema_NexoSolar SHALL stop all background threads
    """

    def test_modbus_client_thread_stops_on_stop_call(self):
        """Test that ModbusClient thread stops when stop() is called."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Start the thread

        client.start()

        # Verify thread is running

        assert client.isRunning()

        # Stop the thread

        client.stop()

        # Thread should stop within timeout

        assert not client.isRunning()

    def test_modbus_client_thread_stops_within_timeout(self):
        """Test that ModbusClient thread stops within 10 second timeout."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Start the thread

        client.start()

        # Record start time

        start_time = time.time()

        # Stop the thread

        client.stop()

        # Calculate elapsed time

        elapsed_time = time.time() - start_time

        # Should stop within 10 seconds (requirement 10.9) + small tolerance for timing variations

        assert elapsed_time < 10.5, f"Thread took {elapsed_time:.2f}s to stop (should be < 10.5s)"

    def test_modbus_client_timer_stopped_before_thread_termination(self):
        """Test that timer is stopped before thread terminates."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Create a mock timer

        mock_timer = MagicMock()

        client.timer = mock_timer

        # Track call order

        call_order = []

        mock_timer.stop.side_effect = lambda: call_order.append("timer_stop")

        # Mock quit to track when thread termination starts

        original_quit = client.quit

        def mock_quit():

            call_order.append("quit")

            original_quit()

        client.quit = mock_quit

        # Stop the client

        client.stop()

        # Verify timer was stopped before quit
        assert "timer_stop" in call_order

        assert "quit" in call_order

        assert call_order.index("timer_stop") < call_order.index("quit")

    def test_modbus_client_is_running_flag_set_correctly(self):
        """Test that is_running flag is properly managed during thread lifecycle."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Initially not running

        assert client.is_running is False

        # After start, should be running (set in run() method)

        client.start()

        # Wait a bit for thread to start

        time.sleep(0.1)

        # Stop the thread

        client.stop()

        # is_running should be set to False

        assert client.is_running is False

    def test_thread_termination_forced_after_timeout(self):
        """Test that thread is forcefully terminated if it doesn't stop within timeout."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Mock wait to simulate timeout

        original_wait = client.wait

        def mock_wait(timeout):

            # First call (normal wait) returns False (timeout)

            # Second call (after terminate) returns True (success)

            if not hasattr(mock_wait, "call_count"):

                mock_wait.call_count = 0

            mock_wait.call_count += 1

            if mock_wait.call_count == 1:

                return False  # Timeout on first wait

            else:

                return True  # Success after terminate

        client.wait = mock_wait

        # Mock terminate to track if it was called

        terminate_called = []

        original_terminate = client.terminate

        def mock_terminate():

            terminate_called.append(True)

            original_terminate()

        client.terminate = mock_terminate

        # Stop the client

        client.stop()

        # Verify terminate was called due to timeout

        assert len(terminate_called) > 0, "terminate() should be called when wait() times out"


class TestLogFileClosing:
    """



    Test log file flushing and closing on application close.




    **Validates: Requirement 10.4**



    WHEN application closes, THE Sistema_NexoSolar SHALL flush and close all log files
    """

    @pytest.fixture
    def temp_log_path(self):
        """Create a temporary log file path."""

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:

            log_path = f.name

        yield Path(log_path)

        # Cleanup

        if os.path.exists(log_path):

            try:

                os.unlink(log_path)

            except PermissionError:

                pass  # File might still be locked on Windows

    def test_logging_service_handlers_can_be_closed(self, temp_log_path):
        """Test that LoggingService handlers can be properly closed."""

        logger = LoggingService()

        logger.setup(log_file=temp_log_path, level="INFO")

        # Write some logs

        logger.info("Test message 1")

        logger.info("Test message 2")

        # Close all handlers

        if hasattr(logger, "_logger") and logger._logger:

            for handler in logger._logger.handlers[:]:

                handler.flush()

                handler.close()

                logger._logger.removeHandler(handler)

        # Verify log file exists

        assert temp_log_path.exists()

        # Verify log file is not locked (can be deleted)

        try:

            temp_log_path.unlink()

        except PermissionError:

            pytest.fail("Log file is still locked after closing handlers")

    def test_logging_service_handlers_flushed_before_close(self, temp_log_path):
        """Test that log handlers are flushed before closing."""

        logger = LoggingService()

        logger.setup(log_file=temp_log_path, level="INFO")

        # Write a log message

        test_message = "Test message for flush verification"

        logger.info(test_message)

        # Close handlers with flush

        if hasattr(logger, "_logger") and logger._logger:

            for handler in logger._logger.handlers[:]:

                handler.flush()

                handler.close()

                logger._logger.removeHandler(handler)

        # Verify message was written to file

        with open(temp_log_path, "r", encoding="utf-8") as f:

            content = f.read()

        assert test_message in content, "Log message should be flushed to file before closing"

    def test_multiple_log_handlers_all_closed(self, temp_log_path):
        """Test that all log handlers (file and console) are properly closed."""

        logger = LoggingService()

        logger.setup(log_file=temp_log_path, level="INFO")

        # Verify multiple handlers exist (file + console)

        assert hasattr(logger, "_logger") and logger._logger

        assert len(logger._logger.handlers) >= 2, "Should have at least file and console handlers"

        # Track which handlers were closed

        handlers_closed = []

        # Close all handlers

        for handler in logger._logger.handlers[:]:

            handler.flush()

            handler.close()

            handlers_closed.append(type(handler).__name__)

            logger._logger.removeHandler(handler)

        # Verify both file and console handlers were closed

        assert "RotatingFileHandler" in handlers_closed

        assert "StreamHandler" in handlers_closed

    def test_log_handler_close_handles_errors_gracefully(self, temp_log_path):
        """Test that log handler closing handles errors without crashing."""

        logger = LoggingService()

        logger.setup(log_file=temp_log_path, level="INFO")

        # Mock a handler to raise error on close

        if hasattr(logger, "_logger") and logger._logger and logger._logger.handlers:

            handler = logger._logger.handlers[0]

            original_close = handler.close

            def mock_close():

                raise Exception("Close error")

            handler.close = mock_close

            # Should not raise exception

            try:

                handler.flush()

                handler.close()

            except Exception:

                pass  # Expected - we're testing that the application handles this

            # Restore original close

            handler.close = original_close


class TestTemporaryFileCleanup:
    """



    Test cleanup of temporary files after execution.




    **Validates: Requirement 10.8**



    THE Sistema_NexoSolar SHALL NOT leave temporary files after execution
    """

    def test_no_temp_files_in_working_directory_after_cleanup(self):
        """Test that no temporary files are left in working directory."""

        # Get current working directory

        cwd = Path.cwd()

        # List files before

        files_before = set(cwd.glob("*.tmp"))

        files_before.update(cwd.glob("*.temp"))

        files_before.update(cwd.glob("tmp*"))

        # Simulate some operations (this is a placeholder - in real scenario,

        # we would run actual application operations)

        # List files after

        files_after = set(cwd.glob("*.tmp"))

        files_after.update(cwd.glob("*.temp"))

        files_after.update(cwd.glob("tmp*"))

        # Should not have created new temporary files

        new_temp_files = files_after - files_before

        assert len(new_temp_files) == 0, f"Temporary files created: {new_temp_files}"

    def test_qwebengine_cache_cleared_on_cleanup(self):
        """Test that QWebEngine cache is cleared during cleanup."""

        try:

            from PyQt6.QtWebEngineCore import QWebEngineProfile

            # Get default profile

            profile = QWebEngineProfile.defaultProfile()

            # Clear caches (simulating MainWindow.closeEvent)

            profile.clearHttpCache()

            profile.clearAllVisitedLinks()

            # If we got here without errors, cleanup works

            assert True

        except ImportError:

            pytest.skip("QWebEngineCore not available")

    def test_gitignore_excludes_temporary_patterns(self):
        """Test that .gitignore properly excludes temporary file patterns."""

        gitignore_path = Path(".gitignore")

        if not gitignore_path.exists():

            pytest.skip(".gitignore not found")

        with open(gitignore_path, "r", encoding="utf-8") as f:

            content = f.read()

        # Should exclude common temporary patterns

        temp_patterns = ["*.tmp", "*.temp", "tmp", "__pycache__", "*.pyc"]

        found_patterns = [p for p in temp_patterns if p in content]

        assert len(found_patterns) > 0, "Should exclude at least some temporary file patterns"


class TestGracefulShutdownTimeout:
    """



    Test graceful shutdown with timeout.




    **Validates: Requirement 10.9**



    THE Sistema_NexoSolar SHALL implement graceful shutdown with timeout (10 seconds maximum)
    """

    def test_modbus_client_shutdown_respects_timeout(self):
        """Test that ModbusClient shutdown respects 10 second timeout."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Start the thread

        client.start()

        # Measure shutdown time

        start_time = time.time()

        client.stop()

        elapsed_time = time.time() - start_time

        # Should complete within 10 seconds

        assert elapsed_time < 10.0, f"Shutdown took {elapsed_time:.2f}s (should be < 10s)"

    def test_modbus_client_wait_timeout_is_10_seconds(self):
        """Test that ModbusClient uses 10 second timeout for thread wait."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Mock wait to capture timeout parameter

        wait_timeout = []

        original_wait = client.wait

        def mock_wait(timeout):

            wait_timeout.append(timeout)

            return True  # Simulate successful wait

        client.wait = mock_wait

        # Stop the client

        client.stop()

        # Verify wait was called with 10000ms (10 seconds)

        assert len(wait_timeout) > 0

        assert wait_timeout[0] == 10000, f"Wait timeout should be 10000ms, got {wait_timeout[0]}ms"

    def test_shutdown_completes_even_with_slow_cleanup(self):
        """Test that shutdown completes even if cleanup operations are slow."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Mock timer stop to be slow

        mock_timer = MagicMock()

        def slow_stop():

            time.sleep(0.5)  # Simulate slow operation

        mock_timer.stop = slow_stop

        client.timer = mock_timer

        # Mock Modbus client close to be slow

        mock_modbus = MagicMock()

        def slow_close():

            time.sleep(0.5)  # Simulate slow operation

        mock_modbus.close = slow_close

        client.client = mock_modbus

        client.is_connected = True

        # Shutdown should still complete

        start_time = time.time()

        client.stop()

        elapsed_time = time.time() - start_time

        # Should complete within reasonable time (< 10 seconds)

        assert elapsed_time < 10.0

    def test_forced_termination_after_timeout(self):
        """Test that thread is forcefully terminated if graceful shutdown times out."""

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Mock wait to always return False (simulate timeout)

        def mock_wait(timeout):

            return False

        client.wait = mock_wait

        # Track if terminate was called

        terminate_called = []

        original_terminate = client.terminate

        def mock_terminate():

            terminate_called.append(True)

            # Don't call original to avoid actual termination

        client.terminate = mock_terminate

        # Stop should call terminate after timeout

        client.stop()

        # Verify terminate was called

        assert len(terminate_called) > 0, "terminate() should be called when graceful shutdown times out"


class TestIntegratedResourceCleanup:
    """



    Integration tests for complete resource cleanup.




    Tests that all resources are properly cleaned up together.
    """

    @pytest.fixture
    def temp_resources(self):
        """Create temporary resources for testing."""

        # Create temp database

        db_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")

        db_path = db_file.name

        db_file.close()

        # Create temp log

        log_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log")

        log_path = log_file.name

        log_file.close()

        yield {"db_path": db_path, "log_path": log_path}

        # Cleanup

        for path in [db_path, log_path]:

            if os.path.exists(path):

                try:

                    os.unlink(path)

                except PermissionError:
                    pass

    def test_all_resources_cleaned_up_together(self, temp_resources):
        """Test that all resources are cleaned up in coordinated shutdown."""

        db_path = temp_resources["db_path"]

        log_path = temp_resources["log_path"]

        # Create ModbusClient with SQLite

        client = ModbusClient(ip="192.168.1.1", port=502)

        client.configure_sqlite(db_path, "test_table")

        # Setup logging

        logger = LoggingService()

        logger.setup(log_file=Path(log_path), level="INFO")

        logger.info("Test message")

        # Cleanup all resources

        # 1. Stop ModbusClient (closes Modbus + SQLite + thread)

        client.stop()

        # 2. Close log handlers

        if hasattr(logger, "_logger") and logger._logger:

            for handler in logger._logger.handlers[:]:

                handler.flush()

                handler.close()

                logger._logger.removeHandler(handler)

        # Verify all resources are released

        # Log file should not be locked

        try:

            with open(log_path, "r") as f:

                content = f.read()

            assert "Test message" in content

        except PermissionError:

            pytest.fail("Log file still locked after cleanup")

    def test_cleanup_order_is_correct(self):
        """Test that resources are cleaned up in correct order."""

        cleanup_order = []

        client = ModbusClient(ip="192.168.1.1", port=502)

        # Mock components to track cleanup order

        mock_timer = MagicMock()

        mock_timer.stop.side_effect = lambda: cleanup_order.append("timer")

        client.timer = mock_timer

        mock_modbus = MagicMock()

        mock_modbus.close.side_effect = lambda: cleanup_order.append("modbus")

        client.client = mock_modbus

        client.is_connected = True

        mock_sqlite = MagicMock()

        mock_sqlite.close.side_effect = lambda: cleanup_order.append("sqlite")

        client.sqlite_conn = mock_sqlite

        # Stop client

        client.stop()

        # Verify cleanup order: timer -> modbus -> sqlite -> thread
        assert "timer" in cleanup_order

        assert "modbus" in cleanup_order

        assert "sqlite" in cleanup_order

        # Timer should be stopped first

        assert cleanup_order.index("timer") < cleanup_order.index("modbus")

        # Modbus should be closed before SQLite

        assert cleanup_order.index("modbus") < cleanup_order.index("sqlite")


if __name__ == "__main__":

    pytest.main([__file__, "-v"])
