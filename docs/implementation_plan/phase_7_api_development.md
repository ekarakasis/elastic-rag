# 10. Phase 7: API Development

**Goal:** Implement REST API for document ingestion and querying.

**Duration:** 4-5 days
**Status:** ✅ COMPLETED
**Completed:** October 24, 2025
**Dependencies:** Phase 5, Phase 6

### 10.1 FastAPI Setup

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 7.1.1 | Create `src/api/app.py` with FastAPI instance | 🔴 P0 | ✅ | Main FastAPI app |
| 7.1.2 | Configure CORS middleware | 🟡 P1 | ✅ | Allow cross-origin |
| 7.1.3 | Add request/response logging middleware | 🟡 P1 | ✅ | Log all requests |
| 7.1.4 | Configure exception handlers | 🔴 P0 | ✅ | Handle errors gracefully |
| 7.1.5 | Add API documentation setup | 🟡 P1 | ✅ | Swagger/OpenAPI |

### 10.2 Health Endpoints

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 7.2.1 | Create `src/api/health.py` | 🔴 P0 | ✅ | Health routes |
| 7.2.2 | Implement `/health/live` endpoint | 🔴 P0 | ✅ | Liveness probe |
| 7.2.3 | Implement `/health/ready` endpoint | 🔴 P0 | ✅ | Readiness probe |
| 7.2.4 | Implement `/health/startup` endpoint | 🔴 P0 | ✅ | Startup probe |
| 7.2.5 | Test health endpoints | 🔴 P0 | ✅ | Verify responses |

**File Structure:**

```python
# src/api/health.py
"""Health check endpoints."""
from fastapi import APIRouter, Response, status
from src.resilience.health_probes import HealthProbes

router = APIRouter(prefix="/health", tags=["health"])
health_probes = HealthProbes()


@router.get("/live")
async def liveness():
    """Liveness probe endpoint."""
    result = await health_probes.liveness()
    return result


@router.get("/ready")
async def readiness(response: Response):
    """Readiness probe endpoint."""
    result = await health_probes.readiness()
    if result["status"] != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/startup")
async def startup(response: Response):
    """Startup probe endpoint."""
    result = await health_probes.startup()
    if result["status"] != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
```

### 10.3 Document Ingestion Endpoints

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 7.3.1 | Create `src/api/documents.py` | 🔴 P0 | ✅ | Document routes |
| 7.3.2 | Implement `POST /documents/upload` endpoint | 🔴 P0 | ✅ | Upload documents |
| 7.3.3 | Add file validation (type, size) | 🔴 P0 | ✅ | Validate uploads |
| 7.3.4 | Implement async document processing | 🟡 P1 | ✅ | POST /documents/upload/async |
| 7.3.5 | Add progress tracking (optional) | 🟢 P2 | ✅ | GET /documents/status |
| 7.3.6 | Implement `GET /documents` endpoint | 🟢 P2 | ✅ | List all documents |
| 7.3.7 | Implement `DELETE /documents/{id}` endpoint | 🟢 P2 | ✅ | Delete document |

**File Structure:**

```python
# src/api/documents.py
"""Document management endpoints."""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List
from pathlib import Path
import tempfile
import shutil
from src.pipeline.ingestion import IngestionPipeline
import logging

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and process a document.

    Args:
        file: Document file to upload
        background_tasks: FastAPI background tasks

    Returns:
        Upload status and document ID
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE/1024/1024}MB"
        )

    # Save to temporary file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)

        # Process document
        logger.info(f"Processing uploaded file: {file.filename}")
        pipeline = IngestionPipeline()
        chunks = pipeline.ingest_document(tmp_path)

        # Clean up temp file
        tmp_path.unlink()

        return {
            "status": "success",
            "filename": file.filename,
            "chunks_created": len(chunks),
            "message": f"Successfully ingested {file.filename}"
        }

    except Exception as e:
        logger.error(f"Failed to process {file.filename}: {e}")
        if tmp_path.exists():
            tmp_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/batch")
async def upload_batch(files: List[UploadFile] = File(...)):
    """Upload multiple documents."""
    results = []
    for file in files:
        try:
            result = await upload_document(file)
            results.append({"file": file.filename, **result})
        except HTTPException as e:
            results.append({
                "file": file.filename,
                "status": "error",
                "error": e.detail
            })

    return {"results": results}
```

