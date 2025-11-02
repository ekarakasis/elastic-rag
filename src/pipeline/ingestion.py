"""Document ingestion pipeline orchestration."""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from src.ai_models.embedder import Embedder
from src.pipeline.chunker import TextChunker
from src.pipeline.document_processor import DocumentProcessor

if TYPE_CHECKING:
    from src.retrieval.indexer import DocumentIndexer

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates document ingestion pipeline: process → chunk → embed.

    Can optionally integrate with DocumentIndexer for automatic Elasticsearch indexing.
    """

    def __init__(self, indexer: Optional["DocumentIndexer"] = None):
        """Initialize pipeline components.

        Args:
            indexer: Optional DocumentIndexer for automatic indexing to Elasticsearch
        """
        self.processor = DocumentProcessor()
        self.chunker = TextChunker()
        self.embedder = Embedder()
        self.indexer = indexer

        if indexer:
            logger.info("IngestionPipeline initialized with all components + auto-indexing")
        else:
            logger.info("IngestionPipeline initialized with all components")

    def ingest_document(self, file_path: str | Path) -> list[dict]:
        """
        Ingest a single document through the full pipeline.

        Pipeline flow:
        1. Process document (extract text and metadata)
        2. Chunk text into smaller pieces
        3. Generate embeddings for each chunk
        4. Return indexed chunks ready for Elasticsearch

        Args:
            file_path: Path to document file

        Returns:
            List of dictionaries with structure:
            {
                "text": str,              # Chunk text
                "embedding": List[float],  # Vector embedding
                "metadata": dict          # Combined metadata
            }

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format not supported
            RuntimeError: If any pipeline step fails
        """
        file_path = Path(file_path)
        start_time = datetime.now()

        logger.info(f"Starting ingestion of: {file_path.name}")

        try:
            # Step 1: Process document
            logger.info("Step 1/3: Processing document...")
            processed_doc = self.processor.process_document(file_path)
            logger.info(
                f"  ✓ Extracted {len(processed_doc.text)} characters "
                f"({processed_doc.metadata.page_count or 'N/A'} pages)"
            )

            # Step 2: Chunk text
            logger.info("Step 2/3: Chunking text...")
            chunks = self.chunker.chunk_document(processed_doc)
            logger.info(f"  ✓ Created {len(chunks)} chunks")

            if not chunks:
                logger.warning("No chunks created - document may be empty")
                return []

            # Step 3: Generate embeddings
            logger.info("Step 3/3: Generating embeddings...")
            texts = [chunk.text for chunk in chunks]
            embeddings = self.embedder.embed_batch(texts)
            logger.info(f"  ✓ Generated {len(embeddings)} embeddings")

            # Step 4: Combine chunks with embeddings
            indexed_chunks = []
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                indexed_chunks.append(
                    {
                        "text": chunk.text,
                        "embedding": embedding,
                        "metadata": {
                            "source_file": chunk.source_file,
                            "chunk_index": chunk.chunk_index,
                            "start_char": chunk.start_char,
                            "end_char": chunk.end_char,
                            **chunk.metadata,
                            "indexed_at": datetime.utcnow().isoformat(),
                        },
                    }
                )

            # Calculate elapsed time
            elapsed = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Successfully ingested {file_path.name}: "
                f"{len(indexed_chunks)} chunks in {elapsed:.2f}s"
            )

            return indexed_chunks

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"Failed to ingest {file_path.name} after {elapsed:.2f}s: {e}")
            raise

    def ingest_batch(self, file_paths: list[str | Path]) -> dict[str, Any]:
        """
        Ingest multiple documents through the pipeline.

        Args:
            file_paths: List of paths to document files

        Returns:
            Dictionary with structure:
            {
                "total": int,           # Total documents processed
                "successful": int,      # Successfully processed
                "failed": int,          # Failed to process
                "chunks": List[Dict],   # All indexed chunks
                "errors": Dict[str, str]  # Errors by filename
            }
        """
        start_time = datetime.now()
        logger.info(f"Starting batch ingestion of {len(file_paths)} documents")

        results = {
            "total": len(file_paths),
            "successful": 0,
            "failed": 0,
            "chunks": [],
            "errors": {},
        }

        for file_path in file_paths:
            file_path = Path(file_path)

            try:
                chunks = self.ingest_document(file_path)
                results["chunks"].extend(chunks)
                results["successful"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"][file_path.name] = str(e)
                logger.error(f"Failed to ingest {file_path.name}: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Batch ingestion complete: "
            f"{results['successful']}/{results['total']} successful, "
            f"{len(results['chunks'])} total chunks, "
            f"elapsed={elapsed:.2f}s"
        )

        return results

    def ingest_and_index_document(self, file_path: str | Path) -> tuple[list[dict], int]:
        """
        Ingest and automatically index document to Elasticsearch.

        This method combines the ingestion pipeline with automatic indexing.
        Requires an indexer to be provided during initialization.

        Args:
            file_path: Path to document file

        Returns:
            tuple[list[dict], int]: (chunks, indexed_count)
                - chunks: List of all chunks with embeddings
                - indexed_count: Number successfully indexed

        Raises:
            ValueError: If no indexer configured
            FileNotFoundError: If file doesn't exist
            RuntimeError: If ingestion or indexing fails

        Example:
            >>> from src.retrieval import ElasticsearchClient, DocumentIndexer
            >>> es_client = ElasticsearchClient()
            >>> indexer = DocumentIndexer(es_client.get_document_store())
            >>> pipeline = IngestionPipeline(indexer=indexer)
            >>> chunks, indexed = pipeline.ingest_and_index_document("doc.pdf")
            >>> print(f"Indexed {indexed} of {len(chunks)} chunks")
        """
        if not self.indexer:
            raise ValueError(
                "No indexer configured. Initialize pipeline with indexer parameter "
                "or use ingest_document() instead."
            )

        file_path = Path(file_path)
        logger.info(f"Ingesting and indexing: {file_path.name}")

        # Step 1: Ingest through pipeline
        chunks = self.ingest_document(file_path)

        if not chunks:
            logger.warning("No chunks to index")
            return chunks, 0

        # Step 2: Index to Elasticsearch
        logger.info(f"Indexing {len(chunks)} chunks to Elasticsearch...")
        success_count, fail_count = self.indexer.bulk_index(chunks)

        if fail_count > 0:
            logger.warning(f"⚠️  {fail_count} chunks failed to index")

        logger.info(
            f"✓ Ingested and indexed {file_path.name}: {success_count}/{len(chunks)} chunks"
        )

        return chunks, success_count

    def ingest_batch_and_index(self, file_paths: list[str | Path]) -> dict[str, Any]:
        """
        Ingest and index multiple documents to Elasticsearch.

        Args:
            file_paths: List of paths to document files

        Returns:
            Dictionary with structure:
            {
                "total_files": int,         # Total files processed
                "successful_files": int,    # Successfully processed files
                "failed_files": int,        # Failed files
                "total_chunks": int,        # Total chunks created
                "indexed_chunks": int,      # Successfully indexed chunks
                "errors": Dict[str, str],   # Errors by filename
                "elapsed_seconds": float    # Total processing time
            }

        Raises:
            ValueError: If no indexer configured

        Example:
            >>> pipeline = IngestionPipeline(indexer=indexer)
            >>> results = pipeline.ingest_batch_and_index(["doc1.pdf", "doc2.txt"])
            >>> print(f"Indexed {results['indexed_chunks']} chunks from {results['successful_files']} files")
        """
        if not self.indexer:
            raise ValueError(
                "No indexer configured. Initialize pipeline with indexer parameter "
                "or use ingest_batch() instead."
            )

        start_time = datetime.now()
        logger.info(f"Starting batch ingest and index of {len(file_paths)} documents")

        results = {
            "total_files": len(file_paths),
            "successful_files": 0,
            "failed_files": 0,
            "total_chunks": 0,
            "indexed_chunks": 0,
            "errors": {},
        }

        for file_path in file_paths:
            file_path = Path(file_path)

            try:
                chunks, indexed = self.ingest_and_index_document(file_path)
                results["total_chunks"] += len(chunks)
                results["indexed_chunks"] += indexed
                results["successful_files"] += 1

            except Exception as e:
                results["failed_files"] += 1
                results["errors"][file_path.name] = str(e)
                logger.error(f"Failed to ingest and index {file_path.name}: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        results["elapsed_seconds"] = elapsed

        logger.info(
            f"Batch ingest and index complete: "
            f"{results['successful_files']}/{results['total_files']} files, "
            f"{results['indexed_chunks']}/{results['total_chunks']} chunks indexed, "
            f"elapsed={elapsed:.2f}s"
        )

        return results
