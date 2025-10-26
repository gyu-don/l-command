"""
Module for registering and retrieving file handlers.
"""

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from l_command.config import Config


def get_handlers(config: "Config | None" = None) -> list[type[FileHandler]]:
    """Return all available handlers in priority order.

    Args:
        config: Configuration object. If None, use default configuration.

    Returns:
        List of enabled handlers sorted by priority (highest first).
    """
    if config is None:
        from l_command.config import Config

        config = Config.default()

    # Handler name to class mapping
    handler_map: dict[str, type[FileHandler]] = {
        "directory": DirectoryHandler,
        "archive": ArchiveHandler,
        "image": ImageHandler,
        "pdf": PDFHandler,
        "binary": BinaryHandler,
        "media": MediaHandler,
        "json": JsonHandler,
        "xml": XMLHandler,
        "csv": CSVHandler,
        "markdown": MarkdownHandler,
        "yaml": YAMLHandler,
        "default": DefaultFileHandler,
    }

    # Filter enabled handlers
    enabled_handlers: list[type[FileHandler]] = []
    for name, handler_class in handler_map.items():
        handler_config = config.handlers.get(name)
        if handler_config is None or handler_config.enabled:
            enabled_handlers.append(handler_class)

    # Sort by priority
    def get_priority(handler_class: type[FileHandler]) -> int:
        # Convert class name to handler name (e.g., "JsonHandler" -> "json")
        handler_name = handler_class.__name__.replace("Handler", "").lower()
        # Handle special case for DefaultFileHandler
        if handler_name == "defaultfile":
            handler_name = "default"
        handler_config = config.handlers.get(handler_name)
        if handler_config and handler_config.priority is not None:
            return handler_config.priority
        return handler_class.priority()

    return sorted(enabled_handlers, key=get_priority, reverse=True)
