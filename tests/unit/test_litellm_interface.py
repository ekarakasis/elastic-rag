"""Unit tests for LLM interface (with mocked LiteLLM).

This module tests the LLMInterface class with comprehensive coverage of:
- Initialization with both generic LLM and LMStudio settings
- Chat completion with various parameters
- Answer generation for RAG
- Error handling and validation
- Edge cases and boundary conditions
"""

from unittest.mock import MagicMock, patch

import pytest

from src.ai_models.litellm_interface import LLMInterface


@pytest.fixture
def llm_interface():
    """Create an LLMInterface instance."""
    return LLMInterface()


@pytest.fixture
def mock_completion_response():
    """Create a mock completion response from LiteLLM."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is a test response from the LLM."
    return mock_response


@pytest.fixture
def simple_messages():
    """Create a simple message list for testing."""
    return [{"role": "user", "content": "Hello, how are you?"}]


@pytest.fixture
def complex_messages():
    """Create a complex message list with system prompt."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Python?"},
    ]


# === Initialization Tests ===


def test_llm_interface_initialization(llm_interface):
    """Test LLMInterface initializes correctly."""
    assert llm_interface.base_url is not None
    assert llm_interface.model is not None
    assert llm_interface.timeout > 0
    assert 0.0 <= llm_interface.default_temperature <= 2.0
    assert llm_interface.default_max_tokens > 0
    assert llm_interface.provider is not None


def test_llm_interface_initialization_with_generic_llm_settings(llm_interface):
    """Test that LLM interface prefers generic LLM settings when available."""
    # Our .env has LLM__ settings, so it should use those
    assert llm_interface.provider == "lmstudio"
    assert llm_interface.default_max_tokens == 15000  # From LLM__ settings


# === Chat Completion Tests ===


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_chat_completion_success(mock_completion, llm_interface, mock_completion_response):
    """Test successful chat completion."""
    mock_completion.return_value = mock_completion_response

    messages = [{"role": "user", "content": "Hello"}]
    result = llm_interface.chat_completion(messages)

    assert isinstance(result, str)
    assert result == "This is a test response from the LLM."
    mock_completion.assert_called_once()


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_chat_completion_with_system_message(
    mock_completion, llm_interface, mock_completion_response, complex_messages
):
    """Test chat completion with system message."""
    mock_completion.return_value = mock_completion_response

    result = llm_interface.chat_completion(complex_messages)

    assert isinstance(result, str)
    # Verify the messages were passed correctly
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["messages"] == complex_messages


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_chat_completion_with_custom_temperature(
    mock_completion, llm_interface, mock_completion_response, simple_messages
):
    """Test chat completion with custom temperature."""
    mock_completion.return_value = mock_completion_response

    result = llm_interface.chat_completion(simple_messages, temperature=0.5)

    assert isinstance(result, str)
    # Verify temperature was passed to LiteLLM
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["temperature"] == 0.5


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_chat_completion_with_custom_max_tokens(
    mock_completion, llm_interface, mock_completion_response, simple_messages
):
    """Test chat completion with custom max_tokens."""
    mock_completion.return_value = mock_completion_response

    result = llm_interface.chat_completion(simple_messages, max_tokens=500)

    assert isinstance(result, str)
    # Verify max_tokens was passed to LiteLLM
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["max_tokens"] == 500


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_chat_completion_with_both_params(
    mock_completion, llm_interface, mock_completion_response, simple_messages
):
    """Test chat completion with both temperature and max_tokens."""
    mock_completion.return_value = mock_completion_response

    result = llm_interface.chat_completion(simple_messages, temperature=0.3, max_tokens=2000)

    assert isinstance(result, str)
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["temperature"] == 0.3
    assert call_kwargs["max_tokens"] == 2000


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_chat_completion_uses_defaults(
    mock_completion, llm_interface, mock_completion_response, simple_messages
):
    """Test that chat completion uses default values when not specified."""
    mock_completion.return_value = mock_completion_response

    llm_interface.chat_completion(simple_messages)

    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["temperature"] == llm_interface.default_temperature
    assert call_kwargs["max_tokens"] == llm_interface.default_max_tokens


def test_chat_completion_empty_messages(llm_interface):
    """Test that empty messages list raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.chat_completion([])

    assert "cannot be empty" in str(exc_info.value).lower()


def test_chat_completion_invalid_message_not_dict(llm_interface):
    """Test that non-dict message raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.chat_completion(["not a dict"])

    assert "must be a dictionary" in str(exc_info.value).lower()


