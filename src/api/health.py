"""Health check endpoints for monitoring and readiness probes."""

import logging

from fastapi import APIRouter, Response, status

from src.resilience.health_probes import HealthProbes

logger = logging.getLogger(__name__)

# Create router with health prefix
router = APIRouter(prefix="/health", tags=["health"])

# Initialize health probes
health_probes = HealthProbes()


@router.get("/live")
async def liveness() -> dict:
    """Liveness probe endpoint.

    This endpoint indicates whether the application is alive and running.
    It performs minimal checks and should always return healthy unless
    the application has crashed or is completely unresponsive.

    Used by:
        - Kubernetes liveness probes
        - Docker health checks
        - Load balancers

    Returns:
        Dictionary with liveness status:
            - status: Always "healthy" if executing
            - timestamp: Current UTC timestamp
            - probe: Type of probe ("liveness")

    Example Response:
        ```json
        {
            "status": "healthy",
            "timestamp": "2025-10-24T10:30:00.123456",
            "probe": "liveness"
        }
        ```
    """
    result = await health_probes.liveness()
    logger.debug("Liveness probe executed successfully")
    return result


@router.get("/ready")
async def readiness(response: Response) -> dict:
    """Readiness probe endpoint.

    This endpoint indicates whether the application is ready to accept traffic.
    It performs comprehensive checks of all dependencies including:
        - Elasticsearch connectivity and health
        - LLM service availability
        - Circuit breaker state

    If any dependency is unhealthy, returns 503 Service Unavailable to
    inform orchestrators to stop routing traffic to this instance.

    Used by:
        - Kubernetes readiness probes
        - Load balancers for traffic routing
        - Health monitoring systems

    Returns:
        Dictionary with readiness status:
            - status: "healthy" or "unhealthy"
            - timestamp: Current UTC timestamp
            - probe: Type of probe ("readiness")
            - checks: Detailed status of each dependency

    Status Codes:
        - 200 OK: All dependencies healthy, ready to accept traffic
        - 503 Service Unavailable: One or more dependencies unhealthy

    Example Response (Healthy):
        ```json
        {
            "status": "healthy",
            "timestamp": "2025-10-24T10:30:00.123456",
            "probe": "readiness",
            "checks": {
                "elasticsearch": {
                    "status": "healthy",
                    "response_time_ms": 45
                },
                "llm": {
                    "status": "healthy",
                    "response_time_ms": 120
                }
            }
        }
        ```

    Example Response (Unhealthy):
        ```json
        {
            "status": "unhealthy",
            "timestamp": "2025-10-24T10:30:00.123456",
            "probe": "readiness",
            "checks": {
                "elasticsearch": {
                    "status": "unhealthy",
                    "error": "Connection refused"
                },
                "llm": {
                    "status": "healthy",
                    "response_time_ms": 120
                }
            }
        }
        ```
    """
    result = await health_probes.readiness()

    if result["status"] != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning(f"Readiness probe failed: {result}")
    else:
        logger.debug("Readiness probe executed successfully")

    return result


@router.get("/startup")
async def startup(response: Response) -> dict:
    """Startup probe endpoint.

    This endpoint indicates whether the application has completed initialization.
    It performs one-time checks during application startup to verify all
    components are properly initialized before accepting traffic.

    The startup probe is typically checked with a longer timeout and interval
    than readiness probes, allowing the application time to initialize.

    Used by:
        - Kubernetes startup probes
        - Deployment orchestration
        - Initial health verification

    Returns:
        Dictionary with startup status:
            - status: "healthy" or "unhealthy"
            - timestamp: Current UTC timestamp
            - probe: Type of probe ("startup")
            - checks: Detailed status of each component
            - startup_complete: Boolean indicating if startup finished

    Status Codes:
        - 200 OK: Application initialized successfully
        - 503 Service Unavailable: Initialization incomplete or failed

    Example Response (Complete):
        ```json
        {
            "status": "healthy",
            "timestamp": "2025-10-24T10:30:00.123456",
            "probe": "startup",
            "startup_complete": true,
            "checks": {
                "elasticsearch": {
                    "status": "healthy",
                    "response_time_ms": 45
                },
                "llm": {
                    "status": "healthy",
                    "response_time_ms": 120
                }
            }
        }
        ```

    Example Response (Incomplete):
        ```json
        {
            "status": "unhealthy",
            "timestamp": "2025-10-24T10:30:00.123456",
            "probe": "startup",
            "startup_complete": false,
            "checks": {
                "elasticsearch": {
                    "status": "initializing"
                }
            }
        }
        ```
    """
    result = await health_probes.startup()

    if result["status"] != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning(f"Startup probe failed: {result}")
    else:
        logger.info("Startup probe completed successfully")

    return result
