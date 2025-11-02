"""Elasticsearch client wrapper using Haystack integration.

This module provides a wrapper around Haystack's ElasticsearchDocumentStore
for managing connections to Elasticsearch and providing health check capabilities.
"""

import logging
import threading

from haystack_integrations.document_stores.elasticsearch import (
    ElasticsearchDocumentStore,
)

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Module-level singleton cache with thread safety
_client_lock = threading.Lock()
_client_instance: "ElasticsearchClient | None" = None


class ElasticsearchClient:
    """Wrapper for Haystack ElasticsearchDocumentStore.

    Provides simplified access to Elasticsearch through Haystack's integration,
    with added health check and connection management capabilities.
    """

    def __init__(self):
        """Initialize Elasticsearch client from configuration.

        The client reads configuration from settings and initializes
        a Haystack ElasticsearchDocumentStore with appropriate parameters
        for vector similarity search.

        Raises:
            ConnectionError: If unable to connect to Elasticsearch
        """
        settings = get_settings()

        self.hosts = settings.elasticsearch.url
        self.index = settings.elasticsearch.index
        self.embedding_dim = 768  # BGE-M3 model dimension

        logger.info(f"Initializing ElasticsearchDocumentStore: {self.hosts}/{self.index}")

        try:
            # Initialize Haystack document store
            # Note: embedding_dim and similarity are configured when the index is created
            self.document_store = ElasticsearchDocumentStore(
                hosts=self.hosts,
                index=self.index,
            )

            logger.info("✓ ElasticsearchDocumentStore initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ElasticsearchDocumentStore: {e}")
            raise ConnectionError(f"Could not connect to Elasticsearch at {self.hosts}: {e}") from e

    def get_document_store(self) -> ElasticsearchDocumentStore:
        """Get the Haystack document store instance.

        Returns:
            ElasticsearchDocumentStore: The Haystack document store
        """
        return self.document_store

    def health_check(self) -> dict:
        """Check Elasticsearch cluster health.

        Returns:
            dict: Health status information with keys:
                - status: 'healthy' or 'unhealthy'
                - cluster_name: Name of the ES cluster
                - details: Additional cluster information

        Example:
            >>> client = ElasticsearchClient()
            >>> health = client.health_check()
            >>> print(health['status'])
            'healthy'
        """
        try:
            # Access the underlying Elasticsearch client from Haystack
            # The _client attribute is lazily initialized
            if not hasattr(self.document_store, "_client") or self.document_store._client is None:
                # Initialize the client by performing a simple operation
                _ = self.document_store.count_documents()

            es_client = self.document_store._client

            # Get cluster health
            cluster_health = es_client.cluster.health()

            # Get cluster info
            cluster_info = es_client.info()

            health_status = {
                "status": (
                    "healthy" if cluster_health["status"] in ["green", "yellow"] else "unhealthy"
                ),
                "cluster_name": cluster_health.get("cluster_name", "unknown"),
                "cluster_status": cluster_health.get("status", "unknown"),
                "number_of_nodes": cluster_health.get("number_of_nodes", 0),
                "active_shards": cluster_health.get("active_shards", 0),
                "elasticsearch_version": cluster_info.get("version", {}).get("number", "unknown"),
                "details": {
                    "unassigned_shards": cluster_health.get("unassigned_shards", 0),
                    "initializing_shards": cluster_health.get("initializing_shards", 0),
                    "relocating_shards": cluster_health.get("relocating_shards", 0),
                },
            }

            logger.info(
                f"Cluster health check: {health_status['status']} ({health_status['cluster_status']})"
            )

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "cluster_name": "unknown",
                "error": str(e),
            }

    def get_connection_info(self) -> dict:
        """Get connection information.

        Returns:
            dict: Connection details including hosts, index, and settings
        """
        return {
            "hosts": self.hosts,
            "index": self.index,
            "embedding_dim": self.embedding_dim,
            "similarity": "cosine",
        }

    def close(self):
        """Close the Elasticsearch connection.

        This method is called to cleanly shut down the connection.
        """
        try:
            # Haystack's document store doesn't have an explicit close,
            # but we can access the underlying client if needed
            logger.info("Closing Elasticsearch connection")
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")


def get_elasticsearch_client() -> ElasticsearchClient:
    """
    Get or create singleton ElasticsearchClient instance.

    Thread-safe singleton ensures only ONE Elasticsearch connection pool
    is created and reused across all operations (queries, uploads, deletes, etc.).

    Benefits:
    - Single connection pool for entire app lifecycle
    - No connection exhaustion under load
    - Faster operations (no connection setup overhead)

    Returns:
        Cached ElasticsearchClient instance

    Example:
        >>> es_client = get_elasticsearch_client()
        >>> document_store = es_client.get_document_store()
    """
    global _client_instance

    if _client_instance is None:
        with _client_lock:
            # Double-check locking pattern (thread-safe)
            if _client_instance is None:
                _client_instance = ElasticsearchClient()
                logger.info("✓ Created singleton ElasticsearchClient instance")

    return _client_instance


def _reset_elasticsearch_client_cache():
    """
    Reset the singleton cache.

    ⚠️  FOR TESTING ONLY - Do not use in production code.

    This allows tests to reset the singleton state between test runs
    to ensure test isolation.
    """
    global _client_instance
    with _client_lock:
        _client_instance = None
        logger.debug("Reset ElasticsearchClient singleton cache")
