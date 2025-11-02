"""Text chunking using Haystack DocumentSplitter."""

import logging
from dataclasses import dataclass

from haystack import Document
from haystack.components.preprocessors import DocumentSplitter

from src.config.settings import get_settings
from src.pipeline.document_processor import ProcessedDocument

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """A chunk of text with metadata."""

    text: str
    chunk_index: int
    source_file: str
    start_char: int
    end_char: int
    metadata: dict


class TextChunker:
    """Chunks text into smaller pieces for embedding using Haystack."""

    def __init__(self):
        """Initialize chunker with configuration from settings."""
        settings = get_settings()
        self.chunk_size = settings.chunking.size
        self.chunk_overlap = settings.chunking.overlap

        # Initialize Haystack DocumentSplitter
        self.splitter = DocumentSplitter(
            split_length=self.chunk_size,
            split_overlap=self.chunk_overlap,
            split_by="word",  # Split by word count
        )

        logger.info(
            f"TextChunker initialized with size={self.chunk_size}, " f"overlap={self.chunk_overlap}"
        )

    def chunk_text(
        self, text: str, source_file: str, metadata: dict | None = None
    ) -> list[TextChunk]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            source_file: Source filename
            metadata: Additional metadata to attach

        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            logger.warning(f"Empty text provided for chunking from {source_file}")
            return []

        logger.debug(f"Chunking text from {source_file} ({len(text)} characters)")

        # Create Haystack Document
        doc = Document(content=text, meta=metadata or {})

        # Split document using Haystack
        result = self.splitter.run([doc])
        chunks = result["documents"]

        logger.info(f"Created {len(chunks)} chunks from {source_file}")

        # Convert to TextChunk objects
        text_chunks = []
        cumulative_length = 0

        for i, chunk in enumerate(chunks):
            chunk_text = chunk.content
            chunk_length = len(chunk_text)

            text_chunks.append(
                TextChunk(
                    text=chunk_text,
                    chunk_index=i,
                    source_file=source_file,
                    start_char=cumulative_length,
                    end_char=cumulative_length + chunk_length,
                    metadata={**chunk.meta, "chunk_index": i},
                )
            )

            # Update cumulative length (accounting for overlap)
            cumulative_length += chunk_length - self.chunk_overlap

        return text_chunks

    def chunk_document(self, processed_doc: ProcessedDocument) -> list[TextChunk]:
        """
        Chunk a processed document.

        Args:
            processed_doc: ProcessedDocument from DocumentProcessor

        Returns:
            List of TextChunk objects
        """
        logger.info(f"Chunking document: {processed_doc.metadata.filename}")

        # Prepare metadata to include with each chunk
        metadata = {
            "filename": processed_doc.metadata.filename,
            "format": processed_doc.metadata.format,
            "title": processed_doc.metadata.title,
            "author": processed_doc.metadata.author,
            "created_date": processed_doc.metadata.created_date,
            "page_count": processed_doc.metadata.page_count,
        }

        return self.chunk_text(
            text=processed_doc.text,
            source_file=processed_doc.metadata.filename,
            metadata=metadata,
        )
