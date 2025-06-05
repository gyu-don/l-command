"""
Tests for XMLHandler.
"""

import tempfile
from pathlib import Path

from l_command.handlers.xml import XMLHandler


def test_can_handle_xml_extensions() -> None:
    """Test XML handler detection by extension."""
    extensions = [".xml", ".html", ".htm", ".xhtml", ".svg", ".xsl", ".xslt"]

    for ext in extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, mode="w") as tmp:
            tmp.write("<root>content</root>")  # Write some XML content
            tmp.flush()
            path = Path(tmp.name)
            assert XMLHandler.can_handle(path) is True, f"Failed for extension {ext}"

    # Non-XML extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert XMLHandler.can_handle(path) is False


def test_can_handle_xml_content() -> None:
    """Test XML handler detection by content."""
    # XML declaration
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("<?xml version='1.0'?><root></root>")
        tmp.flush()
        path = Path(tmp.name)
        assert XMLHandler.can_handle(path) is True

    # HTML DOCTYPE
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("<!doctype html><html></html>")
        tmp.flush()
        path = Path(tmp.name)
        assert XMLHandler.can_handle(path) is True

    # HTML tag
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("<html><body>content</body></html>")
        tmp.flush()
        path = Path(tmp.name)
        assert XMLHandler.can_handle(path) is True

    # Non-XML content
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("This is not XML or HTML")
        tmp.flush()
        path = Path(tmp.name)
        assert XMLHandler.can_handle(path) is False


def test_priority() -> None:
    """Test XML handler priority."""
    assert XMLHandler.priority() == 45
