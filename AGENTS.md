# Agent Development Guide - Elastic RAG

**Purpose**: This guide helps coding agents work effectively in the Elastic RAG codebase.

---

## 🔄 Current Session State (Last Updated: 2025-11-02)

**Active Work**: Documentation & Code Quality Review Complete

**Recent Completed Work**:

- ✅ **Code Quality Review Report** (2025-11-02):
  - Comprehensive 30+ page production readiness assessment
  - Grade: A- (85% test coverage achieved)
  - 319 tests passing (85% core coverage, 66% total with UI)
  - Production readiness: 75-80% (4-6 weeks to full production)
  - Report: `Prompts/reports/2025-11-02_code_quality_review.md`

- ✅ **Memory Leakage Analysis Report** (2025-11-02):
  - Static code analysis for resource management and memory leaks
  - Grade: B+ (Good with one backend fix needed)
  - Identified 1 critical backend issue: unbounded `_processing_status` dict
  - Properly scoped Gradio UI as dev/demo tool (no memory fixes needed)
  - Report: `Prompts/reports/2025-11-02_memory_leakage_analysis.md`

- ✅ **Updated Issue Tracking** (2025-11-02):
  - Updated `issues_tracking/2025-10-31_09-19-23_001_gradio_ui_improvements.md`
  - Added comprehensive executive summary with status tables
  - Documented all completed phases (1, 2, Delete Bug Fix)
  - Phase 2.5 (auto-refresh) marked as acceptable partial implementation
  - Phase 3 (Document-Specific Search) ready and awaiting user approval

**Previous Major Work** (2025-10-31 to 2025-11-01):

- ✅ **Gradio UI Phase 1** - Fixed critical bugs (source display, chunk count, API response)
- ✅ **Gradio UI Phase 2** - UI redesign with 4 user-requested fixes (pagination, font size, formatting, tabs)
- ✅ **Delete Document Bug Fix** - Fixed 404 error (source_file.keyword → source_file)
- ⚠️ **Phase 2.5** - Auto-refresh partially implemented (manual "Refresh Status" button works, automatic polling not possible due to Gradio 4.x limitations)

**Current System Status**:

- Backend API: ✅ Production-ready (except `_processing_status` cleanup needed)
- Gradio UI: ✅ Fit for purpose as dev/demo tool
- Tests: ✅ 319 passing (85% core coverage)
- Code Quality: ✅ All ruff + black checks passing
- Documentation: ✅ Comprehensive and up-to-date
- Memory Management: ⚠️ One backend fix recommended (7-10 hours)

**Known Issues & Limitations**:

1. **Backend**: Unbounded `_processing_status` dict in `src/api/documents.py` (line 36)
   - Impact: Memory leak in high-volume production scenarios
   - Priority: 🔥 CRITICAL for production deployment
   - Fix Time: 4-6 hours
   - Solution: Implement TTL cleanup or Redis with expiration

2. **Gradio UI**: Auto-refresh requires manual button click
   - Impact: Minor UX inconvenience for dev/demo tool
   - Priority: ℹ️ LOW (acceptable for intended use)
   - Status: WONTFIX (Gradio 4.x limitation, manual button sufficient)

**Next Steps**:

1. **User Decision**: Approve Phase 3 (Document-Specific Search) implementation?
2. **Backend Production**: Implement `_processing_status` cleanup (if production deployment planned)
3. **Optional**: Phase 4 UI polish features (inline delete, source cards, example questions)

**Quick Test Commands**:

```bash
# Start services
task start        # Start backend (localhost:8000)
task ui:dev       # Start Gradio UI (localhost:7860)

# Run tests
task test         # All 319 tests with coverage
task lint         # Code quality checks

# Check reports
cat Prompts/reports/2025-11-02_code_quality_review.md
cat Prompts/reports/2025-11-02_memory_leakage_analysis.md
```

---

## Issues Tracking System

