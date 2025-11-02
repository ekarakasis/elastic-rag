# Configuration Guide

**Version:** 1.0.0
**Last Updated:** October 25, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration Architecture](#configuration-architecture)
3. [Environment Variables Reference](#environment-variables-reference)
4. [Configuration Patterns](#configuration-patterns)
5. [Validation and Type Safety](#validation-and-type-safety)
6. [Secret Management](#secret-management)
7. [Environment-Specific Configurations](#environment-specific-configurations)
8. [Troubleshooting Configuration Issues](#troubleshooting-configuration-issues)

---

## Overview

Elastic RAG uses a sophisticated configuration system built on Pydantic Settings, providing:

- **Type Safety** - All configuration values are validated at startup
- **Environment-Based** - Load configuration from environment variables or `.env` file
- **Nested Structure** - Double underscore (`__`) delimiter for hierarchical configuration
- **Secure Secrets** - Automatic masking of sensitive values in logs
- **Sensible Defaults** - Many values have reasonable defaults

### Quick Start

1. Copy the example configuration:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration
3. Start the application (configuration is automatically loaded)

---

## Configuration Architecture

### Loading Order

Configuration is loaded in this order (later sources override earlier ones):

1. **Default Values** - Defined in Pydantic models
2. **Environment Variables** - System environment
3. **.env File** - Project root `.env` file
4. **Validation** - Type checking and constraint validation

### Naming Convention

Environment variables use double underscore (`__`) as a delimiter for nested structures:

```bash
# Maps to: settings.app.host
APP__HOST=0.0.0.0

# Maps to: settings.lmstudio.base_url
LMSTUDIO__BASE_URL=http://localhost:1234/v1

# Maps to: settings.circuit_breaker.failure_threshold
CIRCUIT_BREAKER__FAILURE_THRESHOLD=5
```

Variable names are **case-insensitive**:

- `APP__HOST` = `app__host` = `App__Host`

---

## Environment Variables Reference

### Application Settings

Core FastAPI application configuration.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `APP__HOST` | string | `0.0.0.0` | No | Server host (0.0.0.0 = all interfaces) |
| `APP__PORT` | int | `8000` | No | Server port number |
| `APP__LOG_LEVEL` | string | `INFO` | No | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `APP__ENVIRONMENT` | string | `development` | No | Environment (development, staging, production) |

**Example:**

```bash
APP__HOST=0.0.0.0
APP__PORT=8000
APP__LOG_LEVEL=INFO
APP__ENVIRONMENT=development
```

---

### Embedder Configuration (Recommended)

Provider-agnostic configuration for embedding models. Works with any OpenAI-compatible API.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `EMBEDDER__PROVIDER` | string | - | No | Provider name (lmstudio, openai, anthropic) |
| `EMBEDDER__BASE_URL` | string | - | Yes* | API endpoint URL |
| `EMBEDDER__MODEL` | string | - | Yes* | Embedding model name |
| `EMBEDDER__API_KEY` | secret | - | No | API key for authentication |
| `EMBEDDER__TIMEOUT` | int | `30` | No | Request timeout in seconds |

\* Required if using embedder (either EMBEDDER__or LMSTUDIO__ must be configured)

**LMStudio Example:**

```bash
EMBEDDER__PROVIDER=lmstudio
EMBEDDER__BASE_URL=http://localhost:1234/v1
EMBEDDER__MODEL=nomic-embed-text
EMBEDDER__API_KEY=lmstudio
EMBEDDER__TIMEOUT=30
```

**OpenAI Example:**

```bash
EMBEDDER__PROVIDER=openai
EMBEDDER__BASE_URL=https://api.openai.com/v1
EMBEDDER__MODEL=text-embedding-3-small
EMBEDDER__API_KEY=sk-your-actual-key-here
EMBEDDER__TIMEOUT=30
```

---

### LLM Configuration (Recommended)

Provider-agnostic configuration for chat completion models. Works with any OpenAI-compatible API.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `LLM__PROVIDER` | string | - | No | Provider name (lmstudio, openai, anthropic) |
| `LLM__BASE_URL` | string | - | Yes* | API endpoint URL |
| `LLM__MODEL` | string | - | Yes* | Chat model name |
| `LLM__API_KEY` | secret | - | No | API key for authentication |
| `LLM__TIMEOUT` | int | `30` | No | Request timeout in seconds |
| `LLM__TEMPERATURE` | float | `0.7` | No | Sampling temperature (0.0-2.0) |
| `LLM__MAX_TOKENS` | int | `15000` | No | Maximum response tokens |

\* Required for LLM functionality

**LMStudio Example:**

```bash
LLM__PROVIDER=lmstudio
LLM__BASE_URL=http://localhost:1234/v1
LLM__MODEL=llama-3.2-3b-instruct
LLM__API_KEY=lmstudio
LLM__TIMEOUT=30
LLM__TEMPERATURE=0.7
LLM__MAX_TOKENS=15000
```

**OpenAI Example:**

```bash
LLM__PROVIDER=openai
LLM__BASE_URL=https://api.openai.com/v1
LLM__MODEL=gpt-4
LLM__API_KEY=sk-your-actual-key-here
LLM__TIMEOUT=30
LLM__TEMPERATURE=0.7
LLM__MAX_TOKENS=4000
```

**Temperature Guidelines:**

- `0.0-0.3`: Deterministic, factual responses
- `0.3-0.7`: Balanced (recommended for RAG)
- `0.7-1.2`: Creative responses
- `1.2-2.0`: Highly creative/random

---

### LMStudio Configuration (Legacy)

Legacy LMStudio-specific settings. Used as fallback if LLM__/EMBEDDER__ not configured.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `LMSTUDIO__BASE_URL` | string | - | Yes | LMStudio API URL (must include /v1) |
| `LMSTUDIO__EMBEDDING_MODEL` | string | - | Yes | Embedding model name |
| `LMSTUDIO__CHAT_MODEL` | string | - | No | Chat model name (use LLM__ instead) |
| `LMSTUDIO__API_KEY` | secret | - | No | API key (usually "lmstudio" for local) |
| `LMSTUDIO__TIMEOUT` | int | `30` | No | Request timeout in seconds |

**Example:**

```bash
LMSTUDIO__BASE_URL=http://localhost:1234/v1
LMSTUDIO__EMBEDDING_MODEL=nomic-embed-text
LMSTUDIO__CHAT_MODEL=llama-3.2-3b-instruct
LMSTUDIO__API_KEY=lmstudio
LMSTUDIO__TIMEOUT=30
```

---

### Elasticsearch Configuration

Configuration for Elasticsearch document storage and vector search.

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ELASTICSEARCH__HOST` | string | `elasticsearch` | Yes | Elasticsearch hostname |
| `ELASTICSEARCH__PORT` | int | `9200` | No | Elasticsearch port |
| `ELASTICSEARCH__INDEX` | string | `documents` | No | Index name for documents |
| `ELASTICSEARCH__USERNAME` | secret | - | No | Authentication username |
| `ELASTICSEARCH__PASSWORD` | secret | - | No | Authentication password |

**Docker Compose Example:**

```bash
ELASTICSEARCH__HOST=elasticsearch
ELASTICSEARCH__PORT=9200
ELASTICSEARCH__INDEX=documents
```

**Local Elasticsearch Example:**

```bash
ELASTICSEARCH__HOST=localhost
ELASTICSEARCH__PORT=9200
ELASTICSEARCH__INDEX=documents
ELASTICSEARCH__USERNAME=elastic
ELASTICSEARCH__PASSWORD=your-password
```

---

### Chunking Configuration

Document chunking settings for text processing.

| Variable | Type | Default | Constraints | Description |
|----------|------|---------|-------------|-------------|
| `CHUNKING__SIZE` | int | `512` | 100-2000 | Chunk size in tokens |
| `CHUNKING__OVERLAP` | int | `50` | ≥ 0 | Overlap between chunks |

**Guidelines:**

- **Small chunks (256-512)**: Better precision, more chunks
- **Medium chunks (512-1024)**: Balanced (recommended)
- **Large chunks (1024-2000)**: More context, fewer chunks
- **Overlap**: 10-20% of chunk size maintains context

**Example:**

```bash
CHUNKING__SIZE=512
CHUNKING__OVERLAP=50
```

---

### Retrieval Configuration

Settings for document retrieval during RAG queries.

| Variable | Type | Default | Constraints | Description |
|----------|------|---------|-------------|-------------|
| `RETRIEVAL__TOP_K` | int | `5` | > 0 | Number of documents to retrieve |
| `RETRIEVAL__SIMILARITY_THRESHOLD` | float | `0.7` | 0.0-1.0 | Minimum similarity score |

**Guidelines:**

- **Top-K = 3-5**: Fast, focused responses
- **Top-K = 5-10**: More context, better coverage
- **Top-K > 10**: Comprehensive but may add noise
- **Threshold = 0.5-0.6**: More permissive
- **Threshold = 0.7-0.8**: Balanced (recommended)
- **Threshold = 0.8-1.0**: Very strict, high precision

**Example:**

```bash
RETRIEVAL__TOP_K=5
RETRIEVAL__SIMILARITY_THRESHOLD=0.7
```

---

### Circuit Breaker Configuration

Resilience settings to prevent cascading failures.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CIRCUIT_BREAKER__FAILURE_THRESHOLD` | int | `5` | Failures before opening circuit |
| `CIRCUIT_BREAKER__TIMEOUT_SECONDS` | int | `60` | Recovery timeout in seconds |
| `CIRCUIT_BREAKER__HALF_OPEN_MAX_CALLS` | int | `3` | Max calls in half-open state |

**Circuit States:**

- **CLOSED**: Normal operation
- **OPEN**: Service failed, requests blocked
- **HALF_OPEN**: Testing recovery

**Example:**

```bash
CIRCUIT_BREAKER__FAILURE_THRESHOLD=5
CIRCUIT_BREAKER__TIMEOUT_SECONDS=60
CIRCUIT_BREAKER__HALF_OPEN_MAX_CALLS=3
```

---

### Health Check Configuration

Kubernetes-style health probe settings.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `HEALTH__CHECK_TIMEOUT` | int | `1` | Individual check timeout (seconds) |
| `HEALTH__STARTUP_TIMEOUT` | int | `30` | Startup timeout (seconds) |
| `HEALTH__READINESS_INTERVAL` | int | `5` | Readiness check interval (seconds) |

**Example:**

```bash
HEALTH__CHECK_TIMEOUT=1
HEALTH__STARTUP_TIMEOUT=30
HEALTH__READINESS_INTERVAL=5
```

---

### File Upload Configuration

API file upload validation settings.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FILE_UPLOAD__ALLOWED_EXTENSIONS` | set[str] | `.pdf,.docx,.pptx,.html,.txt` | Allowed file extensions |
| `FILE_UPLOAD__MAX_FILE_SIZE_MB` | int | `50` | Maximum file size in MB |

**Example:**

```bash
FILE_UPLOAD__ALLOWED_EXTENSIONS=.pdf,.docx,.txt
FILE_UPLOAD__MAX_FILE_SIZE_MB=50
```

---

## Configuration Patterns

### Development Configuration

Optimized for local development with verbose logging:

```bash
# Application
APP__LOG_LEVEL=DEBUG
APP__ENVIRONMENT=development

# LMStudio (local)
LLM__PROVIDER=lmstudio
LLM__BASE_URL=http://localhost:1234/v1
LLM__MODEL=llama-3.2-3b-instruct
LLM__API_KEY=lmstudio
LLM__TEMPERATURE=0.7

EMBEDDER__PROVIDER=lmstudio
EMBEDDER__BASE_URL=http://localhost:1234/v1
EMBEDDER__MODEL=nomic-embed-text
EMBEDDER__API_KEY=lmstudio

# Elasticsearch (Docker)
ELASTICSEARCH__HOST=elasticsearch
ELASTICSEARCH__PORT=9200

# Relaxed retrieval
RETRIEVAL__TOP_K=10
RETRIEVAL__SIMILARITY_THRESHOLD=0.6

# Forgiving circuit breaker
CIRCUIT_BREAKER__FAILURE_THRESHOLD=10
CIRCUIT_BREAKER__TIMEOUT_SECONDS=30
```

---

### Production Configuration

Optimized for production with stricter settings:

```bash
# Application
APP__LOG_LEVEL=WARNING
APP__ENVIRONMENT=production
APP__HOST=0.0.0.0
APP__PORT=8000

# Cloud LLM provider
LLM__PROVIDER=openai
LLM__BASE_URL=https://api.openai.com/v1
LLM__MODEL=gpt-4
LLM__API_KEY=${OPENAI_API_KEY}
LLM__TIMEOUT=30
LLM__TEMPERATURE=0.5
LLM__MAX_TOKENS=4000

EMBEDDER__PROVIDER=openai
EMBEDDER__BASE_URL=https://api.openai.com/v1
EMBEDDER__MODEL=text-embedding-3-small
EMBEDDER__API_KEY=${OPENAI_API_KEY}
EMBEDDER__TIMEOUT=30

# Elasticsearch (production)
ELASTICSEARCH__HOST=elasticsearch.production.internal
ELASTICSEARCH__PORT=9200
ELASTICSEARCH__USERNAME=${ES_USERNAME}
ELASTICSEARCH__PASSWORD=${ES_PASSWORD}
ELASTICSEARCH__INDEX=documents-prod

# Conservative retrieval
RETRIEVAL__TOP_K=5
RETRIEVAL__SIMILARITY_THRESHOLD=0.75

# Strict circuit breaker
CIRCUIT_BREAKER__FAILURE_THRESHOLD=5
CIRCUIT_BREAKER__TIMEOUT_SECONDS=60
CIRCUIT_BREAKER__HALF_OPEN_MAX_CALLS=3

# Health checks
HEALTH__CHECK_TIMEOUT=1
HEALTH__STARTUP_TIMEOUT=30

# File upload limits
FILE_UPLOAD__MAX_FILE_SIZE_MB=50
```

---

### Testing Configuration

Optimized for running tests:

```bash
# Application
APP__LOG_LEVEL=ERROR
APP__ENVIRONMENT=testing

# LMStudio or mocked
LLM__PROVIDER=lmstudio
LLM__BASE_URL=http://localhost:1234/v1
LLM__MODEL=test-model
LLM__TIMEOUT=5

EMBEDDER__PROVIDER=lmstudio
EMBEDDER__BASE_URL=http://localhost:1234/v1
EMBEDDER__MODEL=test-embedding
EMBEDDER__TIMEOUT=5

# Elasticsearch (test instance)
ELASTICSEARCH__HOST=localhost
ELASTICSEARCH__PORT=9200
ELASTICSEARCH__INDEX=documents-test

# Fast retrieval
RETRIEVAL__TOP_K=3
RETRIEVAL__SIMILARITY_THRESHOLD=0.5

# Lenient circuit breaker
CIRCUIT_BREAKER__FAILURE_THRESHOLD=20
CIRCUIT_BREAKER__TIMEOUT_SECONDS=10
```

---

## Validation and Type Safety

### Type Validation

All configuration values are validated at application startup:

```python
# Automatic type conversion
APP__PORT=8000  # String "8000" → int 8000

# Type mismatch raises error
APP__PORT=abc  # ❌ ValidationError: value is not a valid integer

# Constraints checked
CHUNKING__SIZE=50  # ❌ ValidationError: must be >= 100
```

### Constraint Validation

Pydantic validators enforce constraints:

- **CHUNKING__SIZE**: 100 ≤ size ≤ 2000
- **CHUNKING__OVERLAP**: ≥ 0
- **RETRIEVAL__TOP_K**: > 0
- **RETRIEVAL__SIMILARITY_THRESHOLD**: 0.0 ≤ threshold ≤ 1.0
- **FILE_UPLOAD__MAX_FILE_SIZE_MB**: 0 < size ≤ 1000

### Required Fields

Some fields are required and must be set:

```bash
# ❌ Will fail validation
# Missing ELASTICSEARCH__HOST

# ✅ Valid
ELASTICSEARCH__HOST=elasticsearch
```

---

## Secret Management

### SecretStr Fields

Sensitive values use Pydantic's `SecretStr` for automatic masking:

```python
from src.config.settings import get_settings

settings = get_settings()

# Automatically masked in logs
print(settings.lmstudio.api_key)  # Output: **********

# Extract actual value (use carefully!)
from src.config.secrets import SecretConfig
actual_key = SecretConfig.get_secret_value(settings.lmstudio.api_key)
```

### Secret Fields

- `EMBEDDER__API_KEY`
- `LLM__API_KEY`
- `LMSTUDIO__API_KEY`
- `ELASTICSEARCH__USERNAME`
- `ELASTICSEARCH__PASSWORD`

### Best Practices

1. **Never log secrets directly**

   ```python
   # ❌ Bad
   logger.info(f"API Key: {settings.lmstudio.api_key}")

   # ✅ Good
   logger.info("API Key configured")
   ```

2. **Use environment variables for secrets**

   ```bash
   # ❌ Don't commit secrets in .env
   LLM__API_KEY=sk-abc123...

   # ✅ Use environment variables
   export LLM__API_KEY=sk-abc123...
   ```

3. **Use secret management systems in production**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Kubernetes Secrets

---

## Environment-Specific Configurations

### Multiple Environments

Create separate files for each environment:

```bash
# Development
.env.development

# Staging
.env.staging

# Production
.env.production
```

### Loading Specific Environment

```bash
# Method 1: Copy to .env
cp .env.production .env

# Method 2: Set in environment
export APP__ENVIRONMENT=production
export LLM__API_KEY=your-key
```

### Docker Compose Override

```yaml
# docker-compose.override.yml
services:
  app:
    environment:
      - APP__ENVIRONMENT=production
      - LLM__API_KEY=${OPENAI_API_KEY}
```

---

## Troubleshooting Configuration Issues

### Configuration Not Loading

**Problem:** Changes to `.env` not reflected

**Solutions:**

1. Restart the application (settings loaded at startup)
2. Check file location (must be in project root)
3. Verify file name is exactly `.env`
4. Check for syntax errors in `.env`

### Validation Errors

**Problem:** `ValidationError` on startup

**Solutions:**

1. Check error message for specific field
2. Verify value type (int vs string)
3. Check constraints (ranges, valid values)
4. Ensure required fields are set

**Example:**

```
ValidationError: 1 validation error for Settings
chunking
  size
    ensure this value is greater than or equal to 100
```

Fix: `CHUNKING__SIZE=512` (was below minimum)

### Connection Failures

**Problem:** Can't connect to Elasticsearch or LMStudio

**Solutions:**

1. Verify services are running
2. Check host/port configuration
3. For Docker: use service name (not localhost)
4. For local: use localhost
5. Check firewall settings

### Missing Required Fields

**Problem:** `Field required` error

**Solutions:**

1. Set the required field in `.env`
2. Or set via environment variable
3. Check spelling (case-insensitive but must match)

### Secret Access Issues

**Problem:** Can't use API key

**Solutions:**

1. Ensure SecretStr is unwrapped:

   ```python
   from src.config.secrets import SecretConfig
   key = SecretConfig.get_secret_value(settings.llm.api_key)
   ```

2. Verify secret is set in environment
3. Check for extra spaces/newlines

---

## Accessing Configuration in Code

### Get Settings Singleton

```python
from src.config.settings import get_settings

settings = get_settings()
```

### Access Configuration Values

```python
# Application settings
host = settings.app.host
port = settings.app.port
log_level = settings.app.log_level

# LLM settings
llm_base_url = settings.llm.base_url
llm_model = settings.llm.model

# Elasticsearch settings
es_url = settings.elasticsearch.url  # Computed property
es_index = settings.elasticsearch.index

# Chunking settings
chunk_size = settings.chunking.size
chunk_overlap = settings.chunking.overlap
```

### Computed Properties

Some settings have computed properties:

```python
# Elasticsearch URL (computed from host + port)
settings.elasticsearch.url  # "http://elasticsearch:9200"

# Combined LLM/LMStudio settings
settings.get_llm_config()  # Returns LLM__ or LMSTUDIO__ config
settings.get_embedder_config()  # Returns EMBEDDER__ or LMSTUDIO__ config
```

---

## Configuration Files Reference

### .env

Main configuration file (not committed to git)

### .env.example

Template with all available options and documentation

### src/config/settings.py

Pydantic Settings models defining configuration structure

### src/config/secrets.py

Secret handling utilities (SecretStr, masking)

### src/config/base.py

Base configuration classes and utilities

---

## Summary

Elastic RAG's configuration system provides:

✅ **Type-safe** configuration with automatic validation
✅ **Flexible** provider-agnostic LLM/embedder configuration
✅ **Secure** secret management with automatic masking
✅ **Environment-aware** with support for multiple environments
✅ **Well-documented** with extensive examples and guidelines
✅ **Production-ready** with sensible defaults and constraints

For additional help, see:

- [README.md](../README.md) - Quick start and basic configuration
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide
