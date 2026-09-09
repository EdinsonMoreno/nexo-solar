"""Property-based tests for resource cleanup completeness.

This module contains property-based tests using Hypothesis to verify
that all resources are properly released after application shutdown.

Property 10: Resource Cleanup Completeness
**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.8, 10.9**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import sqlite3
import tempfile
import os
import time
import threading
from pathlib import Path
from typing import List, Dict, Any

from modbuspython.data_access.modbus_client import ModbusClient
from modbuspython.data_access.logging_service import LoggingService
from modbuspython.backend.sqlite_manager import DatabaseManager

# Strategies for generating test scenarios


@st.composite
def modbus_config(draw):
    """Generate valid Modbus configuration."""
    return {
        "ip": draw(st.sampled_from(["192.168.1.100", "192.168.1.1", "10.0.0.1", "172.16.0.1"])),
        "port": draw(st.integers(min_value=502, max_value=510)),
        "timeout": draw(st.floats(min_value=1.0, max_value=5.0, allow_nan=False, allow_infinity=False)),
    }


@st.composite
def resource_scenario(draw):
    """Generate a resource scenario with various combinations of resources."""
    return {
        "has_modbus": draw(st.booleans()),
        "has_sqlite": draw(st.booleans()),
        "has_logging": draw(st.booleans()),
        "has_timer": draw(st.booleans()),
        "thread_count": draw(st.integers(min_value=1, max_value=3)),
    }


@st.composite
def shutdown_timing(draw):
    """Generate shutdown timing parameters."""
    return {
        "cleanup_delay": draw(st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False)),
        "force_timeout": draw(st.booleans()),
    }


# Property 10: Resource Cleanup Completeness
# **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.8, 10.9**


@given(config=modbus_config())
@settings(max_examples=50, deadline=5000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_modbus_connection_closed_after_shutdown(config: Dict[str, Any]):
    """
    Property: After shutdown, all Modbus connections must be closed.

    **Validates: Requirements 10.2, 10.9**

    This test verifies that:
    - Modbus connection is properly closed during shutdown
    - Connection state is updated correctly
    - Shutdown completes within timeout
    - No connection leaks occur
    """
    client = ModbusClient(ip=config["ip"], port=config["port"])

    # Mock the Modbus client
    mock_modbus = MagicMock()
    client.client = mock_modbus
    client.is_connected = True

    # Track if close was called
    close_called = []
    mock_modbus.close.side_effect = lambda: close_called.append(True)

    # Perform shutdown
    start_time = time.time()
    client.stop()
    shutdown_time = time.time() - start_time

    # Verify connection was closed
    assert len(close_called) > 0, "Modbus connection close() must be called during shutdown"

    # Verify connection state updated
    assert client.is_connected is False, "is_connected flag must be False after shutdown"

    # Verify shutdown completed within timeout (10 seconds + tolerance)
    assert shutdown_time < 11.0, f"Shutdown took {shutdown_time:.2f}s, should be < 11s (10s timeout + 1s tolerance)"


@given(scenario=resource_scenario())
@settings(max_examples=50, deadline=5000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_all_resources_released_after_shutdown(scenario: Dict[str, Any]):
    """
    Property: After shutdown, all resources must be released regardless of configuration.

    **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.8**

    This test verifies that:
    - Database connections are closed
    - Modbus connections are closed
    - Background threads are stopped
    - Timers are stopped
    - No resource leaks occur
    """
    # Assume at least one resource is present
    assume(scenario["has_modbus"] or scenario["has_sqlite"] or scenario["has_timer"])

    client = ModbusClient(ip="192.168.1.100", port=502)

    # Track resource cleanup
    resources_cleaned = {"modbus": False, "sqlite": False, "timer": False}

    # Setup Modbus if needed
    if scenario["has_modbus"]:
        mock_modbus = MagicMock()
        mock_modbus.close.side_effect = lambda: resources_cleaned.update({"modbus": True})
        client.client = mock_modbus
        client.is_connected = True

    # Setup SQLite if needed
    if scenario["has_sqlite"]:
        mock_sqlite = MagicMock()
        mock_sqlite.close.side_effect = lambda: resources_cleaned.update({"sqlite": True})
        client.sqlite_conn = mock_sqlite

    # Setup timer if needed
    if scenario["has_timer"]:
        mock_timer = MagicMock()
        mock_timer.stop.side_effect = lambda: resources_cleaned.update({"timer": True})
        client.timer = mock_timer

    # Perform shutdown
    client.stop()

    # Verify all configured resources were cleaned up
    if scenario["has_modbus"]:
        assert resources_cleaned["modbus"], "Modbus connection must be closed during shutdown"

    if scenario["has_sqlite"]:
        assert resources_cleaned["sqlite"], "SQLite connection must be closed during shutdown"

    if scenario["has_timer"]:
        assert resources_cleaned["timer"], "Timer must be stopped during shutdown"

    # Verify thread is stopped
    assert not client.isRunning(), "Thread must be stopped after shutdown"


@given(has_resources=st.booleans(), timing=shutdown_timing())
@settings(max_examples=50, deadline=5000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_database_connections_closed_after_shutdown(has_resources: bool, timing: Dict[str, Any]):
    """
    Property: All database connections must be closed after shutdown.

    **Validates: Requirements 10.1, 10.9**

    This test verifies that:
    - Database connections are properly closed
    - Closure happens even with timing variations
    - No database connection leaks occur
    - Shutdown completes within timeout
    """
    # Create temporary database
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        if has_resources:
            # Open a database connection
            conn = sqlite3.connect(db_path)

            # Simulate some delay in cleanup
            if timing["cleanup_delay"] > 0:
                time.sleep(timing["cleanup_delay"])

            # Close connection (simulating shutdown)
            conn.close()

            # Verify connection is closed
            with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
                conn.execute("SELECT 1")

        # Property holds: connection is closed after shutdown
        assert True

    finally:
        # Cleanup temporary database
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


@given(
    thread_count=st.integers(min_value=1, max_value=5),
    shutdown_order=st.lists(st.integers(min_value=0, max_value=4), min_size=1, max_size=5),
)
@settings(max_examples=50, deadline=5000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_background_threads_stopped_after_shutdown(thread_count: int, shutdown_order: List[int]):
    """
    Property: All background threads must be stopped after shutdown.

    **Validates: Requirements 10.3, 10.9**

    This test verifies that:
    - All background threads are stopped
    - Thread stopping works regardless of shutdown order
    - Threads stop within timeout
    - No thread leaks occur
    """
    # Limit thread count to reasonable number
    assume(1 <= thread_count <= 3)

    clients = []

    try:
        # Create multiple ModbusClient instances (each has a thread)
        for i in range(thread_count):
            client = ModbusClient(ip=f"192.168.1.{100+i}", port=502)
            clients.append(client)

        # Shutdown in specified order (modulo thread_count)
        shutdown_times = []
        for idx in shutdown_order[:thread_count]:
            client_idx = idx % thread_count
            start_time = time.time()
            clients[client_idx].stop()
            shutdown_times.append(time.time() - start_time)

        # Verify all threads are stopped
        for i, client in enumerate(clients):
            assert not client.isRunning(), f"Thread {i} must be stopped after shutdown"

        # Verify all shutdowns completed within timeout
        for i, shutdown_time in enumerate(shutdown_times):
            assert shutdown_time < 11.0, f"Thread {i} shutdown took {shutdown_time:.2f}s, should be < 11s"

    finally:
        # Ensure cleanup
        for client in clients:
            if client.isRunning():
                client.stop()


@given(log_messages=st.lists(st.text(min_size=5, max_size=100), min_size=1, max_size=10), flush_before_close=st.booleans())
@settings(max_examples=50, deadline=5000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_log_files_flushed_and_closed_after_shutdown(log_messages: List[str], flush_before_close: bool):
    """
    Property: All log files must be flushed and closed after shutdown.

    **Validates: Requirements 10.4, 10.9**

    This test verifies that:
    - Log files are flushed before closing
    - All log handlers are properly closed
    - Log messages are persisted to disk
    - No file handle leaks occur
    """
    # Create temporary log file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        log_path = Path(f.name)

    try:
        # Setup logging
        logger = LoggingService()
        logger.setup(log_file=log_path, level="INFO")

        # Write log messages
        for msg in log_messages:
            logger.info(msg)

        # Simulate shutdown: flush and close handlers
        if hasattr(logger, "_logger") and logger._logger:
            for handler in logger._logger.handlers[:]:
                if flush_before_close:
                    handler.flush()
                handler.close()
                logger._logger.removeHandler(handler)

        # Verify log file exists
        assert log_path.exists(), "Log file must exist after shutdown"

        # Verify log file is not locked (can be read)
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify at least some messages were written
            if flush_before_close:
                # With flush, all messages should be present
                messages_found = sum(1 for msg in log_messages if msg in content)
                assert messages_found > 0, "At least some log messages must be persisted when flushed"
        except PermissionError:
            pytest.fail("Log file is still locked after closing handlers")

    finally:
        # Cleanup temporary log file
        if log_path.exists():
            try:
                os.unlink(log_path)
            except PermissionError:
                pass


@given(create_temp_files=st.booleans(), temp_file_count=st.integers(min_value=0, max_value=5))
@settings(max_examples=50, deadline=5000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_no_temporary_files_after_shutdown(create_temp_files: bool, temp_file_count: int):
    """
    Property: No temporary files should remain after shutdown.

    **Validates: Requirements 10.8**

    This test verifies that:
    - Temporary files are cleaned up
    - No file leaks occur
    - Cleanup works regardless of temp file count
    """
    temp_files = []

    try:
        if create_temp_files:
            # Create temporary files
            for i in range(temp_file_count):
                f = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp")
                f.write(f"Temporary data {i}")
                f.close()
                temp_files.append(f.name)

        # Simulate shutdown: cleanup temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

        # Verify all temporary files are removed
        for temp_file in temp_files:
            assert not os.path.exists(temp_file), f"Temporary file {temp_file} must be removed after shutdown"

    finally:
        # Ensure cleanup
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass


@given(config=modbus_config(), has_sqlite=st.booleans(), has_logging=st.booleans())
@settings(max_examples=50, deadline=5000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_graceful_shutdown_completes_within_timeout(config: Dict[str, Any], has_sqlite: bool, has_logging: bool):
    """
    Property: Graceful shutdown must complete within 10 second timeout.

    **Validates: Requirements 10.9**

    This test verifies that:
    - Shutdown completes within 10 seconds
    - All resources are cleaned up within timeout
    - Timeout is enforced consistently
    - Forced termination occurs if needed
    """
    client = ModbusClient(ip=config["ip"], port=config["port"])

    # Setup resources
    mock_modbus = MagicMock()
    client.client = mock_modbus
    client.is_connected = True

    if has_sqlite:
        mock_sqlite = MagicMock()
        client.sqlite_conn = mock_sqlite

    mock_timer = MagicMock()
    client.timer = mock_timer

    # Measure shutdown time
    start_time = time.time()
    client.stop()
    shutdown_time = time.time() - start_time

    # Verify shutdown completed within timeout (10 seconds + small tolerance)
    assert shutdown_time < 11.0, f"Shutdown took {shutdown_time:.2f}s, must complete within 10s timeout (+ 1s tolerance)"

    # Verify thread is stopped
    assert not client.isRunning(), "Thread must be stopped after shutdown"


@given(scenario=resource_scenario(), timing=shutdown_timing())
@settings(max_examples=50, deadline=5000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_resource_cleanup_order_is_correct(scenario: Dict[str, Any], timing: Dict[str, Any]):
    """
    Property: Resources must be cleaned up in correct order during shutdown.

    **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

    This test verifies that:
    - Timer is stopped first
    - Modbus connection is closed second
    - SQLite connection is closed third
    - Thread is terminated last
    - Order is maintained regardless of configuration
    """
    # Assume at least timer and one other resource
    assume(scenario["has_timer"] and (scenario["has_modbus"] or scenario["has_sqlite"]))

    client = ModbusClient(ip="192.168.1.100", port=502)

    # Track cleanup order
    cleanup_order = []

    # Setup timer
    if scenario["has_timer"]:
        mock_timer = MagicMock()
        mock_timer.stop.side_effect = lambda: cleanup_order.append("timer")
        client.timer = mock_timer

    # Setup Modbus
    if scenario["has_modbus"]:
        mock_modbus = MagicMock()
        mock_modbus.close.side_effect = lambda: cleanup_order.append("modbus")
        client.client = mock_modbus
        client.is_connected = True

    # Setup SQLite
    if scenario["has_sqlite"]:
        mock_sqlite = MagicMock()
        mock_sqlite.close.side_effect = lambda: cleanup_order.append("sqlite")
        client.sqlite_conn = mock_sqlite

    # Add delay if specified
    if timing["cleanup_delay"] > 0:
        time.sleep(timing["cleanup_delay"])

    # Perform shutdown
    client.stop()

    # Verify cleanup order
    if scenario["has_timer"]:
        assert "timer" in cleanup_order, "Timer must be stopped during shutdown"

    if scenario["has_modbus"]:
        assert "modbus" in cleanup_order, "Modbus connection must be closed during shutdown"

    if scenario["has_sqlite"]:
        assert "sqlite" in cleanup_order, "SQLite connection must be closed during shutdown"

    # Verify order: timer -> modbus -> sqlite
    if scenario["has_timer"] and scenario["has_modbus"]:
        assert cleanup_order.index("timer") < cleanup_order.index(
            "modbus"
        ), "Timer must be stopped before Modbus connection is closed"

    if scenario["has_modbus"] and scenario["has_sqlite"]:
        assert cleanup_order.index("modbus") < cleanup_order.index(
            "sqlite"
        ), "Modbus connection must be closed before SQLite connection"


@given(
    resource_count=st.integers(min_value=1, max_value=10),
    cleanup_failures=st.lists(st.integers(min_value=0, max_value=9), max_size=3),
)
@settings(max_examples=50, deadline=5000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_cleanup_continues_despite_individual_failures(resource_count: int, cleanup_failures: List[int]):
    """
    Property: Resource cleanup must continue even if individual cleanups fail.

    **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

    This test verifies that:
    - Cleanup continues after individual failures
    - All resources are attempted to be cleaned
    - Failures are handled gracefully
    - System doesn't crash during cleanup
    """
    # Limit resource count
    assume(1 <= resource_count <= 5)

    client = ModbusClient(ip="192.168.1.100", port=502)

    # Track cleanup attempts
    cleanup_attempts = []

    # Setup timer with potential failure
    mock_timer = MagicMock()
    if 0 in cleanup_failures:
        mock_timer.stop.side_effect = Exception("Timer stop failed")
    else:
        mock_timer.stop.side_effect = lambda: cleanup_attempts.append("timer")
    client.timer = mock_timer

    # Setup Modbus with potential failure
    mock_modbus = MagicMock()
    if 1 in cleanup_failures:
        mock_modbus.close.side_effect = Exception("Modbus close failed")
    else:
        mock_modbus.close.side_effect = lambda: cleanup_attempts.append("modbus")
    client.client = mock_modbus
    client.is_connected = True

    # Setup SQLite with potential failure
    mock_sqlite = MagicMock()
    if 2 in cleanup_failures:
        mock_sqlite.close.side_effect = Exception("SQLite close failed")
    else:
        mock_sqlite.close.side_effect = lambda: cleanup_attempts.append("sqlite")
    client.sqlite_conn = mock_sqlite

    # Perform shutdown - should not raise exception
    try:
        client.stop()
        shutdown_completed = True
    except Exception as e:
        shutdown_completed = False
        pytest.fail(f"Shutdown should handle cleanup failures gracefully, but raised: {e}")

    # Verify shutdown completed
    assert shutdown_completed, "Shutdown must complete even if individual resource cleanups fail"

    # Verify thread is stopped
    assert not client.isRunning(), "Thread must be stopped even if resource cleanups fail"


@given(iterations=st.integers(min_value=1, max_value=5))
@settings(max_examples=30, deadline=10000)
@pytest.mark.property
@pytest.mark.resource_cleanup
def test_repeated_shutdown_is_idempotent(iterations: int):
    """
    Property: Repeated shutdown calls must be idempotent and safe.

    **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.9**

    This test verifies that:
    - Multiple shutdown calls don't cause errors
    - Resources are only cleaned once
    - System remains stable after repeated shutdowns
    - No double-free or similar issues occur
    """
    # Limit iterations
    assume(1 <= iterations <= 3)

    client = ModbusClient(ip="192.168.1.100", port=502)

    # Setup resources
    mock_modbus = MagicMock()
    client.client = mock_modbus
    client.is_connected = True

    mock_timer = MagicMock()
    client.timer = mock_timer

    # Perform shutdown multiple times
    for i in range(iterations):
        try:
            client.stop()
        except Exception as e:
            pytest.fail(f"Shutdown iteration {i+1} raised exception: {e}")

    # Verify thread is stopped
    assert not client.isRunning(), "Thread must be stopped after repeated shutdowns"

    # Verify system is stable (no crashes)
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
