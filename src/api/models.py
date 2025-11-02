"""Pydantic models for API request and response validation."""

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for query endpoint.

    Attributes:
        query: The user's question (1-500 characters)
        top_k: Number of documents to retrieve (1-20, default 5)
        context_override: Optional pre-fetched context to use instead of retrieval
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User query",
        examples=["What is machine learning?"],
    )
    top_k: int | None = Field(
        5,
        ge=1,
        le=20,
        description="Number of documents to retrieve",
    )
    context_override: list[str] | None = Field(
        None,
        description="Optional pre-fetched context",
    )


class QueryResponse(BaseModel):
    """Response model for query endpoint.

    Attributes:
        answer: The generated answer from the RAG agent
        sources: List of source documents with metadata
        query: The original query string
        metadata: Optional metadata about the response
    """

    answer: str = Field(
        ...,
        description="Generated answer",
    )
    sources: list[dict[str, Any]] = Field(
        ...,
        description="Source documents with metadata",
    )
    query: str = Field(
        ...,
        description="Original query",
    )
    metadata: dict[str, Any] | None = Field(
        None,
        description="Optional response metadata",
    )


class BatchQueryRequest(BaseModel):
    """Request model for batch query endpoint.

    Attributes:
        queries: List of query strings to process
        top_k: Number of documents to retrieve for each query
    """

    queries: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of queries to process",
    )
    top_k: int | None = Field(
        5,
        ge=1,
        le=20,
        description="Number of documents to retrieve per query",
    )


class UploadResponse(BaseModel):
    """Response model for document upload endpoint.

    Attributes:
        status: Status of the upload (success/error)
        filename: Name of the uploaded file
        document_id: Unique identifier for the document (source filename)
        chunks_created: Number of chunks created from the document
        message: Human-readable message about the upload
    """

    status: str = Field(
        ...,
        description="Upload status",
        examples=["success", "error"],
    )
    filename: str = Field(
        ...,
        description="Uploaded filename",
    )
    document_id: str = Field(
        ...,
        description="Document identifier (source filename)",
    )
    chunks_created: int = Field(
        ...,
        ge=0,
        description="Number of chunks created",
    )
    message: str = Field(
        ...,
        description="Status message",
    )


class BatchUploadResult(BaseModel):
    """Result for a single file in batch upload.

    Attributes:
        file: Filename
        status: Status of this specific upload
        chunks_created: Number of chunks (if successful)
        error: Error message (if failed)
    """

    file: str = Field(
        ...,
        description="Filename",
    )
    status: str = Field(
        ...,
        description="Upload status",
    )
    chunks_created: int | None = Field(
        None,
        description="Number of chunks created",
    )
    error: str | None = Field(
        None,
        description="Error message if failed",
    )


class BatchUploadResponse(BaseModel):
    """Response model for batch upload endpoint.

    Attributes:
        results: List of results for each uploaded file
        total: Total number of files processed
        successful: Number of successful uploads
        failed: Number of failed uploads
    """

    results: list[BatchUploadResult] = Field(
        ...,
        description="Upload results for each file",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total files processed",
    )
    successful: int = Field(
        ...,
        ge=0,
        description="Number of successful uploads",
    )
    failed: int = Field(
        ...,
        ge=0,
        description="Number of failed uploads",
    )


class DocumentInfo(BaseModel):
    """Information about an indexed document.

    Attributes:
        source_file: Original filename or source
        chunks_count: Number of chunks for this document
        indexed_at: Timestamp when document was indexed
        metadata: Additional document metadata
    """

    source_file: str = Field(
        ...,
        description="Source filename",
    )
    chunks_count: int = Field(
        ...,
        ge=0,
        description="Number of chunks",
    )
    indexed_at: str | None = Field(
        None,
        description="Index timestamp",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class DocumentListResponse(BaseModel):
    """Response model for document listing endpoint.

    Attributes:
        documents: List of document information
        total: Total number of unique documents
        total_chunks: Total number of chunks across all documents
    """

    documents: list[DocumentInfo] = Field(
        ...,
        description="List of documents",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Number of unique documents",
    )
    total_chunks: int = Field(
        ...,
        ge=0,
        description="Total number of chunks",
    )


class ProcessingStatus(BaseModel):
    """Status of document processing.

    Attributes:
        task_id: Unique identifier for processing task
        filename: Name of file being processed
        status: Current status (pending/processing/completed/failed)
        progress: Progress percentage (0-100)
        chunks_created: Number of chunks created (if completed)
        error: Error message (if failed)
        started_at: Timestamp when processing started
        completed_at: Timestamp when processing completed (if finished)
    """

    task_id: str = Field(
        ...,
        description="Task identifier",
    )
    filename: str = Field(
        ...,
        description="Filename being processed",
    )
    status: str = Field(
        ...,
        description="Processing status",
        examples=["pending", "processing", "completed", "failed"],
    )
    progress: int = Field(
        0,
        ge=0,
        le=100,
        description="Progress percentage",
    )
    chunks_created: int | None = Field(
        None,
        description="Number of chunks created",
    )
    error: str | None = Field(
        None,
        description="Error message if failed",
    )
    started_at: str = Field(
        ...,
        description="Start timestamp",
    )
    completed_at: str | None = Field(
        None,
        description="Completion timestamp",
    )


class ErrorResponse(BaseModel):
    """Standard error response model.

    Attributes:
        error: Error type/category
        message: Human-readable error message
        detail: Additional error details
        status_code: HTTP status code
    """

    error: str = Field(
        ...,
        description="Error type",
    )
    message: str = Field(
        ...,
        description="Error message",
    )
    detail: str | None = Field(
        None,
        description="Additional error details",
    )
    status_code: int = Field(
        ...,
        description="HTTP status code",
    )
