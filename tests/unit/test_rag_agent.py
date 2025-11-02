"""
Unit tests for RAG Agent using Google ADK.

Tests the create_rag_agent factory function and retrieval tool integration.
"""

from unittest.mock import Mock, patch

import pytest

from src.agent.rag_agent import create_rag_agent, get_agent_config


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock()
    # Mock LLM settings
    settings.llm = Mock()
    settings.llm.provider = "lmstudio"
    settings.llm.model = "test-model"
    settings.llm.base_url = "http://localhost:1234/v1"
    settings.llm.api_key = Mock()
    settings.llm.api_key.get_secret_value.return_value = "test-key"
    settings.llm.temperature = 0.7
    settings.llm.max_tokens = 15000
    # Mock Elasticsearch settings
    settings.elasticsearch = Mock()
    settings.elasticsearch.host = "http://localhost:9200"
    settings.elasticsearch.index = "test-index"
    return settings


@pytest.fixture
def mock_searcher():
    """Create mock searcher."""
    with patch("src.agent.rag_agent.SemanticSearcher") as mock:
        searcher_instance = Mock()
        mock.return_value = searcher_instance
        yield searcher_instance


@pytest.fixture
def mock_llm_agent():
    """Create mock LlmAgent class."""
    with patch("src.agent.rag_agent.LlmAgent") as mock:
        agent_instance = Mock()
        mock.return_value = agent_instance
        yield mock


@pytest.fixture
def mock_lite_llm():
    """Create mock LiteLlm class."""
    with patch("src.agent.rag_agent.LiteLlm") as mock:
        model_instance = Mock()
        mock.return_value = model_instance
        yield mock


@pytest.fixture
def mock_function_tool():
    """Create mock FunctionTool class."""
    with patch("src.agent.rag_agent.FunctionTool") as mock:
        tool_instance = Mock()
        mock.return_value = tool_instance
        yield mock


