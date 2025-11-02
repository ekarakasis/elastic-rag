# 7. Phase 4: Elasticsearch Integration

**Goal:** Implement indexing and retrieval using Elasticsearch.

**Duration:** 3-4 days
**Status:** ✅ COMPLETED
**Completed:** October 21, 2025
**Dependencies:** Phase 2, Phase 3

**Summary:** Successfully implemented Elasticsearch integration using Haystack's elasticsearch-haystack package. Created client wrapper, index manager, document indexer, and multi-mode searcher (vector, BM25, hybrid). All functionality tested and working with 80% code coverage on Phase 4 modules.

### 7.1 Elasticsearch Client Setup

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 4.1.1 | Create `src/retrieval/elasticsearch_client.py` | 🔴 P0 | ✅ | ES client wrapper using Haystack |
| 4.1.2 | Implement ElasticsearchDocumentStore initialization | 🔴 P0 | ✅ | Use elasticsearch-haystack integration |
| 4.1.3 | Add connection health checks | 🔴 P0 | ✅ | Verify ES availability |
| 4.1.4 | Implement authentication (future) | 🟢 P2 | ⬜ | Username/password support |
| 4.1.5 | Create unit tests with mocked ES | 🟡 P1 | ✅ | Test without real ES |

**Implementation Note:**

Use the `elasticsearch-haystack` integration package which provides `ElasticsearchDocumentStore`:

```python
# Installation: pip install elasticsearch-haystack
from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore

# Initialize document store
document_store = ElasticsearchDocumentStore(
    hosts="http://localhost:9200",
    index="documents"
)
```

### 7.2 Index Management

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 4.2.1 | Design Elasticsearch index schema | 🔴 P0 | ✅ | Define mappings for Haystack |
| 4.2.2 | Create `src/retrieval/index_manager.py` | 🔴 P0 | ✅ | Wrapper around ElasticsearchDocumentStore |
| 4.2.3 | Implement index creation with mappings | 🔴 P0 | ✅ | Dense vector + metadata |
| 4.2.4 | Implement index deletion | 🟡 P1 | ✅ | For cleanup/reset |
| 4.2.5 | Add index existence check | 🔴 P0 | ✅ | Before creating/using |
| 4.2.6 | Implement index settings optimization | 🟡 P1 | ✅ | Shards, replicas |

**Implementation Note:**

The `ElasticsearchDocumentStore` from `elasticsearch-haystack` handles index creation automatically. You can customize the index by providing embedding dimensions and other settings during initialization:

```python
from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore

document_store = ElasticsearchDocumentStore(
    hosts="http://localhost:9200",
    index="documents",
    embedding_dim=768,  # Match your embedding model dimensions
    similarity="cosine"  # Or "dot_product", "l2_norm"
)
```

**Index Schema Design:**

The Haystack integration automatically creates an appropriate schema for:

- Document content (text)
- Embeddings (dense vectors)
- Metadata fields
- Timestamps

```json
{
  "mappings": {
    "properties": {
      "text": {
        "type": "text",
        "analyzer": "standard"
      },
      "embedding": {
        "type": "dense_vector",
        "dims": 768,
        "index": true,
        "similarity": "cosine"
      },
      "metadata": {
        "properties": {
          "source_file": {"type": "keyword"},
          "chunk_index": {"type": "integer"},
          "filename": {"type": "keyword"},
          "format": {"type": "keyword"},
          "title": {"type": "text"},
          "author": {"type": "keyword"},
          "created_date": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
          "page_count": {"type": "integer"}
        }
      },
      "indexed_at": {
        "type": "date"
      }
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index": {
      "knn": true
    }
  }
}
```

### 7.3 Document Indexing

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 4.3.1 | Create `src/retrieval/indexer.py` | 🔴 P0 | ✅ | Document indexing module |
| 4.3.2 | Implement single document indexing | 🔴 P0 | ✅ | Index one chunk |
| 4.3.3 | Implement bulk indexing | 🔴 P0 | ✅ | Batch multiple chunks |
| 4.3.4 | Add indexing progress tracking | 🟡 P1 | ✅ | Log progress |
| 4.3.5 | Implement error handling for index failures | 🔴 P0 | ✅ | Retry logic |
| 4.3.6 | Add document update capability | 🟢 P2 | ✅ | Update existing docs |
| 4.3.7 | Create integration tests with real ES | 🟡 P1 | ✅ | Test indexing |

**File Structure:**

