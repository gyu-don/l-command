"""
Tests for MarkdownHandler.
"""

import tempfile
from pathlib import Path

from l_command.handlers.markdown import MarkdownHandler


def test_can_handle_markdown_extensions() -> None:
    """Test Markdown handler detection by extension."""
    extensions = [".md", ".markdown", ".mdown", ".mkd", ".mdx"]

    for ext in extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, mode="w") as tmp:
            tmp.write("# Header\nSome **bold** text")
            tmp.flush()
            path = Path(tmp.name)
            assert MarkdownHandler.can_handle(path) is True, f"Failed for extension {ext}"

    # Non-Markdown extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert MarkdownHandler.can_handle(path) is False


def test_priority() -> None:
    """Test Markdown handler priority."""
    assert MarkdownHandler.priority() == 35
