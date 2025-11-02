# Elastic RAG Demos

This directory contains demonstration scripts that showcase how to use the Elastic RAG system components.

## Quick Start

```bash
# Run all demos sequentially
task demo-all

# Or run individual demos
task demo-phase3    # Document processing pipeline
task demo-phase4    # Elasticsearch integration
task demo-phase5    # RAG agent with Google ADK
task demo-phase6    # Resilience layer (circuit breaker & health probes)
task demo-phase7    # API layer (FastAPI REST endpoints)
```

## Available Demos

### Phase 3: Document Processing Pipeline

**File:** `demo_phase3.py`

Demonstrates the complete document ingestion pipeline:

- Document processing with Docling (supports PDF, DOCX, PPTX, HTML, TXT, MD, etc.)
- Text chunking with configurable size and overlap
- Embedding generation using LMStudio's local models
- End-to-end pipeline orchestration

**Prerequisites:**

- LMStudio running locally on `http://localhost:1234`
- Embedding model loaded (e.g., `text-embedding-bge-m3`)
- Configuration in `.env` file

**Run:**

```bash
task demo-phase3
# or
uv run python demos/demo_phase3.py
```

**Expected Output:**

- Processing time
- Number of chunks created
- Embedding dimensions (typically 768 or 1024)
- Sample embedding values

---

### Phase 4: Elasticsearch Integration

**File:** `demo_phase4.py`

Demonstrates the complete Elasticsearch integration for vector storage and semantic search:

- Elasticsearch health check and connection
- Index creation with vector field mappings
- Document indexing with embeddings
- Semantic search with vector similarity
- Hybrid search (keyword + semantic)
- Search result formatting with scores and metadata
- Index management operations

**Prerequisites:**

- Elasticsearch running locally on `http://localhost:9200`
- LMStudio running locally on `http://localhost:1234`
- Embedding model loaded in LMStudio
- Configuration in `.env` file

**Run:**

```bash
task demo-phase4
# or
uv run python demos/demo_phase4.py
```

**Expected Output:**

- Elasticsearch version and health status
- Index creation confirmation
- Document indexing progress
- Search results with relevance scores
- Example semantic search queries
- Comparison of semantic vs keyword search

---

### Phase 5: RAG Agent with Google ADK

**File:** `demo_phase5.py`

Demonstrates the complete RAG (Retrieval-Augmented Generation) agent using Google ADK:

- Stateless agent architecture
- Tool-based retrieval integration
- Context-aware answer generation
- Source citation in responses
- Real LLM integration via LiteLLM
- End-to-end query processing

**Prerequisites:**

- Elasticsearch running locally on `http://localhost:9200`
- LMStudio running locally on `http://localhost:1234`
- Chat model loaded in LMStudio (e.g., `qwen3-30b-a3b-mlx`)
- Embedding model loaded in LMStudio
- Configuration in `.env` file with LLM settings

**Run:**

```bash
task demo-phase5
# or
uv run python demos/demo_phase5.py
```

**Expected Output:**

- Prerequisites check (Elasticsearch + LMStudio status)
- Knowledge base setup (document indexing)
- Agent configuration display
- Retrieval tool test results
- Complete RAG query responses with citations
- Feature showcase (stateless design, tool integration)

---

## Prerequisites Summary

### Required Services

| Service | URL | Purpose | Phase 3 | Phase 4 | Phase 5 | Phase 6 | Phase 7 |
|---------|-----|---------|---------|---------|---------|---------|---------|
| LMStudio | `http://localhost:1234` | Embeddings + Chat | ✅ | ✅ | ✅ | ✅ | ✅ |
| Elasticsearch | `http://localhost:9200` | Vector storage | ❌ | ✅ | ✅ | ✅ | ✅ |
| FastAPI | `http://localhost:8000` | REST API | ❌ | ❌ | ❌ | ❌ | ✅ |

### Required Models

- **Embedding Model**: `text-embedding-bge-m3` or similar (for all phases)
- **Chat Model**: `qwen3-30b-a3b-mlx` or similar (for Phase 5 only)

### Setup Steps

