# 6. Technology Stack

### 6.1 Core Technologies

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Language** | Python | 3.11+ | Core implementation |
| **Package Manager** | UV | Latest | Fast dependency management |
| **Task Runner** | Taskfile | Latest | Build automation |
| **Containerization** | Docker | Latest | Deployment |

### 6.2 AI/ML Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Agent Framework** | Google ADK | Agent orchestration |
| **LLM Interface** | LiteLLM | Universal LLM adapter |
| **Local LLM** | LMStudio | Local inference |
| **Embeddings** | BGE-M3 | Vector generation (1024 dims) |
| **Document Processing** | Docling | Format conversion |
| **RAG Pipeline** | Haystack 2.0 | Pipeline orchestration |

### 6.3 Storage & Search

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Vector Store** | Elasticsearch 8.x | Vector + keyword search |
| **Index Management** | Custom | Lifecycle management |
| **Search Strategy** | Hybrid | Vector (70%) + BM25 (30%) |

### 6.4 Resilience & Monitoring

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Circuit Breaker** | Custom | Failure protection |
| **Health Probes** | Kubernetes-style | System monitoring |
| **Logging** | Python logging | Observability |

### 6.5 Configuration & Testing

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Configuration** | Pydantic Settings | Type-safe config |
| **Environment** | python-dotenv | Env var loading |
| **Testing** | pytest | Test framework |
| **Async Testing** | pytest-asyncio | Async test support |
| **Mocking** | unittest.mock | Test isolation |
