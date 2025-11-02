"""HTTP client for communicating with Elastic RAG FastAPI backend."""

import logging
import time
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class ElasticRAGClient:
    """Client for interacting with the Elastic RAG API.

    This client provides methods for:
    - Document upload and management
    - Query/chat operations
    - Health checks

    Features:
    - Automatic retry with exponential backoff (3 attempts)
    - Configurable timeouts
    - Connection resilience
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        upload_timeout: float = 120.0,
        query_timeout: float = 60.0,
    ):
        """Initialize the API client.

        Args:
            api_url: Base URL of the FastAPI backend
            upload_timeout: Timeout for upload requests in seconds (default: 120s)
            query_timeout: Timeout for query requests in seconds (default: 60s)
        """
        self.api_url = api_url.rstrip("/")
        self.upload_timeout = upload_timeout
        self.query_timeout = query_timeout
        logger.info(f"Initialized ElasticRAGClient for {self.api_url}")

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def health_check(self) -> dict[str, Any]:
        """Check if the API is healthy and responsive.

        Returns:
            Dictionary with health status information

        Raises:
            httpx.HTTPError: If health check fails
        """
        try:
            response = httpx.get(f"{self.api_url}/health/live", timeout=5.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def upload_document(
        self, file_path: str | Path, original_filename: str | None = None
    ) -> dict[str, Any]:
        """Upload a document using the async endpoint.

        Note: This method uses the async upload endpoint which returns immediately
        while document processing happens in the background. This prevents long
        uploads (e.g., PDFs with OCR taking 1-2 minutes) from blocking the API.

        Args:
            file_path: Path to the document file (may be temporary)
            original_filename: Original filename to use (if file_path is temporary).
                             If not provided, uses file_path.name

        Returns:
            Dictionary with:
                - status: "processing" (indicates background processing)
                - filename: Name of uploaded file
                - document_id: Document identifier
                - chunks_created: 0 (processing not complete yet)
                - message: Status message with task_id

        Raises:
            FileNotFoundError: If file doesn't exist
            httpx.HTTPError: If upload fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Use original filename if provided, otherwise use file path name
        upload_filename = original_filename or file_path.name

        logger.info(f"Uploading document: {upload_filename} (from {file_path.name})")
        try:
            with open(file_path, "rb") as f:
                files = {"file": (upload_filename, f, "application/octet-stream")}
                # Use async endpoint to avoid blocking the API during document processing
                response = httpx.post(
                    f"{self.api_url}/documents/upload/async",
                    files=files,
                    timeout=30.0,  # Short timeout since async returns immediately
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Upload queued: {upload_filename} -> {result.get('document_id')}")
                return result
        except Exception as e:
            logger.error(f"Upload failed for {upload_filename}: {e}", exc_info=True)
            raise

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def upload_document_async(self, file_path: str | Path) -> str:
        """Upload a document asynchronously (returns task ID for polling).

        Args:
            file_path: Path to the document file

        Returns:
            Task ID for polling upload status

        Raises:
            FileNotFoundError: If file doesn't exist
            httpx.HTTPError: If upload initiation fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Starting async upload: {file_path.name}")
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}
                response = httpx.post(
                    f"{self.api_url}/documents/upload/async",
                    files=files,
                    timeout=self.upload_timeout,
                )
                response.raise_for_status()
                result = response.json()
                task_id = result.get("task_id")
                logger.info(f"Async upload started: {file_path.name} -> task {task_id}")
                return task_id
        except Exception as e:
            logger.error(f"Async upload failed for {file_path.name}: {e}", exc_info=True)
            raise

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def get_upload_status(self, task_id: str) -> dict[str, Any]:
        """Get the status of an async upload task.

        Args:
            task_id: Task ID from upload_document_async

        Returns:
            Dictionary with task status:
                - status: "pending", "processing", "completed", or "failed"
                - progress: Progress percentage (0-100)
                - result: Upload result (if completed)
                - error: Error message (if failed)

        Raises:
            httpx.HTTPError: If status check fails
        """
        try:
            response = httpx.get(
                f"{self.api_url}/documents/upload/status/{task_id}",
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get status for task {task_id}: {e}")
            raise

    def poll_upload_status(
        self, task_id: str, poll_interval: float = 1.0, timeout: float = 300.0
    ) -> dict[str, Any]:
        """Poll upload status until completion or timeout.

        Args:
            task_id: Task ID from upload_document_async
            poll_interval: Seconds between status checks (default: 1s)
            timeout: Maximum time to wait in seconds (default: 5min)

        Returns:
            Final upload result dictionary

        Raises:
            TimeoutError: If upload doesn't complete within timeout
            RuntimeError: If upload fails
        """
        start_time = time.time()
        logger.info(f"Polling upload status for task {task_id}")

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Upload polling timed out after {timeout}s for task {task_id}")

            status_data = self.get_upload_status(task_id)
            status = status_data.get("status")

            if status == "completed":
                logger.info(f"Upload completed: task {task_id}")
                return status_data.get("result", {})
            elif status == "failed":
                error = status_data.get("error", "Unknown error")
                logger.error(f"Upload failed: task {task_id} - {error}")
                raise RuntimeError(f"Upload failed: {error}")

            time.sleep(poll_interval)

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def list_processing_status(self) -> list[dict[str, Any]]:
        """List all processing tasks and their statuses.

        Returns:
            List of processing status dictionaries

        Raises:
            RuntimeError: If request fails
        """
        try:
            response = httpx.get(f"{self.api_url}/documents/status", timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list processing status: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def list_documents(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """List all indexed documents with pagination.

        Args:
            page: Page number (1-indexed, default: 1)
            page_size: Number of documents per page (default: 20)

        Returns:
            Dictionary with:
                - documents: List of document metadata
                - total: Total number of documents
                - page: Current page number
                - page_size: Documents per page
                - total_pages: Total number of pages

        Raises:
            httpx.HTTPError: If listing fails
        """
        try:
            response = httpx.get(
                f"{self.api_url}/documents/",
                params={"page": page, "page_size": page_size},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID.

        Args:
            document_id: Document ID to delete

        Returns:
            True if deletion was successful

        Raises:
            httpx.HTTPError: If deletion fails
        """
        logger.info(f"Deleting document: {document_id}")
        try:
            response = httpx.delete(
                f"{self.api_url}/documents/{document_id}",
                timeout=10.0,
            )
            response.raise_for_status()
            logger.info(f"Document deleted: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def query(self, question: str, top_k: int = 5) -> dict[str, Any]:
        """Query the RAG system with a question.

        Args:
            question: Question to ask
            top_k: Number of source documents to retrieve (default: 5)

        Returns:
            Dictionary with:
                - answer: Generated answer from LLM
                - sources: List of source documents with text and metadata
                - query: Original question
                - metadata: Query metadata (duration, model, etc.)

        Raises:
            httpx.HTTPError: If query fails
        """
        logger.info(f"Querying: {question[:50]}...")
        try:
            response = httpx.post(
                f"{self.api_url}/query/",
                json={"query": question, "top_k": top_k},
                timeout=self.query_timeout,
            )
            response.raise_for_status()
            result = response.json()
            logger.info("Query completed successfully")
            return result
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            raise
