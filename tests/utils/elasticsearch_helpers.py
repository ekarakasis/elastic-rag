"""
Test Helper Utilities for Elasticsearch State Verification

This module provides reusable helper functions for testing Elasticsearch integrations.
These utilities extract common testing patterns to reduce duplication and improve test reliability.

Functions:
    - wait_for_indexing: Poll until document is indexed to Elasticsearch
    - verify_document_indexed: Check if a specific document exists and is indexed
    - cleanup_test_documents: Remove test documents from Elasticsearch
    - get_document_by_filename: Retrieve document metadata by filename
    - count_indexed_documents: Get total document count from Elasticsearch

Usage in tests:
    from tests.utils.elasticsearch_helpers import wait_for_indexing, verify_document_indexed

    def test_my_feature(client):
        # Upload document
        response = client.post("/documents/upload", files={"file": my_file})

        # Use helper to verify indexing
        assert wait_for_indexing(client, my_file.name, timeout=5.0)

        # Verify document details
        doc_info = verify_document_indexed(client, my_file.name)
        assert doc_info is not None
        assert doc_info["chunks_count"] > 0
"""

import time
from typing import Any

from fastapi.testclient import TestClient


def wait_for_indexing(
    client: TestClient,
    filename: str,
    timeout: float = 5.0,
    retry_delay: float = 0.5,
) -> bool:
    """
    Poll for document indexing completion.

    Uses intelligent polling instead of fixed sleep times. Checks if a document
    with the given filename appears in Elasticsearch with chunks_count > 0.

    Args:
        client: FastAPI TestClient instance
        filename: Name of the file to wait for
        timeout: Maximum time to wait in seconds (default: 5.0)
        retry_delay: Delay between retries in seconds (default: 0.5)

    Returns:
        True if document is indexed within timeout, False otherwise

    Example:
        >>> assert wait_for_indexing(client, "test.txt", timeout=3.0)
    """
    max_retries = int(timeout / retry_delay)

    for _attempt in range(max_retries):
        try:
            response = client.get("/documents/")
            if response.status_code == 200:
                data = response.json()
                documents = data.get("documents", [])

                # Check if our document exists with chunks
                for doc in documents:
                    if doc.get("source_file") == filename:
                        chunks_count = doc.get("chunks_count", 0)
                        if chunks_count > 0:
                            return True

            # Not found yet, wait and retry
            time.sleep(retry_delay)
        except Exception:
            # Connection error or other issue, wait and retry
            time.sleep(retry_delay)
            continue

    return False


def verify_document_indexed(
    client: TestClient,
    filename: str,
) -> dict[str, Any] | None:
    """
    Verify that a document is indexed to Elasticsearch and return its metadata.

    Checks if the document exists in the /documents/ list and has been indexed
    (chunks_count > 0).

    Args:
        client: FastAPI TestClient instance
        filename: Name of the file to verify

    Returns:
        Document metadata dict if found and indexed, None otherwise

    Example:
        >>> doc = verify_document_indexed(client, "test.txt")
        >>> assert doc is not None
        >>> assert doc["chunks_count"] > 0
    """
    try:
        response = client.get("/documents/")
        if response.status_code != 200:
            return None

        data = response.json()
        documents = data.get("documents", [])

        for doc in documents:
            if doc.get("source_file") == filename:
                # Verify it has been indexed
                if doc.get("chunks_count", 0) > 0:
                    return doc
                return None

        return None
    except Exception:
        return None


def get_document_by_filename(
    client: TestClient,
    filename: str,
) -> dict[str, Any] | None:
    """
    Retrieve document metadata by filename.

    Unlike verify_document_indexed, this returns the document even if
    chunks_count is 0, useful for checking upload status.

    Args:
        client: FastAPI TestClient instance
        filename: Name of the file to find

    Returns:
        Document metadata dict if found, None otherwise

    Example:
        >>> doc = get_document_by_filename(client, "test.txt")
        >>> if doc:
        >>>     print(f"Found with {doc['chunks_count']} chunks")
    """
    try:
        response = client.get("/documents/")
        if response.status_code != 200:
            return None

        data = response.json()
        documents = data.get("documents", [])

        for doc in documents:
            if doc.get("source_file") == filename:
                return doc

        return None
    except Exception:
        return None


