"""
Simple runner utility for executing RAG agents with Google ADK.

This module provides a simplified interface for running stateless RAG agents
without requiring explicit session management.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable, Generator

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

logger = logging.getLogger(__name__)


class SimpleRAGRunner:
    """
    Simplified runner for stateless RAG agent queries.

    This runner handles the boilerplate of creating sessions and formatting
    messages for the Google ADK Runner, making it easy to execute queries
    against a RAG agent.

    Example:
        >>> agent, get_sources = create_rag_agent()
        >>> runner = SimpleRAGRunner(agent, get_sources)
        >>> answer, sources = runner.query("What is Python?")
        >>> print(answer)
        >>> print(f"Found {len(sources)} sources")
    """

    def __init__(
        self,
        agent: LlmAgent,
        get_sources_func: Callable[[], list[dict]] | None = None,
        app_name: str = "elastic_rag",
    ):
        """
        Initialize the runner with an agent.

        Args:
            agent: The LlmAgent to execute queries against
            get_sources_func: Optional function to retrieve sources after query
            app_name: Name of the application (required by ADK Runner)
        """
        self.agent = agent
        self.get_sources_func = get_sources_func
        self.app_name = app_name
        # Create in-memory session service (stateless)
        self.session_service = InMemorySessionService()
        # Create runner
        self.runner = Runner(app_name=app_name, agent=agent, session_service=self.session_service)
        logger.info(f"SimpleRAGRunner initialized for app: {app_name}")

    def query(
        self,
        question: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> tuple[str, list[dict]]:
        """
        Execute a query against the RAG agent.

        Args:
            question: The user's question
            user_id: Optional user ID (defaults to random UUID)
            session_id: Optional session ID (defaults to random UUID)

        Returns:
            Tuple of (answer, sources) where:
            - answer: The agent's response text
            - sources: List of source documents used (empty if no get_sources_func)

        Example:
            >>> answer, sources = runner.query("What is machine learning?")
            >>> print(f"Answer: {answer}")
            >>> print(f"Used {len(sources)} sources")
        """

        question = f"{question} /no_think"

        # Run async version in event loop
        return asyncio.run(self._query_async(question, user_id, session_id))

    async def _query_async(
        self,
        question: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> tuple[str, list[dict]]:
        """Async implementation of query.

        Returns:
            Tuple of (answer, sources) where sources is the list of documents
            retrieved during the query execution.
        """

        question = f"{question} /no_think"

        # Generate IDs if not provided (stateless mode)
        user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"

        # Create session if it doesn't exist
        try:
            await self.session_service.get_session(user_id=user_id, session_id=session_id)
        except Exception:
            # Session doesn't exist, create it
            await self.session_service.create_session(
                app_name=self.app_name, user_id=user_id, session_id=session_id
            )

        # Create message content
        message = types.Content(role="user", parts=[types.Part(text=question)])

        logger.info(f"Executing query: '{question}' (user={user_id}, session={session_id})")

        # Run the agent and collect response
        response_text = ""
        try:
            events = self.runner.run_async(
                user_id=user_id, session_id=session_id, new_message=message
            )

            # Process events to extract the response
            async for event in events:
                if hasattr(event, "content") and event.content:
                    # Extract text from content parts
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text

            # Get sources from the agent if available
            sources = []
            if self.get_sources_func:
                sources = self.get_sources_func()
                logger.info(f"Retrieved {len(sources)} sources from agent")

            logger.info(f"Query completed, response length: {len(response_text)} chars")
            return response_text.strip(), sources

        except Exception as e:
            logger.error(f"Error executing query: {e}", exc_info=True)
            raise

    def query_with_events(
        self,
        question: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> Generator[dict, None, None]:
        """
        Execute a query and yield detailed events.

        This method provides access to the raw event stream from the agent,
        allowing inspection of tool calls, intermediate results, etc.

        Args:
            question: The user's question
            user_id: Optional user ID (defaults to random UUID)
            session_id: Optional session ID (defaults to random UUID)

        Yields:
            Dictionary representations of events with type and data

        Example:
            >>> for event in runner.query_with_events("What is Python?"):
            ...     print(f"Event: {event['type']}")
            ...     if event['type'] == 'tool_call':
            ...         print(f"  Tool: {event['tool_name']}")
        """

        question = f"{question} /no_think"

        # Generate IDs if not provided
        user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"

        # Create session if it doesn't exist
        try:
            self.session_service.get_session(user_id=user_id, session_id=session_id)
        except Exception:
            # Session doesn't exist, create it
            self.session_service.create_session(
                app_name=self.app_name, user_id=user_id, session_id=session_id
            )

        # Create message content
        message = types.Content(role="user", parts=[types.Part(text=question)])

        logger.info(f"Executing query with events: '{question}'")

        try:
            events = self.runner.run(user_id=user_id, session_id=session_id, new_message=message)

            for event in events:
                # Convert event to dict for easier inspection
                event_dict = {
                    "type": type(event).__name__,
                    "event": event,
                }

                # Add specific data based on event type
                if hasattr(event, "content") and event.content:
                    event_dict["content"] = event.content
                    # Extract text if available
                    texts = []
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            texts.append(part.text)
                    if texts:
                        event_dict["text"] = "".join(texts)

                if hasattr(event, "function_call"):
                    event_dict["function_call"] = event.function_call

                yield event_dict

        except Exception as e:
            logger.error(f"Error in query_with_events: {e}", exc_info=True)
            raise

    def close(self):
        """Close the runner and cleanup resources."""
        if self.runner:
            # Runner.close() is async, but we can just delete the reference
            # since we're using InMemorySessionService which doesn't need cleanup
            self.runner = None
            logger.info("SimpleRAGRunner closed")
