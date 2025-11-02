"""Document indexing using Haystack ElasticsearchDocumentStore.

This module provides functionality to index documents and chunks into Elasticsearch
using Haystack's Document abstraction for seamless integration.
"""

import logging
from datetime import datetime

from haystack import Document
from haystack_integrations.document_stores.elasticsearch import (
    ElasticsearchDocumentStore,
)

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Indexes documents using Haystack Elasticsearch integration.

    Converts pipeline output chunks into Haystack Documents and writes them
    to Elasticsearch with proper embeddings and metadata.
    """

    def __init__(self, document_store: ElasticsearchDocumentStore):
        """Initialize indexer with Haystack document store.

        Args:
            document_store: Haystack ElasticsearchDocumentStore instance
        """
        self.document_store = document_store
        self.index_name = document_store._index

        logger.info(f"DocumentIndexer initialized for index: {self.index_name}")

    def index_chunk(self, chunk_data: dict) -> bool:
        """Index a single chunk using Haystack Document.

        Args:
            chunk_data: Dictionary with structure:
                {
                    "text": str,              # Chunk text content
                    "embedding": List[float],  # Vector embedding
                    "metadata": dict          # Chunk metadata
                }

        Returns:
            bool: True if indexing succeeded

        Raises:
            ValueError: If chunk_data is invalid
            RuntimeError: If indexing fails

        Example:
            >>> indexer = DocumentIndexer(document_store)
            >>> chunk = {
            ...     "text": "Sample text",
            ...     "embedding": [0.1, 0.2, ...],  # 768 dimensions
            ...     "metadata": {"source_file": "doc.pdf"}
            ... }
            >>> indexer.index_chunk(chunk)
            True
        """
        try:
            # Validate chunk data
            if not chunk_data.get("text"):
                raise ValueError("Chunk must have 'text' field")
            if not chunk_data.get("embedding"):
                raise ValueError("Chunk must have 'embedding' field")
            if not chunk_data.get("metadata"):
                raise ValueError("Chunk must have 'metadata' field")

            # Create Haystack Document
            doc = Document(
                content=chunk_data["text"],
                embedding=chunk_data["embedding"],
                meta={
                    **chunk_data["metadata"],
                    "indexed_at": datetime.utcnow().isoformat(),
                },
            )

            # Write to document store
            written = self.document_store.write_documents([doc])

            if written > 0:
                logger.debug(
                    f"Successfully indexed chunk from {chunk_data['metadata'].get('source_file', 'unknown')}"
                )
                return True
            else:
                logger.warning("Document write returned 0 documents written")
                return False

        except ValueError as e:
            logger.error(f"Invalid chunk data: {e}")
            raise

        except Exception as e:
            logger.error(f"Failed to index chunk: {e}")
            raise RuntimeError(f"Indexing failed: {e}") from e

    def bulk_index(self, chunks: list[dict]) -> tuple[int, int]:
        """Bulk index multiple chunks using Haystack.

        This method is more efficient than indexing chunks one by one
        as it batches the operations to Elasticsearch.

        Args:
            chunks: List of chunk dictionaries (same structure as index_chunk)

        Returns:
            tuple[int, int]: (successful_count, failed_count)

        Example:
            >>> indexer = DocumentIndexer(document_store)
            >>> chunks = [chunk1, chunk2, chunk3]
            >>> success, failed = indexer.bulk_index(chunks)
            >>> print(f"Indexed {success} chunks, {failed} failed")
            Indexed 3 chunks, 0 failed
        """
        if not chunks:
            logger.warning("No chunks provided for bulk indexing")
            return 0, 0

        logger.info(f"Bulk indexing {len(chunks)} chunks...")

        documents = []
        failed_count = 0

        # Convert chunks to Haystack Documents
        for i, chunk in enumerate(chunks):
            try:
                # Validate basic structure
                if not chunk.get("text") or not chunk.get("embedding") or not chunk.get("metadata"):
                    logger.warning(f"Skipping invalid chunk at index {i}")
                    failed_count += 1
                    continue

                doc = Document(
                    content=chunk["text"],
                    embedding=chunk["embedding"],
                    meta={
                        **chunk["metadata"],
                        "indexed_at": datetime.utcnow().isoformat(),
                    },
                )
                documents.append(doc)

            except Exception as e:
                logger.warning(f"Failed to prepare chunk {i} for indexing: {e}")
                failed_count += 1

        if not documents:
            logger.error("No valid documents to index")
            return 0, len(chunks)

        try:
            # Bulk write using Haystack document store
            written_count = self.document_store.write_documents(documents)

            logger.info(f"✓ Indexed {written_count} chunks, {failed_count} failed")

            return written_count, failed_count

        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return 0, len(chunks)

    def update_document(self, doc_id: str, chunk_data: dict) -> bool:
        """Update an existing document.

        Note: This is a P2 feature. Currently implemented as delete + reindex.

        Args:
            doc_id: Document ID to update
            chunk_data: New chunk data (same structure as index_chunk)

        Returns:
            bool: True if update succeeded

        Example:
            >>> indexer = DocumentIndexer(document_store)
            >>> indexer.update_document("doc_123", updated_chunk)
            True
        """
        try:
            # For now, we delete and reindex
            # Haystack's write_documents with duplicate content will update
            logger.info(f"Updating document: {doc_id}")

            # Create updated document
            doc = Document(
                id=doc_id,
                content=chunk_data["text"],
                embedding=chunk_data["embedding"],
                meta={
                    **chunk_data["metadata"],
                    "indexed_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )

            # Write will update if ID exists
            written = self.document_store.write_documents([doc])

            if written > 0:
                logger.info(f"✓ Document {doc_id} updated")
                return True
            else:
                logger.warning(f"Failed to update document {doc_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return False

    def delete_documents_by_source(self, source_file: str) -> int:
        """Delete all documents from a specific source file.

        Args:
            source_file: Source filename to filter by

        Returns:
            int: Number of documents deleted

        Example:
            >>> indexer = DocumentIndexer(document_store)
            >>> deleted = indexer.delete_documents_by_source("sample.pdf")
            >>> print(f"Deleted {deleted} chunks")
            Deleted 25 chunks
        """
        try:
            logger.info(f"Deleting documents from source: {source_file}")

            # Use filter to delete by metadata
            filters = {"source_file": source_file}

            # Get count before deletion
            docs = self.document_store.filter_documents(filters=filters)
            count = len(docs) if docs else 0

            if count > 0:
                # Delete the filtered documents
                self.document_store.delete_documents(filters=filters)
                logger.info(f"✓ Deleted {count} documents from {source_file}")

            return count

        except Exception as e:
            logger.error(f"Failed to delete documents by source: {e}")
            return 0

    def get_document_count(self) -> int:
        """Get total number of indexed documents.

        Returns:
            int: Total document count in the index

        Example:
            >>> indexer = DocumentIndexer(document_store)
            >>> count = indexer.get_document_count()
            >>> print(f"Total documents: {count}")
            Total documents: 150
        """
        try:
            count = self.document_store.count_documents()
            return count

        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0
