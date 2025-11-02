"""Document management UI component for Gradio interface."""

import logging
from pathlib import Path
from typing import Any

import gradio as gr

from src.ui.api_client import ElasticRAGClient
from src.ui.components.utils import (
    ALLOWED_EXTENSIONS,
    create_document_table_data,
    validate_file,
)

logger = logging.getLogger(__name__)


def create_document_upload_compact(client: ElasticRAGClient) -> tuple[gr.Group, dict[str, Any]]:
    """Create compact document upload section for single-page layout.

    Args:
        client: ElasticRAGClient instance for API communication

    Returns:
        Tuple of (Gradio Group component, dictionary of component references)
    """
    with gr.Group() as upload_section:
        with gr.Row():
            file_input = gr.File(
                label="Select Document(s)",
                file_count="multiple",
                file_types=list(ALLOWED_EXTENSIONS),
                type="filepath",
                scale=3,
            )
            with gr.Column(scale=1):
                upload_btn = gr.Button("📤 Upload", variant="primary", size="lg")
                clear_upload_btn = gr.Button("Clear", size="sm")

        upload_status = gr.Markdown("", visible=False)
        upload_progress = gr.Progress()

        # Hidden state to track if documents are processing (for auto-refresh)
        processing_state = gr.State(value=0)  # Count of documents processing

    components = {
        "file_input": file_input,
        "upload_btn": upload_btn,
        "clear_upload_btn": clear_upload_btn,
        "upload_status": upload_status,
        "upload_progress": upload_progress,
        "processing_state": processing_state,
    }

    # Event handlers
    def upload_files(files, progress=gr.Progress()):
        """Upload one or more files and return a trigger for auto-refresh.

        Args:
            files: List of file paths or file info dicts from Gradio File component

        Returns:
            Tuple with (upload_status, processing_count) for auto-refresh triggering
        """
        if not files:
            return (
                gr.update(value="❌ **Error:** No files selected", visible=True),
                0,  # No processing
            )

        results = []
        total_files = len(files)
        processing_count = 0

        for idx, file_info in enumerate(files, 1):
            progress((idx - 1) / total_files, desc=f"Uploading {idx}/{total_files}...")

            # Gradio File component returns file info as dict with 'name' (original) and 'path' (temp)
            # Or sometimes just a string path (depending on version)
            if isinstance(file_info, dict):
                file_path = file_info.get("path", "")
                original_filename = file_info.get(
                    "orig_name", file_info.get("name", Path(file_path).name)
                )
            else:
                # Fallback: string path (use filename from path)
                file_path = file_info
                # Try to extract original name from Gradio's temp path pattern
                # Gradio typically stores as: /tmp/gradio/session_id/original_filename
                path_obj = Path(file_path)
                original_filename = path_obj.name

            # Validate file
            is_valid, error_msg = validate_file(file_path)
            if not is_valid:
                results.append(f"❌ {original_filename}: {error_msg}")
                continue

            try:
                # Upload using async endpoint with original filename (returns immediately)
                result = client.upload_document(file_path, original_filename=original_filename)
                filename = result.get("filename", original_filename)
                doc_id = result.get("document_id", "unknown")
                status = result.get("status", "unknown")
                # For async uploads, chunks_created is 0 since processing happens in background
                if status == "processing":
                    results.append(f"⏳ {filename}: Processing in background ({doc_id})")
                    processing_count += 1
                else:
                    chunks = result.get("chunks_created", 0)
                    results.append(f"✅ {filename}: Uploaded ({doc_id}, {chunks} chunks)")
            except Exception as e:
                results.append(f"❌ {original_filename}: {str(e)}")
                logger.error(f"Upload failed for {original_filename}: {e}", exc_info=True)

        progress(1.0, desc="Upload complete")

        # Format results with processing indicator
        status_message = "\n\n".join(results)
        if processing_count > 0:
            status_message += f"\n\n🔄 **{processing_count} document(s) processing...** The list will auto-refresh when ready."

        return (
            gr.update(value=status_message, visible=True),
            processing_count,  # Return count for auto-refresh triggering
        )

    def clear_upload():
        """Clear upload area."""
        return {
            file_input: gr.update(value=None),
            upload_status: gr.update(value="", visible=False),
        }

    # Connect event handlers
    upload_btn.click(
        fn=upload_files,
        inputs=[file_input],
        outputs=[upload_status, processing_state],
    )

    clear_upload_btn.click(
        fn=clear_upload,
        inputs=[],
        outputs=[file_input, upload_status],
    )

    return upload_section, components


