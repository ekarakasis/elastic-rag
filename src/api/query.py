"""Query endpoints for RAG agent interaction."""

import logging

from fastapi import APIRouter, HTTPException, status

from src.agent.rag_agent import create_rag_agent
from src.agent.runner import SimpleRAGRunner
from src.api.exceptions import CircuitBreakerOpenError, QueryProcessingError
from src.api.models import BatchQueryRequest, QueryRequest, QueryResponse
from src.resilience.circuit_breaker import CircuitBreakerError

logger = logging.getLogger(__name__)

# Create router with query prefix
router = APIRouter(prefix="/query", tags=["query"])


@router.post("/", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """Process a single user query using the RAG agent.

    This endpoint processes queries in a stateless manner - each query is
    independent with no conversation history or session state. The agent:
        1. Retrieves relevant context from Elasticsearch
        2. Generates an answer using the LLM
        3. Returns the answer with source citations

    The query processing is protected by a circuit breaker to prevent
    cascading failures when the LLM service is unavailable.

    Args:
        request: QueryRequest containing:
            - query: The user's question (1-500 characters)
            - top_k: Number of documents to retrieve (1-20, default 5)
            - context_override: Optional pre-fetched context

    Returns:
        QueryResponse with:
            - answer: Generated answer from the RAG agent
            - sources: List of source documents with metadata
            - query: The original query
            - metadata: Optional response metadata

    Raises:
        QueryProcessingError: If query processing fails
        CircuitBreakerOpenError: If LLM circuit breaker is open

    Example Request:
        ```json
        {
            "query": "What is machine learning?",
            "top_k": 5
        }
        ```

    Example Response:
        ```json
        {
            "answer": "Machine learning is a subset of artificial intelligence...",
            "sources": [
                {
                    "text": "Machine learning algorithms...",
                    "metadata": {
                        "source_file": "ml_intro.pdf",
                        "chunk_index": 0
                    }
                }
            ],
            "query": "What is machine learning?",
            "metadata": null
        }
        ```

    Example Usage:
        ```bash
        curl -X POST "http://localhost:8000/query/" \\
             -H "Content-Type: application/json" \\
             -d '{"query": "What is machine learning?", "top_k": 5}'
        ```
    """
    try:
        logger.info(f"Processing query: '{request.query[:50]}...'")

        # Create RAG agent (stateless) - returns agent and sources accessor
        agent, get_sources = create_rag_agent(top_k=request.top_k or 5)

        # Create runner for executing queries
        runner = SimpleRAGRunner(agent, get_sources)

        # Execute query (use async method directly to avoid event loop conflict)
        answer, sources = await runner._query_async(request.query)

        # Format sources for API response
        formatted_sources = []
        for source in sources:
            formatted_source = {
                "content": source.get("text", ""),
                "score": source.get("score", 0.0),
                "metadata": source.get("metadata", {}),
            }
            # Extract filename from metadata if available
            if "source_file" in source.get("metadata", {}):
                formatted_source["filename"] = source["metadata"]["source_file"]

            formatted_sources.append(formatted_source)

        response = QueryResponse(
            answer=answer,
            sources=formatted_sources,
            query=request.query,
            metadata={"top_k": request.top_k or 5, "sources_count": len(formatted_sources)},
        )

        logger.info(
            f"Query processed successfully: {len(answer)} chars, {len(formatted_sources)} sources"
        )
        return response

    except CircuitBreakerError as e:
        logger.error(f"Circuit breaker open for query: {request.query[:50]}")
        raise CircuitBreakerOpenError() from e

    except Exception as e:
        logger.error(f"Query processing failed: {e}", exc_info=True)
        raise QueryProcessingError(f"Failed to process query: {str(e)}") from e


@router.post("/batch", response_model=list[QueryResponse])
async def process_batch_queries(request: BatchQueryRequest) -> list[QueryResponse]:
    """Process multiple queries in a single request.

    Each query is processed independently in stateless mode with no
    shared context or conversation history. This is useful for:
        - Bulk question answering
        - Testing multiple queries
        - Parallel query processing

    Note: Queries are processed sequentially. For production use with
    many queries, consider implementing async parallel processing.

    Args:
        request: BatchQueryRequest containing:
            - queries: List of query strings (1-10 queries)
            - top_k: Number of documents to retrieve per query

    Returns:
        List of QueryResponse objects, one for each input query

    Raises:
        QueryProcessingError: If batch processing fails
        CircuitBreakerOpenError: If LLM circuit breaker is open

    Example Request:
        ```json
        {
            "queries": [
                "What is machine learning?",
                "What is deep learning?",
                "What is neural networks?"
            ],
            "top_k": 5
        }
        ```

    Example Response:
        ```json
        [
            {
                "answer": "Machine learning is...",
                "sources": [...],
                "query": "What is machine learning?",
                "metadata": {"top_k": 5}
            },
            {
                "answer": "Deep learning is...",
                "sources": [...],
                "query": "What is deep learning?",
                "metadata": {"top_k": 5}
            },
            {
                "answer": "Neural networks are...",
                "sources": [...],
                "query": "What is neural networks?",
                "metadata": {"top_k": 5}
            }
        ]
        ```

    Example Usage:
        ```bash
        curl -X POST "http://localhost:8000/query/batch" \\
             -H "Content-Type: application/json" \\
             -d '{
                "queries": ["What is ML?", "What is AI?"],
                "top_k": 5
             }'
        ```
    """
    if not request.queries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No queries provided",
        )

    logger.info(f"Processing batch of {len(request.queries)} queries")

    responses: list[QueryResponse] = []

    for query in request.queries:
        try:
            # Create individual query request
            query_request = QueryRequest(
                query=query,
                top_k=request.top_k,
                context_override=None,
            )

            # Process query
            response = await process_query(query_request)
            responses.append(response)

        except Exception as e:
            logger.warning(f"Failed to process query in batch '{query[:50]}': {e}")
            # Add error response
            responses.append(
                QueryResponse(
                    answer=f"Error: {str(e)}",
                    sources=[],
                    query=query,
                    metadata={"error": str(e)},
                )
            )

    logger.info(f"Batch processing complete: {len(responses)} responses")
    return responses
