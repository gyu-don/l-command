import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from l_command.handlers.binary import BinaryHandler

if TYPE_CHECKING:
    from unittest.mock import CaptureLog, MonkeyPatch


def create_binary_file(path: Path, content: bytes) -> None:
    path.write_bytes(content)


def create_text_file(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def test_can_handle_binary_and_text(tmp_path: Path) -> None:
    # バイナリファイル
    binary_file = tmp_path / "test.bin"
    create_binary_file(binary_file, b"\x00\x01\x02\x03")
    assert BinaryHandler.can_handle(binary_file) is True

    # テキストファイル
    text_file = tmp_path / "test.txt"
    create_text_file(text_file, "This is a text file.")
    assert BinaryHandler.can_handle(text_file) is False

    # 空ファイル
    empty_file = tmp_path / "empty.bin"
    create_binary_file(empty_file, b"")
    assert BinaryHandler.can_handle(empty_file) is False


def test_can_handle_with_file_command(tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
    # fileコマンドがbinaryを返す場合
    binary_file = tmp_path / "filecmd.bin"
    create_binary_file(binary_file, b"\x00\x01\x02")
    monkeypatch.setattr("shutil.which", lambda cmd: True if cmd == "file" else None)
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: MagicMock(stdout="binary\n", returncode=0))
    assert BinaryHandler.can_handle(binary_file) is True

    # fileコマンドがus-asciiを返す場合（内容はバイナリ）
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: MagicMock(stdout="us-ascii\n", returncode=0))
    assert BinaryHandler.can_handle(binary_file) is True  # fallbackでTrue


def test_handle_hexdump_and_less(tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
    # hexdump, lessが両方ある場合
    binary_file = tmp_path / "large.bin"
    create_binary_file(binary_file, b"\x00" * 1024)
    monkeypatch.setattr("shutil.which", lambda cmd: True)
    
    # Mock the Popen call for hexdump
    mock_hexdump_process = MagicMock()
    mock_hexdump_process.stdout = MagicMock()
    mock_hexdump_process.wait.return_value = 0
    
    with patch("subprocess.Popen", return_value=mock_hexdump_process) as mock_popen:
        # Mock the smart_pager function
        with patch("l_command.handlers.binary.smart_pager") as mock_pager:
            BinaryHandler.handle(binary_file)
            
            # Verify Popen was called with hexdump command
            mock_popen.assert_called_with(
                ["hexdump", "-C", str(binary_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            # Verify smart_pager was called with the process and less command
            mock_pager.assert_called_with(mock_hexdump_process, ["less", "-R"])


def test_handle_hexdump_not_found(tmp_path: Path, caplog: "CaptureLog") -> None:
    binary_file = tmp_path / "nofound.bin"
    create_binary_file(binary_file, b"\x00\x01")
    with patch("shutil.which", return_value=None):
        BinaryHandler.handle(binary_file)
    captured = caplog.records
    assert any("hexdump" in record.message for record in captured)


def test_handle_less_not_found(tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
    binary_file = tmp_path / "noles.bin"
    create_binary_file(binary_file, b"\x00" * 10)
    monkeypatch.setattr("shutil.which", lambda cmd: True if cmd == "hexdump" else None)
    
    # Mock the Popen call for hexdump
    mock_hexdump_process = MagicMock()
    mock_hexdump_process.stdout = MagicMock()
    mock_hexdump_process.wait.return_value = 0
    
    with patch("subprocess.Popen", return_value=mock_hexdump_process) as mock_popen:
        # Mock the smart_pager function
        with patch("l_command.handlers.binary.smart_pager") as mock_pager:
            BinaryHandler.handle(binary_file)
            
            # Verify Popen was called with hexdump command
            mock_popen.assert_called_with(
                ["hexdump", "-C", str(binary_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            # Verify smart_pager was called with the process and less command
            mock_pager.assert_called_with(mock_hexdump_process, ["less", "-R"])


def make_iterable_stdout(lines: list[str]) -> MagicMock:
    """Create a mock stdout object that can be iterated over line by line."""
    mock_stdout = MagicMock()
    mock_stdout.__iter__.return_value = iter(lines)
    # Mock the close method which might be called on the file-like object
    mock_stdout.close = MagicMock()
    return mock_stdout
