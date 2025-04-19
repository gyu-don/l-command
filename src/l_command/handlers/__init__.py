"""
Module for registering and retrieving file handlers.
"""

from l_command.handlers.archive import ArchiveHandler
from l_command.handlers.base import FileHandler
from l_command.handlers.binary import BinaryHandler
from l_command.handlers.default import DefaultFileHandler
from l_command.handlers.directory import DirectoryHandler
from l_command.handlers.json import JsonHandler


def get_handlers() -> list[type[FileHandler]]:
    """Return all available handlers in priority order."""
    handlers: list[type[FileHandler]] = [
        DirectoryHandler,
        JsonHandler,
        ArchiveHandler,
        BinaryHandler,
        DefaultFileHandler,
    ]
    return sorted(handlers, key=lambda h: h.priority(), reverse=True)
