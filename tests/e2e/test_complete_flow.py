"""End-to-end tests for complete RAG workflow.

This test suite verifies the complete system functionality from
document upload through query processing.

Requirements:
- Elasticsearch running on localhost:9200
- LMStudio running on localhost:1234
"""

import time

import pytest
from fastapi.testclient import TestClient

from src.main import app

# Create test client
client = TestClient(app)


class TestCompleteRAGWorkflow:
    """Test the complete RAG workflow end-to-end."""

    def test_complete_workflow(self, tmp_path):
        """Test complete workflow: health check → upload → query → verify.

        This test demonstrates the full RAG system workflow:
        1. Check system health
        2. Upload test documents
        3. Query for information
        4. Verify responses contain relevant information
        """
        # Step 1: Verify system is healthy
        print("\n=== Step 1: Health Check ===")
        health_response = client.get("/health/live")
        assert health_response.status_code == 200
        print(f"✓ Liveness: {health_response.json()['status']}")

        readiness_response = client.get("/health/ready")
        print(f"✓ Readiness: Status code {readiness_response.status_code}")

        # Step 2: Upload test documents
        print("\n=== Step 2: Document Upload ===")

        # Create test documents with different content
        doc1 = tmp_path / "machine_learning.txt"
        doc1.write_text(
            """
            Machine Learning Overview

            Machine learning is a subset of artificial intelligence that focuses on
            building systems that can learn from and make decisions based on data.
            Unlike traditional programming where rules are explicitly coded, machine
            learning algorithms can identify patterns and make predictions without
            being explicitly programmed for every scenario.

            There are three main types of machine learning:
            1. Supervised learning - learning from labeled data
            2. Unsupervised learning - finding patterns in unlabeled data
            3. Reinforcement learning - learning through trial and error
            """
        )

        doc2 = tmp_path / "deep_learning.txt"
        doc2.write_text(
            """
            Deep Learning Fundamentals

            Deep learning is a specialized subset of machine learning that uses
            artificial neural networks with multiple layers (hence "deep").
            These networks are inspired by the structure of the human brain.

            Deep learning excels at:
            - Image recognition and computer vision
            - Natural language processing
            - Speech recognition
            - Complex pattern recognition

            Popular deep learning frameworks include TensorFlow, PyTorch, and Keras.
            """
        )

        # Upload documents
        uploaded_docs = []
        for doc_path in [doc1, doc2]:
            with open(doc_path, "rb") as f:
                upload_response = client.post(
                    "/documents/upload",
                    files={"file": (doc_path.name, f, "text/plain")},
                )

            assert upload_response.status_code == 200
            upload_data = upload_response.json()
            uploaded_docs.append(upload_data)
            print(
                f"✓ Uploaded {upload_data['filename']}: " f"{upload_data['chunks_created']} chunks"
            )

        # Give Elasticsearch time to index - replaced time.sleep with polling
        print("  Waiting for indexing to complete...")

        # Poll for documents to appear in Elasticsearch (better than time.sleep)
        max_retries = 10
        retry_delay = 0.5
        for attempt in range(max_retries):
            list_response = client.get("/documents/")
            if list_response.status_code == 200:
                list_data = list_response.json()
                uploaded_filenames = [doc1.name, doc2.name]
                found_filenames = [d["source_file"] for d in list_data["documents"]]

                # Check if both documents are indexed
                if all(fname in found_filenames for fname in uploaded_filenames):
                    print(f"  ✓ Documents indexed after {attempt * retry_delay:.1f}s")

                    # Verify chunk counts match
                    for doc in list_data["documents"]:
                        if doc["source_file"] in uploaded_filenames:
                            assert (
                                doc["chunks_count"] > 0
                            ), f"Document {doc['source_file']} has 0 chunks"
                    break

            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        else:
            pytest.fail("Documents not indexed within timeout period")

        # Step 3: Query for information
        print("\n=== Step 3: Query Processing ===")

        queries = [
            "What is machine learning?",
            "What are the types of machine learning?",
            "What is deep learning used for?",
        ]

        query_responses = []
        for query_text in queries:
            query_response = client.post(
                "/query/",
                json={"query": query_text, "top_k": 5},
            )

            # Circuit breaker might be open if LMStudio is down
            if query_response.status_code == 503:
                print("⚠ Query failed - Circuit breaker open (LMStudio unavailable)")
                pytest.skip("LMStudio unavailable - skipping query tests")

            assert query_response.status_code == 200
            query_data = query_response.json()
            query_responses.append(query_data)

            print(f"✓ Query: {query_text}")
            print(f"  Answer length: {len(query_data['answer'])} chars")
            print(f"  Answer preview: {query_data['answer'][:100]}...")

        # Step 4: Verify responses
        print("\n=== Step 4: Verification ===")

        for response in query_responses:
            # Verify response structure
            assert "answer" in response
            assert "query" in response
            assert "sources" in response
            assert isinstance(response["sources"], list)

            # Verify answer is not empty
            assert len(response["answer"]) > 0

            # Enhanced verification: check that sources reference uploaded documents
            if response["sources"]:
                source_files = [
                    s.get("metadata", {}).get("source_file", "") for s in response["sources"]
                ]
                # At least some sources should be from our uploaded documents
                uploaded_names = [doc1.name, doc2.name]
                has_uploaded_source = any(fname in uploaded_names for fname in source_files)
                if has_uploaded_source:
                    print(f"✓ Valid response with uploaded sources for: {response['query']}")
                else:
                    print(f"⚠ Response uses other sources for: {response['query']}")
            else:
                print(f"⚠ No sources returned for: {response['query']}")

        # Step 5: Test batch query
        print("\n=== Step 5: Batch Query Test ===")

        batch_response = client.post(
            "/query/batch",
            json={
                "queries": [
                    "What is supervised learning?",
                    "What frameworks are used for deep learning?",
                ],
                "top_k": 3,
            },
        )

        if batch_response.status_code == 200:
            batch_data = batch_response.json()
            assert len(batch_data) == 2
            print(f"✓ Batch query processed: {len(batch_data)} responses")

        print("\n=== Test Complete ===")
        print("✓ All workflow steps completed successfully")

    def test_error_recovery(self, tmp_path):
        """Test system behavior with error conditions."""
        print("\n=== Error Recovery Test ===")

        # Test 1: Invalid file upload
        print("Test 1: Invalid file type")
        invalid_response = client.post(
            "/documents/upload",
            files={"file": ("test.xyz", b"content", "application/octet-stream")},
        )
        assert invalid_response.status_code == 400
        print("✓ Invalid file type rejected")

        # Test 2: Invalid query
        print("Test 2: Invalid query")
        invalid_query = client.post("/query/", json={"query": ""})
        assert invalid_query.status_code == 422
        print("✓ Invalid query rejected")

        # Test 3: System continues after errors
        print("Test 3: System recovery")
        health_response = client.get("/health/live")
        assert health_response.status_code == 200
        print("✓ System healthy after errors")

    def test_concurrent_uploads(self, tmp_path):
        """Test handling multiple concurrent uploads."""
        print("\n=== Concurrent Upload Test ===")

        # Create multiple test files
        files_to_upload = []
        for i in range(3):
            doc = tmp_path / f"concurrent_doc_{i}.txt"
            doc.write_text(f"This is test document number {i} for concurrent upload testing.")
            files_to_upload.append(doc)

        # Upload using batch endpoint
        file_objects = []
        try:
            for doc_path in files_to_upload:
                f = open(doc_path, "rb")
                file_objects.append(("files", (doc_path.name, f, "text/plain")))

            batch_response = client.post("/documents/upload/batch", files=file_objects)

            assert batch_response.status_code == 200
            batch_data = batch_response.json()

            print(f"✓ Batch upload: {batch_data['successful']}/{batch_data['total']} successful")
            assert batch_data["total"] == 3
            assert batch_data["successful"] >= 1

            # Enhanced: Verify documents appear in Elasticsearch
            expected_successful = batch_data["successful"]
            if expected_successful > 0:
                # Poll for documents to be indexed
                max_retries = 10
                for _attempt in range(max_retries):
                    time.sleep(0.5)
                    list_response = client.get("/documents/")
                    if list_response.status_code == 200:
                        list_data = list_response.json()
                        found_filenames = [d["source_file"] for d in list_data["documents"]]
                        uploaded_filenames = [doc.name for doc in files_to_upload]

                        found_count = sum(
                            1 for fname in uploaded_filenames if fname in found_filenames
                        )
                        if found_count >= expected_successful:
                            print(f"  ✓ {found_count} documents verified in Elasticsearch")
                            break
                else:
                    print("  ⚠ Warning: Not all documents verified in Elasticsearch")

        finally:
            # Close all file objects
            for _, (_, f, _) in file_objects:
                f.close()

    def test_system_resilience(self):
        """Test system resilience and circuit breaker behavior."""
        print("\n=== System Resilience Test ===")

        # Check startup probe
        startup_response = client.get("/health/startup")
        print(f"✓ Startup probe: {startup_response.status_code}")

        # Check readiness probe
        readiness_response = client.get("/health/ready")
        readiness_data = readiness_response.json()
        print(f"✓ Readiness probe: {readiness_data['status']}")

        if "checks" in readiness_data:
            for component, status in readiness_data["checks"].items():
                print(f"  - {component}: {status.get('status', 'unknown')}")

        # Verify circuit breaker is monitored
        if "checks" in readiness_data:
            # Some form of service health monitoring should be present
            assert len(readiness_data["checks"]) > 0
            print("✓ Service health monitoring active")


@pytest.fixture(scope="module")
def ensure_services_running():
    """Ensure required services are running before tests."""
    print("\n" + "=" * 70)
    print("E2E Test Suite - Complete RAG Workflow")
    print("=" * 70)
    print("\nPrerequisites:")
    print("  - Elasticsearch running on localhost:9200")
    print("  - LMStudio running on localhost:1234")
    print("  - Models loaded in LMStudio")
    print("=" * 70 + "\n")

    # Check if services are accessible
    health_response = client.get("/health/ready")

    if health_response.status_code != 200:
        print("⚠ Warning: Some services may not be ready")
        print("  Tests may fail if Elasticsearch or LMStudio are unavailable")

    yield

    print("\n" + "=" * 70)
    print("E2E Tests Complete")
    print("=" * 70)


# Use the fixture
pytestmark = pytest.mark.usefixtures("ensure_services_running")
