"""Main Gradio application for Elastic RAG system.

This module provides a web-based user interface for:
- Document upload and management
- Interactive chat with RAG system
- System health monitoring
"""

import logging
from typing import Any

import gradio as gr

from src.ui.api_client import ElasticRAGClient
from src.ui.components.chat_interface import create_chat_interface
from src.ui.components.document_manager import (
    create_document_library,
    create_document_upload_compact,
)

logger = logging.getLogger(__name__)

# Custom CSS for styling
CUSTOM_CSS = """
.gradio-container {
    font-family: 'Inter', sans-serif;
}

.status-success {
    color: #10b981;
    font-weight: 600;
}

.status-error {
    color: #ef4444;
    font-weight: 600;
}

.status-warning {
    color: #f59e0b;
    font-weight: 600;
}

/* Improve chatbot appearance */
.message-wrap {
    padding: 12px;
    border-radius: 8px;
}

/* Make buttons more prominent */
button {
    font-weight: 500;
}

/* Table styling */
.dataframe {
    font-size: 14px;
}

/* Smaller font for sources display - smaller than chat messages */
#sources-display, #sources-display p, #sources-display div {
    font-size: 12px !important;
    line-height: 1.5 !important;
}

#sources-display strong {
    font-size: 12px !important;
    font-weight: 600;
}

#sources-display h1, #sources-display h2, #sources-display h3 {
    font-size: 13px !important;
}
"""


