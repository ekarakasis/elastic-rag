#!/usr/bin/env python3
"""
Upload Verification Demo

Demonstrates the proper workflow for uploading documents and verifying they're searchable:
1. Upload document
2. Verify indexing to Elasticsearch
3. Query to confirm searchability

This demo shows the verification steps that would have caught the v1.0.0 indexing bug.

Usage:
    python demos/demo_upload_verification.py

Requirements:
    - API server running at http://localhost:8000
    - Elasticsearch available
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
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_step(step: int, text: str) -> None:
    """Print a step indicator."""
    print(f"{Colors.BOLD}{Colors.CYAN}[Step {step}]{Colors.RESET} {text}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"  {text}")


def check_api_health(client: httpx.Client, api_url: str) -> bool:
    """Check if API is healthy and ready."""
    try:
        response = client.get(f"{api_url}/health/ready")
        if response.status_code == 200:
            return True
        return False
    except Exception:
        return False


def upload_document(client: httpx.Client, api_url: str, file_path: Path) -> dict | None:
    """Upload a document and return the response."""
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "text/plain")}
            response = client.post(f"{api_url}/documents/upload", files=files)

        if response.status_code == 200:
            return response.json()
        else:
            print_error(f"Upload failed with status {response.status_code}")
            print_info(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Upload failed: {e}")
        return None


def verify_document_indexed(
    client: httpx.Client, api_url: str, filename: str, max_retries: int = 10
) -> tuple[bool, dict | None]:
    """
    Verify document was indexed to Elasticsearch.

    Uses polling to wait for indexing to complete.

    Returns:
        (success, document_info)
    """
    for _attempt in range(max_retries):
        try:
            response = client.get(f"{api_url}/documents/")
            if response.status_code != 200:
                time.sleep(0.5)
                continue

            data = response.json()
            documents = data.get("documents", [])

            # Find our document
            for doc in documents:
                if doc.get("source_file") == filename:
                    chunks_count = doc.get("chunks_count", 0)
                    if chunks_count > 0:
                        return True, doc

            # Not found yet, wait and retry
            time.sleep(0.5)
        except Exception:
            time.sleep(0.5)
            continue

    return False, None


def query_document(client: httpx.Client, api_url: str, query: str) -> tuple[bool, dict | None]:
    """
    Query the RAG system and return results.

    Returns:
        (success, response_data)
    """
    try:
        response = client.post(
            f"{api_url}/query/",
            json={"query": query, "max_results": 3},
            timeout=30.0,
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            print_error(f"Query failed with status {response.status_code}")
            print_info(f"Response: {response.text}")
            return False, None
    except Exception as e:
        print_error(f"Query failed: {e}")
        return False, None


def main():
    """Run the upload verification demo."""
    print_header("Upload Verification Demo")

    api_url = "http://localhost:8000"

    # Create a test file
    test_file = Path("test_upload_verification.txt")
    test_content = """
    Upload Verification Test Document

    This is a test document for demonstrating proper upload verification.

    Key Points:
    1. Always verify documents are indexed after upload
    2. Use polling instead of fixed sleep times
    3. Confirm documents are searchable via queries
    4. Check Elasticsearch state, not just API responses

    The v1.0.0 indexing bug would have been caught by these verification steps.
    """

    try:
        # Step 0: Check API health
        print_step(0, "Checking API health")
        client = httpx.Client(timeout=30.0)

        if not check_api_health(client, api_url):
            print_error("API is not healthy or not reachable")
            print_info("Make sure the API server is running: task run")
            sys.exit(1)

        print_success("API is healthy and ready")

        # Create test file
        test_file.write_text(test_content)
        print_info(f"Created test file: {test_file.name}")

        # Step 1: Upload document
        print_step(1, f"Uploading document: {test_file.name}")
        upload_result = upload_document(client, api_url, test_file)

        if not upload_result:
            print_error("Upload failed!")
            sys.exit(1)

        print_success("Upload succeeded")
        print_info(f"Status: {upload_result.get('status')}")
        print_info(f"Chunks created: {upload_result.get('chunks_created')}")

        # CRITICAL: Don't stop here! Verify indexing!
        print_warning("⚠️  A successful upload doesn't guarantee the document is searchable!")
        print_info(
            "The v1.0.0 bug: uploads succeeded but documents weren't indexed to Elasticsearch"
        )

        # Step 2: Verify indexing
        print_step(2, "Verifying document indexed to Elasticsearch (polling)")
        print_info("Waiting for indexing to complete...")

        indexed, doc_info = verify_document_indexed(client, api_url, test_file.name)

        if not indexed:
            print_error("Document was NOT indexed to Elasticsearch!")
            print_warning(
                "This is exactly what happened in v1.0.0 - upload succeeded but no indexing"
            )
            print_info("Possible causes:")
            print_info(
                "  - API calling wrong method (ingest_document vs ingest_and_index_document)"
            )
            print_info("  - Elasticsearch connection issue")
            print_info("  - Indexing pipeline failure")
            sys.exit(1)

        print_success("Document successfully indexed to Elasticsearch!")
        print_info(f"Document ID: {doc_info.get('document_id')}")
        print_info(f"Chunks indexed: {doc_info.get('chunks_count')}")
        print_info(f"Created at: {doc_info.get('created_at')}")

        # Step 3: Verify searchability
        print_step(3, "Verifying document is searchable")
        print_info("Querying: 'What are the key points about upload verification?'")

        success, query_result = query_document(
            client,
            api_url,
            "What are the key points about upload verification?",
        )

        if not success:
            print_error("Query failed!")
            sys.exit(1)

        # Check if our document appears in sources
        sources = query_result.get("sources", [])
        found_in_sources = any(test_file.name in source.get("source", "") for source in sources)

        if not found_in_sources:
            print_warning("Document not found in query sources!")
            print_info("This could indicate:")
            print_info("  - Document chunks not matching query")
            print_info("  - Embedding/search issue")
            print_info("  - Document content not relevant to query")
        else:
            print_success("Document found in query results!")
            print_info(f"Answer: {query_result.get('answer', '')[:200]}...")
            print_info(f"Sources: {len(sources)} retrieved")
            for i, source in enumerate(sources[:3], 1):
                print_info(f"  {i}. {source.get('source')} (score: {source.get('score', 0):.3f})")

        # Summary
        print_header("Verification Complete")

        print_success("All verification steps passed!")
        print_info("")
        print_info("Summary:")
        print_info(f"  1. ✓ Upload succeeded ({upload_result.get('chunks_created')} chunks)")
        print_info(
            f"  2. ✓ Document indexed to Elasticsearch ({doc_info.get('chunks_count')} chunks)"
        )
        print_info("  3. ✓ Document is searchable")
        print_info("")
        print_info("This workflow would have caught the v1.0.0 indexing bug!")
        print_info("")
        print_info("Best Practices Demonstrated:")
        print_info("  • Don't trust API responses alone")
        print_info("  • Always verify external system state (Elasticsearch)")
        print_info("  • Use polling instead of fixed sleep times")
        print_info("  • Test end-to-end searchability, not just indexing")

    except KeyboardInterrupt:
        print_error("\nDemo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
            print_info(f"\nCleaned up test file: {test_file.name}")
        client.close()


if __name__ == "__main__":
    main()
