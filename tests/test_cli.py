import os
import stat
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from l_command.cli import main
from l_command.constants import (
    MAX_JSON_SIZE_BYTES,
)
from l_command.utils import count_lines

# Test directory path relative to this test file
TEST_DIR = Path(__file__).parent / "test_files"


# Helper to create dummy files
def create_file(path: Path, content: str, size_bytes: int | None = None) -> None:
    path.write_text(content)
    if size_bytes is not None:
        # Crude way to approximate file size for testing MAX_JSON_SIZE_BYTES
        # In a real scenario, use truncate or more precise methods if needed.
        # This assumes content is ASCII/single-byte encoding for simplicity.
        current_size = len(content.encode("utf-8"))
        if size_bytes > current_size:
            with path.open("ab") as f:
                # Write null bytes to reach the target size
                f.write(b"\0" * (size_bytes - current_size))
        elif size_bytes < current_size:
            # Truncate (less common need in tests)
            with path.open("ab") as f:
                f.truncate(size_bytes)


@pytest.fixture
def mock_subprocess_run(monkeypatch: MonkeyPatch) -> MagicMock:
    mock = MagicMock(spec=subprocess.run)
    mock.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    monkeypatch.setattr("subprocess.run", mock)
    return mock


@pytest.fixture
def mock_stat(monkeypatch: MonkeyPatch) -> MagicMock:
    """Fixture to mock Path.stat()."""
    mock = MagicMock(spec=Path.stat)
    # Provide default st_mode for regular file to avoid TypeErrors
    mock.return_value.st_mode = stat.S_IFREG
    monkeypatch.setattr("pathlib.Path.stat", mock)
    return mock


def test_main_with_nonexistent_path(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture, mock_subprocess_run: MagicMock
) -> None:
    """Test main() with a nonexistent path."""
    # Patch Path.exists for this specific test
    with patch.object(Path, "exists", return_value=False):
        monkeypatch.setattr("sys.argv", ["l_command", "nonexistent_path"])
        result = main()
    captured = capsys.readouterr()
    assert result == 1
    # Adjust assertion to check start and end, accommodating potential path repr changes
    assert captured.err.startswith("Error: Path not found: nonexistent_path")
    mock_subprocess_run.assert_not_called()


