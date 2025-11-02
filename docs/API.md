# API Reference

**Version:** 1.0.0
**Last Updated:** October 25, 2025
**Base URL:** `http://localhost:8000`

---

## Overview

The Elastic RAG API provides REST endpoints for:

- Health monitoring (Kubernetes-style probes)
- Document upload and processing
- Stateless query processing with RAG agent
- Batch operations

### Key Features

- **Stateless Design** - No session management, each request independent
- **Type-Safe** - Pydantic models for validation
- **Circuit Breaker** - Protects against LLM service failures
- **Health Probes** - Kubernetes-ready monitoring
- **Auto Documentation** - Swagger UI at `/docs`

---

## Authentication

Currently no authentication is required. **Not suitable for production use.**

---

## Endpoints

### Root Endpoint

#### GET `/`

Get API information and available endpoints.

**Response 200:**

```json
{
    "name": "Elastic RAG API",
    "version": "1.0.0",
    "status": "running",
    "docs": "/docs",
    "endpoints": {
        "health": "/health/live, /health/ready, /health/startup",
        "upload": "/documents/upload",
        "async_upload": "/documents/upload/async",
        "batch_upload": "/documents/upload/batch",
        "list_documents": "/documents/",
        "delete_document": "/documents/{document_id}",
        "processing_status": "/documents/status/{task_id}",
        "all_tasks": "/documents/status",
        "query": "/query/",
        "batch_query": "/query/batch"
    }
}
```

---

## Health Endpoints

### Liveness Probe

#### GET `/health/live`

Check if the API is alive and running. Always returns healthy if executing.

**Response 200:**

```json
{
    "status": "healthy",
    "timestamp": "2025-10-24T10:30:00.123456",
    "probe": "liveness"
}
```

**Use Case:** Kubernetes liveness probe, crash detection

---

### Readiness Probe

#### GET `/health/ready`

Check if the API is ready to accept traffic. Performs dependency health checks.

**Response 200 (Healthy):**

```json
{
    "status": "healthy",
    "timestamp": "2025-10-24T10:30:00.123456",
    "probe": "readiness",
    "checks": {
        "elasticsearch": {
            "status": "healthy",
            "response_time_ms": 45
        },
        "llm": {
            "status": "healthy",
            "response_time_ms": 120
        }
    }
}
```

**Response 503 (Unhealthy):**

```json
{
    "status": "unhealthy",
    "timestamp": "2025-10-24T10:30:00.123456",
    "probe": "readiness",
    "checks": {
        "elasticsearch": {
            "status": "unhealthy",
            "error": "Connection refused"
        },
        "llm": {
            "status": "healthy",
            "response_time_ms": 120
        }
    }
}
```

**Use Case:** Kubernetes readiness probe, load balancer routing

---

### Startup Probe

#### GET `/health/startup`

Check if application initialization is complete.

**Response 200 (Complete):**

```json
{
    "status": "healthy",
    "timestamp": "2025-10-24T10:30:00.123456",
    "probe": "startup",
    "startup_complete": true,
    "checks": {...}
}
```

**Response 503 (Incomplete):**

```json
{
    "status": "unhealthy",
    "timestamp": "2025-10-24T10:30:00.123456",
    "probe": "startup",
    "startup_complete": false
}
```

**Use Case:** Kubernetes startup probe, deployment verification

---

## Document Endpoints

### Upload Single Document

#### POST `/documents/upload`

Upload and process a single document.

**Request:**

- Content-Type: `multipart/form-data`
- Field: `file` (binary)

**Supported Formats:**

- PDF (`.pdf`)
- Microsoft Word (`.docx`)
- Microsoft PowerPoint (`.pptx`)
- HTML (`.html`)
- Plain text (`.txt`)

**File Limits:**

- Maximum size: 50MB
- Must have supported extension

**Response 200:**

```json
{
    "status": "success",
    "filename": "document.pdf",
    "chunks_created": 42,
    "message": "Successfully ingested document.pdf"
}
```

**Error Responses:**

**400 Bad Request** - Invalid file type:

```json
{
    "error": "FileValidationError",
    "message": "File type '.exe' not supported. Allowed types: .pdf, .docx, .pptx, .html, .txt",
    "status_code": 400
}
```

**413 Payload Too Large** - File too large:

```json
{
    "error": "FileTooLargeError",
    "message": "File too large. Maximum size: 50MB",
    "status_code": 413
}
```

**500 Internal Server Error** - Processing failed:

