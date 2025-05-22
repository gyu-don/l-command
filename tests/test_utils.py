"""
Tests for the utils module.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from l_command.utils import count_lines, smart_pager


def test_count_lines(tmp_path: Path) -> None:
    """Test count_lines function."""
    # Create a test file with known content
    test_file = tmp_path / "test_file.txt"
    with test_file.open("w") as f:
        f.write("line1\nline2\nline3\n")

    # Test counting lines
    line_count = 3
    assert count_lines(test_file) == line_count


def test_count_lines_empty_file(tmp_path: Path) -> None:
    """Test count_lines function with an empty file."""
    # Create an empty test file
    test_file = tmp_path / "empty_file.txt"
    test_file.open("w").close()

    # Test counting lines in an empty file
    assert count_lines(test_file) == 0


def test_smart_pager_with_file(tmp_path: Path) -> None:
    """Test smart_pager with a file."""
    # Create a small test file
    test_file = tmp_path / "small_file.txt"
    with test_file.open("w") as f:
        f.write("line1\nline2\n")

    with (
        patch("sys.stdout.isatty", return_value=True),
        patch("os.get_terminal_size") as mock_terminal_size,
        patch("l_command.utils._handle_file_with_pager") as mock_handle_file,
    ):
        mock_terminal_size.return_value = os.terminal_size((80, 24))  # 24 lines
        smart_pager(test_file)
        # For small files, pager should not be used
        mock_handle_file.assert_called_once_with(test_file, 24, ["less", "-RFX"])


def test_smart_pager_with_process() -> None:
    """Test smart_pager with a subprocess.Popen object."""
    # Create a mock process
    mock_process = MagicMock()
    mock_process.stdout = MagicMock()

    with patch("sys.stdout.isatty", return_value=False), \
         patch("shutil.copyfileobj") as mock_copyfileobj:
        smart_pager(mock_process)
        mock_copyfileobj.assert_called_once()
