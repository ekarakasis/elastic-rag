"""Demo script for Phase 3 - Document Processing Pipeline."""

from pathlib import Path

from src.pipeline.ingestion import IngestionPipeline


def main():
    """Demonstrate the document processing pipeline."""
    print("=" * 70)
    print("Elastic RAG - Phase 3 Demo: Document Processing Pipeline")
    print("=" * 70)
    print()

    # Initialize pipeline
    print("🚀 Initializing ingestion pipeline...")
    pipeline = IngestionPipeline()
    print("   ✓ DocumentProcessor initialized")
    print("   ✓ TextChunker initialized")
    print("   ✓ Embedder initialized")
    print()

    # Get sample file (navigate to project root, then to tests/fixtures)
    project_root = Path(__file__).parent.parent
    sample_file = project_root / "tests" / "fixtures" / "sample.txt"

    if not sample_file.exists():
        print(f"❌ Sample file not found: {sample_file}")
        print("   Please run this from the project root directory")
        return

    print(f"📄 Processing document: {sample_file.name}")
    print()

    try:
        # Check LMStudio connection first
        import httpx

        try:
            response = httpx.get("http://localhost:1234/v1/models", timeout=2.0)
            if response.status_code == 200:
                print("✅ LMStudio is running and accessible")
                models_data = response.json()
                if models_data.get("data"):
                    print(f"   Available models: {len(models_data['data'])}")
                print()
            else:
                print("⚠️  LMStudio responded but with unexpected status")
                print()
        except Exception as e:
            print("❌ LMStudio is not accessible at http://localhost:1234")
            print(f"   Error: {e}")
            print("   Please ensure LMStudio is running with a model loaded.")
            return

        # Run the full pipeline with real embeddings
        print("🚀 Running FULL pipeline with LMStudio embeddings...")
        print()

        import time

        start_time = time.time()

        # Use the complete pipeline
        indexed_chunks = pipeline.ingest_document(sample_file)

        elapsed = time.time() - start_time

        print()
        print("=" * 70)
        print("✅ Phase 3 Pipeline Demo Complete!")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  • Document processed: {sample_file.name}")
        print(f"  • Processing time: {elapsed:.2f} seconds")
        print(f"  • Chunks created: {len(indexed_chunks)}")
        print(
            f"  • Embedding dimension: {len(indexed_chunks[0]['embedding']) if indexed_chunks else 'N/A'}"
        )
        print()

        print("First chunk details:")
        if indexed_chunks:
            chunk = indexed_chunks[0]
            preview = chunk["text"][:150] + "..." if len(chunk["text"]) > 150 else chunk["text"]
            print(f"  • Text preview: {preview}")
            print(f"  • Embedding sample (first 5 dims): {chunk['embedding'][:5]}")
            print(f"  • Source file: {chunk['metadata']['source_file']}")
            print(f"  • Chunk index: {chunk['metadata']['chunk_index']}")
            print(f"  • Indexed at: {chunk['metadata']['indexed_at']}")
        print()

        print("✅ Ready for: Elasticsearch indexing (Phase 4)")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("This is expected if LMStudio is not running.")
        print("All tests use mocked embeddings to avoid this requirement.")


if __name__ == "__main__":
    main()
