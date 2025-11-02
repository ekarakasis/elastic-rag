"""Document upload and management endpoints."""

import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status

from src.api.exceptions import (
    DocumentProcessingError,
    FileTooLargeError,
    FileValidationError,
)
from src.api.models import (
    BatchUploadResponse,
    BatchUploadResult,
    DocumentInfo,
    DocumentListResponse,
    ProcessingStatus,
    UploadResponse,
)
from src.config.settings import get_settings
from src.pipeline.ingestion import IngestionPipeline
from src.retrieval.elasticsearch_client import get_elasticsearch_client
from src.retrieval.indexer import DocumentIndexer

logger = logging.getLogger(__name__)

# Create router with documents prefix
router = APIRouter(prefix="/documents", tags=["documents"])

# In-memory storage for processing status tracking
# In production, use Redis or a proper database
_processing_status: dict[str, dict] = {}


def process_document_background(tmp_path: Path, filename: str, task_id: str) -> None:
    """Process document in background with progress tracking.

    This function runs as a background task after the upload endpoint
    returns a response. It handles the full ingestion pipeline,
    tracks progress, and cleans up temporary files.

    Args:
        tmp_path: Path to temporary file
        filename: Original filename for logging
        task_id: Unique task identifier for progress tracking

    Note:
        Exceptions are logged but not raised since this runs in background.
        Progress is tracked in the _processing_status dictionary.
    """
    try:
        logger.info(f"Background processing started for: {filename} (task: {task_id})")

        # Update status to processing
        _processing_status[task_id]["status"] = "processing"
        _processing_status[task_id]["progress"] = 10

        # Initialize pipeline with indexer for automatic indexing
        es_client = get_elasticsearch_client()
        document_store = es_client.get_document_store()
        indexer = DocumentIndexer(document_store=document_store)
        pipeline = IngestionPipeline(indexer=indexer)

        _processing_status[task_id]["progress"] = 30

        # Process document through pipeline AND index to Elasticsearch
        chunks, indexed_count = pipeline.ingest_and_index_document(tmp_path)

        _processing_status[task_id]["progress"] = 90

        # Update status to completed
        _processing_status[task_id]["status"] = "completed"
        _processing_status[task_id]["progress"] = 100
        _processing_status[task_id]["chunks_created"] = len(chunks)
        _processing_status[task_id]["indexed_count"] = indexed_count
        _processing_status[task_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            f"Background processing completed for {filename}: {len(chunks)} chunks created, "
            f"{indexed_count} indexed to Elasticsearch"
        )

    except Exception as e:
        logger.error(f"Background processing failed for {filename}: {e}", exc_info=True)
        _processing_status[task_id]["status"] = "failed"
        _processing_status[task_id]["progress"] = 0
        _processing_status[task_id]["error"] = str(e)
        _processing_status[task_id]["completed_at"] = datetime.utcnow().isoformat()

    finally:
        # Clean up temporary file and directory
        if tmp_path and tmp_path.exists():
            try:
                temp_dir = tmp_path.parent
                tmp_path.unlink()
                temp_dir.rmdir()
                logger.debug(f"Cleaned up temporary file and directory: {tmp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {tmp_path}: {e}")


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file extension and size.

    Args:
        file: The uploaded file to validate

    Raises:
        FileValidationError: If file extension is not supported
        FileTooLargeError: If file size exceeds maximum
    """
    # Get settings
    settings = get_settings()
    allowed_extensions = settings.file_upload.get_allowed_extensions_set()

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in allowed_extensions:
        raise FileValidationError(
            f"File type '{file_ext}' not supported. "
            f"Allowed types: {', '.join(sorted(allowed_extensions))}"
        )  # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > settings.file_upload.max_file_size_bytes:
        raise FileTooLargeError(settings.file_upload.max_file_size_mb)

    logger.debug(f"File validation passed: {file.filename} ({file_size} bytes, {file_ext})")


@router.post("/upload/async", response_model=UploadResponse)
async def upload_document_async(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> UploadResponse:
    """Upload and process a document asynchronously.

    This endpoint accepts a document file, validates it, saves it to a temporary
    location, and returns immediately while processing continues in the background.

    This is useful for:
        - Large documents that take time to process
        - Providing faster API response times
        - Non-blocking uploads in bulk operations

    Processing happens asynchronously after the response is sent:
        1. Extract text and metadata using Docling
        2. Split into chunks with overlap
        3. Generate embeddings for each chunk
        4. Index in Elasticsearch
        5. Clean up temporary files

    Supported file types:
        - PDF (.pdf)
        - Microsoft Word (.docx)
        - Microsoft PowerPoint (.pptx)
        - HTML (.html)
        - Plain text (.txt)

    Args:
        file: The document file to upload (multipart/form-data)
        background_tasks: FastAPI background tasks handler

    Returns:
        UploadResponse with:
            - status: "processing" (indicates background processing started)
            - filename: Name of uploaded file
            - chunks_created: 0 (processing not complete yet)
            - message: Human-readable status message

    Raises:
        FileValidationError: If file type not supported or filename missing
        FileTooLargeError: If file exceeds maximum size
        DocumentProcessingError: If initial file save fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/documents/upload/async" \\
             -H "accept: application/json" \\
             -H "Content-Type: multipart/form-data" \\
             -F "file=@document.pdf"
        ```

    Example Response:
        ```json
        {
            "status": "processing",
            "filename": "document.pdf",
            "chunks_created": 0,
            "message": "Document queued for processing: document.pdf"
        }
        ```

    Note:
        To check processing status, use the GET /documents endpoint or monitor logs.
        For synchronous processing, use POST /documents/upload instead.
    """
    if not file.filename:
        raise FileValidationError("Filename is required")

    # Validate file
    validate_file(file)

    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Save to temporary file with original filename
        temp_dir = Path(tempfile.mkdtemp())
        tmp_path = temp_dir / file.filename

        content = await file.read()
        tmp_path.write_bytes(content)

        logger.info(f"Document queued for async processing: {file.filename} (task: {task_id})")

        # Initialize progress tracking
        _processing_status[task_id] = {
            "task_id": task_id,
            "filename": file.filename,
            "status": "pending",
            "progress": 0,
            "chunks_created": None,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }

        # Queue background processing
        background_tasks.add_task(process_document_background, tmp_path, file.filename, task_id)

        return UploadResponse(
            status="processing",
            filename=file.filename,
            document_id=file.filename,
            chunks_created=0,
            message=f"Document queued for processing: {file.filename} (track with task_id: {task_id})",
        )

    except (FileValidationError, FileTooLargeError):
        # Re-raise validation errors
        raise

    except Exception as e:
        logger.error(f"Failed to save {file.filename}: {e}", exc_info=True)
        raise DocumentProcessingError(f"Failed to save document: {str(e)}") from e


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """Upload and process a single document.

    This endpoint accepts a document file, validates it, processes it through
    the ingestion pipeline, and indexes it in Elasticsearch for retrieval.

    Supported file types:
        - PDF (.pdf)
        - Microsoft Word (.docx)
        - Microsoft PowerPoint (.pptx)
        - HTML (.html)
        - Plain text (.txt)

    Processing steps:
        1. Validate file extension and size
        2. Save to temporary location
        3. Extract text and metadata using Docling
        4. Split into chunks with overlap
        5. Generate embeddings for each chunk
        6. Index in Elasticsearch
        7. Clean up temporary files

    Args:
        file: The document file to upload (multipart/form-data)

    Returns:
        UploadResponse with:
            - status: "success" or "error"
            - filename: Name of uploaded file
            - chunks_created: Number of chunks created
            - message: Human-readable status message

    Raises:
        FileValidationError: If file type not supported or filename missing
        FileTooLargeError: If file exceeds 50MB
        DocumentProcessingError: If processing fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/documents/upload" \\
             -H "accept: application/json" \\
             -H "Content-Type: multipart/form-data" \\
             -F "file=@document.pdf"
        ```

    Example Response:
        ```json
        {
            "status": "success",
            "filename": "document.pdf",
            "chunks_created": 42,
            "message": "Successfully ingested document.pdf"
        }
        ```
    """
    if not file.filename:
        raise FileValidationError("Filename is required")

    # Validate file
    validate_file(file)

    tmp_path = None
    try:
        # Save to temporary file with original filename
        # This ensures metadata extraction gets the correct filename
        temp_dir = Path(tempfile.mkdtemp())
        tmp_path = temp_dir / file.filename

        content = await file.read()
        tmp_path.write_bytes(content)

        logger.info(f"Processing uploaded file: {file.filename}")

        # Initialize pipeline with indexer for automatic indexing
        es_client = get_elasticsearch_client()
        document_store = es_client.get_document_store()
        indexer = DocumentIndexer(document_store=document_store)
        pipeline = IngestionPipeline(indexer=indexer)

        # Process document through pipeline AND index to Elasticsearch
        chunks, indexed_count = pipeline.ingest_and_index_document(tmp_path)

        logger.info(
            f"Successfully ingested {file.filename}: {len(chunks)} chunks created, "
            f"{indexed_count} indexed to Elasticsearch"
        )

        return UploadResponse(
            status="success",
            filename=file.filename,
            document_id=file.filename,
            chunks_created=len(chunks),
            message=f"Successfully ingested {file.filename}",
        )

    except (FileValidationError, FileTooLargeError):
        # Re-raise validation errors
        raise

    except Exception as e:
        logger.error(f"Failed to process {file.filename}: {e}", exc_info=True)
        raise DocumentProcessingError(f"Failed to process document: {str(e)}") from e

    finally:
        # Clean up temporary file and directory
        if tmp_path and tmp_path.exists():
            try:
                temp_dir = tmp_path.parent
                tmp_path.unlink()
                temp_dir.rmdir()
                logger.debug(f"Cleaned up temporary file and directory: {tmp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {tmp_path}: {e}")


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_batch(files: list[UploadFile] = File(...)) -> BatchUploadResponse:
    """Upload and process multiple documents in a single request.

    This endpoint accepts multiple files and processes each one independently.
    If one file fails, the others will still be processed.

    Processing:
        - Each file is validated and processed independently
        - Failures don't affect other files
        - Returns detailed results for each file

    Args:
        files: List of document files to upload (multipart/form-data)

    Returns:
        BatchUploadResponse with:
            - results: List of results for each file
            - total: Total number of files processed
            - successful: Number of successful uploads
            - failed: Number of failed uploads

    Example:
        ```bash
        curl -X POST "http://localhost:8000/documents/upload/batch" \\
             -H "accept: application/json" \\
             -H "Content-Type: multipart/form-data" \\
             -F "files=@doc1.pdf" \\
             -F "files=@doc2.txt"
        ```

    Example Response:
        ```json
        {
            "results": [
                {
                    "file": "doc1.pdf",
                    "status": "success",
                    "chunks_created": 42,
                    "error": null
                },
                {
                    "file": "doc2.txt",
                    "status": "error",
                    "chunks_created": null,
                    "error": "File too large"
                }
            ],
            "total": 2,
            "successful": 1,
            "failed": 1
        }
        ```
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    logger.info(f"Processing batch upload: {len(files)} files")

    results: list[BatchUploadResult] = []
    successful = 0
    failed = 0

    for file in files:
        filename = file.filename or "unknown"

        try:
            # Process individual file
            result = await upload_document(file)

            results.append(
                BatchUploadResult(
                    file=filename,
                    status="success",
                    chunks_created=result.chunks_created,
                    error=None,
                )
            )
            successful += 1

        except HTTPException as e:
            results.append(
                BatchUploadResult(
                    file=filename,
                    status="error",
                    chunks_created=None,
                    error=e.detail,
                )
            )
            failed += 1
            logger.warning(f"Failed to process {filename}: {e.detail}")

        except Exception as e:
            results.append(
                BatchUploadResult(
                    file=filename,
                    status="error",
                    chunks_created=None,
                    error=str(e),
                )
            )
            failed += 1
            logger.error(f"Unexpected error processing {filename}: {e}", exc_info=True)

    logger.info(
        f"Batch upload complete: {successful} successful, {failed} failed "
        f"out of {len(files)} total"
    )

    return BatchUploadResponse(
        results=results,
        total=len(files),
        successful=successful,
        failed=failed,
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """List all indexed documents with metadata.

    This endpoint queries Elasticsearch to retrieve information about all
    indexed documents, including their source files, chunk counts, and
    indexing timestamps.

    The documents are aggregated by source file, showing how many chunks
    each source document produced during the ingestion process.

    Returns:
        DocumentListResponse with:
            - documents: List of DocumentInfo objects
            - total: Number of unique source documents
            - total_chunks: Total number of chunks across all documents

    Raises:
        HTTPException: If unable to query Elasticsearch

    Example:
        ```bash
        curl -X GET "http://localhost:8000/documents/" \\
             -H "accept: application/json"
        ```

    Example Response:
        ```json
        {
            "documents": [
                {
                    "source_file": "machine_learning.pdf",
                    "chunks_count": 42,
                    "indexed_at": "2025-10-24T10:30:00",
                    "metadata": {
                        "file_type": "pdf",
                        "page_count": 15
                    }
                },
                {
                    "source_file": "deep_learning.docx",
                    "chunks_count": 28,
                    "indexed_at": "2025-10-24T11:15:00",
                    "metadata": {
                        "file_type": "docx"
                    }
                }
            ],
            "total": 2,
            "total_chunks": 70
        }
        ```

    Note:
        Documents are sorted by indexed_at timestamp (most recent first).
    """
    try:
        logger.info("Listing all indexed documents")

        # Get document store
        es_client = get_elasticsearch_client()
        document_store = es_client.get_document_store()

        # Get all documents from Elasticsearch
        # We use filter_documents with empty filters to get all docs
        all_docs = document_store.filter_documents(filters={})

        # Aggregate by source file
        doc_aggregation: dict[str, dict] = {}

        for doc in all_docs:
            meta = doc.meta or {}
            source_file = meta.get("source_file", "unknown")

            if source_file not in doc_aggregation:
                doc_aggregation[source_file] = {
                    "source_file": source_file,
                    "chunks_count": 0,
                    "indexed_at": meta.get("indexed_at"),
                    "metadata": {
                        k: v
                        for k, v in meta.items()
                        if k not in ["source_file", "indexed_at", "chunk_index"]
                    },
                }

            doc_aggregation[source_file]["chunks_count"] += 1

            # Keep the most recent indexed_at timestamp
            current_timestamp = doc_aggregation[source_file]["indexed_at"]
            new_timestamp = meta.get("indexed_at")
            if new_timestamp and (not current_timestamp or new_timestamp > current_timestamp):
                doc_aggregation[source_file]["indexed_at"] = new_timestamp

        # Convert to list and sort by indexed_at (most recent first)
        documents_list = sorted(
            doc_aggregation.values(),
            key=lambda x: x.get("indexed_at") or "",
            reverse=True,
        )

        # Create response
        documents = [DocumentInfo(**doc_info) for doc_info in documents_list]
        total_chunks = sum(doc.chunks_count for doc in documents)

        logger.info(f"Found {len(documents)} unique documents with {total_chunks} total chunks")

        return DocumentListResponse(
            documents=documents,
            total=len(documents),
            total_chunks=total_chunks,
        )

    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document list: {str(e)}",
        ) from e


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict[str, str | int]:
    """Delete a document and all its associated chunks.

    This endpoint removes all chunks belonging to a specific source document
    from Elasticsearch. The document_id should be the source filename (e.g.,
    "machine_learning.pdf").

    All chunks with matching source_file metadata will be deleted.

    Args:
        document_id: Source filename to delete (URL-encoded if contains special chars)

    Returns:
        Dictionary with:
            - status: "success"
            - document_id: The deleted document identifier
            - chunks_deleted: Number of chunks removed
            - message: Human-readable status message

    Raises:
        HTTPException(404): If document not found
        HTTPException(500): If deletion fails

    Example:
        ```bash
        # Delete by filename
        curl -X DELETE "http://localhost:8000/documents/machine_learning.pdf" \\
             -H "accept: application/json"

        # For filenames with spaces (URL-encoded)
        curl -X DELETE "http://localhost:8000/documents/my%20document.pdf" \\
             -H "accept: application/json"
        ```

    Example Response:
        ```json
        {
            "status": "success",
            "document_id": "machine_learning.pdf",
            "chunks_deleted": 42,
            "message": "Successfully deleted machine_learning.pdf and 42 chunks"
        }
        ```

    Note:
        This operation cannot be undone. Deleted documents must be re-uploaded
        to be indexed again.
    """
    try:
        logger.info(f"Deleting document: {document_id}")

        # Get document store
        es_client = get_elasticsearch_client()
        document_store = es_client.get_document_store()

        # Find all chunks for this source file
        # source_file is already a keyword type, no need for .keyword suffix
        matching_docs = document_store.filter_documents(
            filters={"field": "source_file", "operator": "==", "value": document_id}
        )

        if not matching_docs:
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found",
            )

        # Get document IDs to delete
        doc_ids_to_delete = [doc.id for doc in matching_docs]
        chunks_count = len(doc_ids_to_delete)

        logger.info(f"Found {chunks_count} chunks to delete for {document_id}")

        # Delete documents
        document_store.delete_documents(doc_ids_to_delete)

        logger.info(f"Successfully deleted {document_id}: {chunks_count} chunks removed")

        return {
            "status": "success",
            "document_id": document_id,
            "chunks_deleted": chunks_count,
            "message": f"Successfully deleted {document_id} and {chunks_count} chunks",
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        ) from e


