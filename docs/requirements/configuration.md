# 10. Configuration

### 10.1 Central Configuration Architecture

The system implements a centralized configuration management approach using Pydantic Settings for type-safe, validated, and extensible configuration.

#### 10.1.1 Configuration Module Design

**Location:** `src/config/settings.py`

**Key Features:**

- Single source of truth for all configuration
- Type-safe using Pydantic models
- Automatic validation on startup
- Environment variable loading from `.env` files
- Extensible without code modifications
- Secrets masking for security
- Support for multiple environments

#### 10.1.2 Configuration File Structure

```python
# Pseudo-code structure
class LMStudioSettings(BaseSettings):
    """LMStudio-specific configuration"""
    base_url: str
    embedding_model: str
    chat_model: str
    api_key: Optional[SecretStr]  # Future use

class ElasticsearchSettings(BaseSettings):
    """Elasticsearch-specific configuration"""
    host: str
    port: int
    index: str
    username: Optional[SecretStr]  # Future use
    password: Optional[SecretStr]  # Future use

class AppSettings(BaseSettings):
    """Application-wide configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"

class Settings(BaseSettings):
    """Master configuration class"""
    app: AppSettings
    lmstudio: LMStudioSettings
    elasticsearch: ElasticsearchSettings
    # Automatically extensible - add new sections here

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"  # Allows LMSTUDIO__BASE_URL
        case_sensitive = False
```

#### 10.1.3 Configuration Access Pattern

All components access configuration through a singleton instance:

```python
from src.config.settings import get_settings

settings = get_settings()
lmstudio_url = settings.lmstudio.base_url
```

#### 10.1.4 Extensibility Design

Adding new configuration parameters requires:

1. Add parameter to appropriate Pydantic model
2. Add to `.env.example` with documentation
3. No code changes in consuming components (automatic discovery)

### 10.2 Environment Variables

```bash
# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
APP_LOG_LEVEL=INFO
APP_ENVIRONMENT=development

# LMStudio Configuration
LMSTUDIO__BASE_URL=http://localhost:1234/v1
LMSTUDIO__EMBEDDING_MODEL=nomic-embed-text
LMSTUDIO__CHAT_MODEL=llama-3.2-3b-instruct
LMSTUDIO__API_KEY=  # Optional, for future use

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
CIRCUIT_BREAKER__EXPECTED_EXCEPTION=RequestException

# Health Probe Configuration
HEALTH__CHECK_TIMEOUT=1
HEALTH__STARTUP_TIMEOUT=30
HEALTH__READINESS_INTERVAL=5

# Secrets (use SecretStr in Pydantic for masking)
# JWT_SECRET_KEY=your-secret-key-here  # Future use
# EXTERNAL_API_KEY=your-api-key-here   # Future use
```

### 10.3 Secrets Management

#### 10.3.1 Secrets Handling Strategy

**Secrets Definition:** Sensitive configuration values that must not be exposed (API keys, passwords, tokens)

**Implementation:**

- Use Pydantic `SecretStr` type for all secrets
- Secrets automatically masked in logs and str() representations
- Access secrets only when needed using `.get_secret_value()`
- Validate secret presence and format on startup

**Example:**

```python
from pydantic import BaseSettings, SecretStr

class LMStudioSettings(BaseSettings):
    api_key: Optional[SecretStr] = None

    def get_api_key(self) -> str:
        """Safely retrieve API key"""
        if self.api_key:
            return self.api_key.get_secret_value()
        return ""
```

#### 10.3.2 Secrets Storage

**Development:**

- Stored in `.env` file (gitignored)
- Never committed to version control

**Production (Future):**

- Docker secrets (`/run/secrets/`)
- Kubernetes secrets
- External secret managers (AWS Secrets Manager, HashiCorp Vault)

#### 10.3.3 `.env.example` Template

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

# LMStudio (Local LLM)
LMSTUDIO__BASE_URL=http://localhost:1234/v1
LMSTUDIO__EMBEDDING_MODEL=<your-embedding-model>
LMSTUDIO__CHAT_MODEL=<your-chat-model>
LMSTUDIO__API_KEY=  # Leave empty for local LMStudio

# Elasticsearch
ELASTICSEARCH__HOST=elasticsearch
ELASTICSEARCH__PORT=9200
ELASTICSEARCH__INDEX=documents

# SECRETS (Never commit actual values!)
# JWT_SECRET_KEY=<generate-random-secret>
# ELASTICSEARCH__PASSWORD=<your-password>
```

### 10.4 Configuration Validation

The configuration module performs validation on startup:

1. **Type Validation:** All values must match declared types
2. **Required Fields:** Missing required fields raise `ValidationError`
3. **Format Validation:** URLs, ports, file paths validated
4. **Range Validation:** Numeric values within acceptable ranges
5. **Secret Validation:** Secrets present when required

**Startup Behavior:**

- Invalid configuration → Application fails to start
- Clear error messages indicate which parameter is invalid
- Prevents runtime errors from misconfiguration