1. **Start services:**

   ```bash
   task start  # Starts Elasticsearch
   ```

2. **Start LMStudio:**
   - Open LMStudio application
   - Load an embedding model (required for all demos)
   - Load a chat model (required for Phase 5 only)
   - Start the local server

3. **Verify configuration:**

   ```bash
   task health  # Check service status
   ```

## Running All Demos

```bash
# Run all demos in sequence
task demo-all

# This will execute:
# 1. Phase 3: Document processing (no Elasticsearch needed)
# 2. Phase 4: Elasticsearch integration (creates index, stores docs)
# 3. Phase 5: RAG agent (uses indexed docs from Phase 4)
```

## Demo Flow

The demos are designed to build on each other:

```text
Phase 3: Process Documents → Create Embeddings
    ↓
Phase 4: Store in Elasticsearch → Enable Semantic Search
    ↓
Phase 5: Retrieve Context → Generate Answers with LLM
    ↓
Phase 6: Circuit Breakers → Health Monitoring → Resilience
    ↓
Phase 7: REST API → HTTP Endpoints → Production Interface
```

Running them in order provides the best demonstration of the complete RAG pipeline.

## Troubleshooting

### LMStudio Not Responding

```bash
# Check if LMStudio server is running
curl http://localhost:1234/v1/models

# Expected: JSON response with model list
```

### Elasticsearch Not Running

```bash
# Start Elasticsearch
task start

# Check status
curl http://localhost:9200
```

### Demo Fails with Missing Documents

If Phase 5 fails to find documents:

```bash
# Re-run Phase 4 to index documents
task demo-phase4
```

### Import Errors

```bash
# Reinstall dependencies
task install

# Or update dependencies
task update
```

## Adding New Demos

When adding new demonstrations:

1. Follow the naming convention: `demo_phaseN.py` or `demo_feature_name.py`
2. Include clear docstrings explaining what the demo showcases
3. Add prerequisites and setup instructions
4. Update this README with the new demo information
5. Keep demos simple and focused on specific features
6. Add a task command in `Taskfile.yml` for easy execution

### Phase 6: Resilience Layer

**File:** `demo_phase6.py`

Demonstrates resilience features for production reliability:

- Circuit Breaker pattern with state transitions (CLOSED → OPEN → HALF_OPEN)
- Automatic failure detection and recovery mechanisms
- LLM interface protected by circuit breaker
- Kubernetes-style health probes (liveness, readiness, startup)
- Integrated resilience system with real services

**Prerequisites:**

- Elasticsearch (optional but recommended): `docker-compose -f docker/docker-compose.yml up -d`
- LMStudio with loaded model (optional but recommended)

**What's Special:**

- **NO MOCKING**: Uses 100% real services
- **Dual Purpose**: Working example + real-world testing
- **Graceful Degradation**: Runs even when services unavailable
- **Interactive**: Shows state transitions in real-time
- **Production Code**: Uses actual implementation, not test doubles

**Run:**

```bash
# Using task command (recommended)
task demo-phase6

# Or run directly with uv
uv run python demos/demo_phase6.py
```

**Note:** The demo adapts based on available services - runs full demo with both ES & LMStudio, or partial demos with what's available.

The demo will:

1. Check which services are available
2. Run circuit breaker basics (always works)
3. Test LLM with circuit breaker (if LMStudio available)
4. Test health probes (checks all services)
5. Show integrated resilience system (if services available)

**Output Features:**

- 🟢 Green checkmarks for successes
- 🔴 Red X marks for failures
- 🟡 Yellow info messages
- 🟣 Purple lightning for state changes
- Automatic progression through all demos

**Key Demonstrations:**

1. **Circuit Breaker States**
   - CLOSED: Normal operation, failures counted
   - OPEN: Service protection, calls rejected
   - HALF_OPEN: Recovery testing, limited calls

2. **Real Service Integration**
   - Actual Elasticsearch health checks
   - Real LMStudio LLM calls
   - True network conditions and timeouts

3. **Graceful Failure Handling**
   - Circuit opens after threshold failures
   - Automatic recovery after timeout
   - Fallback responses when service unavailable