@router.get("/status/{task_id}", response_model=ProcessingStatus)
async def get_processing_status(task_id: str) -> ProcessingStatus:
    """Get processing status for an async document upload.

    This endpoint allows you to check the progress of a document that
    was uploaded using the /documents/upload/async endpoint.

    The status will show:
        - pending: Document queued but not started
        - processing: Currently being processed
        - completed: Successfully processed
        - failed: Processing failed with error

    Args:
        task_id: The task ID returned from /documents/upload/async

    Returns:
        ProcessingStatus with current progress and status information

    Raises:
        HTTPException(404): If task_id not found

    Example:
        ```bash
        curl -X GET "http://localhost:8000/documents/status/{task_id}" \\
             -H "accept: application/json"
        ```

    Example Response:
        ```json
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "filename": "document.pdf",
            "status": "processing",
            "progress": 65,
            "chunks_created": null,
            "error": null,
            "started_at": "2025-10-24T10:30:00",
            "completed_at": null
        }
        ```

    Note:
        Status is kept in memory and will be lost on server restart.
        In production, use Redis or a database for persistent tracking.
    """
    if task_id not in _processing_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task ID '{task_id}' not found",
        )

    status_data = _processing_status[task_id]
    return ProcessingStatus(**status_data)


@router.get("/status", response_model=list[ProcessingStatus])
async def list_processing_status() -> list[ProcessingStatus]:
    """List all processing tasks and their statuses.

    Returns information about all async document processing tasks,
    including pending, in-progress, completed, and failed tasks.

    Returns:
        List of ProcessingStatus objects for all tracked tasks

    Example:
        ```bash
        curl -X GET "http://localhost:8000/documents/status" \\
             -H "accept: application/json"
        ```

    Example Response:
        ```json
        [
            {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "doc1.pdf",
                "status": "completed",
                "progress": 100,
                "chunks_created": 42,
                "error": null,
                "started_at": "2025-10-24T10:30:00",
                "completed_at": "2025-10-24T10:31:15"
            },
            {
                "task_id": "660f9511-f39c-52e5-b827-557766551111",
                "filename": "doc2.pdf",
                "status": "processing",
                "progress": 30,
                "chunks_created": null,
                "error": null,
                "started_at": "2025-10-24T10:32:00",
                "completed_at": null
            }
        ]
        ```

    Note:
        List is sorted by start time (most recent first).
    """
    # Sort by started_at timestamp, most recent first
    sorted_statuses = sorted(
        _processing_status.values(),
        key=lambda x: x.get("started_at", ""),
        reverse=True,
    )

    return [ProcessingStatus(**status_data) for status_data in sorted_statuses]
