"""Tests for Gradio UI components."""

from unittest.mock import Mock, patch

import pytest

from src.ui.api_client import ElasticRAGClient
from src.ui.components.utils import (
    format_file_size,
    format_timestamp,
    get_status_emoji,
    sanitize_filename,
    truncate_text,
)


class TestUtils:
    """Test utility functions."""

    def test_format_file_size(self):
        """Test file size formatting."""
        assert format_file_size(500) == "500 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        timestamp = "2025-10-30T14:30:00Z"
        result = format_timestamp(timestamp)
        assert "Oct 30, 2025" in result

    def test_truncate_text(self):
        """Test text truncation."""
        text = "a" * 200
        result = truncate_text(text, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")

        short_text = "short"
        assert truncate_text(short_text, max_length=100) == short_text

    def test_get_status_emoji(self):
        """Test status emoji mapping."""
        assert get_status_emoji("completed") == "✅"
        assert get_status_emoji("failed") == "❌"
        assert get_status_emoji("processing") == "⏳"
        assert get_status_emoji("pending") == "⏸️"
        assert get_status_emoji("ready") == "✅"
        assert get_status_emoji("unknown") == "❓"

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        dangerous = 'test<>:"/\\|?*.txt'
        result = sanitize_filename(dangerous)
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "/" not in result
        assert "\\" not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result


class TestAPIClient:
    """Test API client."""

    def test_client_initialization(self):
        """Test client initialization."""
        client = ElasticRAGClient(api_url="http://localhost:8000")
        assert client.api_url == "http://localhost:8000"
        assert client.upload_timeout == 120.0
        assert client.query_timeout == 60.0

    @patch("src.ui.api_client.httpx")
    def test_health_check(self, mock_httpx):
        """Test health check method."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status = Mock()
        mock_httpx.get.return_value = mock_response

        client = ElasticRAGClient()
        result = client.health_check()

        assert result["status"] == "healthy"
        mock_httpx.get.assert_called_once()


@pytest.mark.skip(reason="Requires running Gradio app - manual testing only")
class TestGradioApp:
    """Test Gradio application (requires manual testing)."""

    def test_create_app(self):
        """Test app creation."""
        from src.ui.gradio_app import create_gradio_app

        app = create_gradio_app(api_url="http://localhost:8000")
        assert app is not None
