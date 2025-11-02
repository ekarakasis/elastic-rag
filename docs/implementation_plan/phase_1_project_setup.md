# 4. Phase 1: Project Setup & Infrastructure

**Goal:** Establish project foundation with proper tooling, structure, and containerization.

**Duration:** 3-5 days
**Status:** ✅ COMPLETED
**Completed:** October 20, 2025

### 4.1 Development Environment Setup

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 1.1.1 | Install and configure `uv` package manager | 🔴 P0 | ✅ | Pre-installed |
| 1.1.2 | Install Docker Desktop and verify installation | 🔴 P0 | ✅ | Pre-installed |
| 1.1.3 | Install Task (Taskfile) runner | 🔴 P0 | ✅ | Pre-installed |
| 1.1.4 | Install LMStudio and required models | 🔴 P0 | ✅ | Pre-installed with 9 models |
| 1.1.5 | Configure LMStudio server on localhost:1234 | 🔴 P0 | ✅ | Verified - API responding |

**Verification Steps:**

- [ ] `uv --version` returns valid version
- [ ] `docker --version` and `docker compose version` work
- [ ] `task --version` returns valid version
- [ ] LMStudio API responds at `http://localhost:1234/v1/models`
- [ ] Can list loaded models via API

---

### 4.2 Project Structure Creation

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 1.2.1 | Create base directory structure | 🔴 P0 | ✅ | Complete with all subdirectories |
| 1.2.2 | Initialize Git repository | 🔴 P0 | ✅ | Pre-initialized |
| 1.2.3 | Create `.gitignore` file | 🔴 P0 | ✅ | Python, Docker, env exclusions |
| 1.2.4 | Create `README.md` skeleton | 🟡 P1 | ✅ | Comprehensive documentation |
| 1.2.5 | Set up `docs/` directory with initial files | 🟡 P1 | ✅ | ARCHITECTURE.md, API.md added |

**Directory Structure to Create:**

```
elastic_rag/
├── docs/
│   ├── REQUIREMENTS.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── ARCHITECTURE.md (placeholder)
│   └── API.md (placeholder)
├── src/
│   ├── __init__.py
│   ├── main.py (placeholder)
│   ├── agent/
│   │   └── __init__.py
│   ├── pipeline/
│   │   └── __init__.py
│   ├── retrieval/
│   │   └── __init__.py
│   ├── llm/
│   │   └── __init__.py
│   ├── resilience/
│   │   └── __init__.py
│   ├── api/
│   │   └── __init__.py
│   └── config/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
└── .gitignore
```

**Verification Steps:**

- [ ] All directories exist with `__init__.py` files
- [ ] Git repository initialized
- [ ] `.gitignore` excludes `.env` and common Python artifacts
- [ ] README.md contains project name and basic description

---

### 4.3 Python Project Configuration

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 1.3.1 | Create `pyproject.toml` with project metadata | 🔴 P0 | ✅ | Complete with metadata |
| 1.3.2 | Add core dependencies to `pyproject.toml` | 🔴 P0 | ✅ | All dependencies added |
| 1.3.3 | Run `uv sync` to create virtual environment | 🔴 P0 | ✅ | 151 packages installed |
| 1.3.4 | Configure development tools (black, ruff, mypy) | 🟡 P1 | ✅ | Configured in pyproject.toml |
| 1.3.5 | Create `.python-version` file | 🟡 P1 | ✅ | Python 3.11 specified |

**Core Dependencies (pyproject.toml):**

```toml
[project]
name = "elastic-rag"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "elasticsearch>=8.11.0",
    "haystack-ai>=2.0.0",
    "elasticsearch-haystack>=1.0.0",  # Haystack Elasticsearch integration
    "litellm>=1.17.0",
    "google-adk>=0.1.0",  # Verify exact package name
    "docling>=0.1.0",  # Verify exact package name
    "tenacity>=8.2.0",  # For circuit breaker
    "httpx>=0.25.0",
    "python-multipart>=0.0.6",  # For file uploads
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.11.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]
```

**Verification Steps:**

- [ ] `pyproject.toml` validates without errors
- [ ] `uv sync` completes successfully
- [ ] Virtual environment created at `.venv/`
- [ ] `uv.lock` file generated
- [ ] Can activate venv and import key packages

---

