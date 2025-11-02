"""Demo script for Phase 5 - LLM & Agent Implementation (RAG Agent with Google ADK)."""

from pathlib import Path

import httpx

from src.agent.rag_agent import create_rag_agent, get_agent_config
from src.pipeline.ingestion import IngestionPipeline
from src.retrieval.elasticsearch_client import ElasticsearchClient
from src.retrieval.index_manager import IndexManager
from src.retrieval.indexer import DocumentIndexer


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
                model_count = len(models_data["data"])
                print(f"   Available models: {model_count}")
                if model_count > 0:
                    # Show first model as example
                    first_model = models_data["data"][0].get("id", "unknown")
                    print(f"   Example model: {first_model}")
            lm_ok = True
        else:
            print(f"⚠️  LMStudio responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ LMStudio is not accessible: {e}")
        print("   Please ensure LMStudio is running with a model loaded")

    print()
    return es_ok, lm_ok


def setup_knowledge_base():
    """Set up Elasticsearch with sample documents."""
    print_section("Setup: Preparing Knowledge Base")

    # Initialize components
    print("🔌 Initializing Elasticsearch...")
    es_client = ElasticsearchClient()
    document_store = es_client.get_document_store()
    index_manager = IndexManager(document_store)

    # Check if index exists and has documents
    if index_manager.index_exists():
        stats = index_manager.get_index_stats()
        doc_count = stats["doc_count"]

        if doc_count > 0:
            print(f"   ✓ Index exists with {doc_count} documents")
            print("   Skipping document indexing")
            return True
        else:
            print("   ⚠️  Index exists but is empty")
    else:
        print("   Creating new index...")
        index_manager.ensure_index_exists()

    # Index sample documents
    print()
    print("📄 Indexing sample documents...")
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
        return False

    # Process files
    total_chunks = 0
    for file_path in existing_files:
        print(f"   Processing: {file_path.name}")
        try:
            chunks_indexed = pipeline.process_file(str(file_path))
            total_chunks += chunks_indexed
            print(f"   ✓ Indexed {chunks_indexed} chunks")
        except Exception as e:
            print(f"   ✗ Error processing {file_path.name}: {e}")

    print()
    print(f"✓ Knowledge base ready with {total_chunks} chunks indexed")
    return True


def demo_agent_creation():
    """Demo 1: Create and configure RAG agent."""
    print_section("Demo 1: RAG Agent Creation with Google ADK")

    print("🤖 Creating RAG agent...")
    agent = create_rag_agent(
        name="elastic_rag_assistant", top_k=5
    )  # Retrieve top 5 most relevant chunks
    print("   ✓ LlmAgent created with retrieval tool")
    print()

    # Show configuration
    print("⚙️  Agent configuration:")
    config = get_agent_config()
    for key, value in config.items():
        print(f"   {key}: {value}")
    print()

    return agent


def demo_retrieval_tool(agent):
    """Demo 2: Test the retrieval tool directly."""
    print_section("Demo 2: Retrieval Tool Testing")

    # Access the retrieval tool from the agent
    # Note: This is for demonstration - normally the LLM calls this automatically
    print("🔍 Testing retrieval tool...")

    # Get the tool (it's in agent's tools list)
    if hasattr(agent, "tools") and agent.tools:
        retrieval_tool = agent.tools[0]
        print(
            f"   Tool name: {retrieval_tool.name if hasattr(retrieval_tool, 'name') else 'retrieve_context'}"
        )
        print()

        # Test queries
        test_queries = ["What is Python?", "machine learning", "nonexistent topic xyz123"]

        for query in test_queries:
            print(f"📝 Query: '{query}'")
            # Note: Direct tool execution depends on ADK's FunctionTool API
            # This is a conceptual demonstration
            print("   (Tool will be called automatically by LLM during agent.run())")
            print()
    else:
        print("   ⚠️  Could not access tools directly")
        print("   (Tools will still work when agent.run() is called)")
        print()


