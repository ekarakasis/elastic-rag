"""Unit tests for health probes.

This module tests the HealthProbes class with comprehensive coverage of:
- Liveness probe (always healthy)
- Readiness probe (checks all dependencies)
- Startup probe (one-time initialization check)
- Elasticsearch health checks
- LMStudio/LLM service health checks
- Timeout handling
- Error scenarios
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.resilience.health_probes import HealthProbes


@pytest.fixture
def health_probes():
    """Create a HealthProbes instance."""
    return HealthProbes()


@pytest.fixture
def mock_es_healthy():
    """Mock a healthy Elasticsearch response."""
    mock_es = MagicMock()
    mock_es.cluster.health.return_value = {"status": "green"}
    return mock_es


@pytest.fixture
def mock_es_yellow():
    """Mock a yellow Elasticsearch response (still acceptable)."""
    mock_es = MagicMock()
    mock_es.cluster.health.return_value = {"status": "yellow"}
    return mock_es


@pytest.fixture
def mock_es_unhealthy():
    """Mock an unhealthy Elasticsearch response."""
    mock_es = MagicMock()
    mock_es.cluster.health.return_value = {"status": "red"}
    return mock_es


# === Initialization Tests ===


def test_health_probes_initialization(health_probes):
    """Test HealthProbes initializes correctly."""
    assert health_probes.settings is not None
    assert health_probes.timeout > 0
    assert health_probes.startup_complete is False


# === Liveness Probe Tests ===


@pytest.mark.asyncio
async def test_liveness_always_healthy(health_probes):
    """Test liveness probe always returns healthy."""
    result = await health_probes.liveness()

    assert result["status"] == "healthy"
    assert result["probe"] == "liveness"
    assert "timestamp" in result
    assert isinstance(result["timestamp"], str)


@pytest.mark.asyncio
async def test_liveness_response_structure(health_probes):
    """Test liveness response has correct structure."""
    result = await health_probes.liveness()

    assert "status" in result
    assert "timestamp" in result
    assert "probe" in result
    assert len(result) == 3  # Only these three fields


# === Readiness Probe Tests ===


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_readiness_all_healthy(mock_client, mock_es_class, health_probes, mock_es_healthy):
    """Test readiness probe when all services are healthy."""
    # Mock Elasticsearch
    mock_es_class.return_value = mock_es_healthy

    # Mock httpx client for LMStudio
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_context

    result = await health_probes.readiness()

    assert result["status"] == "healthy"
    assert result["probe"] == "readiness"
    assert "timestamp" in result
    assert "checks" in result

    # Check individual service checks
    assert result["checks"]["elasticsearch"]["status"] == "healthy"
    assert result["checks"]["lmstudio"]["status"] == "healthy"


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_readiness_elasticsearch_down(mock_client, mock_es_class, health_probes):
    """Test readiness probe when Elasticsearch is down."""
    # Mock Elasticsearch failure
    mock_es_class.side_effect = Exception("Connection refused")

    # Mock LMStudio healthy
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_context

    result = await health_probes.readiness()

    assert result["status"] == "unhealthy"
    assert result["checks"]["elasticsearch"]["status"] == "unhealthy"


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_readiness_lmstudio_down(mock_client, mock_es_class, health_probes, mock_es_healthy):
    """Test readiness probe when LMStudio is down."""
    # Mock Elasticsearch healthy
    mock_es_class.return_value = mock_es_healthy

    # Mock LMStudio failure
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    mock_client.return_value = mock_context

    result = await health_probes.readiness()

    assert result["status"] == "unhealthy"
    assert result["checks"]["lmstudio"]["status"] == "unhealthy"


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_readiness_all_services_down(mock_client, mock_es_class, health_probes):
    """Test readiness probe when all services are down."""
    # Mock Elasticsearch failure
    mock_es_class.side_effect = Exception("Connection refused")

    # Mock LMStudio failure
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    mock_client.return_value = mock_context

    result = await health_probes.readiness()

    assert result["status"] == "unhealthy"
    assert result["checks"]["elasticsearch"]["status"] == "unhealthy"
    assert result["checks"]["lmstudio"]["status"] == "unhealthy"


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_readiness_yellow_elasticsearch(
    mock_client, mock_es_class, health_probes, mock_es_yellow
):
    """Test readiness probe accepts yellow Elasticsearch status."""
    # Mock Elasticsearch with yellow status (acceptable)
    mock_es_class.return_value = mock_es_yellow

    # Mock LMStudio healthy
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_context

    result = await health_probes.readiness()

    assert result["status"] == "healthy"
    assert result["checks"]["elasticsearch"]["status"] == "healthy"


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_readiness_red_elasticsearch(
    mock_client, mock_es_class, health_probes, mock_es_unhealthy
):
    """Test readiness probe rejects red Elasticsearch status."""
    # Mock Elasticsearch with red status (unhealthy)
    mock_es_class.return_value = mock_es_unhealthy

    # Mock LMStudio healthy
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_context

    result = await health_probes.readiness()

    assert result["status"] == "unhealthy"
    assert result["checks"]["elasticsearch"]["status"] == "unhealthy"


# === Startup Probe Tests ===


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
async def test_startup_success(mock_es_class, health_probes, mock_es_healthy):
    """Test startup probe succeeds with healthy Elasticsearch."""
    mock_es_class.return_value = mock_es_healthy

    result = await health_probes.startup()

    assert result["status"] == "healthy"
    assert result["probe"] == "startup"
    assert "timestamp" in result
    assert "error" not in result
    assert health_probes.startup_complete is True


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
async def test_startup_failure(mock_es_class, health_probes):
    """Test startup probe fails when Elasticsearch is unavailable."""
    mock_es_class.side_effect = Exception("Connection refused")

    result = await health_probes.startup()

    assert result["status"] == "unhealthy"
    assert result["probe"] == "startup"
    assert "error" in result
    assert health_probes.startup_complete is False


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
async def test_startup_only_runs_once(mock_es_class, health_probes, mock_es_healthy):
    """Test startup probe only runs checks once."""
    mock_es_class.return_value = mock_es_healthy

    # First call
    result1 = await health_probes.startup()
    assert result1["status"] == "healthy"
    assert health_probes.startup_complete is True

    # Second call should not re-run checks
    mock_es_class.reset_mock()
    result2 = await health_probes.startup()

    assert result2["status"] == "healthy"
    # Elasticsearch should not have been called again
    mock_es_class.assert_not_called()


@pytest.mark.asyncio
async def test_startup_reset(health_probes):
    """Test startup flag can be reset for testing."""
    health_probes.startup_complete = True

    health_probes.reset_startup()

    assert health_probes.startup_complete is False


# === Elasticsearch Health Check Tests ===


@patch("src.resilience.health_probes.Elasticsearch")
def test_check_elasticsearch_green(mock_es_class, health_probes, mock_es_healthy):
    """Test Elasticsearch check with green status."""
    mock_es_class.return_value = mock_es_healthy

    result = health_probes._check_elasticsearch()

    assert result is True
    mock_es_class.assert_called_once()


@patch("src.resilience.health_probes.Elasticsearch")
def test_check_elasticsearch_yellow(mock_es_class, health_probes, mock_es_yellow):
    """Test Elasticsearch check with yellow status (acceptable)."""
    mock_es_class.return_value = mock_es_yellow

    result = health_probes._check_elasticsearch()

    assert result is True


@patch("src.resilience.health_probes.Elasticsearch")
def test_check_elasticsearch_red(mock_es_class, health_probes, mock_es_unhealthy):
    """Test Elasticsearch check with red status (unhealthy)."""
    mock_es_class.return_value = mock_es_unhealthy

    result = health_probes._check_elasticsearch()

    assert result is False


@patch("src.resilience.health_probes.Elasticsearch")
def test_check_elasticsearch_connection_error(mock_es_class, health_probes):
    """Test Elasticsearch check with connection error."""
    mock_es_class.side_effect = Exception("Connection refused")

    result = health_probes._check_elasticsearch()

    assert result is False


@patch("src.resilience.health_probes.Elasticsearch")
def test_check_elasticsearch_timeout(mock_es_class, health_probes):
    """Test Elasticsearch check respects timeout."""
    mock_es_class.return_value.cluster.health.side_effect = TimeoutError("Timeout")

    result = health_probes._check_elasticsearch()

    assert result is False


# === LMStudio Health Check Tests ===


@pytest.mark.asyncio
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_check_lmstudio_healthy(mock_client, health_probes):
    """Test LMStudio check with successful response."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_context

    result = await health_probes._check_lmstudio()

    assert result is True


