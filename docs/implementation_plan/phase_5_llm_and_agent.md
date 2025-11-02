# 8. Phase 5: LLM & Agent Implementation

**Goal:** Implement stateless agent using Google ADK and LiteLLM for answer generation.

**Duration:** 5-7 days
**Status:** ✅ COMPLETED (December 2024)
**Dependencies:** Phase 2, Phase 4

### 8.1 LiteLLM Integration

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 5.1.1 | Research LiteLLM API for LMStudio | 🔴 P0 | ✅ | Provider-agnostic approach adopted |
| 5.1.2 | Create `src/ai_models/litellm_interface.py` | 🔴 P0 | ✅ | 273 lines, 88% coverage |
| 5.1.3 | Implement chat completion method | 🔴 P0 | ✅ | chat_completion() with error handling |
| 5.1.4 | Add streaming support (optional) | 🟢 P2 | ⬜ | Deferred - not required for MVP |
| 5.1.5 | Implement error handling and retries | 🔴 P0 | ✅ | Comprehensive error handling added |
| 5.1.6 | Add timeout configuration | 🔴 P0 | ✅ | Default 30s timeout in settings |
| 5.1.7 | Create unit tests with mocked responses | 🟡 P1 | ✅ | 33 tests passing, 88% coverage |

**File Structure:**

```python
# src/ai_models/litellm_interface.py
"""LLM interface using LiteLLM."""
from typing import List, Dict, Optional
import litellm
from src.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)


class LLMInterface:
    """Interface to LLM via LiteLLM."""

    def __init__(self):
        """Initialize LLM interface."""
        settings = get_settings()
        self.base_url = settings.lmstudio.base_url
        self.model = settings.lmstudio.chat_model
        self.timeout = settings.lmstudio.timeout

        # Configure LiteLLM
        litellm.api_base = self.base_url

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate chat completion.

        Args:
            messages: List of message dicts with role and content
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            Generated response text

        Raises:
            RuntimeError: If generation fails
        """
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_base=self.base_url,
                timeout=self.timeout
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise RuntimeError(f"LLM generation failed: {e}")

    def generate_answer(
        self,
        query: str,
        context: List[str],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate answer based on query and context.

        Args:
            query: User query
            context: List of context chunks
            system_prompt: Optional system instructions

        Returns:
            Generated answer
        """
        # Build context string
        context_str = "\n\n".join([
            f"[{i+1}] {chunk}"
            for i, chunk in enumerate(context)
        ])

        # Build messages
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        else:
            messages.append({
                "role": "system",
                "content": (
                    "You are a helpful assistant that answers questions "
                    "based on the provided context. Always cite your sources "
                    "using the reference numbers [1], [2], etc."
                )
            })

        messages.append({
            "role": "user",
            "content": f"Context:\n{context_str}\n\nQuestion: {query}\n\nAnswer:"
        })

        return self.chat_completion(messages)
```

### 8.2 Google ADK Agent Implementation

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 5.2.1 | Research Google ADK fundamentals | 🔴 P0 | ✅ | LlmAgent, FunctionTool, Runner researched |
| 5.2.2 | Create `src/agent/rag_agent.py` | 🔴 P0 | ✅ | Simplified to 136 lines using LlmAgent |
| 5.2.3 | Design stateless agent architecture | 🔴 P0 | ✅ | include_contents='none' for true statelessness |
| 5.2.4 | Implement query processing workflow | 🔴 P0 | ✅ | Tool-based retrieval with FunctionTool |
| 5.2.5 | Integrate retrieval component | 🔴 P0 | ✅ | retrieve_context() tool function |
| 5.2.6 | Integrate LLM interface | 🔴 P0 | ✅ | LiteLlm backend with ADK |
| 5.2.7 | Implement source citation in answers | 🔴 P0 | ✅ | Citations via system prompt |
| 5.2.8 | Add prompt engineering | 🟡 P1 | ✅ | Optimized for RAG with citations |
| 5.2.9 | Create unit tests for agent | 🟡 P1 | ✅ | 15 tests, 100% coverage on agent module |

**File Structure:**

