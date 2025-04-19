from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from l_command.handlers.binary import BinaryHandler

if TYPE_CHECKING:
    from unittest.mock import CaptureFixture, MonkeyPatch


def create_binary_file(path: Path, content: bytes) -> None:
    with path.open("wb") as f:
        f.write(content)


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


def make_iterable_stdout(lines: list[str]) -> MagicMock:
    mock_stdout = MagicMock()
    mock_stdout.__iter__.return_value = iter(lines)
    mock_stdout.close = MagicMock()
    return mock_stdout


def test_handle_hexdump_and_less(tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
    # hexdump, lessが両方ある場合
    binary_file = tmp_path / "large.bin"
    create_binary_file(binary_file, b"\x00" * 1024)
    monkeypatch.setattr("shutil.which", lambda cmd: True)
    monkeypatch.setattr("os.get_terminal_size", lambda: type("T", (), {"lines": 10})())

    with patch("subprocess.Popen") as mock_popen, patch("subprocess.run") as mock_run:
        # 1回目: 行数カウント用
        mock_proc1 = MagicMock()
        mock_proc1.stdout = make_iterable_stdout(["line\n"] * 20)
        mock_proc1.wait.return_value = 0
        # 2回目: less用
        mock_proc2 = MagicMock()
        mock_proc2.stdout = MagicMock()
        mock_proc2.wait.return_value = 0
        mock_proc2.stdout.close = MagicMock()
        mock_popen.side_effect = [mock_proc1, mock_proc2]
        mock_run.return_value = MagicMock()

        BinaryHandler.handle(binary_file)
        assert mock_popen.call_count == 2
        mock_run.assert_called_with(["less", "-R"], stdin=mock_proc2.stdout, check=True)
        mock_proc2.stdout.close.assert_called()
        mock_proc2.wait.assert_called()


def test_handle_hexdump_not_found(tmp_path: Path, capsys: "CaptureFixture") -> None:
    binary_file = tmp_path / "nofound.bin"
    create_binary_file(binary_file, b"\x00\x01")
    with patch("shutil.which", return_value=None):
        BinaryHandler.handle(binary_file)
    captured = capsys.readouterr()
    assert "hexdump" in captured.err


def test_handle_less_not_found(tmp_path: Path, monkeypatch: "MonkeyPatch") -> None:
    binary_file = tmp_path / "noles.bin"
    create_binary_file(binary_file, b"\x00" * 10)
    monkeypatch.setattr("shutil.which", lambda cmd: True if cmd == "hexdump" else None)
    monkeypatch.setattr("os.get_terminal_size", lambda: type("T", (), {"lines": 1})())
    with patch("subprocess.Popen") as mock_popen, patch("subprocess.run") as mock_run:
        # 1回目: 行数カウント用
        mock_proc1 = MagicMock()
        mock_proc1.stdout = make_iterable_stdout(["line\n"] * 5)
        mock_proc1.wait.return_value = 0
        mock_popen.return_value = mock_proc1
        mock_run.return_value = MagicMock()
        BinaryHandler.handle(binary_file)
        mock_run.assert_called_with(["hexdump", "-C", str(binary_file)], check=True)
