"""Unit tests for Index Manager."""

from unittest.mock import MagicMock

import pytest

from src.retrieval.index_manager import IndexManager


@pytest.fixture
def mock_store():
    """Mock document store with ES client."""
    store = MagicMock()
    store._index = "test_index"
    store._client = None
    store.count_documents.return_value = 0
    return store


@pytest.fixture
def index_manager(mock_store):
    """Create IndexManager with mocked store."""
    return IndexManager(mock_store)


def test_index_manager_initialization(mock_store):
    """Test IndexManager initializes correctly."""
    manager = IndexManager(mock_store)

    assert manager.document_store == mock_store
    assert manager.index_name == "test_index"


def test_client_property_lazy_init(index_manager, mock_store):
    """Test that _client property initializes lazily."""
    # Setup ES client
    es_client = MagicMock()
    mock_store._client = None

    def init_client():
        mock_store._client = es_client
        return 0

    mock_store.count_documents.side_effect = init_client

    # Access client
    client = index_manager._client

    assert client is es_client
    mock_store.count_documents.assert_called_once()


def test_ensure_index_exists_when_exists(index_manager, mock_store):
    """Test ensure_index_exists when index already exists."""
    # Setup ES client
    es_client = MagicMock()
    es_client.indices.exists.return_value = True
    mock_store._client = es_client

    result = index_manager.ensure_index_exists()

    assert result is True
    es_client.indices.exists.assert_called()


def test_ensure_index_exists_catches_exceptions(index_manager, mock_store):
    """Test ensure_index_exists catches exceptions from index_exists."""
    # Make index_exists throw exception but method still returns True
    # because Haystack creates index automatically on first write
    es_client = MagicMock()
    es_client.indices.exists.side_effect = Exception("Connection error")
    mock_store._client = es_client

    result = index_manager.ensure_index_exists()

    # Method handles exception gracefully and still returns True
    # since it relies on Haystack's automatic index creation
    assert result is True


def test_delete_index_success(index_manager, mock_store):
    """Test delete_index removes index successfully."""
    es_client = MagicMock()
    es_client.indices.exists.return_value = True
    es_client.indices.delete.return_value = {"acknowledged": True}
    mock_store._client = es_client

    result = index_manager.delete_index()

    assert result is True
    es_client.indices.delete.assert_called_once_with(index="test_index", ignore=[404])


def test_delete_index_when_not_exists(index_manager, mock_store):
    """Test delete_index when index doesn't exist."""
    es_client = MagicMock()
    es_client.indices.exists.return_value = False
    mock_store._client = es_client

    result = index_manager.delete_index()

    assert result is True


def test_delete_index_handles_exception(index_manager, mock_store):
    """Test delete_index handles exceptions."""
    es_client = MagicMock()
    es_client.indices.exists.return_value = True
    es_client.indices.delete.side_effect = Exception("Delete failed")
    mock_store._client = es_client

    result = index_manager.delete_index()

    assert result is False


def test_index_exists_true(index_manager, mock_store):
    """Test index_exists returns True when index exists."""
    es_client = MagicMock()
    es_client.indices.exists.return_value = True
    mock_store._client = es_client

    result = index_manager.index_exists()

    assert result is True


def test_index_exists_false(index_manager, mock_store):
    """Test index_exists returns False when index doesn't exist."""
    es_client = MagicMock()
    es_client.indices.exists.return_value = False
    mock_store._client = es_client

    result = index_manager.index_exists()

    assert result is False


def test_get_index_stats_success(index_manager, mock_store):
    """Test get_index_stats returns statistics."""
    es_client = MagicMock()
    es_client.indices.exists.return_value = True
    es_client.indices.stats.return_value = {
        "indices": {
            "test_index": {
                "total": {
                    "docs": {"count": 100, "deleted": 5},
                    "store": {"size_in_bytes": 1024000},
                }
            }
        }
    }
    mock_store._client = es_client
    mock_store.count_documents.return_value = 100

    stats = index_manager.get_index_stats()

    assert stats["doc_count"] == 100
    assert stats["size"] == 1024000
    assert stats["status"] == "healthy"


def test_optimize_index_success(index_manager, mock_store):
    """Test optimize_index performs forcemerge."""
    es_client = MagicMock()
    es_client.indices.forcemerge.return_value = {"_shards": {"successful": 1}}
    mock_store._client = es_client

    result = index_manager.optimize_index()

    assert result is True
    es_client.indices.forcemerge.assert_called()


def test_optimize_index_handles_exception(index_manager, mock_store):
    """Test optimize_index handles exceptions."""
    es_client = MagicMock()
    es_client.indices.exists.return_value = True
    es_client.indices.forcemerge.side_effect = Exception("Optimize failed")
    mock_store._client = es_client

    result = index_manager.optimize_index()

    assert result is False
