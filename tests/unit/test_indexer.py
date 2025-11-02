"""Unit tests for Document Indexer."""

from unittest.mock import MagicMock

import pytest
from haystack import Document

from src.retrieval.indexer import DocumentIndexer


@pytest.fixture
def mock_store():
    """Mock document store."""
    store = MagicMock()
    store._index = "test_index"
    store.write_documents.return_value = 1
    store.delete_documents.return_value = None
    return store


@pytest.fixture
def indexer(mock_store):
    """Create DocumentIndexer with mocked store."""
    return DocumentIndexer(mock_store)


@pytest.fixture
def sample_chunk():
    """Sample chunk data."""
    return {
        "text": "This is a test chunk.",
        "embedding": [0.1] * 768,
        "metadata": {
            "source_file": "test.txt",
            "chunk_index": 0,
            "start_char": 0,
            "end_char": 21,
        },
    }


def test_indexer_initialization(mock_store):
    """Test DocumentIndexer initializes correctly."""
    indexer = DocumentIndexer(mock_store)

    assert indexer.document_store == mock_store
    assert indexer.index_name == "test_index"


def test_index_chunk_success(indexer, mock_store, sample_chunk):
    """Test index_chunk successfully indexes a single chunk."""
    result = indexer.index_chunk(sample_chunk)

    assert result is True
    mock_store.write_documents.assert_called_once()

    # Check that Document was created correctly
    call_args = mock_store.write_documents.call_args
    documents = call_args[0][0]
    assert len(documents) == 1
    doc = documents[0]
    assert isinstance(doc, Document)
    assert doc.content == "This is a test chunk."
    assert doc.embedding == [0.1] * 768
    assert doc.meta["source_file"] == "test.txt"


def test_index_chunk_invalid_no_text(indexer, sample_chunk):
    """Test index_chunk raises error when text is missing."""
    sample_chunk["text"] = ""

    with pytest.raises(ValueError, match="Chunk must have 'text' field"):
        indexer.index_chunk(sample_chunk)


def test_index_chunk_invalid_no_embedding(indexer, sample_chunk):
    """Test index_chunk raises error when embedding is missing."""
    sample_chunk["embedding"] = []

    with pytest.raises(ValueError, match="Chunk must have 'embedding' field"):
        indexer.index_chunk(sample_chunk)


def test_index_chunk_invalid_no_metadata(indexer, sample_chunk):
    """Test index_chunk raises error when metadata is missing."""
    del sample_chunk["metadata"]

    with pytest.raises(ValueError, match="Chunk must have 'metadata' field"):
        indexer.index_chunk(sample_chunk)


def test_index_chunk_handles_exception(indexer, mock_store, sample_chunk):
    """Test index_chunk handles exceptions."""
    mock_store.write_documents.side_effect = Exception("Index failed")

    with pytest.raises(RuntimeError, match="Indexing failed"):
        indexer.index_chunk(sample_chunk)


def test_index_chunk_returns_false_when_no_docs_written(indexer, mock_store, sample_chunk):
    """Test index_chunk returns False when no documents written."""
    mock_store.write_documents.return_value = 0

    result = indexer.index_chunk(sample_chunk)

    assert result is False


def test_bulk_index_success(indexer, mock_store):
    """Test bulk_index successfully indexes multiple chunks."""
    chunks = [
        {
            "text": f"Chunk {i}",
            "embedding": [0.1] * 768,
            "metadata": {"source_file": "test.txt", "chunk_index": i},
        }
        for i in range(5)
    ]

    mock_store.write_documents.return_value = 5

    success, failed = indexer.bulk_index(chunks)

    assert success == 5
    assert failed == 0
    mock_store.write_documents.assert_called_once()


def test_bulk_index_empty_list(indexer, mock_store):
    """Test bulk_index with empty list."""
    success, failed = indexer.bulk_index([])

    assert success == 0
    assert failed == 0
    mock_store.write_documents.assert_not_called()


def test_bulk_index_with_invalid_chunks(indexer, mock_store):
    """Test bulk_index handles invalid chunks."""
    chunks = [
        {"text": "Valid chunk", "embedding": [0.1] * 768, "metadata": {"source_file": "test.txt"}},
        {"text": "", "embedding": [], "metadata": {}},  # Invalid
        {
            "text": "Another valid",
            "embedding": [0.2] * 768,
            "metadata": {"source_file": "test.txt"},
        },
    ]

    mock_store.write_documents.return_value = 2

    success, failed = indexer.bulk_index(chunks)

    assert success == 2
    assert failed == 1


def test_bulk_index_write_failure(indexer, mock_store):
    """Test bulk_index handles write failures."""
    chunks = [{"text": "Chunk", "embedding": [0.1] * 768, "metadata": {"source_file": "test.txt"}}]

    mock_store.write_documents.side_effect = Exception("Write failed")

    success, failed = indexer.bulk_index(chunks)

    assert success == 0
    assert failed == 1


def test_delete_documents_by_source_success(indexer, mock_store):
    """Test delete_documents_by_source removes documents."""
    # Mock filter_documents to return some docs
    mock_docs = [MagicMock(), MagicMock(), MagicMock()]
    mock_store.filter_documents.return_value = mock_docs

    result = indexer.delete_documents_by_source("test.txt")

    assert result == 3  # Returns number of deleted docs
    mock_store.filter_documents.assert_called_once()
    mock_store.delete_documents.assert_called_once()


def test_delete_documents_by_source_with_exception(indexer, mock_store):
    """Test delete_documents_by_source handles exceptions."""
    mock_store.delete_documents.side_effect = Exception("Delete failed")

    result = indexer.delete_documents_by_source("test.txt")

    # Returns 0 on error (no documents deleted)
    assert result == 0
