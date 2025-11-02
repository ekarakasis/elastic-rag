# 6. Phase 3: Document Processing Pipeline

**Goal:** Implement document ingestion, conversion, chunking, and embedding generation.

**Duration:** 4-6 days
**Status:** ✅ COMPLETED
**Completed:** October 21, 2025
**Dependencies:** Phase 1, Phase 2

### 6.1 Docling Integration

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 3.1.1 | Research Docling API and capabilities | 🔴 P0 | ✅ | Reviewed documentation |
| 3.1.2 | Create `src/pipeline/document_processor.py` | 🔴 P0 | ✅ | Document conversion module |
| 3.1.3 | Implement document format detection | 🔴 P0 | ✅ | PDF, DOCX, PPTX, HTML, TXT, MD |
| 3.1.4 | Implement text extraction from documents | 🔴 P0 | ✅ | Using Docling |
| 3.1.5 | Implement metadata extraction | 🟡 P1 | ✅ | Title, author, date, page count |
| 3.1.6 | Add error handling for conversion failures | 🔴 P0 | ✅ | Graceful degradation |
| 3.1.7 | Create unit tests for document processor | 🟡 P1 | ✅ | 12 tests with fixtures |

**File Structure:**

```python
# src/pipeline/document_processor.py
"""Document processing and conversion."""
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import docling  # Adjust based on actual API


@dataclass
class DocumentMetadata:
    """Document metadata."""
    filename: str
    format: str
    title: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[str] = None
    page_count: Optional[int] = None


@dataclass
class ProcessedDocument:
    """Processed document with text and metadata."""
    text: str
    metadata: DocumentMetadata


class DocumentProcessor:
    """Processes documents using Docling."""

    SUPPORTED_FORMATS = {".pdf", ".docx", ".pptx", ".html", ".txt"}

    def __init__(self):
        """Initialize document processor."""
        self.converter = None  # Initialize Docling converter

    def is_supported(self, file_path: Path) -> bool:
        """Check if file format is supported."""
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS

    def process_document(self, file_path: Path) -> ProcessedDocument:
        """
        Process a document and extract text and metadata.

        Args:
            file_path: Path to document file

        Returns:
            ProcessedDocument with text and metadata

        Raises:
            ValueError: If format not supported
            RuntimeError: If conversion fails
        """
        if not self.is_supported(file_path):
            raise ValueError(f"Unsupported format: {file_path.suffix}")

        try:
            # Use Docling to convert document
            # This is pseudo-code - adjust based on actual API
            text = self._extract_text(file_path)
            metadata = self._extract_metadata(file_path)

            return ProcessedDocument(text=text, metadata=metadata)

        except Exception as e:
            raise RuntimeError(f"Failed to process {file_path}: {e}")

    def _extract_text(self, file_path: Path) -> str:
        """Extract text from document."""
        # Implement using Docling
        pass

    def _extract_metadata(self, file_path: Path) -> DocumentMetadata:
        """Extract metadata from document."""
        # Implement using Docling
        pass
```

**Verification Steps:**

- [ ] Can import Docling library
- [ ] Can detect supported document formats
- [ ] Can extract text from PDF
- [ ] Can extract text from DOCX
- [ ] Can extract metadata (title, author, etc.)
- [ ] Error handling works for corrupted files

---

### 6.2 Text Chunking Implementation

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 3.2.1 | Research Haystack DocumentSplitter API | 🔴 P0 | ✅ | Reviewed Haystack 2.0 API |
| 3.2.2 | Create `src/pipeline/chunker.py` | 🔴 P0 | ✅ | Text chunking module |
| 3.2.3 | Implement text chunking with overlap | 🔴 P0 | ✅ | Using Haystack DocumentSplitter |
| 3.2.4 | Preserve metadata in chunks | 🔴 P0 | ✅ | Metadata attached to all chunks |
| 3.2.5 | Add configurable chunk size and overlap | 🔴 P0 | ✅ | From config module (512/50) |
| 3.2.6 | Handle edge cases (short documents) | 🟡 P1 | ✅ | Empty text handling |
| 3.2.7 | Create unit tests for chunker | 🟡 P1 | ✅ | 12 comprehensive tests |

