"""Unit tests for configuration management.

This module tests all configuration classes, validation logic, secret handling,
and environment variable loading.
"""

import os

import pytest
from pydantic import SecretStr, ValidationError

from src.config.secrets import SecretConfig
from src.config.settings import (
    AppSettings,
    ChunkingSettings,
    CircuitBreakerSettings,
    ElasticsearchSettings,
    HealthSettings,
    LLMSettings,
    LMStudioSettings,
    RetrievalSettings,
    Settings,
    get_settings,
    reset_settings,
)


class TestAppSettings:
    """Tests for AppSettings configuration."""

    def test_app_settings_defaults(self):
        """Test that AppSettings has correct default values."""
        settings = AppSettings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.log_level == "INFO"
        assert settings.environment == "development"

    def test_app_settings_custom_values(self):
        """Test AppSettings with custom values."""
        settings = AppSettings(
            host="127.0.0.1", port=9000, log_level="DEBUG", environment="production"
        )
        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.log_level == "DEBUG"
        assert settings.environment == "production"


class TestLMStudioSettings:
    """Tests for LMStudioSettings configuration."""

    def test_lmstudio_settings_valid(self):
        """Test valid LMStudio configuration."""
        settings = LMStudioSettings(
            base_url="http://localhost:1234/v1",
            embedding_model="nomic-embed-text",
            chat_model="llama-3.2-3b-instruct",
        )
        assert settings.base_url == "http://localhost:1234/v1"
        assert settings.embedding_model == "nomic-embed-text"
        assert settings.chat_model == "llama-3.2-3b-instruct"
        assert settings.timeout == 30
        assert settings.api_key is None

    def test_lmstudio_settings_with_api_key(self):
        """Test LMStudio settings with API key."""
        settings = LMStudioSettings(
            base_url="http://localhost:1234/v1",
            embedding_model="test-model",
            chat_model="test-chat",
            api_key="sk-test-key-123",
        )
        assert settings.api_key is not None
        # Secret should be masked in string representation
        assert "sk-test-key-123" not in str(settings)
        assert "sk-test-key-123" not in repr(settings)

    def test_lmstudio_url_validation_invalid(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioSettings(base_url="invalid-url", embedding_model="test", chat_model="test")
        assert "base_url must start with http://" in str(exc_info.value)

    def test_lmstudio_url_validation_https(self):
        """Test that HTTPS URLs are accepted."""
        settings = LMStudioSettings(
            base_url="https://api.example.com/v1", embedding_model="test", chat_model="test"
        )
        assert settings.base_url == "https://api.example.com/v1"

    def test_lmstudio_url_trailing_slash_removed(self):
        """Test that trailing slashes are removed from URL."""
        settings = LMStudioSettings(
            base_url="http://localhost:1234/v1/", embedding_model="test", chat_model="test"
        )
        assert settings.base_url == "http://localhost:1234/v1"

    def test_lmstudio_invalid_timeout(self):
        """Test that negative timeout is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioSettings(
                base_url="http://localhost:1234/v1",
                embedding_model="test",
                chat_model="test",
                timeout=-1,
            )
        assert "timeout must be a positive integer" in str(exc_info.value)

    def test_lmstudio_zero_timeout(self):
        """Test that zero timeout is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LMStudioSettings(
                base_url="http://localhost:1234/v1",
                embedding_model="test",
                chat_model="test",
                timeout=0,
            )
        assert "timeout must be a positive integer" in str(exc_info.value)


class TestLLMSettings:
    """Tests for LLMSettings configuration (generic LLM provider)."""

    def test_llm_settings_valid(self):
        """Test valid LLM configuration."""

        settings = LLMSettings(
            provider="lmstudio",
            base_url="http://localhost:1234/v1",
            model="openai/qwen3-30b-a3b-mlx",
        )
        assert settings.provider == "lmstudio"
        assert settings.base_url == "http://localhost:1234/v1"
        assert settings.model == "openai/qwen3-30b-a3b-mlx"
        assert settings.timeout == 30
        assert settings.temperature == 0.7
        assert settings.max_tokens == 15000

    def test_llm_settings_with_custom_params(self):
        """Test LLM settings with custom parameters."""

        settings = LLMSettings(
            provider="openai",
            base_url="https://api.openai.com/v1",
            model="gpt-4",
            api_key="sk-test-key",
            timeout=60,
            temperature=0.5,
            max_tokens=8000,
        )
        assert settings.provider == "openai"
        assert settings.temperature == 0.5
        assert settings.max_tokens == 8000
        assert settings.timeout == 60
        # API key should be masked
        assert "sk-test-key" not in str(settings)

    def test_llm_url_validation_invalid(self):
        """Test that invalid URLs are rejected."""

        with pytest.raises(ValidationError) as exc_info:
            LLMSettings(base_url="invalid-url", model="test")
        assert "base_url must start with http://" in str(exc_info.value)

    def test_llm_url_validation_https(self):
        """Test that HTTPS URLs are accepted."""

        settings = LLMSettings(base_url="https://api.openai.com/v1", model="gpt-4")
        assert settings.base_url == "https://api.openai.com/v1"

    def test_llm_url_trailing_slash_removed(self):
        """Test that trailing slashes are removed from URL."""

        settings = LLMSettings(base_url="http://localhost:1234/v1/", model="test")
        assert settings.base_url == "http://localhost:1234/v1"

    def test_llm_invalid_timeout(self):
        """Test that negative timeout is rejected."""

        with pytest.raises(ValidationError) as exc_info:
            LLMSettings(base_url="http://localhost:1234/v1", model="test", timeout=-1)
        assert "timeout must be a positive integer" in str(exc_info.value)

    def test_llm_zero_timeout(self):
        """Test that zero timeout is rejected."""

        with pytest.raises(ValidationError) as exc_info:
            LLMSettings(base_url="http://localhost:1234/v1", model="test", timeout=0)
        assert "timeout must be a positive integer" in str(exc_info.value)

    def test_llm_temperature_validation_negative(self):
        """Test that negative temperature is rejected."""

        with pytest.raises(ValidationError) as exc_info:
            LLMSettings(base_url="http://localhost:1234/v1", model="test", temperature=-0.1)
        assert "temperature must be between 0.0 and 2.0" in str(exc_info.value)

    def test_llm_temperature_validation_too_high(self):
        """Test that temperature > 2.0 is rejected."""

        with pytest.raises(ValidationError) as exc_info:
            LLMSettings(base_url="http://localhost:1234/v1", model="test", temperature=2.5)
        assert "temperature must be between 0.0 and 2.0" in str(exc_info.value)

    def test_llm_temperature_edge_cases(self):
        """Test temperature edge cases (0.0 and 2.0)."""

        # 0.0 should be valid
        settings1 = LLMSettings(base_url="http://localhost:1234/v1", model="test", temperature=0.0)
        assert settings1.temperature == 0.0

        # 2.0 should be valid
        settings2 = LLMSettings(base_url="http://localhost:1234/v1", model="test", temperature=2.0)
        assert settings2.temperature == 2.0

    def test_llm_max_tokens_validation_negative(self):
        """Test that negative max_tokens is rejected."""

        with pytest.raises(ValidationError) as exc_info:
            LLMSettings(base_url="http://localhost:1234/v1", model="test", max_tokens=-100)
        assert "max_tokens must be a positive integer" in str(exc_info.value)

    def test_llm_max_tokens_validation_zero(self):
        """Test that zero max_tokens is rejected."""

        with pytest.raises(ValidationError) as exc_info:
            LLMSettings(base_url="http://localhost:1234/v1", model="test", max_tokens=0)
        assert "max_tokens must be a positive integer" in str(exc_info.value)

    def test_llm_max_tokens_large_value(self):
        """Test that large max_tokens values are accepted."""

        settings = LLMSettings(base_url="http://localhost:1234/v1", model="test", max_tokens=40000)
        assert settings.max_tokens == 40000


class TestElasticsearchSettings:
    """Tests for ElasticsearchSettings configuration."""

    def test_elasticsearch_settings_defaults(self):
        """Test Elasticsearch settings with defaults."""
        settings = ElasticsearchSettings()
        assert settings.host == "elasticsearch"
        assert settings.port == 9200
        assert settings.index == "documents"
        assert settings.username is None
        assert settings.password is None

    def test_elasticsearch_url_property(self):
        """Test that url property constructs correct URL."""
        settings = ElasticsearchSettings(host="localhost", port=9200)
        assert settings.url == "http://localhost:9200"

    def test_elasticsearch_with_auth(self):
        """Test Elasticsearch settings with authentication."""
        settings = ElasticsearchSettings(username="elastic_user", password="secret123")
        # Secrets should be masked
        assert "secret123" not in str(settings)
        assert "elastic_user" not in str(settings)
        # But should contain masked representation
        assert "**********" in str(settings)


class TestChunkingSettings:
    """Tests for ChunkingSettings configuration."""

    def test_chunking_settings_defaults(self):
        """Test chunking settings defaults."""
        settings = ChunkingSettings()
        assert settings.size == 512
        assert settings.overlap == 50

    def test_chunking_settings_custom(self):
        """Test chunking settings with custom values."""
        settings = ChunkingSettings(size=1000, overlap=100)
        assert settings.size == 1000
        assert settings.overlap == 100

    def test_chunking_size_too_small(self):
        """Test that chunk size below 100 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkingSettings(size=50)
        assert "chunk_size must be between 100 and 2000" in str(exc_info.value)

    def test_chunking_size_too_large(self):
        """Test that chunk size above 2000 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkingSettings(size=3000)
        assert "chunk_size must be between 100 and 2000" in str(exc_info.value)

    def test_chunking_negative_overlap(self):
        """Test that negative overlap is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkingSettings(overlap=-10)
        assert "overlap must be non-negative" in str(exc_info.value)


class TestRetrievalSettings:
    """Tests for RetrievalSettings configuration."""

    def test_retrieval_settings_defaults(self):
        """Test retrieval settings defaults."""
        settings = RetrievalSettings()
        assert settings.top_k == 5
        assert settings.similarity_threshold == 0.7

    def test_retrieval_settings_custom(self):
        """Test retrieval settings with custom values."""
        settings = RetrievalSettings(top_k=10, similarity_threshold=0.8)
        assert settings.top_k == 10
        assert settings.similarity_threshold == 0.8

    def test_retrieval_invalid_top_k(self):
        """Test that zero or negative top_k is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RetrievalSettings(top_k=0)
        assert "top_k must be a positive integer" in str(exc_info.value)

        with pytest.raises(ValidationError):
            RetrievalSettings(top_k=-1)

    def test_retrieval_threshold_below_zero(self):
        """Test that threshold below 0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RetrievalSettings(similarity_threshold=-0.1)
        assert "similarity_threshold must be between 0 and 1" in str(exc_info.value)

    def test_retrieval_threshold_above_one(self):
        """Test that threshold above 1 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RetrievalSettings(similarity_threshold=1.5)
        assert "similarity_threshold must be between 0 and 1" in str(exc_info.value)

    def test_retrieval_threshold_boundary_values(self):
        """Test that 0 and 1 are valid threshold values."""
        settings_zero = RetrievalSettings(similarity_threshold=0.0)
        assert settings_zero.similarity_threshold == 0.0

        settings_one = RetrievalSettings(similarity_threshold=1.0)
        assert settings_one.similarity_threshold == 1.0


class TestCircuitBreakerSettings:
    """Tests for CircuitBreakerSettings configuration."""

    def test_circuit_breaker_defaults(self):
        """Test circuit breaker defaults."""
        settings = CircuitBreakerSettings()
        assert settings.failure_threshold == 5
        assert settings.timeout_seconds == 60
        assert settings.half_open_max_calls == 3

    def test_circuit_breaker_invalid_values(self):
        """Test that zero or negative values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CircuitBreakerSettings(failure_threshold=0)
        assert "Circuit breaker values must be positive integers" in str(exc_info.value)

        with pytest.raises(ValidationError):
            CircuitBreakerSettings(timeout_seconds=-1)

        with pytest.raises(ValidationError):
            CircuitBreakerSettings(half_open_max_calls=0)


class TestHealthSettings:
    """Tests for HealthSettings configuration."""

    def test_health_settings_defaults(self):
        """Test health settings defaults."""
        settings = HealthSettings()
        assert settings.check_timeout == 1
        assert settings.startup_timeout == 30
        assert settings.readiness_interval == 5

    def test_health_settings_invalid_values(self):
        """Test that zero or negative values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            HealthSettings(check_timeout=0)
        assert "Health check timeout values must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError):
            HealthSettings(startup_timeout=-1)

        with pytest.raises(ValidationError):
            HealthSettings(readiness_interval=0)


class TestSecretConfig:
    """Tests for SecretConfig utility class."""

    def test_get_secret_value_with_value(self):
        """Test extracting value from SecretStr."""
        secret = SecretStr("my-secret-key")
        value = SecretConfig.get_secret_value(secret)
        assert value == "my-secret-key"

    def test_get_secret_value_with_none(self):
        """Test extracting value from None."""
        value = SecretConfig.get_secret_value(None)
        assert value == ""

    def test_is_secret_set_with_value(self):
        """Test checking if secret is set."""
        secret = SecretStr("my-key")
        assert SecretConfig.is_secret_set(secret) is True

    def test_is_secret_set_with_none(self):
        """Test checking if None secret is set."""
        assert SecretConfig.is_secret_set(None) is False

    def test_is_secret_set_with_empty_string(self):
        """Test checking if empty string secret is set."""
        secret = SecretStr("")
        assert SecretConfig.is_secret_set(secret) is False

    def test_is_secret_set_with_whitespace(self):
        """Test checking if whitespace-only secret is set."""
        secret = SecretStr("   ")
        assert SecretConfig.is_secret_set(secret) is False

    def test_secret_str_masking(self):
        """Test that SecretStr masks values in string representation."""
        secret = SecretStr("super-secret-password")
        assert "super-secret-password" not in str(secret)
        assert "super-secret-password" not in repr(secret)
        assert "**********" in str(secret)


class TestSettingsSingleton:
    """Tests for Settings singleton pattern."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()
        # Set required environment variables
        os.environ["LMSTUDIO__BASE_URL"] = "http://localhost:1234/v1"
        os.environ["LMSTUDIO__EMBEDDING_MODEL"] = "test-embed"
        os.environ["LMSTUDIO__CHAT_MODEL"] = "test-chat"

    def teardown_method(self):
        """Clean up environment variables after each test."""
        reset_settings()
        for key in list(os.environ.keys()):
            if key.startswith(("LMSTUDIO__", "APP__", "ELASTICSEARCH__")):
                del os.environ[key]

    def test_get_settings_returns_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reset_settings_clears_singleton(self):
        """Test that reset_settings clears the singleton."""
        settings1 = get_settings()
        reset_settings()
        settings2 = get_settings()
        assert settings1 is not settings2


class TestEnvironmentVariableLoading:
    """Tests for loading configuration from environment variables."""

    def setup_method(self):
        """Set up environment variables before each test."""
        reset_settings()
        os.environ["LMSTUDIO__BASE_URL"] = "http://localhost:1234/v1"
        os.environ["LMSTUDIO__EMBEDDING_MODEL"] = "test-embed"
        os.environ["LMSTUDIO__CHAT_MODEL"] = "test-chat"

    def teardown_method(self):
        """Clean up environment variables after each test."""
        reset_settings()
        for key in list(os.environ.keys()):
            if key.startswith(
                ("LMSTUDIO__", "APP__", "ELASTICSEARCH__", "CHUNKING__", "RETRIEVAL__")
            ):
                del os.environ[key]

    def test_load_from_environment_variables(self):
        """Test loading configuration from environment variables."""
        os.environ["APP__LOG_LEVEL"] = "DEBUG"
        os.environ["ELASTICSEARCH__HOST"] = "custom-host"
        os.environ["CHUNKING__SIZE"] = "1024"

        settings = get_settings()
        assert settings.app.log_level == "DEBUG"
        assert settings.elasticsearch.host == "custom-host"
        assert settings.chunking.size == 1024

    def test_nested_delimiter_syntax(self):
        """Test that double underscore works as nested delimiter."""
        os.environ["LMSTUDIO__BASE_URL"] = "https://api.test.com/v1"
        reset_settings()

        settings = get_settings()
        assert settings.lmstudio.base_url == "https://api.test.com/v1"

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case-insensitive."""
        os.environ["lmstudio__base_url"] = "http://test.com/v1"
        reset_settings()

        settings = get_settings()
        assert settings.lmstudio.base_url == "http://test.com/v1"

    def test_partial_configuration(self):
        """Test that partial configuration uses defaults."""
        # Only set required LMStudio vars, others should use defaults
        settings = get_settings()

        assert settings.app.host == "0.0.0.0"  # Default
        assert settings.app.port == 8000  # Default
        assert settings.chunking.size == 1024  # Default
        assert settings.lmstudio.base_url == "http://localhost:1234/v1"  # From env

    def test_type_conversion(self):
        """Test that environment variables are converted to correct types."""
        os.environ["APP__PORT"] = "9000"
        os.environ["CHUNKING__SIZE"] = "1000"
        os.environ["RETRIEVAL__SIMILARITY_THRESHOLD"] = "0.85"
        reset_settings()

        settings = get_settings()
        assert isinstance(settings.app.port, int)
        assert settings.app.port == 9000
        assert isinstance(settings.chunking.size, int)
        assert settings.chunking.size == 1000
        assert isinstance(settings.retrieval.similarity_threshold, float)
        assert settings.retrieval.similarity_threshold == 0.85


class TestMasterSettings:
    """Tests for the master Settings class."""

    def setup_method(self):
        """Set up required environment variables."""
        reset_settings()
        os.environ["LMSTUDIO__BASE_URL"] = "http://localhost:1234/v1"
        os.environ["LMSTUDIO__EMBEDDING_MODEL"] = "test-embed"
        os.environ["LMSTUDIO__CHAT_MODEL"] = "test-chat"

    def teardown_method(self):
        """Clean up after each test."""
        reset_settings()
        for key in list(os.environ.keys()):
            if key.startswith(("LMSTUDIO__", "APP__", "ELASTICSEARCH__")):
                del os.environ[key]

    def test_settings_has_all_sections(self):
        """Test that Settings includes all configuration sections."""
        settings = get_settings()

        assert hasattr(settings, "app")
        assert hasattr(settings, "embedder")
        assert hasattr(settings, "llm")
        assert hasattr(settings, "lmstudio")
        assert hasattr(settings, "elasticsearch")
        assert hasattr(settings, "chunking")
        assert hasattr(settings, "retrieval")
        assert hasattr(settings, "circuit_breaker")
        assert hasattr(settings, "health")

    def test_settings_section_types(self):
        """Test that all sections have correct types."""
        settings = get_settings()

        assert isinstance(settings.app, AppSettings)
        assert isinstance(settings.lmstudio, LMStudioSettings)
        assert isinstance(settings.elasticsearch, ElasticsearchSettings)
        assert isinstance(settings.chunking, ChunkingSettings)
        assert isinstance(settings.retrieval, RetrievalSettings)
        assert isinstance(settings.circuit_breaker, CircuitBreakerSettings)
        assert isinstance(settings.health, HealthSettings)

    def test_lmstudio_is_required(self):
        """Test that LMStudio configuration is required."""
        # Clear LMStudio env vars and prevent loading from .env file
        for key in list(os.environ.keys()):
            if key.startswith("LMSTUDIO__"):
                del os.environ[key]
        reset_settings()

        # Should raise validation error due to missing required fields
        # We need to create a Settings object directly without .env file
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                lmstudio=LMStudioSettings(
                    base_url=None, embedding_model="test", chat_model="test"
                )  # This should fail
            )
        # Verify it's because of missing base_url
        assert "base_url" in str(exc_info.value).lower() or "none" in str(exc_info.value).lower()
