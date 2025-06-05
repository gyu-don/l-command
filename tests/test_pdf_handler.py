"""
Tests for PDFHandler.
"""

import tempfile
from pathlib import Path

from l_command.handlers.pdf import PDFHandler


def test_can_handle_pdf_extension() -> None:
    """Test PDF handler detection by extension."""
    # PDF file with .pdf extension
    with tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb") as tmp:
        tmp.write(b"%PDF-1.4\n%dummy content")  # Write minimal PDF header
        tmp.flush()
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is True

    # PDF file with .PDF extension (uppercase)
    with tempfile.NamedTemporaryFile(suffix=".PDF", mode="wb") as tmp:
        tmp.write(b"%PDF-1.5\n%dummy content")
        tmp.flush()
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is True

    # Empty PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is False

    # Non-PDF extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is False


def test_can_handle_pdf_content() -> None:
    """Test PDF handler detection by content."""
    # PDF content with magic bytes
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as tmp:
        tmp.write(b"%PDF-1.4\n%dummy content")
        tmp.flush()
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is True

    # Non-PDF content
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as tmp:
        tmp.write(b"This is not a PDF")
        tmp.flush()
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is False


def test_priority() -> None:
    """Test PDF handler priority."""
    assert PDFHandler.priority() == 60
