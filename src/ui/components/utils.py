"""Utility functions for UI components."""

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported file extensions
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".htm", ".txt", ".md", ".adoc"}


def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB", "250 KB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / 1024**2:.1f} MB"
    else:
        return f"{size_bytes / 1024**3:.1f} GB"


def format_timestamp(timestamp: str | datetime) -> str:
    """Format timestamp to human-readable format.

    Args:
        timestamp: ISO format timestamp string or datetime object

    Returns:
        Formatted string (e.g., "Oct 30, 2025 14:30")
    """
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return timestamp

    return timestamp.strftime("%b %d, %Y %H:%M")


def validate_file(file_path: str | Path, max_size_mb: int = 50) -> tuple[bool, str]:
    """Validate file for upload.

    Args:
        file_path: Path to file
        max_size_mb: Maximum file size in MB

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            return False, "File does not exist"

        if not file_path.is_file():
            return False, "Path is not a file"

        # Check extension
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return (
                False,
                f"Unsupported file type: {file_path.suffix}. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        # Check size
        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024**2)
        if size_mb > max_size_mb:
            return (
                False,
                f"File too large: {format_file_size(size_bytes)}. Maximum: {max_size_mb} MB",
            )

        return True, ""

    except Exception as e:
        logger.error(f"File validation error: {e}")
        return False, f"Validation error: {str(e)}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with "..." if truncated
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text by replacing multiple spaces/newlines with single space.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple whitespace characters (including newlines) with single space
    normalized = re.sub(r"\s+", " ", text)
    return normalized.strip()


def format_sources(sources: list[dict]) -> str:
    """Format source documents for display.

    Args:
        sources: List of source document dictionaries with 'content' and 'metadata'

    Returns:
        Formatted markdown string with source information
    """
    if not sources:
        return "No sources found."

    logger.debug(f"Formatting {len(sources)} sources for display")
    formatted = []
    for i, source in enumerate(sources, 1):
        # API returns 'content' field, not 'text' (fix for bug)
        content = source.get("content", source.get("text", "")).strip()
        metadata = source.get("metadata", {})
        score = source.get("score", 0.0)

        # Normalize whitespace in content (remove excessive newlines/spaces)
        content = normalize_whitespace(content)

        # Extract metadata - try both field names for compatibility
        filename = metadata.get("original_filename", metadata.get("source_file", "unknown"))
        chunk_id = metadata.get("chunk_index", "?")

        # Use HTML small tags for metadata (smaller, cleaner look)
        formatted.append(
            f"**Source {i}** | Score: {score:.3f}\n"
            f"<small>📄 {filename} • Chunk {chunk_id}</small>\n\n"
            f"{truncate_text(content, 300)}\n\n"
            f"---"
        )

    return "\n\n".join(formatted)


def create_document_table_data(documents: list[dict]) -> list[list[str]]:
    """Convert document list to table data format for Gradio Dataframe.

    Args:
        documents: List of document dictionaries from API (DocumentInfo structure)

    Returns:
        List of lists for Gradio Dataframe (each inner list is a row)
    """
    table_data = []
    for doc in documents:
        # API returns 'source_file' as the document identifier
        source_file = doc.get("source_file", "unknown")
        # API returns 'chunks_count' not 'chunk_count'
        chunks = doc.get("chunks_count", 0)
        # API returns 'indexed_at' not 'upload_date'
        indexed_at = doc.get("indexed_at", "")
        file_type = Path(source_file).suffix.upper().lstrip(".")

        # Format indexed date
        formatted_date = format_timestamp(indexed_at) if indexed_at else "Unknown"

        # Use source_file as both ID and filename
        table_data.append([source_file, source_file, file_type, chunks, formatted_date])

    return table_data


def get_status_emoji(status: str) -> str:
    """Get emoji for status.

    Args:
        status: Status string (e.g., "completed", "failed", "processing")

    Returns:
        Emoji representing the status
    """
    status_map = {
        "completed": "✅",
        "failed": "❌",
        "processing": "⏳",
        "pending": "⏸️",
        "ready": "✅",
    }
    return status_map.get(status.lower(), "❓")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove any path separators
    filename = Path(filename).name

    # Remove any potentially dangerous characters
    dangerous_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    for char in dangerous_chars:
        filename = filename.replace(char, "_")

    return filename
