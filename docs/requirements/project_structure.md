# 9. Project Structure

```
elastic_rag/
├── docs/
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   └── API.md
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   └── adk_agent.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── document_processor.py
│   │   ├── chunker.py
│   │   └── indexer.py
│   ├── retrieval/
│   │   ├── __init__.py
│   │   └── elasticsearch_retriever.py
│   ├── llm/
│   │   ├── __init__.py
│   │   └── litellm_interface.py
│   ├── resilience/
│   │   ├── __init__.py
│   │   ├── circuit_breaker.py
│   │   └── health_probes.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── health.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── base.py
│   │   └── secrets.py
│   └── main.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── Taskfile.yml
├── pyproject.toml
├── uv.lock
├── .env.example
├── .env  # gitignored
├── .gitignore
└── README.md
```
