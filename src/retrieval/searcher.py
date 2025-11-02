"""Semantic search using Haystack Elasticsearch retrievers.

This module provides multiple search modes:
- Vector similarity search (semantic)
- BM25 keyword search
- Hybrid search (combining vector and keyword)
- Metadata filtering across all search modes
"""

import logging

from haystack_integrations.components.retrievers.elasticsearch import (
    ElasticsearchBM25Retriever,
    ElasticsearchEmbeddingRetriever,
)
from haystack_integrations.document_stores.elasticsearch import (
    ElasticsearchDocumentStore,
)

from src.ai_models.embedder import Embedder
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class SemanticSearcher:
    """Performs search using Haystack Elasticsearch integration.

    Supports multiple search modes:
    - Semantic search using vector embeddings (P0)
    - Keyword search using BM25 (P1)
    - Hybrid search combining both (P2)
    - Metadata filtering (P2)
    """

    def __init__(self, document_store: ElasticsearchDocumentStore):
        """Initialize searcher with document store.

        Args:
            document_store: Haystack ElasticsearchDocumentStore instance
        """
        settings = get_settings()
        self.document_store = document_store
        self.top_k = settings.retrieval.top_k
        self.threshold = settings.retrieval.similarity_threshold
        self.embedder = Embedder()

        # Initialize Haystack embedding retriever for vector search (P0)
        self.embedding_retriever = ElasticsearchEmbeddingRetriever(document_store=document_store)

        # Initialize BM25 retriever for keyword search (P1)
        self.bm25_retriever = ElasticsearchBM25Retriever(document_store=document_store)

        logger.info(
            f"SemanticSearcher initialized (top_k={self.top_k}, threshold={self.threshold})"
        )

    def _normalize_filters(self, filters: dict | None) -> dict | None:
        """Normalize filters to Haystack format.

        Converts simple dict filters like {"field": "value"} to Haystack format:
        {"field": "meta.field", "operator": "==", "value": "value"}

        Args:
            filters: Simple filter dict or Haystack-formatted filters

        Returns:
            Haystack-formatted filters or None
        """
        if not filters:
            return None

        # Check if already in Haystack format (has "operator" key)
        if "operator" in filters:
            return filters

        # Convert simple dict to Haystack format
        conditions = []
        for field, value in filters.items():
            conditions.append({"field": f"meta.{field}", "operator": "==", "value": value})

        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"operator": "AND", "conditions": conditions}

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict | None = None,
    ) -> list[dict]:
        """Perform vector similarity search using embeddings.

        This is the primary semantic search method using vector embeddings
        for finding semantically similar documents.

        Args:
            query: Search query text
            top_k: Number of results to return (default from config)
            filters: Optional metadata filters (P2), e.g. {"source_file": "doc.pdf"}

        Returns:
            list[dict]: List of results with structure:
                {
                    "text": str,         # Document text
                    "score": float,      # Similarity score
                    "metadata": dict     # Document metadata
                }

        Example:
            >>> searcher = SemanticSearcher(document_store)
            >>> results = searcher.search("What is machine learning?", top_k=5)
            >>> for result in results:
            ...     print(f"Score: {result['score']:.4f}, Text: {result['text'][:50]}")
        """
        if top_k is None:
            top_k = self.top_k

        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []

        try:
            logger.info(f"Vector search: '{query[:50]}...' (top_k={top_k})")

            # Generate query embedding
            query_embedding = self.embedder.embed_text(query)
            logger.debug(f"Generated query embedding (dim={len(query_embedding)})")

            # Normalize filters to Haystack format
            normalized_filters = self._normalize_filters(filters)

            # Use Haystack embedding retriever
            result = self.embedding_retriever.run(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=normalized_filters,
            )

            documents = result.get("documents", [])

            # Filter by threshold and format results
            results = []
            for doc in documents:
                if doc.score >= self.threshold:
                    results.append(
                        {
                            "text": doc.content,
                            "score": doc.score,
                            "metadata": doc.meta,
                        }
                    )

            logger.info(f"Found {len(results)} results above threshold {self.threshold}")

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def keyword_search(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict | None = None,
    ) -> list[dict]:
        """Perform BM25 keyword search.

        Uses Elasticsearch's BM25 algorithm for traditional keyword-based search.
        Good for exact term matching and specific terminology.

        Args:
            query: Search query text
            top_k: Number of results to return (default from config)
            filters: Optional metadata filters (P2)

        Returns:
            list[dict]: List of results (same structure as search())

        Example:
            >>> searcher = SemanticSearcher(document_store)
            >>> results = searcher.keyword_search("neural network layers", top_k=5)
        """
        if top_k is None:
            top_k = self.top_k

        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []

        try:
            logger.info(f"BM25 keyword search: '{query[:50]}...' (top_k={top_k})")

            # Normalize filters to Haystack format
            normalized_filters = self._normalize_filters(filters)

            # Use Haystack BM25 retriever
            result = self.bm25_retriever.run(
                query=query,
                top_k=top_k,
                filters=normalized_filters,
            )

            documents = result.get("documents", [])

            # Format results (BM25 returns documents with scores)
            results = self._format_results(documents)

            logger.info(f"Found {len(results)} BM25 results")

            return results

        except Exception as e:
            logger.error(f"BM25 keyword search failed: {e}")
            return []

    def hybrid_search(
        self,
        query: str,
        top_k: int | None = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filters: dict | None = None,
    ) -> list[dict]:
        """Combine vector and keyword search for hybrid results.

        Retrieves results from both semantic (vector) and keyword (BM25) search,
        then combines them with configurable weights for final ranking.

        Args:
            query: Search query text
            top_k: Number of final results (default from config)
            vector_weight: Weight for vector search scores (0-1)
            keyword_weight: Weight for keyword search scores (0-1)
            filters: Optional metadata filters (P2)

        Returns:
            list[dict]: Combined and re-ranked results

        Example:
            >>> searcher = SemanticSearcher(document_store)
            >>> results = searcher.hybrid_search(
            ...     "machine learning",
            ...     vector_weight=0.6,
            ...     keyword_weight=0.4
            ... )
        """
        if top_k is None:
            top_k = self.top_k

        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []

        try:
            logger.info(
                f"Hybrid search: '{query[:50]}...' "
                f"(v_weight={vector_weight}, k_weight={keyword_weight})"
            )

            # Get results from both retrievers (fetch more for better coverage)
            fetch_k = top_k * 2

            vector_results = self.search(query, top_k=fetch_k, filters=filters)
            keyword_results = self.keyword_search(query, top_k=fetch_k, filters=filters)

            # Combine and re-rank
            combined = self._combine_results(
                vector_results,
                keyword_results,
                vector_weight,
                keyword_weight,
            )

            # Return top-k from combined results
            final_results = combined[:top_k]

            logger.info(
                f"Hybrid search combined {len(vector_results)} vector + "
                f"{len(keyword_results)} keyword → {len(final_results)} final results"
            )

            return final_results

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

    def search_with_filters(
        self,
        query: str,
        top_k: int | None = None,
        source_file: str | None = None,
        format_type: str | None = None,
        custom_filters: dict | None = None,
    ) -> list[dict]:
        """Convenience method for filtered search with common metadata fields.

        Args:
            query: Search query text
            top_k: Number of results
            source_file: Filter by source filename
            format_type: Filter by document format (pdf, docx, etc.)
            custom_filters: Additional custom filters

        Returns:
            list[dict]: Filtered search results

        Example:
            >>> searcher = SemanticSearcher(document_store)
            >>> results = searcher.search_with_filters(
            ...     "machine learning",
            ...     source_file="ml_book.pdf",
            ...     format_type="pdf"
            ... )
        """
        # Build filters in Haystack format
        # Haystack requires: {"field": "field_name", "operator": "==", "value": "value"}
        # For multiple filters, use: {"operator": "AND", "conditions": [...]}
        conditions = []

        if source_file:
            conditions.append({"field": "meta.source_file", "operator": "==", "value": source_file})

        if format_type:
            conditions.append({"field": "meta.format", "operator": "==", "value": format_type})

        if not conditions:
            filters = None
        elif len(conditions) == 1:
            filters = conditions[0]
        else:
            filters = {"operator": "AND", "conditions": conditions}

        logger.info(f"Filtered search with filters: {filters}")

        return self.search(query, top_k=top_k, filters=filters)

    def _format_results(self, documents) -> list[dict]:
        """Format Haystack documents to standardized dict format.

        Args:
            documents: List of Haystack Document objects

        Returns:
            list[dict]: Formatted results
        """
        results = []
        for doc in documents:
            results.append(
                {
                    "text": doc.content,
                    "score": doc.score if hasattr(doc, "score") and doc.score else 1.0,
                    "metadata": doc.meta,
                }
            )
        return results

    def _combine_results(
        self,
        vector_results: list[dict],
        keyword_results: list[dict],
        vector_weight: float,
        keyword_weight: float,
    ) -> list[dict]:
        """Combine and re-rank results from vector and keyword search.

        Uses a weighted scoring approach to merge results from both search modes.
        Handles duplicate documents by combining their scores.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            vector_weight: Weight for vector scores
            keyword_weight: Weight for keyword scores

        Returns:
            list[dict]: Combined and sorted results
        """
        # Create a dictionary to track combined scores
        # Key: document text (as unique identifier)
        combined_scores = {}

        # Normalize weights
        total_weight = vector_weight + keyword_weight
        v_norm = vector_weight / total_weight
        k_norm = keyword_weight / total_weight

        # Process vector results
        for result in vector_results:
            text = result["text"]
            score = result["score"] * v_norm
            combined_scores[text] = {
                "score": score,
                "text": text,
                "metadata": result["metadata"],
                "sources": ["vector"],
            }

        # Process keyword results
        for result in keyword_results:
            text = result["text"]
            score = result["score"] * k_norm

            if text in combined_scores:
                # Document appears in both - combine scores
                combined_scores[text]["score"] += score
                combined_scores[text]["sources"].append("keyword")
            else:
                # New document from keyword search
                combined_scores[text] = {
                    "score": score,
                    "text": text,
                    "metadata": result["metadata"],
                    "sources": ["keyword"],
                }

        # Convert to list and sort by combined score
        combined = list(combined_scores.values())
        combined.sort(key=lambda x: x["score"], reverse=True)

        # Remove 'sources' field for clean output
        for result in combined:
            result.pop("sources", None)

        return combined

    def get_search_stats(self) -> dict:
        """Get search statistics and configuration.

        Returns:
            dict: Current search configuration
        """
        return {
            "top_k": self.top_k,
            "similarity_threshold": self.threshold,
            "embedding_dim": 768,
            "retrievers": ["embedding", "bm25"],
            "supports_hybrid": True,
            "supports_filtering": True,
        }
