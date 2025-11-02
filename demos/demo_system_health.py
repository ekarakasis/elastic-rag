#!/usr/bin/env python3
"""
System Health Check Demo

Performs comprehensive health checks on all Elastic RAG system components:
1. API health probes (liveness, readiness, startup)
2. Elasticsearch connection and index status
3. LLM service availability (LMStudio)
4. Document processing pipeline
5. Query/retrieval functionality

Helps users verify their complete system setup and diagnose issues.

Usage:
    python demos/demo_system_health.py

Requirements:
    - API server running at http://localhost:8000
    - Elasticsearch available
    - LMStudio running (optional, will warn if unavailable)
"""

import sys
import time
from pathlib import Path

import httpx


# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_section(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}▶ {text}{Colors.RESET}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"  {Colors.GREEN}✓{Colors.RESET} {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"  {Colors.RED}✗{Colors.RESET} {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"    {text}")


def check_api_root(client: httpx.Client, api_url: str) -> tuple[bool, dict | None]:
    """Check API root endpoint."""
    try:
        response = client.get(api_url)
        if response.status_code == 200:
            return True, response.json()
        return False, None
    except Exception as e:
        print_error(f"Failed to connect: {e}")
        return False, None


def check_liveness(client: httpx.Client, api_url: str) -> bool:
    """Check liveness probe."""
    try:
        response = client.get(f"{api_url}/health/live")
        return response.status_code == 200
    except Exception:
        return False


def check_readiness(client: httpx.Client, api_url: str) -> tuple[bool, dict | None]:
    """Check readiness probe."""
    try:
        response = client.get(f"{api_url}/health/ready")
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json() if response.status_code != 500 else None
    except Exception:
        return False, None


def check_startup(client: httpx.Client, api_url: str) -> bool:
    """Check startup probe."""
    try:
        response = client.get(f"{api_url}/health/startup")
        return response.status_code == 200
    except Exception:
        return False


def check_elasticsearch(client: httpx.Client, api_url: str) -> tuple[bool, dict | None]:
    """Check Elasticsearch connection and document count."""
    try:
        response = client.get(f"{api_url}/documents/")
        if response.status_code == 200:
            data = response.json()
            return True, data
        return False, None
    except Exception:
        return False, None


def test_upload_capability(client: httpx.Client, api_url: str) -> tuple[bool, dict | None]:
    """Test document upload and processing."""
    test_file = Path("health_check_test.txt")
    test_content = "This is a health check test document."

    try:
        # Create test file
        test_file.write_text(test_content)

        # Upload
        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "text/plain")}
            response = client.post(f"{api_url}/documents/upload", files=files)

        if response.status_code == 200:
            return True, response.json()
        return False, None
    except Exception:
        return False, None
    finally:
        if test_file.exists():
            test_file.unlink()


def verify_uploaded_document(
    client: httpx.Client, api_url: str, filename: str
) -> tuple[bool, dict | None]:
    """Verify document was indexed."""
    try:
        time.sleep(1)  # Brief wait for indexing
        response = client.get(f"{api_url}/documents/")
        if response.status_code == 200:
            data = response.json()
            documents = data.get("documents", [])

            for doc in documents:
                if doc.get("source_file") == filename:
                    return True, doc
        return False, None
    except Exception:
        return False, None


def test_query_capability(client: httpx.Client, api_url: str) -> tuple[bool, dict | None]:
    """Test query/retrieval functionality."""
    try:
        response = client.post(
            f"{api_url}/query/",
            json={"query": "test", "max_results": 1},
            timeout=30.0,
        )

        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 503:
            # Circuit breaker open
            return False, {"error": "LLM service unavailable (circuit breaker open)"}
        return False, None
    except Exception as e:
        return False, {"error": str(e)}


