"""Document processing and conversion using Docling."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Document metadata extracted from the source."""

    filename: str
    format: str
    title: str | None = None
    author: str | None = None
    created_date: str | None = None
    page_count: int | None = None


@dataclass
class ProcessedDocument:
    """Processed document with text and metadata."""

    text: str
    metadata: DocumentMetadata


class DocumentProcessor:
    """Processes documents using Docling."""

    # Supported document formats
    SUPPORTED_FORMATS = {
        ".pdf": InputFormat.PDF,
        ".docx": InputFormat.DOCX,
        ".pptx": InputFormat.PPTX,
        ".html": InputFormat.HTML,
        ".htm": InputFormat.HTML,
        ".txt": None,  # Plain text doesn't need Docling
        ".md": InputFormat.MD,
        ".asciidoc": InputFormat.ASCIIDOC,
        ".adoc": InputFormat.ASCIIDOC,
    }

    def __init__(
        self,
        do_ocr: bool = True,
        do_table_structure: bool = True,
        do_table_cell_matching: bool = True,
        ocr_languages: list[str] | None = None,
    ):
        """Initialize document processor with Docling converter.

        Args:
            do_ocr: Enable OCR for text extraction from images (default: True)
            do_table_structure: Enable table structure extraction (default: True)
            do_table_cell_matching: Enable table cell matching (default: True)
            ocr_languages: List of OCR languages (default: ["en"])
        """
        if ocr_languages is None:
            ocr_languages = ["en"]

        # Configure PDF processing options
        pdf_pipeline_options = PdfPipelineOptions()
        pdf_pipeline_options.do_ocr = do_ocr
        pdf_pipeline_options.do_table_structure = do_table_structure
        pdf_pipeline_options.table_structure_options.do_cell_matching = do_table_cell_matching
        pdf_pipeline_options.ocr_options.lang = ocr_languages

        # Configure accelerator options for better performance
        num_threads = max(1, os.cpu_count() // 2)  # Use half of available CPU cores
        pdf_pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=num_threads,
            device=AcceleratorDevice.AUTO,  # Automatically select best device (CPU/GPU)
        )

        # Create format options
        pdf_format_option = PdfFormatOption(pipeline_options=pdf_pipeline_options)

        # Initialize DocumentConverter with configured options
        self.converter = DocumentConverter(format_options={InputFormat.PDF: pdf_format_option})

        logger.info(
            f"DocumentProcessor initialized with OCR={'enabled' if do_ocr else 'disabled'}, "
            f"table_structure={'enabled' if do_table_structure else 'disabled'}, "
            f"num_threads={num_threads}, "
            f"languages={ocr_languages}"
        )

    def is_supported(self, file_path: Path) -> bool:
        """
        Check if file format is supported.

        Args:
            file_path: Path to document file

        Returns:
            True if format is supported, False otherwise
        """
        suffix = file_path.suffix.lower()
        return suffix in self.SUPPORTED_FORMATS

    def process_document(self, file_path: Path) -> ProcessedDocument:
        """
        Process a document and extract text and metadata.

        Args:
            file_path: Path to document file

        Returns:
            ProcessedDocument with text and metadata

        Raises:
            ValueError: If format not supported
            RuntimeError: If conversion fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.is_supported(file_path):
            raise ValueError(
                f"Unsupported format: {file_path.suffix}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS.keys())}"
            )

        logger.info(f"Processing document: {file_path.name}")

        try:
            # Handle plain text files separately
            if file_path.suffix.lower() == ".txt":
                text = self._extract_text_from_txt(file_path)
                metadata = self._create_basic_metadata(file_path)
            else:
                # Use Docling for other formats
                text = self._extract_text(file_path)
                metadata = self._extract_metadata(file_path)

            logger.info(
                f"Successfully processed {file_path.name}: " f"{len(text)} characters extracted"
            )

            return ProcessedDocument(text=text, metadata=metadata)

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            raise RuntimeError(f"Failed to process {file_path}: {e}") from e

    def _extract_text_from_txt(self, file_path: Path) -> str:
        """
        Extract text from plain text file.

        Args:
            file_path: Path to text file

        Returns:
            Text content
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(file_path, encoding="latin-1") as f:
                return f.read()

    def _extract_text(self, file_path: Path) -> str:
        """
        Extract text from document using Docling.

        Args:
            file_path: Path to document file

        Returns:
            Extracted text content
        """
        logger.debug(f"Converting {file_path.name} with Docling...")

        # Convert document
        result = self.converter.convert(str(file_path))

        # Export to markdown for text extraction
        text = result.document.export_to_markdown()

        return text

    def _extract_metadata(self, file_path: Path) -> DocumentMetadata:
        """
        Extract metadata from document using Docling.

        Args:
            file_path: Path to document file

        Returns:
            DocumentMetadata with extracted information
        """
        logger.debug(f"Extracting metadata from {file_path.name}...")

        # Convert document
        result = self.converter.convert(str(file_path))
        doc = result.document

        # Extract metadata from Docling document
        metadata = DocumentMetadata(
            filename=file_path.name,
            format=file_path.suffix.lower(),
            title=None,  # Docling doesn't expose this directly in basic API
            author=None,
            created_date=None,
            page_count=len(doc.pages) if hasattr(doc, "pages") else None,
        )

        return metadata

    def _create_basic_metadata(self, file_path: Path) -> DocumentMetadata:
        """
        Create basic metadata for plain text files.

        Args:
            file_path: Path to text file

        Returns:
            DocumentMetadata with basic information
        """
        return DocumentMetadata(
            filename=file_path.name,
            format=file_path.suffix.lower(),
            title=file_path.stem,
            author=None,
            created_date=None,
            page_count=None,
        )
