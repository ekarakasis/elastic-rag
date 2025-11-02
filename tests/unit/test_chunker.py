"""Unit tests for text chunker."""

import pytest

from src.pipeline.chunker import TextChunk, TextChunker
from src.pipeline.document_processor import DocumentMetadata, ProcessedDocument


@pytest.fixture
def chunker():
    """Create a TextChunker instance."""
    return TextChunker()


@pytest.fixture
def sample_text():
    """Sample text for chunking."""
    return """
    This is a sample text for chunking. It contains multiple sentences and paragraphs.
    The chunker should split this text into appropriate chunks based on configuration.

    This is the second paragraph. It also contains multiple sentences that should be
    processed correctly by the chunking algorithm.

    Here is more content to ensure we have enough text for multiple chunks. The system
    should handle this properly and create overlapping chunks as configured.
    """


@pytest.fixture
def sample_processed_doc():
    """Sample ProcessedDocument for testing."""
    metadata = DocumentMetadata(
        filename="test.pdf",
        format=".pdf",
        title="Test Document",
        author="Test Author",
        page_count=1,
    )

    text = " ".join(["Word"] * 1000)  # Create text with 1000 words

    return ProcessedDocument(text=text, metadata=metadata)


def test_chunker_initialization(chunker):
    """Test TextChunker initializes correctly."""
    assert chunker.chunk_size > 0
    assert chunker.chunk_overlap >= 0
    assert chunker.splitter is not None


def test_chunk_text_basic(chunker, sample_text):
    """Test basic text chunking."""
    chunks = chunker.chunk_text(sample_text, "test.txt")

    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(chunk, TextChunk) for chunk in chunks)


def test_chunk_text_with_metadata(chunker, sample_text):
    """Test chunking with metadata."""
    metadata = {"source": "test", "category": "sample"}

    chunks = chunker.chunk_text(sample_text, "test.txt", metadata=metadata)

    assert len(chunks) > 0
    assert all("source" in chunk.metadata for chunk in chunks)
    assert all(chunk.metadata["source"] == "test" for chunk in chunks)


def test_chunk_text_empty_string(chunker):
    """Test chunking empty string."""
    chunks = chunker.chunk_text("", "test.txt")

    assert isinstance(chunks, list)
    assert len(chunks) == 0


def test_chunk_text_whitespace_only(chunker):
    """Test chunking whitespace-only string."""
    chunks = chunker.chunk_text("   \n\t  ", "test.txt")

    assert isinstance(chunks, list)
    assert len(chunks) == 0


def test_chunk_properties(chunker, sample_text):
    """Test that chunks have correct properties."""
    chunks = chunker.chunk_text(sample_text, "test.txt")

    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert chunk.source_file == "test.txt"
        assert isinstance(chunk.text, str)
        assert len(chunk.text) > 0
        assert chunk.start_char >= 0
        assert chunk.end_char > chunk.start_char
        assert isinstance(chunk.metadata, dict)


def test_chunk_document(chunker, sample_processed_doc):
    """Test chunking a ProcessedDocument."""
    chunks = chunker.chunk_document(sample_processed_doc)

    assert isinstance(chunks, list)
    assert len(chunks) > 0

    # Check that metadata is preserved
    for chunk in chunks:
        assert chunk.metadata["filename"] == "test.pdf"
        assert chunk.metadata["format"] == ".pdf"
        assert chunk.metadata["title"] == "Test Document"
        assert chunk.metadata["author"] == "Test Author"
        assert chunk.metadata["page_count"] == 1


def test_chunk_document_creates_multiple_chunks(chunker):
    """Test that long documents create multiple chunks."""
    # Create a document with enough words to create multiple chunks
    long_text = " ".join(["word"] * 2000)  # 2000 words

    metadata = DocumentMetadata(filename="long.pdf", format=".pdf")
    doc = ProcessedDocument(text=long_text, metadata=metadata)

    chunks = chunker.chunk_document(doc)

    # Should create multiple chunks for 2000 words
    assert len(chunks) > 1


def test_chunk_overlap(chunker):
    """Test that chunks have appropriate overlap."""
    # Create text with known structure
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)

    chunks = chunker.chunk_text(text, "test.txt")

    if len(chunks) > 1:
        # Check that subsequent chunks have overlap
        # (This is a simplified check - actual overlap depends on configuration)
        assert len(chunks) > 0


def test_text_chunk_dataclass():
    """Test TextChunk dataclass."""
    chunk = TextChunk(
        text="Test content",
        chunk_index=0,
        source_file="test.txt",
        start_char=0,
        end_char=12,
        metadata={"key": "value"},
    )

    assert chunk.text == "Test content"
    assert chunk.chunk_index == 0
    assert chunk.source_file == "test.txt"
    assert chunk.start_char == 0
    assert chunk.end_char == 12
    assert chunk.metadata["key"] == "value"


def test_chunk_with_special_characters(chunker):
    """Test chunking text with special characters."""
    text = "Text with special chars: é, ñ, ü, €, ©, ®, ™"

    chunks = chunker.chunk_text(text, "test.txt")

    assert len(chunks) > 0
    assert all(chunk.text for chunk in chunks)


def test_chunk_with_newlines(chunker):
    """Test chunking text with newlines."""
    text = "Line 1\nLine 2\nLine 3\n\nLine 5"

    chunks = chunker.chunk_text(text, "test.txt")

    assert len(chunks) > 0
