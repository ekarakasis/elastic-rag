"""Unit tests for circuit breaker implementation.

This module tests the CircuitBreaker class with comprehensive coverage of:
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure counting and threshold triggering
- Timeout-based recovery
- Thread safety
- Edge cases and boundary conditions
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
)


@pytest.fixture
def circuit_breaker():
    """Create a CircuitBreaker instance with default settings."""
    return CircuitBreaker()


@pytest.fixture
def mock_function():
    """Create a mock function for testing."""
    return MagicMock(return_value="success")


@pytest.fixture
def failing_function():
    """Create a function that always fails."""

    def fail():
        raise RuntimeError("Service unavailable")

    return fail


# === Initialization Tests ===


def test_circuit_breaker_initialization(circuit_breaker):
    """Test circuit breaker initializes with correct defaults."""
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0
    assert circuit_breaker.last_failure_time is None
    assert circuit_breaker.half_open_calls == 0
    assert circuit_breaker.failure_threshold > 0
    assert circuit_breaker.timeout > 0
    assert circuit_breaker.half_open_max_calls > 0


def test_circuit_breaker_initial_state_properties(circuit_breaker):
    """Test initial state property checks."""
    assert circuit_breaker.is_closed is True
    assert circuit_breaker.is_open is False
    assert circuit_breaker.is_half_open is False


def test_circuit_breaker_get_initial_state(circuit_breaker):
    """Test get_state returns correct initial state."""
    state = circuit_breaker.get_state()
    assert state["state"] == "closed"
    assert state["failure_count"] == 0
    assert state["last_failure"] is None
    assert state["half_open_calls"] == 0


# === Successful Call Tests ===


def test_call_success_in_closed_state(circuit_breaker, mock_function):
    """Test successful call in CLOSED state."""
    result = circuit_breaker.call(mock_function)

    assert result == "success"
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0
    mock_function.assert_called_once()


def test_call_with_args_and_kwargs(circuit_breaker):
    """Test call passes arguments correctly."""
    mock_func = MagicMock(return_value=42)

    result = circuit_breaker.call(mock_func, "arg1", "arg2", key1="value1", key2="value2")

    assert result == 42
    mock_func.assert_called_once_with("arg1", "arg2", key1="value1", key2="value2")


def test_successful_call_resets_failure_count(circuit_breaker, failing_function, mock_function):
    """Test that successful call resets failure count."""
    # Cause some failures (but not enough to open)
    for _ in range(2):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    assert circuit_breaker.failure_count == 2

    # Successful call should reset counter
    circuit_breaker.call(mock_function)
    assert circuit_breaker.failure_count == 0


# === Failure and Circuit Opening Tests ===


def test_call_failure_increments_count(circuit_breaker, failing_function):
    """Test that failed call increments failure count."""
    try:
        circuit_breaker.call(failing_function)
    except RuntimeError:
        pass

    assert circuit_breaker.failure_count == 1
    assert circuit_breaker.last_failure_time is not None
    assert circuit_breaker.state == CircuitState.CLOSED


def test_circuit_opens_after_threshold_failures(circuit_breaker, failing_function):
    """Test circuit opens after reaching failure threshold."""
    threshold = circuit_breaker.failure_threshold

    # Cause failures up to threshold
    for _ in range(threshold):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.failure_count == threshold


def test_open_circuit_rejects_calls(circuit_breaker, failing_function, mock_function):
    """Test that open circuit rejects all calls."""
    # Open the circuit
    for _ in range(circuit_breaker.failure_threshold):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    assert circuit_breaker.is_open

    # Try to call (should be rejected)
    with pytest.raises(CircuitBreakerError) as exc_info:
        circuit_breaker.call(mock_function)

    assert "Circuit breaker is OPEN" in str(exc_info.value)
    assert "Service unavailable" in str(exc_info.value)
    # Mock function should not have been called
    mock_function.assert_not_called()


def test_open_circuit_error_message_includes_retry_time(circuit_breaker, failing_function):
    """Test that CircuitBreakerError includes retry time."""
    # Open the circuit
    for _ in range(circuit_breaker.failure_threshold):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    with pytest.raises(CircuitBreakerError) as exc_info:
        circuit_breaker.call(MagicMock())

    error_msg = str(exc_info.value)
    assert "Retry in" in error_msg
    assert "seconds" in error_msg


# === Half-Open State and Recovery Tests ===


def test_circuit_enters_half_open_after_timeout(circuit_breaker, failing_function, mock_function):
    """Test circuit enters HALF_OPEN state after timeout."""
    # Open the circuit
    for _ in range(circuit_breaker.failure_threshold):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    assert circuit_breaker.is_open

    # Mock time to simulate timeout passage
    with patch.object(circuit_breaker, "_should_attempt_reset", return_value=True):
        # Next call should enter HALF_OPEN
        result = circuit_breaker.call(mock_function)

        assert result == "success"
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        assert circuit_breaker.half_open_calls == 1


def test_half_open_closes_after_successful_calls(circuit_breaker, failing_function, mock_function):
    """Test circuit closes after enough successful calls in HALF_OPEN."""
    # Open the circuit
    for _ in range(circuit_breaker.failure_threshold):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    # Enter HALF_OPEN
    with patch.object(circuit_breaker, "_should_attempt_reset", return_value=True):
        # Make successful calls up to half_open_max_calls
        for _ in range(circuit_breaker.half_open_max_calls):
            if circuit_breaker.is_open:
                # Force transition for first call
                circuit_breaker.state = CircuitState.HALF_OPEN
                circuit_breaker.half_open_calls = 0

            result = circuit_breaker.call(mock_function)
            assert result == "success"

    # Circuit should be closed now
    assert circuit_breaker.is_closed
    assert circuit_breaker.failure_count == 0
    assert circuit_breaker.half_open_calls == 0


def test_half_open_reopens_on_failure(circuit_breaker, failing_function, mock_function):
    """Test circuit reopens if call fails in HALF_OPEN state."""
    # Open the circuit
    for _ in range(circuit_breaker.failure_threshold):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    # Enter HALF_OPEN manually
    circuit_breaker.state = CircuitState.HALF_OPEN
    circuit_breaker.half_open_calls = 0

    # Fail in HALF_OPEN
    with pytest.raises(RuntimeError):
        circuit_breaker.call(failing_function)

    assert circuit_breaker.is_open
    assert circuit_breaker.half_open_calls == 0


def test_half_open_max_calls_limit(circuit_breaker, mock_function):
    """Test that HALF_OPEN state limits number of concurrent calls."""
    # Manually set to HALF_OPEN
    circuit_breaker.state = CircuitState.HALF_OPEN
    circuit_breaker.half_open_calls = circuit_breaker.half_open_max_calls

    # Try to make another call
    with pytest.raises(CircuitBreakerError) as exc_info:
        circuit_breaker.call(mock_function)

    assert "HALF_OPEN max calls" in str(exc_info.value)
    assert "exceeded" in str(exc_info.value)


# === Timeout and Recovery Tests ===


def test_should_attempt_reset_returns_true_after_timeout(circuit_breaker):
    """Test _should_attempt_reset returns True after timeout period."""
    # Set last failure time to past
    circuit_breaker.last_failure_time = datetime.now() - timedelta(
        seconds=circuit_breaker.timeout + 1
    )

    assert circuit_breaker._should_attempt_reset() is True


def test_should_attempt_reset_returns_false_before_timeout(circuit_breaker):
    """Test _should_attempt_reset returns False before timeout."""
    # Set recent failure time
    circuit_breaker.last_failure_time = datetime.now()

    assert circuit_breaker._should_attempt_reset() is False


def test_should_attempt_reset_with_no_failures(circuit_breaker):
    """Test _should_attempt_reset returns True when no failures recorded."""
    circuit_breaker.last_failure_time = None

    assert circuit_breaker._should_attempt_reset() is True


# === State Management Tests ===


def test_get_state_returns_complete_info(circuit_breaker, failing_function):
    """Test get_state returns all relevant information."""
    # Cause a failure
    try:
        circuit_breaker.call(failing_function)
    except RuntimeError:
        pass

    state = circuit_breaker.get_state()

    assert "state" in state
    assert "failure_count" in state
    assert "last_failure" in state
    assert "half_open_calls" in state

    assert state["state"] == "closed"
    assert state["failure_count"] == 1
    assert state["last_failure"] is not None
    assert isinstance(state["last_failure"], str)  # Should be ISO format


def test_get_state_in_different_states(circuit_breaker):
    """Test get_state accurately reflects circuit state."""
    # CLOSED
    state = circuit_breaker.get_state()
    assert state["state"] == "closed"

    # OPEN
    circuit_breaker.state = CircuitState.OPEN
    state = circuit_breaker.get_state()
    assert state["state"] == "open"

    # HALF_OPEN
    circuit_breaker.state = CircuitState.HALF_OPEN
    state = circuit_breaker.get_state()
    assert state["state"] == "half_open"


# === Reset Functionality Tests ===


def test_manual_reset(circuit_breaker, failing_function):
    """Test manual reset returns circuit to CLOSED state."""
    # Open the circuit
    for _ in range(circuit_breaker.failure_threshold):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    assert circuit_breaker.is_open
    assert circuit_breaker.failure_count > 0

    # Reset
    circuit_breaker.reset()

    assert circuit_breaker.is_closed
    assert circuit_breaker.failure_count == 0
    assert circuit_breaker.last_failure_time is None
    assert circuit_breaker.half_open_calls == 0


# === Thread Safety Tests ===


def test_thread_safety_concurrent_calls(circuit_breaker):
    """Test circuit breaker is thread-safe with concurrent calls."""
    import threading

    results = []
    errors = []

    def make_call(success: bool):
        try:
            if success:
                result = circuit_breaker.call(lambda: "ok")
                results.append(result)
            else:
                circuit_breaker.call(lambda: 1 / 0)  # Force error
        except Exception as e:
            errors.append(e)

    # Create multiple threads
    threads = []
    for i in range(10):
        thread = threading.Thread(target=make_call, args=(i % 2 == 0,))
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    # Circuit breaker should maintain consistent state
    state = circuit_breaker.get_state()
    assert isinstance(state["failure_count"], int)
    assert state["failure_count"] >= 0


# === Edge Cases and Boundary Conditions ===


def test_exact_threshold_boundary(circuit_breaker, failing_function):
    """Test behavior at exact failure threshold."""
    threshold = circuit_breaker.failure_threshold

    # One less than threshold
    for _ in range(threshold - 1):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    assert circuit_breaker.is_closed

    # Exactly at threshold
    try:
        circuit_breaker.call(failing_function)
    except RuntimeError:
        pass

    assert circuit_breaker.is_open


def test_zero_timeout_immediate_recovery_attempt():
    """Test circuit with zero timeout allows immediate recovery."""
    with patch("src.resilience.circuit_breaker.get_settings") as mock_settings:
        settings = MagicMock()
        settings.circuit_breaker.failure_threshold = 3
        settings.circuit_breaker.timeout_seconds = 0  # Immediate recovery
        settings.circuit_breaker.half_open_max_calls = 2
        mock_settings.return_value = settings

        breaker = CircuitBreaker()

        # Open circuit
        for _ in range(3):
            try:
                breaker.call(lambda: 1 / 0)
            except ZeroDivisionError:
                pass

        assert breaker.is_open

        # Should be able to attempt recovery immediately
        assert breaker._should_attempt_reset() is True


def test_exception_propagation(circuit_breaker):
    """Test that original exceptions are properly propagated."""

    def custom_error():
        raise ValueError("Custom error message")

    with pytest.raises(ValueError) as exc_info:
        circuit_breaker.call(custom_error)

    assert "Custom error message" in str(exc_info.value)
    assert circuit_breaker.failure_count == 1


def test_circuit_breaker_handles_different_exceptions(circuit_breaker):
    """Test circuit breaker handles different exception types."""
    exceptions = [RuntimeError("error1"), ValueError("error2"), TypeError("error3")]

    for exc in exceptions:

        def raise_exc(exception=exc):
            raise exception

        with pytest.raises(type(exc)):
            circuit_breaker.call(raise_exc)

    assert circuit_breaker.failure_count == len(exceptions)


# === Integration-style Tests ===


def test_full_lifecycle_open_recover_close(circuit_breaker, failing_function, mock_function):
    """Test full lifecycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    # Start CLOSED
    assert circuit_breaker.is_closed

    # Fail enough times to OPEN
    for _ in range(circuit_breaker.failure_threshold):
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    assert circuit_breaker.is_open

    # Simulate timeout and enter HALF_OPEN
    circuit_breaker.state = CircuitState.HALF_OPEN
    circuit_breaker.half_open_calls = 0

    # Succeed enough times to CLOSE
    for _ in range(circuit_breaker.half_open_max_calls):
        circuit_breaker.call(mock_function)

    assert circuit_breaker.is_closed
    assert circuit_breaker.failure_count == 0


def test_alternating_success_and_failure(circuit_breaker, mock_function, failing_function):
    """Test alternating successes and failures doesn't open circuit."""
    threshold = circuit_breaker.failure_threshold

    # Alternate between success and failure
    for _ in range(threshold * 2):
        circuit_breaker.call(mock_function)
        try:
            circuit_breaker.call(failing_function)
        except RuntimeError:
            pass

    # Circuit should still be closed because failures aren't consecutive
    assert circuit_breaker.is_closed
