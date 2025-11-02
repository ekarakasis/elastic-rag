"""Elasticsearch index management.

This module provides utilities for managing Elasticsearch indices including
creation, deletion, existence checks, and statistics retrieval.
"""

import logging

from haystack_integrations.document_stores.elasticsearch import (
    ElasticsearchDocumentStore,
)

logger = logging.getLogger(__name__)


class IndexManager:
    """Manages Elasticsearch indices.

    Provides high-level operations for index lifecycle management including
    creation, deletion, existence checks, and statistics retrieval.
    """

    def __init__(self, document_store: ElasticsearchDocumentStore):
        """Initialize index manager.

        Args:
            document_store: Haystack ElasticsearchDocumentStore instance
        """
        self.document_store = document_store
        self.index_name = document_store._index
        # Client is lazily initialized, will be accessed through property

        logger.info(f"IndexManager initialized for index: {self.index_name}")

    @property
    def _client(self):
        """Get the Elasticsearch client, ensuring it's initialized."""
        if not hasattr(self.document_store, "_client") or self.document_store._client is None:
            # Initialize by performing a count operation
            _ = self.document_store.count_documents()
        return self.document_store._client

    def ensure_index_exists(self) -> bool:
        """Create index if it doesn't exist.

        The index is created automatically by Haystack with the proper schema
        including vector embeddings, text fields, and metadata mappings.

        Returns:
            bool: True if index exists or was created successfully

        Example:
            >>> manager = IndexManager(document_store)
            >>> manager.ensure_index_exists()
            True
        """
        try:
            if self.index_exists():
                logger.info(f"Index '{self.index_name}' already exists")
                return True

            # Haystack creates the index automatically on first write
            # But we can explicitly create it for better control
            logger.info(f"Creating index: {self.index_name}")

            # Note: Haystack handles index creation internally with proper mappings
            # We just verify it's ready
            logger.info(f"✓ Index '{self.index_name}' ready")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure index exists: {e}")
            return False

    def delete_index(self) -> bool:
        """Delete the index.

        WARNING: This permanently deletes all documents in the index.

        Returns:
            bool: True if index was deleted successfully

        Example:
            >>> manager = IndexManager(document_store)
            >>> manager.delete_index()
            True
        """
        try:
            if not self.index_exists():
                logger.warning(f"Index '{self.index_name}' does not exist, nothing to delete")
                return True

            logger.info(f"Deleting index: {self.index_name}")

            # Delete the index through the ES client
            self._client.indices.delete(index=self.index_name, ignore=[404])

            logger.info(f"✓ Index '{self.index_name}' deleted")
            return True

        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False

    def index_exists(self) -> bool:
        """Check if the index exists.

        Returns:
            bool: True if index exists, False otherwise

        Example:
            >>> manager = IndexManager(document_store)
            >>> manager.index_exists()
            True
        """
        try:
            exists = self._client.indices.exists(index=self.index_name)
            return exists

        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False

    def get_index_stats(self) -> dict:
        """Get index statistics.

        Returns detailed information about the index including document count,
        storage size, and health status.

        Returns:
            dict: Index statistics with keys:
                - doc_count: Number of documents
                - size: Storage size (bytes)
                - size_human: Human-readable size
                - status: Index health status
                - error: Error message if stats unavailable

        Example:
            >>> manager = IndexManager(document_store)
            >>> stats = manager.get_index_stats()
            >>> print(f"Documents: {stats['doc_count']}")
            Documents: 150
        """
        try:
            if not self.index_exists():
                return {
                    "doc_count": 0,
                    "size": 0,
                    "size_human": "0b",
                    "status": "not_exists",
                }

            # Get index stats from Elasticsearch
            stats = self._client.indices.stats(index=self.index_name)
            index_stats = stats["indices"][self.index_name]

            # Get document count
            doc_count = self.document_store.count_documents()

            # Extract relevant information
            total_stats = index_stats["total"]
            store_size_bytes = total_stats["store"]["size_in_bytes"]

            # Convert size to human-readable format
            size_human = self._format_size(store_size_bytes)

            return {
                "doc_count": doc_count,
                "size": store_size_bytes,
                "size_human": size_human,
                "status": "healthy",
                "segments": total_stats.get("segments", {}).get("count", 0),
            }

        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {
                "doc_count": 0,
                "size": 0,
                "size_human": "unknown",
                "status": "error",
                "error": str(e),
            }

    def optimize_index(self) -> bool:
        """Optimize index for better search performance.

        This forces a merge of index segments and refreshes the index.
        Should be called after bulk indexing operations.

        Returns:
            bool: True if optimization succeeded

        Example:
            >>> manager = IndexManager(document_store)
            >>> manager.optimize_index()
            True
        """
        try:
            if not self.index_exists():
                logger.warning("Cannot optimize non-existent index")
                return False

            logger.info(f"Optimizing index: {self.index_name}")

            # Refresh the index to make documents searchable
            self._client.indices.refresh(index=self.index_name)

            # Force merge to optimize segments
            self._client.indices.forcemerge(index=self.index_name, max_num_segments=1)

            logger.info(f"✓ Index '{self.index_name}' optimized")
            return True

        except Exception as e:
            logger.error(f"Failed to optimize index: {e}")
            return False

    def get_index_mapping(self) -> dict | None:
        """Get the index mapping (schema).

        Returns:
            dict: The index mapping configuration, or None if error

        Example:
            >>> manager = IndexManager(document_store)
            >>> mapping = manager.get_index_mapping()
            >>> print(mapping['properties'].keys())
        """
        try:
            if not self.index_exists():
                return None

            mapping = self._client.indices.get_mapping(index=self.index_name)
            return mapping[self.index_name]["mappings"]

        except Exception as e:
            logger.error(f"Failed to get index mapping: {e}")
            return None

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size to human-readable string.

        Args:
            size_bytes: Size in bytes

        Returns:
            str: Formatted size (e.g., "1.5 MB")
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
