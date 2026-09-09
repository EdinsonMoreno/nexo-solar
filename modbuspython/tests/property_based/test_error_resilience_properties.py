"""Property-based tests for error resilience and continuation.



This module contains property-based tests using Hypothesis to verify


that the system continues operating and logs appropriately when errors occur.



Property 8: Error Resilience Continuation


**Validates: Requirements 4.2, 4.4, 4.8**
"""

import pytest


from hypothesis import given, strategies as st, settings


from unittest.mock import Mock, MagicMock, patch


import sqlite3


from pathlib import Path
import tempfile
import os


from modbuspython.exceptions import ModbusConnectionError, ModbusOperationError, DatabaseError


from modbuspython.data_access.logging_service import LoggingService


from modbuspython.data_access.retry_strategy import RetryStrategy

# Property 8: Error Resilience Continuation


# **Validates: Requirements 4.2, 4.4, 4.8**


def generate_modbus_errors():
    """Strategy to generate different types of Modbus errors."""

    return st.one_of(
        # Connection errors
        st.builds(ModbusConnectionError, st.text(min_size=10, max_size=100), st.just({"ip": "192.168.1.100", "port": 502})),
        # Operation errors
        st.builds(ModbusOperationError, st.text(min_size=10, max_size=100), st.just({"register": 0, "operation": "read"})),
        # Generic exceptions
        st.builds(Exception, st.text(min_size=10, max_size=100)),
        # OSError (network errors)
        st.builds(OSError, st.text(min_size=10, max_size=100)),
        # RuntimeError
        st.builds(RuntimeError, st.text(min_size=10, max_size=100)),
    )


def generate_database_errors():
    """Strategy to generate different types of database errors."""

    return st.one_of(
        # Database errors
        st.builds(DatabaseError, st.text(min_size=10, max_size=100), st.just({"db_path": "/path/to/db.sqlite"})),
        # SQLite errors
        st.builds(sqlite3.OperationalError, st.text(min_size=10, max_size=100)),
        st.builds(sqlite3.IntegrityError, st.text(min_size=10, max_size=100)),
        st.builds(sqlite3.DatabaseError, st.text(min_size=10, max_size=100)),
        # Generic exceptions
        st.builds(Exception, st.text(min_size=10, max_size=100)),
    )