def create_document_library(client: ElasticRAGClient) -> tuple[gr.Group, dict[str, Any]]:
    """Create document library section with table and management controls.

    Args:
        client: ElasticRAGClient instance for API communication

    Returns:
        Tuple of (Gradio Group component, dictionary of component references)
    """
    with gr.Group() as library_section:
        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh", size="sm")
            total_docs_display = gr.Markdown("**Total Documents:** 0")

        # Document table (scrollable, shows all documents - pagination removed)
        document_table = gr.Dataframe(
            headers=["ID", "Filename", "Type", "Chunk Count", "Upload Date"],
            datatype=["str", "str", "str", "number", "str"],
            col_count=(5, "fixed"),
            row_count=(20, "dynamic"),
            interactive=False,
            wrap=True,
        )

        # Delete section
        with gr.Row():
            doc_id_input = gr.Textbox(
                label="Document ID to Delete",
                placeholder="Enter document ID from table",
                scale=3,
            )
            delete_btn = gr.Button("🗑️ Delete", variant="stop", size="lg", scale=1)

        with gr.Row():
            delete_all_btn = gr.Button("🗑️ Delete All Documents", variant="stop", size="sm")

        delete_status = gr.Markdown("", visible=False)

    components = {
        "document_table": document_table,
        "refresh_btn": refresh_btn,
        "total_docs_display": total_docs_display,
        "doc_id_input": doc_id_input,
        "delete_btn": delete_btn,
        "delete_all_btn": delete_all_btn,
        "delete_status": delete_status,
    }

    # Event handlers
    def refresh_documents():
        """Refresh document list (fetch all documents)."""
        try:
            # Fetch all documents (high page_size to get all)
            docs_data = client.list_documents(page=1, page_size=1000)
            table_data = create_document_table_data(docs_data.get("documents", []))
            total_docs = docs_data.get("total", 0)

            return {
                document_table: gr.update(value=table_data),
                total_docs_display: gr.update(value=f"**Total Documents:** {total_docs}"),
            }
        except Exception as e:
            logger.error(f"Failed to refresh documents: {e}", exc_info=True)
            return {
                document_table: gr.update(value=[]),
                total_docs_display: gr.update(
                    value=f"❌ **Error:** Failed to load documents - {str(e)}"
                ),
            }

    def delete_document(doc_id: str):
        """Delete a document by ID."""
        if not doc_id or not doc_id.strip():
            return {
                delete_status: gr.update(
                    value="❌ **Error:** Please enter a document ID", visible=True
                ),
                document_table: gr.update(),
                total_docs_display: gr.update(),
                doc_id_input: gr.update(),
            }

        doc_id = doc_id.strip()

        try:
            client.delete_document(doc_id)
            # Refresh document list
            refresh_result = refresh_documents()
            refresh_result[delete_status] = gr.update(
                value=f"✅ **Success:** Document {doc_id} deleted", visible=True
            )
            refresh_result[doc_id_input] = gr.update(value="")
            return refresh_result
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}", exc_info=True)
            return {
                delete_status: gr.update(
                    value=f"❌ **Error:** Failed to delete document - {str(e)}",
                    visible=True,
                ),
                document_table: gr.update(),
                total_docs_display: gr.update(),
                doc_id_input: gr.update(),
            }

    def delete_all_documents():
        """Delete all documents."""
        try:
            # Get all documents
            docs_data = client.list_documents(page=1, page_size=1000)
            documents = docs_data.get("documents", [])

            if not documents:
                return {
                    delete_status: gr.update(
                        value="ℹ️ **Info:** No documents to delete", visible=True
                    ),
                    document_table: gr.update(),
                    total_docs_display: gr.update(value="**Total Documents:** 0"),
                    doc_id_input: gr.update(),
                }

            # Delete each document
            deleted_count = 0
            failed_count = 0
            errors = []

            for doc in documents:
                doc_id = doc.get("source_file", "")
                if doc_id:
                    try:
                        client.delete_document(doc_id)
                        deleted_count += 1
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"{doc_id}: {str(e)}")
                        logger.error(f"Failed to delete {doc_id}: {e}")

            # Prepare status message
            if failed_count == 0:
                status_msg = f"✅ **Success:** Deleted all {deleted_count} documents"
            else:
                status_msg = (
                    f"⚠️ **Partial Success:** Deleted {deleted_count} documents, "
                    f"{failed_count} failed\n\n"
                    f"Errors:\n" + "\n".join(errors[:5])  # Show first 5 errors
                )

            # Refresh document list
            refresh_result = refresh_documents()
            refresh_result[delete_status] = gr.update(value=status_msg, visible=True)
            refresh_result[doc_id_input] = gr.update(value="")
            return refresh_result

        except Exception as e:
            logger.error(f"Failed to delete all documents: {e}", exc_info=True)
            return {
                delete_status: gr.update(
                    value=f"❌ **Error:** Failed to delete documents - {str(e)}",
                    visible=True,
                ),
                document_table: gr.update(),
                total_docs_display: gr.update(),
                doc_id_input: gr.update(),
            }

    # Connect event handlers
    refresh_btn.click(
        fn=refresh_documents,
        inputs=[],
        outputs=[document_table, total_docs_display],
    )

    delete_btn.click(
        fn=delete_document,
        inputs=[doc_id_input],
        outputs=[delete_status, document_table, total_docs_display, doc_id_input],
    )

    delete_all_btn.click(
        fn=delete_all_documents,
        inputs=[],
        outputs=[delete_status, document_table, total_docs_display, doc_id_input],
    )

    return library_section, components


