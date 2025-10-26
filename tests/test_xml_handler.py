"""
Tests for XMLHandler.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from l_command.handlers.xml import XMLHandler

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from pytest_mock import MockerFixture


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


def test_handle_empty_xml(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling empty XML file."""
    xml_file = tmp_path / "empty.xml"
    xml_file.touch()

    XMLHandler.handle(xml_file)

    captured = capsys.readouterr()
    assert "(Empty XML/HTML file)" in captured.out


def test_handle_xml_size_exceeds_limit(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling XML file that exceeds size limit."""
    from l_command.handlers.xml import MAX_XML_SIZE_BYTES

    xml_file = tmp_path / "large.xml"
    xml_file.write_text("<root>content</root>")

    # Mock stat to return size over limit
    mock_stat = mocker.patch("pathlib.Path.stat")
    mock_stat_result = mocker.Mock()
    mock_stat_result.st_size = MAX_XML_SIZE_BYTES + 1
    mock_stat.return_value = mock_stat_result

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    XMLHandler.handle(xml_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(xml_file)


def test_handle_xml_with_xmllint(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling XML with xmllint formatter."""
    xml_file = tmp_path / "test.xml"
    xml_file.write_text("<?xml version='1.0'?><root><child>text</child></root>")

    # Mock xmllint available
    mock_popen = mocker.patch("subprocess.Popen")
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Mock smart_pager
    mock_pager = mocker.patch("l_command.handlers.xml.smart_pager")

    XMLHandler.handle(xml_file)

    # Verify xmllint was called
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert "xmllint" in args[0]
    assert "--format" in args


def test_handle_html_with_xmllint(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling HTML with xmllint."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<!DOCTYPE html><html><body><p>text</p></body></html>")

    # Mock xmllint available
    mock_popen = mocker.patch("subprocess.Popen")
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Mock smart_pager
    mock_pager = mocker.patch("l_command.handlers.xml.smart_pager")

    XMLHandler.handle(html_file)

    # Verify xmllint was called
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert "xmllint" in args[0]


def test_handle_xml_xmllint_format_failed(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling XML when xmllint formatting fails."""
    xml_file = tmp_path / "test.xml"
    xml_file.write_text("<root>content</root>")

    # Mock xmllint format failing
    mock_popen = mocker.patch("subprocess.Popen")
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mock_process.wait.return_value = 1  # Format failed
    mock_popen.return_value = mock_process

    # Mock smart_pager
    mock_pager = mocker.patch("l_command.handlers.xml.smart_pager")

    # Mock xmllint validate
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    XMLHandler.handle(xml_file)

    # Should show validation and content
    captured = capsys.readouterr()
    assert "XML/HTML File:" in captured.out or mock_default.called


def test_handle_xml_xmllint_not_found(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling XML when xmllint is not available."""
    xml_file = tmp_path / "test.xml"
    xml_file.write_text("<root>content</root>")

    # Mock xmllint not available
    mocker.patch("subprocess.Popen", side_effect=FileNotFoundError("xmllint not found"))

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    XMLHandler.handle(xml_file)

    # Should show info and raw content
    captured = capsys.readouterr()
    assert "XML/HTML File:" in captured.out or mock_default.called


def test_handle_svg_file(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling SVG file (XML variant)."""
    svg_file = tmp_path / "test.svg"
    svg_file.write_text('<svg xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="40"/></svg>')

    # Mock xmllint available
    mock_popen = mocker.patch("subprocess.Popen")
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Mock smart_pager
    mock_pager = mocker.patch("l_command.handlers.xml.smart_pager")

    XMLHandler.handle(svg_file)

    # Verify xmllint was called
    mock_popen.assert_called_once()


def test_handle_malformed_xml(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling malformed XML."""
    xml_file = tmp_path / "malformed.xml"
    xml_file.write_text("<root><unclosed>")

    # Mock xmllint failing
    mock_popen = mocker.patch("subprocess.Popen")
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mock_process.wait.return_value = 1
    mock_popen.return_value = mock_process

    # Mock smart_pager
    mock_pager = mocker.patch("l_command.handlers.xml.smart_pager")

    # Mock xmllint validate with error
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.returncode = 1
    mock_result.stderr = "parser error: Opening and ending tag mismatch"
    mock_run.return_value = mock_result

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    XMLHandler.handle(xml_file)

    # Should show validation errors
    captured = capsys.readouterr()
    assert "XML/HTML File:" in captured.out or "Validation errors" in captured.out or mock_default.called


def test_handle_xml_os_error(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling XML with OS error."""
    xml_file = tmp_path / "error.xml"
    xml_file.write_text("<root>content</root>")

    # Mock stat to raise OSError
    mocker.patch.object(Path, "stat", side_effect=OSError("Permission denied"))

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    XMLHandler.handle(xml_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(xml_file)
