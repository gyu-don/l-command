"""
Handler for processing PDF files.
"""

import logging
import subprocess
from pathlib import Path

from l_command.handlers.base import FileHandler

# Constants specific to PDF handling
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024  # 50MB limit for PDF processing
PDF_PREVIEW_PAGES = 5  # Number of pages to preview

logger = logging.getLogger(__name__)


class PDFHandler(FileHandler):
    """Handler for processing PDF files."""

    @classmethod
    def can_handle(cls: type["PDFHandler"], path: Path) -> bool:
        """Check if the path is a PDF file.

        Args:
            path: The path to check.

        Returns:
            True if the path is a PDF file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() == ".pdf":
            try:
                if path.stat().st_size == 0:
                    return False
            except OSError:
                return False  # Cannot stat, likely doesn't exist or permission error
            return True

        # Check by content (PDF magic bytes)
        try:
            with path.open("rb") as f:
                header = f.read(8)
                if header.startswith(b"%PDF-"):
                    return True
        except OSError:
            pass

        return False

    @classmethod
    def handle(cls: type["PDFHandler"], path: Path) -> None:
        """Display PDF file information and text content.

        Args:
            path: The PDF file path to display.
        """
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                print("(Empty PDF file)")
                return

            if file_size > MAX_PDF_SIZE_BYTES:
                logger.warning(
                    f"PDF file size ({file_size} bytes) exceeds limit "
                    f"({MAX_PDF_SIZE_BYTES} bytes). "
                    f"Falling back to default viewer.",
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Try to use pdfminer.six
            try:
                from pdfminer.high_level import extract_text

                # Extract text from PDF
                text_content = extract_text(str(path))
                if text_content.strip():
                    # Create a temporary process-like object for smart_pager
                    content_lines = text_content.split("\n")

                    # Display metadata first
                    print(f"PDF File: {path.name}")
                    print(f"Size: {file_size:,} bytes")
                    print(f"Pages: {len(content_lines) // 50 if content_lines else 'Unknown'}")  # Rough estimate
                    print("-" * 50)

                    # Use smart_pager by writing content to stdout or pager
                    if len(content_lines) > 20:  # Use threshold for paging
                        # Create a subprocess to pipe content through less
                        pager_process = subprocess.Popen(
                            ["less", "-RFX"],
                            stdin=subprocess.PIPE,
                            text=True,
                        )
                        if pager_process.stdin:
                            try:
                                pager_process.stdin.write(text_content)
                                pager_process.stdin.close()
                                pager_process.wait()
                            except BrokenPipeError:
                                # User exited pager early
                                pass
                    else:
                        print(text_content)
                else:
                    print(f"PDF File: {path.name}")
                    print(f"Size: {file_size:,} bytes")
                    print("(No extractable text content)")

            except ImportError:
                logger.warning(
                    "pdfminer.six not available. Install with: uv add pdfminer.six",
                )
                # Show basic file info instead
                print(f"PDF File: {path.name}")
                print(f"Size: {file_size:,} bytes")
                print("(Install pdfminer.six for text extraction)")

            except Exception as e:
                logger.warning(f"Error extracting PDF text: {e}")
                print(f"PDF File: {path.name}")
                print(f"Size: {file_size:,} bytes")
                print("(Error extracting text content)")

        except OSError as e:
            logger.error(
                f"Error accessing PDF file: {e}",
            )
            # Fallback if we can't even get the file size
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def priority(cls: type["PDFHandler"]) -> int:
        """Return the priority of the PDF handler.

        Returns:
            60 (high priority, higher than JSON).
        """
        return 60  # PDF has higher priority than JSON
