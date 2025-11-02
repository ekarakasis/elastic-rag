# 7. System Dependencies

### 7.1 External Services

- **LMStudio:** Running locally with:
  - Embedding model loaded
  - Chat completion model loaded
  - API endpoint accessible

### 7.2 Python Packages

- google-adk (agentic framework)
- litellm (LLM interface)
- docling (document conversion)
- haystack-ai (RAG pipeline and core components)
- elasticsearch-haystack (Haystack Elasticsearch integration)
- elasticsearch (Python client - dependency of elasticsearch-haystack)
- fastapi (API framework - recommended)
- uvicorn (ASGI server)
- pydantic (data validation)
- pydantic-settings (configuration management with environment variables)
- python-dotenv (environment file loading)
- pybreaker or tenacity (circuit breaker implementation)
- Additional dependencies as identified during development
