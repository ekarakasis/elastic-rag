# 3. Component Architecture

### 3.1 Configuration Layer (`src/config/`)

**Purpose:** Centralized, type-safe configuration management

**Components:**

```
src/config/
├── __init__.py          # Module exports
├── base.py              # Base configuration classes
├── settings.py          # Application settings (Pydantic)
└── secrets.py           # Secrets management (SecretStr)
```

**Key Classes:**

- `Settings`: Main configuration container
  - `AppSettings`: Application config (host, port, log level)
  - `LMStudioSettings`: LMStudio config (base URL, models, timeout)
  - `ElasticsearchSettings`: ES config (host, port, index, auth)
  - `ChunkingSettings`: Document chunking config (size, overlap)
  - `RetrievalSettings`: Search config (top_k, similarity threshold)
  - `CircuitBreakerSettings`: Resilience config (thresholds, timeouts)
  - `HealthSettings`: Health probe config (timeouts, intervals)

**Features:**

- Environment variable loading with `__` delimiter
- Type validation and conversion
- Default values for non-critical settings
- Secret masking for sensitive data
- Nested configuration structure

---

### 3.2 Document Processing Pipeline (`src/pipeline/`)

**Purpose:** Convert documents into searchable chunks with embeddings

**Components:**

```
src/pipeline/
├── __init__.py              # Module exports
├── document_processor.py    # Docling integration
├── chunker.py              # Text splitting logic
└── ingestion.py            # Pipeline orchestration
```

**Flow:**

```
Document (PDF/DOCX/HTML/etc.)
    ↓
Document Processor (Docling)
    ↓
Plain Text Extraction
    ↓
Chunker (token-based splitting)
    ↓
Chunks with Metadata
    ↓
Embedder (BGE-M3)
    ↓
Chunks with Vectors
    ↓
Indexer → Elasticsearch
```

**Key Classes:**

- `DocumentProcessor`: Handles document format conversion
- `Chunker`: Splits text into overlapping chunks
- `IngestionPipeline`: Orchestrates the entire process

**Features:**

- Multi-format support (PDF, DOCX, PPTX, HTML, Markdown, TXT)
- Token-based chunking with configurable size and overlap
- Metadata preservation (filename, source, timestamps)
- Batch processing support
- Error handling and logging

---

### 3.3 AI Models Layer (`src/ai_models/`)

**Purpose:** LLM interaction and embedding generation

**Components:**

```
src/ai_models/
├── __init__.py              # Module exports
├── litellm_interface.py     # Universal LLM adapter
└── embedder.py              # Embedding generation
```

**Key Classes:**

- `LLMInterface`: Universal adapter for LLM providers
  - Wraps LiteLLM for provider abstraction
  - Circuit breaker integration
  - Streaming and non-streaming support
  - Error handling and retries

- `Embedder`: Vector embedding generation
  - Uses LMStudio's BGE-M3 model
  - Batch embedding support
  - Consistent vector dimensions (1024)

**Circuit Breaker Integration:**

```python
class LLMInterface:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()

    def chat_completion(self, messages, stream=False):
        return self.circuit_breaker.call(
            self._litellm_completion,
            messages=messages,
            stream=stream
        )
```

**Features:**

- Provider-agnostic design (currently LMStudio, future: OpenAI, Anthropic, etc.)
- Automatic retry on transient failures
- Circuit breaker protection
- Comprehensive logging
- Streaming response support

---

### 3.4 Retrieval Layer (`src/retrieval/`)

**Purpose:** Document storage, indexing, and hybrid search

**Components:**

```
src/retrieval/
├── __init__.py                  # Module exports
├── elasticsearch_client.py      # ES connection management
├── index_manager.py             # Index lifecycle management
├── indexer.py                   # Document indexing
└── searcher.py                  # Hybrid search implementation
```

**Key Classes:**

- `ElasticsearchClient`: Connection pool and client management
  - Singleton pattern for connection reuse
  - Authentication support
  - Health checking
  - Error handling

- `IndexManager`: Index lifecycle management
  - Index creation with proper mappings
  - Index deletion and cleanup
  - Schema management
  - Version control

- `Indexer`: Document storage
  - Batch indexing support
  - Automatic embedding generation
  - Metadata handling
  - Duplicate prevention

- `Searcher`: Hybrid search
  - Vector similarity search (cosine)
  - BM25 keyword search
  - Score normalization and combination
  - Configurable weights
  - Result ranking

**Index Schema:**

