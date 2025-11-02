"""Demo script for Phase 4 - Elasticsearch Integration."""

from pathlib import Path

import httpx

from src.pipeline.ingestion import IngestionPipeline
from src.retrieval.elasticsearch_client import ElasticsearchClient
from src.retrieval.index_manager import IndexManager
from src.retrieval.indexer import DocumentIndexer
from src.retrieval.searcher import SemanticSearcher


def print_section(title: str):
    """Print a formatted section header."""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()


def check_prerequisites() -> tuple[bool, bool]:
    """Check if Elasticsearch and LMStudio are running.

    Returns:
        tuple[bool, bool]: (elasticsearch_ok, lmstudio_ok)
    """
    print("🔍 Checking prerequisites...")

    # Check Elasticsearch
    es_ok = False
    try:
        response = httpx.get("http://localhost:9200", timeout=2.0)
        if response.status_code == 200:
            print("✅ Elasticsearch is running")
            es_info = response.json()
            version = es_info.get("version", {}).get("number", "unknown")
            print(f"   Version: {version}")
            es_ok = True
        else:
            print(f"❌ Elasticsearch responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ Elasticsearch is not accessible: {e}")
        print("   Please run: task start")

    # Check LMStudio
    lm_ok = False
    try:
        response = httpx.get("http://localhost:1234/v1/models", timeout=2.0)
        if response.status_code == 200:
            print("✅ LMStudio is running")
            models_data = response.json()
            if models_data.get("data"):
                print(f"   Available models: {len(models_data['data'])}")
            lm_ok = True
        else:
            print(f"⚠️  LMStudio responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ LMStudio is not accessible: {e}")
        print("   Please ensure LMStudio is running with a model loaded")

    print()
    return es_ok, lm_ok


def demo_elasticsearch_connection():
    """Demo 1: Elasticsearch connection and health check."""
    print_section("Demo 1: Elasticsearch Connection & Health Check")

    print("🔌 Initializing Elasticsearch client...")
    es_client = ElasticsearchClient()

    conn_info = es_client.get_connection_info()
    print(f"   Connection: {conn_info['hosts']}")
    print(f"   Index: {conn_info['index']}")
    print(f"   Embedding dimension: {conn_info['embedding_dim']}")
    print(f"   Similarity: {conn_info['similarity']}")
    print()

    print("🏥 Checking cluster health...")
    health = es_client.health_check()
    print(f"   Status: {health['status']} ({health.get('cluster_status', 'unknown')})")
    print(f"   Cluster: {health['cluster_name']}")
    print(f"   Nodes: {health.get('number_of_nodes', 0)}")
    print(f"   Active shards: {health.get('active_shards', 0)}")
    print()

    return es_client


def demo_index_management(es_client: ElasticsearchClient):
    """Demo 2: Index management operations."""
    print_section("Demo 2: Index Management")

    document_store = es_client.get_document_store()
    index_manager = IndexManager(document_store)

    # Check if index exists
    print("📋 Checking index status...")
    if index_manager.index_exists():
        print(f"   ⚠️  Index '{index_manager.index_name}' already exists")
        print("   Deleting for fresh start...")
        index_manager.delete_index()
        print("   ✓ Index deleted")
    else:
        print(f"   Index '{index_manager.index_name}' does not exist yet")

    # Create index
    print()
    print("📋 Creating index...")
    index_manager.ensure_index_exists()
    print(f"   ✓ Index '{index_manager.index_name}' ready")

    # Get initial stats
    print()
    print("📊 Initial index statistics:")
    stats = index_manager.get_index_stats()
    print(f"   Documents: {stats['doc_count']}")
    print(f"   Size: {stats['size_human']}")
    print(f"   Status: {stats['status']}")
    print()

    return index_manager


def demo_document_indexing(document_store):
    """Demo 3: Document indexing."""
    print_section("Demo 3: Document Indexing")

    # Initialize components
    indexer = DocumentIndexer(document_store)
    pipeline = IngestionPipeline(indexer=indexer)

    # Get sample files
    project_root = Path(__file__).parent.parent
    sample_files = [
        project_root / "tests" / "fixtures" / "sample.txt",
        project_root / "tests" / "fixtures" / "sample.html",
    ]

    # Filter existing files
    existing_files = [f for f in sample_files if f.exists()]

    if not existing_files:
        print("❌ No sample files found in tests/fixtures/")
        return indexer, 0

    print(f"📄 Found {len(existing_files)} sample documents")
    print()

    # Ingest and index each document
    total_indexed = 0
    for file_path in existing_files:
        print(f"Processing: {file_path.name}")
        chunks, indexed = pipeline.ingest_and_index_document(file_path)
        total_indexed += indexed
        print(f"   ✓ Indexed {indexed} chunks from {file_path.name}")

    print()
    print(f"✅ Total indexed: {total_indexed} chunks from {len(existing_files)} documents")
    print()

    return indexer, total_indexed


def demo_vector_search(searcher: SemanticSearcher):
    """Demo 4: Semantic search with vector embeddings."""
    print_section("Demo 4: Vector Similarity Search (Semantic)")

    test_queries = [
        "What is this document about?",
        "elastic search",
    ]

    for query in test_queries:
        print(f"🔍 Query: '{query}'")
        results = searcher.search(query, top_k=3)

        print(f"   Found {len(results)} results")

        for i, result in enumerate(results, 1):
            print(f"\n   Result {i}:")
            print(f"   Score: {result['score']:.4f}")
            print(f"   Source: {result['metadata'].get('source_file', 'unknown')}")
            preview = result["text"][:100] + "..." if len(result["text"]) > 100 else result["text"]
            print(f"   Text: {preview}")

        print()