class TestCreateRagAgent:
    """Tests for create_rag_agent function."""

    def test_creates_agent_with_default_settings(
        self, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test agent creation with default settings."""
        with patch("src.agent.rag_agent.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings.llm.model = "test-model"
            mock_settings.llm.base_url = "http://localhost:1234/v1"
            mock_settings.llm.api_key = None
            mock_settings.llm.temperature = 0.7
            mock_settings.llm.max_tokens = 15000
            mock_settings_class.return_value = mock_settings

            agent, get_sources = create_rag_agent()

            # Verify Settings was instantiated
            mock_settings_class.assert_called_once()

            # Verify LlmAgent was created
            mock_llm_agent.assert_called_once()
            assert agent == mock_llm_agent.return_value
            assert callable(get_sources)

    def test_creates_agent_with_custom_settings(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test agent creation with custom settings."""
        agent, get_sources = create_rag_agent(settings=mock_settings, name="custom_agent", top_k=10)

        # Verify LlmAgent was created with correct name
        call_kwargs = mock_llm_agent.call_args[1]
        assert call_kwargs["name"] == "custom_agent"

        # Verify agent instance and get_sources function returned
        assert agent == mock_llm_agent.return_value
        assert callable(get_sources)

    def test_configures_lite_llm_model(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test LiteLlm model is configured correctly."""
        agent, get_sources = create_rag_agent(settings=mock_settings)

        # Verify LiteLlm was instantiated with correct parameters
        mock_lite_llm.assert_called_once_with(
            model=mock_settings.llm.model,
            base_url=mock_settings.llm.base_url,
            api_key="test-key",
            temperature=mock_settings.llm.temperature,
            max_tokens=mock_settings.llm.max_tokens,
        )

    def test_configures_lite_llm_without_api_key(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test LiteLlm configuration when api_key is None."""
        mock_settings.llm.api_key = None

        agent, get_sources = create_rag_agent(settings=mock_settings)

        # Verify LiteLlm was called with api_key=None
        call_kwargs = mock_lite_llm.call_args[1]
        assert call_kwargs["api_key"] is None

    def test_creates_retrieval_tool(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test FunctionTool is created from retrieval function."""
        agent, get_sources = create_rag_agent(settings=mock_settings)

        # Verify FunctionTool constructor was called
        mock_function_tool.assert_called_once()

        # Get the function that was passed
        retrieval_func = mock_function_tool.call_args[0][0]
        assert callable(retrieval_func)
        assert retrieval_func.__name__ == "retrieve_context"

    def test_llm_agent_receives_tool(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test LlmAgent is created with the retrieval tool."""
        agent, get_sources = create_rag_agent(settings=mock_settings)

        # Verify LlmAgent was called with tools list
        call_kwargs = mock_llm_agent.call_args[1]
        assert "tools" in call_kwargs
        assert len(call_kwargs["tools"]) == 1
        assert call_kwargs["tools"][0] == mock_function_tool.return_value

    def test_llm_agent_receives_instruction(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test LlmAgent is created with proper instructions."""
        agent, get_sources = create_rag_agent(settings=mock_settings)

        # Verify LlmAgent was called with instruction
        call_kwargs = mock_llm_agent.call_args[1]
        assert "instruction" in call_kwargs
        instruction = call_kwargs["instruction"]

        # Check instruction contains key guidance
        assert "retrieve_context" in instruction
        assert "cite sources" in instruction.lower()
        assert "reference numbers" in instruction.lower()

    def test_llm_agent_receives_model(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test LlmAgent is created with the LiteLlm model."""
        agent, get_sources = create_rag_agent(settings=mock_settings)

        # Verify LlmAgent was called with model
        call_kwargs = mock_llm_agent.call_args[1]
        assert "model" in call_kwargs
        assert call_kwargs["model"] == mock_lite_llm.return_value


class TestRetrievalTool:
    """Tests for the retrieve_context function."""

    def test_retrieval_function_with_results(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test retrieval function formats results correctly."""
        # Setup mock search results
        mock_searcher.hybrid_search.return_value = [
            {"text": "First document content", "score": 0.9},
            {"text": "Second document content", "score": 0.8},
            {"text": "Third document content", "score": 0.7},
        ]

        # Create agent and get the retrieval function
        agent, get_sources = create_rag_agent(settings=mock_settings, top_k=3)
        retrieval_func = mock_function_tool.call_args[0][0]

        # Call the retrieval function
        result = retrieval_func("test query")

        # Verify searcher was called correctly
        mock_searcher.hybrid_search.assert_called_once_with(query="test query", top_k=3)

        # Verify result formatting
        assert "[1] First document content" in result
        assert "[2] Second document content" in result
        assert "[3] Third document content" in result

        # Verify sources are accessible via get_sources
        sources = get_sources()
        assert len(sources) == 3
        assert sources[0]["text"] == "First document content"

    def test_retrieval_function_with_no_results(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test retrieval function handles empty results."""
        mock_searcher.hybrid_search.return_value = []

        # Create agent and get the retrieval function
        agent, get_sources = create_rag_agent(settings=mock_settings)
        retrieval_func = mock_function_tool.call_args[0][0]

        # Call the retrieval function
        result = retrieval_func("test query")

        # Verify message for no results
        assert result == "No relevant information found."

        # Verify sources are empty
        sources = get_sources()
        assert len(sources) == 0

    def test_retrieval_function_skips_empty_content(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test retrieval function skips documents with empty content."""
        mock_searcher.hybrid_search.return_value = [
            {"text": "Valid content", "score": 0.9},
            {"text": "", "score": 0.8},
            {"text": "   ", "score": 0.7},  # Whitespace only
            {"text": "Another valid", "score": 0.6},
        ]

        # Create agent and get the retrieval function
        agent, get_sources = create_rag_agent(settings=mock_settings)
        retrieval_func = mock_function_tool.call_args[0][0]

        # Call the retrieval function
        result = retrieval_func("test query")

        # Verify only valid content is included (enumeration is based on ALL results, not filtered)
        assert "[1] Valid content" in result
        assert "Another valid" in result
        # Empty and whitespace-only content should be skipped
        assert result.count("Valid content") == 1
        assert result.count("Another valid") == 1

        # Verify all sources are stored (even empty ones)
        sources = get_sources()
        assert len(sources) == 4

    def test_retrieval_function_respects_top_k(
        self, mock_settings, mock_searcher, mock_llm_agent, mock_lite_llm, mock_function_tool
    ):
        """Test retrieval function uses correct top_k parameter."""
        # Setup mock return value
        mock_searcher.hybrid_search.return_value = [
            {"text": "Test content", "score": 0.9},
        ]

        # Create agent with custom top_k
        agent, get_sources = create_rag_agent(settings=mock_settings, top_k=7)
        retrieval_func = mock_function_tool.call_args[0][0]

        # Call the retrieval function
        retrieval_func("test query")

        # Verify top_k was passed correctly
        mock_searcher.hybrid_search.assert_called_once()
        call_kwargs = mock_searcher.hybrid_search.call_args[1]
        assert call_kwargs["top_k"] == 7


class TestGetAgentConfig:
    """Tests for get_agent_config function."""

    def test_returns_config_with_default_settings(self):
        """Test config with default settings."""
        with patch("src.agent.rag_agent.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings.llm.provider = "lmstudio"
            mock_settings.llm.model = "test-model"
            mock_settings.llm.temperature = 0.7
            mock_settings.llm.max_tokens = 15000
            mock_settings.elasticsearch.host = "http://localhost:9200"
            mock_settings.elasticsearch.index_name = "test-index"
            mock_settings_class.return_value = mock_settings

            config = get_agent_config()

            assert config["framework"] == "google-adk"
            assert config["agent_type"] == "LlmAgent"
            assert config["llm_provider"] == "lmstudio"
            assert config["llm_model"] == "test-model"
            assert config["mode"] == "stateless"

    def test_returns_config_with_custom_settings(self, mock_settings):
        """Test config with custom settings."""
        config = get_agent_config(settings=mock_settings)

        assert config["framework"] == "google-adk"
        assert config["agent_type"] == "LlmAgent"
        assert config["llm_provider"] == mock_settings.llm.provider
        assert config["llm_model"] == mock_settings.llm.model
        assert config["llm_temperature"] == mock_settings.llm.temperature
        assert config["llm_max_tokens"] == mock_settings.llm.max_tokens
        assert config["elasticsearch_host"] == mock_settings.elasticsearch.host
        assert config["elasticsearch_index"] == mock_settings.elasticsearch.index
        assert config["mode"] == "stateless"

    def test_config_contains_all_expected_keys(self, mock_settings):
        """Test config contains all expected configuration keys."""
        config = get_agent_config(settings=mock_settings)

        expected_keys = [
            "framework",
            "agent_type",
            "llm_provider",
            "llm_model",
            "llm_temperature",
            "llm_max_tokens",
            "elasticsearch_host",
            "elasticsearch_index",
            "mode",
        ]

        for key in expected_keys:
            assert key in config, f"Missing key: {key}"
