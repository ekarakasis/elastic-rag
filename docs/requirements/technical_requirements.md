# 4. Technical Requirements

### 4.1 Programming Language

- **Primary Language:** Python 3.11+
- **Rationale:** Excellent ecosystem for ML/AI, strong library support

### 4.2 Core Technologies

#### 4.2.1 Agentic Framework

- **Technology:** Google ADK (Agent Development Kit)
- **Version:** Latest stable
- **Purpose:** Agent orchestration and workflow management

#### 4.2.2 LLM Interface

- **Technology:** LiteLLM
- **Version:** Latest stable
- **Purpose:** Unified API for multiple LLM providers
- **Providers Support:**
  - LMStudio (local inference - primary for v1.0)
  - OpenAI (future)
  - Anthropic (future)
  - Google Gemini (future)
  - Other providers as needed

#### 4.2.3 Document Processing

- **Technology:** Docling
- **Version:** Latest stable
- **Purpose:** Convert various document formats to text
- **Supported Formats:**
  - PDF
  - DOCX
  - PPTX
  - HTML
  - Other common document formats

#### 4.2.4 RAG Pipeline

- **Technology:** Haystack
- **Version:** Latest stable (2.x)
- **Components Used:**
  - Text chunking (DocumentSplitter)
  - Pipeline orchestration
  - Document store integration
  - Retrieval components

#### 4.2.5 Search and Storage

- **Technology:** Elasticsearch
- **Version:** 8.x
- **Purpose:** Vector and keyword search, document storage
- **Features:**
  - Dense vector search
  - BM25 keyword search
  - Hybrid search capabilities
  - Document metadata storage

#### 4.2.6 Vectorization

- **Provider:** LMStudio
- **Purpose:** Generate embeddings for documents and queries
- **Requirements:**
  - Compatible embedding model
  - Local inference capability
  - Consistent vector dimensions

### 4.3 Development Tools

#### 4.3.1 Package Manager

- **Technology:** uv
- **Purpose:** Fast Python package management
- **Features:**
  - Dependency resolution
  - Virtual environment management
  - Lock file generation

#### 4.3.2 Task Runner

- **Technology:** Taskfile (Task)
- **Purpose:** Automation of common operations
- **Required Tasks:**
  - `task start` - Start the application
  - `task stop` - Stop the application
  - `task build` - Build Docker image
  - `task dev` - Development mode
  - `task test` - Run tests
  - `task clean` - Clean up resources

### 4.4 Containerization

- **Technology:** Docker
- **Version:** Latest stable
- **Requirements:**
  - Multi-stage build for optimization
  - Docker Compose for orchestration
  - Volume mounts for data persistence
  - Health checks for services
  - Environment variable configuration