```python
# src/retrieval/indexer.py
"""Document indexing using Haystack ElasticsearchDocumentStore."""
from typing import List, Dict
from datetime import datetime
from haystack import Document
from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore
from src.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Indexes documents using Haystack Elasticsearch integration."""

    def __init__(self, document_store: ElasticsearchDocumentStore):
        """Initialize indexer with Haystack document store."""
        self.document_store = document_store

    def index_chunk(self, chunk_data: dict) -> bool:
        """
        Index a single chunk using Haystack Document.

        Args:
            chunk_data: Dict with text, embedding, metadata

        Returns:
            True if successful
        """
        try:
            # Create Haystack Document
            doc = Document(
                content=chunk_data["text"],
                embedding=chunk_data["embedding"],
                meta={
                    **chunk_data["metadata"],
                    "indexed_at": datetime.utcnow().isoformat()
                }
            )

            # Write to document store
            self.document_store.write_documents([doc])

            return True

        except Exception as e:
            logger.error(f"Failed to index chunk: {e}")
            return False

    def bulk_index(self, chunks: List[dict]) -> tuple[int, int]:
        """
        Bulk index multiple chunks using Haystack.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Tuple of (successful_count, failed_count)
        """
        documents = []
        for chunk in chunks:
            doc = Document(
                content=chunk["text"],
                embedding=chunk["embedding"],
                meta={
                    **chunk["metadata"],
                    "indexed_at": datetime.utcnow().isoformat()
                }
            )
            documents.append(doc)

        try:
            # Bulk write using Haystack document store
            written_count = self.document_store.write_documents(documents)

            logger.info(f"Indexed {written_count} chunks")
            return written_count, len(chunks) - written_count

        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return 0, len(chunks)
```

### 7.4 Semantic Search Implementation

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 4.4.1 | Create `src/retrieval/searcher.py` | 🔴 P0 | ✅ | Search implementation |
| 4.4.2 | Implement vector similarity search | 🔴 P0 | ✅ | Use ElasticsearchEmbeddingRetriever |
| 4.4.3 | Implement keyword search (BM25) | 🟡 P1 | ✅ | Use ElasticsearchBM25Retriever |
| 4.4.4 | Implement hybrid search | 🟢 P2 | ✅ | Combine vector + keyword |
| 4.4.5 | Add result ranking and scoring | 🔴 P0 | ✅ | Sort by relevance |
| 4.4.6 | Implement configurable top-k | 🔴 P0 | ✅ | From settings |
| 4.4.7 | Add metadata filtering | 🟢 P2 | ✅ | Filter by source, etc. |
| 4.4.8 | Create unit and integration tests | 🟡 P1 | ✅ | Test search |

**Implementation Note:**

Haystack provides two retriever components for Elasticsearch:

- `ElasticsearchEmbeddingRetriever`: For vector/semantic search
- `ElasticsearchBM25Retriever`: For keyword-based search

**File Structure:**

```python
# src/retrieval/searcher.py
"""Semantic search using Haystack Elasticsearch retrievers."""
from typing import List, Dict, Optional
from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore
from haystack_integrations.components.retrievers.elasticsearch import ElasticsearchEmbeddingRetriever
from src.config.settings import get_settings
from src.ai_models.embedder import Embedder
import logging

logger = logging.getLogger(__name__)


class SemanticSearcher:
    """Performs semantic search using Haystack Elasticsearch integration."""

    def __init__(self, document_store: ElasticsearchDocumentStore):
        """Initialize searcher with document store."""
        settings = get_settings()
        self.document_store = document_store
        self.top_k = settings.retrieval.top_k
        self.threshold = settings.retrieval.similarity_threshold
        self.embedder = Embedder()

        # Initialize Haystack embedding retriever
        self.retriever = ElasticsearchEmbeddingRetriever(
            document_store=document_store
        )

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Perform semantic search using Haystack retriever.

        Args:
            query: Search query
            top_k: Number of results (default from config)
            filters: Optional metadata filters

        Returns:
            List of matching documents with scores
        """
        if top_k is None:
            top_k = self.top_k

        # Generate query embedding
        query_embedding = self.embedder.embed_text(query)

        try:
            # Use Haystack retriever
            result = self.retriever.run(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters
            )

            documents = result["documents"]

            # Format results
            results = []
            for doc in documents:
                if doc.score >= self.threshold:
                    results.append({
                        "text": doc.content,
                        "score": doc.score,
                        "metadata": doc.meta
                    })

            logger.info(f"Found {len(results)} results for query")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
```

### 7.5 Integration with Pipeline

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 4.5.1 | Update `IngestionPipeline` to use indexer | 🔴 P0 | ✅ | Auto-index after chunking |
| 4.5.2 | Add end-to-end integration test | 🟡 P1 | ✅ | Ingest → search |
| 4.5.3 | Implement index health monitoring | 🟡 P1 | ✅ | Check ES status |

### 7.6 Phase 4 Completion Checklist

- [x] Elasticsearch client configured
- [x] Index created with proper schema
- [x] Can index documents successfully
- [x] Semantic search working
- [x] Results ranked by relevance
- [x] Integration tests passing
- [x] Error handling comprehensive

**Phase 4 Exit Criteria:**

- ✅ Can index documents with embeddings
- ✅ Semantic search returns relevant results
- ✅ Top-k configuration works
- ✅ ES health checks passing
- ✅ All tests pass (138 passed, 1 skipped)
- ✅ Code coverage: 80% for Phase 4 modules