def create_gradio_app(
    api_url: str = "http://localhost:8000",
    title: str = "Elastic RAG System",
    description: str | None = None,
) -> gr.Blocks:
    """Create the main Gradio application.

    Args:
        api_url: URL of the FastAPI backend
        title: Application title
        description: Optional description text

    Returns:
        Gradio Blocks application
    """
    # Initialize API client
    client = ElasticRAGClient(api_url=api_url)

    # Check API health on startup
    api_status = "🟢 Connected"
    try:
        client.health_check()
        logger.info("API health check successful")
    except Exception as e:
        logger.error(f"API health check failed: {e}")
        api_status = f"🔴 Disconnected - {str(e)}"

    # Default description
    if description is None:
        description = (
            "Upload documents and ask questions to get AI-powered answers "
            "with source citations from your document collection."
        )

    # Create Gradio app
    with gr.Blocks(
        title=title,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="gray",
            neutral_hue="slate",
        ),
        css=CUSTOM_CSS,
    ) as app:
        # Header
        gr.Markdown(f"# {title}")
        gr.Markdown(description)

        # API Status
        with gr.Accordion("🔍 System Status", open=False):
            api_status_display = gr.Markdown(f"**API Status:** {api_status}")
            refresh_status_btn = gr.Button("Refresh Status", size="sm")

            def refresh_api_status():
                """Refresh API connection status."""
                try:
                    client.health_check()
                    status_text = "🟢 **Connected** - API is healthy"
                    return gr.update(value=status_text)
                except Exception as e:
                    status_text = f"🔴 **Disconnected** - {str(e)}"
                    return gr.update(value=status_text)

            refresh_status_btn.click(
                fn=refresh_api_status,
                inputs=[],
                outputs=[api_status_display],
            )

        # Main content - tabbed layout for logical separation
        with gr.Tabs():
            # Tab 1: Document Management (Upload + Library)
            with gr.Tab("📁 Document Management"):
                gr.Markdown("### Upload Documents")
                gr.Markdown(
                    f"Upload documents to the RAG system. "
                    f"Supported: {', '.join(['.txt', '.pdf', '.html', '.md', '.docx'])}"
                )
                doc_upload_section, upload_components = create_document_upload_compact(client)

                gr.Markdown("---")  # Visual separator

                gr.Markdown("### Document Library")
                doc_library_section, library_components = create_document_library(client)

                # Manual refresh approach - user clicks refresh button
                # This is more reliable than timer-based polling
                refresh_btn = gr.Button("🔄 Refresh Document List", variant="secondary", size="sm")

                initial_doc_count_state = gr.State(value=0)

                def refresh_documents():
                    """Manually refresh document list."""
                    try:
                        docs_data = client.list_documents(page=1, page_size=1000)
                        from src.ui.components.utils import create_document_table_data

                        table_data = create_document_table_data(docs_data.get("documents", []))
                        total = docs_data.get("total", 0)
                        logger.info(f"Manual refresh: {total} documents")
                        return (
                            gr.update(value=table_data),
                            gr.update(value=f"**Total Documents:** {total}"),
                        )
                    except Exception as e:
                        logger.error(f"Refresh error: {e}", exc_info=True)
                        return gr.update(), gr.update()

                def check_and_clear_processing_message(initial_count, processing_count):
                    """After upload, check processing status directly from API."""
                    if processing_count <= 0:
                        return 0, gr.update()

                    try:
                        # Wait a moment for processing to start
                        import time

                        time.sleep(2)

                        # Check processing status from API (queries Elasticsearch directly)
                        processing_statuses = client.list_processing_status()

                        # Count how many are still processing or pending
                        active_count = sum(
                            1
                            for status in processing_statuses
                            if status.get("status") in ["pending", "processing"]
                        )

                        # Count completed in this batch
                        completed_count = sum(
                            1
                            for status in processing_statuses
                            if status.get("status") == "completed"
                        )

                        logger.info(
                            f"Status check: active={active_count}, completed={completed_count}, "
                            f"expected={processing_count}"
                        )

                        if active_count == 0 and completed_count >= processing_count:
                            # All done!
                            logger.info(f"All documents processed: {completed_count} completed")
                            return (
                                0,
                                gr.update(
                                    value=f"✅ **Complete!** {completed_count} document(s) indexed. Click refresh button to update list.",
                                    visible=True,
                                ),
                            )
                        elif active_count > 0:
                            # Still processing
                            logger.debug(f"Documents still processing: {active_count} active")
                            return (
                                active_count,
                                gr.update(
                                    value=f"🔄 **{active_count} document(s) processing...** Click the refresh button below after ~2 minutes to see them.",
                                    visible=True,
                                ),
                            )
                        else:
                            # Processing complete but count mismatch - show generic message
                            return (
                                0,
                                gr.update(
                                    value="✅ **Processing complete!** Click refresh button to update list.",
                                    visible=True,
                                ),
                            )

                    except Exception as e:
                        logger.error(f"Check error: {e}", exc_info=True)
                        return (
                            0,
                            gr.update(
                                value="⚠️ **Status check failed.** Click refresh button to update list.",
                                visible=True,
                            ),
                        )

                # Store initial count when upload starts
                upload_components["processing_state"].change(
                    fn=lambda processing_count: (
                        client.list_documents(page=1, page_size=1000).get("total", 0)
                        if processing_count > 0
                        else 0
                    ),
                    inputs=[upload_components["processing_state"]],
                    outputs=[initial_doc_count_state],
                ).then(
                    # Check once after a delay
                    fn=check_and_clear_processing_message,
                    inputs=[initial_doc_count_state, upload_components["processing_state"]],
                    outputs=[
                        upload_components["processing_state"],
                        upload_components["upload_status"],
                    ],
                )

                # Manual refresh button
                refresh_btn.click(
                    fn=refresh_documents,
                    inputs=[],
                    outputs=[
                        library_components["document_table"],
                        library_components["total_docs_display"],
                    ],
                )

            # Tab 2: Chat Interface
            with gr.Tab("💬 Chat"):
                chat_ui, chat_components = create_chat_interface(client)

        # Footer
        gr.Markdown(
            """
            ---
            **Elastic RAG System** | Built with [Gradio](https://gradio.app) |
            [Documentation](https://github.com/yourusername/elastic_rag)
            """
        )

    return app


def launch_app(
    api_url: str = "http://localhost:8000",
    host: str = "0.0.0.0",
    port: int = 7860,
    share: bool = False,
    **kwargs: Any,
) -> None:
    """Launch the Gradio application.

    Args:
        api_url: URL of the FastAPI backend
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 7860)
        share: Enable Gradio sharing (default: False)
        **kwargs: Additional arguments passed to gr.Blocks.launch()
    """
    logger.info(f"Launching Gradio UI on {host}:{port}")
    logger.info(f"API URL: {api_url}")

    app = create_gradio_app(api_url=api_url)

    app.launch(
        server_name=host,
        server_port=port,
        share=share,
        **kwargs,
    )
