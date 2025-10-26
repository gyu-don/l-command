"""
Tests for MarkdownHandler.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from l_command.handlers.markdown import MarkdownHandler

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from pytest_mock import MockerFixture


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


def test_handle_empty_markdown(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling empty Markdown file."""
    md_file = tmp_path / "empty.md"
    md_file.touch()

    MarkdownHandler.handle(md_file)

    captured = capsys.readouterr()
    assert "(Empty Markdown file)" in captured.out


def test_handle_markdown_size_exceeds_limit(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling Markdown file that exceeds size limit."""
    from l_command.handlers.markdown import MAX_MARKDOWN_SIZE_BYTES

    md_file = tmp_path / "large.md"
    md_file.write_text("# Title\n\nContent")

    # Mock stat to return size over limit
    mock_stat = mocker.patch("pathlib.Path.stat")
    mock_stat_result = mocker.Mock()
    mock_stat_result.st_size = MAX_MARKDOWN_SIZE_BYTES + 1
    mock_stat.return_value = mock_stat_result

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    MarkdownHandler.handle(md_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(md_file)


def test_handle_markdown_with_glow(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling Markdown with glow renderer."""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Title\n\nSome **bold** text")

    # Mock glow command
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 0

    # Mock isatty
    mocker.patch("sys.stdout.isatty", return_value=False)

    MarkdownHandler.handle(md_file)

    # Verify glow was called
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "glow" in args[0]
    assert str(md_file) in args


def test_handle_markdown_with_mdcat(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling Markdown with mdcat (fallback from glow)."""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Title\n\nSome text")

    # Mock glow not available, mdcat available
    mock_popen = mocker.patch("subprocess.Popen")
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Mock smart_pager
    mock_pager = mocker.patch("l_command.handlers.markdown.smart_pager")

    # Mock run to fail for glow
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = FileNotFoundError("glow not found")

    MarkdownHandler.handle(md_file)

    # Verify mdcat was called
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert "mdcat" in args[0]


def test_handle_markdown_with_pandoc(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling Markdown with pandoc (fallback from glow and mdcat)."""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Title")

    # Mock glow not available
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = FileNotFoundError("not found")

    # Mock mdcat and pandoc available (both via Popen)
    call_count = 0

    def popen_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_process = mocker.Mock()
        mock_process.stdout = mocker.Mock()
        # First call (mdcat) fails, second call (pandoc) succeeds
        mock_process.wait.return_value = 1 if call_count == 1 else 0
        return mock_process

    mock_popen = mocker.patch("subprocess.Popen", side_effect=popen_side_effect)

    # Mock smart_pager
    mock_pager = mocker.patch("l_command.handlers.markdown.smart_pager")

    MarkdownHandler.handle(md_file)

    # Verify both mdcat and pandoc were called
    assert mock_popen.call_count == 2  # mdcat then pandoc


def test_handle_markdown_no_renderer(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling Markdown when no renderer is available."""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Title")

    # Mock all renderers not available
    mocker.patch("subprocess.run", side_effect=FileNotFoundError("not found"))
    mocker.patch("subprocess.Popen", side_effect=FileNotFoundError("not found"))

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    MarkdownHandler.handle(md_file)

    # Should fall back to showing source
    captured = capsys.readouterr()
    # The handler might print info before falling back
    # Verify DefaultFileHandler was eventually called
    assert mock_default.called


def test_handle_markdown_os_error(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling Markdown with OS error."""
    md_file = tmp_path / "error.md"
    md_file.write_text("# Title")

    # Mock stat to raise OSError
    mocker.patch.object(Path, "stat", side_effect=OSError("Permission denied"))

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    MarkdownHandler.handle(md_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(md_file)
