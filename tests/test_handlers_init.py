"""Tests for handler registry integration with configuration."""

from l_command.config import Config, HandlerConfig
from l_command.handlers import get_handlers
from l_command.handlers.archive import ArchiveHandler
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


def test_get_handlers_with_default_config() -> None:
    """Test get_handlers with default configuration."""
    handlers = get_handlers()
    assert len(handlers) == 12

    # Check that all handlers are present
    handler_classes = set(handlers)
    assert DirectoryHandler in handler_classes
    assert ArchiveHandler in handler_classes
    assert ImageHandler in handler_classes
    assert PDFHandler in handler_classes
    assert BinaryHandler in handler_classes
    assert MediaHandler in handler_classes
    assert JsonHandler in handler_classes
    assert XMLHandler in handler_classes
    assert CSVHandler in handler_classes
    assert MarkdownHandler in handler_classes
    assert YAMLHandler in handler_classes
    assert DefaultFileHandler in handler_classes


def test_get_handlers_priority_order() -> None:
    """Test that handlers are returned in priority order."""
    handlers = get_handlers()

    # DirectoryHandler should be first (priority 100)
    assert handlers[0] == DirectoryHandler

    # DefaultFileHandler should be last (priority 0)
    assert handlers[-1] == DefaultFileHandler


def test_get_handlers_with_disabled_handler() -> None:
    """Test get_handlers when a handler is disabled."""
    config = Config.default()
    config.handlers["json"] = HandlerConfig(enabled=False, priority=50)

    handlers = get_handlers(config)

    # JSON handler should not be in the list
    assert JsonHandler not in handlers
    assert len(handlers) == 11


def test_get_handlers_with_multiple_disabled_handlers() -> None:
    """Test get_handlers with multiple disabled handlers."""
    config = Config.default()
    config.handlers["json"] = HandlerConfig(enabled=False)
    config.handlers["pdf"] = HandlerConfig(enabled=False)
    config.handlers["image"] = HandlerConfig(enabled=False)

    handlers = get_handlers(config)

    assert JsonHandler not in handlers
    assert PDFHandler not in handlers
    assert ImageHandler not in handlers
    assert len(handlers) == 9


def test_get_handlers_with_custom_priority() -> None:
    """Test get_handlers with custom priority values."""
    config = Config.default()
    # Make JSON handler have highest priority
    config.handlers["json"] = HandlerConfig(enabled=True, priority=150)

    handlers = get_handlers(config)

    # JSON handler should now be first (higher than Directory's 100)
    assert handlers[0] == JsonHandler


def test_get_handlers_with_swapped_priorities() -> None:
    """Test get_handlers with swapped priorities."""
    config = Config.default()
    # Swap JSON and PDF priorities
    config.handlers["json"] = HandlerConfig(enabled=True, priority=60)
    config.handlers["pdf"] = HandlerConfig(enabled=True, priority=50)

    handlers = get_handlers(config)

    # Find positions
    json_pos = handlers.index(JsonHandler)
    pdf_pos = handlers.index(PDFHandler)

    # JSON should come before PDF now
    assert json_pos < pdf_pos


def test_get_handlers_priority_preserved_when_not_specified() -> None:
    """Test that default priority is used when not specified in config."""
    config = Config.default()
    # Only change enabled status, not priority
    config.handlers["json"] = HandlerConfig(enabled=True, priority=None)

    handlers = get_handlers(config)

    # JSON handler should still be present and in roughly the same position
    assert JsonHandler in handlers

    # Check that it's still around the middle (default priority 50)
    json_pos = handlers.index(JsonHandler)
    assert 3 < json_pos < 9  # Should be in the middle range


def test_get_handlers_with_handler_options() -> None:
    """Test that handler options are preserved (even if not used yet)."""
    config = Config.default()
    config.handlers["json"] = HandlerConfig(enabled=True, priority=50, options={"jq_args": ["--indent", "2"]})

    handlers = get_handlers(config)

    # Handlers should still work normally
    assert JsonHandler in handlers

    # Options are stored in config (not used by handlers yet in Phase 1)
    assert config.handlers["json"].options == {"jq_args": ["--indent", "2"]}


def test_get_handlers_all_disabled_except_default() -> None:
    """Test get_handlers with all handlers disabled except default."""
    config = Config.default()
    for handler_name in config.handlers:
        if handler_name not in ["directory", "default"]:
            config.handlers[handler_name] = HandlerConfig(enabled=False)

    handlers = get_handlers(config)

    # Should only have Directory and Default handlers
    assert len(handlers) == 2
    assert DirectoryHandler in handlers
    assert DefaultFileHandler in handlers


def test_get_handlers_no_config_parameter() -> None:
    """Test that get_handlers works without config parameter."""
    handlers = get_handlers(None)
    assert len(handlers) == 12


def test_get_handlers_maintains_handler_map_completeness() -> None:
    """Test that all handlers in default config are in the handler map."""
    config = Config.default()
    handlers = get_handlers(config)

    # All 12 default handlers should be retrieved
    assert len(handlers) == 12
