"""LLM interface using LiteLLM for chat completions.

This module provides a provider-agnostic interface for chat completion using LiteLLM.
Supports multiple providers (OpenAI, LMStudio, Anthropic, etc.) through unified
configuration. Prefers generic LLM settings but falls back to LMStudio-specific
settings for backward compatibility.

Includes circuit breaker protection to prevent cascading failures when the LLM
service is unavailable.

Example:
    >>> from src.ai_models.litellm_interface import LLMInterface
    >>> llm = LLMInterface()
    >>> messages = [{"role": "user", "content": "Hello!"}]
    >>> response = llm.chat_completion(messages)
    >>> print(response)
    "Hello! How can I help you today?"
"""

import logging

import litellm

from src.config.settings import get_settings
from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerError

logger = logging.getLogger(__name__)


class LLMInterface:
    """Generates chat completions using any LLM provider via LiteLLM.

    Supports multiple providers (OpenAI, LMStudio, Anthropic, etc.) through
    unified configuration. Prefers generic LLM settings but falls back
    to LMStudio-specific settings for backward compatibility.

    Stateless design: Each completion is independent with no conversation memory.

    Includes circuit breaker protection to prevent cascading failures and provide
    graceful degradation when the LLM service is unavailable.

    Attributes:
        provider: Name of the LLM provider (e.g., 'lmstudio', 'openai')
        base_url: API base URL for the provider
        model: Model name to use for completions
        api_key: API key for authentication
        timeout: Request timeout in seconds
        default_temperature: Default sampling temperature
        default_max_tokens: Default maximum tokens in response
        circuit_breaker: Circuit breaker for resilience
    """

    def __init__(self):
        """Initialize LLM interface with configuration from settings."""
        settings = get_settings()

        # Initialize circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker()

        # Prefer generic LLM settings, fall back to LMStudio
        if settings.llm:
            self.provider = settings.llm.provider
            self.base_url = settings.llm.base_url
            self.model = settings.llm.model
            self.api_key = settings.llm.api_key.get_secret_value()
            self.timeout = settings.llm.timeout
            self.default_temperature = settings.llm.temperature
            self.default_max_tokens = settings.llm.max_tokens
            logger.info(
                f"LLM initialized with provider={self.provider}, "
                f"model={self.model}, base_url={self.base_url}"
            )
        else:
            # Backward compatibility: use LMStudio settings
            self.provider = "lmstudio"
            self.base_url = settings.lmstudio.base_url
            self.model = settings.lmstudio.chat_model
            self.api_key = (
                settings.lmstudio.api_key.get_secret_value()
                if settings.lmstudio.api_key
                else "lmstudio"
            )
            self.timeout = settings.lmstudio.timeout
            self.default_temperature = 0.7
            self.default_max_tokens = 15000
            logger.info(
                f"LLM initialized with model={self.model}, base_url={self.base_url} "
                "(using LMStudio settings for backward compatibility)"
            )

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate chat completion (stateless).

        This method generates a single completion without maintaining conversation
        history. Each call is independent.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                     Roles: 'system', 'user', 'assistant'
                     Example: [
                         {"role": "system", "content": "You are a helpful assistant."},
                         {"role": "user", "content": "What is Python?"}
                     ]
            temperature: Sampling temperature (0.0-2.0). Lower values are more
                        deterministic. Uses default if None.
            max_tokens: Maximum tokens in response. Uses default if None.

        Returns:
            Generated response text as a string

        Raises:
            ValueError: If messages is empty or has invalid structure
            RuntimeError: If completion generation fails

        Example:
            >>> llm = LLMInterface()
            >>> messages = [{"role": "user", "content": "Hello!"}]
            >>> response = llm.chat_completion(messages, temperature=0.7)
            >>> print(response)
            "Hello! How can I help you today?"
        """
        if not messages:
            raise ValueError("messages list cannot be empty")

        # Validate message structure
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"Message {i} must be a dictionary")
            if "role" not in msg or "content" not in msg:
                raise ValueError(f"Message {i} must have 'role' and 'content' keys")
            if msg["role"] not in ["system", "user", "assistant"]:
                raise ValueError(
                    f"Message {i} has invalid role '{msg['role']}'. "
                    "Must be 'system', 'user', or 'assistant'"
                )

        # Use defaults if not provided
        temperature = temperature if temperature is not None else self.default_temperature
        max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens

        # Validate temperature
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")

        # Validate max_tokens
        if max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")

        try:
            logger.debug(
                f"Generating completion: messages={len(messages)}, "
                f"temperature={temperature}, max_tokens={max_tokens}"
            )

            # Define the LLM call function for circuit breaker
            def _call_llm():
                response = litellm.completion(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_base=self.base_url,
                    api_key=self.api_key,
                    timeout=self.timeout,
                )
                return response.choices[0].message.content

            # Execute with circuit breaker protection
            content = self.circuit_breaker.call(_call_llm)

            logger.debug(f"Generated completion ({len(content)} characters)")

            return content

        except CircuitBreakerError as e:
            # Circuit is open - provide fallback response
            logger.error(f"Circuit breaker is open: {e}")
            circuit_state = self.circuit_breaker.get_state()
            fallback_message = (
                "The AI service is temporarily unavailable due to repeated failures. "
                f"The service will attempt to recover automatically. "
                f"Current state: {circuit_state['state']}, "
                f"failures: {circuit_state['failure_count']}. "
                "Please try again in a moment."
            )
            raise RuntimeError(fallback_message) from e

        except Exception as e:
            logger.error(f"Failed to generate completion: {e}")
            raise RuntimeError(f"Failed to generate completion: {e}") from e

    def generate_answer(
        self,
        query: str,
        context: list[str],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate answer based on query and context (RAG-specific).

        This method formats the context with reference numbers [1], [2], etc.,
        and constructs a proper prompt for RAG-style question answering.

        Args:
            query: User question/query
            context: List of context chunks to use for answering. Each chunk
                    will be numbered [1], [2], etc. in the prompt.
            system_prompt: Optional custom system instructions. If None, uses
                          a default RAG-optimized prompt.
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override

        Returns:
            Generated answer text

        Raises:
            ValueError: If query or context is invalid
            RuntimeError: If answer generation fails

        Example:
            >>> llm = LLMInterface()
            >>> query = "What is Python?"
            >>> context = [
            ...     "Python is a high-level programming language.",
            ...     "It was created by Guido van Rossum in 1991."
            ... ]
            >>> answer = llm.generate_answer(query, context)
            >>> print(answer)
            "Python is a high-level programming language [1] created by
            Guido van Rossum in 1991 [2]."
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        if not context:
            raise ValueError("context list cannot be empty")

        # Filter out empty context chunks
        valid_context = [c for c in context if c and c.strip()]
        if not valid_context:
            raise ValueError("context list contains only empty strings")

        # Build context string with reference numbers
        context_str = "\n\n".join([f"[{i+1}] {chunk}" for i, chunk in enumerate(valid_context)])

        # Build messages
        messages = []

        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            default_prompt = (
                "You are a helpful assistant that answers questions based on the provided "
                "context. Always cite your sources using the reference numbers [1], [2], etc. "
                "If the context doesn't contain enough information to answer the question, "
                "clearly state what information is missing. Be accurate, concise, and helpful."
            )
            messages.append({"role": "system", "content": default_prompt})

        # Add user message with context and question
        user_message = f"Context:\n{context_str}\n\nQuestion: {query}\n\nAnswer:"
        messages.append({"role": "user", "content": user_message})

        logger.info(f"Generating answer for query: {query[:100]}...")
        logger.debug(f"Using {len(valid_context)} context chunks")

        # Generate completion
        return self.chat_completion(
            messages=messages, temperature=temperature, max_tokens=max_tokens
        )