def test_chat_completion_missing_role(llm_interface):
    """Test that message without 'role' raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.chat_completion([{"content": "Hello"}])

    assert "role" in str(exc_info.value).lower() and "content" in str(exc_info.value).lower()


def test_chat_completion_missing_content(llm_interface):
    """Test that message without 'content' raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.chat_completion([{"role": "user"}])

    assert "role" in str(exc_info.value).lower() and "content" in str(exc_info.value).lower()


def test_chat_completion_invalid_role(llm_interface):
    """Test that invalid role raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.chat_completion([{"role": "invalid", "content": "Test"}])

    assert "invalid role" in str(exc_info.value).lower()


def test_chat_completion_invalid_temperature_negative(llm_interface, simple_messages):
    """Test that negative temperature raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.chat_completion(simple_messages, temperature=-0.1)

    assert "temperature" in str(exc_info.value).lower()


def test_chat_completion_invalid_temperature_too_high(llm_interface, simple_messages):
    """Test that temperature > 2.0 raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.chat_completion(simple_messages, temperature=2.5)

    assert "temperature" in str(exc_info.value).lower()


def test_chat_completion_temperature_edge_cases(llm_interface, simple_messages):
    """Test temperature edge cases (0.0 and 2.0 should be valid)."""
    # Mock the completion to avoid actual API calls
    with patch("src.ai_models.litellm_interface.litellm.completion") as mock_completion:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_completion.return_value = mock_response

        # 0.0 should be valid
        result1 = llm_interface.chat_completion(simple_messages, temperature=0.0)
        assert result1 == "Response"

        # 2.0 should be valid
        result2 = llm_interface.chat_completion(simple_messages, temperature=2.0)
        assert result2 == "Response"


def test_chat_completion_invalid_max_tokens_negative(llm_interface, simple_messages):
    """Test that negative max_tokens raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.chat_completion(simple_messages, max_tokens=-100)

    assert "max_tokens" in str(exc_info.value).lower()


def test_chat_completion_invalid_max_tokens_zero(llm_interface, simple_messages):
    """Test that zero max_tokens raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.chat_completion(simple_messages, max_tokens=0)

    assert "max_tokens" in str(exc_info.value).lower()


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_chat_completion_api_error(mock_completion, llm_interface, simple_messages):
    """Test handling of API errors."""
    mock_completion.side_effect = Exception("API connection failed")

    with pytest.raises(RuntimeError) as exc_info:
        llm_interface.chat_completion(simple_messages)

    assert "Failed to generate completion" in str(exc_info.value)
    assert "API connection failed" in str(exc_info.value)


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_chat_completion_timeout_error(mock_completion, llm_interface, simple_messages):
    """Test handling of timeout errors."""
    mock_completion.side_effect = TimeoutError("Request timed out")

    with pytest.raises(RuntimeError) as exc_info:
        llm_interface.chat_completion(simple_messages)

    assert "Failed to generate completion" in str(exc_info.value)


# === Generate Answer Tests (RAG-specific) ===


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_generate_answer_success(mock_completion, llm_interface, mock_completion_response):
    """Test successful answer generation."""
    mock_completion.return_value = mock_completion_response

    query = "What is Python?"
    context = ["Python is a programming language.", "It was created by Guido van Rossum."]

    result = llm_interface.generate_answer(query, context)

    assert isinstance(result, str)
    assert result == "This is a test response from the LLM."
    mock_completion.assert_called_once()


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_generate_answer_formats_context_with_numbers(
    mock_completion, llm_interface, mock_completion_response
):
    """Test that context chunks are formatted with reference numbers."""
    mock_completion.return_value = mock_completion_response

    query = "Test query"
    context = ["Chunk 1", "Chunk 2", "Chunk 3"]

    llm_interface.generate_answer(query, context)

    # Check that the user message contains formatted context
    call_kwargs = mock_completion.call_args.kwargs
    messages = call_kwargs["messages"]
    user_message = messages[-1]["content"]

    assert "[1]" in user_message
    assert "[2]" in user_message
    assert "[3]" in user_message
    assert "Chunk 1" in user_message
    assert "Chunk 2" in user_message
    assert "Chunk 3" in user_message


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_generate_answer_uses_default_system_prompt(
    mock_completion, llm_interface, mock_completion_response
):
    """Test that default system prompt is used when none provided."""
    mock_completion.return_value = mock_completion_response

    query = "Test"
    context = ["Context"]

    llm_interface.generate_answer(query, context)

    # Check system message
    call_kwargs = mock_completion.call_args.kwargs
    messages = call_kwargs["messages"]
    system_message = messages[0]

    assert system_message["role"] == "system"
    assert "cite your sources" in system_message["content"].lower()
    assert "reference numbers" in system_message["content"].lower()


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_generate_answer_uses_custom_system_prompt(
    mock_completion, llm_interface, mock_completion_response
):
    """Test that custom system prompt is used when provided."""
    mock_completion.return_value = mock_completion_response

    query = "Test"
    context = ["Context"]
    custom_prompt = "You are a test assistant with special instructions."

    llm_interface.generate_answer(query, context, system_prompt=custom_prompt)

    # Check system message
    call_kwargs = mock_completion.call_args.kwargs
    messages = call_kwargs["messages"]
    system_message = messages[0]

    assert system_message["role"] == "system"
    assert system_message["content"] == custom_prompt


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_generate_answer_with_custom_temperature(
    mock_completion, llm_interface, mock_completion_response
):
    """Test answer generation with custom temperature."""
    mock_completion.return_value = mock_completion_response

    query = "Test"
    context = ["Context"]

    llm_interface.generate_answer(query, context, temperature=0.3)

    # Verify temperature was passed
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["temperature"] == 0.3


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_generate_answer_with_custom_max_tokens(
    mock_completion, llm_interface, mock_completion_response
):
    """Test answer generation with custom max_tokens."""
    mock_completion.return_value = mock_completion_response

    query = "Test"
    context = ["Context"]

    llm_interface.generate_answer(query, context, max_tokens=5000)

    # Verify max_tokens was passed
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["max_tokens"] == 5000


def test_generate_answer_empty_query(llm_interface):
    """Test that empty query raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.generate_answer("", ["Context"])

    assert "query" in str(exc_info.value).lower()