```json
{
    "error": "DocumentProcessingError",
    "message": "Failed to process document: ...",
    "status_code": 500
}
```

**Example:**

```bash
curl -X POST "http://localhost:8000/documents/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"
```

**⚠️ IMPORTANT: Verify Upload Success**

A `200 OK` response indicates the document was **processed**, but you should verify it was **indexed to Elasticsearch** before querying:

```bash
# Wait 1-2 seconds for indexing to complete
sleep 2

# Verify document appears in list
curl "http://localhost:8000/documents/" | jq '.documents[] | select(.source_file == "document.pdf")'

# Check that chunks were indexed
# Expected: Should show document with chunks_count > 0
```

If the document doesn't appear or `chunks_count` is 0, the upload may have failed silently. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for diagnosis.

**Why This Matters:** In v1.0.0, documents could upload successfully but not index to Elasticsearch, making them unsearchable. Always verify indexing completed.

---

### Upload Multiple Documents

#### POST `/documents/upload/batch`

Upload and process multiple documents in one request.

**Request:**

- Content-Type: `multipart/form-data`
- Field: `files` (multiple files)

**Response 200:**

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
            "error": "File type not supported"
        }
    ],
    "total": 2,
    "successful": 1,
    "failed": 1
}
```

**Example:**

```bash
curl -X POST "http://localhost:8000/documents/upload/batch" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "files=@doc1.pdf" \
     -F "files=@doc2.txt"
```

**⚠️ IMPORTANT: Verify Batch Upload Success**

Even if all files show `"status": "success"`, verify they were indexed to Elasticsearch:

```bash
# Wait for indexing to complete
sleep 2

# Verify all documents appear
curl "http://localhost:8000/documents/" | jq '.documents[] | {file: .source_file, chunks: .chunks_count}'

# Expected: All uploaded files should appear with chunks_count > 0
```

**Batch Upload Notes:**

- Individual file failures are reported in the response
- Successful files should still be verified for indexing
- Use `/documents/` endpoint to confirm all files are searchable

---

### Upload Document Asynchronously

#### POST `/documents/upload/async`

Upload and process a document asynchronously in the background. Returns immediately with a task ID for tracking progress.

**Request:**

- Content-Type: `multipart/form-data`
- Field: `file` (binary)

**Supported Formats:**

- PDF (`.pdf`)
- Microsoft Word (`.docx`)
- Microsoft PowerPoint (`.pptx`)
- HTML (`.html`)
- Plain text (`.txt`)

**Response 202:**

```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Document processing started",
    "status_url": "/documents/status/550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses:**

**400 Bad Request** - Invalid file type:

```json
{
    "error": "FileValidationError",
    "message": "File type '.exe' not supported. Allowed types: .pdf, .docx, .pptx, .html, .txt",
    "status_code": 400
}
```

**413 Payload Too Large** - File too large:

```json
{
    "error": "FileTooLargeError",
    "message": "File too large. Maximum size: 50MB",
    "status_code": 413
}
```

**Example:**

```bash
curl -X POST "http://localhost:8000/documents/upload/async" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"
```

---

### List All Documents

#### GET `/documents/`

Retrieve a list of all indexed documents with metadata and chunk counts.

**Response 200:**

```json
{
    "documents": [
        {
            "source_file": "document.pdf",
            "chunks_count": 42,
            "indexed_at": "2024-01-15T10:30:00Z",
            "metadata": {
                "file_type": "pdf",
                "size_bytes": 1048576
            }
        },
        {
            "source_file": "presentation.pptx",
            "chunks_count": 28,
            "indexed_at": "2024-01-15T11:00:00Z",
            "metadata": {
                "file_type": "pptx"
            }
        }
    ],
    "total": 2,
    "total_chunks": 70
}
```

**Example:**

```bash
curl -X GET "http://localhost:8000/documents/" \
     -H "accept: application/json"
```

---

### Delete Document

#### DELETE `/documents/{document_id}`

Delete all chunks associated with a specific document from the index.

**Path Parameters:**

- `document_id` (string, required): The source filename or document identifier

**Response 200:**

```json
{
    "status": "success",
    "message": "Deleted 42 chunks for document 'document.pdf'"
}
```

**Error Responses:**

**404 Not Found** - Document doesn't exist:

```json
{
    "detail": "Document 'nonexistent.pdf' not found"
}
```

**Example:**

```bash
curl -X DELETE "http://localhost:8000/documents/document.pdf" \
     -H "accept: application/json"
```

---

### Get Processing Status

