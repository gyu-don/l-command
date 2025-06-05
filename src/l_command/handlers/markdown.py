"""
Handler for processing Markdown files.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from l_command.handlers.base import FileHandler
from l_command.utils import count_lines, smart_pager

# Constants specific to Markdown handling
MAX_MARKDOWN_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit for Markdown processing
SUPPORTED_MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".mdx"}

logger = logging.getLogger(__name__)


class MarkdownHandler(FileHandler):
    """Handler for processing Markdown files."""

    @classmethod
    def can_handle(cls: type["MarkdownHandler"], path: Path) -> bool:
        """Check if the path is a Markdown file.

        Args:
            path: The path to check.

        Returns:
            True if the path is a Markdown file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() in SUPPORTED_MARKDOWN_EXTENSIONS:
            try:
                if path.stat().st_size == 0:
                    return False
            except OSError:
                return False  # Cannot stat, likely doesn't exist or permission error
            return True

        return False

    @classmethod
    def handle(cls: type["MarkdownHandler"], path: Path) -> None:
        """Display Markdown file with rendered or source view options.

        Args:
            path: The Markdown file path to display.
        """
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                print("(Empty Markdown file)")
                return

            if file_size > MAX_MARKDOWN_SIZE_BYTES:
                logger.warning(
                    f"Markdown file size ({file_size} bytes) exceeds limit "
                    f"({MAX_MARKDOWN_SIZE_BYTES} bytes). "
                    f"Falling back to default viewer.",
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Try different markdown renderers in order of preference
            if cls._try_glow(path) or cls._try_mdcat(path) or cls._try_pandoc(path):
                return
            else:
                # Fallback to showing source with syntax highlighting
                cls._show_markdown_source(path, file_size)

        except OSError as e:
            logger.error(
                f"Error accessing Markdown file: {e}",
            )
            # Fallback if we can't even get the file size
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def _try_glow(cls: type["MarkdownHandler"], path: Path) -> bool:
        """Try to render Markdown using glow.

        Args:
            path: The Markdown file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # If stdout is not a TTY, output directly without paging
            if not sys.stdout.isatty():
                subprocess.run(
                    ["glow", str(path)],
                    check=True,
                )
                return True

            # Get terminal height (same approach as smart_pager)
            try:
                terminal_height = os.get_terminal_size().lines
            except OSError:
                terminal_height = sys.maxsize  # Very large fallback if not in a terminal

            line_count = count_lines(path)

            if line_count > terminal_height:
                # Use glow with pager for long content
                subprocess.run(
                    ["glow", "-p", str(path)],
                    check=True,
                )
            else:
                # Use glow without pager for short content
                subprocess.run(
                    ["glow", str(path)],
                    check=True,
                )
            return True
        except FileNotFoundError:
            return False
        except subprocess.CalledProcessError:
            return False

    @classmethod
    def _try_mdcat(cls: type["MarkdownHandler"], path: Path) -> bool:
        """Try to render Markdown using mdcat.

        Args:
            path: The Markdown file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # mdcat provides good terminal markdown rendering
            mdcat_process = subprocess.Popen(
                ["mdcat", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Use smart_pager to handle the output
            smart_pager(mdcat_process, ["less", "-R"])

            # Check if mdcat process failed
            mdcat_retcode = mdcat_process.wait()
            return mdcat_retcode == 0
        except FileNotFoundError:
            return False
        except subprocess.SubprocessError:
            return False

    @classmethod
    def _try_pandoc(cls: type["MarkdownHandler"], path: Path) -> bool:
        """Try to render Markdown using pandoc.

        Args:
            path: The Markdown file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # pandoc can convert markdown to plain text with some formatting
            pandoc_process = subprocess.Popen(
                ["pandoc", "-f", "markdown", "-t", "plain", "--wrap=auto", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Use smart_pager to handle the output
            smart_pager(pandoc_process, ["less", "-R"])

            # Check if pandoc process failed
            pandoc_retcode = pandoc_process.wait()
            return pandoc_retcode == 0
        except FileNotFoundError:
            return False
        except subprocess.SubprocessError:
            return False

    @classmethod
    def _show_markdown_source(cls: type["MarkdownHandler"], path: Path, file_size: int) -> None:
        """Show Markdown file source with information.

        Args:
            path: The Markdown file path.
            file_size: The file size in bytes.
        """
        print(f"Markdown File: {path.name}")
        print(f"Size: {file_size:,} bytes")
        print("Rendering: Source view (install 'glow', 'mdcat', or 'pandoc' for rendered view)")
        print("-" * 50)

        # Try to use bat for syntax highlighting, fallback to cat
        try:
            bat_process = subprocess.Popen(
                ["bat", "--language=markdown", "--style=plain", "--paging=never", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Use smart_pager to handle the output
            smart_pager(bat_process, ["less", "-R"])

            # Check if bat process failed
            bat_retcode = bat_process.wait()
            if bat_retcode == 0:
                return
        except FileNotFoundError:
            pass
        except subprocess.SubprocessError:
            pass

        # Fallback to default handler
        from l_command.handlers.default import DefaultFileHandler

        DefaultFileHandler.handle(path)

    @classmethod
    def priority(cls: type["MarkdownHandler"]) -> int:
        """Return the priority of the Markdown handler.

        Returns:
            35 (medium priority, lower than CSV).
        """
        return 35  # Markdown has priority lower than CSV but higher than default