def create_document_manager(client: ElasticRAGClient) -> tuple[gr.Column, dict[str, Any]]:
    """Create document management UI component.

    This component provides:
    - File upload with drag & drop
    - Document list table (scrollable, no pagination)
    - Delete functionality
    - Upload progress tracking
    - Status indicators

    Args:
        client: ElasticRAGClient instance for API communication

    Returns:
        Tuple of (Gradio Column component, dictionary of component references)
    """
    with gr.Column() as doc_manager:
        gr.Markdown("## 📁 Document Management")
        gr.Markdown(
            "Upload documents to the RAG system. "
            f"Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

        # Upload Section
        with gr.Group():
            gr.Markdown("### Upload Documents")

            file_input = gr.File(
                label="Select File(s)",
                file_count="multiple",
                file_types=list(ALLOWED_EXTENSIONS),
                type="filepath",
            )

            with gr.Row():
                upload_btn = gr.Button("Upload", variant="primary", size="lg")
                clear_upload_btn = gr.Button("Clear", size="lg")

            upload_status = gr.Markdown("", visible=False)
            upload_progress = gr.Progress()

        # Document Library Section
        with gr.Group():
            gr.Markdown("### Document Library")

            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh", size="sm")
                total_docs_display = gr.Markdown("**Total Documents:** 0")

            # Document table (scrollable, shows all documents)
            document_table = gr.Dataframe(
                headers=["ID", "Filename", "Type", "Chunks", "Upload Date"],
                datatype=["str", "str", "str", "number", "str"],
                col_count=(5, "fixed"),
                row_count=(20, "dynamic"),
                interactive=False,
                wrap=True,
            )

            # Delete section
            with gr.Row():
                doc_id_input = gr.Textbox(
                    label="Document ID to Delete",
                    placeholder="Enter document ID from table",
                    scale=3,
                )
                delete_btn = gr.Button("🗑️ Delete", variant="stop", size="lg", scale=1)

            delete_status = gr.Markdown("", visible=False)

    # Store component references
    components = {
        "file_input": file_input,
        "upload_btn": upload_btn,
        "clear_upload_btn": clear_upload_btn,
        "upload_status": upload_status,
        "upload_progress": upload_progress,
        "document_table": document_table,
        "refresh_btn": refresh_btn,
        "total_docs_display": total_docs_display,
        "doc_id_input": doc_id_input,
        "delete_btn": delete_btn,
        "delete_status": delete_status,
    }

    # Event handlers
    def upload_files(files, progress=gr.Progress()):
        """Upload one or more files."""
        if not files:
            return {
                upload_status: gr.update(value="❌ **Error:** No files selected", visible=True),
            }

        results = []
        total_files = len(files)

        for idx, file_path in enumerate(files, 1):
            progress((idx - 1) / total_files, desc=f"Uploading {idx}/{total_files}...")

            # Validate file
            is_valid, error_msg = validate_file(file_path)
            if not is_valid:
                filename = Path(file_path).name
                results.append(f"❌ {filename}: {error_msg}")
                continue

            try:
                # Upload using sync endpoint
                result = client.upload_document(file_path)
                filename = result.get("filename", Path(file_path).name)
                doc_id = result.get("document_id", "unknown")
                chunks = result.get("chunks_created", 0)
                results.append(f"✅ {filename}: Uploaded ({doc_id}, {chunks} chunks)")
            except Exception as e:
                filename = Path(file_path).name
                results.append(f"❌ {filename}: {str(e)}")
                logger.error(f"Upload failed for {filename}: {e}", exc_info=True)

        progress(1.0, desc="Upload complete")

        # Format results
        status_message = "\n\n".join(results)

        # Refresh document list
        try:
            docs_data = client.list_documents(page=1, page_size=1000)
            table_data = create_document_table_data(docs_data.get("documents", []))
            total_docs = docs_data.get("total", 0)

            return {
                upload_status: gr.update(value=status_message, visible=True),
                document_table: gr.update(value=table_data),
                total_docs_display: gr.update(value=f"**Total Documents:** {total_docs}"),
            }
        except Exception as e:
            logger.error(f"Failed to refresh document list: {e}")
            return {
                upload_status: gr.update(
                    value=status_message + f"\n\n⚠️ Failed to refresh list: {str(e)}",
                    visible=True,
                ),
            }

    def clear_upload():
        """Clear upload area."""
        return {
            file_input: gr.update(value=None),
            upload_status: gr.update(value="", visible=False),
        }

    def refresh_documents():
        """Refresh document list (fetch all documents)."""
        try:
            docs_data = client.list_documents(page=1, page_size=1000)
            table_data = create_document_table_data(docs_data.get("documents", []))
            total_docs = docs_data.get("total", 0)

            return {
                document_table: gr.update(value=table_data),
                total_docs_display: gr.update(value=f"**Total Documents:** {total_docs}"),
            }
        except Exception as e:
            logger.error(f"Failed to refresh documents: {e}", exc_info=True)
            return {
                document_table: gr.update(value=[]),
                total_docs_display: gr.update(
                    value=f"❌ **Error:** Failed to load documents - {str(e)}"
                ),
            }

    def delete_document(doc_id: str):
        """Delete a document by ID."""
        if not doc_id or not doc_id.strip():
            return {
                delete_status: gr.update(
                    value="❌ **Error:** Please enter a document ID", visible=True
                ),
            }

        doc_id = doc_id.strip()

        try:
            client.delete_document(doc_id)
            # Refresh document list
            refresh_result = refresh_documents()
            refresh_result[delete_status] = gr.update(
                value=f"✅ **Success:** Document {doc_id} deleted", visible=True
            )
            refresh_result[doc_id_input] = gr.update(value="")
            return refresh_result
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}", exc_info=True)
            return {
                delete_status: gr.update(
                    value=f"❌ **Error:** Failed to delete document - {str(e)}",
                    visible=True,
                ),
            }

    # Connect event handlers
    upload_btn.click(
        fn=upload_files,
        inputs=[file_input],
        outputs=[upload_status, document_table, total_docs_display],
    )

    clear_upload_btn.click(
        fn=clear_upload,
        inputs=[],
        outputs=[file_input, upload_status],
    )

    refresh_btn.click(
        fn=refresh_documents,
        inputs=[],
        outputs=[document_table, total_docs_display],
    )

    delete_btn.click(
        fn=delete_document,
        inputs=[doc_id_input],
        outputs=[delete_status, document_table, total_docs_display, doc_id_input],
    )

    return doc_manager, components
