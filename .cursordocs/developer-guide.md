# 開発者ガイド

このドキュメントは、`l`コマンドの開発者向けの詳細な情報を提供します。

## プロジェクトアーキテクチャ

### 全体構造

`l`コマンドは以下の主要なコンポーネントで構成されています：

- **CLI インターフェース** (`cli.py`): コマンドライン引数の解析と処理のエントリーポイント
- **定数モジュール** (`constants.py`): 設定値と定数の定義
- **ハンドラ**: 各種ファイルタイプやディレクトリの処理

### 動作フロー

1. ユーザーが `l [path]` を実行
2. パスが存在するかチェック
3. パスの種類（ファイル/ディレクトリ/その他）を判定
4. 適切なハンドラで処理:
   - ディレクトリ → `ls -la --color=auto`
   - JSONファイル → `jq` + 必要に応じて `less`
   - 通常ファイル → ファイル長に応じて `cat` または `less`

## 機能の実装状況と拡張方法

### 現在実装されている機能

- ディレクトリ表示 (`ls -la --color=auto`)
- ファイル表示（ファイル長に応じて `cat` または `less`）
- JSONファイルの検出と整形表示
  - 拡張子ベースの検出 (`.json`)
  - コンテンツベースの検出 (文字列の先頭が `{` または `[`)
  - `jq` で整形
  - 構文チェックと大きなファイルのフォールバック処理

### 拡張の実装方法

#### 新しいファイルタイプハンドラの追加

新しいファイルタイプ（例：YAML、Markdown）のサポートを追加する場合は、以下の手順に従います：

1. `should_try_<handler>` 関数を追加：
   ```python
   def should_try_yaml(file_path: Path) -> bool:
       """YAMLファイルかどうかを判定する。"""
       if file_path.suffix.lower() in [".yml", ".yaml"]:
           return True

       # コンテンツベースの検出（必要に応じて）
       try:
           with file_path.open("rb") as f:
               content_start = f.read(Constants.CONTENT_CHECK_BYTES)
               # YAMLの検出ロジック
       except OSError:
           pass

       return False
   ```

2. 表示ハンドラを実装：
   ```python
   def display_yaml_with_yq(file_path: Path) -> None:
       """YAMLファイルを整形表示する。"""
       # サイズチェック
       # ツールの存在確認
       # 表示処理
   ```

3. `main()` 関数のディスパッチロジックを更新：
   ```python
   if path.is_file():
       if should_try_jq(path):
           display_json_with_jq(path)
       elif should_try_yaml(path):
           display_yaml_with_yq(path)
       else:
           display_file_default(path)
   ```

## テスト戦略

### テストの種類

1. **ユニットテスト**: 個々の関数の機能をテスト
   - `should_try_jq` のような判定関数
   - ユーティリティ関数

2. **統合テスト**: コマンド全体の動作をテスト
   - 様々な入力に対する `main()` の動作
   - サブプロセス呼び出しの正確性

3. **モックテスト**: 外部依存（コマンド実行など）をモックしてテスト
   - `subprocess` モジュールのモック
   - ファイルシステム操作のモック

### テスト例

JSONファイル検出のテスト例：

```python
def test_should_try_jq_with_json_extension():
    # .json拡張子を持つファイルを検出するかテスト
    temp_file = Path("test.json")
    assert should_try_jq(temp_file) == True

def test_should_try_jq_with_json_content():
    # JSONコンテンツを持つ拡張子なしファイルを検出するかテスト
    temp_file = Path("test_no_ext")
    # テスト用のファイルを作成してJSONコンテンツを書き込む
    with temp_file.open("w") as f:
        f.write('{"key": "value"}')
    try:
        assert should_try_jq(temp_file) == True
    finally:
        # テスト後にファイルを削除
        temp_file.unlink()
```

subprocess呼び出しのテスト例：

```python
@patch("subprocess.run")
def test_display_file_default_short_file(mock_run):
    # ファイルが端末の高さより短い場合、catを使用することをテスト
    # テスト用のファイルとモックを設定
    # display_file_default呼び出し
    # subprocess.runがcatで呼ばれたことを検証
    mock_run.assert_called_once_with(["cat", ANY], check=True)
```

## ベストプラクティス

### コード設計

1. **単一責任の原則**: 各関数は一つの責任を持つ
   - 例: `should_try_jq` はJSONファイル判定のみを行う

2. **優雅な失敗**: エラーハンドリングを適切に実装
   - ツールが存在しない場合のフォールバック
   - ファイルアクセスエラーのハンドリング

3. **設定の集中管理**: 定数は `constants.py` に集約

### 実装のヒント

1. **新機能の追加**:
   - まず動作仕様をドキュメント化
   - テストケースを先に作成（TDD）
   - 実装後に既存のテストが壊れていないことを確認

2. **コマンド実行の最適化**:
   - 不要なプロセス生成を避ける
   - 大きなファイルの処理には注意（メモリ使用量）
   - ユーザー体験を優先（処理速度、視覚的一貫性）

## よくある質問

### Q: 新しいファイルタイプのサポートはどのように追加すればよいですか？

A: 「拡張の実装方法」セクションを参照してください。基本的には、
1. 検出関数（`should_try_X`）
2. 表示関数（`display_X`）
3. メイン関数での分岐処理
の3つを実装します。

### Q: テストを実行するには？

A: 以下のコマンドでテストを実行できます。
```bash
uv run pytest tests/
```

特定のテストだけを実行する場合：
```bash
uv run pytest tests/test_json_detection.py::test_should_try_jq
```

### Q: 大きなファイルを効率的に処理する方法は？

A: 以下の戦略を検討してください：
- ストリーム処理（ファイル全体をメモリに読み込まない）
- サンプリング（大きなJSONの最初の部分のみ表示）
- 適切なページング（`less`など）
- 適切なタイムアウト処理
