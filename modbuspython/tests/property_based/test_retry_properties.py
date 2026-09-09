"""Property-based tests for retry strategy.

This module contains property-based tests using Hypothesis to verify
retry logic invariants and properties.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock
from modbuspython.data_access.retry_strategy import RetryStrategy

# Property 9: Retry Logic Execution
# **Validates: Requirements 4.3, 4.9, 4.10**


@given(max_attempts=st.integers(min_value=1, max_value=10), fail_count=st.integers(min_value=0, max_value=15))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.retry
def test_retry_logic_execution_count(max_attempts: int, fail_count: int):
    """
    Property: The retry strategy must execute exactly min(fail_count+1, max_attempts) attempts.

    **Validates: Requirements 4.3, 4.9, 4.10**

    This test verifies that:
    - If operation succeeds before max_attempts, exactly fail_count+1 attempts are made
    - If operation fails all attempts, exactly max_attempts attempts are made
    - The number of attempts never exceeds max_attempts
    - The number of attempts is always at least 1 (initial attempt)

    The property being tested is:
        actual_attempts = min(fail_count + 1, max_attempts)

    Where:
    - fail_count: number of times the operation fails before succeeding
    - max_attempts: maximum number of retry attempts configured
    - fail_count + 1: includes the initial attempt plus all failures
    """
    # Create retry strategy with specified max_attempts
    retry = RetryStrategy(max_attempts=max_attempts, initial_delay=0.01, backoff_factor=1.5)  # Small delay for fast tests

    # Track actual number of calls
    call_count = 0

    def mock_operation():
        """Mock operation that fails fail_count times, then succeeds."""
        nonlocal call_count
        call_count += 1

        # Fail for the first fail_count attempts
        if call_count <= fail_count:
            raise Exception(f"Simulated failure {call_count}")

        # Succeed after fail_count failures
        return "success"

    # Set function name for logging
    mock_operation.__name__ = "mock_operation"

    # Execute with retry
    result, success = retry.execute_with_retry(mock_operation)

    # Calculate expected number of attempts
    expected_attempts = min(fail_count + 1, max_attempts)

    # Verify actual attempts match expected
    assert call_count == expected_attempts, (
        f"Retry logic execution count failed. "
        f"max_attempts={max_attempts}, fail_count={fail_count}, "
        f"expected_attempts={expected_attempts}, actual_attempts={call_count}"
    )

    # Verify success/failure status
    if fail_count < max_attempts:
        # Operation should succeed (we have enough attempts)
        assert success is True, f"Operation should succeed when fail_count ({fail_count}) < max_attempts ({max_attempts})"
        assert result == "success", f"Result should be 'success' when operation succeeds"
    else:
        # Operation should fail (not enough attempts)
        assert success is False, f"Operation should fail when fail_count ({fail_count}) >= max_attempts ({max_attempts})"
        assert result is None, f"Result should be None when all attempts are exhausted"


@given(max_attempts=st.integers(min_value=1, max_value=10), success_on_attempt=st.integers(min_value=1, max_value=10))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.retry
def test_retry_stops_on_success(max_attempts: int, success_on_attempt: int):
    """
    Property: Retry strategy must stop immediately upon success, not continue to max_attempts.

    **Validates: Requirements 4.3, 4.9**

    This test verifies that:
    - Retry stops as soon as operation succeeds
    - No additional attempts are made after success
    - Success is correctly detected and reported
    """
    # Only test cases where success happens within max_attempts
    assume(success_on_attempt <= max_attempts)

    retry = RetryStrategy(max_attempts=max_attempts, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def mock_operation():
        """Mock operation that succeeds on specific attempt."""
        nonlocal call_count
        call_count += 1

        if call_count < success_on_attempt:
            raise Exception(f"Failure {call_count}")

        return f"success_on_attempt_{success_on_attempt}"

    mock_operation.__name__ = "mock_operation"

    result, success = retry.execute_with_retry(mock_operation)

    # Verify it stopped exactly when it succeeded
    assert call_count == success_on_attempt, (
        f"Retry should stop on success. " f"success_on_attempt={success_on_attempt}, actual_calls={call_count}"
    )

    assert success is True, f"Success flag should be True when operation succeeds"

    assert result == f"success_on_attempt_{success_on_attempt}", f"Result should be returned when operation succeeds"


@given(max_attempts=st.integers(min_value=1, max_value=10))
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.retry
def test_retry_exhausts_all_attempts_on_continuous_failure(max_attempts: int):
    """
    Property: When operation always fails, retry must execute exactly max_attempts times.

    **Validates: Requirements 4.3, 4.9, 4.10**

    This test verifies that:
    - All configured attempts are used when operation continuously fails
    - Retry doesn't give up early
    - Failure is correctly reported after all attempts exhausted
    """
    retry = RetryStrategy(max_attempts=max_attempts, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def always_fails():
        """Mock operation that always fails."""
        nonlocal call_count
        call_count += 1
        raise Exception(f"Always fails (attempt {call_count})")

    always_fails.__name__ = "always_fails"

    result, success = retry.execute_with_retry(always_fails)

    # Verify all attempts were used
    assert call_count == max_attempts, (
        f"All attempts should be used when operation always fails. " f"max_attempts={max_attempts}, actual_calls={call_count}"
    )

    assert success is False, f"Success flag should be False when all attempts fail"

    assert result is None, f"Result should be None when all attempts are exhausted"


@given(max_attempts=st.integers(min_value=2, max_value=10), fail_count=st.integers(min_value=1, max_value=9))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.retry
def test_retry_never_exceeds_max_attempts(max_attempts: int, fail_count: int):
    """
    Property: Retry strategy must never execute more than max_attempts times.

    **Validates: Requirements 4.3, 4.9**

    This is a safety property ensuring the retry mechanism respects
    the configured maximum attempts limit.
    """
    retry = RetryStrategy(max_attempts=max_attempts, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def mock_operation():
        """Mock operation with configurable failure count."""
        nonlocal call_count
        call_count += 1

        if call_count <= fail_count:
            raise Exception(f"Failure {call_count}")

        return "success"

    mock_operation.__name__ = "mock_operation"

    retry.execute_with_retry(mock_operation)

    # Verify we never exceed max_attempts
    assert call_count <= max_attempts, (
        f"Retry must never exceed max_attempts. " f"max_attempts={max_attempts}, actual_calls={call_count}"
    )


@given(max_attempts=st.integers(min_value=1, max_value=10))
@settings(max_examples=100, deadline=None)
@pytest.mark.property
@pytest.mark.retry
def test_retry_always_attempts_at_least_once(max_attempts: int):
    """
    Property: Retry strategy must always attempt the operation at least once.

    **Validates: Requirements 4.3, 4.9**

    This test verifies that:
    - Even with max_attempts=1, the operation is attempted
    - The initial attempt always happens regardless of configuration
    """
    retry = RetryStrategy(max_attempts=max_attempts, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def mock_operation():
        """Mock operation that tracks calls."""
        nonlocal call_count
        call_count += 1
        return "success"

    mock_operation.__name__ = "mock_operation"

    result, success = retry.execute_with_retry(mock_operation)

    # Verify at least one attempt was made
    assert call_count >= 1, f"Retry must always attempt at least once. actual_calls={call_count}"

    assert success is True, f"Operation should succeed on first attempt"

    assert result == "success", f"Result should be returned"


@given(max_attempts=st.integers(min_value=1, max_value=5), fail_count=st.integers(min_value=0, max_value=10))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.retry
def test_retry_result_consistency(max_attempts: int, fail_count: int):
    """
    Property: Retry result (success/failure) must be consistent with actual execution.

    **Validates: Requirements 4.3, 4.9, 4.10**

    This test verifies that:
    - success=True implies result is not None and operation succeeded
    - success=False implies result is None and all attempts failed
    - The success flag accurately reflects the operation outcome
    """
    retry = RetryStrategy(max_attempts=max_attempts, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def mock_operation():
        """Mock operation with configurable failure count."""
        nonlocal call_count
        call_count += 1

        if call_count <= fail_count:
            raise Exception(f"Failure {call_count}")

        return f"success_after_{fail_count}_failures"

    mock_operation.__name__ = "mock_operation"

    result, success = retry.execute_with_retry(mock_operation)

    # Verify consistency between success flag and result
    if success:
        # If success=True, result must not be None
        assert result is not None, f"When success=True, result must not be None. Got result={result}"

        # Result should be the expected success value
        assert result == f"success_after_{fail_count}_failures", f"Result should match expected success value"

        # Success should only happen if we had enough attempts
        assert fail_count < max_attempts, (
            f"Success should only occur when fail_count < max_attempts. "
            f"fail_count={fail_count}, max_attempts={max_attempts}"
        )
    else:
        # If success=False, result must be None
        assert result is None, f"When success=False, result must be None. Got result={result}"

        # Failure should only happen if we didn't have enough attempts
        assert fail_count >= max_attempts, (
            f"Failure should only occur when fail_count >= max_attempts. "
            f"fail_count={fail_count}, max_attempts={max_attempts}"
        )


@given(
    max_attempts=st.integers(min_value=1, max_value=10),
    fail_count=st.integers(min_value=0, max_value=15),
    return_value=st.one_of(
        st.integers(),
        st.text(min_size=1, max_size=50),
        st.booleans(),
        st.lists(st.integers(), max_size=10),
        st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
    ),
)
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.retry
def test_retry_preserves_return_value(max_attempts: int, fail_count: int, return_value):
    """
    Property: Retry strategy must preserve and return the exact value from successful operation.

    **Validates: Requirements 4.3, 4.9**

    This test verifies that:
    - The return value from the operation is not modified
    - Different types of return values are handled correctly
    - The returned value is exactly what the operation returned
    """
    # Only test cases where operation succeeds
    assume(fail_count < max_attempts)

    retry = RetryStrategy(max_attempts=max_attempts, initial_delay=0.01, backoff_factor=1.5)

    call_count = 0

    def mock_operation():
        """Mock operation that returns specific value after failures."""
        nonlocal call_count
        call_count += 1

        if call_count <= fail_count:
            raise Exception(f"Failure {call_count}")

        return return_value

    mock_operation.__name__ = "mock_operation"

    result, success = retry.execute_with_retry(mock_operation)

    # Verify the return value is preserved exactly
    assert result == return_value, f"Retry must preserve exact return value. " f"expected={return_value}, got={result}"

    assert success is True, f"Operation should succeed"


@given(max_attempts=st.integers(min_value=1, max_value=10), fail_count=st.integers(min_value=0, max_value=15))
@settings(max_examples=200, deadline=None)
@pytest.mark.property
@pytest.mark.retry
def test_retry_idempotence(max_attempts: int, fail_count: int):
    """
    Property: Running the same retry configuration twice should produce identical results.

    **Validates: Requirements 4.3, 4.9**

    This test verifies that:
    - Retry behavior is deterministic for the same inputs
    - Multiple executions with same configuration produce same outcomes
    - No hidden state affects retry behavior
    """
    retry = RetryStrategy(max_attempts=max_attempts, initial_delay=0.01, backoff_factor=1.5)

    # First execution
    call_count_1 = 0

    def mock_operation_1():
        nonlocal call_count_1
        call_count_1 += 1
        if call_count_1 <= fail_count:
            raise Exception(f"Failure {call_count_1}")
        return "success"

    mock_operation_1.__name__ = "mock_operation"

    result_1, success_1 = retry.execute_with_retry(mock_operation_1)

    # Second execution with same configuration
    call_count_2 = 0

    def mock_operation_2():
        nonlocal call_count_2
        call_count_2 += 1
        if call_count_2 <= fail_count:
            raise Exception(f"Failure {call_count_2}")
        return "success"

    mock_operation_2.__name__ = "mock_operation"

    result_2, success_2 = retry.execute_with_retry(mock_operation_2)

    # Verify both executions produced identical results
    assert call_count_1 == call_count_2, (
        f"Retry should be deterministic. "
        f"First execution: {call_count_1} attempts, Second execution: {call_count_2} attempts"
    )

    assert success_1 == success_2, f"Success flag should be identical across executions"

    assert result_1 == result_2, f"Results should be identical across executions"
