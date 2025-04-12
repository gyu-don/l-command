# 実装例

このドキュメントでは、`l`コマンドの拡張実装例を提供します。

## YAMLファイル対応の実装例

以下は、YAMLファイルを処理するための実装例です。

```python
from pathlib import Path
import subprocess
import os
import sys
from typing import Optional

from l_command.constants import YAML_CONTENT_CHECK_BYTES, MAX_YAML_SIZE_BYTES

def should_try_yq(file_path: Path) -> bool:
    """Determine if a file is likely YAML and should be processed with yq."""
    # 拡張子による判定
    if file_path.suffix.lower() in [".yaml", ".yml"]:
        try:
            if file_path.stat().st_size == 0:
                return False
        except OSError:
            return False
        return True

    # コンテンツによる判定（オプション）
    try:
        with file_path.open("rb") as f:
            content_start = f.read(YAML_CONTENT_CHECK_BYTES)
            if not content_start:
                return False
            try:
                content_text = content_start.decode("utf-8").strip()
                # YAMLの特徴的なパターンを検出
                if ":" in content_text and not content_text.startswith("{"):
                    return True
            except UnicodeDecodeError:
                pass
    except OSError:
        pass

    return False

def display_yaml_with_yq(file_path: Path) -> None:
    """Display YAML file using yq with appropriate formatting."""
    try:
        file_size = file_path.stat().st_size
        if file_size == 0:
            print("(Empty file)")
            return

        if file_size > MAX_YAML_SIZE_BYTES:
            print(
                f"File size ({file_size} bytes) exceeds limit "
                f"({MAX_YAML_SIZE_BYTES} bytes). "
                f"Falling back to default viewer.",
                file=sys.stderr,
            )
            display_file_default(file_path)
            return

        # YAMLの構文確認（オプション）
        try:
            subprocess.run(
                ["yq", ".", str(file_path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            print("yq command not found. Falling back to default viewer.", file=sys.stderr)
            display_file_default(file_path)
            return
        except subprocess.CalledProcessError as e:
            print(
                f"File identified as YAML but failed validation: {e.stderr.decode('utf-8', errors='replace')}. "
                "Falling back to default viewer.",
                file=sys.stderr,
            )
            display_file_default(file_path)
            return

        # ターミナルの高さ取得とページング処理
        try:
            terminal_height = os.get_terminal_size().lines
        except OSError:
            terminal_height = float("inf")

        line_count = count_lines(file_path)

        try:
            if line_count > terminal_height:
                # lessを使ってページング
                yq_process = subprocess.Popen(
                    ["yq", ".", str(file_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                subprocess.run(
                    ["less", "-R"],
                    stdin=yq_process.stdout,
                    check=True,
                )
                yq_process.stdout.close()
                yq_retcode = yq_process.wait()
                if yq_retcode != 0:
                    print(f"yq process exited with code {yq_retcode}", file=sys.stderr)
                    display_file_default(file_path)
            else:
                # 直接表示
                subprocess.run(["yq", ".", str(file_path)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error displaying YAML with yq: {e}", file=sys.stderr)
            display_file_default(file_path)
        except OSError as e:
            print(f"Error running yq command: {e}", file=sys.stderr)
            display_file_default(file_path)

    except OSError as e:
        print(f"Error accessing file stats for YAML processing: {e}", file=sys.stderr)
        display_file_default(file_path)
```

## CSVファイル対応の実装例

以下は、CSVファイルを処理するための実装例です。

```python
def should_try_csv_formatter(file_path: Path) -> bool:
    """Determine if a file is likely CSV and should be formatted."""
    # 拡張子による判定
    if file_path.suffix.lower() in [".csv", ".tsv"]:
        try:
            if file_path.stat().st_size == 0:
                return False
        except OSError:
            return False
        return True

    # コンテンツによる判定（オプション）
    try:
        with file_path.open("rb") as f:
            content_start = f.read(1024)
            if not content_start:
                return False
            try:
                content_text = content_start.decode("utf-8")
                # カンマが多数ある行を検出
                lines = content_text.split("\n")
                if len(lines) >= 2:
                    commas_in_first_line = lines[0].count(",")
                    if commas_in_first_line >= 2:
                        # 2行目も同じようなカンマ数か確認
                        if len(lines) > 1 and abs(lines[1].count(",") - commas_in_first_line) <= 1:
                            return True
            except UnicodeDecodeError:
                pass
    except OSError:
        pass

    return False

def display_csv_with_column(file_path: Path) -> None:
    """Display CSV file using column command for better formatting."""
    delimiter = "," if file_path.suffix.lower() == ".csv" else "\t"

    try:
        file_size = file_path.stat().st_size
        if file_size == 0:
            print("(Empty file)")
            return

        if file_size > 5 * 1024 * 1024:  # 5MB
            print(
                f"File size ({file_size} bytes) exceeds limit. "
                f"Falling back to default viewer.",
                file=sys.stderr,
            )
            display_file_default(file_path)
            return

        # ターミナルの高さ取得とページング処理
        try:
            terminal_height = os.get_terminal_size().lines
        except OSError:
            terminal_height = float("inf")

        line_count = count_lines(file_path)

        try:
            if line_count > terminal_height:
                # lessを使ってページング
                column_process = subprocess.Popen(
                    ["column", "-t", "-s", delimiter, str(file_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                subprocess.run(
                    ["less", "-S"],  # -Sは横スクロールを可能にする
                    stdin=column_process.stdout,
                    check=True,
                )
                column_process.stdout.close()
                column_retcode = column_process.wait()
                if column_retcode != 0:
                    print(f"column process exited with code {column_retcode}", file=sys.stderr)
                    display_file_default(file_path)
            else:
                # 直接表示
                subprocess.run(["column", "-t", "-s", delimiter, str(file_path)], check=True)
        except FileNotFoundError:
            print("column command not found. Falling back to default viewer.", file=sys.stderr)
            display_file_default(file_path)
        except subprocess.CalledProcessError as e:
            print(f"Error displaying CSV with column: {e}", file=sys.stderr)
            display_file_default(file_path)
        except OSError as e:
            print(f"Error running column command: {e}", file=sys.stderr)
            display_file_default(file_path)

    except OSError as e:
        print(f"Error accessing file stats for CSV processing: {e}", file=sys.stderr)
        display_file_default(file_path)
```

## 実装のためのチェックリスト

新しいファイルタイプハンドラを追加する際のチェックリスト：

1. **定数の追加**:
   - `constants.py` に必要な定数を追加（サイズ制限など）

2. **検出関数の実装**:
   - 拡張子による検出
   - コンテンツによる検出（オプション）
   - エラーハンドリング

3. **表示関数の実装**:
   - サイズチェック
   - 外部コマンドの存在確認
   - ページング処理（必要に応じて）
   - エラーハンドリングとフォールバック

4. **メイン関数の更新**:
   - 新しい条件分岐の追加

5. **テストの作成**:
   - 検出関数のテスト
   - 表示関数のテスト（モックを使用）
   - エラーケースのテスト
