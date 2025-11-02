"""Text embedding generation using LiteLLM and LMStudio."""

import logging

import litellm

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class Embedder:
    """Generates embeddings using any LLM provider via LiteLLM.

    Supports multiple providers (OpenAI, LMStudio, Anthropic, etc.) through
    unified configuration. Prefers generic embedder settings but falls back
    to LMStudio-specific settings for backward compatibility.
    """

    def __init__(self):
        """Initialize embedder with configuration from settings."""
        settings = get_settings()

        # Prefer generic embedder settings, fall back to LMStudio
        if settings.embedder:
            self.provider = settings.embedder.provider
            self.base_url = settings.embedder.base_url
            self.model = settings.embedder.model
            self.api_key = settings.embedder.api_key.get_secret_value()
            self.timeout = settings.embedder.timeout
            logger.info(
                f"Embedder initialized with provider={self.provider}, "
                f"model={self.model}, base_url={self.base_url}"
            )
        else:
            # Backward compatibility: use LMStudio settings
            self.provider = "lmstudio"
            self.base_url = settings.lmstudio.base_url
            self.model = settings.lmstudio.embedding_model
            self.api_key = (
                settings.lmstudio.api_key.get_secret_value()
                if settings.lmstudio.api_key
                else "lmstudio"
            )
            self.timeout = settings.lmstudio.timeout
            logger.info(
                f"Embedder initialized with model={self.model}, base_url={self.base_url} "
                "(using LMStudio settings for backward compatibility)"
            )

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            RuntimeError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            logger.debug(f"Generating embedding for text ({len(text)} characters)")

            # Use LiteLLM to generate embedding
            response = litellm.embedding(
                model=self.model,
                input=[text],
                api_base=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout,
            )

            # Extract embedding from response
            embedding = response.data[0]["embedding"]

            logger.debug(f"Generated embedding with dimension {len(embedding)}")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}") from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            RuntimeError: If batch embedding generation fails
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("Cannot embed batch with all empty texts")

        try:
            logger.info(f"Generating embeddings for batch of {len(valid_texts)} texts")

            # Use LiteLLM to generate embeddings in batch
            response = litellm.embedding(
                model=self.model,
                input=valid_texts,
                api_base=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout,
            )

            # Extract embeddings from response
            embeddings = [item["embedding"] for item in response.data]

            logger.info(
                f"Successfully generated {len(embeddings)} embeddings, "
                f"dimension={len(embeddings[0]) if embeddings else 0}"
            )

            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise RuntimeError(f"Failed to generate batch embeddings: {e}") from e
