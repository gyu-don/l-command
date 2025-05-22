"""
Handler for processing directories.
"""

import logging
import subprocess
from pathlib import Path

from l_command.handlers.base import FileHandler
from l_command.utils import smart_pager

logger = logging.getLogger(__name__)


class DirectoryHandler(FileHandler):
    """Handler for processing directories."""

    @classmethod
    def can_handle(cls: type["DirectoryHandler"], path: Path) -> bool:
        """Check if the path is a directory.

        Args:
            path: The path to check.

        Returns:
            True if the path is a directory, False otherwise.
        """
        return path.is_dir()

    @classmethod
    def handle(cls: type["DirectoryHandler"], path: Path) -> None:
        """Display directory contents using ls -la, with paging if needed.

        The choice between direct output and pager is handled by smart_pager
        based on the output's line count and the terminal's height.

        Args:
            path: The directory path to display.
        """
        try:
            # Run ls with color output
            ls_process = subprocess.Popen(
                ["ls", "-la", "--color=always", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Use smart_pager to handle the output
            smart_pager(ls_process, ["less", "-R"])

            # Check if ls process failed
            ls_retcode = ls_process.wait()
            if ls_retcode != 0:
                logger.error(f"ls process exited with code {ls_retcode}")

        except subprocess.SubprocessError as e:
            logger.error(f"Error displaying directory with ls: {e}")
        except OSError as e:
            logger.error(f"Error accessing directory: {e}")

    @classmethod
    def priority(cls: type["DirectoryHandler"]) -> int:
        """Return the priority of the directory handler.

        Returns:
            100 (highest priority).
        """
        return 100  # Directory has highest priority
