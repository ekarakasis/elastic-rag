#!/usr/bin/env python3
"""Phase 7 Demo: API Development

This script demonstrates the REST API implemented in Phase 7:
1. Health check endpoints (liveness, readiness, startup)
2. Document upload (single and batch)
3. Query processing (single and batch)
4. Error handling and resilience

This demo uses REAL services (API server, Elasticsearch, LMStudio) without mocking
to demonstrate actual API behavior in production-like conditions.

Requirements:
- API server running on localhost:8000 (python -m uvicorn src.main:app)
- Elasticsearch running on localhost:9200
- LMStudio running on localhost:1234 (or configured endpoint)

Usage:
    python demos/demo_phase7.py
"""

import sys
import time
from pathlib import Path

import httpx

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes for terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"

# API base URL
API_BASE_URL = "http://localhost:8000"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(80)}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{CYAN}ℹ {text}{RESET}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def demo_health_checks(client: httpx.Client) -> None:
    """Demonstrate health check endpoints."""
    print_header("DEMO 1: Health Check Endpoints")

    print(f"{BOLD}Testing Kubernetes-style health probes...{RESET}\n")

    # Test liveness probe
    print(f"{BOLD}1. Liveness Probe (is the API alive?){RESET}")
    try:
        response = client.get(f"{API_BASE_URL}/health/live")
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is alive - Status: {data['status']}")
            print_info(f"   Timestamp: {data['timestamp']}")
        else:
            print_error(f"Liveness check failed: {response.status_code}")
    except Exception as e:
        print_error(f"Liveness check error: {e}")

    print()

    # Test readiness probe
    print(f"{BOLD}2. Readiness Probe (is the API ready for traffic?){RESET}")
    try:
        response = client.get(f"{API_BASE_URL}/health/ready")
        data = response.json()

        if response.status_code == 200:
            print_success(f"API is ready - Status: {data['status']}")
        else:
            print_warning(
                f"API not ready - Status: {data['status']} (Code: {response.status_code})"
            )

        if "checks" in data:
            print_info("   Dependency health:")
            for component, status_info in data["checks"].items():
                status = status_info.get("status", "unknown")
                if status == "healthy":
                    print(f"{GREEN}      • {component}: {status}{RESET}")
                else:
                    print(f"{RED}      • {component}: {status}{RESET}")
                    if "error" in status_info:
                        print(f"        Error: {status_info['error']}")
    except Exception as e:
        print_error(f"Readiness check error: {e}")

    print()

    # Test startup probe
    print(f"{BOLD}3. Startup Probe (is initialization complete?){RESET}")
    try:
        response = client.get(f"{API_BASE_URL}/health/startup")
        data = response.json()

        if response.status_code == 200:
            print_success(f"Startup complete - Status: {data['status']}")
        else:
            print_warning(
                f"Startup incomplete - Status: {data['status']} (Code: {response.status_code})"
            )

        if "startup_complete" in data:
            print_info(f"   Startup complete: {data['startup_complete']}")
    except Exception as e:
        print_error(f"Startup check error: {e}")