#### GET `/documents/status/{task_id}`

Check the status of an asynchronous document processing task.

**Path Parameters:**

- `task_id` (string, required): UUID returned from async upload endpoint

**Response 200 - Processing:**

```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "document.pdf",
    "status": "processing",
    "progress": 45,
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": null,
    "error": null
}
```

**Response 200 - Completed:**

```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "document.pdf",
    "status": "completed",
    "progress": 100,
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:32:15Z",
    "error": null
}
```

**Response 200 - Failed:**

```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "document.pdf",
    "status": "failed",
    "progress": 0,
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:30:05Z",
    "error": "Failed to process document: Invalid PDF format"
}
```

**Error Responses:**

**404 Not Found** - Task doesn't exist:

```json
{
    "detail": "Task not found"
}
```

**Example:**

```bash
curl -X GET "http://localhost:8000/documents/status/550e8400-e29b-41d4-a716-446655440000" \
     -H "accept: application/json"
```

---

### List All Processing Tasks

#### GET `/documents/status`

Retrieve the status of all document processing tasks (current and historical).

**Response 200:**

```json
{
    "tasks": [
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "filename": "document.pdf",
            "status": "completed",
            "progress": 100,
            "started_at": "2024-01-15T10:30:00Z",
            "completed_at": "2024-01-15T10:32:15Z",
            "error": null
        },
        {
            "task_id": "660f9511-f39c-52e5-b827-557766551111",
            "filename": "presentation.pptx",
            "status": "processing",
            "progress": 60,
            "started_at": "2024-01-15T11:00:00Z",
            "completed_at": null,
            "error": null
        }
    ],
    "total": 2
}
```

**Example:**

```bash
curl -X GET "http://localhost:8000/documents/status" \
     -H "accept: application/json"
```

---

## Query Endpoints

### Process Single Query

#### POST `/query/`

Process a user query through the RAG agent. Stateless - no conversation history.

**Request Body:**

```json
{
    "query": "What is machine learning?",
    "top_k": 5
}
```

**Request Fields:**

- `query` (string, required): User question (1-500 characters)
- `top_k` (integer, optional): Number of documents to retrieve (1-20, default 5)

**Response 200:**

```json
{
    "answer": "Machine learning is a subset of artificial intelligence that focuses on building systems that can learn from and make decisions based on data...",
    "sources": [],
    "query": "What is machine learning?",
    "metadata": {
        "top_k": 5
    }
}
```

**Error Responses:**

**422 Validation Error** - Invalid input:

```json
{
    "error": "ValidationError",
    "message": "Request validation failed",
    "detail": "query: String should have at least 1 character",
    "status_code": 422
}
```

**500 Internal Server Error** - Processing failed:

```json
{
    "error": "QueryProcessingError",
    "message": "Failed to process query: ...",
    "status_code": 500
}
```

**503 Service Unavailable** - Circuit breaker open:

```json
{
    "error": "CircuitBreakerOpenError",
    "message": "LLM service temporarily unavailable. Circuit breaker is open. Please retry later.",
    "status_code": 503
}
```

**Example:**

```bash
curl -X POST "http://localhost:8000/query/" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is machine learning?", "top_k": 5}'
```

---

### Process Multiple Queries

#### POST `/query/batch`

Process multiple queries independently (no shared context).

**Request Body:**

```json
{
    "queries": [
        "What is machine learning?",
        "What is deep learning?"
    ],
    "top_k": 5
}
```

**Request Fields:**

- `queries` (array of strings, required): List of queries (1-10 queries)
- `top_k` (integer, optional): Number of documents per query (1-20, default 5)

**Response 200:**

```json
[
    {
        "answer": "Machine learning is...",
        "sources": [],
        "query": "What is machine learning?",
        "metadata": {"top_k": 5}
    },
    {
        "answer": "Deep learning is...",
        "sources": [],
        "query": "What is deep learning?",
        "metadata": {"top_k": 5}
    }
]
```

**Example:**

```bash
curl -X POST "http://localhost:8000/query/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "queries": ["What is ML?", "What is AI?"],
       "top_k": 5
     }'
```

---

## Data Models

### QueryRequest

```python
{
    "query": str,                    # 1-500 characters
    "top_k": Optional[int],          # 1-20, default 5
    "context_override": Optional[List[str]]  # Optional pre-fetched context
}
```

### QueryResponse

```python
{
    "answer": str,                   # Generated answer
    "sources": List[Dict],           # Source documents
    "query": str,                    # Original query
    "metadata": Optional[Dict]       # Response metadata
}
```