def demo_keyword_search(searcher: SemanticSearcher):
    """Demo 5: BM25 keyword search."""
    print_section("Demo 5: BM25 Keyword Search")

    test_query = "elastic search"

    print(f"🔍 Keyword Query: '{test_query}'")
    results = searcher.keyword_search(test_query, top_k=3)

    print(f"   Found {len(results)} results")

    for i, result in enumerate(results, 1):
        print(f"\n   Result {i}:")
        print(f"   Score: {result['score']:.4f}")
        print(f"   Source: {result['metadata'].get('source_file', 'unknown')}")
        preview = result["text"][:100] + "..." if len(result["text"]) > 100 else result["text"]
        print(f"   Text: {preview}")

    print()


def demo_hybrid_search(searcher: SemanticSearcher):
    """Demo 6: Hybrid search combining vector and BM25."""
    print_section("Demo 6: Hybrid Search (Vector + BM25)")

    test_query = "What is elasticsearch?"

    print(f"🔍 Hybrid Query: '{test_query}'")
    print("   Combining semantic (70%) and keyword (30%) search")

    results = searcher.hybrid_search(test_query, top_k=3, vector_weight=0.7, keyword_weight=0.3)

    print(f"   Found {len(results)} combined results")

    for i, result in enumerate(results, 1):
        print(f"\n   Result {i}:")
        print(f"   Combined Score: {result['score']:.4f}")
        print(f"   Source: {result['metadata'].get('source_file', 'unknown')}")
        preview = result["text"][:100] + "..." if len(result["text"]) > 100 else result["text"]
        print(f"   Text: {preview}")

    print()


def demo_metadata_filtering(searcher: SemanticSearcher):
    """Demo 7: Metadata filtering."""
    print_section("Demo 7: Metadata Filtering")

    test_query = "document"

    # Example 1: Filter by source file
    print(f"🔍 Query with filter: '{test_query}' (source_file='sample.txt')")
    results = searcher.search_with_filters(test_query, top_k=3, source_file="sample.txt")

    print(f"   Found {len(results)} results from sample.txt")

    if results:
        for i, result in enumerate(results[:2], 1):
            print(f"\n   Result {i}:")
            print(f"   Score: {result['score']:.4f}")
            print(f"   Source: {result['metadata'].get('source_file')}")

    print()

    # Example 2: Filter by format
    print(f"🔍 Query with filter: '{test_query}' (format='html')")
    filters = {"format": "html"}
    results = searcher.search(test_query, top_k=3, filters=filters)

    print(f"   Found {len(results)} results with format=html")

    print()


def demo_index_statistics(index_manager: IndexManager):
    """Demo 8: Final index statistics."""
    print_section("Demo 8: Final Index Statistics")

    stats = index_manager.get_index_stats()

    print("📊 Index Statistics:")
    print(f"   Documents: {stats['doc_count']}")
    print(f"   Size: {stats['size_human']}")
    print(f"   Status: {stats['status']}")
    print(f"   Segments: {stats.get('segments', 'N/A')}")
    print()


def main():
    """Run the complete Phase 4 demo."""
    print_section("Elastic RAG - Phase 4 Demo: Elasticsearch Integration")

    # Check prerequisites
    es_ok, lm_ok = check_prerequisites()

    if not es_ok:
        print("❌ Cannot proceed without Elasticsearch")
        print("   Please start services: task start")
        return

    if not lm_ok:
        print("❌ Cannot proceed without LMStudio")
        print("   Please start LMStudio with an embedding model")
        return

    try:
        # Demo 1: Connection
        es_client = demo_elasticsearch_connection()

        # Demo 2: Index Management
        index_manager = demo_index_management(es_client)

        # Demo 3: Document Indexing
        document_store = es_client.get_document_store()
        indexer, total_indexed = demo_document_indexing(document_store)

        if total_indexed == 0:
            print("❌ No documents indexed, cannot demonstrate search")
            return

        # Initialize searcher
        searcher = SemanticSearcher(document_store)

        # Demo 4: Vector Search
        demo_vector_search(searcher)

        # Demo 5: BM25 Keyword Search
        demo_keyword_search(searcher)

        # Demo 6: Hybrid Search
        demo_hybrid_search(searcher)

        # Demo 7: Metadata Filtering
        demo_metadata_filtering(searcher)

        # Demo 8: Statistics
        demo_index_statistics(index_manager)

        # Final Summary
        print_section("✅ Phase 4 Demo Complete!")

        print("Features Demonstrated:")
        print("  ✓ Elasticsearch connection and health checks")
        print("  ✓ Index management (create, delete, stats)")
        print("  ✓ Document indexing (single + batch)")
        print("  ✓ Vector similarity search (semantic)")
        print("  ✓ BM25 keyword search")
        print("  ✓ Hybrid search (vector + keyword)")
        print("  ✓ Metadata filtering")
        print()

        print("Statistics:")
        print(f"  • Documents indexed: {total_indexed} chunks")
        print(f"  • Index size: {index_manager.get_index_stats()['size_human']}")
        print("  • Search modes: 3 (vector, BM25, hybrid)")
        print()

        print("✅ Ready for: Phase 5 (LLM & Agent Implementation)")
        print()

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