**File Structure:**

```python
# src/pipeline/chunker.py
"""Text chunking using Haystack."""
from typing import List
from dataclasses import dataclass
from haystack import Document
from haystack.components.preprocessors import DocumentSplitter
from src.config.settings import get_settings


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
    """Chunks text into smaller pieces for embedding."""

    def __init__(self):
        """Initialize chunker with configuration."""
        settings = get_settings()
        self.chunk_size = settings.chunking.size
        self.chunk_overlap = settings.chunking.overlap

        self.splitter = DocumentSplitter(
            split_length=self.chunk_size,
            split_overlap=self.chunk_overlap,
            split_by="word"
        )

    def chunk_text(
        self,
        text: str,
        source_file: str,
        metadata: dict = None
    ) -> List[TextChunk]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            source_file: Source filename
            metadata: Additional metadata to attach

        Returns:
            List of TextChunk objects
        """
        if not text.strip():
            return []

        # Create Haystack Document
        doc = Document(content=text, meta=metadata or {})

        # Split document
        result = self.splitter.run([doc])
        chunks = result["documents"]

        # Convert to TextChunk objects
        text_chunks = []
        for i, chunk in enumerate(chunks):
            text_chunks.append(TextChunk(
                text=chunk.content,
                chunk_index=i,
                source_file=source_file,
                start_char=0,  # Haystack doesn't provide char positions in basic splitter
                end_char=len(chunk.content),
                metadata=chunk.meta
            ))

        return text_chunks

    def chunk_document(self, processed_doc) -> List[TextChunk]:
        """
        Chunk a processed document.

        Args:
            processed_doc: ProcessedDocument from DocumentProcessor

        Returns:
            List of TextChunk objects
        """
        metadata = {
            "filename": processed_doc.metadata.filename,
            "format": processed_doc.metadata.format,
            "title": processed_doc.metadata.title,
            "author": processed_doc.metadata.author,
        }

        return self.chunk_text(
            text=processed_doc.text,
            source_file=processed_doc.metadata.filename,
            metadata=metadata
        )
```

**Verification Steps:**

- [ ] Can chunk long text into multiple pieces
- [ ] Chunks have proper overlap
- [ ] Chunk size respects configuration
- [ ] Metadata preserved in all chunks
- [ ] Handles short documents correctly
- [ ] Edge cases handled (empty text, very long text)

---

### 6.3 Embedding Generation

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 3.3.1 | Research LiteLLM embedding API | 🔴 P0 | ✅ | Reviewed LiteLLM API |
| 3.3.2 | Create `src/ai_models/embedder.py` | 🔴 P0 | ✅ | Embedding generation module |
| 3.3.3 | Implement LMStudio embedding via LiteLLM | 🔴 P0 | ✅ | Connect to LMStudio |
| 3.3.4 | Add batch embedding support | 🟡 P1 | ✅ | Process multiple chunks |
| 3.3.5 | Implement error handling and retries | 🔴 P0 | ✅ | Handle API failures |
| 3.3.6 | Add embedding caching (optional) | 🟢 P2 | ⬜ | Future enhancement |
| 3.3.7 | Create unit tests for embedder | 🟡 P1 | ✅ | 14 tests with mocking |

**File Structure:**

```python
# src/ai_models/embedder.py
"""Text embedding generation using LiteLLM and LMStudio."""
from typing import List
import litellm
from src.config.settings import get_settings


class Embedder:
    """Generates embeddings using LMStudio via LiteLLM."""

    def __init__(self):
        """Initialize embedder with configuration."""
        settings = get_settings()
        self.base_url = settings.lmstudio.base_url
        self.model = settings.lmstudio.embedding_model
        self.timeout = settings.lmstudio.timeout

        # Configure LiteLLM for LMStudio
        litellm.api_base = self.base_url

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding

        Raises:
            RuntimeError: If embedding generation fails
        """
        try:
            response = litellm.embedding(
                model=self.model,
                input=[text],
                api_base=self.base_url
            )
            return response.data[0]["embedding"]

        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        try:
            response = litellm.embedding(
                model=self.model,
                input=texts,
                api_base=self.base_url
            )
            return [item["embedding"] for item in response.data]

        except Exception as e:
            raise RuntimeError(f"Failed to generate batch embeddings: {e}")
```

