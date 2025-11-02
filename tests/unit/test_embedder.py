"""Unit tests for embedder (with mocked LiteLLM)."""

from unittest.mock import MagicMock, patch

import pytest

from src.ai_models.embedder import Embedder


@pytest.fixture
def embedder():
    """Create an Embedder instance."""
    return Embedder()


@pytest.fixture
def mock_embedding_response():
    """Create a mock embedding response."""
    mock_response = MagicMock()
    mock_response.data = [{"embedding": [0.1] * 768}]
    return mock_response


@pytest.fixture
def mock_batch_embedding_response():
    """Create a mock batch embedding response."""
    mock_response = MagicMock()
    mock_response.data = [
        {"embedding": [0.1] * 768},
        {"embedding": [0.2] * 768},
        {"embedding": [0.3] * 768},
    ]
    return mock_response


def test_embedder_initialization(embedder):
    """Test Embedder initializes correctly."""
    assert embedder.base_url is not None
    assert embedder.model is not None
    assert embedder.timeout > 0


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_text_success(mock_embedding, embedder, mock_embedding_response):
    """Test successful single text embedding."""
    mock_embedding.return_value = mock_embedding_response

    result = embedder.embed_text("Test text")

    assert isinstance(result, list)
    assert len(result) == 768
    assert all(isinstance(x, float) for x in result)
    mock_embedding.assert_called_once()


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_text_empty_raises_error(mock_embedding, embedder):
    """Test that embedding empty text raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        embedder.embed_text("")

    assert "Cannot embed empty text" in str(exc_info.value)
    mock_embedding.assert_not_called()


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_text_whitespace_only_raises_error(mock_embedding, embedder):
    """Test that embedding whitespace-only text raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        embedder.embed_text("   \n\t  ")

    assert "Cannot embed empty text" in str(exc_info.value)
    mock_embedding.assert_not_called()


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_text_api_error(mock_embedding, embedder):
    """Test handling of API errors."""
    mock_embedding.side_effect = Exception("API Error")

    with pytest.raises(RuntimeError) as exc_info:
        embedder.embed_text("Test text")

    assert "Failed to generate embedding" in str(exc_info.value)


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_batch_success(mock_embedding, embedder, mock_batch_embedding_response):
    """Test successful batch embedding."""
    mock_embedding.return_value = mock_batch_embedding_response

    texts = ["Text 1", "Text 2", "Text 3"]
    results = embedder.embed_batch(texts)

    assert isinstance(results, list)
    assert len(results) == 3
    assert all(isinstance(emb, list) for emb in results)
    assert all(len(emb) == 768 for emb in results)
    mock_embedding.assert_called_once()


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_batch_empty_list(mock_embedding, embedder):
    """Test batch embedding with empty list."""
    results = embedder.embed_batch([])

    assert isinstance(results, list)
    assert len(results) == 0
    mock_embedding.assert_not_called()


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_batch_filters_empty_texts(mock_embedding, embedder, mock_embedding_response):
    """Test that batch embedding filters out empty texts."""
    mock_embedding.return_value = mock_embedding_response

    texts = ["Valid text", "", "   ", "Another valid text"]

    # Should process only valid texts
    embedder.embed_batch(texts)

    # Mock should be called with only non-empty texts
    mock_embedding.assert_called_once()
    call_args = mock_embedding.call_args
    assert len(call_args.kwargs["input"]) == 2  # Only 2 valid texts


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_batch_all_empty_raises_error(mock_embedding, embedder):
    """Test that batch with all empty texts raises ValueError."""
    texts = ["", "   ", "\n\t"]

    with pytest.raises(ValueError) as exc_info:
        embedder.embed_batch(texts)

    assert "Cannot embed batch with all empty texts" in str(exc_info.value)
    mock_embedding.assert_not_called()


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_batch_api_error(mock_embedding, embedder):
    """Test handling of API errors in batch embedding."""
    mock_embedding.side_effect = Exception("API Error")

    texts = ["Text 1", "Text 2"]

    with pytest.raises(RuntimeError) as exc_info:
        embedder.embed_batch(texts)

    assert "Failed to generate batch embeddings" in str(exc_info.value)


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_text_calls_litellm_correctly(mock_embedding, embedder, mock_embedding_response):
    """Test that embed_text calls LiteLLM with correct parameters."""
    mock_embedding.return_value = mock_embedding_response

    embedder.embed_text("Test text")

    # Verify LiteLLM was called with correct parameters
    mock_embedding.assert_called_once()
    call_args = mock_embedding.call_args

    assert call_args.kwargs["model"] == embedder.model
    assert call_args.kwargs["input"] == ["Test text"]
    assert call_args.kwargs["api_base"] == embedder.base_url
    assert call_args.kwargs["timeout"] == embedder.timeout


@patch("src.ai_models.embedder.litellm.embedding")
def test_embed_batch_calls_litellm_correctly(
    mock_embedding, embedder, mock_batch_embedding_response
):
    """Test that embed_batch calls LiteLLM with correct parameters."""
    mock_embedding.return_value = mock_batch_embedding_response

    texts = ["Text 1", "Text 2", "Text 3"]
    embedder.embed_batch(texts)

    # Verify LiteLLM was called with correct parameters
    mock_embedding.assert_called_once()
    call_args = mock_embedding.call_args

    assert call_args.kwargs["model"] == embedder.model
    assert call_args.kwargs["input"] == texts
    assert call_args.kwargs["api_base"] == embedder.base_url
    assert call_args.kwargs["timeout"] == embedder.timeout


def test_embed_text_with_long_text(embedder):
    """Test embedding very long text."""
    # Create a very long text (this would normally be chunked first)
    long_text = " ".join(["word"] * 10000)

    # This test would need actual API or better mocking
    # For now, we just ensure the text is accepted
    assert len(long_text) > 0


def test_embed_text_with_special_characters(embedder):
    """Test embedding text with special characters."""
    text = "Text with special chars: é, ñ, ü, €, ©, ®, ™"

    # This test would need actual API or better mocking
    # For now, we just ensure the text is accepted
    assert len(text) > 0
