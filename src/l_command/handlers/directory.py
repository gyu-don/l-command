"""
Handler for processing directories.
"""

import subprocess
from pathlib import Path

from l_command.handlers.base import FileHandler


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
        """Display directory contents using ls -la.

        Args:
            path: The directory path to display.
        """
        subprocess.run(["ls", "-la", "--color=auto", str(path)])

    @classmethod
    def priority(cls: type["DirectoryHandler"]) -> int:
        """Return the priority of the directory handler.

        Returns:
            100 (highest priority).
        """
        return 100  # Directory has highest priority