### 10.4 Query Endpoints

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 7.4.1 | Create `src/api/query.py` | 🔴 P0 | ✅ | Query routes |
| 7.4.2 | Define query request/response models | 🔴 P0 | ✅ | Pydantic models |
| 7.4.3 | Implement `POST /query` endpoint | 🔴 P0 | ✅ | Process queries |
| 7.4.4 | Add query validation | 🔴 P0 | ✅ | Validate input |
| 7.4.5 | Implement response formatting | 🔴 P0 | ✅ | Format with sources |
| 7.4.6 | Add error handling | 🔴 P0 | ✅ | Handle failures |

**File Structure:**

```python
# src/api/query.py
"""Query endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from src.agent.adk_agent import RAGAgent
import logging

router = APIRouter(prefix="/query", tags=["query"])
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """Query request model."""
    query: str = Field(..., min_length=1, max_length=500, description="User query")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of results to retrieve")
    context_override: Optional[List[str]] = Field(None, description="Optional pre-fetched context")


class Source(BaseModel):
    """Source metadata model."""
    source_file: str
    chunk_index: int
    title: Optional[str] = None
    author: Optional[str] = None


class QueryResponse(BaseModel):
    """Query response model."""
    answer: str
    sources: List[Dict]
    query: str


@router.post("/", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a user query (stateless).

    Each query is processed independently without conversation history.

    Args:
        request: Query request with query text and options

    Returns:
        QueryResponse with answer and sources
    """
    try:
        logger.info(f"Received query: {request.query[:50]}...")

        agent = RAGAgent()
        response = agent.process_query(
            query=request.query,
            context_override=request.context_override,
            top_k=request.top_k
        )

        return QueryResponse(
            answer=response.answer,
            sources=response.sources,
            query=response.query
        )

    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )


@router.post("/batch")
async def process_batch_queries(queries: List[str]):
    """
    Process multiple queries independently.

    Args:
        queries: List of query strings

    Returns:
        List of query responses
    """
    agent = RAGAgent()
    responses = agent.process_batch(queries)

    return {
        "results": [
            {
                "query": r.query,
                "answer": r.answer,
                "sources": r.sources
            }
            for r in responses
        ]
    }
```

### 10.5 Main Application

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 7.5.1 | Update `src/main.py` with FastAPI app | 🔴 P0 | ✅ | Main entry point |
| 7.5.2 | Register all routers | 🔴 P0 | ✅ | Include all endpoints |
| 7.5.3 | Add startup/shutdown events | 🟡 P1 | ✅ | Initialize resources |
| 7.5.4 | Configure logging | 🔴 P0 | ✅ | Setup logging |
| 7.5.5 | Add root endpoint with API info | 🟡 P1 | ✅ | Basic info endpoint |

**File Structure:**

```python
# src/main.py
"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from src.api import health, documents, query
from src.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Elastic RAG API",
    description="Elasticsearch-based RAG system with stateless agent",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(query.router)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting Elastic RAG API...")
    settings = get_settings()
    logger.info(f"Environment: {settings.app.environment}")
    logger.info(f"Log level: {settings.app.log_level}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down Elastic RAG API...")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Elastic RAG API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health/live"
    }
```

### 10.6 API Testing

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 7.6.1 | Create API integration tests | 🟡 P1 | ✅ | Test endpoints |
| 7.6.2 | Test document upload flow | 🔴 P0 | ✅ | End-to-end test |
| 7.6.3 | Test query flow | 🔴 P0 | ✅ | End-to-end test |
| 7.6.4 | Test error handling | 🟡 P1 | ✅ | Invalid inputs |
| 7.6.5 | Test health endpoints | 🔴 P0 | ✅ | All health checks |
| 7.6.6 | Load testing (optional) | 🟢 P2 | ⬜ | Optional - can be done later |

### 10.7 Phase 7 Completion Checklist

- [x] FastAPI app configured
- [x] All endpoints implemented
- [x] Health probes accessible
- [x] Document upload working
- [x] Query processing working
- [x] API documentation generated
- [x] Tests passing
- [x] Async document processing implemented
- [x] Progress tracking added
- [x] Document listing endpoint
- [x] Document deletion endpoint
- [x] All new endpoints tested (300 tests passing)

**Phase 7 Exit Criteria:**

- ✅ Can upload documents via API (sync and async)
- ✅ Can query via API and get responses
- ✅ Health endpoints respond correctly
- ✅ API documentation accessible
- ✅ All tests pass (300 passed, 1 skipped, 84% coverage)
- ✅ Can list all indexed documents
- ✅ Can delete documents by ID
- ✅ Can track async processing progress
