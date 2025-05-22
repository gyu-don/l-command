"""
Default handler for processing regular files.
"""

import logging
from pathlib import Path

from l_command.handlers.base import FileHandler
from l_command.utils import count_lines, smart_pager

logger = logging.getLogger(__name__)


class DefaultFileHandler(FileHandler):
    """Default handler for processing regular files."""

    @classmethod
    def can_handle(cls: type["DefaultFileHandler"], path: Path) -> bool:
        """Check if the path is a regular file.

        Args:
            path: The path to check.

        Returns:
            True if the path is a regular file, False otherwise.
        """
        return path.is_file()

    @classmethod
    def handle(cls: type["DefaultFileHandler"], path: Path) -> None:
        """Display file content using smart_pager.

        The choice between direct output and pager is handled by smart_pager
        based on the file's line count and the terminal's height.

        Args:
            path: The file path to display.
        """
        try:
            smart_pager(path)
        except Exception as e:
            logger.error(f"Error displaying file: {e}")

    @classmethod
    def priority(cls: type["DefaultFileHandler"]) -> int:
        """Return the priority of the default handler.

        Returns:
            0 (lowest priority).
        """
        return 0  # Lowest priority
