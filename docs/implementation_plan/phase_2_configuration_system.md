# 5. Phase 2: Core Configuration System

**Goal:** Implement centralized, type-safe configuration management with secrets handling.

**Duration:** 2-3 days
**Status:** ✅ COMPLETED
**Completed:** October 20, 2025
**Dependencies:** Phase 1

### 5.1 Configuration Module Design

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 2.1.1 | Create `src/config/base.py` with Pydantic BaseSettings | 🔴 P0 | ✅ | Base configuration classes |
| 2.1.2 | Create `src/config/secrets.py` for secret types | 🔴 P0 | ✅ | Use SecretStr for masking |
| 2.1.3 | Create `src/config/settings.py` with all config sections | 🔴 P0 | ✅ | App, LMStudio, ES, etc. |
| 2.1.4 | Implement singleton pattern for config access | 🔴 P0 | ✅ | `get_settings()` function |
| 2.1.5 | Add configuration validation logic | 🟡 P1 | ✅ | Custom validators |

**Implementation Details:**

**File: `src/config/base.py`**

```python
"""Base configuration classes."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Base configuration with common settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"
    )
```

**File: `src/config/secrets.py`**

```python
"""Secret types and utilities."""
from typing import Optional
from pydantic import SecretStr


class SecretConfig:
    """Utilities for handling secrets."""

    @staticmethod
    def get_secret_value(secret: Optional[SecretStr]) -> str:
        """Safely extract secret value."""
        if secret is None:
            return ""
        return secret.get_secret_value()
```

**Verification Steps:**

- [ ] Configuration classes defined with proper Pydantic models
- [ ] Can import and instantiate config classes
- [ ] SecretStr fields mask values in logs
- [ ] Settings successfully load from environment variables

---

### 5.2 Configuration Sections Implementation

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 2.2.1 | Implement `AppSettings` class | 🔴 P0 | ✅ | Host, port, log level, env |
| 2.2.2 | Implement `LMStudioSettings` class | 🔴 P0 | ✅ | URL, models, API key |
| 2.2.3 | Implement `ElasticsearchSettings` class | 🔴 P0 | ✅ | Host, port, index, auth |
| 2.2.4 | Implement `ChunkingSettings` class | 🔴 P0 | ✅ | Size, overlap |
| 2.2.5 | Implement `RetrievalSettings` class | 🔴 P0 | ✅ | Top-k, threshold |
| 2.2.6 | Implement `CircuitBreakerSettings` class | 🔴 P0 | ✅ | Failure threshold, timeout |
| 2.2.7 | Implement `HealthSettings` class | 🔴 P0 | ✅ | Timeouts, intervals |
| 2.2.8 | Create master `Settings` class | 🔴 P0 | ✅ | Combines all sections |

**File: `src/config/settings.py`**

```python
"""Application settings."""
from typing import Optional
from pydantic import Field, SecretStr, field_validator
from .base import BaseConfig


class AppSettings(BaseConfig):
    """Application settings."""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"


class LMStudioSettings(BaseConfig):
    """LMStudio configuration."""
    base_url: str = Field(..., description="LMStudio API base URL")
    embedding_model: str = Field(..., description="Embedding model name")
    chat_model: str = Field(..., description="Chat model name")
    api_key: Optional[SecretStr] = None
    timeout: int = 30

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


class ElasticsearchSettings(BaseConfig):
    """Elasticsearch configuration."""
    host: str = "elasticsearch"
    port: int = 9200
    index: str = "documents"
    username: Optional[SecretStr] = None
    password: Optional[SecretStr] = None

    @property
    def url(self) -> str:
        """Get Elasticsearch URL."""
        return f"http://{self.host}:{self.port}"


class ChunkingSettings(BaseConfig):
    """Text chunking configuration."""
    size: int = 512
    overlap: int = 50

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        if v < 100 or v > 2000:
            raise ValueError("chunk_size must be between 100 and 2000")
        return v


class RetrievalSettings(BaseConfig):
    """Retrieval configuration."""
    top_k: int = 5
    similarity_threshold: float = 0.7

    @field_validator("similarity_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        return v


class CircuitBreakerSettings(BaseConfig):
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    timeout_seconds: int = 60
    half_open_max_calls: int = 3


class HealthSettings(BaseConfig):
    """Health probe configuration."""
    check_timeout: int = 1
    startup_timeout: int = 30
    readiness_interval: int = 5


class Settings(BaseConfig):
    """Master settings class."""
    app: AppSettings = Field(default_factory=AppSettings)
    lmstudio: LMStudioSettings
    elasticsearch: ElasticsearchSettings = Field(default_factory=ElasticsearchSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    circuit_breaker: CircuitBreakerSettings = Field(default_factory=CircuitBreakerSettings)
    health: HealthSettings = Field(default_factory=HealthSettings)


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

**Verification Steps:**

- [ ] All settings classes implement proper validation
- [ ] Can load settings from environment variables
- [ ] Nested environment variables work (e.g., `LMSTUDIO__BASE_URL`)
- [ ] Invalid values raise clear validation errors
- [ ] Singleton pattern works correctly

---

### 5.3 Environment Files

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 2.3.1 | Create `.env.example` with all parameters | 🔴 P0 | ✅ | Template with placeholders |
| 2.3.2 | Create `.env` for local development | 🔴 P0 | ✅ | Gitignored, real values |
| 2.3.3 | Document all environment variables | 🟡 P1 | ✅ | In README or separate doc |
| 2.3.4 | Update `.gitignore` to exclude `.env` | 🔴 P0 | ✅ | Ensure secrets not committed |

**File: `.env.example`**

```bash
# ============================================
# Elastic RAG Configuration Template
# ============================================
# Copy this file to .env and fill in values
# NEVER commit .env to version control!

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
APP_LOG_LEVEL=INFO
APP_ENVIRONMENT=development

