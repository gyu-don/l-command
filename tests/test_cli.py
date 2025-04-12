import stat
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from l_command.cli import count_lines, main
from l_command.constants import LINE_THRESHOLD, MAX_JSON_SIZE_BYTES


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
    with patch.object(Path, "is_dir", return_value=True), patch.object(
        Path, "is_file", return_value=False
    ), patch.object(Path, "exists", return_value=True):
        monkeypatch.setattr("sys.argv", ["l_command", str(test_dir)])
        result = main()

    assert result == 0
    mock_subprocess_run.assert_called_once_with(
        ["ls", "-la", "--color=auto", str(test_dir)]
    )


def test_main_with_small_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """閾値以下の行数のファイルを指定した場合のテスト"""
    # テスト用のファイルを作成（閾値以下の行数）
    test_file = tmp_path / "small_file.txt"
    content = "\n".join(["line"] * (LINE_THRESHOLD - 1))
    test_file.write_text(content)

    # コマンドライン引数をモック
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # main関数を実行
    result = main()

    # 戻り値が0（成功）であることを確認
    assert result == 0


def test_main_with_large_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """閾値を超える行数のファイルを指定した場合のテスト"""
    # テスト用のファイルを作成（閾値を超える行数）
    test_file = tmp_path / "large_file.txt"
    content = "\n".join(["line"] * (LINE_THRESHOLD + 1))
    test_file.write_text(content)

    # コマンドライン引数をモック
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # main関数を実行
    result = main()

    # 戻り値が0（成功）であることを確認
    assert result == 0


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
    """Test main() with a small non-JSON file (uses cat)."""
    test_file = tmp_path / "small_file.txt"
    create_file(test_file, "line1\nline2")
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Patch count_lines for this execution
    with patch("l_command.cli.count_lines", return_value=2) as mock_count:
        # Ensure Path methods work correctly on the real temp file
        # No need to mock is_dir/is_file for real files
        result = main()

    assert result == 0
    # count_lines should be called with a Path object pointing to test_file
    mock_count.assert_called_once()
    assert mock_count.call_args[0][0] == test_file
    mock_subprocess_run.assert_called_once_with(["cat", str(test_file)], check=True)


def test_main_with_large_text_file(
    tmp_path: Path, monkeypatch: MonkeyPatch, mock_subprocess_run: MagicMock
) -> None:
    """Test main() with a large non-JSON file (uses less)."""
    test_file = tmp_path / "large_file.txt"
    create_file(test_file, "many lines...")
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    with patch(
        "l_command.cli.count_lines", return_value=LINE_THRESHOLD + 1
    ) as mock_count:
        result = main()

    assert result == 0
    mock_count.assert_called_once()
    assert mock_count.call_args[0][0] == test_file
    mock_subprocess_run.assert_called_once_with(
        ["less", "-RFX", str(test_file)], check=True
    )


