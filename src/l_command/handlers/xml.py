"""
Handler for processing XML and HTML files.
"""

import logging
import subprocess
from pathlib import Path

from l_command.handlers.base import FileHandler
from l_command.utils import smart_pager

# Constants specific to XML/HTML handling
MAX_XML_SIZE_BYTES = 50 * 1024 * 1024  # 50MB limit for XML processing
XML_CONTENT_CHECK_BYTES = 1024
SUPPORTED_XML_EXTENSIONS = {".xml", ".html", ".htm", ".xhtml", ".svg", ".xsl", ".xslt"}

logger = logging.getLogger(__name__)


class XMLHandler(FileHandler):
    """Handler for processing XML and HTML files."""

    @classmethod
    def can_handle(cls: type["XMLHandler"], path: Path) -> bool:
        """Check if the path is an XML or HTML file.

        Args:
            path: The path to check.

        Returns:
            True if the path is an XML/HTML file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() in SUPPORTED_XML_EXTENSIONS:
            try:
                if path.stat().st_size == 0:
                    return False
            except OSError:
                return False  # Cannot stat, likely doesn't exist or permission error
            return True

        # Check by content
        try:
            with path.open("rb") as f:
                content_start = f.read(XML_CONTENT_CHECK_BYTES)
                if not content_start:
                    return False
                try:
                    content_text = content_start.decode("utf-8").strip()
                    # Look for XML declaration or common XML/HTML tags
                    content_lower = content_text.lower()
                    if (
                        content_text.startswith("<?xml")
                        or content_lower.startswith("<!doctype html")
                        or content_lower.startswith("<html")
                        or "</" in content_lower
                        and ">" in content_lower
                    ):
                        return True
                except UnicodeDecodeError:
                    pass
        except OSError:
            pass

        return False

    @classmethod
    def handle(cls: type["XMLHandler"], path: Path) -> None:
        """Display XML/HTML file using xmllint with fallbacks.

        Args:
            path: The XML/HTML file path to display.
        """
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                print("(Empty XML/HTML file)")
                return

            if file_size > MAX_XML_SIZE_BYTES:
                logger.warning(
                    f"XML/HTML file size ({file_size} bytes) exceeds limit "
                    f"({MAX_XML_SIZE_BYTES} bytes). "
                    f"Falling back to default viewer.",
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Try to use xmllint for formatting
            try:
                # First, try to format the XML/HTML
                xmllint_process = subprocess.Popen(
                    ["xmllint", "--format", "--encode", "UTF-8", str(path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Use smart_pager to handle the output
                smart_pager(xmllint_process, ["less", "-R"])

                # Check if xmllint process failed
                xmllint_retcode = xmllint_process.wait()
                if xmllint_retcode != 0:
                    # If formatting failed, try without formatting
                    cls._try_xmllint_without_format(path)

                return

            except FileNotFoundError:
                logger.warning(
                    "xmllint command not found. Install libxml2-utils package.",
                )
                cls._show_xml_info_and_content(path, file_size)
                return

            except subprocess.SubprocessError as e:
                logger.warning(f"xmllint failed: {e}")
                cls._show_xml_info_and_content(path, file_size)
                return

        except OSError as e:
            logger.error(
                f"Error accessing XML/HTML file: {e}",
            )
            # Fallback if we can't even get the file size
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def _try_xmllint_without_format(cls: type["XMLHandler"], path: Path) -> None:
        """Try xmllint without formatting (for validation only).

        Args:
            path: The XML/HTML file path.
        """
        try:
            # Try to validate without formatting
            result = subprocess.run(
                ["xmllint", "--noout", str(path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"XML/HTML File: {path.name} (Valid)")
                # Show the original content since formatting failed
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
            else:
                print(f"XML/HTML File: {path.name} (Validation errors)")
                if result.stderr:
                    print("Validation errors:")
                    print(result.stderr.strip())
                print("\nRaw content:")
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)

        except subprocess.SubprocessError:
            # If even validation fails, show raw content
            cls._show_xml_info_and_content(path, path.stat().st_size)

    @classmethod
    def _show_xml_info_and_content(cls: type["XMLHandler"], path: Path, file_size: int) -> None:
        """Show XML/HTML file information and raw content.

        Args:
            path: The XML/HTML file path.
            file_size: The file size in bytes.
        """
        print(f"XML/HTML File: {path.name}")

        # Determine file type based on extension
        ext = path.suffix.lower()
        if ext in {".html", ".htm", ".xhtml"}:
            print("Type: HTML document")
        elif ext == ".svg":
            print("Type: SVG image")
        elif ext in {".xsl", ".xslt"}:
            print("Type: XSLT stylesheet")
        else:
            print("Type: XML document")

        print(f"Size: {file_size:,} bytes")
        print("(Install 'libxml2-utils' for XML formatting and validation)")
        print("-" * 50)

        # Show raw content using default handler
        from l_command.handlers.default import DefaultFileHandler

        DefaultFileHandler.handle(path)

    @classmethod
    def priority(cls: type["XMLHandler"]) -> int:
        """Return the priority of the XML handler.

        Returns:
            45 (medium priority, lower than JSON).
        """
        return 45  # XML has priority lower than JSON but higher than default