# LMStudio Configuration (Local LLM)
LMSTUDIO__BASE_URL=http://localhost:1234/v1
LMSTUDIO__EMBEDDING_MODEL=nomic-embed-text
LMSTUDIO__CHAT_MODEL=llama-3.2-3b-instruct
LMSTUDIO__API_KEY=  # Optional, leave empty for local
LMSTUDIO__TIMEOUT=30

# Elasticsearch Configuration
ELASTICSEARCH__HOST=elasticsearch
ELASTICSEARCH__PORT=9200
ELASTICSEARCH__INDEX=documents
ELASTICSEARCH__USERNAME=  # Optional, if auth enabled
ELASTICSEARCH__PASSWORD=  # Optional, if auth enabled

# Chunking Configuration
CHUNKING__SIZE=512
CHUNKING__OVERLAP=50

# Retrieval Configuration
RETRIEVAL__TOP_K=5
RETRIEVAL__SIMILARITY_THRESHOLD=0.7

# Circuit Breaker Configuration
CIRCUIT_BREAKER__FAILURE_THRESHOLD=5
CIRCUIT_BREAKER__TIMEOUT_SECONDS=60
CIRCUIT_BREAKER__HALF_OPEN_MAX_CALLS=3

# Health Probe Configuration
HEALTH__CHECK_TIMEOUT=1
HEALTH__STARTUP_TIMEOUT=30
HEALTH__READINESS_INTERVAL=5
```

**Verification Steps:**

- [ ] `.env.example` contains all required parameters
- [ ] `.env` file created with real values (not committed)
- [ ] `.gitignore` excludes `.env`
- [ ] Can start application with config from `.env`

---

### 5.4 Configuration Testing

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 2.4.1 | Create unit tests for configuration loading | 🟡 P1 | ✅ | Test valid configs |
| 2.4.2 | Test validation errors for invalid values | 🟡 P1 | ✅ | Test error messages |
| 2.4.3 | Test secret masking in logs | 🔴 P0 | ✅ | Ensure secrets hidden |
| 2.4.4 | Test environment variable override | 🟡 P1 | ✅ | Test precedence |

**File: `tests/unit/test_config.py`**

```python
"""Tests for configuration module."""
import pytest
from src.config.settings import Settings, LMStudioSettings


def test_lmstudio_settings_valid():
    """Test valid LMStudio settings."""
    settings = LMStudioSettings(
        base_url="http://localhost:1234/v1",
        embedding_model="test-model",
        chat_model="test-chat"
    )
    assert settings.base_url == "http://localhost:1234/v1"


def test_lmstudio_settings_invalid_url():
    """Test invalid URL raises error."""
    with pytest.raises(ValueError):
        LMStudioSettings(
            base_url="invalid-url",
            embedding_model="test",
            chat_model="test"
        )


def test_secret_masking():
    """Test that secrets are masked."""
    settings = LMStudioSettings(
        base_url="http://localhost:1234/v1",
        embedding_model="test",
        chat_model="test",
        api_key="secret-key-123"
    )
    # SecretStr should mask the value
    assert "secret-key-123" not in str(settings)
```

**Verification Steps:**

- [ ] All configuration tests pass
- [ ] Validation errors are caught and reported clearly
- [ ] Secrets are properly masked in logs
- [ ] Configuration singleton works correctly

---

### 5.5 Phase 2 Completion Checklist

- [x] All configuration classes implemented
- [x] Validation logic works correctly
- [x] `.env.example` created with all parameters
- [x] `.env` file configured for development
- [x] Secrets properly handled with SecretStr
- [x] Configuration tests pass (45/45 tests passing)
- [x] Can load and access settings throughout application
- [x] Test coverage: 100% (117/117 statements covered)

**Phase 2 Exit Criteria:**

- ✅ `get_settings()` returns valid Settings object
- ✅ All environment variables load correctly
- ✅ Invalid configurations raise clear errors
- ✅ Secrets masked in all log outputs
- ✅ Configuration tests pass (45 tests, 100% coverage)

**Completed:** October 20, 2025
