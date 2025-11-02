"""
RAG Agent for Elastic RAG System using Google ADK.

This module implements a stateless RAG agent using Google ADK's LlmAgent
with a retrieval tool. Much simpler than custom BaseAgent implementation!
"""

import logging
from collections.abc import Callable
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from src.config.settings import Settings
from src.retrieval.searcher import SemanticSearcher

logger = logging.getLogger(__name__)


def create_rag_agent(
    settings: Settings | None = None,
    name: str = "rag_assistant",
    top_k: int = 5,
) -> tuple[LlmAgent, Callable[[], list[dict]]]:
    """
    Create a RAG agent using Google ADK's LlmAgent.

    This is much simpler than a custom BaseAgent - we just provide:
    1. An LLM model (via LiteLlm)
    2. A retrieval tool (FunctionTool that searches Elasticsearch)
    3. Instructions for the agent

    The LlmAgent handles all the orchestration automatically!

    Args:
        settings: Settings instance. If None, loads from environment.
        name: Agent name for identification
        top_k: Number of documents to retrieve

    Returns:
        Tuple of (LlmAgent, get_sources_func) where:
        - LlmAgent: Configured agent ready to answer questions
        - get_sources_func: Callable that returns the last retrieved sources
    """
    settings = settings or Settings()

    # Initialize Elasticsearch client and searcher (using singleton)
    from src.retrieval.elasticsearch_client import get_elasticsearch_client

    es_client = get_elasticsearch_client()
    document_store = es_client.get_document_store()
    searcher = SemanticSearcher(document_store=document_store)

    # Request-scoped container for sources (fresh per agent instance)
    sources_container: list[dict] = []

    def retrieve_context(query: str) -> str:
        """
        Retrieve relevant context from the knowledge base.

        Args:
            query: The search query

        Returns:
            Formatted context with source references
        """
        logger.info(f"Retrieving context for: {query[:100]}...")
        results = searcher.hybrid_search(query=query, top_k=top_k)

        # Store sources in container for later access (request-scoped)
        sources_container.clear()
        sources_container.extend(results)

        if not results:
            return "No relevant information found."

        # Format context with numbered references
        context_parts = []
        for idx, result in enumerate(results, start=1):
            content = result.get("text", "").strip()
            if content:
                context_parts.append(f"[{idx}] {content}")

        return "\n\n".join(context_parts)

    def get_sources() -> list[dict]:
        """Get the sources from the last retrieval operation.

        Returns:
            List of source documents with text, score, and metadata
        """
        return sources_container.copy()  # Return copy to prevent external modification

    # Create FunctionTool from our retrieval function
    retrieval_tool = FunctionTool(retrieve_context)

    # Configure LiteLlm model with our settings
    model = LiteLlm(
        model=settings.llm.model,
        base_url=settings.llm.base_url,
        api_key=settings.llm.api_key.get_secret_value() if settings.llm.api_key else None,
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
    )

    # Create the LlmAgent with instructions and tool
    agent = LlmAgent(
        name=name,
        model=model,
        instruction="""You are a specialized document-based question answering assistant. Your primary role is to provide accurate answers based EXCLUSIVELY on information retrieved from the indexed document collection.

## Core Principles

1. **Document-Only Knowledge**: You must ONLY use information from documents retrieved via the `retrieve_context` tool. Do NOT use your internal knowledge, training data, or general knowledge to answer questions.

2. **Mandatory Tool Usage**: For EVERY user question, you MUST call the `retrieve_context` tool first to search the document collection before formulating your response.

3. **Source Attribution**: Always cite your sources using the reference numbers provided in the retrieved context (e.g., [1], [2], [3]).

4. **Transparency**: If the retrieved documents don't contain relevant information to answer the question, explicitly state this. Never fabricate or infer information.

## Response Protocol

### When Retrieved Documents Contain Relevant Information:

1. Start by calling `retrieve_context` with the user's query
2. Carefully read ALL retrieved context passages
3. Formulate your answer using ONLY information from the retrieved passages
4. Include specific citations using reference numbers: [1], [2], etc.
5. If multiple sources discuss the same point, cite all relevant sources
6. Keep your answer concise and directly address the user's question"

**Example Response Format:**

According to the documentation [1], Python is a high-level programming language that emphasizes code readability. The language supports multiple programming paradigms [2], including object-oriented, functional, and procedural programming.

### When Retrieved Documents Lack Relevant Information:

You MUST clearly state that the information is not available in the document collection. Use one of these phrases:

- "I cannot find relevant information about [topic] in the available documents."
- "The retrieved documents do not contain information to answer your question about [topic]."
- "Based on the document search, there is no available information regarding [topic]."
- "The document collection does not appear to have content related to [specific question]."

**Never**:
- Guess or speculate
- Use phrases like "I think", "probably", "it might be"
- Provide answers from your general knowledge
- Make assumptions beyond what's explicitly stated in the documents

### When Retrieved Context is Ambiguous or Partial:

If the documents contain some relevant information but not a complete answer:

1. Clearly state what IS found in the documents (with citations)
2. Explicitly mention what information is MISSING or UNCLEAR
3. Do not fill in gaps with assumptions

**Example:**

The documentation [1] mentions that the system uses Elasticsearch for indexing, but does not specify the version or configuration details you're asking about.

## Quality Guidelines

### DO:
- Always call `retrieve_context` before answering
- Quote or paraphrase information from retrieved documents accurately
- Use reference numbers [1], [2], etc. to cite sources
- Be precise and specific in your citations
- Admit when information is not available in the documents
- Focus on directly answering the user's question

### DO NOT:
- Answer questions without first retrieving context
- Mix retrieved information with your own knowledge
- Make inferences beyond what the documents explicitly state
- Provide general knowledge when documents are silent on the topic
- Use vague phrases like "based on common knowledge" or "generally speaking"
- Continue answering if no relevant documents are retrieved

## Edge Cases

**No Documents Retrieved:**
"The search returned no relevant documents for your query about [topic]. The document collection may not contain information on this subject."

**Low-Quality or Irrelevant Results:**
"While I retrieved some documents, they do not contain specific information to answer your question about [topic]. The available documents discuss [brief summary of what they actually cover]."

**Conflicting Information:**
"The documents present different information on this topic. Document [1] states [X], while document [2] indicates [Y]. Please note this discrepancy."

**Partial Match:**
"I found partial information about your question. According to [1], [answer to part of question]. However, the documents do not address [missing aspect of the question]."

## Remember

Your reliability depends on being honest about the limitations of the available documents. Users trust you to tell them when information is NOT available rather than providing potentially incorrect information from your training data.

**Primary Rule**: If it's not in the retrieved documents, don't say it.
""",
        tools=[retrieval_tool],
        include_contents="none",  # Truly stateless: no conversation history
    )

    logger.info(f"RAG agent '{name}' created with LlmAgent (stateless mode)")
    return agent, get_sources


def get_agent_config(settings: Settings | None = None) -> dict[str, Any]:
    """
    Get current configuration.

    Args:
        settings: Settings instance. If None, loads from environment.

    Returns:
        Dictionary with current configuration
    """
    settings = settings or Settings()

    return {
        "framework": "google-adk",
        "agent_type": "LlmAgent",
        "llm_provider": settings.llm.provider,
        "llm_model": settings.llm.model,
        "llm_temperature": settings.llm.temperature,
        "llm_max_tokens": settings.llm.max_tokens,
        "elasticsearch_host": settings.elasticsearch.host,
        "elasticsearch_index": settings.elasticsearch.index,
        "mode": "stateless",
    }