---

### Phase 7: API Layer

**File:** `demo_phase7.py`

Demonstrates the complete REST API implementation with FastAPI:

- API information and available endpoints
- Kubernetes-style health probes (liveness, readiness, startup)
- Document upload (single and batch)
- Query processing (single and batch)
- Error handling and validation
- Circuit breaker integration (503 responses when LLM unavailable)
- Interactive Swagger UI and ReDoc documentation

**Prerequisites:**

- FastAPI application running on `http://localhost:8000`
- Elasticsearch running on `http://localhost:9200`
- LMStudio running on `http://localhost:1234` with models loaded
- Configuration in `.env` file

**What's Special:**

- **NO MOCKING**: Uses 100% real API endpoints
- **Complete Workflow**: Upload → Index → Query → Verify
- **Interactive**: Shows all API features in action
- **Production Code**: Real HTTP requests to running API
- **Error Examples**: Demonstrates validation and error handling

**Run:**

```bash
# Start the API first (in a separate terminal)
task dev

# Then run the demo (in another terminal)
task demo-phase7
# or
uv run python demos/demo_phase7.py
```

**The demo will:**

1. Check API availability and show endpoint information
2. Test all health probes (liveness, readiness, startup)
3. Upload sample documents (single and batch)
4. Verify document processing and indexing
5. Process queries (single and batch)
6. Demonstrate error handling (invalid files, validation errors)
7. Show circuit breaker behavior (if LLM unavailable)

**Output Features:**

- 🟢 Green checkmarks for successful operations
- 🔴 Red X marks for expected errors (demonstrations)
- 🔵 Blue info messages for API responses
- 📄 Document upload progress and results
- 💬 Query responses with answers
- ⚡ Timing information for all operations

**Key Demonstrations:**

1. **Health Probes**
   - Liveness: Is API running?
   - Readiness: Can API handle traffic?
   - Startup: Is initialization complete?
   - Dependency health checks (Elasticsearch, LLM)

2. **Document Upload**
   - Single file upload with validation
   - Batch upload with multiple files
   - Error handling for invalid files
   - File size and type validation

3. **Query Processing**
   - Single query with RAG agent
   - Batch queries (independent processing)
   - Configurable top_k retrieval
   - Circuit breaker protection

4. **Error Handling**
   - File validation errors (400)
   - File size errors (413)
   - Validation errors (422)
   - Processing errors (500)
   - Circuit breaker open (503)

**API Documentation Access:**

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- OpenAPI Schema: <http://localhost:8000/openapi.json>

**Example Workflow:**

```python
# The demo performs this complete workflow:
1. GET /              → API info
2. GET /health/ready  → Check services
3. POST /documents/upload → Upload document
4. Wait 2 seconds     → Allow indexing
5. POST /query/       → Query RAG system
6. Verify response    → Check answer quality
```

---

---

### Upload Verification Demo (v1.0.1+)

**File:** `demo_upload_verification.py`

**NEW in v1.0.1** - Demonstrates the proper workflow for verifying document uploads and preventing silent failures:

- Upload document via API
- **Verify indexing to Elasticsearch** (critical step!)
- Confirm document is searchable via queries
- Shows verification patterns that would have caught the v1.0.0 indexing bug

**Prerequisites:**

- FastAPI application running on `http://localhost:8000`
- Elasticsearch running on `http://localhost:9200`
- LMStudio running on `http://localhost:1234` (optional - demo shows warning if unavailable)

**Why This Matters:**

In v1.0.0, documents could upload successfully (200 OK response) but **fail to index to Elasticsearch**, making them unsearchable. This demo shows the verification steps that prevent this silent failure.

**Run:**

```bash
python demos/demo_upload_verification.py
```

**The demo will:**

1. Check API health
2. Upload a test document
3. ⚠️ **Verify indexing to Elasticsearch** (the critical step)
4. Confirm document is searchable via query
5. Show best practices for upload verification

**Output Features:**

