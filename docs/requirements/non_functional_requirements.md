# 6. Non-Functional Requirements

### 6.1 Performance (NFR-1)

| ID | Requirement | Phase |
|---|---|---|
| NFR-1.1 | Document ingestion shall process at least 10 pages per second | 8 |
| NFR-1.2 | Query response time shall be under 5 seconds (end-to-end) | 8 |
| NFR-1.3 | System shall support concurrent queries (minimum 5 simultaneous users) | 8 |
| NFR-1.4 | Elasticsearch indexing shall complete within 2 seconds per document chunk | 8 |
| NFR-1.5 | Health probe endpoints shall respond within 1 second | 7 |

### 6.2 Scalability (NFR-2)

| ID | Requirement | Phase |
|---|---|---|
| NFR-2.1 | System shall handle document corpus of up to 10,000 documents (v1.0) | 8 |
| NFR-2.2 | Architecture shall support horizontal scaling for future versions | 9 |
| NFR-2.3 | Vector database shall support up to 1M embeddings | 8 |
| NFR-2.4 | Stateless agent design shall enable easy horizontal scaling | 5 |

### 6.3 Reliability (NFR-3)

| ID | Requirement | Phase |
|---|---|---|
| NFR-3.1 | System uptime shall be 99% during operation | 9 |
| NFR-3.2 | Circuit breaker shall prevent cascading failures to LLM services | 6 |
| NFR-3.3 | System shall implement automatic retry for transient failures | 6 |
| NFR-3.4 | System shall persist data across container restarts | 1 |
| NFR-3.5 | System shall implement health checks for all critical services | 7 |
| NFR-3.6 | Circuit breaker shall open after 5 consecutive failures (configurable) | 6 |
| NFR-3.7 | System shall provide graceful degradation when LLM service is unavailable | 6 |

### 6.4 Maintainability (NFR-4)

| ID | Requirement | Phase |
|---|---|---|
| NFR-4.1 | Code shall follow Python PEP 8 style guidelines | 8 |
| NFR-4.2 | All modules shall have comprehensive docstrings | 9 |
| NFR-4.3 | System shall use environment variables for configuration | 2 |
| NFR-4.4 | System shall provide detailed logging for debugging | 7 |

### 6.5 Security (NFR-5)

| ID | Requirement | Phase |
|---|---|---|
| NFR-5.1 | System shall not expose sensitive data in logs | 2 |
| NFR-5.2 | Secrets shall be masked in all log outputs using Pydantic SecretStr | 2 |
| NFR-5.3 | API endpoints shall implement input validation | 7 |
| NFR-5.4 | Elasticsearch shall be accessible only within Docker network | 1 |
| NFR-5.5 | Environment variables shall be used for sensitive configuration | 2 |
| NFR-5.6 | Configuration module shall validate secret formats on startup | 2 |
| NFR-5.7 | `.env` files shall be excluded from version control via `.gitignore` | 1 |
| NFR-5.8 | Only `.env.example` with placeholders shall be committed | 1 |

### 6.6 Portability (NFR-6)

| ID | Requirement | Phase |
|---|---|---|
| NFR-6.1 | System shall run identically on macOS, Linux, and Windows (via Docker) | 1 |
| NFR-6.2 | All dependencies shall be pinned in lock files | 1 |
| NFR-6.3 | Docker image shall be self-contained | 1 |