The `issues_tracking/` folder contains detailed plans, bug reports, and enhancement proposals for the project. Each issue is documented in a separate markdown file with a structured naming convention.

### Naming Convention

```
YYYY-mm-dd_HH-MM-SS_###_descriptive_name.md
```

- **Timestamp**: ISO 8601 format (YYYY-mm-dd_HH-MM-SS) for chronological ordering
- **Issue ID**: Three-digit sequential number (001, 002, etc.)
- **Description**: Short kebab-case description of the issue

### Purpose

- **Track known issues**: Bugs, limitations, and technical debt
- **Document enhancement plans**: Detailed proposals for new features or improvements
- **Provide context**: Full analysis, proposed solutions, risk assessment, and implementation details
- **Enable continuity**: Agents can reference past decisions and understand project evolution

### Usage for Agents

1. **Check for existing issues**: Before starting work, review `issues_tracking/` for related plans or known issues
2. **Reference in commits**: Link to issue files in commit messages (e.g., "Implements Phase 1 of issues_tracking/2025-10-31_09-19-23_001_gradio_ui_improvements.md")
3. **Update status**: When implementing changes, update the status section in the issue file
4. **Create new issues**: Document new problems or enhancement ideas with proper naming and structure

### Current Active Issues

- **[2025-10-31_09-19-23_001_gradio_ui_improvements.md](./issues_tracking/2025-10-31_09-19-23_001_gradio_ui_improvements.md)**: Comprehensive Gradio UI redesign and bug fixes
  - **Status**: Phase 1 ✅ | Phase 2 ✅ | Phase 2.5 ⚠️ PARTIAL | Delete Bug ✅ | Phase 3 ⏳ READY
  - **Priority**: High
  - **Last Updated**: 2025-11-02
  - **Next Action**: Phase 3 (Document-Specific Search) awaiting user approval

  **Completed Work**:
  - ✅ **Phase 1** - Fixed critical bugs (source display, chunk count, document_id)
  - ✅ **Phase 2** - UI redesign with 4 user fixes (pagination, font size, formatting, tabs)
  - ⚠️ **Phase 2.5** - Auto-refresh partial (manual button works, auto-polling not possible in Gradio 4.x)
  - ✅ **Delete Bug** - Fixed 404 error (`source_file.keyword` → `source_file`)
  - ✅ **All 319 tests passing** (85% core coverage)

  **Remaining Work**:
  - ⏳ **Phase 3** - Document-specific search (2-3 hours, awaiting approval)
  - ⏳ **Phase 4** - UX polish (1-2 hours, optional)

  **Key Insight**: Gradio UI properly scoped as development/demo tool. Auto-refresh limitation acceptable for intended use case. Production clients should use FastAPI backend API directly.

## RAG Agent Instructions

The RAG agent in `src/agent/rag_agent.py` has comprehensive built-in instructions for document-only responses. These instructions are defined in the `instruction` parameter when creating the `LlmAgent`.

**Core Principles** (lines 111-195 in rag_agent.py):

1. **Document-Only Knowledge**: Agent MUST use ONLY information from documents retrieved via `retrieve_context` tool
   - Never use internal knowledge, training data, or general knowledge
   - If information isn't in documents, explicitly state this

2. **Mandatory Tool Usage**: For EVERY question, agent MUST call `retrieve_context` first
   - No exceptions - tool must be called before responding

3. **Source Attribution**: Always cite sources with reference numbers [1], [2], [3]
   - Cite all relevant sources for each claim
   - Format: "According to [1], ..." or "The documentation states [2] ..."

4. **Transparency**: If documents lack relevant information, use these phrases:
   - "I cannot find relevant information about [topic] in the available documents"
   - "The retrieved documents do not contain information to answer your question about [topic]"
   - "Based on the document search, there is no available information regarding [topic]"
   - "The document collection does not appear to have content related to [specific question]"

**Never**:

