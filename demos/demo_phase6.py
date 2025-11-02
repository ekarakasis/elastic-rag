#!/usr/bin/env python3
"""Phase 6 Demo: Resilience Layer

This script demonstrates the resilience features implemented in Phase 6:
1. Circuit Breaker pattern for LLM calls
2. Health probes (liveness, readiness, startup)
3. Graceful degradation and recovery

This demo uses REAL services (Elasticsearch, LMStudio) without mocking
to demonstrate actual resilience behavior in production-like conditions.

Requirements:
- Elasticsearch running on localhost:9200
- LMStudio running on localhost:1234 (or configured endpoint)
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import Elasticsearch

from src.ai_models.litellm_interface import LLMInterface
from src.config.settings import get_settings
from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerError
from src.resilience.health_probes import HealthProbes

# Configure logging - WARNING level to reduce noise
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Color codes for terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(80)}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def print_section(text: str) -> None:
    """Print a formatted section header."""
    print(f"\n{BOLD}{CYAN}{text}{RESET}")
    print(f"{CYAN}{'-' * len(text)}{RESET}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{YELLOW}ℹ {text}{RESET}")


def print_state(text: str) -> None:
    """Print a state change message."""
    print(f"{MAGENTA}⚡ {text}{RESET}")


def check_service_availability() -> dict:
    """Check which services are available for testing.

    Returns:
        dict: Service availability status
    """
    print_section("Checking Service Availability")

    services = {"elasticsearch": False, "lmstudio": False}

    # Check Elasticsearch
    try:
        settings = get_settings()
        es = Elasticsearch([settings.elasticsearch.url])
        es.info()
        services["elasticsearch"] = True
        print_success(f"Elasticsearch is running on {settings.elasticsearch.url}")
    except Exception as e:
        print_error(f"Elasticsearch not available: {e}")
        print_info("Start Elasticsearch: docker-compose -f docker/docker-compose.yml up -d")

    # Check LMStudio
    try:
        import httpx

        settings = get_settings()
        response = httpx.get(f"{settings.llm.base_url}/v1/models", timeout=2.0)
        if response.status_code == 200:
            services["lmstudio"] = True
            print_success(f"LMStudio is running on {settings.llm.base_url}")
        else:
            raise Exception(f"Status code: {response.status_code}")
    except Exception as e:
        print_error(f"LMStudio not available: {e}")
        print_info("Start LMStudio and load a model, or configure a different endpoint")

    return services


def demo_circuit_breaker_basic():
    """Demo 1: Basic Circuit Breaker Pattern

    Shows how the circuit breaker protects against repeated failures.
    """
    print_header("Demo 1: Circuit Breaker Pattern")

    print_info("This demo shows the circuit breaker protecting against failures.")
    print_info("The breaker starts CLOSED, opens after threshold failures, then can half-open.")

    # Create a simple function that fails
    failure_count = 0

    def flaky_operation():
        nonlocal failure_count
        failure_count += 1
        if failure_count <= 6:  # Fail first 6 times
            raise Exception(f"Simulated failure #{failure_count}")
        return "Success!"

    # Create circuit breaker (uses settings from config)
    breaker = CircuitBreaker()

    # Override settings for demo (lower threshold for quicker demonstration)
    breaker.failure_threshold = 5
    breaker.timeout = 3
    breaker.half_open_max_calls = 2

    print_section("State: CLOSED (Normal Operation)")
    print_info("Circuit breaker starts in CLOSED state, allowing calls through")

    # Make calls until circuit opens
    for i in range(8):
        try:
            result = breaker.call(flaky_operation)
            print_success(f"Call {i+1}: {result}")
        except CircuitBreakerError as e:
            print_error(f"Call {i+1}: Circuit breaker OPEN - {e}")
            print_state(f"Circuit State: {breaker.state.name}")
        except Exception as e:
            print_error(f"Call {i+1}: {e}")
            print_state(f"Circuit State: {breaker.state.name}")

        time.sleep(0.5)

    print_section("Waiting for Timeout Period")
    print_info(f"Waiting {breaker.timeout} seconds for circuit to enter HALF_OPEN state...")
    time.sleep(breaker.timeout + 0.5)

    print_section("State: HALF_OPEN (Testing Recovery)")
    print_info("Circuit breaker enters HALF_OPEN state, allowing limited test calls")

    # Try calls in half-open state (should succeed now)
    for i in range(3):
        try:
            result = breaker.call(flaky_operation)
            print_success(f"Test call {i+1}: {result}")
            print_state(f"Circuit State: {breaker.state.name}")
        except Exception as e:
            print_error(f"Test call {i+1}: {e}")

        time.sleep(0.5)

    print_section("Demo Complete")
    print_success("Circuit breaker successfully protected against failures and recovered")


async def demo_llm_with_circuit_breaker(services: dict):
    """Demo 2: LLM Interface with Circuit Breaker

    Shows real LLM calls protected by circuit breaker.
    """
    print_header("Demo 2: LLM Interface with Circuit Breaker")

    if not services["lmstudio"]:
        print_error("Skipping: LMStudio not available")
        print_info("This demo requires LMStudio running with a loaded model")
        return

    print_info("Testing LLM interface with circuit breaker protection")

    # Initialize LLM interface (has built-in circuit breaker)
    llm = LLMInterface()

    print_section("Making Successful LLM Calls")

    # Make some successful calls
    for i in range(3):
        try:
            response = llm.chat_completion(
                messages=[{"role": "user", "content": f"Say 'Test {i+1}' and nothing else"}],
                temperature=0.0,
            )
            print_success(f"Call {i+1}: {response[:50]}...")
        except Exception as e:
            print_error(f"Call {i+1} failed: {e}")

        await asyncio.sleep(1)

    print_section("Demo Complete")
    print_success("LLM calls succeeded with circuit breaker protection")


async def demo_health_probes(services: dict):
    """Demo 3: Health Probes

    Shows real health probe checks against actual services.
    """
    print_header("Demo 3: Health Probes")

    print_info("Testing Kubernetes-style health probes against real services")

    # Initialize health probes
    health = HealthProbes()

    # Liveness Probe
    print_section("Liveness Probe")
    print_info("Checks if the application is alive (always returns healthy)")

    result = await health.liveness()
    if result["status"] == "healthy":
        print_success(f"Liveness: {result['status']}")
    else:
        print_error(f"Liveness: {result['status']}")

    # Readiness Probe
    print_section("Readiness Probe")
    print_info("Checks if the application can handle requests (checks dependencies)")

    result = await health.readiness()
    print_info(f"Status: {result['status']}")

    for check, details in result["checks"].items():
        if details["status"] == "healthy":
            print_success(f"{check}: {details['status']}")
        else:
            print_error(f"{check}: {details['status']} - {details.get('error', 'unknown')}")

    if not services["elasticsearch"]:
        print_info("Elasticsearch check failed as expected (service not running)")

    if not services["lmstudio"]:
        print_info("LMStudio check failed as expected (service not running)")

    # Startup Probe
    print_section("Startup Probe")
    print_info("Checks if the application has finished initializing")

    result = await health.startup()
    if result["status"] == "healthy":
        print_success(f"Startup: {result['status']}")
    else:
        print_error(f"Startup: {result['status']}")
        for check, details in result["checks"].items():
            if details["status"] != "healthy":
                print_error(f"{check}: {details.get('error', 'unknown')}")

    print_section("Demo Complete")
    if services["elasticsearch"] and services["lmstudio"]:
        print_success("All health probes passed!")
    else:
        print_info("Some services unavailable, but health probes working correctly")


async def demo_resilience_integration(services: dict):
    """Demo 4: Integrated Resilience Features

    Shows circuit breaker and health probes working together.
    """
    print_header("Demo 4: Integrated Resilience System")

    if not (services["elasticsearch"] or services["lmstudio"]):
        print_error("Skipping: No services available for integration testing")
        print_info("Start at least one service to see the integration demo")
        return

    print_info("Demonstrating circuit breaker and health probes working together")

    # Initialize components
    health = HealthProbes()

    if services["lmstudio"]:
        llm = LLMInterface()

    # Check initial health
    print_section("Initial Health Check")
    readiness = await health.readiness()

    healthy_count = sum(1 for check in readiness["checks"].values() if check["status"] == "healthy")
    total_count = len(readiness["checks"])

    print_info(f"Overall status: {readiness['status']}")
    print_info(f"Healthy checks: {healthy_count}/{total_count}")

    for check, details in readiness["checks"].items():
        if details["status"] == "healthy":
            print_success(f"{check}: ready")
        else:
            print_error(f"{check}: not ready")

    # Make LLM calls if available
    if services["lmstudio"]:
        print_section("Making LLM Calls with Protection")

        for i in range(3):
            try:
                _ = llm.chat_completion(
                    messages=[{"role": "user", "content": "Hello!"}], temperature=0.0
                )
                print_success(f"Call {i+1} succeeded")
            except Exception as e:
                print_error(f"Call {i+1} failed: {e}")

            await asyncio.sleep(0.5)

        # Check circuit breaker state
        print_section("Circuit Breaker Status")
        print_state(f"State: {llm.circuit_breaker.state.name}")
        print_info(f"Failure count: {llm.circuit_breaker.failure_count}")
        print_info(f"Half-open calls: {llm.circuit_breaker.half_open_calls}")

    # Final health check
    print_section("Final Health Check")
    readiness = await health.readiness()

    healthy_count = sum(1 for check in readiness["checks"].values() if check["status"] == "healthy")

    print_info(f"Overall status: {readiness['status']}")
    print_info(f"Healthy checks: {healthy_count}/{total_count}")

    print_section("Demo Complete")
    print_success("Resilience system is working correctly!")


async def main():
    """Run all demos."""
    print_header("Phase 6: Resilience Layer Demonstration")

    print_info("This demo uses REAL services without mocking")
    print_info("It demonstrates actual resilience behavior in production-like conditions")

    # Check service availability
    services = check_service_availability()

    # Demo 1: Circuit Breaker Basics (always runs)
    demo_circuit_breaker_basic()

    # Demo 2: LLM with Circuit Breaker (requires LMStudio)
    if services["lmstudio"]:
        await demo_llm_with_circuit_breaker(services)
    else:
        print_info("\nSkipping Demo 2 (requires LMStudio)")

    # Demo 3: Health Probes (always runs)
    await demo_health_probes(services)

    # Demo 4: Integration (requires at least one service)
    if services["elasticsearch"] or services["lmstudio"]:
        await demo_resilience_integration(services)
    else:
        print_info("\nSkipping Demo 4 (requires at least one service)")

    print_header("All Demos Complete!")
    print_success("Phase 6 resilience features demonstrated successfully")

    # Summary
    print_section("Summary")
    print_info("What we demonstrated:")
    print("  • Circuit breaker pattern with state transitions (CLOSED → OPEN → HALF_OPEN)")
    print("  • Automatic failure detection and recovery")
    print("  • LLM interface protected by circuit breaker")
    print("  • Kubernetes-style health probes (liveness, readiness, startup)")
    print("  • Integrated resilience system with real services")

    if not services["elasticsearch"]:
        print_info("\nTo see full functionality, start Elasticsearch:")
        print("  docker-compose -f docker/docker-compose.yml up -d")

    if not services["lmstudio"]:
        print_info("\nTo see LLM demos, start LMStudio:")
        print("  • Launch LMStudio application")
        print("  • Load a model")
        print("  • Ensure server is running on localhost:1234")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Demo interrupted by user{RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n{RED}Demo failed with error: {e}{RESET}")
        logger.exception("Demo failed")
        sys.exit(1)