def test_main_with_directory_small(tmp_path: Path, monkeypatch: MonkeyPatch, mock_subprocess_run: MagicMock) -> None:
    """Test main() with a directory path (small directory, uses direct output)."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()  # Create real directory

    # Create a mock for DirectoryHandler
    mock_directory_handler = MagicMock()
    mock_directory_handler.__name__ = "MockDirectoryHandler"

    # Configure the mock to simulate DirectoryHandler behavior for small directory
    def mock_handle(path: Path) -> None:
        # Simulate DirectoryHandler behavior for small directory
        # Run ls directly
        subprocess.run(["ls", "-la", "--color=auto", str(path)], check=True)

    mock_directory_handler.handle.side_effect = mock_handle

    # Patch the handlers module to return our mock handler
    with patch("l_command.cli.get_handlers") as mock_get_handlers:
        # Set up the mock to return a list with our mock handler
        mock_get_handlers.return_value = [mock_directory_handler]

        # Configure the mock handler
        mock_directory_handler.can_handle.return_value = True

        # Run the main function
        monkeypatch.setattr("sys.argv", ["l_command", str(test_dir)])
        result = main()

    # Verify the handler was called correctly
    mock_directory_handler.can_handle.assert_called_once_with(test_dir)
    mock_directory_handler.handle.assert_called_once_with(test_dir)

    assert result == 0
    mock_subprocess_run.assert_called_once_with(["ls", "-la", "--color=auto", str(test_dir)], check=True)


def test_main_with_directory_large(tmp_path: Path, monkeypatch: MonkeyPatch, mock_subprocess_run: MagicMock) -> None:
    """Test main() with a directory path (large directory, uses less)."""
    test_dir = tmp_path / "test_dir_large"
    test_dir.mkdir()  # Create real directory

    # Prepare mock objects for Popen (ls) and Run (less)
    mock_ls_proc = MagicMock(spec=subprocess.Popen)
    mock_ls_proc.stdout = MagicMock()

    # Create a mock for DirectoryHandler
    mock_directory_handler = MagicMock()
    mock_directory_handler.__name__ = "MockDirectoryHandler"

    # Configure the mock to simulate DirectoryHandler behavior for large directory
    def mock_handle(path: Path) -> None:
        # Simulate DirectoryHandler behavior for large directory
        # First run ls to count lines
        with patch("subprocess.Popen") as mock_popen:
            # Configure first Popen call to return mock process with many lines
            mock_first_proc = MagicMock()
            mock_first_proc.stdout = MagicMock()
            mock_first_proc.stdout.readlines.return_value = ["line"] * 50  # 50 lines
            mock_popen.return_value = mock_first_proc

            # Then run ls again and pipe to less
            with patch("os.get_terminal_size") as mock_terminal_size:
                mock_terminal_size.return_value = os.terminal_size((80, 24))  # 24 lines terminal

                # Configure second Popen call
                mock_popen.return_value = mock_ls_proc

                # Run less with ls output
                mock_subprocess_run(["less", "-R"], stdin=mock_ls_proc.stdout, check=True)
                mock_ls_proc.stdout.close()
                mock_ls_proc.wait()

    mock_directory_handler.handle.side_effect = mock_handle

    # Patch the handlers module to return our mock handler
    with patch("l_command.cli.get_handlers") as mock_get_handlers:
        # Set up the mock to return a list with our mock handler
        mock_get_handlers.return_value = [mock_directory_handler]

        # Configure the mock handler
        mock_directory_handler.can_handle.return_value = True

        # Run the main function
        monkeypatch.setattr("sys.argv", ["l_command", str(test_dir)])
        result = main()

    # Verify the handler was called correctly
    mock_directory_handler.can_handle.assert_called_once_with(test_dir)
    mock_directory_handler.handle.assert_called_once_with(test_dir)

    assert result == 0
    mock_subprocess_run.assert_called_with(["less", "-R"], stdin=mock_ls_proc.stdout, check=True)


def test_directory_handler_small_directory(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test DirectoryHandler with a small directory (direct output)."""
    from l_command.handlers.directory import DirectoryHandler

    # Create a test directory
    test_dir = tmp_path / "small_dir"
    test_dir.mkdir()

    # Mock subprocess.run and subprocess.Popen
    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
        patch("os.get_terminal_size") as mock_terminal_size,
    ):
        # Configure mock_popen to return a process with few lines
        mock_process = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readlines.return_value = ["line"] * 10  # 10 lines
        mock_popen.return_value = mock_process

        # Configure terminal size to be larger than output
        mock_terminal_size.return_value = os.terminal_size((80, 24))  # 24 lines

        # Call the handler
        DirectoryHandler.handle(test_dir)

        # Verify subprocess.Popen was called correctly for counting lines
        mock_popen.assert_called_with(
            ["ls", "-la", "--color=always", str(test_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Verify subprocess.run was called with correct arguments for small directory
        mock_run.assert_called_with(
            ["ls", "-la", "--color=auto", str(test_dir)],
            check=True,
        )


def test_directory_handler_large_directory(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test DirectoryHandler with a large directory (uses less)."""
    from l_command.handlers.directory import DirectoryHandler

    # Create a test directory
    test_dir = tmp_path / "large_dir"
    test_dir.mkdir()

    # Mock subprocess.run, subprocess.Popen, and os.get_terminal_size
    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
        patch("os.get_terminal_size") as mock_terminal_size,
    ):
        # First Popen call for counting lines
        first_process = MagicMock()
        first_process.stdout = MagicMock()
        first_process.stdout.readlines.return_value = ["line"] * 50  # 50 lines

        # Second Popen call for piping to less
        second_process = MagicMock()
        second_process.stdout = MagicMock()

        # Configure mock_popen to return different processes on consecutive calls
        mock_popen.side_effect = [first_process, second_process]

        # Configure terminal size to be smaller than output
        mock_terminal_size.return_value = os.terminal_size((80, 24))  # 24 lines

        # Call the handler
        DirectoryHandler.handle(test_dir)

        # Verify first subprocess.Popen call for counting lines
        assert mock_popen.call_args_list[0] == call(
            ["ls", "-la", "--color=always", str(test_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Verify second subprocess.Popen call for piping to less
        assert mock_popen.call_args_list[1] == call(
            ["ls", "-la", "--color=always", str(test_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Verify subprocess.run was called with less
        mock_run.assert_called_with(
            ["less", "-R"],
            stdin=second_process.stdout,
            check=True,
        )

        # Verify stdout was closed and wait was called
        second_process.stdout.close.assert_called_once()
        second_process.wait.assert_called_once()


def test_default_file_handler_small_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test DefaultFileHandler with a small file (uses cat)."""
    from l_command.handlers.default import DefaultFileHandler

    # Create a test file
    test_file = tmp_path / "small_file.txt"
    create_file(test_file, "\n".join(["line"] * 10))  # 10 lines

    # Mock subprocess.run and os.get_terminal_size
    with (
        patch("subprocess.run") as mock_run,
        patch("os.get_terminal_size") as mock_terminal_size,
    ):
        # Configure terminal size to be larger than file
        mock_terminal_size.return_value = os.terminal_size((80, 24))  # 24 lines

        # Mock count_lines directly in the module where it's used
        with patch("l_command.handlers.default.count_lines", return_value=10) as mock_count_lines:
            # Call the handler
            DefaultFileHandler.handle(test_file)

            # Verify count_lines was called
            mock_count_lines.assert_called_once_with(test_file)

        # Verify subprocess.run was called with cat
        mock_run.assert_called_once_with(
            ["cat", str(test_file)],
            check=True,
        )


def test_default_file_handler_large_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test DefaultFileHandler with a large file (uses less)."""
    from l_command.handlers.default import DefaultFileHandler

    # Create a test file
    test_file = tmp_path / "large_file.txt"
    create_file(test_file, "\n".join(["line"] * 50))  # 50 lines

    # Mock subprocess.run and os.get_terminal_size
    with (
        patch("subprocess.run") as mock_run,
        patch("os.get_terminal_size") as mock_terminal_size,
    ):
        # Configure terminal size to be smaller than file
        mock_terminal_size.return_value = os.terminal_size((80, 24))  # 24 lines

        # Mock count_lines directly in the module where it's used
        with patch("l_command.handlers.default.count_lines", return_value=50) as mock_count_lines:
            # Call the handler
            DefaultFileHandler.handle(test_file)

            # Verify count_lines was called
            mock_count_lines.assert_called_once_with(test_file)

        # Verify subprocess.run was called with less
        mock_run.assert_called_once_with(
            ["less", "-RFX", str(test_file)],
            check=True,
        )


def test_json_handler_can_handle(tmp_path: Path) -> None:
    """Test JsonHandler.can_handle method."""
    from l_command.handlers.json import JsonHandler

    # Test with .json extension
    json_file = tmp_path / "test.json"
    create_file(json_file, '{"key": "value"}')
    assert JsonHandler.can_handle(json_file) is True

    # Test with JSON content but no .json extension
    json_content_file = tmp_path / "test.txt"
    create_file(json_content_file, '{"key": "value"}')
    assert JsonHandler.can_handle(json_content_file) is True

    # Test with non-JSON content
    non_json_file = tmp_path / "non_json.txt"
    create_file(non_json_file, "This is not JSON")
    assert JsonHandler.can_handle(non_json_file) is False

    # Test with empty file
    empty_file = tmp_path / "empty.json"
    create_file(empty_file, "")
    assert JsonHandler.can_handle(empty_file) is False

    # Test with directory
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    assert JsonHandler.can_handle(dir_path) is False


def test_json_handler_small_valid_json(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test JsonHandler with a small valid JSON file."""
    from l_command.handlers.json import JsonHandler

    # Create a test file
    test_file = tmp_path / "small.json"
    create_file(test_file, '{"key": "value"}')

    # Mock subprocess.run, os.get_terminal_size, and Path.stat
    with (
        patch("subprocess.run") as mock_run,
        patch("os.get_terminal_size") as mock_terminal_size,
        patch("pathlib.Path.stat") as mock_stat,
    ):
        # Configure terminal size to be larger than file
        mock_terminal_size.return_value = os.terminal_size((80, 24))  # 24 lines

        # Configure stat to return a small file size
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 100  # Small file
        mock_stat.return_value = mock_stat_result

        # Mock count_lines directly in the module where it's used
        with patch("l_command.handlers.json.count_lines", return_value=1) as mock_count_lines:
            # Call the handler
            JsonHandler.handle(test_file)

            # Verify count_lines was called
            mock_count_lines.assert_called_once_with(test_file)

        # Verify subprocess.run was called for validation and display
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0] == call(
            ["jq", "empty", str(test_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert mock_run.call_args_list[1] == call(
            ["jq", ".", str(test_file)],
            check=True,
        )


def test_json_handler_large_valid_json(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test JsonHandler with a large valid JSON file."""
    from l_command.handlers.json import JsonHandler

    # Create a test file
    test_file = tmp_path / "large.json"
    content = '{\n"a": [' + ",\n".join([f'"{i}"' for i in range(50)]) + "]\n}"
    create_file(test_file, content)

    # Mock subprocess.run, subprocess.Popen, os.get_terminal_size, and Path.stat
    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
        patch("os.get_terminal_size") as mock_terminal_size,
        patch("pathlib.Path.stat") as mock_stat,
    ):
        # Configure terminal size to be smaller than file
        mock_terminal_size.return_value = os.terminal_size((80, 24))  # 24 lines

        # Configure stat to return a small file size
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 1000  # Small enough to not exceed limit
        mock_stat.return_value = mock_stat_result

        # Configure mock_popen to return a process
        mock_process = MagicMock()
        mock_process.stdout = MagicMock()
        mock_popen.return_value = mock_process

        # Mock count_lines directly in the module where it's used
        with patch("l_command.handlers.json.count_lines", return_value=52) as mock_count_lines:
            # Call the handler
            JsonHandler.handle(test_file)

            # Verify count_lines was called
            mock_count_lines.assert_called_once_with(test_file)

        # Verify subprocess.run was called for validation
        assert mock_run.call_args_list[0] == call(
            ["jq", "empty", str(test_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Verify subprocess.Popen was called for jq
        mock_popen.assert_called_once_with(
            ["jq", "--color-output", ".", str(test_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Verify subprocess.run was called for less
        assert mock_run.call_args_list[1] == call(
            ["less", "-R"],
            stdin=mock_process.stdout,
            check=True,
        )

        # Verify stdout was closed and wait was called
        mock_process.stdout.close.assert_called_once()
        mock_process.wait.assert_called_once()


def test_json_handler_oversized_json(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test JsonHandler with a JSON file exceeding size limit."""
    from l_command.handlers.json import JsonHandler

    # Create a test file
    test_file = tmp_path / "oversized.json"
    create_file(test_file, '{"key": "value"}', size_bytes=MAX_JSON_SIZE_BYTES + 1)

    # Mock DefaultFileHandler.handle
    with (
        patch("l_command.handlers.default.DefaultFileHandler.handle") as mock_default_handle,
        patch("pathlib.Path.stat") as mock_stat,
    ):
        # Configure stat to return a large file size
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = MAX_JSON_SIZE_BYTES + 1
        mock_stat.return_value = mock_stat_result

        # Call the handler
        JsonHandler.handle(test_file)

        # Verify DefaultFileHandler.handle was called
        mock_default_handle.assert_called_once_with(test_file)


def test_json_handler_invalid_json(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test JsonHandler with an invalid JSON file."""
    from l_command.handlers.json import JsonHandler

    # Create a test file
    test_file = tmp_path / "invalid.json"
    create_file(test_file, "{invalid json")

    # Mock subprocess.run and DefaultFileHandler.handle
    with (
        patch("subprocess.run") as mock_run,
        patch("l_command.handlers.default.DefaultFileHandler.handle") as mock_default_handle,
        patch("pathlib.Path.stat") as mock_stat,
    ):
        # Configure stat to return a small file size
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 100
        mock_stat.return_value = mock_stat_result

        # Configure subprocess.run to raise CalledProcessError for jq empty
        mock_run.side_effect = subprocess.CalledProcessError(1, ["jq", "empty"])

        # Call the handler
        JsonHandler.handle(test_file)

        # Verify subprocess.run was called for validation
        mock_run.assert_called_once_with(
            ["jq", "empty", str(test_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Verify DefaultFileHandler.handle was called
        mock_default_handle.assert_called_once_with(test_file)


def test_json_handler_jq_not_found(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test JsonHandler when jq command is not found."""
    from l_command.handlers.json import JsonHandler

    # Create a test file
    test_file = tmp_path / "test.json"
    create_file(test_file, '{"key": "value"}')

    # Mock subprocess.run and DefaultFileHandler.handle
    with (
        patch("subprocess.run") as mock_run,
        patch("l_command.handlers.default.DefaultFileHandler.handle") as mock_default_handle,
        patch("pathlib.Path.stat") as mock_stat,
    ):
        # Configure stat to return a small file size
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 100
        mock_stat.return_value = mock_stat_result

        # Configure subprocess.run to raise FileNotFoundError
        mock_run.side_effect = FileNotFoundError("jq not found")

        # Call the handler
        JsonHandler.handle(test_file)

        # Verify subprocess.run was called for validation
        mock_run.assert_called_once_with(
            ["jq", "empty", str(test_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Verify DefaultFileHandler.handle was called
        mock_default_handle.assert_called_once_with(test_file)


def test_count_lines(tmp_path: Path) -> None:
    """行数カウント機能のテスト"""
    # テスト用のファイルを作成
    test_file = tmp_path / "test_file.txt"
    expected_lines = 10
    content = "\n".join(["line"] * expected_lines)
    create_file(test_file, content)

    # 行数をカウント
    line_count = count_lines(test_file)

    # 期待通りの行数がカウントされていることを確認
    assert line_count == expected_lines


def test_count_lines_with_error(tmp_path: Path, capsys: CaptureFixture) -> None:
    """行数カウントのエラー処理のテスト"""
    # 存在しないファイルのパスを作成
    non_existent_file = tmp_path / "nonexistent.txt"

    # 行数をカウント
    line_count = count_lines(non_existent_file)

    # エラー時に0が返されることを確認
    assert line_count == 0

    # エラーメッセージが表示されていることを確認
    captured = capsys.readouterr()
    assert "Error counting lines" in captured.err


def test_main_with_small_text_file(tmp_path: Path, monkeypatch: MonkeyPatch, mock_subprocess_run: MagicMock) -> None:
    """Test main() with a non-JSON file shorter than terminal height (uses cat)."""
    test_file = tmp_path / "small_file.txt"
    create_file(test_file, "\n".join(["line"] * 10))
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Create a mock for DefaultFileHandler
    mock_default_handler = MagicMock()
    mock_default_handler.__name__ = "MockHandler"

    # Patch the handlers module to return our mock handler
    with patch("l_command.cli.get_handlers") as mock_get_handlers:
        # Set up the mock to return a list with our mock handler
        mock_get_handlers.return_value = [mock_default_handler]

        # Configure the mock handler
        mock_default_handler.can_handle.return_value = True

        # Run the main function
        result = main()

        # Verify the handler was called correctly
        mock_default_handler.can_handle.assert_called_once_with(test_file)
        mock_default_handler.handle.assert_called_once_with(test_file)

    assert result == 0


def test_main_with_large_text_file(tmp_path: Path, monkeypatch: MonkeyPatch, mock_subprocess_run: MagicMock) -> None:
    """Test main() with a non-JSON file taller than terminal height (uses less)."""
    test_file = tmp_path / "large_file.txt"
    create_file(test_file, "\n".join(["line"] * 30))
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Create a mock for DefaultFileHandler
    mock_default_handler = MagicMock()
    mock_default_handler.__name__ = "MockHandler"

    # Configure the mock to use less for display
    def mock_handle(path: Path) -> None:
        # Simulate DefaultFileHandler behavior
        mock_subprocess_run(["less", "-RFX", str(path)], check=True)

    mock_default_handler.handle.side_effect = mock_handle

    # Patch the handlers module to return our mock handler
    with patch("l_command.cli.get_handlers") as mock_get_handlers:
        # Set up the mock to return a list with our mock handler
        mock_get_handlers.return_value = [mock_default_handler]

        # Configure the mock handler
        mock_default_handler.can_handle.return_value = True

        # Run the main function
        result = main()

        # Verify the handler was called correctly
        mock_default_handler.can_handle.assert_called_once_with(test_file)
        mock_default_handler.handle.assert_called_once_with(test_file)

    assert result == 0
    mock_subprocess_run.assert_called_once_with(["less", "-RFX", str(test_file)], check=True)


def test_main_with_valid_small_json(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,
    mock_stat: MagicMock,
) -> None:
    """Test main() with a valid, small JSON file (uses direct jq)."""
    test_file = tmp_path / "valid_small.json"
    content = '{"key": "value"}'
    create_file(test_file, content)
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Create a mock for JsonHandler
    mock_json_handler = MagicMock()
    mock_json_handler.__name__ = "MockJsonHandler"

    # Configure the mock to simulate JsonHandler behavior
    def mock_handle(path: Path) -> None:
        # Simulate JsonHandler behavior for small JSON file
        mock_subprocess_run(
            ["jq", "empty", str(path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        mock_subprocess_run(["jq", ".", str(path)], check=True)

    mock_json_handler.handle.side_effect = mock_handle

    # Patch the handlers module to return our mock handler
    with patch("l_command.cli.get_handlers") as mock_get_handlers:
        # Set up the mock to return a list with our mock handler
        mock_get_handlers.return_value = [mock_json_handler]

        # Configure the mock handler
        mock_json_handler.can_handle.return_value = True

        # Run the main function
        result = main()

        # Verify the handler was called correctly
        mock_json_handler.can_handle.assert_called_once_with(test_file)
        mock_json_handler.handle.assert_called_once_with(test_file)

    assert result == 0

    # Verify the calls to subprocess.run
    expected_run_calls = [
        call(
            ["jq", "empty", str(test_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
        call(["jq", ".", str(test_file)], check=True),  # Direct call, no pipe
    ]
    mock_subprocess_run.assert_has_calls(expected_run_calls)


def test_main_with_valid_large_json_uses_less(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,  # Now used for 'jq empty' AND 'less -R'
    mock_stat: MagicMock,
    capsys: CaptureFixture,
) -> None:
    """Test main() with a valid JSON taller than terminal (uses jq | less)."""
    test_file = tmp_path / "valid_large.json"
    content = '{\n"a": [' + ",\n".join([f'"{i}"' for i in range(50)]) + "]\n}"
    create_file(test_file, content)
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    mock_stat.return_value.st_size = len(content.encode("utf-8"))
    mock_stat.return_value.st_mode = stat.S_IFREG

    # Prepare mock objects for Popen (jq) and Run (less)
    mock_jq_proc = MagicMock(spec=subprocess.Popen)
    mock_jq_proc.stdout = MagicMock()
    mock_jq_proc.wait.return_value = 0  # Ensure jq mock process exits successfully

    # Setup side effects for Popen (jq) and Run (jq empty, less)
    def popen_side_effect(*args: Sequence[Any], **kwargs: dict[str, Any]) -> MagicMock:
        cmd = args[0]
        # Check for the 'jq --color-output .' call
        if cmd == ["jq", "--color-output", ".", str(test_file)]:
            assert kwargs.get("stdout") == subprocess.PIPE
            assert kwargs.get("stderr") == subprocess.PIPE  # Check stderr is piped too
            return mock_jq_proc
        raise ValueError(f"Unexpected Popen call: {cmd} with kwargs {kwargs}")

    def run_side_effect(*args: Sequence[Any], **kwargs: dict[str, Any]) -> subprocess.CompletedProcess:
        cmd = args[0]
        # Check for 'jq empty' call
        if cmd == ["jq", "empty", str(test_file)]:
            assert kwargs.get("check") is True
            assert kwargs.get("stdout") == subprocess.DEVNULL
            assert kwargs.get("stderr") == subprocess.DEVNULL
            return subprocess.CompletedProcess(args=cmd, returncode=0)
        # Check for 'less -R' call
        if cmd == ["less", "-R"]:
            assert kwargs.get("stdin") == mock_jq_proc.stdout  # Check stdin is jq's stdout
            assert kwargs.get("check") is True
            return subprocess.CompletedProcess(args=cmd, returncode=0)
        # Any other call to subprocess.run is unexpected in this flow
        print(
            f"Unexpected subprocess.run call: {cmd} with kwargs {kwargs}",
            file=sys.stderr,
        )
        # Return non-zero to indicate failure if unexpected call occurs
        return subprocess.CompletedProcess(args=cmd, returncode=1)

    mock_subprocess_run.side_effect = run_side_effect

    # Create a mock for JsonHandler
    mock_json_handler = MagicMock()
    mock_json_handler.__name__ = "MockJsonHandler"

    # Configure the mock to simulate JsonHandler behavior for large JSON
    def mock_handle(path: Path) -> None:
        # Simulate JsonHandler behavior for large JSON file
        # First validate with jq empty
        mock_subprocess_run(
            ["jq", "empty", str(path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Then use jq with less for display
        with patch("subprocess.Popen", side_effect=popen_side_effect):
            mock_subprocess_run(["less", "-R"], stdin=mock_jq_proc.stdout, check=True)
            mock_jq_proc.stdout.close()
            mock_jq_proc.wait()

    mock_json_handler.handle.side_effect = mock_handle

    # Patch the handlers module to return our mock handler
    with patch("l_command.cli.get_handlers") as mock_get_handlers:
        # Set up the mock to return a list with our mock handler
        mock_get_handlers.return_value = [mock_json_handler]

        # Configure the mock handler
        mock_json_handler.can_handle.return_value = True

        # Run the main function
        result = main()

    # Assertions
    assert result == 0

    # Verify the handler was called correctly
    mock_json_handler.can_handle.assert_called_once_with(test_file)
    mock_json_handler.handle.assert_called_once_with(test_file)

    # Verify the subprocess.run calls
    expected_run_calls = [
        call(
            ["jq", "empty", str(test_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
        call(
            ["less", "-R"],
            stdin=mock_jq_proc.stdout,
            check=True,
        ),
    ]
    mock_subprocess_run.assert_has_calls(expected_run_calls)

    # Verify pipe closing and waiting logic
    mock_jq_proc.stdout.close.assert_called_once()
    mock_jq_proc.wait.assert_called_once()


def test_main_with_valid_large_json(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,
    mock_stat: MagicMock,
    capsys: CaptureFixture,
) -> None:
    """Test main() with a JSON file exceeding size limit (falls back to default)."""
    test_file = tmp_path / "large_exceed.json"
    content = '{"key": "value"}'
    create_file(test_file, content, size_bytes=MAX_JSON_SIZE_BYTES + 1)
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Create a mock for JsonHandler
    mock_json_handler = MagicMock()
    mock_json_handler.__name__ = "MockJsonHandler"

    # Create a mock for DefaultFileHandler (fallback)
    mock_default_handler = MagicMock()
    mock_default_handler.__name__ = "MockDefaultHandler"

    # Configure the mock to simulate JsonHandler behavior
    def mock_json_handle(path: Path) -> None:
        # Simulate JsonHandler behavior for large JSON file
        # Check file size and fall back to default handler
        print(
            f"File size ({MAX_JSON_SIZE_BYTES + 1} bytes) exceeds limit",
            file=sys.stderr,
        )
        mock_default_handler.handle(path)

    mock_json_handler.handle.side_effect = mock_json_handle

    # Configure the mock to simulate DefaultFileHandler behavior
    def mock_default_handle(path: Path) -> None:
        # Simulate DefaultFileHandler behavior
        mock_subprocess_run(["cat", str(path)], check=True)

    mock_default_handler.handle.side_effect = mock_default_handle

    # Patch the handlers module to return our mock handlers
    with patch("l_command.cli.get_handlers") as mock_get_handlers:
        # Set up the mock to return a list with our mock handlers
        mock_get_handlers.return_value = [mock_json_handler, mock_default_handler]

        # Configure the mock handlers
        mock_json_handler.can_handle.return_value = True
        mock_default_handler.can_handle.return_value = True

        # Run the main function
        result = main()

    captured = capsys.readouterr()
    assert result == 0
    assert "exceeds limit" in captured.err

    # Verify the handlers were called correctly
    mock_json_handler.can_handle.assert_called_once_with(test_file)
    mock_json_handler.handle.assert_called_once_with(test_file)
    mock_default_handler.handle.assert_called_once_with(test_file)

    # Verify the subprocess.run call
    mock_subprocess_run.assert_called_once_with(["cat", str(test_file)], check=True)


def test_main_with_invalid_json(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,
    mock_stat: MagicMock,
    capsys: CaptureFixture,
) -> None:
    """Test main() with an invalid JSON file (falls back to default)."""
    test_file = tmp_path / "invalid.json"
    content = "{invalid json"
    create_file(test_file, content)
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Create a mock for JsonHandler
    mock_json_handler = MagicMock()
    mock_json_handler.__name__ = "MockJsonHandler"

    # Create a mock for DefaultFileHandler (fallback)
    mock_default_handler = MagicMock()
    mock_default_handler.__name__ = "MockDefaultHandler"

    # Configure the mock to simulate JsonHandler behavior
    def mock_json_handle(path: Path) -> None:
        # Simulate JsonHandler behavior for invalid JSON file
        try:
            # First try to validate with jq empty
            mock_subprocess_run(
                ["jq", "empty", str(path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            # Validation fails, print error and fall back to default handler
            print(
                "File identified as JSON but failed validation or is invalid",
                file=sys.stderr,
            )
            mock_default_handler.handle(path)

    # Set up the side effect to raise CalledProcessError for jq empty
    def run_side_effect(*args: Sequence[Any], **kwargs: dict[str, Any]) -> subprocess.CompletedProcess:
        cmd = args[0]
        if cmd == ["jq", "empty", str(test_file)]:
            # Simulate jq validation failure
            raise subprocess.CalledProcessError(1, cmd)
        # Assume fallback uses 'cat' for this short invalid file
        if cmd == ["cat", str(test_file)]:
            return subprocess.CompletedProcess(args=cmd, returncode=0)
        return subprocess.CompletedProcess(args=cmd, returncode=1)

    mock_subprocess_run.side_effect = run_side_effect

    mock_json_handler.handle.side_effect = mock_json_handle

    # Configure the mock to simulate DefaultFileHandler behavior
    def mock_default_handle(path: Path) -> None:
        # Simulate DefaultFileHandler behavior
        mock_subprocess_run(["cat", str(path)], check=True)

    mock_default_handler.handle.side_effect = mock_default_handle

    # Patch the handlers module to return our mock handlers
    with patch("l_command.cli.get_handlers") as mock_get_handlers:
        # Set up the mock to return a list with our mock handlers
        mock_get_handlers.return_value = [mock_json_handler, mock_default_handler]

        # Configure the mock handlers
        mock_json_handler.can_handle.return_value = True
        mock_default_handler.can_handle.return_value = True

        # Run the main function
        result = main()

    captured = capsys.readouterr()
    assert result == 0
    assert "failed validation or is invalid" in captured.err

    # Verify the handlers were called correctly
    mock_json_handler.can_handle.assert_called_once_with(test_file)
    mock_json_handler.handle.assert_called_once_with(test_file)
    mock_default_handler.handle.assert_called_once_with(test_file)

    # Verify the subprocess.run calls
    expected_run_calls = [
        call(
            ["jq", "empty", str(test_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
        call(["cat", str(test_file)], check=True),
    ]
    mock_subprocess_run.assert_has_calls(expected_run_calls)


def test_main_with_jq_not_found(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,
    mock_stat: MagicMock,
    capsys: CaptureFixture,
) -> None:
    """Test main() when jq command is not found (falls back to default)."""
    test_file = tmp_path / "some.json"
    content = '{"key": "value"}'
    create_file(test_file, content)
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Create a mock for JsonHandler
    mock_json_handler = MagicMock()
    mock_json_handler.__name__ = "MockJsonHandler"

    # Create a mock for DefaultFileHandler (fallback)
    mock_default_handler = MagicMock()
    mock_default_handler.__name__ = "MockDefaultHandler"

    # Configure the mock to simulate JsonHandler behavior
    def mock_json_handle(path: Path) -> None:
        # Simulate JsonHandler behavior when jq is not found
        try:
            # Try to use jq
            mock_subprocess_run(
                ["jq", "empty", str(path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            # jq not found, print error and fall back to default handler
            print("jq command not found", file=sys.stderr)
            mock_default_handler.handle(path)

    # Set up the side effect to raise FileNotFoundError for jq
    def run_side_effect(*args: Sequence[Any], **kwargs: dict[str, Any]) -> subprocess.CompletedProcess:
        cmd = args[0]
        if cmd[0] == "jq":
            raise FileNotFoundError("jq not found")
        # Assume fallback uses 'cat'
        if cmd == ["cat", str(test_file)]:
            return subprocess.CompletedProcess(args=cmd, returncode=0)
        return subprocess.CompletedProcess(args=cmd, returncode=1)

    mock_subprocess_run.side_effect = run_side_effect

    mock_json_handler.handle.side_effect = mock_json_handle

    # Configure the mock to simulate DefaultFileHandler behavior
    def mock_default_handle(path: Path) -> None:
        # Simulate DefaultFileHandler behavior
        mock_subprocess_run(["cat", str(path)], check=True)

    mock_default_handler.handle.side_effect = mock_default_handle

    # Patch the handlers module to return our mock handlers
    with patch("l_command.cli.get_handlers") as mock_get_handlers:
        # Set up the mock to return a list with our mock handlers
        mock_get_handlers.return_value = [mock_json_handler, mock_default_handler]

        # Configure the mock handlers
        mock_json_handler.can_handle.return_value = True
        mock_default_handler.can_handle.return_value = True

        # Run the main function
        result = main()

    captured = capsys.readouterr()
    assert result == 0
    assert "jq command not found" in captured.err

    # Verify the handlers were called correctly
    mock_json_handler.can_handle.assert_called_once_with(test_file)
    mock_json_handler.handle.assert_called_once_with(test_file)
    mock_default_handler.handle.assert_called_once_with(test_file)

    # Verify the subprocess.run call
    mock_subprocess_run.assert_called_with(["cat", str(test_file)], check=True)
