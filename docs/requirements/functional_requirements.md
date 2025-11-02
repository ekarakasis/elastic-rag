# 5. Functional Requirements

### 5.1 Document Ingestion (FR-1)

| ID | Requirement | Phase |
|---|---|---|
| FR-1.1 | System shall accept documents in multiple formats (PDF, DOCX, PPTX, HTML) | 3 |
| FR-1.2 | System shall convert documents to plain text using Docling | 3 |
| FR-1.3 | System shall extract metadata from documents (title, author, date, etc.) | 3 |
| FR-1.4 | System shall handle document conversion errors gracefully | 3 |

### 5.2 Text Processing (FR-2)

| ID | Requirement | Phase |
|---|---|---|
| FR-2.1 | System shall split documents into chunks using Haystack's text chunker | 3 |
| FR-2.2 | Chunk size shall be configurable (default: 512 tokens) | 3 |
| FR-2.3 | System shall maintain context overlap between chunks (default: 50 tokens) | 3 |
| FR-2.4 | System shall preserve document hierarchy and metadata in chunks | 3 |

### 5.3 Vectorization and Indexing (FR-3)

| ID | Requirement | Phase |
|---|---|---|
| FR-3.1 | System shall generate embeddings using LMStudio's embedding model | 3 |
| FR-3.2 | System shall store embeddings and chunks in Elasticsearch | 4 |
| FR-3.3 | System shall support batch indexing for multiple documents | 4 |
| FR-3.4 | System shall provide indexing progress feedback | 4 |

### 5.4 Retrieval (FR-4)

| ID | Requirement | Phase |
|---|---|---|
| FR-4.1 | System shall perform semantic search using vector similarity | 4 |
| FR-4.2 | System shall support keyword search using BM25 | 4 |
| FR-4.3 | System shall support hybrid search (combining semantic and keyword) | 4 |
| FR-4.4 | Number of retrieved chunks shall be configurable (default: 5) | 4 |
| FR-4.5 | System shall rank results by relevance score | 4 |

### 5.5 Agent-Based Answer Generation (FR-5)

| ID | Requirement | Phase |
|---|---|---|
| FR-5.1 | Agent shall process user queries through Google ADK (stateless operation) | 5 |
| FR-5.2 | Agent shall accept query and pre-retrieved context as input | 5 |
| FR-5.3 | Agent shall generate answers using LiteLLM interface | 5 |
| FR-5.4 | Agent shall use LMStudio for local inference | 5 |
| FR-5.5 | Agent shall cite sources in responses | 5 |
| FR-5.6 | Agent shall NOT maintain conversation history or memory between requests | 5 |
| FR-5.7 | Agent shall gracefully handle LLM service failures via circuit breaker | 6 |

### 5.6 Resilience and Reliability (FR-6)

| ID | Requirement | Phase |
|---|---|---|
| FR-6.1 | System shall implement circuit breaker pattern for LLM communication | 6 |
| FR-6.2 | Circuit breaker shall have configurable failure threshold (default: 5 failures) | 6 |
| FR-6.3 | Circuit breaker shall have configurable timeout period (default: 60 seconds) | 6 |
| FR-6.4 | System shall provide fallback responses when circuit is open | 6 |
| FR-6.5 | System shall log circuit state changes | 6 |

### 5.7 Health Monitoring (FR-7)

| ID | Requirement | Phase |
|---|---|---|
| FR-7.1 | System shall expose HTTP health probe endpoints | 7 |
| FR-7.2 | Liveness probe shall return 200 if application is running | 7 |
| FR-7.3 | Readiness probe shall verify dependencies | 7 |
| FR-7.4 | Startup probe shall verify initial system configuration | 7 |
| FR-7.5 | Health probes shall respond within 1 second | 7 |

### 5.8 API Interface (FR-8)

| ID | Requirement | Phase |
|---|---|---|
| FR-8.1 | System shall provide REST API endpoints | 7 |
| FR-8.2 | API shall use JSON for request/response format | 7 |
| FR-8.3 | API shall include error handling and validation | 7 |
| FR-8.4 | Query endpoint shall accept both query and optional context override | 7 |

### 5.9 Configuration Management (FR-9)

| ID | Requirement | Phase |
|---|---|---|
| FR-9.1 | System shall implement a central configuration module | 2 |
| FR-9.2 | Configuration module shall read from `.env` files | 2 |
| FR-9.3 | Configuration shall use Pydantic Settings for type-safe configuration | 2 |
| FR-9.4 | Configuration shall be extensible without code changes | 2 |
| FR-9.5 | Configuration shall validate all environment variables on startup | 2 |
| FR-9.6 | Configuration shall provide default values for non-critical settings | 2 |
| FR-9.7 | Configuration shall raise clear errors for missing required settings | 2 |
| FR-9.8 | All components shall access configuration through the central config module | 2 |
| FR-9.9 | Configuration shall support different environments (dev, test, prod) | 2 |

### 5.10 Secrets Management (FR-10)

| ID | Requirement | Phase |
|---|---|---|
| FR-10.1 | System shall separate secrets from regular configuration | 2 |
| FR-10.2 | Secrets shall NEVER be committed to version control | 1 |
| FR-10.3 | System shall support reading secrets from environment variables | 2 |
| FR-10.4 | System shall support reading secrets from Docker secrets (future) | 9 |
| FR-10.5 | Secrets shall be marked as sensitive in Pydantic models (masked in logs) | 2 |
| FR-10.6 | System shall validate secret format and presence on startup | 2 |
| FR-10.7 | Failed secret loading shall prevent application startup | 2 |
| FR-10.8 | Configuration module shall provide safe secret access methods | 2 |
| FR-10.9 | Secrets shall include API keys, database credentials, JWT signing keys | 2 |
| FR-10.10 | Example secrets file (`.env.example`) shall contain placeholders only | 1 |
