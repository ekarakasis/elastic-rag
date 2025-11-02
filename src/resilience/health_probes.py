"""Health probes for system monitoring and readiness checks.

This module implements health check endpoints following Kubernetes probe patterns:
- Liveness: Is the application alive and running?
- Readiness: Is the application ready to accept traffic?
- Startup: Has the application completed initialization?

These probes help orchestration systems make decisions about traffic routing,
container restarts, and system health.

Example:
    >>> probes = HealthProbes()
    >>> liveness = await probes.liveness()
    >>> readiness = await probes.readiness()
    >>> startup = await probes.startup()
"""

import logging
from datetime import datetime
from typing import Any

import httpx
from elasticsearch import Elasticsearch

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class HealthProbes:
    """Health check implementations for system monitoring.

    Provides three types of health probes:
    - Liveness: Basic application health (is it running?)
    - Readiness: Ready to handle traffic (are dependencies available?)
    - Startup: Initialization complete (one-time check)

    Attributes:
        settings: Application settings
        timeout: Timeout for individual health checks
        startup_complete: Flag indicating if startup checks have passed
    """

    def __init__(self):
        """Initialize health probes with configuration from settings."""
        self.settings = get_settings()
        self.timeout = self.settings.health.check_timeout
        self.startup_complete = False

        logger.info(f"Health probes initialized with timeout={self.timeout}s")

    async def liveness(self) -> dict[str, Any]:
        """Liveness probe - is the application running?

        This is a simple check that returns healthy as long as the code
        is executing. Used by orchestration systems to detect if the
        application has crashed or hung.

        Returns:
            Dictionary containing:
                - status: Always "healthy" if executing
                - timestamp: Current UTC timestamp
                - probe: Probe type ("liveness")

        Example:
            >>> probes = HealthProbes()
            >>> result = await probes.liveness()
            >>> print(result)
            {'status': 'healthy', 'timestamp': '2025-10-24T...', 'probe': 'liveness'}
        """
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "probe": "liveness",
        }

    async def readiness(self) -> dict[str, Any]:
        """Readiness probe - ready to accept traffic?

        Performs comprehensive checks of all dependencies to determine if
        the application is ready to handle requests. Checks:
        - Elasticsearch connectivity and health
        - LMStudio/LLM service availability
        - Circuit breaker state (optional, if available)

        Returns:
            Dictionary containing:
                - status: "healthy" or "unhealthy"
                - timestamp: Current UTC timestamp
                - probe: Probe type ("readiness")
                - checks: Dict with individual check results

        Example:
            >>> probes = HealthProbes()
            >>> result = await probes.readiness()
            >>> print(result['status'])
            'healthy'
        """
        checks = {}
        overall_healthy = True

        # Check Elasticsearch
        es_healthy = self._check_elasticsearch()
        checks["elasticsearch"] = {
            "status": "healthy" if es_healthy else "unhealthy",
            "required": True,
        }
        overall_healthy = overall_healthy and es_healthy

        # Check LMStudio/LLM service
        lm_healthy = await self._check_lmstudio()
        checks["lmstudio"] = {
            "status": "healthy" if lm_healthy else "unhealthy",
            "required": True,
        }
        overall_healthy = overall_healthy and lm_healthy

        # Note: Circuit breaker check would go here if we want to expose it
        # For now, circuit breaker is part of the LLM interface and not
        # directly checked in readiness (it's an internal resilience mechanism)

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "probe": "readiness",
            "checks": checks,
        }

    async def startup(self) -> dict[str, Any]:
        """Startup probe - has initialization completed?

        Performs one-time initialization checks to ensure the application
        is ready to start handling requests. This is typically slower than
        readiness checks and is only run once during startup.

        Checks:
        - Elasticsearch connectivity and index availability
        - Basic configuration validation

        Returns:
            Dictionary containing:
                - status: "healthy" or "unhealthy"
                - timestamp: Current UTC timestamp
                - probe: Probe type ("startup")
                - error: Optional error message if unhealthy

        Example:
            >>> probes = HealthProbes()
            >>> result = await probes.startup()
            >>> print(result['status'])
            'healthy'
        """
        if not self.startup_complete:
            # Perform one-time startup checks
            try:
                # Check Elasticsearch is accessible
                if not self._check_elasticsearch():
                    raise RuntimeError("Elasticsearch not accessible")

                # Mark startup as complete
                self.startup_complete = True
                logger.info("Startup checks completed successfully")

            except Exception as e:
                logger.error(f"Startup check failed: {e}")
                return {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "probe": "startup",
                    "error": str(e),
                }

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "probe": "startup",
        }

    def _check_elasticsearch(self) -> bool:
        """Check Elasticsearch connectivity and health.

        Attempts to connect to Elasticsearch and verify cluster health.
        Accepts GREEN or YELLOW status as healthy.

        Returns:
            True if Elasticsearch is accessible and healthy, False otherwise

        Note:
            Uses configured timeout to prevent hanging
        """
        try:
            es = Elasticsearch(hosts=[self.settings.elasticsearch.url], timeout=self.timeout)

            # Check cluster health
            health = es.cluster.health()

            # GREEN or YELLOW are acceptable
            is_healthy = health["status"] in ["green", "yellow"]

            if is_healthy:
                logger.debug(f"Elasticsearch health: {health['status']}")
            else:
                logger.warning(f"Elasticsearch unhealthy: {health['status']}")

            return is_healthy

        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False

    async def _check_lmstudio(self) -> bool:
        """Check LMStudio/LLM service availability.

        Attempts to connect to the LLM service (LMStudio or other provider)
        and verify it's responding to requests.

        Returns:
            True if LLM service is available, False otherwise

        Note:
            Uses configured timeout to prevent hanging
        """
        try:
            # Use the appropriate base URL (generic LLM or LMStudio)
            if self.settings.llm:
                base_url = self.settings.llm.base_url
            else:
                base_url = self.settings.lmstudio.base_url

            # Try to get models endpoint
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{base_url}/models")
                is_healthy = response.status_code == 200

                if is_healthy:
                    logger.debug(f"LMStudio health check passed: {base_url}")
                else:
                    logger.warning(f"LMStudio returned status {response.status_code}")

                return is_healthy

        except httpx.TimeoutException:
            logger.error(f"LMStudio health check timed out after {self.timeout}s")
            return False
        except Exception as e:
            logger.error(f"LMStudio health check failed: {e}")
            return False

    def reset_startup(self):
        """Reset startup flag (primarily for testing).

        This allows startup checks to be run again, which is useful
        in test scenarios but should not typically be used in production.
        """
        self.startup_complete = False
        logger.debug("Startup flag reset")