**Verification Steps:**

- [ ] Can connect to LMStudio via LiteLLM
- [ ] Can generate embedding for single text
- [ ] Can generate embeddings in batch
- [ ] Embeddings have correct dimensions
- [ ] Error handling works for API failures
- [ ] Timeout configuration respected

---

### 6.4 Pipeline Orchestration

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 3.4.1 | Create `src/pipeline/ingestion.py` | 🔴 P0 | ✅ | Orchestrate full pipeline |
| 3.4.2 | Implement end-to-end ingestion flow | 🔴 P0 | ✅ | Document → chunks → embeddings |
| 3.4.3 | Add progress tracking and logging | 🟡 P1 | ✅ | Detailed logging at each step |
| 3.4.4 | Implement batch processing | 🟡 P1 | ✅ | Process multiple documents |
| 3.4.5 | Add error recovery and rollback | 🟡 P1 | ✅ | Handle partial failures |

**File Structure:**

```python
# src/pipeline/ingestion.py
"""Document ingestion pipeline orchestration."""
from pathlib import Path
from typing import List
import logging
from .document_processor import DocumentProcessor
from .chunker import TextChunker
from ..ai_models.embedder import Embedder

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates document ingestion pipeline."""

    def __init__(self):
        """Initialize pipeline components."""
        self.processor = DocumentProcessor()
        self.chunker = TextChunker()
        self.embedder = Embedder()

    def ingest_document(self, file_path: Path) -> List[dict]:
        """
        Ingest a single document through the full pipeline.

        Args:
            file_path: Path to document

        Returns:
            List of chunks with embeddings ready for indexing
        """
        logger.info(f"Ingesting document: {file_path}")

        # Step 1: Process document
        logger.debug("Processing document...")
        processed_doc = self.processor.process_document(file_path)

        # Step 2: Chunk text
        logger.debug(f"Chunking text (size={self.chunker.chunk_size})...")
        chunks = self.chunker.chunk_document(processed_doc)
        logger.info(f"Created {len(chunks)} chunks")

        # Step 3: Generate embeddings
        logger.debug("Generating embeddings...")
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.embed_batch(texts)

        # Step 4: Combine chunks with embeddings
        indexed_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            indexed_chunks.append({
                "text": chunk.text,
                "embedding": embedding,
                "metadata": {
                    "source_file": chunk.source_file,
                    "chunk_index": chunk.chunk_index,
                    **chunk.metadata
                }
            })

        logger.info(f"Successfully ingested {file_path}")
        return indexed_chunks
```

**Verification Steps:**

- [ ] Can ingest document end-to-end
- [ ] Progress logged at each step
- [ ] Chunks have text, embeddings, and metadata
- [ ] Batch processing works correctly
- [ ] Errors handled and logged appropriately

---

### 6.5 Phase 3 Completion Checklist

- [x] Document processor working for all formats
- [x] Text chunking with proper overlap
- [x] Embedding generation via LMStudio (with LiteLLM)
- [x] Full ingestion pipeline operational
- [x] All unit tests passing (83 unit tests + 12 integration tests)
- [x] Error handling comprehensive
- [x] Logging informative
- [x] Test coverage 96% for pipeline modules
- [x] Sample fixtures created

**Phase 3 Exit Criteria:**

- ✅ Can process PDF, DOCX, HTML, TXT, MD, and other supported formats
- ✅ Documents split into proper chunks with configurable size/overlap
- ✅ Embeddings generated successfully via LiteLLM → LMStudio
- ✅ End-to-end ingestion pipeline works (process → chunk → embed)
- ✅ All tests pass (95 tests total, 96% coverage)
- ✅ Batch processing implemented with error recovery
- ✅ Comprehensive logging and progress tracking
- ✅ **Multi-provider support:** Refactored for provider-agnostic configuration
- ✅ **Easy provider switching:** Can switch between LMStudio, OpenAI, Anthropic, etc.
- ✅ **Backward compatible:** Existing LMStudio configs still work

**Completed:** October 21, 2025
**Refactored:** October 21, 2025 (Multi-provider support added)
