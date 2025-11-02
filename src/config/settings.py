"""Application settings and configuration management.

This module defines all configuration sections for the Elastic RAG application
and provides a singleton pattern for accessing settings throughout the application.

Configuration can be provided via:
- Environment variables
- .env file in the project root
- Default values defined in the classes

Environment variables use double underscore (__) as a delimiter for nested
configuration. For example:
    LMSTUDIO__BASE_URL=http://localhost:1234/v1
    ELASTICSEARCH__HOST=elasticsearch
"""

from pydantic import Field, SecretStr, field_validator

from .base import BaseConfig


class AppSettings(BaseConfig):
    """General application settings.

    Attributes:
        host: Host address to bind the FastAPI server to
        port: Port number for the FastAPI server
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Application environment (development, staging, production)
    """

    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port number")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Application environment")


class EmbedderSettings(BaseConfig):
    """Generic embedder configuration for any LLM provider.

    Provider-agnostic configuration that works with OpenAI, LMStudio, Anthropic,
    or any OpenAI-compatible API. This allows easy switching between providers.

    Attributes:
        provider: Provider name (e.g., 'lmstudio', 'openai', 'anthropic')
        base_url: Full URL to API endpoint (e.g., http://localhost:1234/v1)
        model: Name of the embedding model
        api_key: API key for the provider (use 'dummy' for local endpoints)
        timeout: Request timeout in seconds
    """

    provider: str = Field(default="lmstudio", description="LLM provider name")
    base_url: str = Field(..., description="Provider API base URL")
    model: str = Field(..., description="Embedding model name")
    api_key: SecretStr = Field(default=SecretStr("dummy"), description="API key for provider")
    timeout: int = Field(default=30, description="Request timeout in seconds")

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that base_url is a proper HTTP/HTTPS URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")  # Remove trailing slash if present

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate that timeout is a positive integer."""
        if v <= 0:
            raise ValueError("timeout must be a positive integer")
        return v


class LLMSettings(BaseConfig):
    """Generic LLM configuration for any chat completion provider.

    Provider-agnostic configuration that works with OpenAI, LMStudio, Anthropic,
    or any OpenAI-compatible API. This allows easy switching between providers
    for chat completion and answer generation.

    Attributes:
        provider: Provider name (e.g., 'lmstudio', 'openai', 'anthropic')
        base_url: Full URL to API endpoint (e.g., http://localhost:1234/v1)
        model: Name of the chat/completion model
        api_key: API key for the provider (use 'dummy' for local endpoints)
        timeout: Request timeout in seconds
        temperature: Default sampling temperature (0.0-2.0)
        max_tokens: Default maximum tokens in response
    """

    provider: str = Field(default="lmstudio", description="LLM provider name")
    base_url: str = Field(..., description="Provider API base URL")
    model: str = Field(..., description="Chat completion model name")
    api_key: SecretStr = Field(default=SecretStr("dummy"), description="API key for provider")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    temperature: float = Field(default=0.7, description="Sampling temperature (0.0-2.0)")
    max_tokens: int = Field(default=15000, description="Maximum tokens in response")

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that base_url is a proper HTTP/HTTPS URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate that timeout is a positive integer."""
        if v <= 0:
            raise ValueError("timeout must be a positive integer")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate that temperature is between 0 and 2."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Validate that max_tokens is positive."""
        if v <= 0:
            raise ValueError("max_tokens must be a positive integer")
        return v


class LMStudioSettings(BaseConfig):
    """LMStudio local LLM server configuration.

    LMStudio provides local LLM inference for both chat completion and embeddings.
    This configuration section defines how to connect to the LMStudio server.

    Note: For embeddings, prefer using EmbedderSettings for provider flexibility.
    This section is kept for backward compatibility and chat model configuration.

    Attributes:
        base_url: Full URL to LMStudio API endpoint (must include /v1)
        embedding_model: Name of the embedding model loaded in LMStudio
        chat_model: Name of the chat/completion model loaded in LMStudio
        api_key: Optional API key (typically not needed for local LMStudio)
        timeout: Request timeout in seconds
    """

    base_url: str = Field(..., description="LMStudio API base URL (e.g., http://localhost:1234/v1)")
    embedding_model: str = Field(..., description="Embedding model name (e.g., nomic-embed-text)")
    chat_model: str = Field(..., description="Chat model name (e.g., llama-3.2-3b-instruct)")
    api_key: SecretStr | None = Field(default=None, description="Optional API key for LMStudio")
    timeout: int = Field(default=30, description="Request timeout in seconds")

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that base_url is a proper HTTP/HTTPS URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")  # Remove trailing slash if present

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate that timeout is a positive integer."""
        if v <= 0:
            raise ValueError("timeout must be a positive integer")
        return v


class ElasticsearchSettings(BaseConfig):
    """Elasticsearch configuration.

    Configuration for connecting to Elasticsearch for document storage and
    vector similarity search.

    Attributes:
        host: Elasticsearch hostname or IP address
        port: Elasticsearch port number
        index: Index name for storing documents
        username: Optional username for authentication
        password: Optional password for authentication
    """

    host: str = Field(default="elasticsearch", description="Elasticsearch hostname")
    port: int = Field(default=9200, description="Elasticsearch port")
    index: str = Field(default="documents", description="Index name for documents")
    username: SecretStr | None = Field(
        default=None, description="Optional username for authentication"
    )
    password: SecretStr | None = Field(
        default=None, description="Optional password for authentication"
    )

    @property
    def url(self) -> str:
        """Get the full Elasticsearch URL.

        Returns:
            Full URL in format http://host:port
        """
        return f"http://{self.host}:{self.port}"


class ChunkingSettings(BaseConfig):
    """Text chunking configuration.

    Configuration for splitting documents into smaller chunks for embedding
    and retrieval. Chunks can overlap to maintain context across boundaries.

    Attributes:
        size: Maximum chunk size in tokens/characters
        overlap: Number of tokens/characters to overlap between chunks
    """

    size: int = Field(default=512, description="Chunk size in tokens")
    overlap: int = Field(default=50, description="Overlap between chunks in tokens")

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        """Validate that chunk size is within reasonable bounds."""
        if v < 100 or v > 2000:
            raise ValueError("chunk_size must be between 100 and 2000")
        return v

    @field_validator("overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Validate that overlap is reasonable."""
        if v < 0:
            raise ValueError("overlap must be non-negative")
        # Note: We can't validate against size here as it may not be set yet
        # This validation will happen when the full model is constructed
        return v


class RetrievalSettings(BaseConfig):
    """Document retrieval configuration.

    Configuration for retrieving relevant documents from Elasticsearch
    during the RAG query process.

    Attributes:
        top_k: Number of top documents to retrieve
        similarity_threshold: Minimum similarity score (0-1) for retrieval
    """

    top_k: int = Field(default=5, description="Number of documents to retrieve")
    similarity_threshold: float = Field(
        default=0.7, description="Minimum similarity score threshold"
    )

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        """Validate that top_k is a positive integer."""
        if v <= 0:
            raise ValueError("top_k must be a positive integer")
        return v

    @field_validator("similarity_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """Validate that similarity_threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        return v


class CircuitBreakerSettings(BaseConfig):
    """Circuit breaker configuration for resilience.

    Circuit breakers prevent cascading failures by temporarily stopping
    requests to failing services, giving them time to recover.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        timeout_seconds: Time to wait before attempting recovery
        half_open_max_calls: Max calls to allow in half-open state
    """

    failure_threshold: int = Field(
        default=5, description="Number of failures before opening circuit"
    )
    timeout_seconds: int = Field(default=60, description="Timeout before attempting recovery")
    half_open_max_calls: int = Field(default=3, description="Max calls in half-open state")

    @field_validator("failure_threshold", "timeout_seconds", "half_open_max_calls")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Validate that values are positive integers."""
        if v <= 0:
            raise ValueError("Circuit breaker values must be positive integers")
        return v


class HealthSettings(BaseConfig):
    """Health check and monitoring configuration.

    Configuration for health probes, startup checks, and readiness monitoring.

    Attributes:
        check_timeout: Timeout for individual health checks
        startup_timeout: Max time to wait for startup completion
        readiness_interval: Interval between readiness checks
    """

    check_timeout: int = Field(default=1, description="Health check timeout in seconds")
    startup_timeout: int = Field(default=30, description="Startup timeout in seconds")
    readiness_interval: int = Field(default=5, description="Readiness check interval in seconds")

    @field_validator("check_timeout", "startup_timeout", "readiness_interval")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Validate that timeout values are positive."""
        if v <= 0:
            raise ValueError("Health check timeout values must be positive")
        return v


class FileUploadSettings(BaseConfig):
    """File upload configuration for API endpoints.

    Configuration for document upload validation including allowed file types
    and maximum file size limits.

    Attributes:
        allowed_extensions: Comma-separated string or set of allowed file extensions
        max_file_size_mb: Maximum file size in megabytes
    """

    allowed_extensions: str = Field(
        default=".pdf,.docx,.pptx,.html,.txt",
        description="Comma-separated allowed file extensions for upload",
    )
    max_file_size_mb: int = Field(default=50, description="Maximum file size in megabytes")

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, v) -> str:
        """Parse extensions from various input formats."""
        if isinstance(v, list | set | tuple):
            # If already a collection, join with commas
            return ",".join(str(ext) for ext in v)
        return str(v)

    @field_validator("allowed_extensions")
    @classmethod
    def validate_extensions(cls, v: str) -> str:
        """Validate that all extensions start with a dot."""
        extensions = {ext.strip() for ext in v.split(",") if ext.strip()}
        for ext in extensions:
            if not ext.startswith("."):
                raise ValueError(f"Extension must start with a dot: {ext}")
        return v

    @field_validator("max_file_size_mb")
    @classmethod
    def validate_max_size(cls, v: int) -> int:
        """Validate that max file size is positive and reasonable."""
        if v <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if v > 1000:  # 1GB limit
            raise ValueError("max_file_size_mb cannot exceed 1000 MB (1 GB)")
        return v

    def get_allowed_extensions_set(self) -> set[str]:
        """Get allowed extensions as a set.

        Returns:
            Set of allowed file extensions
        """
        return {ext.strip() for ext in self.allowed_extensions.split(",") if ext.strip()}

    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes.

        Returns:
            Maximum file size in bytes
        """
        return self.max_file_size_mb * 1024 * 1024


class Settings(BaseConfig):
    """Master settings class combining all configuration sections.

    This class aggregates all configuration sections and provides a single
    point of access to all application settings. Use the get_settings()
    function to access the singleton instance.

    Attributes:
        app: General application settings
        embedder: Generic embedder configuration (provider-agnostic)
        llm: Generic LLM configuration (provider-agnostic)
        lmstudio: LMStudio LLM server configuration (for backward compatibility)
        elasticsearch: Elasticsearch configuration
        chunking: Text chunking configuration
        retrieval: Document retrieval configuration
        circuit_breaker: Circuit breaker resilience configuration
        health: Health check configuration
        file_upload: File upload configuration
    """

    app: AppSettings = Field(default_factory=AppSettings, description="Application settings")
    embedder: EmbedderSettings | None = Field(
        default=None, description="Generic embedder configuration (optional, provider-agnostic)"
    )
    llm: LLMSettings | None = Field(
        default=None, description="Generic LLM configuration (optional, provider-agnostic)"
    )
    lmstudio: LMStudioSettings = Field(
        default_factory=LMStudioSettings, description="LMStudio configuration (required)"
    )
    elasticsearch: ElasticsearchSettings = Field(
        default_factory=ElasticsearchSettings, description="Elasticsearch configuration"
    )
    chunking: ChunkingSettings = Field(
        default_factory=ChunkingSettings, description="Chunking configuration"
    )
    retrieval: RetrievalSettings = Field(
        default_factory=RetrievalSettings, description="Retrieval configuration"
    )
    circuit_breaker: CircuitBreakerSettings = Field(
        default_factory=CircuitBreakerSettings, description="Circuit breaker configuration"
    )
    health: HealthSettings = Field(
        default_factory=HealthSettings, description="Health check configuration"
    )
    file_upload: FileUploadSettings = Field(
        default_factory=FileUploadSettings, description="File upload configuration"
    )


# Global singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings singleton.

    This function provides thread-safe access to the application settings.
    Settings are loaded once on first call and cached for subsequent calls.

    Returns:
        Settings: The global settings instance

    Example:
        >>> from src.config.settings import get_settings
        >>> settings = get_settings()
        >>> print(settings.lmstudio.base_url)
        http://localhost:1234/v1
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the settings singleton.

    This function is primarily useful for testing to force reloading
    of settings from environment variables.

    Warning:
        This should not be used in production code.
    """
    global _settings
    _settings = None
