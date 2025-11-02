"""Secret handling utilities for the Elastic RAG application.

This module provides utilities for safely handling sensitive configuration data
like API keys, passwords, and tokens. It uses Pydantic's SecretStr to ensure
secrets are masked in logs and string representations.
"""

from pydantic import SecretStr


class SecretConfig:
    """Utilities for handling secrets safely.

    This class provides helper methods for working with Pydantic SecretStr
    fields to ensure sensitive data is never accidentally exposed in logs,
    error messages, or debug output.
    """

    @staticmethod
    def get_secret_value(secret: SecretStr | None) -> str:
        """Safely extract the actual value from a SecretStr field.

        This method should only be used when the actual secret value is needed
        (e.g., when making API calls). The value should never be logged or
        included in error messages.

        Args:
            secret: A SecretStr field or None

        Returns:
            The actual secret value as a string, or empty string if None

        Example:
            >>> from pydantic import SecretStr
            >>> api_key = SecretStr("sk-1234567890")
            >>> SecretConfig.get_secret_value(api_key)
            'sk-1234567890'
            >>> print(api_key)  # Masked output
            '**********'
        """
        if secret is None:
            return ""
        return secret.get_secret_value()

    @staticmethod
    def is_secret_set(secret: SecretStr | None) -> bool:
        """Check if a secret has a non-empty value.

        This is useful for optional secrets to determine if they were provided.

        Args:
            secret: A SecretStr field or None

        Returns:
            True if secret is set and non-empty, False otherwise

        Example:
            >>> from pydantic import SecretStr
            >>> api_key = SecretStr("sk-1234")
            >>> SecretConfig.is_secret_set(api_key)
            True
            >>> SecretConfig.is_secret_set(None)
            False
        """
        if secret is None:
            return False
        value = secret.get_secret_value()
        return bool(value and value.strip())
