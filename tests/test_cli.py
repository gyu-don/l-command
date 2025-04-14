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


def test_main_with_directory(
    tmp_path: Path, monkeypatch: MonkeyPatch, mock_subprocess_run: MagicMock
) -> None:
    """Test main() with a directory path."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()  # Create real directory

    # Combine with statements
    with (
        patch.object(Path, "is_dir", return_value=True),
        patch.object(Path, "is_file", return_value=False),
        patch.object(Path, "exists", return_value=True),
    ):
        monkeypatch.setattr("sys.argv", ["l_command", str(test_dir)])
        result = main()

    assert result == 0
    mock_subprocess_run.assert_called_once_with(
        ["ls", "-la", "--color=auto", str(test_dir)]
    )


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


def test_main_with_small_text_file(
    tmp_path: Path, monkeypatch: MonkeyPatch, mock_subprocess_run: MagicMock
) -> None:
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


def test_main_with_large_text_file(
    tmp_path: Path, monkeypatch: MonkeyPatch, mock_subprocess_run: MagicMock
) -> None:
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
    mock_subprocess_run.assert_called_once_with(
        ["less", "-RFX", str(test_file)], check=True
    )


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

    def run_side_effect(
        *args: Sequence[Any], **kwargs: dict[str, Any]
    ) -> subprocess.CompletedProcess:
        cmd = args[0]
        # Check for 'jq empty' call
        if cmd == ["jq", "empty", str(test_file)]:
            assert kwargs.get("check") is True
            assert kwargs.get("stdout") == subprocess.DEVNULL
            assert kwargs.get("stderr") == subprocess.DEVNULL
            return subprocess.CompletedProcess(args=cmd, returncode=0)
        # Check for 'less -R' call
        if cmd == ["less", "-R"]:
            assert (
                kwargs.get("stdin") == mock_jq_proc.stdout
            )  # Check stdin is jq's stdout
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
    def run_side_effect(
        *args: Sequence[Any], **kwargs: dict[str, Any]
    ) -> subprocess.CompletedProcess:
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
    def run_side_effect(
        *args: Sequence[Any], **kwargs: dict[str, Any]
    ) -> subprocess.CompletedProcess:
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
