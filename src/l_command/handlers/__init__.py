"""
Module for registering and retrieving file handlers.
"""

from l_command.handlers.archive import ArchiveHandler
from l_command.handlers.base import FileHandler
from l_command.handlers.binary import BinaryHandler
from l_command.handlers.csv import CSVHandler
from l_command.handlers.default import DefaultFileHandler
from l_command.handlers.directory import DirectoryHandler
from l_command.handlers.image import ImageHandler
from l_command.handlers.json import JsonHandler
from l_command.handlers.markdown import MarkdownHandler
from l_command.handlers.media import MediaHandler
from l_command.handlers.pdf import PDFHandler
from l_command.handlers.xml import XMLHandler
from l_command.handlers.yaml import YAMLHandler


def get_handlers() -> list[type[FileHandler]]:
    """Return all available handlers in priority order."""
    handlers: list[type[FileHandler]] = [
        DirectoryHandler,
        ImageHandler,
        PDFHandler,
        MediaHandler,
        JsonHandler,
        XMLHandler,
        CSVHandler,
        MarkdownHandler,
        YAMLHandler,
        ArchiveHandler,
        BinaryHandler,
        DefaultFileHandler,
    ]
    return sorted(handlers, key=lambda h: h.priority(), reverse=True)