def main():
    """Run comprehensive system health checks."""
    print_header("Elastic RAG System Health Check")

    api_url = "http://localhost:8000"
    client = httpx.Client(timeout=30.0)

    overall_status = "healthy"
    warnings = []
    errors = []

    try:
        # 1. API Root
        print_section("1. API Root Endpoint")
        success, root_data = check_api_root(client, api_url)

        if success:
            print_success("API is reachable")
            print_info(f"Name: {root_data.get('name')}")
            print_info(f"Version: {root_data.get('version')}")
            print_info(f"Status: {root_data.get('status')}")
        else:
            print_error("API is not reachable")
            print_info("Make sure the server is running: task run")
            errors.append("API not reachable")
            overall_status = "critical"

        # 2. Health Probes
        print_section("2. Health Probes")

        # Liveness
        if check_liveness(client, api_url):
            print_success("Liveness probe: healthy")
        else:
            print_error("Liveness probe: failed")
            errors.append("Liveness probe failed")
            overall_status = "critical"

        # Startup
        if check_startup(client, api_url):
            print_success("Startup probe: healthy")
        else:
            print_error("Startup probe: failed")
            errors.append("Startup probe failed")
            overall_status = "critical"

        # Readiness
        ready, ready_data = check_readiness(client, api_url)
        if ready:
            print_success("Readiness probe: healthy")
            if ready_data:
                dependencies = ready_data.get("dependencies", {})
                for dep_name, dep_status in dependencies.items():
                    if dep_status == "healthy":
                        print_info(f"  ✓ {dep_name}: healthy")
                    else:
                        print_info(f"  ✗ {dep_name}: {dep_status}")
        else:
            print_warning("Readiness probe: not ready")
            warnings.append("API not ready (dependencies may be unavailable)")
            if ready_data:
                dependencies = ready_data.get("dependencies", {})
                for dep_name, dep_status in dependencies.items():
                    print_info(f"  ✗ {dep_name}: {dep_status}")
            if overall_status == "healthy":
                overall_status = "degraded"

        # 3. Elasticsearch
        print_section("3. Elasticsearch")
        es_ok, es_data = check_elasticsearch(client, api_url)

        if es_ok:
            print_success("Elasticsearch is accessible")
            doc_count = len(es_data.get("documents", []))
            print_info(f"Documents indexed: {doc_count}")

            if doc_count > 0:
                # Show sample
                sample_docs = es_data.get("documents", [])[:3]
                print_info("Sample documents:")
                for doc in sample_docs:
                    print_info(f"  • {doc.get('source_file')} ({doc.get('chunks_count')} chunks)")
        else:
            print_error("Elasticsearch not accessible")
            print_info("Check Elasticsearch connection in API logs")
            errors.append("Elasticsearch not accessible")
            overall_status = "critical"

        # 4. Document Upload Pipeline
        print_section("4. Document Upload & Processing Pipeline")
        upload_ok, upload_data = test_upload_capability(client, api_url)

        if upload_ok:
            print_success("Document upload works")
            print_info(f"Chunks created: {upload_data.get('chunks_created')}")

            # Verify indexing
            print_info("Verifying indexing to Elasticsearch...")
            indexed, doc_info = verify_uploaded_document(client, api_url, "health_check_test.txt")

            if indexed:
                print_success("Document indexed successfully")
                print_info(f"Chunks in Elasticsearch: {doc_info.get('chunks_count')}")
            else:
                print_error("Document NOT indexed to Elasticsearch")
                print_info("This was the v1.0.0 bug - check API version (should be ≥ 1.0.1)")
                errors.append("Upload succeeds but indexing fails")
                overall_status = "critical"
        else:
            print_error("Document upload failed")
            errors.append("Document upload pipeline broken")
            overall_status = "critical"

        # 5. Query/Retrieval
        print_section("5. Query & Retrieval System")
        query_ok, query_data = test_query_capability(client, api_url)

        if query_ok:
            print_success("Query system works")
            answer_length = len(query_data.get("answer", ""))
            source_count = len(query_data.get("sources", []))
            print_info(f"Answer length: {answer_length} characters")
            print_info(f"Sources retrieved: {source_count}")
        else:
            error_msg = query_data.get("error", "Unknown error") if query_data else "Request failed"

            if "circuit breaker" in error_msg.lower() or "unavailable" in error_msg.lower():
                print_warning("Query system degraded: LLM service unavailable")
                print_info("LMStudio may not be running")
                print_info("Start LMStudio: lms server start")
                warnings.append("LLM service unavailable")
                if overall_status == "healthy":
                    overall_status = "degraded"
            else:
                print_error(f"Query system failed: {error_msg}")
                errors.append("Query system broken")
                if overall_status == "healthy":
                    overall_status = "degraded"

        # Summary
        print_header("Health Check Summary")

        if overall_status == "healthy":
            print(f"{Colors.BOLD}{Colors.GREEN}✓ SYSTEM STATUS: HEALTHY{Colors.RESET}")
            print("\nAll systems operational!")
        elif overall_status == "degraded":
            print(f"{Colors.BOLD}{Colors.YELLOW}⚠ SYSTEM STATUS: DEGRADED{Colors.RESET}")
            print("\nSome components are unavailable but core functionality works.")
        else:
            print(f"{Colors.BOLD}{Colors.RED}✗ SYSTEM STATUS: CRITICAL{Colors.RESET}")
            print("\nCritical components are not working.")

        # Warnings
        if warnings:
            print(f"\n{Colors.YELLOW}Warnings:{Colors.RESET}")
            for warning in warnings:
                print(f"  ⚠ {warning}")

        # Errors
        if errors:
            print(f"\n{Colors.RED}Errors:{Colors.RESET}")
            for error in errors:
                print(f"  ✗ {error}")

        # Recommendations
        print(f"\n{Colors.CYAN}Recommendations:{Colors.RESET}")

        if "API not reachable" in errors:
            print("  1. Start the API server: task run")

        if "Elasticsearch not accessible" in errors:
            print("  2. Start Elasticsearch: docker compose up -d")

        if "LLM service unavailable" in warnings:
            print("  3. Start LMStudio: lms server start")
            print("     Or configure a different LLM in LITELLM_BASE_URL")

        if "indexing fails" in str(errors):
            print("  4. Upgrade to v1.0.1+ to fix indexing bug")
            print("     Check current version: curl http://localhost:8000/")

        if not errors and not warnings:
            print("  • System is fully operational!")
            print("  • You can start using the RAG system")
            print("  • Try the upload verification demo: python demos/demo_upload_verification.py")

        print()

        # Exit code
        if overall_status == "critical":
            sys.exit(1)
        elif overall_status == "degraded":
            sys.exit(2)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print_error("\nHealth check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
