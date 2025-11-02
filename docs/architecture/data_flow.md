# 4. Data Flow Diagrams

### 4.1 Document Ingestion Pipeline

**Purpose:** Transform documents into searchable chunks with embeddings

#### 4.1.1 High-Level Ingestion Flow

```mermaid
graph LR
    DOC[Document File] --> PROC[Document Processor]
    PROC --> TEXT[Plain Text]
    TEXT --> CHUNK[Chunker]
    CHUNK --> CHUNKS[Text Chunks]
    CHUNKS --> EMBED[Embedder]
    EMBED --> VECTORS[Chunks with Vectors]
    VECTORS --> INDEX[Indexer]
    INDEX --> ES[Elasticsearch]
```

#### 4.1.2 Detailed Ingestion Sequence

```mermaid
sequenceDiagram
    participant User
    participant IngestionPipeline
    participant DocumentProcessor
    participant Chunker
    participant Embedder
    participant Indexer
    participant Elasticsearch

    User->>IngestionPipeline: ingest_document(file_path)

    Note over IngestionPipeline: Step 1: Process Document
    IngestionPipeline->>DocumentProcessor: process_document(file_path)
    DocumentProcessor->>DocumentProcessor: Docling conversion
    DocumentProcessor-->>IngestionPipeline: ProcessedDocument(text, metadata)

    Note over IngestionPipeline: Step 2: Chunk Text
    IngestionPipeline->>Chunker: chunk_document(processed_doc)
    Chunker->>Chunker: Split with overlap (512 tokens)
    Chunker-->>IngestionPipeline: List[TextChunk]

    Note over IngestionPipeline: Step 3: Generate Embeddings
    IngestionPipeline->>Embedder: embed_batch(chunk_texts)
    Embedder->>Embedder: BGE-M3 vectorization
    Embedder-->>IngestionPipeline: List[Vector(1024 dims)]

    Note over IngestionPipeline: Step 4: Index to Elasticsearch
    IngestionPipeline->>Indexer: index_documents(chunks_with_vectors)
    Indexer->>Elasticsearch: Bulk index operation
    Elasticsearch-->>Indexer: Success response
    Indexer-->>IngestionPipeline: Indexed count
    IngestionPipeline-->>User: Success message
```

#### 4.1.3 Document Processor Details

```mermaid
graph TB
    INPUT[Input File]
    CHECK{Check Format}
    PDF[PDF Handler]
    DOCX[DOCX Handler]
    HTML[HTML Handler]
    TXT[TXT Handler]
    MD[Markdown Handler]
    DOCLING[Docling Converter]
    TEXT[Extracted Text]
    META[Metadata Extraction]
    OUTPUT[ProcessedDocument]

    INPUT --> CHECK
    CHECK -->|.pdf| PDF
    CHECK -->|.docx| DOCX
    CHECK -->|.html| HTML
    CHECK -->|.txt| TXT
    CHECK -->|.md| MD
    PDF --> DOCLING
    DOCX --> DOCLING
    HTML --> DOCLING
    TXT --> TEXT
    MD --> TEXT
    DOCLING --> TEXT
    TEXT --> META
    META --> OUTPUT
```

#### 4.1.4 Chunking Strategy

```mermaid
graph TB
    DOC[Document Text]
    TOKENIZE[Tokenize Text]
    SPLIT{Split by Size}
    CHUNK1[Chunk 1: tokens 0-512]
    CHUNK2[Chunk 2: tokens 462-974]
    CHUNK3[Chunk 3: tokens 924-1436]
    OVERLAP[Overlap: 50 tokens]
    OUTPUT[List of Chunks]

    DOC --> TOKENIZE
    TOKENIZE --> SPLIT
    SPLIT --> CHUNK1
    SPLIT --> CHUNK2
    SPLIT --> CHUNK3
    CHUNK1 --> OVERLAP
    CHUNK2 --> OVERLAP
    CHUNK3 --> OVERLAP
    OVERLAP --> OUTPUT
```

### 4.2 Query Processing Pipeline

**Purpose:** Retrieve relevant context and generate answers

#### 4.2.1 High-Level Query Flow

```mermaid
graph LR
    QUERY[User Query] --> RUNNER[Agent Runner]
    RUNNER --> SEARCH[Hybrid Search]
    SEARCH --> CONTEXT[Retrieved Context]
    CONTEXT --> AGENT[RAG Agent]
    AGENT --> LLM[LLM Interface]
    LLM --> CB[Circuit Breaker]
    CB --> LMSTUDIO[LMStudio]
    LMSTUDIO --> RESPONSE[Generated Answer]
    RESPONSE --> USER[User]
```

#### 4.2.2 Detailed Query Sequence

