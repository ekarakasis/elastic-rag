"""Retrieval module for Elasticsearch integration.

This module provides components for document indexing and retrieval using
Elasticsearch through Haystack integration.
"""

from src.retrieval.elasticsearch_client import ElasticsearchClient
from src.retrieval.index_manager import IndexManager
from src.retrieval.indexer import DocumentIndexer
from src.retrieval.searcher import SemanticSearcher

__all__ = [
    "ElasticsearchClient",
    "IndexManager",
    "DocumentIndexer",
    "SemanticSearcher",
]