def test_main_with_valid_small_json(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,
    mock_stat: MagicMock,
) -> None:
    """Test main() with a valid small JSON file."""
    test_file = tmp_path / "valid_small.json"
    content = '{"key": "value"}'
    create_file(test_file, content)
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Set the size via mock_stat
    mock_stat.return_value.st_size = 100
    # st_mode is already set to S_IFREG by the fixture

    # Rely on default successful mock return for subprocess
    result = main()

    assert result == 0
    expected_calls = [
        call(
            ["jq", "empty", str(test_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
        call(["jq", ".", str(test_file)], check=True),
    ]
    mock_subprocess_run.assert_has_calls(expected_calls)


def test_main_with_valid_large_json(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,
    mock_stat: MagicMock,
    capsys: CaptureFixture,
) -> None:
    """Test main() with a valid large JSON file (falls back to default)."""
    test_file = tmp_path / "valid_large.json"
    create_file(test_file, '{"data": [1, 2, 3]}')
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # Set large size via mock_stat
    mock_stat.return_value.st_size = MAX_JSON_SIZE_BYTES + 1

    fallback_cmd_base = ["cat"]
    fallback_args = fallback_cmd_base + [str(test_file)]

    # Refine type hints for side_effect function
    def run_side_effect(
        *args: Sequence[Any],
        **kwargs: dict[str, Any],
    ) -> subprocess.CompletedProcess:
        cmd = args[0]
        if cmd == fallback_args:
            return subprocess.CompletedProcess(args=cmd, returncode=0)
        pytest.fail(f"Unexpected subprocess call: {cmd}")

    mock_subprocess_run.side_effect = run_side_effect

    # Patch count_lines for the fallback call
    with patch("l_command.cli.count_lines", return_value=10) as mock_count:
        result = main()

    captured = capsys.readouterr()
    assert result == 0
    assert "File size" in captured.err
    assert "Falling back to default viewer" in captured.err
    mock_count.assert_called_once_with(test_file)
    expected_fallback_call = call(fallback_args, check=True)
    mock_subprocess_run.assert_has_calls([expected_fallback_call])
    assert mock_subprocess_run.call_count == 1


def test_main_with_invalid_json(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,
    mock_stat: MagicMock,
    capsys: CaptureFixture,
) -> None:
    """Test main() with an invalid JSON file (falls back to default)."""
    test_file = tmp_path / "invalid.json"
    create_file(test_file, '{"key": value_no_quotes}')

    # Fix: Use mock_stat for size, remove mock_path logic
    mock_stat.return_value.st_size = 100

    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    fallback_cmd_base = ["cat"]
    fallback_args = fallback_cmd_base + [str(test_file)]
    jq_empty_args = ["jq", "empty", str(test_file)]

    # Refine type hints for side_effect function
    def run_side_effect(
        *args: Sequence[Any],
        **kwargs: dict[str, Any],
    ) -> subprocess.CompletedProcess:
        cmd = args[0]
        if cmd == jq_empty_args:
            raise subprocess.CalledProcessError(1, cmd)
        elif cmd == fallback_args:
            return subprocess.CompletedProcess(args=cmd, returncode=0)
        pytest.fail(f"Unexpected subprocess call: {cmd}")

    mock_subprocess_run.side_effect = run_side_effect

    with patch("l_command.cli.count_lines", return_value=10) as mock_count:
        result = main()

    captured = capsys.readouterr()
    assert result == 0
    assert "failed validation or is invalid" in captured.err
    assert "Falling back to default viewer" in captured.err
    mock_count.assert_called_once_with(test_file)
    expected_calls = [
        call(
            jq_empty_args,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
        call(fallback_args, check=True),
    ]
    mock_subprocess_run.assert_has_calls(expected_calls)


def test_main_with_jq_not_found(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    mock_subprocess_run: MagicMock,
    mock_stat: MagicMock,
    capsys: CaptureFixture,
) -> None:
    """Test main() when jq command is not found (falls back to default)."""
    test_file = tmp_path / "some.json"
    create_file(test_file, '{"a": 1}')

    # Fix: Use mock_stat for size, remove mock_path logic
    mock_stat.return_value.st_size = 100

    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    fallback_cmd_base = ["cat"]
    fallback_args = fallback_cmd_base + [str(test_file)]
    jq_empty_args = ["jq", "empty", str(test_file)]

    # Refine type hints for side_effect function
    def run_side_effect(
        *args: Sequence[Any],
        **kwargs: dict[str, Any],
    ) -> subprocess.CompletedProcess:
        cmd = args[0]
        if cmd == jq_empty_args:
            if mock_subprocess_run.call_count == 1:
                raise FileNotFoundError("[Errno 2] No such file or directory: 'jq'")
            else:
                pytest.fail(f"jq empty called unexpectedly again: {cmd}")
        elif cmd == fallback_args:
            return subprocess.CompletedProcess(args=cmd, returncode=0)
        pytest.fail(f"Unexpected subprocess call: {cmd}")

    mock_subprocess_run.side_effect = run_side_effect

    with patch("l_command.cli.count_lines", return_value=10) as mock_count:
        result = main()

    captured = capsys.readouterr()
    assert result == 0
    assert "jq command not found" in captured.err
    assert "Falling back to default viewer" in captured.err
    mock_count.assert_called_once_with(test_file)
    expected_calls = [
        call(
            jq_empty_args,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
        call(fallback_args, check=True),
    ]
    mock_subprocess_run.assert_has_calls(expected_calls)
