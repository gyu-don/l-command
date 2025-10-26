"""
Tests for XMLHandler.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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


@patch("subprocess.Popen")
def test_xmllint_timeout_handling(mock_popen: MagicMock) -> None:
    """Test that xmllint timeout is handled gracefully."""
    # Create a mock process that will timeout on wait()
    mock_process = MagicMock()
    mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="xmllint", timeout=30)
    mock_process.stdout = None
    mock_process.stderr = None
    mock_popen.return_value = mock_process

    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w") as tmp:
        tmp.write("<root>content</root>")
        tmp.flush()
        path = Path(tmp.name)

        # Should not raise an exception
        XMLHandler.handle(path)

        # Verify process.kill was called after timeout
        assert mock_process.kill.called