def count_indexed_documents(client: TestClient) -> int:
    """
    Get the total count of indexed documents in Elasticsearch.

    Args:
        client: FastAPI TestClient instance

    Returns:
        Number of documents in Elasticsearch, or -1 on error

    Example:
        >>> initial_count = count_indexed_documents(client)
        >>> # ... upload document ...
        >>> final_count = count_indexed_documents(client)
        >>> assert final_count > initial_count
    """
    try:
        response = client.get("/documents/")
        if response.status_code != 200:
            return -1

        data = response.json()
        documents = data.get("documents", [])
        return len(documents)
    except Exception:
        return -1


def cleanup_test_documents(
    client: TestClient,
    filenames: list[str],
) -> dict[str, bool]:
    """
    Attempt to clean up test documents from Elasticsearch.

    Tries to delete documents by finding their document IDs and calling
    DELETE /documents/{id}. Best effort - doesn't fail if cleanup fails.

    Args:
        client: FastAPI TestClient instance
        filenames: List of filenames to clean up

    Returns:
        Dict mapping filename -> success (True if deleted, False otherwise)

    Example:
        >>> cleanup = cleanup_test_documents(client, ["test1.txt", "test2.txt"])
        >>> # Don't assert on cleanup results - it's best effort
    """
    results = {}

    for filename in filenames:
        try:
            # Find the document
            doc = get_document_by_filename(client, filename)
            if doc is None:
                results[filename] = False
                continue

            # Get document ID
            doc_id = doc.get("document_id")
            if doc_id is None:
                results[filename] = False
                continue

            # Try to delete
            response = client.delete(f"/documents/{doc_id}")
            results[filename] = response.status_code in (200, 204)
        except Exception:
            results[filename] = False

    return results


def wait_for_document_deletion(
    client: TestClient,
    filename: str,
    timeout: float = 5.0,
    retry_delay: float = 0.5,
) -> bool:
    """
    Poll until document is deleted from Elasticsearch.

    Waits for the document to disappear from the /documents/ list.

    Args:
        client: FastAPI TestClient instance
        filename: Name of the file to wait for deletion
        timeout: Maximum time to wait in seconds (default: 5.0)
        retry_delay: Delay between retries in seconds (default: 0.5)

    Returns:
        True if document is deleted within timeout, False otherwise

    Example:
        >>> client.delete(f"/documents/{doc_id}")
        >>> assert wait_for_document_deletion(client, "test.txt")
    """
    max_retries = int(timeout / retry_delay)

    for _attempt in range(max_retries):
        doc = get_document_by_filename(client, filename)
        if doc is None:
            return True

        time.sleep(retry_delay)

    return False


def get_chunks_for_document(
    client: TestClient,
    filename: str,
) -> list[dict[str, Any]]:
    """
    Get all chunks for a specific document.

    Note: This requires querying Elasticsearch directly as the API doesn't
    expose a chunks endpoint. Returns empty list if not accessible.

    Args:
        client: FastAPI TestClient instance
        filename: Name of the file to get chunks for

    Returns:
        List of chunk dictionaries (may be empty)

    Example:
        >>> chunks = get_chunks_for_document(client, "test.txt")
        >>> assert len(chunks) > 0
    """
    # This is a placeholder - would need direct ES access
    # For now, we can infer chunk count from document metadata
    doc = get_document_by_filename(client, filename)
    if doc is None:
        return []

    # Can't get actual chunks without direct ES access
    # Return empty list - tests should use chunks_count instead
    return []
