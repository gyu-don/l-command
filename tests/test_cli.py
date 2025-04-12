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

from l_command.cli import (
    count_lines,
    main,
)
from l_command.constants import (
    MAX_JSON_SIZE_BYTES,
)

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
    file_lines = 10
    terminal_height = 24
    create_file(test_file, "\n".join(["line"] * file_lines))
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Patch count_lines and get_terminal_size
    with (
        patch("l_command.cli.count_lines", return_value=file_lines) as mock_count,
        patch("os.get_terminal_size") as mock_terminal_size,
    ):
        mock_terminal_size.return_value = os.terminal_size((80, terminal_height))
        result = main()

    assert result == 0
    mock_count.assert_called_once_with(test_file)
    mock_terminal_size.assert_called()
    mock_subprocess_run.assert_called_once_with(["cat", str(test_file)], check=True)


def test_main_with_large_text_file(
    tmp_path: Path, monkeypatch: MonkeyPatch, mock_subprocess_run: MagicMock
) -> None:
    """Test main() with a non-JSON file taller than terminal height (uses less)."""
    test_file = tmp_path / "large_file.txt"
    file_lines = 30
    terminal_height = 24
    create_file(test_file, "\n".join(["line"] * file_lines))
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Use parenthesis syntax for multiple patches
    with (
        patch("l_command.cli.count_lines", return_value=file_lines) as mock_count,
        patch("os.get_terminal_size") as mock_terminal_size,
    ):
        mock_terminal_size.return_value = os.terminal_size((80, terminal_height))
        result = main()

    assert result == 0
    mock_count.assert_called_once_with(test_file)
    mock_terminal_size.assert_called()
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
    file_lines = 1  # Define lines <= terminal height
    terminal_height = 24
    create_file(test_file, content)
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    mock_stat.return_value.st_size = len(content.encode("utf-8"))
    mock_stat.return_value.st_mode = stat.S_IFREG

    # Use parenthesis syntax for multiple patches
    with (
        patch("l_command.cli.count_lines", return_value=file_lines) as mock_count,
        patch("os.get_terminal_size") as mock_terminal_size,
    ):
        mock_terminal_size.return_value = os.terminal_size((80, terminal_height))

        # Mock subprocess.run side effect for 'jq empty' and 'jq .' calls
        def run_side_effect(
            *args: Sequence[Any], **kwargs: dict[str, Any]
        ) -> subprocess.CompletedProcess:
            cmd = args[0]
            if cmd == ["jq", "empty", str(test_file)]:
                return subprocess.CompletedProcess(args=cmd, returncode=0)
            if cmd == ["jq", ".", str(test_file)]:
                return subprocess.CompletedProcess(args=cmd, returncode=0)
            print(f"Unexpected subprocess.run call: {cmd}", file=sys.stderr)
            return subprocess.CompletedProcess(args=cmd, returncode=1)

        mock_subprocess_run.side_effect = run_side_effect

        result = main()

    assert result == 0
    mock_count.assert_called_once_with(test_file)
    mock_terminal_size.assert_called()  # Verify terminal size was checked

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
    file_lines = 52
    terminal_height = 24
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

    # Use parenthesis syntax for multiple patches
    with (
        patch("l_command.cli.count_lines", return_value=file_lines) as mock_count,
        patch("os.get_terminal_size") as mock_terminal_size,
        patch(
            "subprocess.Popen", side_effect=popen_side_effect
        ) as mock_popen,  # Patch Popen here
    ):
        mock_terminal_size.return_value = os.terminal_size((80, terminal_height))
        result = main()

    # Assertions remain largely the same, but check mock_subprocess_run calls now
    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""

    mock_count.assert_called_once_with(test_file)
    mock_terminal_size.assert_called()

    # Verify 'jq --color-output .' was called via Popen
    mock_popen.assert_called_once_with(
        ["jq", "--color-output", ".", str(test_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Verify 'jq empty' and 'less -R' were called via Run
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
    assert mock_subprocess_run.call_count == 2  # Ensure no other run calls

    # Verify pipe closing and waiting logic
    mock_jq_proc.stdout.close.assert_called_once()
    # mock_less_proc is no longer used, less is called via run
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

    # Mock stat to return large size
    mock_stat.return_value.st_size = MAX_JSON_SIZE_BYTES + 1
    mock_stat.return_value.st_mode = stat.S_IFREG

    # Define fallback_lines and terminal_height HERE
    fallback_lines = 5
    terminal_height = 24
    # Mock os.get_terminal_size for the fallback display_file_default
    # Use parenthesis syntax for multiple patches
    with (
        patch("os.get_terminal_size") as mock_terminal_size,
        patch("l_command.cli.count_lines", return_value=fallback_lines) as mock_count,
    ):
        mock_terminal_size.return_value = os.terminal_size((80, terminal_height))

        # Mock subprocess.run for the fallback 'cat' call
        def run_side_effect(
            *args: Sequence[Any], **kwargs: dict[str, Any]
        ) -> subprocess.CompletedProcess:
            cmd = args[0]
            if cmd == ["cat", str(test_file)]:
                return subprocess.CompletedProcess(args=cmd, returncode=0)
            print(
                f"Unexpected subprocess.run call in size fallback: {cmd}",
                file=sys.stderr,
            )
            return subprocess.CompletedProcess(args=cmd, returncode=1)

        mock_subprocess_run.side_effect = run_side_effect

        result = main()

    captured = capsys.readouterr()
    assert result == 0
    assert "exceeds limit" in captured.err
    # Check that display_file_default's mechanism (cat or less) was called
    # In this case, lines (5) < height (24), so 'cat' is expected
    mock_subprocess_run.assert_called_once_with(["cat", str(test_file)], check=True)
    mock_count.assert_called_once_with(test_file)
    mock_terminal_size.assert_called()


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

    mock_stat.return_value.st_size = len(content.encode("utf-8"))
    mock_stat.return_value.st_mode = stat.S_IFREG

    # Mock subprocess for jq empty (fails) and fallback (cat/less)
    def run_side_effect(
        *args: Sequence[Any],
        **kwargs: dict[str, Any],
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

    # Mock os.get_terminal_size and count_lines for the fallback
    with (
        patch("os.get_terminal_size") as mock_terminal_size,
        patch("l_command.cli.count_lines", return_value=1) as mock_count,
    ):
        # Provide both lines and columns for the mock
        mock_terminal_size.return_value = os.terminal_size((80, 24))
        result = main()

    captured = capsys.readouterr()
    assert result == 0
    assert "failed validation or is invalid" in captured.err
    # Check that fallback mechanism (cat) was called
    # Need to check calls carefully due to side effect raising error
    assert mock_subprocess_run.call_count == 2
    # First call is jq empty
    assert mock_subprocess_run.call_args_list[0] == call(
        ["jq", "empty", str(test_file)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Second call is the fallback (cat)
    assert mock_subprocess_run.call_args_list[1] == call(
        ["cat", str(test_file)], check=True
    )
    mock_count.assert_called_once_with(test_file)
    mock_terminal_size.assert_called()


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

    mock_stat.return_value.st_size = len(content.encode("utf-8"))
    mock_stat.return_value.st_mode = stat.S_IFREG

    # Mock subprocess to raise FileNotFoundError for jq
    def run_side_effect(
        *args: Sequence[Any],
        **kwargs: dict[str, Any],
    ) -> subprocess.CompletedProcess:
        cmd = args[0]
        if cmd[0] == "jq":
            raise FileNotFoundError("jq not found")
        # Assume fallback uses 'cat'
        if cmd == ["cat", str(test_file)]:
            return subprocess.CompletedProcess(args=cmd, returncode=0)
        return subprocess.CompletedProcess(args=cmd, returncode=1)

    mock_subprocess_run.side_effect = run_side_effect

    # Mock os.get_terminal_size and count_lines for the fallback
    with (
        patch("os.get_terminal_size") as mock_terminal_size,
        patch("l_command.cli.count_lines", return_value=1) as mock_count,
    ):
        # Provide both lines and columns for the mock
        mock_terminal_size.return_value = os.terminal_size((80, 24))
        result = main()

    captured = capsys.readouterr()
    assert result == 0
    assert "jq command not found" in captured.err
    # Check that fallback mechanism (cat) was called
    mock_subprocess_run.assert_called_with(["cat", str(test_file)], check=True)
    mock_count.assert_called_once_with(test_file)
    mock_terminal_size.assert_called()