```python
# src/agent/adk_agent.py
"""Stateless RAG agent using Google ADK."""
from typing import Dict, List, Optional
from dataclasses import dataclass
# Import Google ADK components (adjust based on actual API)
# from google_adk import Agent, Tool
from src.retrieval.searcher import SemanticSearcher
from src.ai_models.litellm_interface import LLMInterface
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Agent response with answer and sources."""
    answer: str
    sources: List[Dict]
    query: str


class RAGAgent:
    """Stateless RAG agent - no conversation memory."""

    def __init__(self):
        """Initialize agent components."""
        self.searcher = SemanticSearcher()
        self.llm = LLMInterface()

        # System prompt for the agent
        self.system_prompt = """You are a helpful AI assistant that answers questions
based strictly on the provided context. Your responses should:
1. Be accurate and based only on the given information
2. Cite sources using reference numbers [1], [2], etc.
3. Admit when you don't have enough information
4. Be clear and concise
"""

    def process_query(
        self,
        query: str,
        context_override: Optional[List[str]] = None,
        top_k: Optional[int] = None
    ) -> AgentResponse:
        """
        Process a user query (stateless operation).

        This method is completely stateless - each query is processed
        independently without any memory of previous queries.

        Args:
            query: User question
            context_override: Optional pre-fetched context (for testing)
            top_k: Number of chunks to retrieve

        Returns:
            AgentResponse with answer and sources
        """
        logger.info(f"Processing query: {query}")

        # Step 1: Retrieve relevant context (unless overridden)
        if context_override is None:
            search_results = self.searcher.search(query, top_k=top_k)
            context_chunks = [r["text"] for r in search_results]
            sources = [r["metadata"] for r in search_results]
        else:
            context_chunks = context_override
            sources = []

        if not context_chunks:
            return AgentResponse(
                answer="I don't have enough information to answer this question.",
                sources=[],
                query=query
            )

        logger.debug(f"Retrieved {len(context_chunks)} context chunks")

        # Step 2: Generate answer using LLM
        answer = self.llm.generate_answer(
            query=query,
            context=context_chunks,
            system_prompt=self.system_prompt
        )

        logger.info("Answer generated successfully")

        return AgentResponse(
            answer=answer,
            sources=sources,
            query=query
        )

    def process_batch(self, queries: List[str]) -> List[AgentResponse]:
        """
        Process multiple queries independently (all stateless).

        Args:
            queries: List of queries to process

        Returns:
            List of AgentResponse objects
        """
        return [self.process_query(q) for q in queries]
```

### 8.3 Agent Testing

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 5.3.1 | Create test queries dataset | 🟡 P1 | ✅ | Sample queries in demo_phase5.py |
| 5.3.2 | Test agent with real LMStudio | 🔴 P0 | ✅ | demos/demo_phase5.py fully functional |
| 5.3.3 | Verify stateless behavior | 🔴 P0 | ✅ | Confirmed via include_contents='none' |
| 5.3.4 | Test source citation quality | 🟡 P1 | ✅ | Citations working correctly |
| 5.3.5 | Test error handling | 🔴 P0 | ✅ | Comprehensive error handling verified |

### 8.4 Additional Implementations

| Task ID | Task | Priority | Status | Notes |
|---------|------|----------|--------|-------|
| 5.4.1 | Create async runner for agent | 🔴 P0 | ✅ | src/agent/runner.py (SimpleRAGRunner) |
| 5.4.2 | Add LLMSettings configuration | 🔴 P0 | ✅ | Provider-agnostic config with validation |
| 5.4.3 | Create real integration demo | 🔴 P0 | ✅ | demos/demo_phase5.py (324 lines) |

### 8.5 Phase 5 Completion Checklist

- [x] LiteLLM interface working with LMStudio
- [x] Agent can process queries end-to-end
- [x] Stateless architecture verified (include_contents='none')
- [x] Source citations included in responses
- [x] Error handling comprehensive
- [x] Tests passing (187 total, 95% coverage)
- [x] Real integration demo created and working
- [x] Async runner implemented

**Phase 5 Exit Criteria:**

- ✅ Can generate answers from queries
- ✅ Answers based on retrieved context
- ✅ Sources properly cited
- ✅ No conversation memory maintained (true statelessness)
- ✅ All tests pass (95% overall coverage)

**Key Achievements:**

- **Simplified Architecture**: Reduced from 260 lines (custom BaseAgent) to 136 lines using Google ADK's LlmAgent
- **True Statelessness**: Discovered and implemented `include_contents='none'` parameter for zero conversation history
- **Provider-Agnostic**: LiteLLM supports OpenAI, Anthropic, LMStudio, and more
- **Comprehensive Testing**: 88% coverage on LiteLLM interface, 100% on agent module
- **Real Integration**: Full demo with actual Elasticsearch and LMStudio (no mocking)
