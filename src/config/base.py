"""Base configuration classes for the Elastic RAG application.

This module provides the foundational configuration classes that all other
configuration sections inherit from. It sets up environment variable loading,
nested configuration support, and common settings behavior.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Base configuration class with common settings for all config sections.

    This class provides:
    - Automatic loading from .env files
    - Support for nested configuration using double underscore delimiter
    - Case-insensitive environment variable matching
    - UTF-8 encoding for env files
    - Ignores extra fields not defined in the model

    Example:
        For a nested field like `lmstudio.base_url`, you can set it using:
        LMSTUDIO__BASE_URL=http://localhost:1234/v1
    """

    model_config = SettingsConfigDict(
        # Load environment variables from .env file
        env_file=".env",
        env_file_encoding="utf-8",
        # Support nested configuration with double underscore
        # e.g., LMSTUDIO__BASE_URL maps to lmstudio.base_url
        env_nested_delimiter="__",
        # Make environment variable names case-insensitive
        case_sensitive=False,
        # Ignore extra fields in environment that aren't in the model
        extra="ignore",
    )