```json
{
  "mappings": {
    "properties": {
      "content": {"type": "text"},
      "embedding": {
        "type": "dense_vector",
        "dims": 1024,
        "index": true,
        "similarity": "cosine"
      },
      "metadata": {
        "properties": {
          "filename": {"type": "keyword"},
          "chunk_index": {"type": "integer"},
          "timestamp": {"type": "date"}
        }
      }
    }
  }
}
```

**Hybrid Search Algorithm:**

```python
def hybrid_search(query: str, top_k: int = 5):
    # 1. Vector search
    query_embedding = embedder.embed(query)
    vector_results = es.knn_search(query_embedding)

    # 2. Keyword search
    keyword_results = es.bm25_search(query)

    # 3. Normalize scores
    vector_scores = normalize_scores(vector_results)
    keyword_scores = normalize_scores(keyword_results)

    # 4. Combine with weights
    combined = combine_scores(
        vector_scores,
        keyword_scores,
        weights=(0.7, 0.3)
    )

    # 5. Return top-k
    return combined[:top_k]
```

**Features:**

- Connection pooling for efficiency
- Automatic index management
- Batch operations
- Hybrid search with configurable weights
- Metadata filtering
- Result highlighting

---

### 3.5 Agent Layer (`src/agent/`)

**Purpose:** Stateless query processing and answer generation

**Components:**

```
src/agent/
├── __init__.py          # Module exports
├── rag_agent.py         # Google ADK agent implementation
└── runner.py            # Agent execution orchestration
```

**Key Classes:**

- `RAGAgent`: Stateless agent implementation
  - No conversation memory
  - Query-context-answer flow
  - Source citation
  - Error handling

- `AgentRunner`: Execution orchestration
  - Query preprocessing
  - Context retrieval
  - Agent invocation
  - Response formatting

**Agent Flow:**

```
User Query
    ↓
Runner.process_query()
    ↓
Searcher.hybrid_search()
    ↓
Retrieved Context (chunks)
    ↓
RAGAgent.generate_answer()
    ↓
LLMInterface.chat_completion()
    ↓
Answer with Citations
```

**Stateless Design:**

```python
class RAGAgent:
    def generate_answer(self, query: str, context: List[str]) -> str:
        """
        Generate answer from query and context.

        NO STATE IS MAINTAINED between calls.
        Each query is completely independent.
        """
        prompt = self._build_prompt(query, context)
        return self.llm.chat_completion(prompt)
```

**Features:**

- Fully stateless operation
- No conversation history
- Context-based answers only
- Automatic source citation
- Error handling and fallbacks

---

### 3.6 Resilience Layer (`src/resilience/`)

**Purpose:** System reliability and fault tolerance

**Components:**

```
src/resilience/
├── __init__.py              # Module exports
├── circuit_breaker.py       # Circuit breaker pattern
└── health_probes.py         # Kubernetes-style health checks
```

**Key Classes:**

- `CircuitBreaker`: Prevents cascading failures
  - Three states: CLOSED, OPEN, HALF_OPEN
  - Automatic failure detection
  - Configurable thresholds
  - Thread-safe operation
  - State transition logging

- `HealthProbes`: System health monitoring
  - Liveness probe (is app running?)
  - Readiness probe (is app ready for traffic?)
  - Startup probe (has app initialized?)
  - Async health checks
  - Dependency validation

**Circuit Breaker States:**

```
CLOSED (Normal)
  ↓ (5 failures)
OPEN (Rejecting calls)
  ↓ (60s timeout)
HALF_OPEN (Testing)
  ↓ (3 successes)
CLOSED
```

**Health Probe Endpoints:**

```
GET /health/live    → 200 if app is running
GET /health/ready   → 200 if app can handle traffic
GET /health/startup → 200 if app initialization complete
```

**Features:**

- Automatic failure detection and recovery
- Configurable failure thresholds
- Graceful degradation
- Health monitoring for all dependencies
- Kubernetes-compatible health checks
- Comprehensive logging

---

### 3.7 API Layer (`src/api/`)

**Purpose:** RESTful HTTP interface for document processing and querying

**Components:**

```
src/api/
├── __init__.py              # Module exports & router
├── models.py                # Pydantic request/response models
├── exceptions.py            # Custom exceptions & handlers
├── health.py                # Health check endpoints
├── documents.py             # Document upload endpoints
└── query.py                 # Query processing endpoints
```

**Key Components:**

- `models.py`: Type-safe API models
  - QueryRequest: Single query input validation
  - QueryResponse: Structured answer response
  - BatchQueryRequest: Multiple queries input
  - UploadResponse: Upload status and metadata
  - BatchUploadResponse: Batch upload results
  - DocumentInfo: Document metadata with chunk counts
  - DocumentListResponse: List of indexed documents
  - ProcessingStatus: Async task status tracking
  - ErrorResponse: Structured error information