@pytest.mark.asyncio
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_check_lmstudio_non_200_status(mock_client, health_probes):
    """Test LMStudio check with non-200 status code."""
    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_context

    result = await health_probes._check_lmstudio()

    assert result is False


@pytest.mark.asyncio
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_check_lmstudio_connection_error(mock_client, health_probes):
    """Test LMStudio check with connection error."""
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    mock_client.return_value = mock_context

    result = await health_probes._check_lmstudio()

    assert result is False


@pytest.mark.asyncio
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_check_lmstudio_timeout(mock_client, health_probes):
    """Test LMStudio check handles timeout."""
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(
        side_effect=httpx.TimeoutException("Timeout")
    )
    mock_client.return_value = mock_context

    result = await health_probes._check_lmstudio()

    assert result is False


# === Response Structure Tests ===


@pytest.mark.asyncio
async def test_liveness_response_format(health_probes):
    """Test liveness response has correct format."""
    result = await health_probes.liveness()

    # Required fields
    assert "status" in result
    assert "timestamp" in result
    assert "probe" in result

    # Field types
    assert isinstance(result["status"], str)
    assert isinstance(result["timestamp"], str)
    assert isinstance(result["probe"], str)


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
@patch("src.resilience.health_probes.httpx.AsyncClient")
async def test_readiness_response_format(
    mock_client, mock_es_class, health_probes, mock_es_healthy
):
    """Test readiness response has correct format."""
    mock_es_class.return_value = mock_es_healthy

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.return_value = mock_context

    result = await health_probes.readiness()

    # Required fields
    assert "status" in result
    assert "timestamp" in result
    assert "probe" in result
    assert "checks" in result

    # Field types
    assert isinstance(result["status"], str)
    assert isinstance(result["timestamp"], str)
    assert isinstance(result["probe"], str)
    assert isinstance(result["checks"], dict)

    # Check structure
    assert "elasticsearch" in result["checks"]
    assert "lmstudio" in result["checks"]
    assert "status" in result["checks"]["elasticsearch"]
    assert "required" in result["checks"]["elasticsearch"]


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
async def test_startup_response_format_success(mock_es_class, health_probes, mock_es_healthy):
    """Test startup response format on success."""
    mock_es_class.return_value = mock_es_healthy

    result = await health_probes.startup()

    # Required fields
    assert "status" in result
    assert "timestamp" in result
    assert "probe" in result

    # Should NOT have error on success
    assert "error" not in result


@pytest.mark.asyncio
@patch("src.resilience.health_probes.Elasticsearch")
async def test_startup_response_format_failure(mock_es_class, health_probes):
    """Test startup response format on failure."""
    mock_es_class.side_effect = Exception("Connection error")

    result = await health_probes.startup()

    # Required fields
    assert "status" in result
    assert "timestamp" in result
    assert "probe" in result

    # Should have error on failure
    assert "error" in result
    assert isinstance(result["error"], str)