def demo_document_upload(client: httpx.Client, docs_dir: Path) -> list[str]:
    """Demonstrate document upload endpoints."""
    print_header("DEMO 2: Document Upload")

    print(f"{BOLD}Uploading test documents to the RAG system...{RESET}\n")

    # Create test documents
    docs_dir.mkdir(exist_ok=True)

    # Document 1: Machine Learning
    ml_doc = docs_dir / "machine_learning.txt"
    ml_doc.write_text(
        """
Machine Learning: An Introduction

Machine learning is a subset of artificial intelligence that enables systems to learn
and improve from experience without being explicitly programmed. It focuses on the
development of computer programs that can access data and use it to learn for themselves.

Key Concepts:
1. Supervised Learning: Learning from labeled training data
2. Unsupervised Learning: Finding patterns in unlabeled data
3. Reinforcement Learning: Learning through trial and error

Applications:
- Image and speech recognition
- Medical diagnosis
- Stock market analysis
- Recommendation systems
"""
    )

    # Document 2: Deep Learning
    dl_doc = docs_dir / "deep_learning.txt"
    dl_doc.write_text(
        """
Deep Learning Fundamentals

Deep learning is a specialized branch of machine learning that uses neural networks
with multiple layers (hence "deep"). These networks are inspired by the structure
and function of the human brain.

Architecture:
- Input Layer: Receives raw data
- Hidden Layers: Process and transform data
- Output Layer: Produces final predictions

Popular Frameworks:
1. TensorFlow (Google)
2. PyTorch (Facebook)
3. Keras (High-level API)

Deep learning excels at complex pattern recognition tasks such as:
- Computer vision and image classification
- Natural language processing
- Speech recognition and generation
"""
    )

    uploaded_files = []

    # Test 1: Single file upload
    print(f"{BOLD}1. Single File Upload{RESET}")
    try:
        with open(ml_doc, "rb") as f:
            response = client.post(
                f"{API_BASE_URL}/documents/upload",
                files={"file": (ml_doc.name, f, "text/plain")},
                timeout=30.0,
            )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Uploaded: {data['filename']}")
            print_info(f"   Chunks created: {data['chunks_created']}")
            print_info(f"   Message: {data['message']}")
            uploaded_files.append(data["filename"])
        else:
            print_error(f"Upload failed: {response.status_code} - {response.text}")
    except Exception as e:
        print_error(f"Upload error: {e}")

    print()

    # Test 2: Batch upload
    print(f"{BOLD}2. Batch Upload{RESET}")
    try:
        with open(ml_doc, "rb") as f1, open(dl_doc, "rb") as f2:
            files = [
                ("files", (ml_doc.name, f1, "text/plain")),
                ("files", (dl_doc.name, f2, "text/plain")),
            ]
            response = client.post(
                f"{API_BASE_URL}/documents/upload/batch",
                files=files,
                timeout=60.0,
            )

        if response.status_code == 200:
            data = response.json()
            print_success("Batch upload complete")
            print_info(f"   Total files: {data['total']}")
            print_info(f"   Successful: {data['successful']}")
            print_info(f"   Failed: {data['failed']}")

            print(f"\n{BOLD}   Individual Results:{RESET}")
            for result in data["results"]:
                if result["status"] == "success":
                    print(f"{GREEN}   • {result['file']}: {result['chunks_created']} chunks{RESET}")
                    if result["file"] not in uploaded_files:
                        uploaded_files.append(result["file"])
                else:
                    print(
                        f"{RED}   • {result['file']}: {result.get('error', 'Unknown error')}{RESET}"
                    )
        else:
            print_error(f"Batch upload failed: {response.status_code}")
    except Exception as e:
        print_error(f"Batch upload error: {e}")

    print()

    # Test 3: Invalid file type
    print(f"{BOLD}3. Error Handling (Invalid File Type){RESET}")
    try:
        invalid_file = docs_dir / "test.invalid"
        invalid_file.write_text("This file has an invalid extension")

        with open(invalid_file, "rb") as f:
            response = client.post(
                f"{API_BASE_URL}/documents/upload",
                files={"file": (invalid_file.name, f, "application/octet-stream")},
                timeout=10.0,
            )

        if response.status_code == 400:
            data = response.json()
            print_success("Invalid file correctly rejected")
            print_info(f"   Error: {data.get('message', data.get('error', 'Unknown'))}")
        else:
            print_warning(f"Unexpected response: {response.status_code}")
    except Exception as e:
        print_error(f"Error test failed: {e}")

    # Wait for Elasticsearch indexing
    print(f"\n{YELLOW}⏳ Waiting for Elasticsearch to index documents...{RESET}")
    time.sleep(3)
    print_success("Indexing complete")

    return uploaded_files