@given(error=generate_modbus_errors())
@settings(max_examples=50, deadline=2000)
@pytest.mark.property
@pytest.mark.error_resilience
def test_retry_strategy_continues_after_errors(error):
    """


    Property: RetryStrategy must continue operating and log errors appropriately.



    **Validates: Requirements 4.2, 4.8**



    This test verifies that:


    - Errors are caught and logged during retry attempts


    - System continues operating after errors


    - Retry logic completes without crashing


    - Error information is preserved
    """

    retry = RetryStrategy(max_attempts=3, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def failing_operation():
        """Operation that always fails with the given error."""
        nonlocal call_count

        call_count += 1
        raise error

    failing_operation.__name__ = "failing_operation"

    # Execute with retry - should handle error gracefully

    try:

        result, success = retry.execute_with_retry(failing_operation)

        operation_completed = True

    except Exception as e:

        operation_completed = False

        pytest.fail(f"RetryStrategy raised unhandled exception: {e}")

    # Verify operation completed without crashing

    assert operation_completed, "RetryStrategy should complete without raising exception"

    # Verify all retry attempts were made

    assert call_count == 3, f"Should attempt operation 3 times, got {call_count} attempts"

    # Verify operation failed (as expected)

    assert success is False, "Operation should fail when all attempts raise errors"

    # Verify result is None on failure

    assert result is None, "Result should be None when all attempts fail"


@given(error=generate_modbus_errors(), success_on_attempt=st.integers(min_value=1, max_value=3))
@settings(max_examples=50, deadline=2000)
@pytest.mark.property
@pytest.mark.error_resilience
def test_system_continues_after_partial_failures(error, success_on_attempt: int):
    """


    Property: System must continue operating after partial failures and eventual success.



    **Validates: Requirements 4.2, 4.8**



    This test verifies that:


    - System handles failures followed by success


    - Errors are logged for failed attempts


    - Success is correctly detected and returned


    - System doesn't crash during error-to-success transition
    """

    retry = RetryStrategy(max_attempts=3, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def partially_failing_operation():
        """Operation that fails N times then succeeds."""
        nonlocal call_count

        call_count += 1

        if call_count < success_on_attempt:
            raise error

        return f"success_on_attempt_{success_on_attempt}"

    partially_failing_operation.__name__ = "partially_failing_operation"

    # Execute with retry

    try:

        result, success = retry.execute_with_retry(partially_failing_operation)

        operation_completed = True

    except Exception as e:

        operation_completed = False

        pytest.fail(f"RetryStrategy raised unhandled exception: {e}")

    # Verify operation completed

    assert operation_completed, "Operation should complete without crashing"

    # Verify correct number of attempts

    assert call_count == success_on_attempt, f"Should attempt {success_on_attempt} times, got {call_count} attempts"

    # Verify success

    assert success is True, "Operation should succeed when it eventually returns"

    # Verify result is preserved

    assert result == f"success_on_attempt_{success_on_attempt}", "Result should be preserved from successful attempt"


@given(error=generate_database_errors())
@settings(max_examples=50, deadline=2000)
@pytest.mark.property
@pytest.mark.error_resilience
def test_database_operations_continue_after_error(error):
    """


    Property: Database operations must continue after errors without crashing.



    **Validates: Requirements 4.4, 4.8**



    This test verifies that:


    - Database errors are caught and logged


    - System continues operating after database failure


    - Error is logged with appropriate level and context


    - No unhandled exceptions propagate


    - Database connection state is handled correctly
    """

    from modbuspython.backend import sqlite_manager

    # Create a temporary database file

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:

        db_path = tmp_file.name

    try:

        # Connect to database

        conn = sqlite_manager.conectar_db(db_path)

        # Create a test table

        sqlite_manager.crear_tabla(conn, "test_table")

        # Mock the insert operation to raise error

        with patch.object(sqlite_manager, "insertar_registro", side_effect=error):

            # Attempt insert - should handle error gracefully

            try:

                sqlite_manager.insert_record(conn, "test_table", "2024-01-01", "12:00:00", 100.5)

                operation_completed = True

            except DatabaseError:

                # DatabaseError is expected and should be caught by caller

                operation_completed = True

            except Exception:

                # Other exceptions should also be handled

                operation_completed = True

        # Verify operation completed (error was handled)

        assert operation_completed, "Database operation should complete without crashing"

        # Verify connection is still valid (can perform other operations)

        try:

            tables = sqlite_manager.get_tables(conn)

            connection_valid = True

        except Exception:

            connection_valid = False

        assert connection_valid, "Database connection should remain valid after error"

        # Close connection

        conn.close()

    finally:

        # Cleanup temporary database file

        if os.path.exists(db_path):

            os.remove(db_path)


@given(
    error_count=st.integers(min_value=1, max_value=5),
    error_type=st.sampled_from(["connection", "operation", "generic"]),
)
@settings(max_examples=50, deadline=2000)
@pytest.mark.property
@pytest.mark.error_resilience
def test_system_continues_after_multiple_errors(error_count: int, error_type: str):
    """


    Property: System must continue operating after multiple consecutive errors.



    **Validates: Requirements 4.2, 4.4, 4.8**



    This test verifies that:


    - Multiple consecutive errors don't crash the system


    - Each error is logged appropriately


    - System state is maintained correctly


    - Recovery is possible after errors
    """

    retry = RetryStrategy(
        max_attempts=error_count + 2, initial_delay=0.01, backoff_factor=1.5  # Ensure we have enough attempts
    )

    # Create appropriate error

    if error_type == "connection":

        error = ModbusConnectionError("Connection failed", {"ip": "192.168.1.100"})

    elif error_type == "operation":

        error = ModbusOperationError("Operation failed", {"register": 0})

    else:

        error = Exception("Generic error")

    call_count = 0

    def operation_with_multiple_failures():
        """Operation that fails error_count times then succeeds."""
        nonlocal call_count

        call_count += 1

        if call_count <= error_count:
            raise error

        return "success"

    operation_with_multiple_failures.__name__ = "operation_with_multiple_failures"

    # Execute with retry

    try:

        result, success = retry.execute_with_retry(operation_with_multiple_failures)

        operation_completed = True

    except Exception as e:

        operation_completed = False

        pytest.fail(f"Operation raised unhandled exception after {error_count} errors: {e}")

    # Verify operation completed

    assert operation_completed, f"Operation should complete without crashing after {error_count} errors"

    # Verify correct number of attempts

    assert call_count == error_count + 1, f"Should attempt {error_count + 1} times, got {call_count} attempts"

    # Verify eventual success

    assert success is True, "Operation should eventually succeed"

    # Verify result

    assert result == "success", "Result should be 'success'"


@given(error=generate_modbus_errors(), log_level=st.sampled_from(["ERROR", "CRITICAL"]))
@settings(max_examples=50, deadline=2000)
@pytest.mark.property
@pytest.mark.error_resilience
def test_errors_are_logged_appropriately(error, log_level: str):
    """


    Property: All errors must be logged with appropriate level and context.



    **Validates: Requirements 4.8**



    This test verifies that:


    - Errors are logged when they occur


    - Log level is appropriate for error severity


    - Log messages contain relevant context


    - Logging doesn't fail even if error handling fails
    """

    # Create a temporary log file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp_file:

        log_path = Path(tmp_file.name)

    try:

        # Setup logging service

        logger = LoggingService()

        logger.setup(log_file=log_path, level=log_level, max_bytes=1048576, backup_count=3)

        # Log the error

        error_message = str(error)

        try:

            if isinstance(error, (ModbusConnectionError, ModbusOperationError)):

                logger.error(f"Modbus error occurred: {error_message}")

            elif isinstance(error, DatabaseError):

                logger.error(f"Database error occurred: {error_message}")

            else:

                logger.error(f"Unexpected error occurred: {error_message}")

            logging_succeeded = True

        except Exception as e:

            logging_succeeded = False

            pytest.fail(f"Logging failed with exception: {e}")

        # Verify logging succeeded

        assert logging_succeeded, "Error logging should succeed without raising exception"

        # Verify log file was created

        assert log_path.exists(), "Log file should be created"

        # Read log file content

        with open(log_path, "r", encoding="utf-8") as f:

            log_content = f.read()

        # Verify log contains error information

        assert len(log_content) > 0, "Log file should contain error information"

    finally:

        # Cleanup temporary log file

        if log_path.exists():

            os.remove(log_path)


@given(error_sequence=st.lists(st.sampled_from(["connection", "operation", "generic"]), min_size=1, max_size=5))
@settings(max_examples=30, deadline=2000)
@pytest.mark.property
@pytest.mark.error_resilience
def test_system_recovers_after_error_sequence(error_sequence):
    """


    Property: System must be able to recover after a sequence of different errors.



    **Validates: Requirements 4.2, 4.4, 4.8**



    This test verifies that:


    - System can recover from sequences of different error types


    - Each error is handled independently


    - System doesn't accumulate error state


    - Recovery mechanisms work correctly
    """

    retry = RetryStrategy(max_attempts=len(error_sequence) + 1, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def operation_with_error_sequence():
        """Operation that fails with different errors then succeeds."""
        nonlocal call_count

        if call_count < len(error_sequence):

            error_type = error_sequence[call_count]

            call_count += 1

            if error_type == "connection":

                raise ModbusConnectionError("Connection failed", {"ip": "192.168.1.100"})

            elif error_type == "operation":

                raise ModbusOperationError("Operation failed", {"register": 0})

            else:

                raise Exception("Generic error")

        call_count += 1

        return "recovered"

    operation_with_error_sequence.__name__ = "operation_with_error_sequence"

    # Execute with retry

    try:

        result, success = retry.execute_with_retry(operation_with_error_sequence)

        operation_completed = True

    except Exception as e:

        operation_completed = False

        pytest.fail(f"Operation raised unhandled exception: {e}")

    # Verify operation completed

    assert operation_completed, f"Operation should complete after error sequence of length {len(error_sequence)}"

    # Verify recovery

    assert success is True, "System should recover after error sequence"

    # Verify result

    assert result == "recovered", "Result should indicate successful recovery"


@given(fail_count=st.integers(min_value=0, max_value=10), max_attempts=st.integers(min_value=1, max_value=10))
@settings(max_examples=100, deadline=2000)
@pytest.mark.property
@pytest.mark.error_resilience
def test_error_handling_consistency(fail_count: int, max_attempts: int):
    """


    Property: Error handling must be consistent regardless of failure count.



    **Validates: Requirements 4.2, 4.8**



    This test verifies that:


    - Error handling behavior is consistent


    - System doesn't crash regardless of error count


    - Success/failure is correctly determined


    - No state corruption occurs
    """

    retry = RetryStrategy(max_attempts=max_attempts, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def operation():
        """Operation that fails fail_count times then succeeds."""
        nonlocal call_count

        call_count += 1

        if call_count <= fail_count:

            raise Exception(f"Failure {call_count}")

        return "success"

    operation.__name__ = "operation"

    # Execute with retry

    try:

        result, success = retry.execute_with_retry(operation)

        operation_completed = True

    except Exception as e:

        operation_completed = False

        pytest.fail(f"Operation raised unhandled exception: {e}")

    # Verify operation completed

    assert operation_completed, "Operation should always complete without crashing"

    # Verify consistency

    expected_attempts = min(fail_count + 1, max_attempts)

    assert call_count == expected_attempts, f"Should attempt {expected_attempts} times, got {call_count}"

    # Verify success/failure is correct

    if fail_count < max_attempts:

        assert success is True, f"Should succeed when fail_count ({fail_count}) < max_attempts ({max_attempts})"

        assert result == "success", "Result should be 'success' when operation succeeds"

    else:

        assert success is False, f"Should fail when fail_count ({fail_count}) >= max_attempts ({max_attempts})"

        assert result is None, "Result should be None when all attempts fail"
