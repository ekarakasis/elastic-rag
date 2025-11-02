# 7. Deployment Architecture

### 7.1 Container Architecture Overview

```mermaid
graph TB
    USER[User/Client]

    subgraph DOCKER[Docker Compose Environment]
        APP[Application Container]
        ES[Elasticsearch Container]
    end

    LMS[LMStudio Host Process]

    USER -->|Port 8000| APP
    APP -->|Port 9200| ES
    APP -->|Port 1234| LMS

    ES_VOL[(ES Data Volume)]
    APP_VOL[(App Data Volume)]

    ES --> ES_VOL
    APP --> APP_VOL
```

### 7.2 Detailed Container Layout

```mermaid
graph TB
    subgraph APP_CONTAINER[Application Container - elastic_rag_app]
        PYTHON[Python 3.11 Runtime]
        SRC[Source Code /app/src]
        VENV[Virtual Environment]
        HEALTH[Health Endpoints]
        PORT8000[Exposed Port 8000]
    end

    subgraph ES_CONTAINER[Elasticsearch Container]
        ES_RUNTIME[Elasticsearch 8.x]
        ES_CONFIG[Configuration]
        ES_STORAGE[Data Storage]
        PORT9200[Exposed Port 9200]
    end

    subgraph HOST[Host Machine]
        LMS_SERVER[LMStudio Server]
        MODELS[Model Files]
        PORT1234[Port 1234]
    end

    APP_CONTAINER -->|HTTP| ES_CONTAINER
    APP_CONTAINER -->|HTTP| HOST
```

### 7.3 Network Communication Flow

```mermaid
sequenceDiagram
    participant User
    participant AppContainer
    participant ESContainer
    participant LMStudioHost

    Note over User,LMStudioHost: Deployment Network Topology

    User->>AppContainer: HTTP :8000
    AppContainer->>ESContainer: HTTP :9200 (internal)
    AppContainer->>LMStudioHost: HTTP host.docker.internal:1234

    Note over AppContainer,ESContainer: Docker internal network
    Note over AppContainer,LMStudioHost: Host network access
```

### 7.2 Docker Compose Configuration

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ELASTICSEARCH__HOST=elasticsearch
      - LMSTUDIO__BASE_URL=http://host.docker.internal:1234/v1
    depends_on:
      elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - ./data:/app/data

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  es_data:
    driver: local
```

### 7.4 Docker Compose Configuration

The above YAML defines the complete Docker Compose setup for the application.

### 7.5 Resource Requirements

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| **Application** | 1-2 cores | 2-4 GB | 1 GB |
| **Elasticsearch** | 2-4 cores | 4-8 GB | 10+ GB |
| **LMStudio** | 4-8 cores | 8-16 GB | 20+ GB |
| **Total** | 7-14 cores | 14-28 GB | 31+ GB |

### 7.6 Volume Mounts

| Volume | Purpose | Persistence |
|--------|---------|-------------|
| `es_data` | Elasticsearch indices | Docker volume |
| `./data` | Application data/cache | Host mount |
| LMStudio models | Model files | Host storage |
