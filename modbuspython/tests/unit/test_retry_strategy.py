"""
Unit tests for RetryStrategy.

Tests the retry mechanism with exponential backoff including:
- Successful operations on first attempt
- Successful operations after N failures
- Operations that fail all attempts
- Exponential backoff timing
- Logging of retry attempts
"""

import pytest
import time
from unittest.mock import Mock, patch, call
from modbuspython.data_access.retry_strategy import RetryStrategy, retry_decorator


class TestRetryStrategy:
    """Unit tests for RetryStrategy class."""

    def test_successful_operation_first_attempt(self):
        """Test that successful operation on first attempt returns immediately."""
        retry = RetryStrategy(max_attempts=3, initial_delay=1.0)

        # Mock function that succeeds immediately
        mock_func = Mock(return_value="success")
        mock_func.__name__ = "mock_func"

        result, success = retry.execute_with_retry(mock_func, "arg1", kwarg1="value1")

        assert success is True
        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    def test_successful_operation_after_n_failures(self):
        """Test that operation succeeds after N failures."""
        retry = RetryStrategy(max_attempts=4, initial_delay=0.1, backoff_factor=2.0)

        # Mock function that fails twice then succeeds
        mock_func = Mock(side_effect=[Exception("Failure 1"), Exception("Failure 2"), "success"])
        mock_func.__name__ = "mock_func"

        start_time = time.time()
        result, success = retry.execute_with_retry(mock_func)
        elapsed_time = time.time() - start_time

        assert success is True
        assert result == "success"
        assert mock_func.call_count == 3

        # Verify delays occurred (0.1s + 0.2s = 0.3s minimum)
        assert elapsed_time >= 0.3, f"Expected at least 0.3s delay, got {elapsed_time:.3f}s"

    def test_operation_fails_all_attempts(self):
        """Test that operation failing all attempts returns None and False."""
        retry = RetryStrategy(max_attempts=3, initial_delay=0.05)

        # Mock function that always fails
        mock_func = Mock(side_effect=Exception("Always fails"))
        mock_func.__name__ = "mock_func"

        result, success = retry.execute_with_retry(mock_func)

        assert success is False
        assert result is None
        assert mock_func.call_count == 3

    def test_exponential_backoff_timing(self):
        """Test that exponential backoff delays are applied correctly."""
        initial_delay = 0.1
        backoff_factor = 2.0
        retry = RetryStrategy(max_attempts=4, initial_delay=initial_delay, backoff_factor=backoff_factor)

        # Mock function that always fails
        mock_func = Mock(side_effect=Exception("Fail"))
        mock_func.__name__ = "mock_func"

        start_time = time.time()
        retry.execute_with_retry(mock_func)
        elapsed_time = time.time() - start_time

        # Expected delays: 0.1s, 0.2s, 0.4s = 0.7s total
        expected_min_delay = initial_delay + (initial_delay * backoff_factor) + (initial_delay * backoff_factor**2)

        assert elapsed_time >= expected_min_delay, f"Expected at least {expected_min_delay:.3f}s, got {elapsed_time:.3f}s"

        # Allow some tolerance for execution time (should be less than 2x expected)
        assert (
            elapsed_time < expected_min_delay * 2
        ), f"Delay too long: {elapsed_time:.3f}s (expected ~{expected_min_delay:.3f}s)"

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        retry = RetryStrategy(max_attempts=5, initial_delay=1.0, backoff_factor=10.0, max_delay=2.0)

        # Calculate delays for each attempt
        delay_1 = retry.calculate_delay(1)  # 1.0
        delay_2 = retry.calculate_delay(2)  # 10.0 -> capped to 2.0
        delay_3 = retry.calculate_delay(3)  # 100.0 -> capped to 2.0

        assert delay_1 == 1.0
        assert delay_2 == 2.0, f"Expected 2.0 (capped), got {delay_2}"
        assert delay_3 == 2.0, f"Expected 2.0 (capped), got {delay_3}"

    def test_calculate_delay_method(self):
        """Test the calculate_delay method with various attempt numbers."""
        retry = RetryStrategy(initial_delay=1.0, backoff_factor=2.0, max_delay=30.0)

        assert retry.calculate_delay(0) == 0.0
        assert retry.calculate_delay(1) == 1.0
        assert retry.calculate_delay(2) == 2.0
        assert retry.calculate_delay(3) == 4.0
        assert retry.calculate_delay(4) == 8.0
        assert retry.calculate_delay(5) == 16.0

    @patch("modbuspython.data_access.retry_strategy.LoggingService")
    def test_logging_of_attempts(self, mock_logging_service):
        """Test that retry attempts are logged appropriately."""
        mock_logger = Mock()
        mock_logging_service.return_value = mock_logger

        retry = RetryStrategy(max_attempts=3, initial_delay=0.05)

        # Mock function that fails twice then succeeds
        mock_func = Mock(side_effect=[Exception("Failure 1"), Exception("Failure 2"), "success"])
        mock_func.__name__ = "test_function"

        retry.execute_with_retry(mock_func)

        # Verify debug logs for each attempt
        assert mock_logger.debug.call_count >= 3

        # Verify warning logs for failures
        assert mock_logger.warning.call_count == 2

        # Verify info log for eventual success
        assert mock_logger.info.call_count == 1

    @patch("modbuspython.data_access.retry_strategy.LoggingService")
    def test_logging_all_attempts_failed(self, mock_logging_service):
        """Test that error is logged when all attempts fail."""
        mock_logger = Mock()
        mock_logging_service.return_value = mock_logger

        retry = RetryStrategy(max_attempts=3, initial_delay=0.05)

        # Mock function that always fails
        mock_func = Mock(side_effect=Exception("Always fails"))
        mock_func.__name__ = "failing_function"

        retry.execute_with_retry(mock_func)

        # Verify error log when all attempts exhausted
        assert mock_logger.error.call_count == 1

        # Verify the error message contains relevant information
        error_call = mock_logger.error.call_args
        assert "All 3 attempts failed" in error_call[0][0]
        assert "failing_function" in error_call[0][0]

    def test_retry_with_positional_and_keyword_args(self):
        """Test that retry correctly passes positional and keyword arguments."""
        retry = RetryStrategy(max_attempts=2, initial_delay=0.05)

        mock_func = Mock(return_value="result")
        mock_func.__name__ = "mock_func"

        retry.execute_with_retry(mock_func, "arg1", "arg2", key1="value1", key2="value2")

        mock_func.assert_called_once_with("arg1", "arg2", key1="value1", key2="value2")

    def test_initialization_validation(self):
        """Test that RetryStrategy validates initialization parameters."""
        # Test max_attempts < 1
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryStrategy(max_attempts=0)

        # Test negative initial_delay
        with pytest.raises(ValueError, match="initial_delay must be non-negative"):
            RetryStrategy(initial_delay=-1.0)

        # Test backoff_factor < 1
        with pytest.raises(ValueError, match="backoff_factor must be at least 1"):
            RetryStrategy(backoff_factor=0.5)

        # Test max_delay < initial_delay
        with pytest.raises(ValueError, match="max_delay must be >= initial_delay"):
            RetryStrategy(initial_delay=10.0, max_delay=5.0)

    def test_single_attempt_configuration(self):
        """Test retry with max_attempts=1 (no retries)."""
        retry = RetryStrategy(max_attempts=1)

        mock_func = Mock(side_effect=Exception("Fail"))
        mock_func.__name__ = "mock_func"

        result, success = retry.execute_with_retry(mock_func)

        assert success is False
        assert result is None
        assert mock_func.call_count == 1

    def test_no_delay_on_last_attempt(self):
        """Test that no delay occurs after the last failed attempt."""
        retry = RetryStrategy(max_attempts=2, initial_delay=1.0)

        mock_func = Mock(side_effect=Exception("Fail"))
        mock_func.__name__ = "mock_func"

        start_time = time.time()
        retry.execute_with_retry(mock_func)
        elapsed_time = time.time() - start_time

        # Should have delay after first attempt (1.0s) but not after second
        # Total time should be around 1.0s, not 2.0s
        assert elapsed_time >= 1.0
        assert elapsed_time < 1.5, f"Should not delay after last attempt, got {elapsed_time:.3f}s"


