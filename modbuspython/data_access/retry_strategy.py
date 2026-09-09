"""Retry strategy with exponential backoff for network operations.

This module provides a flexible retry mechanism for operations that may fail
transiently, such as network requests. It implements exponential backoff to
avoid overwhelming the target system.
"""

import time
import functools
from typing import Callable, TypeVar, Optional, Tuple
from modbuspython.data_access.logging_service import LoggingService

T = TypeVar("T")


class RetryStrategy:
    """Implements retry logic with exponential backoff.

    This class provides a configurable retry mechanism that can be used
    to wrap operations that may fail transiently. It implements exponential
    backoff to progressively increase the delay between retry attempts.

    Attributes:
        max_attempts: Maximum number of retry attempts (including initial attempt)
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for delay after each failed attempt
        max_delay: Maximum delay in seconds between retries

    Example:
        >>> retry = RetryStrategy(max_attempts=3, initial_delay=1.0, backoff_factor=2.0)
        >>> result = retry.execute_with_retry(some_network_operation, arg1, arg2)
    """

    def __init__(
        self, max_attempts: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0, max_delay: float = 30.0
    ):
        """Initialize retry strategy with configuration.

        Args:
            max_attempts: Maximum number of attempts (default: 3)
            initial_delay: Initial delay in seconds (default: 1.0)
            backoff_factor: Exponential backoff multiplier (default: 2.0)
            max_delay: Maximum delay between retries in seconds (default: 30.0)

        Raises:
            ValueError: If max_attempts < 1 or delays are negative
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")
        if backoff_factor < 1:
            raise ValueError("backoff_factor must be at least 1")
        if max_delay < initial_delay:
            raise ValueError("max_delay must be >= initial_delay")

        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self._logger = LoggingService()

    def execute_with_retry(self, func: Callable[..., T], *args, **kwargs) -> Tuple[Optional[T], bool]:
        """Execute a function with retry logic and exponential backoff.

        Attempts to execute the provided function up to max_attempts times.
        If the function raises an exception, waits with exponential backoff
        before retrying. Logs each failed attempt.

        Args:
            func: The function to execute
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Tuple of (result, success):
                - result: The return value of func if successful, None otherwise
                - success: True if operation succeeded, False if all retries exhausted

        Example:
            >>> retry = RetryStrategy(max_attempts=3)
            >>> result, success = retry.execute_with_retry(connect_to_device, host="192.168.1.100")
            >>> if success:
            ...     print(f"Connected: {result}")
            ... else:
            ...     print("Failed after all retries")
        """
        last_exception: Optional[Exception] = None
        delay = self.initial_delay

        for attempt in range(1, self.max_attempts + 1):
            try:
                self._logger.debug(f"Executing {func.__name__} (attempt {attempt}/{self.max_attempts})")
                result = func(*args, **kwargs)

                if attempt > 1:
                    self._logger.info(f"Operation {func.__name__} succeeded on attempt {attempt}/{self.max_attempts}")

                return result, True

            except Exception as e:
                last_exception = e

                self._logger.warning(f"Attempt {attempt}/{self.max_attempts} failed for {func.__name__}: {str(e)}")

                # If this was the last attempt, don't wait
                if attempt < self.max_attempts:
                    self._logger.debug(f"Waiting {delay:.2f}s before retry {attempt + 1}/{self.max_attempts}")
                    time.sleep(delay)

                    # Calculate next delay with exponential backoff
                    delay = min(delay * self.backoff_factor, self.max_delay)

        # All attempts exhausted
        self._logger.error(
            f"All {self.max_attempts} attempts failed for {func.__name__}. " f"Last error: {str(last_exception)}"
        )

        return None, False

    def calculate_delay(self, attempt: int) -> float:
        """Calculate the delay for a given attempt number.

        Uses exponential backoff formula: delay = min(initial_delay * (backoff_factor ^ (attempt - 1)), max_delay)

        Args:
            attempt: The attempt number (1-indexed)

        Returns:
            Delay in seconds for the given attempt

        Example:
            >>> retry = RetryStrategy(initial_delay=1.0, backoff_factor=2.0, max_delay=30.0)
            >>> retry.calculate_delay(1)  # First retry
            1.0
            >>> retry.calculate_delay(2)  # Second retry
            2.0
            >>> retry.calculate_delay(3)  # Third retry
            4.0
        """
        if attempt < 1:
            return 0.0

        delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


def retry_decorator(
    max_attempts: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0, max_delay: float = 30.0
) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """Decorator to add retry logic with exponential backoff to a function.

    This decorator wraps a function with retry logic, automatically retrying
    on exceptions with exponential backoff. The decorated function will return
    None if all retry attempts are exhausted.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Exponential backoff multiplier (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 30.0)

    Returns:
        Decorator function that wraps the target function with retry logic

    Example:
        >>> @retry_decorator(max_attempts=3, initial_delay=1.0)
        ... def connect_to_device(host: str, port: int) -> bool:
        ...     # Connection logic that may fail
        ...     return True
        >>>
        >>> result = connect_to_device("192.168.1.100", 502)
        >>> if result is not None:
        ...     print("Connected successfully")
    """

    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            retry_strategy = RetryStrategy(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                backoff_factor=backoff_factor,
                max_delay=max_delay,
            )
            result, success = retry_strategy.execute_with_retry(func, *args, **kwargs)
            return result

        return wrapper

    return decorator