```mermaid
sequenceDiagram
    participant User
    participant SimpleRAGRunner
    participant RAGAgent
    participant Searcher
    participant Embedder
    participant Elasticsearch
    participant CircuitBreaker
    participant LLMInterface
    participant LMStudio

    User->>SimpleRAGRunner: query(question)

    Note over SimpleRAGRunner: Create stateless session
    SimpleRAGRunner->>SimpleRAGRunner: generate_session_id()

    Note over SimpleRAGRunner: Step 1: Retrieve Context
    SimpleRAGRunner->>RAGAgent: process_query(question)
    RAGAgent->>Searcher: hybrid_search(question)

    Note over Searcher: Vector Search Component
    Searcher->>Embedder: embed(question)
    Embedder-->>Searcher: query_vector[1024]
    Searcher->>Elasticsearch: knn_search(query_vector, top_k=5)
    Elasticsearch-->>Searcher: vector_results[]

    Note over Searcher: Keyword Search Component
    Searcher->>Elasticsearch: bm25_search(question)
    Elasticsearch-->>Searcher: keyword_results[]

    Note over Searcher: Combine Results
    Searcher->>Searcher: normalize_scores()
    Searcher->>Searcher: combine_scores(0.7 vector, 0.3 keyword)
    Searcher-->>RAGAgent: ranked_chunks[top_k]

    Note over RAGAgent: Step 2: Generate Answer
    RAGAgent->>RAGAgent: build_prompt(question, chunks)
    RAGAgent->>CircuitBreaker: call(llm.chat_completion, prompt)

    alt Circuit State: CLOSED
        CircuitBreaker->>LLMInterface: chat_completion(prompt)
        LLMInterface->>LMStudio: POST /v1/chat/completions
        LMStudio-->>LLMInterface: response_text
        LLMInterface-->>CircuitBreaker: success
        CircuitBreaker->>CircuitBreaker: record_success()
        CircuitBreaker-->>RAGAgent: response_text
    else Circuit State: OPEN
        CircuitBreaker-->>RAGAgent: CircuitBreakerError
        RAGAgent->>RAGAgent: fallback_response()
    end

    RAGAgent-->>SimpleRAGRunner: answer_with_citations
    SimpleRAGRunner-->>User: formatted_response
```

#### 4.2.3 Hybrid Search Algorithm

```mermaid
graph TB
    QUERY[User Query]
    EMBED[Embed Query]
    VECTOR_SEARCH[Vector Search]
    KEYWORD_SEARCH[BM25 Search]
    VECTOR_RESULTS[Vector Results]
    KEYWORD_RESULTS[Keyword Results]
    NORMALIZE[Normalize Scores]
    COMBINE[Combine Scores]
    RANK[Rank Results]
    TOPK[Return Top-K]

    QUERY --> EMBED
    QUERY --> KEYWORD_SEARCH
    EMBED --> VECTOR_SEARCH
    VECTOR_SEARCH --> VECTOR_RESULTS
    KEYWORD_SEARCH --> KEYWORD_RESULTS
    VECTOR_RESULTS --> NORMALIZE
    KEYWORD_RESULTS --> NORMALIZE
    NORMALIZE --> COMBINE
    COMBINE --> RANK
    RANK --> TOPK

    Note1[Weight: 0.7]
    Note2[Weight: 0.3]
    VECTOR_RESULTS -.-> Note1
    KEYWORD_RESULTS -.-> Note2
```

### 4.3 Circuit Breaker Pattern

**Purpose:** Prevent cascading failures in LLM communication

#### 4.3.1 Circuit Breaker State Machine

```mermaid
stateDiagram-v2
    [*] --> CLOSED
    CLOSED --> OPEN: failures >= threshold (5)
    OPEN --> HALF_OPEN: timeout expired (60s)
    HALF_OPEN --> CLOSED: success_count >= max_calls (3)
    HALF_OPEN --> OPEN: any failure
    CLOSED --> CLOSED: success
    OPEN --> OPEN: reject all calls
```

#### 4.3.2 Circuit Breaker Call Flow

```mermaid
sequenceDiagram
    participant Caller
    participant CircuitBreaker
    participant Function
    participant State

    Caller->>CircuitBreaker: call(function, args)
    CircuitBreaker->>State: get_state()

    alt State == CLOSED
        CircuitBreaker->>Function: execute(*args, **kwargs)
        alt Success
            Function-->>CircuitBreaker: result
            CircuitBreaker->>State: record_success()
            CircuitBreaker-->>Caller: result
        else Failure
            Function-->>CircuitBreaker: exception
            CircuitBreaker->>State: record_failure()
            CircuitBreaker->>State: check_threshold()
            alt failures >= threshold
                State->>State: transition to OPEN
            end
            CircuitBreaker-->>Caller: raise exception
        end
    else State == OPEN
        CircuitBreaker->>State: check_timeout()
        alt timeout expired
            State->>State: transition to HALF_OPEN
            CircuitBreaker->>Function: execute(*args, **kwargs)
            alt Success
                Function-->>CircuitBreaker: result
                State->>State: increment half_open_calls
                alt half_open_calls >= max
                    State->>State: transition to CLOSED
                end
                CircuitBreaker-->>Caller: result
            else Failure
                Function-->>CircuitBreaker: exception
                State->>State: transition to OPEN
                CircuitBreaker-->>Caller: raise exception
            end
        else timeout not expired
            CircuitBreaker-->>Caller: CircuitBreakerError
        end
    else State == HALF_OPEN
        CircuitBreaker->>Function: execute(*args, **kwargs)
        alt Success
            Function-->>CircuitBreaker: result
            State->>State: increment half_open_calls
            alt half_open_calls >= max
                State->>State: transition to CLOSED
            end
            CircuitBreaker-->>Caller: result
        else Failure
            Function-->>CircuitBreaker: exception
            State->>State: transition to OPEN
            CircuitBreaker-->>Caller: raise exception
        end
    end
```