- Guess or speculate beyond document content
- Use phrases like "I think", "probably", "it might be"
- Provide answers from general knowledge when documents are silent
- Make assumptions or inferences not explicitly stated in documents

**Edge Cases Handled**:

- **No documents retrieved**: State clearly that search returned no results
- **Low-quality/irrelevant results**: Explain that documents don't contain specific information requested
- **Conflicting information**: Cite both sources and note the discrepancy (e.g., "[1] states X while [2] indicates Y")
- **Partial match**: State what IS found (with citations) and what information is MISSING

**Quality Guidelines**:

- Keep answers concise and directly address the question
- Quote or paraphrase document content accurately
- Be precise with citations (no vague references)
- Prioritize user trust by admitting limitations

**Primary Rule**: If it's not in the retrieved documents, don't say it.

See `src/agent/rag_agent.py` lines 111-195 for the complete instruction text embedded in the agent.

---

## Quick File Reference

This section helps you quickly locate the right files and functions for common tasks.

### Core Entry Points

**Configuration & Settings**

- `src/config/settings.py::Settings` - Main settings class (singleton)
- `src/config/settings.py::get_settings()` - Get settings instance
- `src/config/base.py::BaseConfig` - Base configuration class
- `src/config/secrets.py` - Secret handling utilities

**Document Processing Pipeline**

- `src/pipeline/document_processor.py::DocumentProcessor.process_document()` - Main document processing
- `src/pipeline/chunker.py::DocumentChunker.chunk()` - Text chunking with Haystack
- `src/pipeline/ingestion.py::IngestionPipeline.process()` - Full ingestion pipeline

**Search & Retrieval**

- `src/retrieval/searcher.py::SemanticSearcher.hybrid_search()` - Hybrid search (vector + BM25)
- `src/retrieval/searcher.py::SemanticSearcher.search()` - Pure vector search
- `src/retrieval/searcher.py::SemanticSearcher.keyword_search()` - Pure keyword search
- `src/retrieval/indexer.py::DocumentIndexer.index_chunks()` - Index document chunks
- `src/retrieval/elasticsearch_client.py::get_elasticsearch_client()` - Get ES client singleton
- `src/retrieval/index_manager.py::IndexManager` - Index lifecycle management

**LLM & Agent**

- `src/agent/rag_agent.py::create_rag_agent()` - Create stateless RAG agent
- `src/agent/runner.py::run_query()` - Execute query with agent
- `src/ai_models/litellm_interface.py::LiteLLMInterface.generate()` - LLM generation with circuit breaker
- `src/ai_models/embedder.py::Embedder.embed()` - Text embedding generation

**API Endpoints**

- `src/api/documents.py` - Document upload/management routes (`/documents/*`)
- `src/api/query.py` - Query processing routes (`/query`)
- `src/api/health.py` - Health check routes (`/health/*`)
- `src/api/models.py` - Pydantic request/response models
- `src/api/exceptions.py` - Custom exceptions and error handlers
- `src/main.py` - FastAPI app initialization

**Resilience & Health**

- `src/resilience/circuit_breaker.py::CircuitBreaker.call()` - Circuit breaker pattern
- `src/resilience/health_probes.py::HealthProbe` - Kubernetes-style health checks

**Gradio Web UI (Phase 10)**

- `src/ui/gradio_app.py::create_gradio_app()` - Main Gradio application factory
- `src/ui/gradio_app.py::launch_app()` - Launch UI with configurable parameters
- `src/ui/api_client.py::APIClient` - HTTP client for backend API communication
- `src/ui/components/document_manager.py::create_document_manager()` - Document upload/management UI
- `src/ui/components/chat_interface.py::create_chat_interface()` - Chat interface with RAG queries
- `src/ui/components/utils.py` - Utility functions (formatting, validation, etc.)
- `demos/launch_ui.py` - Standalone launcher script with CLI args

### Task-to-File Mapping

