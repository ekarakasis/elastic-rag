"""Unit tests for Elasticsearch client."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_document_store():
    """Mock ElasticsearchDocumentStore."""
    store = MagicMock()
    store._client = MagicMock()
    store._index = "test_index"
    store.count_documents.return_value = 0
    return store


@pytest.fixture
def mock_get_settings():
    """Mock settings function."""
    with patch("src.retrieval.elasticsearch_client.get_settings") as mock:
        settings = MagicMock()
        settings.elasticsearch.url = "http://localhost:9200"
        settings.elasticsearch.index = "test_index"
        mock.return_value = settings
        yield mock


@patch("src.retrieval.elasticsearch_client.ElasticsearchDocumentStore")
def test_client_initialization(mock_store_class, mock_get_settings):
    """Test ElasticsearchClient initializes correctly."""
    from src.retrieval.elasticsearch_client import ElasticsearchClient

    mock_store_class.return_value = MagicMock()

    client = ElasticsearchClient()

    assert client.hosts == "http://localhost:9200"
    assert client.index == "test_index"
    assert client.embedding_dim == 768
    assert client.document_store is not None


@patch("src.retrieval.elasticsearch_client.ElasticsearchDocumentStore")
def test_get_document_store(mock_store_class, mock_get_settings):
    """Test get_document_store returns the store."""
    from src.retrieval.elasticsearch_client import ElasticsearchClient

    mock_store_instance = MagicMock()
    mock_store_class.return_value = mock_store_instance

    client = ElasticsearchClient()
    store = client.get_document_store()

    assert store is mock_store_instance


@patch("src.retrieval.elasticsearch_client.ElasticsearchDocumentStore")
def test_health_check_healthy(mock_store_class, mock_get_settings):
    """Test health check returns healthy status."""
    from src.retrieval.elasticsearch_client import ElasticsearchClient

    # Setup mock ES client
    mock_es_client = MagicMock()
    mock_es_client.cluster.health.return_value = {
        "status": "green",
        "cluster_name": "test-cluster",
        "number_of_nodes": 1,
        "active_shards": 5,
        "unassigned_shards": 0,
        "initializing_shards": 0,
        "relocating_shards": 0,
    }
    mock_es_client.info.return_value = {"version": {"number": "8.0.0"}}

    mock_store_instance = MagicMock()
    mock_store_instance._client = mock_es_client
    mock_store_class.return_value = mock_store_instance

    client = ElasticsearchClient()
    health = client.health_check()

    assert health["status"] == "healthy"
    assert health["cluster_name"] == "test-cluster"
    assert health["cluster_status"] == "green"
    assert health["elasticsearch_version"] == "8.0.0"


@patch("src.retrieval.elasticsearch_client.ElasticsearchDocumentStore")
def test_health_check_unhealthy(mock_store_class, mock_get_settings):
    """Test health check handles errors."""
    from src.retrieval.elasticsearch_client import ElasticsearchClient

    mock_store_instance = MagicMock()
    mock_store_instance._client = None
    mock_store_instance.count_documents.side_effect = Exception("Connection failed")
    mock_store_class.return_value = mock_store_instance

    client = ElasticsearchClient()
    health = client.health_check()

    assert health["status"] == "unhealthy"
    assert "error" in health


@patch("src.retrieval.elasticsearch_client.ElasticsearchDocumentStore")
def test_get_connection_info(mock_store_class, mock_get_settings):
    """Test get_connection_info returns correct details."""
    from src.retrieval.elasticsearch_client import ElasticsearchClient

    mock_store_class.return_value = MagicMock()

    client = ElasticsearchClient()
    info = client.get_connection_info()

    assert info["hosts"] == "http://localhost:9200"
    assert info["index"] == "test_index"
    assert info["embedding_dim"] == 768
    assert info["similarity"] == "cosine"


@patch("src.retrieval.elasticsearch_client.ElasticsearchDocumentStore")
def test_client_initialization_failure(mock_store_class, mock_get_settings):
    """Test client handles initialization failures."""
    from src.retrieval.elasticsearch_client import ElasticsearchClient

    mock_store_class.side_effect = Exception("Connection refused")

    with pytest.raises(ConnectionError):
        ElasticsearchClient()