### 4.4 Health Monitoring System

**Purpose:** Kubernetes-style health probes for system monitoring

#### 4.4.1 Health Probe Types

```mermaid
graph TB
    MONITOR[Monitoring System]
    LIVENESS[Liveness Probe]
    READINESS[Readiness Probe]
    STARTUP[Startup Probe]

    MONITOR --> LIVENESS
    MONITOR --> READINESS
    MONITOR --> STARTUP

    LIVENESS --> L_CHECK{App Running?}
    L_CHECK -->|Yes| L_OK[200 OK]
    L_CHECK -->|No| L_FAIL[500 Error]

    READINESS --> R_CHECK{Ready for Traffic?}
    R_CHECK --> R_ES{Elasticsearch OK?}
    R_CHECK --> R_LLM{LMStudio OK?}
    R_CHECK --> R_CB{Circuit Closed?}
    R_ES -->|Yes| R_OK[200 OK]
    R_LLM -->|Yes| R_OK
    R_CB -->|Yes| R_OK
    R_ES -->|No| R_FAIL[503 Unavailable]
    R_LLM -->|No| R_FAIL
    R_CB -->|No| R_FAIL

    STARTUP --> S_CHECK{Initialized?}
    S_CHECK -->|Yes| S_OK[200 OK]
    S_CHECK -->|No| S_FAIL[503 Unavailable]
```

#### 4.4.2 Readiness Check Sequence

```mermaid
sequenceDiagram
    participant Monitor
    participant HealthProbes
    participant Elasticsearch
    participant LMStudio
    participant CircuitBreaker

    Monitor->>HealthProbes: GET /health/ready

    Note over HealthProbes: Check all dependencies

    par Check Elasticsearch
        HealthProbes->>Elasticsearch: ping()
        alt Elasticsearch available
            Elasticsearch-->>HealthProbes: pong
        else Elasticsearch unavailable
            Elasticsearch-->>HealthProbes: timeout/error
        end
    and Check LMStudio
        HealthProbes->>LMStudio: GET /v1/models
        alt LMStudio available
            LMStudio-->>HealthProbes: 200 OK
        else LMStudio unavailable
            LMStudio-->>HealthProbes: timeout/error
        end
    and Check Circuit Breaker
        HealthProbes->>CircuitBreaker: get_state()
        CircuitBreaker-->>HealthProbes: state (CLOSED/OPEN/HALF_OPEN)
    end

    Note over HealthProbes: Aggregate results

    alt All checks passed
        HealthProbes-->>Monitor: 200 OK (Ready)
    else Any check failed
        HealthProbes-->>Monitor: 503 Service Unavailable
    end
```

### 4.5 Configuration Loading

**Purpose:** Type-safe configuration with environment variables

#### 4.5.1 Configuration Hierarchy

```mermaid
graph TB
    ENV[Environment Variables]
    DOTENV[.env File]
    DEFAULTS[Default Values]
    PYDANTIC[Pydantic Settings]
    VALIDATION[Type Validation]
    SETTINGS[Settings Object]

    ENV --> PYDANTIC
    DOTENV --> PYDANTIC
    DEFAULTS --> PYDANTIC
    PYDANTIC --> VALIDATION
    VALIDATION --> SETTINGS

    SETTINGS --> APP[AppSettings]
    SETTINGS --> LLM[LMStudioSettings]
    SETTINGS --> ES[ElasticsearchSettings]
    SETTINGS --> CHUNK[ChunkingSettings]
    SETTINGS --> RETR[RetrievalSettings]
    SETTINGS --> CB[CircuitBreakerSettings]
    SETTINGS --> HEALTH[HealthSettings]
```

#### 4.5.2 Configuration Loading Sequence

```mermaid
sequenceDiagram
    participant Application
    participant get_settings
    participant Pydantic
    participant dotenv
    participant Environment

    Application->>get_settings: get_settings()

    alt First call (singleton)
        get_settings->>Pydantic: Settings()
        Pydantic->>dotenv: load_dotenv()
        dotenv->>Environment: read .env file
        Environment-->>dotenv: env vars
        dotenv-->>Pydantic: loaded

        Pydantic->>Pydantic: read environment variables
        Pydantic->>Pydantic: apply defaults
        Pydantic->>Pydantic: validate types

        alt Validation success
            Pydantic-->>get_settings: Settings instance
        else Validation failure
            Pydantic-->>get_settings: ValidationError
        end

        get_settings-->>Application: Settings instance
    else Subsequent calls
        get_settings-->>Application: Cached instance
    end
```
