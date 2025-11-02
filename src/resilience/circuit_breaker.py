"""Circuit breaker pattern implementation for resilience.

This module implements the circuit breaker pattern to prevent cascading failures
by temporarily stopping requests to failing services, giving them time to recover.

The circuit breaker has three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Too many failures, requests are rejected immediately
- HALF_OPEN: Testing if service has recovered, limited requests allowed

Example:
    >>> breaker = CircuitBreaker()
    >>> result = breaker.call(some_function, arg1, arg2)
    >>> state = breaker.get_state()
"""

import logging
import threading
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states.

    Attributes:
        CLOSED: Normal operation, requests pass through
        OPEN: Too many failures, requests are rejected immediately
        HALF_OPEN: Testing recovery, limited requests allowed
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and rejects a request."""

    pass


class CircuitBreaker:
    """Circuit breaker pattern implementation.

    Protects against cascading failures by tracking failures and temporarily
    stopping requests to failing services. The circuit opens after a threshold
    of consecutive failures, then attempts recovery after a timeout period.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        timeout: Time in seconds before attempting recovery
        half_open_max_calls: Maximum calls to allow in half-open state
        state: Current circuit state (CLOSED, OPEN, HALF_OPEN)
        failure_count: Current count of consecutive failures
        last_failure_time: Timestamp of most recent failure
        half_open_calls: Count of calls made in half-open state
    """

    def __init__(self):
        """Initialize circuit breaker with settings from configuration."""
        settings = get_settings()
        self.failure_threshold = settings.circuit_breaker.failure_threshold
        self.timeout = settings.circuit_breaker.timeout_seconds
        self.half_open_max_calls = settings.circuit_breaker.half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.half_open_calls = 0

        # Thread safety
        self._lock = threading.RLock()

        logger.info(
            f"Circuit breaker initialized: threshold={self.failure_threshold}, "
            f"timeout={self.timeout}s, half_open_max={self.half_open_max_calls}"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func execution

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception raised by func
        """
        with self._lock:
            # Check if circuit should attempt reset
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info("Circuit breaker entering HALF_OPEN state for recovery attempt")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    elapsed = (
                        (datetime.now() - self.last_failure_time).total_seconds()
                        if self.last_failure_time
                        else 0
                    )
                    remaining = max(0, self.timeout - elapsed)
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN. Service unavailable. "
                        f"Retry in {remaining:.1f} seconds."
                    )

            # Check if half-open state has exceeded max calls
            if (
                self.state == CircuitState.HALF_OPEN
                and self.half_open_calls >= self.half_open_max_calls
            ):
                raise CircuitBreakerError(
                    f"Circuit breaker HALF_OPEN max calls ({self.half_open_max_calls}) exceeded. "
                    "Please wait for recovery."
                )

        # Execute the function (release lock during execution)
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure(e)
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery.

        Returns:
            True if timeout period has elapsed since last failure
        """
        if self.last_failure_time is None:
            return True

        elapsed = datetime.now() - self.last_failure_time
        return elapsed.total_seconds() >= self.timeout

    def _on_success(self):
        """Handle successful call.

        In HALF_OPEN state, tracks successful calls and closes circuit after
        enough successes. In CLOSED state, resets failure count.
        """
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                logger.debug(
                    f"Circuit breaker HALF_OPEN: successful call "
                    f"{self.half_open_calls}/{self.half_open_max_calls}"
                )

                if self.half_open_calls >= self.half_open_max_calls:
                    logger.info(
                        "Circuit breaker closing after successful recovery "
                        f"({self.half_open_calls} successful calls)"
                    )
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.half_open_calls = 0
                    self.last_failure_time = None

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                if self.failure_count > 0:
                    logger.debug(
                        f"Circuit breaker: resetting failure count from {self.failure_count}"
                    )
                    self.failure_count = 0

    def _on_failure(self, exception: Exception):
        """Handle failed call.

        Increments failure count and opens circuit if threshold is reached.
        In HALF_OPEN state, immediately reopens circuit.

        Args:
            exception: The exception that caused the failure
        """
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"Circuit breaker reopening after failure in HALF_OPEN state: {exception}"
                )
                self.state = CircuitState.OPEN
                self.half_open_calls = 0

            elif self.state == CircuitState.CLOSED:
                logger.warning(
                    f"Circuit breaker failure {self.failure_count}/{self.failure_threshold}: {exception}"
                )

                if self.failure_count >= self.failure_threshold:
                    logger.error(
                        f"Circuit breaker OPENING after {self.failure_count} consecutive failures. "
                        f"Service will be unavailable for {self.timeout} seconds."
                    )
                    self.state = CircuitState.OPEN

    @property
    def is_open(self) -> bool:
        """Check if circuit is open.

        Returns:
            True if circuit is in OPEN state
        """
        with self._lock:
            return self.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed.

        Returns:
            True if circuit is in CLOSED state
        """
        with self._lock:
            return self.state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open.

        Returns:
            True if circuit is in HALF_OPEN state
        """
        with self._lock:
            return self.state == CircuitState.HALF_OPEN

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state information.

        Returns:
            Dictionary containing:
                - state: Current state (closed/open/half_open)
                - failure_count: Number of consecutive failures
                - last_failure: ISO timestamp of last failure (or None)
                - half_open_calls: Number of calls in half-open state
        """
        with self._lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "last_failure": (
                    self.last_failure_time.isoformat() if self.last_failure_time else None
                ),
                "half_open_calls": self.half_open_calls,
            }

    def reset(self):
        """Manually reset circuit breaker to CLOSED state.

        This should only be used for testing or administrative purposes.
        The circuit breaker is designed to recover automatically.
        """
        with self._lock:
            logger.info("Circuit breaker manually reset to CLOSED state")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self.half_open_calls = 0
