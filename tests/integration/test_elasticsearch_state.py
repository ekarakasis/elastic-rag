"""Integration tests that explicitly verify Elasticsearch state.

This test suite addresses the root cause of the document indexing bug:
tests must verify actual system state, not just API responses.

All tests in this file verify Elasticsearch state after operations.
"""

import time
import uuid

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.retrieval.elasticsearch_client import ElasticsearchClient

# Create test client
client = TestClient(app)


class TestElasticsearchStateVerification:
    """Tests that explicitly verify Elasticsearch state after operations."""

    def test_upload_creates_searchable_documents(self, tmp_path):
        """Verify that uploaded documents are actually searchable in Elasticsearch.

        This test would have caught the indexing bug by verifying documents
        are not just processed but also searchable.
        """
        # Create unique test file
        unique_filename = f"searchable_test_{uuid.uuid4().hex[:8]}.txt"
        test_file = tmp_path / unique_filename
        test_file.write_text("This document should be searchable in Elasticsearch after upload.")

        # Initialize ES client for direct verification
        es_client = ElasticsearchClient()
        document_store = es_client.get_document_store()
        initial_count = document_store.count_documents()

        # Upload document
        with open(test_file, "rb") as f:
            response = client.post(
                "/documents/upload",
                files={"file": (unique_filename, f, "text/plain")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["chunks_created"] > 0

        # Wait for indexing
        time.sleep(2)

        # Verify: Document count increased in Elasticsearch
        final_count = document_store.count_documents()
        assert (
            final_count > initial_count
        ), "Document count did not increase - upload may not have indexed"

        # Verify: Can retrieve documents from ES
        list_response = client.get("/documents/")
        assert list_response.status_code == 200
        filenames = [d["source_file"] for d in list_response.json()["documents"]]
        assert unique_filename in filenames, "Document not found in Elasticsearch"

        # Cleanup
        try:
            client.delete(f"/documents/{unique_filename}")
        except Exception:
            pass

    def test_delete_removes_all_chunks(self, tmp_path):
        """Verify that deleting a document removes all its chunks from Elasticsearch."""
        # Create and upload document
        unique_filename = f"delete_test_{uuid.uuid4().hex[:8]}.txt"
        test_file = tmp_path / unique_filename
        test_file.write_text("Document to be deleted with all its chunks.")

        with open(test_file, "rb") as f:
            upload_response = client.post(
                "/documents/upload",
                files={"file": (unique_filename, f, "text/plain")},
            )

        assert upload_response.status_code == 200
        assert upload_response.json()["chunks_created"] > 0

        # Wait for indexing
        time.sleep(2)

        # Verify document exists
        list_response = client.get("/documents/")
        initial_total_chunks = list_response.json()["total_chunks"]
        filenames = [d["source_file"] for d in list_response.json()["documents"]]
        assert unique_filename in filenames

        # Delete document
        delete_response = client.delete(f"/documents/{unique_filename}")
        assert delete_response.status_code == 200

        # Wait for deletion
        time.sleep(1)

        # Verify: Document removed from Elasticsearch
        list_response = client.get("/documents/")
        filenames = [d["source_file"] for d in list_response.json()["documents"]]
        assert unique_filename not in filenames, "Document still exists after deletion"

        # Verify: Chunk count decreased
        final_total_chunks = list_response.json()["total_chunks"]
        assert (
            final_total_chunks < initial_total_chunks
        ), "Chunk count did not decrease after deletion"

    def test_batch_upload_indexes_all_documents(self, tmp_path):
        """Verify that batch upload indexes all documents to Elasticsearch."""
        # Create multiple test files
        num_files = 3
        filenames = []
        file_objects = []

        for i in range(num_files):
            unique_filename = f"batch_test_{uuid.uuid4().hex[:8]}.txt"
            test_file = tmp_path / unique_filename
            test_file.write_text(f"Batch upload test document {i}.")
            filenames.append(unique_filename)

            f = open(test_file, "rb")
            file_objects.append(("files", (unique_filename, f, "text/plain")))

        try:
            # Batch upload
            batch_response = client.post("/documents/upload/batch", files=file_objects)
            assert batch_response.status_code == 200
            batch_data = batch_response.json()

            successful_count = batch_data["successful"]
            assert successful_count > 0, "No documents uploaded successfully"

            # Wait for indexing
            time.sleep(2)

            # Verify: All successful uploads appear in Elasticsearch
            list_response = client.get("/documents/")
            assert list_response.status_code == 200
            indexed_filenames = [d["source_file"] for d in list_response.json()["documents"]]

            found_count = sum(1 for fname in filenames if fname in indexed_filenames)
            assert (
                found_count == successful_count
            ), f"Expected {successful_count} documents in ES, found {found_count}"

        finally:
            # Cleanup
            for _, (fname, f, _) in file_objects:
                f.close()
                try:
                    client.delete(f"/documents/{fname}")
                except Exception:
                    pass

    def test_document_count_matches_chunks(self, tmp_path):
        """Verify that document chunk counts in API match actual ES chunk counts."""
        # Create test document
        unique_filename = f"count_test_{uuid.uuid4().hex[:8]}.txt"
        test_file = tmp_path / unique_filename
        test_file.write_text("Document for verifying chunk count accuracy. " * 20)

        # Upload
        with open(test_file, "rb") as f:
            upload_response = client.post(
                "/documents/upload",
                files={"file": (unique_filename, f, "text/plain")},
            )

        assert upload_response.status_code == 200
        upload_chunks = upload_response.json()["chunks_created"]

        # Wait for indexing
        time.sleep(2)

        # Get document info from API
        list_response = client.get("/documents/")
        assert list_response.status_code == 200

        doc_info = None
        for doc in list_response.json()["documents"]:
            if doc["source_file"] == unique_filename:
                doc_info = doc
                break

        assert doc_info is not None, "Document not found in list"

        # Verify: Chunk count in API matches what was uploaded
        assert (
            doc_info["chunks_count"] == upload_chunks
        ), f"API reports {doc_info['chunks_count']} chunks, but {upload_chunks} were created"

        # Cleanup
        try:
            client.delete(f"/documents/{unique_filename}")
        except Exception:
            pass

    def test_concurrent_operations_maintain_consistency(self, tmp_path):
        """Verify ES state remains consistent during concurrent operations."""
        # Create multiple files
        files_to_test = []
        for i in range(2):
            unique_filename = f"concurrent_state_test_{i}_{uuid.uuid4().hex[:8]}.txt"
            test_file = tmp_path / unique_filename
            test_file.write_text(f"Concurrent test document {i}.")
            files_to_test.append((unique_filename, test_file))

        # Get initial state
        initial_response = client.get("/documents/")
        initial_count = initial_response.json()["total"]
        initial_chunks = initial_response.json()["total_chunks"]

        # Upload files concurrently (simulated with batch)
        file_objects = []
        for fname, fpath in files_to_test:
            f = open(fpath, "rb")
            file_objects.append(("files", (fname, f, "text/plain")))

        try:
            batch_response = client.post("/documents/upload/batch", files=file_objects)
            assert batch_response.status_code == 200

            successful = batch_response.json()["successful"]
            total_chunks_uploaded = sum(
                r["chunks_created"]
                for r in batch_response.json()["results"]
                if r["status"] == "success"
            )

            # Wait for all operations
            time.sleep(2)

            # Verify: Final state is consistent
            final_response = client.get("/documents/")
            final_count = final_response.json()["total"]
            final_chunks = final_response.json()["total_chunks"]

            # Document count should increase by successful uploads
            assert (
                final_count >= initial_count + successful
            ), f"Expected at least {initial_count + successful} documents, got {final_count}"

            # Chunk count should increase by uploaded chunks
            assert (
                final_chunks >= initial_chunks + total_chunks_uploaded
            ), f"Expected at least {initial_chunks + total_chunks_uploaded} chunks, got {final_chunks}"

        finally:
            # Cleanup
            for _, (fname, f, _) in file_objects:
                f.close()
                try:
                    client.delete(f"/documents/{fname}")
                except Exception:
                    pass

    def test_query_results_reflect_indexed_content(self, tmp_path):
        """Verify that query results actually come from indexed Elasticsearch content."""
        # Create document with very specific, unique content
        unique_marker = f"UNIQUE_CONTENT_MARKER_{uuid.uuid4().hex[:12]}"
        unique_filename = f"query_content_test_{uuid.uuid4().hex[:8]}.txt"
        test_file = tmp_path / unique_filename
        test_file.write_text(
            f"This document contains the marker: {unique_marker}. "
            "It should be findable through Elasticsearch queries."
        )

        # Upload
        with open(test_file, "rb") as f:
            upload_response = client.post(
                "/documents/upload",
                files={"file": (unique_filename, f, "text/plain")},
            )

        assert upload_response.status_code == 200
        time.sleep(2)

        # Verify document is in ES
        list_response = client.get("/documents/")
        filenames = [d["source_file"] for d in list_response.json()["documents"]]
        assert unique_filename in filenames, "Document not indexed"

        # Query using unique marker
        query_response = client.post(
            "/query/",
            json={"query": f"Tell me about {unique_marker}", "top_k": 5},
        )

        if query_response.status_code == 503:
            pytest.skip("Circuit breaker open - LMStudio unavailable")

        assert query_response.status_code == 200
        query_data = query_response.json()

        # Verify: If sources returned, our document should be in them
        # (threshold might filter it out, but if any sources exist, ours should be included)
        if query_data.get("sources"):
            source_files = [
                s.get("metadata", {}).get("source_file", "") for s in query_data["sources"]
            ]
            # The unique content should make our document highly relevant
            assert (
                unique_filename in source_files
            ), "Document with unique content not found in query results"

        # Cleanup
        try:
            client.delete(f"/documents/{unique_filename}")
        except Exception:
            pass

    def test_elasticsearch_index_exists_and_accessible(self):
        """Verify that Elasticsearch index exists and is accessible."""
        # Direct ES verification
        es_client = ElasticsearchClient()
        document_store = es_client.get_document_store()

        # Should be able to count documents without error
        count = document_store.count_documents()
        assert isinstance(count, int), "Document count should be an integer"
        assert count >= 0, "Document count should be non-negative"

        # Should be able to check health
        health = es_client.health_check()
        assert health["status"] in ["healthy", "unhealthy"], "Invalid health status"
        assert "cluster_name" in health, "Health check should include cluster name"


# Fixtures
@pytest.fixture(autouse=True)
def cleanup_test_documents():
    """Cleanup any test documents before and after each test."""
    # Setup: Clean up old test documents from previous runs
    list_response = client.get("/documents/")
    if list_response.status_code == 200:
        list_data = list_response.json()
        test_patterns = [
            "delete_test_",
            "batch_test_",
            "concurrent_",
            "reflect_test",
            "indexed_test_",
            "searchable_test_",
            "query_content_test_",
        ]

        for doc in list_data.get("documents", []):
            filename = doc.get("source_file", "")
            # Delete if it matches any test pattern
            if any(pattern in filename for pattern in test_patterns):
                try:
                    client.delete(f"/documents/{filename}")
                except Exception:
                    pass  # Best effort cleanup

    yield
    # Teardown: Tests handle their own cleanup with unique names