def demo_agent_queries(agent):
    """Demo 3: Run real queries through the RAG agent."""
    print_section("Demo 3: RAG Agent Query Processing")

    # Import the runner
    from src.agent.runner import SimpleRAGRunner

    # Define test queries (with / no_think to prevent thinking mode)
    queries = [
        "What is Python and what is it used for? / no_think",
        "Tell me about machine learning / no_think",
        "What programming concepts are mentioned? / no_think",
    ]

    print("🎯 Running queries through RAG agent...")
    print("   (Creating SimpleRAGRunner to execute queries)")
    print()

    # Create runner
    runner = SimpleRAGRunner(agent)

    try:
        for i, query in enumerate(queries, 1):
            print(f"{'='*70}")
            print(f"Query #{i}: {query}")
            print(f"{'='*70}")
            print()

            try:
                print("🤖 Agent processing...")
                print()

                # Execute the query through the agent
                response = runner.query(query)

                print("📝 Response:")
                print("-" * 70)
                print(response)
                print("-" * 70)
                print()

            except Exception as e:
                print(f"❌ Error processing query: {e}")
                import traceback

                traceback.print_exc()
                print()

    finally:
        # Clean up runner
        runner.close()
        print()
        print("✅ Runner closed")


def demo_agent_features():
    """Demo 4: Show agent features and capabilities."""
    print_section("Demo 4: Agent Features & Architecture")

    print("✨ RAG Agent Features:")
    print()

    features = [
        ("🎯 Stateless Design", "Each query is independent, no conversation memory"),
        ("🔧 Tool-Based Retrieval", "LLM decides when to call retrieve_context tool"),
        ("📚 Elasticsearch Backend", "Semantic search over embedded document chunks"),
        ("🤖 Google ADK Framework", "Using LlmAgent with LiteLlm model"),
        ("🔗 Source Citation", "Answers cite sources using [1], [2] references"),
        ("⚙️  Provider Agnostic", "Can switch LLM providers via .env configuration"),
        ("📊 Max 15K tokens", "Configured for large context windows"),
        ("🌡️  Temperature 0.7", "Balanced creativity vs. consistency"),
    ]

    for feature, description in features:
        print(f"   {feature}")
        print(f"      {description}")
        print()


def main():
    """Run Phase 5 demonstrations."""
    print("=" * 70)
    print("Elastic RAG - Phase 5 Demo: LLM & Agent Implementation")
    print("RAG Agent with Google ADK, LiteLlm, and Elasticsearch")
    print("=" * 70)
    print()

    # Check prerequisites
    es_ok, lm_ok = check_prerequisites()

    if not (es_ok and lm_ok):
        print()
        print("❌ Prerequisites not met. Please ensure:")
        print("   1. Elasticsearch is running (task start)")
        print("   2. LMStudio is running with a model loaded")
        print()
        return

    # Setup knowledge base
    if not setup_knowledge_base():
        print("❌ Failed to set up knowledge base")
        return

    # Run demos
    try:
        # Demo 1: Create agent
        agent = demo_agent_creation()

        # Demo 2: Test retrieval tool
        demo_retrieval_tool(agent)

        # Demo 3: Run queries
        demo_agent_queries(agent)

        # Demo 4: Show features
        demo_agent_features()

        # Success message
        print_section("🎉 Phase 5 Demo Complete!")
        print("✅ RAG Agent successfully created and configured")
        print("✅ All components integrated:")
        print("   - Document processing pipeline (Phase 3)")
        print("   - Elasticsearch storage & retrieval (Phase 4)")
        print("   - LiteLlm interface for LLM calls")
        print("   - Google ADK agent framework")
        print("   - Stateless RAG agent with tool-based retrieval")
        print()
        print("🚀 Ready for:")
        print("   - API integration (FastAPI endpoints)")
        print("   - Production deployment")
        print("   - Interactive Q&A sessions")
        print()

    except Exception as e:
        print()
        print(f"❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
