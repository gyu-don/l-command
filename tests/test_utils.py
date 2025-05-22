"""
Tests for the utils module.
"""

import io
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from l_command.utils import count_lines, smart_pager


def test_count_lines(tmp_path: Path) -> None:
    """Test count_lines function."""
    # Create a test file with known line count
    test_file = tmp_path / "test.txt"
    with open(test_file, "w") as f:
        f.write("line1\nline2\nline3\n")

    # Test count_lines
    assert count_lines(test_file) == 3


def test_count_lines_error(tmp_path: Path) -> None:
    """Test count_lines function with a non-existent file."""
    # Test with non-existent file
    non_existent = tmp_path / "non_existent.txt"
    with patch("sys.stderr", new=io.StringIO()) as fake_stderr:
        assert count_lines(non_existent) == 0
        assert "Error counting lines" in fake_stderr.getvalue()


def test_smart_pager_path(tmp_path: Path) -> None:
    """Test smart_pager with a Path."""
    test_file = tmp_path / "test.txt"
    with open(test_file, "w") as f:
        f.write("line1\nline2\n")

    with patch("sys.stdout.isatty", return_value=True):
        with patch("os.get_terminal_size") as mock_terminal_size:
            mock_terminal_size.return_value = os.terminal_size((80, 24))  # 24 lines
            with patch("l_command.utils._handle_file_with_pager") as mock_handle_file:
                smart_pager(test_file)
                mock_handle_file.assert_called_once()


def test_smart_pager_process() -> None:
    """Test smart_pager with a subprocess.Popen."""
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.stdout = MagicMock()
    mock_process.stdout.readline.side_effect = [b"line1\n", b"line2\n", b""]

    with patch("os.get_terminal_size") as mock_terminal_size:
        mock_terminal_size.return_value = os.terminal_size((80, 10))  # 10 lines
        with patch("sys.stdout") as mock_stdout:
            smart_pager(mock_process)
            mock_stdout.buffer.write.assert_called()


def test_smart_pager_not_tty() -> None:
    """Test smart_pager when stdout is not a TTY."""
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.stdout = MagicMock()

    with patch("sys.stdout.isatty", return_value=False):
        with patch("shutil.copyfileobj") as mock_copyfileobj:
            smart_pager(mock_process)
            mock_copyfileobj.assert_called_once()
