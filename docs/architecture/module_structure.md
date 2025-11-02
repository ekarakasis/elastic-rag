# 5. Module Structure

### 5.1 Source Code Organization

```
src/
├── __init__.py                      # Root package
├── main.py                          # Application entry point
│
├── config/                          # Configuration layer
│   ├── __init__.py
│   ├── base.py                     # Base config classes
│   ├── settings.py                 # Pydantic settings
│   └── secrets.py                  # Secrets management
│
├── pipeline/                        # Document processing
│   ├── __init__.py
│   ├── document_processor.py       # Docling integration
│   ├── chunker.py                  # Text chunking
│   └── ingestion.py                # Pipeline orchestration
│
├── ai_models/                       # LLM integration
│   ├── __init__.py
│   ├── litellm_interface.py        # Universal LLM adapter
│   └── embedder.py                 # Embedding generation
│
├── retrieval/                       # Search & storage
│   ├── __init__.py
│   ├── elasticsearch_client.py     # ES connection
│   ├── index_manager.py            # Index lifecycle
│   ├── indexer.py                  # Document indexing
│   └── searcher.py                 # Hybrid search
│
├── agent/                           # Agent layer
│   ├── __init__.py
│   ├── rag_agent.py                # Stateless agent
│   └── runner.py                   # Execution orchestration
│
├── resilience/                      # Reliability layer
│   ├── __init__.py
│   ├── circuit_breaker.py          # Circuit breaker
│   └── health_probes.py            # Health monitoring
│
└── api/                             # REST API
    └── __init__.py
```

### 5.2 Module Dependency Graph

```mermaid
graph TB
    CONFIG[config/]
    PIPELINE[pipeline/]
    AI_MODELS[ai_models/]
    RETRIEVAL[retrieval/]
    AGENT[agent/]
    RESILIENCE[resilience/]
    API[api/]

    PIPELINE --> CONFIG
    AI_MODELS --> CONFIG
    AI_MODELS --> RESILIENCE
    RETRIEVAL --> CONFIG
    AGENT --> CONFIG
    AGENT --> AI_MODELS
    AGENT --> RETRIEVAL
    RESILIENCE --> CONFIG
    API --> AGENT
    API --> PIPELINE

    Note1[Base Layer]
    Note2[Service Layer]
    Note3[Application Layer]

    CONFIG -.-> Note1
    PIPELINE -.-> Note2
    AI_MODELS -.-> Note2
    RETRIEVAL -.-> Note2
    RESILIENCE -.-> Note2
    AGENT -.-> Note3
    API -.-> Note3
```

### 5.3 Detailed Component Diagrams

#### 5.3.1 Configuration Layer Components

```mermaid
graph TB
    APP[Application]
    GET_SETTINGS[get_settings Function]
    SETTINGS[Settings Class]

    subgraph SETTINGS_COMPONENTS[Settings Components]
        APP_SET[AppSettings]
        LLM_SET[LMStudioSettings]
        ES_SET[ElasticsearchSettings]
        CHUNK_SET[ChunkingSettings]
        RETR_SET[RetrievalSettings]
        CB_SET[CircuitBreakerSettings]
        HEALTH_SET[HealthSettings]
    end

    SECRETS[Secrets Module]
    BASE[Base Config]

    APP --> GET_SETTINGS
    GET_SETTINGS --> SETTINGS
    SETTINGS --> APP_SET
    SETTINGS --> LLM_SET
    SETTINGS --> ES_SET
    SETTINGS --> CHUNK_SET
    SETTINGS --> RETR_SET
    SETTINGS --> CB_SET
    SETTINGS --> HEALTH_SET

    SETTINGS --> SECRETS
    SETTINGS --> BASE
```

#### 5.3.2 Pipeline Layer Components

```mermaid
graph TB
    INGEST[IngestionPipeline]
    DOC_PROC[DocumentProcessor]
    CHUNKER[TextChunker]
    EMBEDDER[Embedder]

    INGEST --> DOC_PROC
    INGEST --> CHUNKER
    INGEST --> EMBEDDER

    subgraph DOC_PROC_INT[DocumentProcessor Internals]
        DOCLING[Docling Converter]
        META[Metadata Extractor]
        PROCESSED[ProcessedDocument]
    end

    subgraph CHUNKER_INT[TextChunker Internals]
        TOKENIZER[Tokenizer]
        SPLITTER[Text Splitter]
        CHUNK_OBJ[TextChunk]
    end

    DOC_PROC --> DOC_PROC_INT
    CHUNKER --> CHUNKER_INT
```