**"Add a new API endpoint"**
→ Start in `src/api/` (create new router or add to existing)
→ Define models in `src/api/models.py`
→ Add tests in `tests/integration/test_api_integration.py`

**"Modify document processing"**
→ Main logic: `src/pipeline/document_processor.py::DocumentProcessor`
→ Chunking: `src/pipeline/chunker.py::DocumentChunker`
→ Tests: `tests/unit/test_document_processor.py`, `tests/unit/test_chunker.py`

**"Change search behavior"**
→ Search logic: `src/retrieval/searcher.py::SemanticSearcher`
→ Indexing: `src/retrieval/indexer.py::DocumentIndexer`
→ Tests: `tests/unit/test_searcher.py`, `tests/unit/test_indexer.py`

**"Adjust LLM/Agent behavior"**
→ Agent setup: `src/agent/rag_agent.py::create_rag_agent()`
→ LLM interface: `src/ai_models/litellm_interface.py::LiteLLMInterface`
→ Circuit breaker: `src/resilience/circuit_breaker.py::CircuitBreaker`
→ Tests: `tests/unit/test_rag_agent.py`, `tests/unit/test_litellm_interface.py`

**"Update configuration"**
→ Settings class: `src/config/settings.py::Settings`
→ Environment variables: `.env` file
→ Tests: `tests/unit/test_config.py`

**"Fix health checks"**
→ Health probes: `src/resilience/health_probes.py`
→ Health API: `src/api/health.py`
→ Tests: `tests/unit/test_health_probes.py`, `tests/integration/test_api_integration.py`

**"Modify Gradio UI"**
→ Main app: `src/ui/gradio_app.py`
→ Document management: `src/ui/components/document_manager.py`
→ Chat interface: `src/ui/components/chat_interface.py`
→ API client: `src/ui/api_client.py`
→ Tests: `tests/ui/test_gradio_app.py`

**"Add new UI component"**
→ Create new file in `src/ui/components/`
→ Import and integrate in `src/ui/gradio_app.py::create_gradio_app()`
→ Add utility functions to `src/ui/components/utils.py` if needed
→ Add tests in `tests/ui/`

## Quick Start Commands

### Development & Testing

```bash
# Run dev server with hot reload
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
# or: task dev

# Run all tests with coverage
uv run pytest tests/ -v --cov=src --cov-report=term-missing
# or: task test

# Run single test file or function
uv run pytest tests/unit/test_chunker.py -v
uv run pytest tests/unit/test_chunker.py::test_function_name -v

# Run specific test categories
uv run pytest tests/unit/ -v              # Unit tests only
uv run pytest tests/integration/ -v       # Integration tests
uv run pytest tests/e2e/ -v               # End-to-end tests
```

### Code Quality

```bash
# Check code style (must pass before commits)
uv run ruff check src/ tests/
uv run black --check src/ tests/
# or: task lint

# Auto-fix code style issues
uv run ruff check --fix src/ tests/
uv run black src/ tests/
# or: task format

# Type checking
uv run mypy src/
# or: task type-check

# Pre-commit hooks (runs on every commit)
uv run pre-commit run --all-files
# or: task pre-commit
```

### Service Management

```bash
task start          # Start all services (Elasticsearch + App)
task stop           # Stop all services
task logs           # View logs
task health         # Check system health

# Gradio UI (Phase 10)
task ui:dev         # Start UI in development mode (localhost:7860)
task ui:start       # Start UI in production mode (0.0.0.0:7860)
```

## Code Style Rules

### Python Basics

- **Python**: 3.11+
- **Line length**: 100 characters max
- **String quotes**: Use double quotes for strings (enforced by Black)
- **Indentation**: 4 spaces (no tabs)

### Imports

- **Style**: Absolute imports from `src/` (e.g., `from src.config.settings import get_settings`)
- **Sorting**: Ruff with isort profile (auto-sorted on commit)
- **Order**: stdlib → third-party → local (separated by blank lines)