- ✓ Green checkmarks for successful steps
- ⚠ Yellow warnings for important notices
- ✗ Red errors if verification fails
- Colored output showing each verification step
- Educational messages about the v1.0.0 bug

**Key Demonstrations:**

1. **Don't Trust API Responses Alone**
   - A 200 OK doesn't guarantee indexing
   - Always verify external system state

2. **Polling Pattern**
   - Wait for indexing to complete
   - Use intelligent polling, not fixed sleep times

3. **End-to-End Verification**
   - Check document appears in `/documents/` list
   - Verify chunks were indexed
   - Confirm document is searchable

**Expected Output:**

```
[Step 1] Uploading document
✓ Upload succeeded
⚠ A successful upload doesn't guarantee the document is searchable!

[Step 2] Verifying document indexed to Elasticsearch (polling)
✓ Document successfully indexed to Elasticsearch!

[Step 3] Verifying document is searchable
✓ Document found in query results!

This workflow would have caught the v1.0.0 indexing bug!
```

---

### System Health Check Demo

**File:** `demo_system_health.py`

Comprehensive system health check for all Elastic RAG components:

- API health probes (liveness, readiness, startup)
- Elasticsearch connection and document count
- LLM service availability (LMStudio)
- Document upload and processing pipeline
- Query/retrieval functionality
- Overall system status assessment

**Prerequisites:**

- FastAPI application running on `http://localhost:8000` (required)
- Elasticsearch running on `http://localhost:9200` (recommended)
- LMStudio running on `http://localhost:1234` (optional)

**Why Use This:**

- **First-time setup verification** - Confirm everything works
- **Troubleshooting** - Identify which component is failing
- **Production readiness** - Check all systems before deployment
- **Regular health checks** - Ensure system stays healthy

**Run:**

```bash
python demos/demo_system_health.py
```

**The demo will:**

1. Check API root endpoint and version
2. Test all health probes (liveness, readiness, startup)
3. Verify Elasticsearch accessibility and document count
4. Test document upload and indexing pipeline
5. Test query/retrieval system
6. Provide comprehensive status report with recommendations

**Output Features:**

- ✓ Green checkmarks for healthy components
- ⚠ Yellow warnings for degraded services
- ✗ Red errors for critical failures
- Colored section headers
- Detailed status for each component
- Actionable recommendations

**System Status Levels:**

- **HEALTHY** ✓ - All systems operational
- **DEGRADED** ⚠ - Core works but some features unavailable (e.g., LLM down)
- **CRITICAL** ✗ - Major components not working

**Exit Codes:**

- `0` - Healthy (all systems operational)
- `1` - Critical (major failures)
- `2` - Degraded (some services unavailable)

**Expected Output:**

```
▶ 1. API Root Endpoint
  ✓ API is reachable
    Name: Elastic RAG API
    Version: 1.0.1

▶ 2. Health Probes
  ✓ Liveness probe: healthy
  ✓ Readiness probe: healthy

▶ 3. Elasticsearch
  ✓ Elasticsearch is accessible
    Documents indexed: 42

▶ 4. Document Upload & Processing Pipeline
  ✓ Document upload works
  ✓ Document indexed successfully

▶ 5. Query & Retrieval System
  ⚠ Query system degraded: LLM service unavailable
    LMStudio may not be running

Health Check Summary
✓ SYSTEM STATUS: DEGRADED

Recommendations:
  3. Start LMStudio: lms server start
```

**Use Cases:**

- **Before running demos**: Verify all services are available
- **After installation**: Confirm setup is correct
- **Troubleshooting**: Identify which component is failing
- **CI/CD pipelines**: Automated health verification
- **Production deployment**: Pre-deployment readiness check

---

## Notes

- **Demos use real services** (LMStudio, Elasticsearch) - **NOT mocked**
- Make sure required services are running before executing demos
- Check `.env` file for proper configuration (see `.env.example`)
- Demos include comprehensive output and error messages
- Each demo performs prerequisite checks before execution
- Safe to run multiple times - demos are idempotent
- **Phase 6 demo gracefully handles missing services** - runs what it can
- **NEW in v1.0.1**: Upload verification and system health demos help prevent silent failures