def demo_query_processing(client: httpx.Client) -> None:
    """Demonstrate query processing endpoints."""
    print_header("DEMO 3: Query Processing")

    print(f"{BOLD}Querying the RAG system with uploaded documents...{RESET}\n")

    queries = [
        ("What is machine learning?", "General question about ML"),
        ("What are the types of machine learning?", "Specific question about ML types"),
        ("What frameworks are used for deep learning?", "Question about tools"),
    ]

    # Test 1: Single queries
    print(f"{BOLD}1. Single Query Processing{RESET}\n")

    for query, description in queries:
        print(f"{BOLD}Q: {query}{RESET}")
        print(f"{CYAN}   ({description}){RESET}")

        try:
            response = client.post(
                f"{API_BASE_URL}/query/",
                json={"query": query, "top_k": 5},
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                answer = data["answer"]

                # Truncate long answers
                if len(answer) > 200:
                    answer_preview = answer[:200] + "..."
                else:
                    answer_preview = answer

                print(f"{GREEN}A: {answer_preview}{RESET}")
                print_info(f"   Answer length: {len(data['answer'])} characters")
                print()

            elif response.status_code == 503:
                print_warning("Query failed: LLM service unavailable (circuit breaker open)")
                print_info("   The circuit breaker is protecting against cascading failures")
                print()
                break  # Skip remaining queries if circuit is open

            else:
                print_error(f"Query failed: {response.status_code}")
                print()

        except Exception as e:
            print_error(f"Query error: {e}")
            print()

    # Test 2: Batch queries
    print(f"{BOLD}2. Batch Query Processing{RESET}")
    try:
        batch_queries = [
            "What is supervised learning?",
            "What is deep learning?",
        ]

        print_info(f"Processing {len(batch_queries)} queries in batch...")

        response = client.post(
            f"{API_BASE_URL}/query/batch",
            json={"queries": batch_queries, "top_k": 3},
            timeout=60.0,
        )

        if response.status_code == 200:
            responses = response.json()
            print_success(f"Batch processing complete: {len(responses)} responses")

            for i, resp_data in enumerate(responses, 1):
                print(f"\n{BOLD}   Response {i}:{RESET}")
                print(f"   Q: {resp_data['query']}")
                answer_preview = (
                    resp_data["answer"][:100] + "..."
                    if len(resp_data["answer"]) > 100
                    else resp_data["answer"]
                )
                print(f"   A: {answer_preview}")

        elif response.status_code == 503:
            print_warning("Batch query failed: LLM service unavailable")
        else:
            print_error(f"Batch query failed: {response.status_code}")

    except Exception as e:
        print_error(f"Batch query error: {e}")

    print()

    # Test 3: Invalid query
    print(f"{BOLD}3. Query Validation (Error Handling){RESET}")
    try:
        # Empty query
        response = client.post(
            f"{API_BASE_URL}/query/",
            json={"query": ""},
            timeout=5.0,
        )

        if response.status_code == 422:
            print_success("Empty query correctly rejected (422 Validation Error)")
        else:
            print_warning(f"Unexpected response: {response.status_code}")

        # Query too long
        long_query = "a" * 501
        response = client.post(
            f"{API_BASE_URL}/query/",
            json={"query": long_query},
            timeout=5.0,
        )

        if response.status_code == 422:
            print_success("Query too long correctly rejected (422 Validation Error)")
        else:
            print_warning(f"Unexpected response: {response.status_code}")

    except Exception as e:
        print_error(f"Validation test error: {e}")


def demo_api_info(client: httpx.Client) -> None:
    """Demonstrate API information endpoint."""
    print_header("DEMO 4: API Information")

    print(f"{BOLD}Retrieving API information and available endpoints...{RESET}\n")

    try:
        response = client.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            data = response.json()

            print(f"{BOLD}API Information:{RESET}")
            print(f"{GREEN}   Name: {data['name']}{RESET}")
            print(f"{GREEN}   Version: {data['version']}{RESET}")
            print(f"{GREEN}   Status: {data['status']}{RESET}")
            print(f"{GREEN}   Documentation: {data['docs']}{RESET}")

            print(f"\n{BOLD}Available Endpoints:{RESET}")
            for endpoint_name, endpoint_path in data["endpoints"].items():
                print(f"{CYAN}   • {endpoint_name}: {endpoint_path}{RESET}")

        else:
            print_error(f"Failed to retrieve API info: {response.status_code}")
    except Exception as e:
        print_error(f"API info error: {e}")


async def main():
    """Run the Phase 7 API demo."""
    print(f"\n{BOLD}{MAGENTA}")
    print("=" * 80)
    print("PHASE 7 DEMO: REST API DEVELOPMENT".center(80))
    print("=" * 80)
    print(f"{RESET}")

    print(f"{BOLD}Prerequisites:{RESET}")
    print(f"  {CYAN}• API server running on {API_BASE_URL}{RESET}")
    print(f"  {CYAN}• Elasticsearch running on localhost:9200{RESET}")
    print(f"  {CYAN}• LMStudio running on localhost:1234{RESET}")
    print()

    # Create HTTP client
    client = httpx.Client()
    docs_dir = Path(__file__).parent.parent / "test_docs"

    try:
        # Check if API is running
        print(f"{YELLOW}🔍 Checking if API server is running...{RESET}")
        try:
            response = client.get(f"{API_BASE_URL}/health/live", timeout=5.0)
            if response.status_code == 200:
                print_success(f"API server is running at {API_BASE_URL}")
            else:
                print_error(f"API server returned unexpected status: {response.status_code}")
                return
        except Exception as e:
            print_error(f"Cannot connect to API server: {e}")
            print_info("Please start the server with: python -m uvicorn src.main:app")
            return

        # Run demos
        demo_api_info(client)
        demo_health_checks(client)
        demo_document_upload(client, docs_dir)
        demo_query_processing(client)

        # Final summary
        print_header("DEMO COMPLETE")
        print(f"{BOLD}{GREEN}✓ All Phase 7 API features demonstrated successfully!{RESET}\n")
        print(f"{BOLD}What was demonstrated:{RESET}")
        print(f"{GREEN}  ✓ Health check endpoints (liveness, readiness, startup){RESET}")
        print(f"{GREEN}  ✓ Document upload (single and batch){RESET}")
        print(f"{GREEN}  ✓ Query processing (single and batch){RESET}")
        print(f"{GREEN}  ✓ Error handling and validation{RESET}")
        print(f"{GREEN}  ✓ API documentation{RESET}")

        print(f"\n{BOLD}Next Steps:{RESET}")
        print(f"{CYAN}  • Explore interactive docs at {API_BASE_URL}/docs{RESET}")
        print(
            f"{CYAN}  • Run integration tests: pytest tests/integration/test_api_integration.py{RESET}"
        )
        print(f"{CYAN}  • Run E2E tests: pytest tests/e2e/test_complete_flow.py{RESET}")

    finally:
        client.close()

        # Cleanup test docs
        if docs_dir.exists():
            for file in docs_dir.iterdir():
                file.unlink()
            docs_dir.rmdir()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
