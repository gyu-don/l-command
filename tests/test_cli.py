from pathlib import Path

from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from l_command.cli import main


def test_main_with_nonexistent_path(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture
) -> None:
    """存在しないパスを指定した場合のテスト"""
    # コマンドライン引数をモック
    monkeypatch.setattr("sys.argv", ["l_command", "nonexistent_path"])

    # main関数を実行
    result = main()

    # 標準出力を取得
    captured = capsys.readouterr()

    # 戻り値が1（エラー）であることを確認
    assert result == 1
    # エラーメッセージが表示されていることを確認
    assert "Error: Path not found: nonexistent_path" in captured.out


def test_main_with_directory(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """ディレクトリを指定した場合のテスト"""
    # テスト用のディレクトリを作成
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # コマンドライン引数をモック
    monkeypatch.setattr("sys.argv", ["l_command", str(test_dir)])

    # main関数を実行
    result = main()

    # 戻り値が0（成功）であることを確認
    assert result == 0


def test_main_with_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """ファイルを指定した場合のテスト"""
    # テスト用のファイルを作成
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content")

    # コマンドライン引数をモック
    monkeypatch.setattr("sys.argv", ["l_command", str(test_file)])

    # main関数を実行
    result = main()

    # 戻り値が0（成功）であることを確認
    assert result == 0
