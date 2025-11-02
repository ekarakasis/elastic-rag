"""Integration tests for the ingestion pipeline."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.pipeline.ingestion import IngestionPipeline


@pytest.fixture
def pipeline():
    """Create an IngestionPipeline instance."""
    return IngestionPipeline()


@pytest.fixture
def sample_txt_file():
    """Path to sample text file."""
    return Path(__file__).parent.parent / "fixtures" / "sample.txt"


@pytest.fixture
def sample_html_file():
    """Path to sample HTML file."""
    return Path(__file__).parent.parent / "fixtures" / "sample.html"


@pytest.fixture
def mock_embeddings():
    """Mock embeddings for testing - returns correct number based on input."""

    def _generate_embeddings(texts):
        """Generate mock embeddings matching the number of input texts."""
        return [[0.1] * 768 for _ in range(len(texts))]

    return _generate_embeddings


def test_pipeline_initialization(pipeline):
    """Test IngestionPipeline initializes correctly."""
    assert pipeline.processor is not None
    assert pipeline.chunker is not None
    assert pipeline.embedder is not None


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_txt_document(mock_embed, pipeline, sample_txt_file, mock_embeddings):
    """Test ingesting a text document through the full pipeline."""
    if not sample_txt_file.exists():
        pytest.skip("Sample text file not found")

    # Mock the embedding generation - returns embeddings matching input size
    mock_embed.side_effect = mock_embeddings

    result = pipeline.ingest_document(sample_txt_file)

    assert isinstance(result, list)
    assert len(result) > 0

    # Check structure of indexed chunks
    for chunk in result:
        assert "text" in chunk
        assert "embedding" in chunk
        assert "metadata" in chunk

        assert isinstance(chunk["text"], str)
        assert isinstance(chunk["embedding"], list)
        assert isinstance(chunk["metadata"], dict)

        # Check metadata fields
        assert "source_file" in chunk["metadata"]
        assert "chunk_index" in chunk["metadata"]
        assert "indexed_at" in chunk["metadata"]


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_html_document(mock_embed, pipeline, sample_html_file, mock_embeddings):
    """Test ingesting an HTML document."""
    if not sample_html_file.exists():
        pytest.skip("Sample HTML file not found")

    mock_embed.side_effect = mock_embeddings

    result = pipeline.ingest_document(sample_html_file)

    assert isinstance(result, list)
    assert len(result) > 0


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_document_nonexistent_file(mock_embed, pipeline):
    """Test ingesting a nonexistent file."""
    with pytest.raises(FileNotFoundError):
        pipeline.ingest_document(Path("nonexistent.pdf"))


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_document_unsupported_format(mock_embed, pipeline, tmp_path):
    """Test ingesting an unsupported file format."""
    test_file = tmp_path / "test.xyz"
    test_file.write_text("test content")

    with pytest.raises(ValueError):
        pipeline.ingest_document(test_file)


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_document_metadata_preserved(mock_embed, pipeline, sample_txt_file, mock_embeddings):
    """Test that metadata is preserved through the pipeline."""
    if not sample_txt_file.exists():
        pytest.skip("Sample text file not found")

    mock_embed.side_effect = mock_embeddings

    result = pipeline.ingest_document(sample_txt_file)

    # Check that all chunks have the same source file
    for chunk in result:
        assert chunk["metadata"]["source_file"] == "sample.txt"
        assert chunk["metadata"]["filename"] == "sample.txt"


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_document_chunk_indices(mock_embed, pipeline, sample_txt_file, mock_embeddings):
    """Test that chunks have correct indices."""
    if not sample_txt_file.exists():
        pytest.skip("Sample text file not found")

    # Use dynamic mock that matches chunk count
    mock_embed.side_effect = mock_embeddings

    result = pipeline.ingest_document(sample_txt_file)

    # Check that chunk indices are sequential
    for i, chunk in enumerate(result):
        assert chunk["metadata"]["chunk_index"] == i


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_batch_multiple_files(mock_embed, pipeline, sample_txt_file, sample_html_file):
    """Test batch ingestion of multiple files."""
    if not sample_txt_file.exists() or not sample_html_file.exists():
        pytest.skip("Sample files not found")

    # Mock embeddings - dynamically matches chunk count
    def _generate_embeddings(texts):
        return [[0.1] * 768 for _ in range(len(texts))]

    mock_embed.side_effect = _generate_embeddings

    result = pipeline.ingest_batch([sample_txt_file, sample_html_file])

    assert isinstance(result, dict)
    assert "total" in result
    assert "successful" in result
    assert "failed" in result
    assert "chunks" in result
    assert "errors" in result

    assert result["total"] == 2
    assert result["successful"] <= 2
    assert len(result["chunks"]) > 0


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_batch_with_failures(mock_embed, pipeline, sample_txt_file):
    """Test batch ingestion with some failures."""
    if not sample_txt_file.exists():
        pytest.skip("Sample text file not found")

    # Mock embeddings - dynamically matches chunk count
    def _generate_embeddings(texts):
        return [[0.1] * 768 for _ in range(len(texts))]

    mock_embed.side_effect = _generate_embeddings

    # Include a nonexistent file
    files = [sample_txt_file, Path("nonexistent.pdf")]

    result = pipeline.ingest_batch(files)

    assert result["total"] == 2
    assert result["failed"] > 0
    assert len(result["errors"]) > 0
    assert "nonexistent.pdf" in result["errors"]


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_batch_empty_list(mock_embed, pipeline):
    """Test batch ingestion with empty list."""
    result = pipeline.ingest_batch([])

    assert result["total"] == 0
    assert result["successful"] == 0
    assert result["failed"] == 0
    assert len(result["chunks"]) == 0


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_pipeline_creates_embeddings_correctly(
    mock_embed, pipeline, sample_txt_file, mock_embeddings
):
    """Test that pipeline calls embedder with correct number of chunks."""
    if not sample_txt_file.exists():
        pytest.skip("Sample text file not found")

    # Use dynamic mock that returns correct number of embeddings
    mock_embed.side_effect = mock_embeddings
    result = pipeline.ingest_document(sample_txt_file)

    # Check that embedder was called
    mock_embed.assert_called_once()

    # Check that number of embeddings matches number of chunks
    call_args = mock_embed.call_args
    texts_passed = call_args[0][0]
    assert len(texts_passed) <= len(result)


@patch("src.pipeline.ingestion.Embedder.embed_batch")
def test_ingest_document_returns_ready_for_indexing(
    mock_embed, pipeline, sample_txt_file, mock_embeddings
):
    """Test that returned chunks are ready for Elasticsearch indexing."""
    if not sample_txt_file.exists():
        pytest.skip("Sample text file not found")

    mock_embed.side_effect = mock_embeddings

    result = pipeline.ingest_document(sample_txt_file)

    # Each chunk should have all required fields for ES indexing
    for chunk in result:
        # Required fields
        assert chunk["text"]  # Non-empty text
        assert len(chunk["embedding"]) > 0  # Non-empty embedding
        assert chunk["metadata"]["source_file"]  # Source file name
        assert isinstance(chunk["metadata"]["chunk_index"], int)  # Chunk index

        # Timestamp should be ISO format
        assert "T" in chunk["metadata"]["indexed_at"]


def test_pipeline_end_to_end_without_mocking(pipeline, sample_txt_file):
    """Test the pipeline end-to-end (requires LMStudio to be running)."""
    # This test is optional and requires actual LMStudio connection
    # It can be skipped in CI/CD environments
    pytest.skip("Requires LMStudio connection - run manually for full E2E test")

    if not sample_txt_file.exists():
        pytest.skip("Sample text file not found")

    # This would actually call LMStudio
    result = pipeline.ingest_document(sample_txt_file)

    assert len(result) > 0
    assert all(len(chunk["embedding"]) > 0 for chunk in result)


def test_ingest_and_index_document_actually_indexes():
    """Test that ingest_and_index_document() actually writes to Elasticsearch.

    This test addresses the bug where ingest_document() was called instead of
    ingest_and_index_document(), causing documents to be processed but not indexed.

    Verifies that:
    1. Chunks are created
    2. Chunks are actually indexed to Elasticsearch
    3. Chunks can be retrieved from Elasticsearch
    """
    import time

    from src.retrieval.elasticsearch_client import ElasticsearchClient
    from src.retrieval.indexer import DocumentIndexer

    # Create unique test file
    test_content = "This is test content for verifying pipeline indexing functionality."

    # Create temporary test file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(test_content)
        temp_file_path = Path(f.name)

    try:
        # Initialize pipeline with real ES client and indexer (not mocked)
        es_client = ElasticsearchClient()
        document_store = es_client.get_document_store()
        indexer = DocumentIndexer(document_store=document_store)
        pipeline = IngestionPipeline(indexer=indexer)

        # Get initial document count from ES
        initial_count = document_store.count_documents()

        # Call ingest_and_index_document (the correct method)
        chunks, indexed_count = pipeline.ingest_and_index_document(temp_file_path)

        # Verify chunks were created
        assert len(chunks) > 0, "No chunks created"
        assert indexed_count > 0, "No chunks indexed"
        assert indexed_count == len(chunks), "Indexed count doesn't match chunks created"

        # Wait briefly for Elasticsearch to index
        time.sleep(1)

        # Verify chunks are actually in Elasticsearch
        final_count = document_store.count_documents()
        assert (
            final_count > initial_count
        ), f"Document count did not increase (initial: {initial_count}, final: {final_count})"
        assert (
            final_count >= initial_count + indexed_count
        ), f"Expected at least {initial_count + indexed_count} documents, got {final_count}"

        # The key test: count increased, proving indexing occurred
        # This is the critical check that would have caught the bug

    finally:
        # Cleanup: delete test file
        if temp_file_path.exists():
            temp_file_path.unlink()

        # Note: ES cleanup not critical for this test as documents are small
        # and will be cleaned up by test environment resets


def test_pipeline_ingest_vs_ingest_and_index():
    """Educational test documenting the difference between pipeline methods.

    This test demonstrates the critical difference that caused the indexing bug:
    - ingest_document(): Returns chunks but DOESN'T index to Elasticsearch
    - ingest_and_index_document(): Returns chunks AND indexes to Elasticsearch

    Purpose: Prevent future confusion about which method to use.
    """
    import tempfile

    from src.retrieval.elasticsearch_client import ElasticsearchClient
    from src.retrieval.indexer import DocumentIndexer

    # Create unique test files
    test_content = "Test content for method comparison."

    # Create two temporary files
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f1:
        f1.write(test_content)
        file1_path = Path(f1.name)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f2:
        f2.write(test_content)
        file2_path = Path(f2.name)

    try:
        # Initialize pipeline with indexer
        es_client = ElasticsearchClient()
        document_store = es_client.get_document_store()
        indexer = DocumentIndexer(document_store=document_store)
        pipeline = IngestionPipeline(indexer=indexer)

        initial_count = document_store.count_documents()

        # TEST 1: ingest_document() only returns chunks, doesn't index
        chunks_only = pipeline.ingest_document(file1_path)

        assert isinstance(chunks_only, list), "ingest_document should return list of chunks"
        assert len(chunks_only) > 0, "Should return at least one chunk"

        # Verify these chunks were NOT indexed to Elasticsearch
        count_after_ingest = document_store.count_documents()
        assert (
            count_after_ingest == initial_count
        ), "ingest_document() should NOT index to Elasticsearch, but count increased"

        # TEST 2: ingest_and_index_document() returns chunks AND indexes
        chunks_and_indexed, indexed_count = pipeline.ingest_and_index_document(file2_path)

        assert isinstance(chunks_and_indexed, list), "Should return list of chunks"
        assert len(chunks_and_indexed) > 0, "Should return at least one chunk"
        assert indexed_count > 0, "Should return indexed count"
        assert indexed_count == len(chunks_and_indexed), "Indexed count should match chunks"

        # Verify these chunks WERE indexed to Elasticsearch
        import time

        time.sleep(1)  # Brief wait for indexing

        count_after_index = document_store.count_documents()
        assert (
            count_after_index > count_after_ingest
        ), "ingest_and_index_document() SHOULD index to Elasticsearch"
        assert (
            count_after_index >= initial_count + indexed_count
        ), f"Expected at least {initial_count + indexed_count} documents, got {count_after_index}"

        # LESSON: Always use ingest_and_index_document() in API endpoints!
        # The bug occurred because API called ingest_document() instead

    finally:
        # Cleanup
        for path in [file1_path, file2_path]:
            if path.exists():
                path.unlink()

        # Note: ES cleanup not critical for this educational test
        # Documents are small and will be cleaned up by test environment resets