def test_generate_answer_whitespace_only_query(llm_interface):
    """Test that whitespace-only query raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.generate_answer("   \n\t  ", ["Context"])

    assert "query" in str(exc_info.value).lower()


def test_generate_answer_empty_context(llm_interface):
    """Test that empty context list raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.generate_answer("Query", [])

    assert "context" in str(exc_info.value).lower()


def test_generate_answer_context_all_empty_strings(llm_interface):
    """Test that context with all empty strings raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        llm_interface.generate_answer("Query", ["", "   ", "\n\t"])

    assert "context" in str(exc_info.value).lower()
    assert "empty" in str(exc_info.value).lower()


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_generate_answer_filters_empty_context(
    mock_completion, llm_interface, mock_completion_response
):
    """Test that empty context chunks are filtered out."""
    mock_completion.return_value = mock_completion_response

    query = "Test"
    context = ["Valid chunk 1", "", "Valid chunk 2", "   "]

    llm_interface.generate_answer(query, context)

    # Check that only valid chunks were included
    call_kwargs = mock_completion.call_args.kwargs
    messages = call_kwargs["messages"]
    user_message = messages[-1]["content"]

    assert "[1] Valid chunk 1" in user_message
    assert "[2] Valid chunk 2" in user_message
    # Should only have 2 reference numbers
    assert "[3]" not in user_message


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_generate_answer_constructs_proper_messages(
    mock_completion, llm_interface, mock_completion_response
):
    """Test that messages are constructed properly."""
    mock_completion.return_value = mock_completion_response

    query = "What is AI?"
    context = ["AI is artificial intelligence."]

    llm_interface.generate_answer(query, context)

    call_kwargs = mock_completion.call_args.kwargs
    messages = call_kwargs["messages"]

    # Should have 2 messages: system and user
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    # User message should contain context, question, and answer prompt
    user_content = messages[1]["content"]
    assert "Context:" in user_content
    assert "[1]" in user_content
    assert "Question:" in user_content
    assert query in user_content
    assert "Answer:" in user_content


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_generate_answer_api_error(mock_completion, llm_interface):
    """Test handling of API errors during answer generation."""
    mock_completion.side_effect = Exception("API Error")

    query = "Test"
    context = ["Context"]

    with pytest.raises(RuntimeError) as exc_info:
        llm_interface.generate_answer(query, context)

    assert "Failed to generate completion" in str(exc_info.value)


# === Circuit Breaker Integration Tests ===


def test_llm_interface_has_circuit_breaker(llm_interface):
    """Test that LLMInterface initializes with circuit breaker."""
    assert hasattr(llm_interface, "circuit_breaker")
    assert llm_interface.circuit_breaker is not None
    assert llm_interface.circuit_breaker.is_closed


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_circuit_breaker_opens_after_failures(mock_completion, llm_interface):
    """Test that circuit breaker opens after consecutive failures."""
    mock_completion.side_effect = Exception("Service unavailable")

    messages = [{"role": "user", "content": "Test"}]
    threshold = llm_interface.circuit_breaker.failure_threshold

    # Cause failures up to threshold
    for _ in range(threshold):
        with pytest.raises(RuntimeError):
            llm_interface.chat_completion(messages)

    # Circuit should now be open
    assert llm_interface.circuit_breaker.is_open


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_circuit_breaker_fallback_response(mock_completion, llm_interface):
    """Test that circuit breaker provides fallback response when open."""
    mock_completion.side_effect = Exception("Service unavailable")

    messages = [{"role": "user", "content": "Test"}]
    threshold = llm_interface.circuit_breaker.failure_threshold

    # Open the circuit
    for _ in range(threshold):
        with pytest.raises(RuntimeError):
            llm_interface.chat_completion(messages)

    # Next call should get circuit breaker error with fallback
    with pytest.raises(RuntimeError) as exc_info:
        llm_interface.chat_completion(messages)

    error_msg = str(exc_info.value)
    assert "AI service is temporarily unavailable" in error_msg
    assert "repeated failures" in error_msg
    assert "try again in a moment" in error_msg


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_circuit_breaker_recovery(mock_completion, llm_interface, mock_completion_response):
    """Test that circuit breaker can recover after failures."""
    # First, cause failures
    mock_completion.side_effect = Exception("Service unavailable")
    threshold = llm_interface.circuit_breaker.failure_threshold

    messages = [{"role": "user", "content": "Test"}]

    for _ in range(threshold):
        with pytest.raises(RuntimeError):
            llm_interface.chat_completion(messages)

    assert llm_interface.circuit_breaker.is_open

    # Now simulate recovery: service comes back
    mock_completion.side_effect = None
    mock_completion.return_value = mock_completion_response

    # Manually transition to half-open for testing
    llm_interface.circuit_breaker.state = llm_interface.circuit_breaker.state.__class__("half_open")
    llm_interface.circuit_breaker.half_open_calls = 0

    # Make successful calls
    max_calls = llm_interface.circuit_breaker.half_open_max_calls
    for _ in range(max_calls):
        result = llm_interface.chat_completion(messages)
        assert result is not None

    # Circuit should be closed now
    assert llm_interface.circuit_breaker.is_closed


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_circuit_breaker_state_in_error_message(mock_completion, llm_interface):
    """Test that error messages include circuit breaker state."""
    mock_completion.side_effect = Exception("Service unavailable")

    messages = [{"role": "user", "content": "Test"}]
    threshold = llm_interface.circuit_breaker.failure_threshold

    # Open the circuit
    for _ in range(threshold):
        with pytest.raises(RuntimeError):
            llm_interface.chat_completion(messages)

    # Check error includes state information
    with pytest.raises(RuntimeError) as exc_info:
        llm_interface.chat_completion(messages)

    error_msg = str(exc_info.value)
    assert "state:" in error_msg.lower() or "Current state:" in error_msg
    assert "failures:" in error_msg.lower()


@patch("src.ai_models.litellm_interface.litellm.completion")
def test_successful_call_resets_circuit_breaker(
    mock_completion, llm_interface, mock_completion_response
):
    """Test that successful calls reset circuit breaker failure count."""
    messages = [{"role": "user", "content": "Test"}]

    # Cause a few failures (but not enough to open)
    mock_completion.side_effect = Exception("Temporary error")
    for _ in range(2):
        with pytest.raises(RuntimeError):
            llm_interface.chat_completion(messages)

    assert llm_interface.circuit_breaker.failure_count == 2

    # Successful call should reset
    mock_completion.side_effect = None
    mock_completion.return_value = mock_completion_response

    result = llm_interface.chat_completion(messages)
    assert result is not None
    assert llm_interface.circuit_breaker.failure_count == 0


def test_circuit_breaker_get_state(llm_interface):
    """Test that circuit breaker state can be retrieved."""
    state = llm_interface.circuit_breaker.get_state()

    assert "state" in state
    assert "failure_count" in state
    assert "last_failure" in state
    assert state["state"] == "closed"