- `exceptions.py`: Error handling
  - FileValidationError (400): Invalid file type/format
  - FileTooLargeError (413): File exceeds size limit
  - DocumentProcessingError (500): Processing failures
  - QueryProcessingError (500): Query failures
  - CircuitBreakerOpenError (503): LLM unavailable
  - Structured error handlers for all exception types

- `health.py`: Kubernetes-style probes
  - GET `/health/live`: Liveness probe (is app running?)
  - GET `/health/ready`: Readiness probe (can handle traffic?)
  - GET `/health/startup`: Startup probe (initialization complete?)
  - Integrates with HealthProbes from Phase 6

- `documents.py`: Document operations
  - POST `/documents/upload`: Single file upload (synchronous)
  - POST `/documents/upload/async`: Single file upload (asynchronous)
  - POST `/documents/upload/batch`: Multiple files upload
  - GET `/documents/`: List all indexed documents
  - DELETE `/documents/{document_id}`: Delete document by ID
  - GET `/documents/status/{task_id}`: Check processing status
  - GET `/documents/status`: List all processing tasks
  - File validation (extensions, size limits)
  - Automatic ingestion pipeline integration
  - Background task processing with progress tracking
  - Multipart/form-data support

- `query.py`: Query operations
  - POST `/query/`: Single query processing
  - POST `/query/batch`: Multiple queries processing
  - Stateless RAG agent integration
  - Circuit breaker protection
  - Configurable top_k retrieval

**Main Application (`src/main.py`):**

```python
from fastapi import FastAPI
from src.api import health, documents, query

app = FastAPI(
    title="Elastic RAG API",
    version="1.0.0",
    description="RAG system with Elasticsearch and local LLMs"
)

# Middleware
- Request logging (timing, status codes)
- CORS configuration
- Structured exception handling

# Routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(query.router, prefix="/query", tags=["Query"])

# Auto-generated docs at /docs and /redoc
```

**API Features:**

- **Stateless Design**: No session management, each request independent
- **Async Processing**: Background tasks with progress tracking
- **Document Management**: List, delete, and monitor document processing
- **Type Safety**: Pydantic validation for all inputs/outputs
- **Error Handling**: Structured errors with appropriate HTTP codes
- **File Validation**: Extension and size checks
- **Circuit Breaker**: LLM protection (returns 503 when open)
- **Health Probes**: Kubernetes-ready monitoring
- **Auto Documentation**: OpenAPI/Swagger at `/docs`
- **Request Logging**: Structured logs with timing
- **CORS Support**: Configurable cross-origin access

**Endpoints Overview:**

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| GET | `/` | API information | None |
| GET | `/health/live` | Liveness probe | None |
| GET | `/health/ready` | Readiness probe | None |
| GET | `/health/startup` | Startup probe | None |
| POST | `/documents/upload` | Upload single file (sync) | None |
| POST | `/documents/upload/async` | Upload single file (async) | None |
| POST | `/documents/upload/batch` | Upload multiple files | None |
| GET | `/documents/` | List all documents | None |
| DELETE | `/documents/{document_id}` | Delete document | None |
| GET | `/documents/status/{task_id}` | Get task status | None |
| GET | `/documents/status` | List all tasks | None |
| POST | `/query/` | Process single query | None |
| POST | `/query/batch` | Process multiple queries | None |
| GET | `/docs` | Swagger UI | None |
| GET | `/redoc` | ReDoc UI | None |

**File Upload Constraints:**

- Supported formats: `.pdf`, `.docx`, `.pptx`, `.html`, `.txt`
- Maximum size: 50MB per file
- Content-Type: `multipart/form-data`
- Validation errors return 400 Bad Request
- Size errors return 413 Payload Too Large

**Query Constraints:**

- Query length: 1-500 characters
- top_k range: 1-20 documents (default 5)
- Validation errors return 422 Unprocessable Entity
- Processing errors return 500 Internal Server Error
- Circuit breaker open returns 503 Service Unavailable

**Response Structures:**

Success (200):

```json
{
    "status": "success",
    "data": { ... },
    "metadata": { ... }
}
```

Error (4xx/5xx):

```json
{
    "error": "ErrorType",
    "message": "Human-readable message",
    "detail": "Additional context",
    "status_code": 400
}
```

**Middleware Stack:**

1. **Request Logging**: Logs method, path, duration, status
2. **CORS**: Configurable origin/method/header rules
3. **Exception Handling**: Catches and formats all exceptions
4. **Validation**: Pydantic automatic request validation