class TestRetryDecorator:
    """Unit tests for retry_decorator."""

    def test_decorator_successful_operation(self):
        """Test that decorator works for successful operations."""

        @retry_decorator(max_attempts=3, initial_delay=0.05)
        def successful_func(value):
            return value * 2

        result = successful_func(5)

        assert result == 10

    def test_decorator_operation_fails_all_attempts(self):
        """Test that decorator returns None when all attempts fail."""
        call_count = 0

        @retry_decorator(max_attempts=3, initial_delay=0.05)
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")

        result = failing_func()

        assert result is None
        assert call_count == 3

    def test_decorator_succeeds_after_failures(self):
        """Test that decorator succeeds after initial failures."""
        call_count = 0

        @retry_decorator(max_attempts=4, initial_delay=0.05)
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Failure {call_count}")
            return "success"

        result = eventually_succeeds()

        assert result == "success"
        assert call_count == 3

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata."""

        @retry_decorator(max_attempts=2)
        def documented_func():
            """This is a documented function."""
            return "result"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a documented function."

    def test_decorator_with_custom_parameters(self):
        """Test decorator with custom retry parameters."""
        call_count = 0

        @retry_decorator(max_attempts=5, initial_delay=0.05, backoff_factor=3.0, max_delay=10.0)
        def custom_retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Fail once")
            return "success"

        result = custom_retry_func()

        assert result == "success"
        assert call_count == 2

    def test_decorator_with_args_and_kwargs(self):
        """Test that decorator correctly passes arguments."""

        @retry_decorator(max_attempts=2, initial_delay=0.05)
        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = func_with_args("x", "y", c="z")

        assert result == "x-y-z"


class TestRetryStrategyIntegration:
    """Integration tests for RetryStrategy with realistic scenarios."""

    def test_network_operation_simulation(self):
        """Simulate a network operation that fails then succeeds."""
        retry = RetryStrategy(max_attempts=5, initial_delay=0.1, backoff_factor=2.0)

        attempts = []

        def simulated_network_call(host, port):
            attempts.append(time.time())
            if len(attempts) < 3:
                raise ConnectionError(f"Connection refused to {host}:{port}")
            return {"status": "connected", "host": host, "port": port}

        result, success = retry.execute_with_retry(simulated_network_call, host="192.168.1.100", port=502)

        assert success is True
        assert result["status"] == "connected"
        assert len(attempts) == 3

        # Verify exponential backoff occurred
        if len(attempts) >= 2:
            delay_1 = attempts[1] - attempts[0]
            assert delay_1 >= 0.1, f"First delay should be >= 0.1s, got {delay_1:.3f}s"

        if len(attempts) >= 3:
            delay_2 = attempts[2] - attempts[1]
            assert delay_2 >= 0.2, f"Second delay should be >= 0.2s, got {delay_2:.3f}s"

    def test_database_operation_simulation(self):
        """Simulate a database operation with transient failures."""
        retry = RetryStrategy(max_attempts=3, initial_delay=0.05)

        call_count = 0

        def simulated_db_query(query):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise Exception("Database locked")
            elif call_count == 2:
                raise Exception("Timeout")
            else:
                return [{"id": 1, "data": "result"}]

        result, success = retry.execute_with_retry(simulated_db_query, query="SELECT * FROM table")

        assert success is True
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_permanent_failure_scenario(self):
        """Test scenario where operation has permanent failure."""
        retry = RetryStrategy(max_attempts=3, initial_delay=0.05)

        def permanent_failure():
            raise PermissionError("Access denied - permanent error")

        result, success = retry.execute_with_retry(permanent_failure)

        assert success is False
        assert result is None