### UploadResponse

```python
{
    "status": str,                   # "success" or "error"
    "filename": str,                 # Uploaded filename
    "chunks_created": int,           # Number of chunks
    "message": str                   # Status message
}
```

### ErrorResponse

```python
{
    "error": str,                    # Error type
    "message": str,                  # Error message
    "detail": Optional[str],         # Additional details
    "status_code": int               # HTTP status code
}
```

---

## Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid input (file type, etc.) |
| 404 | Not Found | Endpoint doesn't exist |
| 405 | Method Not Allowed | Wrong HTTP method |
| 413 | Payload Too Large | File exceeds size limit |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Dependency unavailable (circuit breaker) |

---

## Rate Limiting

Currently not implemented. **Not suitable for production use.**

---

## Interactive Documentation

### Swagger UI

Access interactive API documentation at:

```
http://localhost:8000/docs
```

Features:

- Try endpoints directly
- View request/response schemas
- Test authentication
- Download OpenAPI schema

### ReDoc

Alternative documentation view at:

```
http://localhost:8000/redoc
```

Features:

- Clean, organized layout
- Better for reading/reference
- Search functionality

### OpenAPI Schema

Machine-readable API specification:

```
http://localhost:8000/openapi.json
```

Use for:

- Client code generation
- API testing tools
- Documentation generators

---

## Error Handling

All errors return structured JSON responses:

```json
{
    "error": "ErrorType",
    "message": "Human-readable message",
    "detail": "Additional context (optional)",
    "status_code": 500
}
```

### Common Errors

**FileValidationError (400):**

- Invalid file extension
- Missing filename
- Unsupported format

**FileTooLargeError (413):**

- File exceeds 50MB limit

**QueryProcessingError (500):**

- Agent processing failed
- Retrieval failed
- Unexpected error

**CircuitBreakerOpenError (503):**

- LLM service unavailable
- Too many failures
- Automatic protection

---

## Best Practices

### Upload Documents

1. **Validate locally** - Check file type and size before upload
2. **Use batch upload** - More efficient for multiple files
3. **Handle errors** - Check response status for each file
4. **Wait for indexing** - Allow 2-3 seconds after upload before querying

### Process Queries

1. **Keep queries concise** - 1-500 characters
2. **Adjust top_k** - More documents = better context but slower
3. **Handle circuit breaker** - Implement retry logic for 503 errors
4. **Batch when possible** - More efficient for multiple questions

### Health Monitoring

1. **Liveness** - Check every 10 seconds
2. **Readiness** - Check before routing traffic
3. **Startup** - Check with longer timeout during initialization

---

## Examples

### Complete Workflow

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

# 1. Check health
health = client.get("/health/ready")
print(f"Health: {health.json()['status']}")

# 2. Upload document
with open("document.pdf", "rb") as f:
    upload = client.post(
        "/documents/upload",
        files={"file": ("document.pdf", f, "application/pdf")}
    )
print(f"Uploaded: {upload.json()['chunks_created']} chunks")

# 3. Query
import time
time.sleep(2)  # Wait for indexing

query = client.post(
    "/query/",
    json={"query": "What is in the document?", "top_k": 5}
)
print(f"Answer: {query.json()['answer']}")
```

### Error Handling

```python
try:
    response = client.post("/query/", json={"query": "test"})
    response.raise_for_status()
    data = response.json()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 503:
        print("LLM unavailable, retrying...")
        time.sleep(10)
        # Retry logic
    else:
        print(f"Error: {e.response.json()}")
```

---

## Configuration

Configure via environment variables (`.env`):

```bash
# API Server
APP__ENVIRONMENT=development
APP__LOG_LEVEL=INFO

# File Upload
MAX_FILE_SIZE_MB=50
ALLOWED_EXTENSIONS=.pdf,.docx,.pptx,.html,.txt

# CORS
CORS_ORIGINS=*

# Health Probes
HEALTH__CHECK_TIMEOUT=5.0
```

---

## Changelog

### Version 1.0.0 (October 24, 2025)

**Added:**

- Health check endpoints (liveness, readiness, startup)
- Document upload (single and batch)
- Query processing (single and batch)
- Structured error handling
- Auto-generated documentation
- Request logging middleware

---

## Support

For issues or questions:

- Check `/docs` for interactive documentation
- Review `demos/demo_phase7.py` for usage examples
- See `PHASE7_SUMMARY.md` for implementation details
