"""Unit tests for Semantic Searcher."""

from unittest.mock import MagicMock, patch

import pytest
from haystack import Document

from src.retrieval.searcher import SemanticSearcher


@pytest.fixture
def mock_store():
    """Mock document store."""
    store = MagicMock()
    store._index = "test_index"
    return store


@pytest.fixture
def mock_get_settings():
    """Mock settings."""
    with patch("src.retrieval.searcher.get_settings") as mock:
        settings = MagicMock()
        settings.retrieval.top_k = 10
        settings.retrieval.similarity_threshold = 0.7
        mock.return_value = settings
        yield mock


@pytest.fixture
def mock_embedder():
    """Mock Embedder class."""
    with patch("src.retrieval.searcher.Embedder") as mock:
        embedder_instance = MagicMock()
        embedder_instance.embed.return_value = [0.1] * 768
        mock.return_value = embedder_instance
        yield mock


@pytest.fixture
@patch("src.retrieval.searcher.ElasticsearchBM25Retriever")
@patch("src.retrieval.searcher.ElasticsearchEmbeddingRetriever")
def searcher(
    mock_embedding_retriever, mock_bm25_retriever, mock_store, mock_get_settings, mock_embedder
):
    """Create SemanticSearcher with mocked dependencies."""
    return SemanticSearcher(mock_store)


@pytest.fixture
def sample_documents():
    """Sample Haystack documents."""
    return [
        Document(
            content="This is document 1",
            embedding=[0.1] * 768,
            meta={"source_file": "doc1.txt", "chunk_index": 0},
            score=0.95,
        ),
        Document(
            content="This is document 2",
            embedding=[0.2] * 768,
            meta={"source_file": "doc2.txt", "chunk_index": 0},
            score=0.85,
        ),
        Document(
            content="This is document 3",
            embedding=[0.3] * 768,
            meta={"source_file": "doc3.txt", "chunk_index": 0},
            score=0.75,
        ),
    ]


def test_searcher_initialization(mock_store, mock_get_settings, mock_embedder):
    """Test SemanticSearcher initializes correctly."""
    with patch("src.retrieval.searcher.ElasticsearchEmbeddingRetriever"):
        with patch("src.retrieval.searcher.ElasticsearchBM25Retriever"):
            searcher = SemanticSearcher(mock_store)

            assert searcher.document_store == mock_store
            assert searcher.top_k == 10
            assert searcher.threshold == 0.7


def test_normalize_filters_simple_dict(searcher):
    """Test filter normalization from simple dict."""
    simple_filters = {"source_file": "doc1.txt", "chunk_index": 0}

    normalized = searcher._normalize_filters(simple_filters)

    assert normalized["operator"] == "AND"
    assert "conditions" in normalized
    assert len(normalized["conditions"]) == 2


def test_normalize_filters_haystack_format(searcher):
    """Test filter normalization with Haystack format."""
    haystack_filters = {"field": "meta.source_file", "operator": "==", "value": "doc1.txt"}

    normalized = searcher._normalize_filters(haystack_filters)

    # Should pass through unchanged
    assert normalized["field"] == "meta.source_file"
    assert normalized["operator"] == "=="
    assert normalized["value"] == "doc1.txt"


def test_normalize_filters_none(searcher):
    """Test filter normalization with None."""
    normalized = searcher._normalize_filters(None)

    assert normalized is None


@patch("src.retrieval.searcher.ElasticsearchEmbeddingRetriever")
def test_search_vector_mode(mock_retriever_class, searcher, sample_documents):
    """Test search with vector mode."""
    mock_retriever = MagicMock()
    mock_retriever.run.return_value = {"documents": sample_documents}
    mock_retriever_class.return_value = mock_retriever

    # Replace the retriever
    searcher.embedding_retriever = mock_retriever

    results = searcher.search("test query", top_k=3)

    assert len(results) == 3
    assert results[0]["text"] == "This is document 1"
    assert results[0]["score"] == 0.95
    assert "metadata" in results[0]


@patch("src.retrieval.searcher.ElasticsearchBM25Retriever")
def test_keyword_search(mock_retriever_class, searcher, sample_documents):
    """Test keyword search with BM25."""
    mock_retriever = MagicMock()
    mock_retriever.run.return_value = {"documents": sample_documents}
    mock_retriever_class.return_value = mock_retriever

    # Replace the retriever
    searcher.bm25_retriever = mock_retriever

    results = searcher.keyword_search("test query", top_k=3)

    assert len(results) == 3
    assert results[0]["text"] == "This is document 1"


def test_search_with_score_threshold(searcher, sample_documents):
    """Test search filters by score threshold."""
    mock_retriever = MagicMock()
    mock_retriever.run.return_value = {"documents": sample_documents}
    searcher.embedding_retriever = mock_retriever
    searcher.threshold = 0.80

    results = searcher.search("test query")

    # Should filter out document with score 0.75
    assert len(results) == 2
    assert all(r["score"] >= 0.80 for r in results)


def test_search_empty_results(searcher):
    """Test search handles empty results."""
    mock_retriever = MagicMock()
    mock_retriever.run.return_value = {"documents": []}
    searcher.embedding_retriever = mock_retriever

    results = searcher.search("test query")

    assert len(results) == 0


def test_search_with_empty_query(searcher):
    """Test search with empty query returns empty results."""
    results = searcher.search("")

    assert len(results) == 0


def test_search_with_filters(searcher, sample_documents):
    """Test search with metadata filters."""
    mock_retriever = MagicMock()
    # Return only documents matching filter
    filtered_docs = [doc for doc in sample_documents if doc.meta["source_file"] == "doc1.txt"]
    mock_retriever.run.return_value = {"documents": filtered_docs}
    searcher.embedding_retriever = mock_retriever

    filters = {"source_file": "doc1.txt"}
    results = searcher.search("test query", filters=filters)

    assert len(results) == 1
    assert results[0]["metadata"]["source_file"] == "doc1.txt"


def test_search_handles_exception(searcher):
    """Test search handles exceptions gracefully."""
    mock_retriever = MagicMock()
    mock_retriever.run.side_effect = Exception("Search failed")
    searcher.embedding_retriever = mock_retriever

    results = searcher.search("test query")

    assert len(results) == 0


def test_hybrid_search_combines_results(searcher, sample_documents):
    """Test hybrid search combines vector and BM25 results."""
    # Setup vector retriever
    mock_vector = MagicMock()
    mock_vector.run.return_value = {"documents": sample_documents[:2]}
    searcher.embedding_retriever = mock_vector

    # Setup BM25 retriever
    mock_bm25 = MagicMock()
    mock_bm25.run.return_value = {"documents": sample_documents[1:]}
    searcher.bm25_retriever = mock_bm25

    results = searcher.hybrid_search("test query", top_k=5)

    # Should combine and deduplicate
    assert len(results) > 0
    mock_vector.run.assert_called_once()
    mock_bm25.run.assert_called_once()
