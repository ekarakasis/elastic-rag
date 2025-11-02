"""Chat interface UI component for Gradio interface."""

import logging
from typing import Any

import gradio as gr

from src.ui.api_client import ElasticRAGClient
from src.ui.components.utils import format_sources

logger = logging.getLogger(__name__)

# Maximum chat history length
MAX_CHAT_HISTORY = 50


def create_chat_interface(client: ElasticRAGClient) -> tuple[gr.Column, dict[str, Any]]:
    """Create chat interface UI component.

    This component provides:
    - Chatbot component with message history (max 50 messages)
    - Message input and send functionality
    - Source citations as Accordion components
    - Top-K slider control
    - Clear chat functionality

    Args:
        client: ElasticRAGClient instance for API communication

    Returns:
        Tuple of (Gradio Column component, dictionary of component references)
    """
    with gr.Column() as chat_interface:
        gr.Markdown("## 💬 Chat with Your Documents")
        gr.Markdown(
            "Ask questions about your uploaded documents. The AI will provide answers with source citations."
        )

        # Warning for no documents
        no_docs_warning = gr.Markdown(
            "⚠️ **No documents indexed yet.** Please upload documents in the Document Management tab first.",
            visible=False,
        )

        # Chat window (expanded height for single-page layout)
        chatbot = gr.Chatbot(
            label="Conversation",
            height=600,
            show_copy_button=True,
            avatar_images=(None, "🤖"),
        )

        # Input section
        with gr.Row():
            msg_input = gr.Textbox(
                label="Your Question",
                placeholder="Type your question here...",
                lines=2,
                scale=4,
            )
            with gr.Column(scale=1):
                send_btn = gr.Button("Send", variant="primary", size="lg")
                clear_btn = gr.Button("Clear Chat", size="lg")

        # Settings
        with gr.Accordion("⚙️ Query Settings", open=False):
            top_k_slider = gr.Slider(
                minimum=1,
                maximum=20,
                value=5,
                step=1,
                label="Top-K Documents",
                info="Number of source documents to retrieve",
            )

        # Source display
        with gr.Accordion("📚 Sources", open=False) as sources_accordion:
            sources_display = gr.Markdown("No sources yet.", elem_id="sources-display")

        # Status message
        status_message = gr.Markdown("", visible=False)

    # Store component references
    components = {
        "chatbot": chatbot,
        "msg_input": msg_input,
        "send_btn": send_btn,
        "clear_btn": clear_btn,
        "top_k_slider": top_k_slider,
        "sources_display": sources_display,
        "sources_accordion": sources_accordion,
        "status_message": status_message,
        "no_docs_warning": no_docs_warning,
    }

    # Chat history state (list of [user_msg, bot_msg] pairs)
    chat_history = gr.State(value=[])

    # Event handlers
    def check_documents_available():
        """Check if any documents are indexed."""
        try:
            docs_data = client.list_documents(page=1, page_size=1)
            total_docs = docs_data.get("total", 0)
            return total_docs > 0
        except Exception as e:
            logger.error(f"Failed to check document availability: {e}")
            return False

    def send_message(message: str, history: list, top_k: int):
        """Send a message and get response."""
        if not message or not message.strip():
            return {
                chatbot: history,
                msg_input: "",
                status_message: gr.update(
                    value="⚠️ **Warning:** Please enter a question", visible=True
                ),
            }

        # Check if documents are available
        if not check_documents_available():
            return {
                chatbot: history,
                msg_input: message,
                no_docs_warning: gr.update(visible=True),
                status_message: gr.update(
                    value="❌ **Error:** No documents available for querying", visible=True
                ),
            }

        # Clear warnings
        message = message.strip()

        # Add user message to history
        history.append([message, None])

        try:
            # Query the API
            result = client.query(question=message, top_k=top_k)

            # Extract answer and sources
            answer = result.get("answer", "No answer generated.")
            sources = result.get("sources", [])
            metadata = result.get("metadata", {})

            # Log diagnostics for source count verification
            logger.info(
                f"Query response: {len(sources)} sources received, "
                f"metadata reports: {metadata.get('sources_count', 'N/A')}"
            )

            # Update last message with bot response
            history[-1][1] = answer

            # Format sources
            sources_text = format_sources(sources)
            logger.debug(f"Formatted {len(sources)} sources for display")

            # Enforce max history length (FIFO)
            if len(history) > MAX_CHAT_HISTORY:
                history = history[-MAX_CHAT_HISTORY:]

            return {
                chatbot: history,
                msg_input: "",
                sources_display: gr.update(value=sources_text),
                status_message: gr.update(value="", visible=False),
                no_docs_warning: gr.update(visible=False),
                chat_history: history,
            }

        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            # Update last message with error
            history[-1][1] = f"❌ **Error:** {str(e)}"

            return {
                chatbot: history,
                msg_input: message,
                sources_display: gr.update(value="No sources (error occurred)."),
                status_message: gr.update(
                    value=f"❌ **Error:** Query failed - {str(e)}", visible=True
                ),
                no_docs_warning: gr.update(visible=False),
                chat_history: history,
            }

    def clear_chat():
        """Clear chat history."""
        return {
            chatbot: [],
            msg_input: "",
            sources_display: gr.update(value="No sources yet."),
            status_message: gr.update(value="", visible=False),
            chat_history: [],
        }

    def submit_on_enter(message: str, history: list, top_k: int):
        """Handle Enter key submission."""
        return send_message(message, history, top_k)

    # Connect event handlers
    send_btn.click(
        fn=send_message,
        inputs=[msg_input, chat_history, top_k_slider],
        outputs=[
            chatbot,
            msg_input,
            sources_display,
            status_message,
            no_docs_warning,
            chat_history,
        ],
    )

    msg_input.submit(
        fn=submit_on_enter,
        inputs=[msg_input, chat_history, top_k_slider],
        outputs=[
            chatbot,
            msg_input,
            sources_display,
            status_message,
            no_docs_warning,
            chat_history,
        ],
    )

    clear_btn.click(
        fn=clear_chat,
        inputs=[],
        outputs=[
            chatbot,
            msg_input,
            sources_display,
            status_message,
            chat_history,
        ],
    )

    return chat_interface, components