### 4.4 Docker Setup

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 1.4.1 | Create `docker/Dockerfile` with multi-stage build | 🔴 P0 | ✅ | Multi-stage with uv |
| 1.4.2 | Create `docker/docker-compose.yml` | 🔴 P0 | ✅ | ES 9.1.5-arm64 + Kibana + App |
| 1.4.3 | Create `.dockerignore` file | 🟡 P1 | ✅ | Optimized exclusions |
| 1.4.4 | Test Docker build locally | 🔴 P0 | ✅ | Build successful |
| 1.4.5 | Configure volume mounts for persistence | 🟡 P1 | ✅ | ES data volume configured |

**Dockerfile Structure (docker/Dockerfile):**

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /app
# Install uv
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ /app/src/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml Structure:**

```yaml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.1
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1024m -Xmx1024m
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ELASTICSEARCH__HOST=elasticsearch
    depends_on:
      elasticsearch:
        condition: service_healthy
    env_file:
      - ../.env

volumes:
  es_data:
```

**Note:** Haystack 2.0 supports Elasticsearch 8.x. The version 8.11.1 is recommended for compatibility.

**Verification Steps:**

- [ ] `docker build -f docker/Dockerfile .` succeeds
- [ ] `docker compose -f docker/docker-compose.yml up` starts services
- [ ] Elasticsearch accessible at <http://localhost:9200>
- [ ] App container starts without errors

---

### 4.5 Taskfile Configuration

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 1.5.1 | Create `Taskfile.yml` in project root | 🔴 P0 | ✅ | Complete with 20+ tasks |
| 1.5.2 | Implement `task build` command | 🔴 P0 | ✅ | Tested and working |
| 1.5.3 | Implement `task start` command | 🔴 P0 | ✅ | Services starting successfully |
| 1.5.4 | Implement `task stop` command | 🔴 P0 | ✅ | Implemented |
| 1.5.5 | Implement `task dev` command | 🟡 P1 | ✅ | Hot reload configured |
| 1.5.6 | Implement `task test` command | 🟡 P1 | ✅ | With coverage support |
| 1.5.7 | Implement `task clean` command | 🟢 P2 | ✅ | Complete cleanup |
| 1.5.8 | Implement `task logs` command | 🟢 P2 | ✅ | Multiple log variants |

**Taskfile.yml Structure:**

```yaml
version: '3'

tasks:
  build:
    desc: Build Docker images
    cmds:
      - docker compose -f docker/docker-compose.yml build

  start:
    desc: Start all services
    cmds:
      - docker compose -f docker/docker-compose.yml up -d
      - echo "Services started. App: http://localhost:8000, Elasticsearch: http://localhost:9200"

  stop:
    desc: Stop all services
    cmds:
      - docker compose -f docker/docker-compose.yml down

  dev:
    desc: Start in development mode with hot reload
    cmds:
      - uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

  test:
    desc: Run test suite
    cmds:
      - uv run pytest tests/ -v

  clean:
    desc: Clean up Docker resources
    cmds:
      - docker compose -f docker/docker-compose.yml down -v
      - docker system prune -f

  logs:
    desc: View service logs
    cmds:
      - docker compose -f docker/docker-compose.yml logs -f
```

**Verification Steps:**

- [ ] `task --list` shows all defined tasks
- [ ] `task build` successfully builds images
- [ ] `task start` starts services in detached mode
- [ ] `task stop` stops all services
- [ ] `task logs` displays service logs

---

### 4.6 Phase 1 Completion Checklist

- [x] All development tools installed and verified
- [x] Project directory structure created
- [x] Git repository initialized with proper `.gitignore`
- [x] Python environment configured with `uv`
- [x] Core dependencies installed and locked (151 packages)
- [x] Docker configuration complete and tested
- [x] Taskfile commands working (20+ commands)
- [x] LMStudio server running and accessible (9 models loaded)
- [x] Can build and start Docker containers

**Phase 1 Exit Criteria:**

- ✅ Docker Compose successfully starts all services
- ✅ Elasticsearch health check passes (status: green)
- ✅ FastAPI app container runs with health endpoints
- ✅ All Taskfile commands execute without errors
- ✅ Kibana accessible at <http://localhost:5601>
- ✅ API docs available at <http://localhost:8000/docs>

**Completed:** October 20, 2025
