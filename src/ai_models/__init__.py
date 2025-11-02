"""AI model integration module for embeddings and language models.

This module provides a unified interface for various AI models used in the RAG system:
- Text embedding models (e.g., BGE-M3) for semantic search
- Large Language Models (LLMs) for text generation and chat
- Integration with multiple providers via LiteLLM and LMStudio

All model interactions are abstracted to support easy switching between providers
while maintaining consistent interfaces throughout the application.
"""
