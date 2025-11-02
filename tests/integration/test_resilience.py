"""Integration tests for resilience layer.

This module tests the integration of circuit breaker and health probes
with real-world scenarios, including:
- Circuit breaker behavior with LLM failures
- Health probe behavior with real service states
- Recovery scenarios
- End-to-end resilience workflows
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.ai_models.litellm_interface import LLMInterface
from src.resilience.circuit_breaker import CircuitBreaker, CircuitState
from src.resilience.health_probes import HealthProbes

# === Circuit Breaker Integration Tests ===


@pytest.mark.asyncio
@patch("src.ai_models.litellm_interface.litellm.completion")
async def test_llm_circuit_breaker_full_lifecycle(mock_completion):
    """Test full circuit breaker lifecycle with LLM interface."""
    llm = LLMInterface()
    messages = [{"role": "user", "content": "Test"}]

    # Start with closed circuit
    assert llm.circuit_breaker.is_closed

    # 1. Cause failures to open circuit
    mock_completion.side_effect = Exception("Service unavailable")
    threshold = llm.circuit_breaker.failure_threshold

    for _ in range(threshold):
        with pytest.raises(RuntimeError):
            llm.chat_completion(messages)

    # Circuit should be open
    assert llm.circuit_breaker.is_open

    # 2. Verify fallback response
    with pytest.raises(RuntimeError) as exc_info:
        llm.chat_completion(messages)

    assert "temporarily unavailable" in str(exc_info.value)

    # 3. Simulate recovery by manually transitioning to half-open
    llm.circuit_breaker.state = CircuitState.HALF_OPEN
    llm.circuit_breaker.half_open_calls = 0

    # 4. Service comes back
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Success"
    mock_completion.side_effect = None
    mock_completion.return_value = mock_response

    # 5. Successful calls close circuit
    max_calls = llm.circuit_breaker.half_open_max_calls
    for _ in range(max_calls):
        result = llm.chat_completion(messages)
        assert result == "Success"

    # Circuit should be closed again
    assert llm.circuit_breaker.is_closed


@pytest.mark.asyncio
async def test_circuit_breaker_with_multiple_instances():
    """Test that each LLM instance has its own circuit breaker."""
    llm1 = LLMInterface()
    llm2 = LLMInterface()

    # They should have separate circuit breakers
    assert llm1.circuit_breaker is not llm2.circuit_breaker

    # Opening one shouldn't affect the other
    llm1.circuit_breaker.state = CircuitState.OPEN
    assert llm1.circuit_breaker.is_open
    assert llm2.circuit_breaker.is_closed


@pytest.mark.asyncio
@patch("src.ai_models.litellm_interface.litellm.completion")
async def test_circuit_breaker_prevents_cascading_failures(mock_completion):
    """Test circuit breaker prevents repeated failed attempts."""
    llm = LLMInterface()
    messages = [{"role": "user", "content": "Test"}]

    # Cause failures to open circuit
    mock_completion.side_effect = Exception("Service unavailable")
    threshold = llm.circuit_breaker.failure_threshold

    for _ in range(threshold):
        with pytest.raises(RuntimeError):
            llm.chat_completion(messages)

    # Circuit is now open
    assert llm.circuit_breaker.is_open

    # Reset mock to verify it's not called
    mock_completion.reset_mock()

    # Attempts should fail fast without calling the service
    with pytest.raises(RuntimeError):
        llm.chat_completion(messages)

    # The actual LLM service should not have been called
    # (circuit breaker intercepted it)
    mock_completion.assert_not_called()


# === Health Probes Integration Tests ===


@pytest.mark.asyncio
async def test_health_probes_liveness_never_fails():
    """Test liveness probe is always healthy."""
    probes = HealthProbes()

    # Multiple calls should always succeed
    for _ in range(10):
        result = await probes.liveness()
        assert result["status"] == "healthy"


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_readiness_reflects_service_health(mock_client, mock_es_class):
    """Test readiness probe accurately reflects service health."""
    from unittest.mock import AsyncMock

    probes = HealthProbes()

    # Scenario 1: All services healthy
    mock_es = MagicMock()
    mock_es.cluster.health.return_value = {"status": "green"}
    mock_es_class.return_value = mock_es

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_context

    result = await probes.readiness()
    assert result["status"] == "healthy"

    # Scenario 2: Elasticsearch down
    mock_es_class.side_effect = Exception("Connection refused")

    result = await probes.readiness()
    assert result["status"] == "unhealthy"
    assert result["checks"]["elasticsearch"]["status"] == "unhealthy"


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
async def test_startup_probe_one_time_check(mock_es_class):
    """Test startup probe only performs checks once."""
    probes = HealthProbes()

    # Mock Elasticsearch healthy
    mock_es = MagicMock()
    mock_es.cluster.health.return_value = {"status": "green"}
    mock_es_class.return_value = mock_es

    # First call performs checks
    result1 = await probes.startup()
    assert result1["status"] == "healthy"
    assert probes.startup_complete is True

    # Verify Elasticsearch was called
    call_count_first = mock_es_class.call_count

    # Second call should not re-check
    result2 = await probes.startup()
    assert result2["status"] == "healthy"

    # Elasticsearch should not be called again
    assert mock_es_class.call_count == call_count_first


# === Combined Resilience Tests ===


@pytest.mark.asyncio
@patch("src.ai_models.litellm_interface.litellm.completion")
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_health_probes_detect_circuit_breaker_issues(
    mock_http_client, mock_es_class, mock_llm_completion
):
    """Test that readiness probe can detect LLM service issues."""
    from unittest.mock import AsyncMock

    # Setup mocks
    mock_es = MagicMock()
    mock_es.cluster.health.return_value = {"status": "green"}
    mock_es_class.return_value = mock_es

    # Simulate LLM service down
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    mock_http_client.return_value = mock_context

    # Health probes should detect service is down
    probes = HealthProbes()
    result = await probes.readiness()

    assert result["status"] == "unhealthy"
    assert result["checks"]["lmstudio"]["status"] == "unhealthy"


@pytest.mark.asyncio
@patch("src.ai_models.litellm_interface.litellm.completion")
async def test_circuit_breaker_state_accessible(mock_completion):
    """Test that circuit breaker state can be inspected."""
    llm = LLMInterface()

    # Get initial state
    state = llm.circuit_breaker.get_state()
    assert state["state"] == "closed"
    assert state["failure_count"] == 0

    # Cause a failure
    mock_completion.side_effect = Exception("Error")
    with pytest.raises(RuntimeError):
        llm.chat_completion([{"role": "user", "content": "Test"}])

    # State should reflect failure
    state = llm.circuit_breaker.get_state()
    assert state["failure_count"] == 1
    assert state["last_failure"] is not None


@pytest.mark.asyncio
@patch("src.ai_models.litellm_interface.litellm.completion")
async def test_circuit_breaker_manual_reset(mock_completion):
    """Test circuit breaker can be manually reset."""
    llm = LLMInterface()
    messages = [{"role": "user", "content": "Test"}]

    # Open the circuit
    mock_completion.side_effect = Exception("Service unavailable")
    threshold = llm.circuit_breaker.failure_threshold

    for _ in range(threshold):
        with pytest.raises(RuntimeError):
            llm.chat_completion(messages)

    assert llm.circuit_breaker.is_open

    # Manual reset
    llm.circuit_breaker.reset()

    assert llm.circuit_breaker.is_closed
    assert llm.circuit_breaker.failure_count == 0


# === Error Handling and Edge Cases ===


@pytest.mark.asyncio
@patch("src.ai_models.litellm_interface.litellm.completion")
async def test_different_exception_types_trigger_circuit_breaker(mock_completion):
    """Test that different exception types all count as failures."""
    llm = LLMInterface()
    messages = [{"role": "user", "content": "Test"}]

    # Cause different types of exceptions
    exceptions = [
        RuntimeError("Runtime error"),
        ValueError("Value error"),
        Exception("Generic error"),
    ]

    for exc in exceptions:
        mock_completion.side_effect = exc
        with pytest.raises(RuntimeError):
            llm.chat_completion(messages)

    # All should count as failures
    assert llm.circuit_breaker.failure_count == len(exceptions)


@pytest.mark.asyncio
async def test_health_probes_timeout_handling():
    """Test health probes respect timeout settings."""
    probes = HealthProbes()

    # Verify timeout is configured
    assert probes.timeout > 0

    # This is a simple verification that the timeout property exists
    # Actual timeout behavior is tested in unit tests with mocked delays


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
async def test_startup_probe_failure_recovery(mock_es_class):
    """Test startup probe can recover after initial failure."""
    probes = HealthProbes()

    # First attempt fails
    mock_es_class.side_effect = Exception("Connection refused")
    result1 = await probes.startup()
    assert result1["status"] == "unhealthy"
    assert probes.startup_complete is False

    # Reset for retry
    probes.reset_startup()

    # Second attempt succeeds
    mock_es = MagicMock()
    mock_es.cluster.health.return_value = {"status": "green"}
    mock_es_class.side_effect = None
    mock_es_class.return_value = mock_es

    result2 = await probes.startup()
    assert result2["status"] == "healthy"
    assert probes.startup_complete is True


# === Performance and Concurrency Tests ===


@pytest.mark.asyncio
async def test_circuit_breaker_thread_safety():
    """Test circuit breaker handles concurrent requests safely."""
    breaker = CircuitBreaker()

    success_count = 0
    failure_count = 0

    def successful_call():
        nonlocal success_count
        result = breaker.call(lambda: "success")
        success_count += 1
        return result

    def failing_call():
        nonlocal failure_count
        try:
            breaker.call(lambda: 1 / 0)
        except ZeroDivisionError:
            failure_count += 1

    # Run multiple concurrent calls
    tasks = []
    for i in range(10):
        if i % 2 == 0:
            task = asyncio.create_task(asyncio.to_thread(successful_call))
        else:
            task = asyncio.create_task(asyncio.to_thread(failing_call))
        tasks.append(task)

    # Wait for all tasks
    await asyncio.gather(*tasks, return_exceptions=True)

    # Verify some calls succeeded and some failed
    assert success_count > 0
    assert failure_count > 0

    # Circuit breaker should maintain consistent state
    state = breaker.get_state()
    assert isinstance(state["failure_count"], int)
    assert state["failure_count"] >= 0


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_multiple_readiness_probes_concurrent(mock_client, mock_es_class):
    """Test multiple concurrent readiness probe calls."""
    from unittest.mock import AsyncMock

    probes = HealthProbes()

    # Setup mocks
    mock_es = MagicMock()
    mock_es.cluster.health.return_value = {"status": "green"}
    mock_es_class.return_value = mock_es

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_context

    # Run multiple probes concurrently
    tasks = [probes.readiness() for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # All should succeed
    for result in results:
        assert result["status"] == "healthy"
        assert "checks" in result
