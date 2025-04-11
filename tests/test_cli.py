from pathlib import Path

from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from l_command.cli import count_lines, main
from l_command.constants import LINE_THRESHOLD


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
    test_file.write_text(content)

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
    assert "Error counting lines" in captured.out
