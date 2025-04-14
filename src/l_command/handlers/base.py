"""
Module defining the base class for file handlers.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class FileHandler(ABC):
    """Base class for handling different file types."""

    @classmethod
    @abstractmethod
    def can_handle(cls: type["FileHandler"], path: Path) -> bool:
        """Determine if this handler can process the path.

        Args:
            path: The path to check.

        Returns:
            True if this handler can process the path, False otherwise.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def handle(cls: type["FileHandler"], path: Path) -> None:
        """Process the path.

        Args:
            path: The path to process.
        """
        raise NotImplementedError

    @classmethod
    def priority(cls: type["FileHandler"]) -> int:
        """Return the priority of this handler (higher is evaluated first).

        Returns:
            The priority as an integer.
        """
        return 0
