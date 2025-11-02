"""API module for FastAPI endpoints."""

from src.api import documents, health, query

__all__ = ["health", "documents", "query"]
