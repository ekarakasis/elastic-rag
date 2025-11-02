"""Unit tests for document processor."""

from pathlib import Path

import pytest

from src.pipeline.document_processor import (
    DocumentMetadata,
    DocumentProcessor,
    ProcessedDocument,
)


@pytest.fixture
def processor():
    """Create a DocumentProcessor instance."""
    return DocumentProcessor()


@pytest.fixture
def sample_txt_file():
    """Path to sample text file."""
    return Path(__file__).parent.parent / "fixtures" / "sample.txt"


@pytest.fixture
def sample_html_file():
    """Path to sample HTML file."""
    return Path(__file__).parent.parent / "fixtures" / "sample.html"


def test_processor_initialization(processor):
    """Test DocumentProcessor initializes correctly."""
    assert processor.converter is not None
    assert processor.SUPPORTED_FORMATS is not None


def test_is_supported_valid_formats(processor):
    """Test is_supported returns True for valid formats."""
    assert processor.is_supported(Path("test.pdf"))
    assert processor.is_supported(Path("test.docx"))
    assert processor.is_supported(Path("test.txt"))
    assert processor.is_supported(Path("test.html"))
    assert processor.is_supported(Path("test.pptx"))


def test_is_supported_invalid_format(processor):
    """Test is_supported returns False for invalid formats."""
    assert not processor.is_supported(Path("test.xyz"))
    assert not processor.is_supported(Path("test.exe"))


def test_process_txt_document(processor, sample_txt_file):
    """Test processing a plain text document."""
    if not sample_txt_file.exists():
        pytest.skip("Sample text file not found")

    result = processor.process_document(sample_txt_file)

    assert isinstance(result, ProcessedDocument)
    assert result.text
    assert len(result.text) > 0
    assert isinstance(result.metadata, DocumentMetadata)
    assert result.metadata.filename == "sample.txt"
    assert result.metadata.format == ".txt"


def test_process_html_document(processor, sample_html_file):
    """Test processing an HTML document."""
    if not sample_html_file.exists():
        pytest.skip("Sample HTML file not found")

    result = processor.process_document(sample_html_file)

    assert isinstance(result, ProcessedDocument)
    assert result.text
    assert len(result.text) > 0
    assert isinstance(result.metadata, DocumentMetadata)
    assert result.metadata.filename == "sample.html"
    assert result.metadata.format == ".html"


def test_process_nonexistent_file(processor):
    """Test processing a file that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        processor.process_document(Path("nonexistent.pdf"))


def test_process_unsupported_format(processor, tmp_path):
    """Test processing an unsupported file format."""
    test_file = tmp_path / "test.xyz"
    test_file.write_text("test content")

    with pytest.raises(ValueError) as exc_info:
        processor.process_document(test_file)

    assert "Unsupported format" in str(exc_info.value)


def test_extract_text_from_txt(processor, tmp_path):
    """Test extracting text from plain text file."""
    test_file = tmp_path / "test.txt"
    test_content = "This is a test document.\nWith multiple lines."
    test_file.write_text(test_content)

    text = processor._extract_text_from_txt(test_file)

    assert text == test_content


def test_extract_text_from_txt_with_encoding(processor, tmp_path):
    """Test extracting text from file with different encoding."""
    test_file = tmp_path / "test.txt"
    test_content = "Test content with special chars: é, ñ, ü"

    # Write with UTF-8 encoding
    test_file.write_text(test_content, encoding="utf-8")

    text = processor._extract_text_from_txt(test_file)

    assert "Test content" in text


def test_create_basic_metadata(processor, tmp_path):
    """Test creating basic metadata for text files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    metadata = processor._create_basic_metadata(test_file)

    assert metadata.filename == "test.txt"
    assert metadata.format == ".txt"
    assert metadata.title == "test"
    assert metadata.author is None
    assert metadata.page_count is None


def test_processed_document_dataclass():
    """Test ProcessedDocument dataclass."""
    metadata = DocumentMetadata(filename="test.pdf", format=".pdf", title="Test", page_count=5)

    doc = ProcessedDocument(text="Test content", metadata=metadata)

    assert doc.text == "Test content"
    assert doc.metadata.filename == "test.pdf"
    assert doc.metadata.page_count == 5


def test_document_metadata_dataclass():
    """Test DocumentMetadata dataclass."""
    metadata = DocumentMetadata(
        filename="test.pdf",
        format=".pdf",
        title="Test Document",
        author="John Doe",
        created_date="2024-01-01",
        page_count=10,
    )

    assert metadata.filename == "test.pdf"
    assert metadata.format == ".pdf"
    assert metadata.title == "Test Document"
    assert metadata.author == "John Doe"
    assert metadata.created_date == "2024-01-01"
    assert metadata.page_count == 10