#### 5.3.3 AI Models Layer Components

```mermaid
graph TB
    LLM_INT[LLMInterface]
    EMBEDDER[Embedder]
    CB[CircuitBreaker]

    LLM_INT --> CB
    CB --> LITELLM[LiteLLM Library]
    LITELLM --> LMSTUDIO[LMStudio API]

    EMBEDDER --> LMSTUDIO

    subgraph LLM_INT_METHODS[LLMInterface Methods]
        CHAT[chat_completion]
        STREAM[chat_completion_stream]
        VALIDATE[validate_connection]
    end

    subgraph EMBEDDER_METHODS[Embedder Methods]
        EMBED_SINGLE[embed]
        EMBED_BATCH[embed_batch]
    end

    LLM_INT --> LLM_INT_METHODS
    EMBEDDER --> EMBEDDER_METHODS
```

#### 5.3.4 Retrieval Layer Components

```mermaid
graph TB
    ES_CLIENT[ElasticsearchClient]
    IDX_MGR[IndexManager]
    INDEXER[Indexer]
    SEARCHER[Searcher]

    IDX_MGR --> ES_CLIENT
    INDEXER --> ES_CLIENT
    SEARCHER --> ES_CLIENT

    ES_CLIENT --> ES[Elasticsearch]

    subgraph SEARCHER_MODES[Search Modes]
        VECTOR[vector_search]
        KEYWORD[keyword_search]
        HYBRID[hybrid_search]
    end

    subgraph INDEXER_OPS[Indexer Operations]
        INDEX_SINGLE[index_document]
        INDEX_BATCH[index_documents]
        DELETE[delete_document]
    end

    subgraph IDX_MGR_OPS[Index Manager Operations]
        CREATE[create_index]
        DELETE_IDX[delete_index]
        EXISTS[index_exists]
        MAPPINGS[get_mappings]
    end

    SEARCHER --> SEARCHER_MODES
    INDEXER --> INDEXER_OPS
    IDX_MGR --> IDX_MGR_OPS
```

#### 5.3.5 Agent Layer Components

```mermaid
graph TB
    RUNNER[SimpleRAGRunner]
    RAG_AGENT[RAGAgent]
    ADK[Google ADK]

    RUNNER --> RAG_AGENT
    RAG_AGENT --> ADK

    subgraph RUNNER_FLOW[Runner Flow]
        QUERY[query method]
        ASYNC[_query_async]
        SESSION[Session Management]
    end

    subgraph RAG_FLOW[RAG Agent Flow]
        PROCESS[process_query]
        RETRIEVE[retrieve_context]
        GENERATE[generate_answer]
        FORMAT[format_response]
    end

    RUNNER --> RUNNER_FLOW
    RAG_AGENT --> RAG_FLOW

    RETRIEVE --> SEARCHER_REF[Searcher]
    GENERATE --> LLM_REF[LLMInterface]
```

#### 5.3.6 Resilience Layer Components

```mermaid
graph TB
    CB[CircuitBreaker]
    HEALTH[HealthProbes]

    subgraph CB_COMPONENTS[Circuit Breaker Components]
        STATE[CircuitState Enum]
        CALL[call method]
        RECORD_SUCCESS[record_success]
        RECORD_FAIL[record_failure]
        GET_STATE[get_state]
    end

    subgraph HEALTH_COMPONENTS[Health Probes Components]
        LIVENESS[liveness_probe]
        READINESS[readiness_probe]
        STARTUP[startup_probe]
        CHECK_ES[check_elasticsearch]
        CHECK_LLM[check_llm]
    end

    CB --> CB_COMPONENTS
    HEALTH --> HEALTH_COMPONENTS

    CALL --> STATE
    RECORD_SUCCESS --> STATE
    RECORD_FAIL --> STATE

    READINESS --> CHECK_ES
    READINESS --> CHECK_LLM
```