```python
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config.settings import get_settings
from src.retrieval.searcher import SemanticSearcher
```

### Type Hints

- **Policy**: Preferred but not strictly enforced (`disallow_untyped_defs = false`)
- **Modern syntax**: Use `list[str]`, `dict[str, int]` instead of `List[str]`, `Dict[str, int]`
- **Imports**: Use `from typing import Any` for `Any` type, `from collections.abc import Callable` for callables

```python
def process_documents(files: list[Path]) -> dict[str, Any]:
    """Good: Modern type hints."""
    pass

def get_callback() -> Callable[[str], None]:
    """Good: Use collections.abc for Callable."""
    pass
```

### Naming Conventions

- **Functions/variables**: `snake_case` (e.g., `document_store`, `process_file`)
- **Classes**: `PascalCase` (e.g., `SemanticSearcher`, `DocumentProcessor`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`)
- **Private**: Prefix with `_` (e.g., `_processing_status`, `_cleanup()`)
- **Descriptive names**: Prefer clarity over brevity (e.g., `document_store` not `ds`)

### Error Handling

- **Custom exceptions**: Use from `src.api.exceptions` (e.g., `DocumentProcessingError`, `FileValidationError`)
- **Logging**: Always log exceptions with context and `exc_info=True`

```python
try:
    result = process_document(file_path)
except Exception as e:
    logger.error(f"Failed to process {filename}: {e}", exc_info=True)
    raise DocumentProcessingError(f"Processing failed: {str(e)}") from e
```

### Documentation

- **Docstrings**: Required for all public functions/classes
- **Format**: Google-style with Args/Returns/Raises sections

```python
def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    """Perform hybrid search combining vector and keyword search.

    Args:
        query: Search query string
        top_k: Number of results to return (default: 5)

    Returns:
        List of result dictionaries with text, score, and metadata

    Raises:
        SearchError: If search fails or connection to Elasticsearch is lost
    """
```

- **Inline comments**: For complex logic, explain "why" not "what"

### Logging

- **Logger**: Module-level logger: `logger = logging.getLogger(__name__)`
- **Levels**:
  - `DEBUG`: Detailed diagnostic info
  - `INFO`: Key operations and flow (e.g., "Processing document X")
  - `WARNING`: Recoverable issues (e.g., "Failed to cleanup temp file")
  - `ERROR`: Operation failures (e.g., "Failed to index document")

```python
logger.info(f"Processing uploaded file: {filename}")
logger.debug(f"File validation passed: {filename} ({file_size} bytes)")
logger.error(f"Failed to process {filename}: {e}", exc_info=True)
```

## Architecture Overview

### Key Components (src/)

```
src/
├── main.py                  # FastAPI app entry point
├── agent/                   # Google ADK stateless RAG agent
│   ├── rag_agent.py        # LlmAgent with retrieval tool
│   └── runner.py           # Query execution interface
├── ai_models/              # LLM interfaces
│   ├── embedder.py         # Text embeddings (LiteLLM)
│   └── litellm_interface.py # Chat completions with circuit breaker
├── api/                    # FastAPI endpoints
│   ├── documents.py        # Document upload/management
│   ├── query.py            # Query processing
│   ├── health.py           # Health checks
│   ├── models.py           # Pydantic request/response models
│   └── exceptions.py       # Custom exceptions & handlers
├── config/                 # Configuration management
│   ├── settings.py         # Pydantic settings (singleton pattern)
│   ├── base.py             # Base config class
│   └── secrets.py          # Secret handling utilities
├── pipeline/               # Document ingestion
│   ├── document_processor.py  # Docling conversion
│   ├── chunker.py          # Text chunking (Haystack)
│   └── ingestion.py        # Pipeline orchestration
├── retrieval/              # Elasticsearch integration
│   ├── elasticsearch_client.py # Singleton client wrapper
│   ├── indexer.py          # Document indexing
│   ├── searcher.py         # Hybrid search (vector + BM25)
│   └── index_manager.py    # Index management
├── resilience/             # Resilience patterns
│   ├── circuit_breaker.py  # Circuit breaker for LLM
│   └── health_probes.py    # Kubernetes-style health checks
└── ui/                     # Gradio web interface (Phase 10)
    ├── gradio_app.py       # Main Gradio application
    ├── api_client.py       # HTTP client for backend API
    └── components/         # UI component modules
        ├── document_manager.py  # Document upload/management UI
        ├── chat_interface.py    # Chat interface with RAG
        └── utils.py        # Utility functions (formatting, validation)
```

### Important Patterns

**Singleton Pattern**: Used for `ElasticsearchClient` and `Settings`

```python
from src.retrieval.elasticsearch_client import get_elasticsearch_client
es_client = get_elasticsearch_client()  # Returns singleton instance
```

**Configuration**: All config via `Settings` (environment variables or .env)

```python
from src.config.settings import get_settings
settings = get_settings()  # Returns singleton
api_key = settings.llm.api_key.get_secret_value()  # SecretStr
```

**Stateless Agent**: No conversation memory, each query is independent

```python
from src.agent.rag_agent import create_rag_agent
agent, get_sources = create_rag_agent()  # Fresh agent instance
response = agent.generate_text("What is...?")
sources = get_sources()  # Get last retrieval sources
```

**Circuit Breaker**: Protects against failing LLM services

- States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing)
- Failures trigger OPEN state, preventing cascade failures

### Data Flow

**Document Ingestion**: File → Docling → Chunks → Embeddings → Elasticsearch
**Query Processing**: Query → Hybrid Search → Context → LLM → Answer + Sources
**UI Workflow**: Gradio UI (localhost:7860) → HTTP → FastAPI Backend (localhost:8000) → ES/LLM

## Configuration

Settings in `.env` file (see `.env.example`):

```bash
# LLM Configuration (LMStudio or other)
EMBEDDER__BASE_URL=http://localhost:1234/v1
EMBEDDER__MODEL=text-embedding-nomic-embed-text-v1.5
LLM__BASE_URL=http://localhost:1234/v1
LLM__MODEL=qwen2.5-14b-instruct

# Elasticsearch
ELASTICSEARCH__HOST=elasticsearch
ELASTICSEARCH__PORT=9200
ELASTICSEARCH__INDEX=documents

# Application
APP__LOG_LEVEL=INFO
APP__ENVIRONMENT=development
```

## Testing Strategy

- **Unit tests** (`tests/unit/`): Test individual components in isolation
- **Integration tests** (`tests/integration/`): Test component interactions (requires Elasticsearch)
- **E2E tests** (`tests/e2e/`): Test complete workflows via API

**Pre-commit hook**: Runs unit tests automatically on commit

## Common Tasks

**Add new API endpoint**:

1. Define route in `src/api/` router
2. Create Pydantic models in `src/api/models.py`
3. Add tests in `tests/unit/` and `tests/integration/`
4. Update API docs

**Modify document processing**:

1. Update `src/pipeline/document_processor.py` or `src/pipeline/chunker.py`
2. Add unit tests
3. Test with demo: `task demo-phase3`

**Change search behavior**:

1. Modify `src/retrieval/searcher.py`
2. Update tests in `tests/unit/test_searcher.py`
3. Test with: `task demo-phase5`

**Modify Gradio UI**:

1. Update relevant component in `src/ui/components/`
2. Update `src/ui/gradio_app.py` if adding new components
3. Add tests in `tests/ui/test_gradio_app.py`
4. Test with: `task ui:dev`

## Reference Documentation

- **[GEMINI.md](./GEMINI.md)**: Technical deep dive (architecture, components, data flows)
- **[README.md](./README.md)**: Project overview and getting started
- **[API.md](./docs/API.md)**: Complete API reference
- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)**: Detailed architecture documentation
- **[CONFIGURATION.md](./docs/CONFIGURATION.md)**: Configuration guide
- **[UI_GUIDE.md](./docs/UI_GUIDE.md)**: Gradio web interface user guide (Phase 10)
- **[Taskfile.yml](./Taskfile.yml)**: All available tasks

## Gradio Web UI (Phase 10)

### Architecture

The Gradio UI is a **standalone web application** that communicates with the FastAPI backend via HTTP:

- **UI Server**: Runs on `localhost:7860` (configurable)
- **API Backend**: Connects to `localhost:8000` (configurable)
- **Communication**: HTTP REST API calls (no direct DB/ES access)
- **State**: Session-based (chat history maintained in Gradio State)

### Key Components

**Main Application** (`src/ui/gradio_app.py`):

- `create_gradio_app()` - Factory function that builds the full Gradio interface
- Two-tab layout: "Document Management" and "Chat"
- System status accordion with health monitoring
- Custom CSS styling and Gradio Soft theme

**Document Manager** (`src/ui/components/document_manager.py`):

- File upload with drag & drop (supports .txt, .pdf, .html, .md, .docx)
- Document table with pagination (20 documents per page)
- Delete document by ID functionality
- Upload progress tracking with Gradio Progress component

**Chat Interface** (`src/ui/components/chat_interface.py`):

- Chatbot component with message history (max 50 messages, FIFO)
- Source citations in expandable accordion
- Top-K slider for tuning number of retrieved documents (1-20)
- Clear chat functionality
- Document availability warnings

**API Client** (`src/ui/api_client.py`):

- HTTP client with automatic retry (exponential backoff)
- Methods: `upload_document()`, `list_documents()`, `delete_document()`, `query()`, `health_check()`
- Error handling and logging

**Utilities** (`src/ui/components/utils.py`):

- File validation (type, size, existence checks)
- Formatting functions (file size, timestamps, text truncation)
- Constants (max file size, allowed extensions)

### Launching the UI

**Development mode** (localhost only):

```bash
task ui:dev
# or: uv run python demos/launch_ui.py --debug
```

**Production mode** (accessible from network):

```bash
task ui:start
# or: uv run python demos/launch_ui.py --host 0.0.0.0 --port 7860
```

**Custom configuration**:

```bash
uv run python demos/launch_ui.py \
  --api-url http://localhost:8000 \
  --host 0.0.0.0 \
  --port 7860 \
  --share  # Create public Gradio link
```

### Important Notes

**No Direct Database Access**: The UI never directly accesses Elasticsearch or the database. All operations go through the FastAPI backend API.

**CORS**: The FastAPI backend must have CORS enabled for the UI to work (already configured with `allow_origins=["*"]`).

**Session State**: Chat history is maintained per-session in Gradio State. Each browser tab/session is independent.

**File Uploads**: Files are uploaded to the API backend via multipart/form-data. The UI handles validation before sending.

**Error Handling**: The API client includes automatic retry with exponential backoff for transient failures.

### Testing the UI

**Unit tests**:

```bash
uv run pytest tests/ui/test_gradio_app.py -v
```

**Manual testing**:

1. Start backend: `task start`
2. Start UI: `task ui:dev`
3. Open browser to <http://localhost:7860>
4. Test upload, chat, delete workflows

See `docs/UI_GUIDE.md` for complete user documentation.

## Troubleshooting

**Type errors after changes**: Run `uv run mypy src/` to check
**Tests failing**: Ensure Elasticsearch is running (`task start`)
**Import errors**: Use absolute imports from `src/`, check `pythonpath` in pytest config
**Pre-commit issues**: Run `task format` then `task pre-commit` to fix
**UI not connecting to API**: Check CORS settings in `src/main.py`, verify API is running on correct port
**UI import errors in IDE**: Expected - Gradio is installed but may not be in IDE's Python path (works at runtime)
