# Issue #23: 設定ファイルスキーマ設計

## 概要

Issue #23 (Phase 1: Add Configuration File Override Capability) の実装に向けた、TOML設定ファイルのスキーマ設計書。

## 目的

現在のハードコードされたハンドラー設定を維持しながら、ユーザーが設定ファイルでハンドラーの有効化/無効化および優先順位をオーバーライドできる機能を提供する。

## 要件（Acceptance Criteria）

1. TOML形式の設定ファイル構造の作成
2. 設定ファイルの読み込みとパース処理の実装
3. ハンドラーの有効化と優先順位のオーバーライド機能
4. 設定ファイルが存在しない場合のデフォルト値へのフォールバック
5. 設定オプションのドキュメント作成

## 現在のハンドラー構造

### ハンドラー一覧と優先順位

| ハンドラー名 | クラス名 | デフォルト優先順位 | 説明 |
|------------|---------|-------------------|------|
| directory | DirectoryHandler | 100 | ディレクトリの表示 |
| archive | ArchiveHandler | 80 | アーカイブファイルの内容表示 |
| image | ImageHandler | 65 | 画像ファイルの表示 |
| pdf | PDFHandler | 60 | PDFファイルのテキスト抽出 |
| binary | BinaryHandler | 60 | バイナリファイルの16進数表示 |
| media | MediaHandler | 55 | 音声/動画ファイルのメタデータ表示 |
| json | JsonHandler | 50 | JSON形式の整形表示 |
| xml | XMLHandler | 45 | XML/HTML形式の整形表示 |
| csv | CSVHandler | 40 | CSV/TSV形式のテーブル表示 |
| markdown | MarkdownHandler | 35 | Markdownのレンダリング表示 |
| yaml | YAMLHandler | 30 | YAML形式の整形表示 |
| default | DefaultFileHandler | 0 | テキストファイルのデフォルト表示 |

### ハンドラーの動作フロー

1. `cli.py:main()` がエントリーポイント
2. `handlers/__init__.py:get_handlers()` が優先順位順にハンドラーリストを返す
3. 各ハンドラーの `can_handle(path)` でマッチするハンドラーを判定
4. 最初にマッチしたハンドラーの `handle(path)` で処理を実行

## TOML設定ファイルスキーマ設計

### ファイル配置と検索順序

設定ファイルは以下の順序で検索され、最初に見つかったファイルを使用する：

1. `$XDG_CONFIG_HOME/l-command/config.toml`（環境変数が設定されている場合）
2. `~/.config/l-command/config.toml`（Linux/macOS）
3. `~/.l-command/config.toml`（後方互換性のため）
4. `./l-command.toml`（カレントディレクトリ、プロジェクト固有設定用）

### スキーマ構造

```toml
# l-command 設定ファイル
# TOML形式: https://toml.io/

# ===========================
# グローバル設定
# ===========================
[general]
# 設定ファイルのバージョン（将来の互換性のため）
version = "1.0"

# ===========================
# ハンドラー設定
# ===========================
[handlers]
# 各ハンドラーの有効化/無効化と優先順位の設定
#
# 設定可能な項目:
# - enabled: ハンドラーの有効化 (true/false)
# - priority: 優先順位 (整数値、高いほど優先)
#
# 注意事項:
# - enabled を指定しない場合、デフォルトで有効
# - priority を指定しない場合、ハードコードされたデフォルト値を使用
# - DirectoryHandler と DefaultFileHandler は無効化できない（システムの基本動作）

# ディレクトリハンドラー（無効化不可）
[handlers.directory]
# enabled = true  # 常に有効（設定しても無視される）
priority = 100    # オーバーライド可能（デフォルト: 100）

# アーカイブハンドラー
[handlers.archive]
enabled = true
priority = 80  # デフォルト: 80

# 画像ハンドラー
[handlers.image]
enabled = true
priority = 65  # デフォルト: 65

# PDFハンドラー
[handlers.pdf]
enabled = true
priority = 60  # デフォルト: 60

# バイナリハンドラー
[handlers.binary]
enabled = true
priority = 60  # デフォルト: 60
# 注: PDFとBinaryが同じ優先順位の場合、登録順で評価される

# メディアハンドラー（音声/動画）
[handlers.media]
enabled = true
priority = 55  # デフォルト: 55

# JSONハンドラー
[handlers.json]
enabled = true
priority = 50  # デフォルト: 50

# XML/HTMLハンドラー
[handlers.xml]
enabled = true
priority = 45  # デフォルト: 45

# CSV/TSVハンドラー
[handlers.csv]
enabled = true
priority = 40  # デフォルト: 40

# Markdownハンドラー
[handlers.markdown]
enabled = true
priority = 35  # デフォルト: 35

# YAMLハンドラー
[handlers.yaml]
enabled = true
priority = 30  # デフォルト: 30

# デフォルトハンドラー（無効化不可）
[handlers.default]
# enabled = true  # 常に有効（設定しても無視される）
# priority = 0    # 変更不可
```

### ユースケース別の設定例

#### 例1: PDFを無効化（テキスト抽出が不要な場合）

```toml
[handlers.pdf]
enabled = false
```

#### 例2: JSONの優先順位を上げる（JSONを優先的に処理）

```toml
[handlers.json]
priority = 70  # デフォルトの50から70に引き上げ
```

#### 例3: Markdownをプレーンテキストとして扱う

```toml
[handlers.markdown]
enabled = false  # Markdownハンドラーを無効化してDefaultHandlerで処理
```

#### 例4: 開発環境用の設定（画像とメディアを無効化）

```toml
[general]
version = "1.0"

[handlers.image]
enabled = false

[handlers.media]
enabled = false

[handlers.pdf]
enabled = false
```

## データ構造設計

### Python側のデータ構造

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class HandlerConfig:
    """個別ハンドラーの設定."""
    enabled: bool = True
    priority: Optional[int] = None  # None の場合はデフォルト値を使用

@dataclass
class GeneralConfig:
    """グローバル設定."""
    version: str = "1.0"

@dataclass
class Config:
    """l-command の設定全体."""
    general: GeneralConfig
    handlers: dict[str, HandlerConfig]  # key: ハンドラー名（例: "json", "pdf"）

    @classmethod
    def default(cls) -> "Config":
        """デフォルト設定を返す."""
        return cls(
            general=GeneralConfig(),
            handlers={
                "directory": HandlerConfig(enabled=True, priority=100),
                "archive": HandlerConfig(enabled=True, priority=80),
                "image": HandlerConfig(enabled=True, priority=65),
                "pdf": HandlerConfig(enabled=True, priority=60),
                "binary": HandlerConfig(enabled=True, priority=60),
                "media": HandlerConfig(enabled=True, priority=55),
                "json": HandlerConfig(enabled=True, priority=50),
                "xml": HandlerConfig(enabled=True, priority=45),
                "csv": HandlerConfig(enabled=True, priority=40),
                "markdown": HandlerConfig(enabled=True, priority=35),
                "yaml": HandlerConfig(enabled=True, priority=30),
                "default": HandlerConfig(enabled=True, priority=0),
            }
        )
```

## 実装方針

### 1. 設定ファイルの読み込み

- `tomllib`（Python 3.11+の標準ライブラリ）を使用してTOMLをパース
- Python 3.10以下の場合は `tomli` を依存関係に追加

### 2. 設定のマージ

1. デフォルト設定を作成
2. 設定ファイルが存在する場合、読み込んでパース
3. 設定ファイルの値でデフォルト設定をオーバーライド
4. マージ済み設定を返す

### 3. ハンドラーレジストリの変更

`handlers/__init__.py:get_handlers()` を変更：

```python
def get_handlers(config: Optional[Config] = None) -> list[type[FileHandler]]:
    """設定に基づいてハンドラーリストを返す."""
    if config is None:
        config = Config.default()

    # ハンドラー名とクラスのマッピング
    handler_map = {
        "directory": DirectoryHandler,
        "archive": ArchiveHandler,
        "image": ImageHandler,
        "pdf": PDFHandler,
        "binary": BinaryHandler,
        "media": MediaHandler,
        "json": JsonHandler,
        "xml": XMLHandler,
        "csv": CSVHandler,
        "markdown": MarkdownHandler,
        "yaml": YAMLHandler,
        "default": DefaultFileHandler,
    }

    # 有効なハンドラーのみをフィルタリング
    enabled_handlers = []
    for name, handler_class in handler_map.items():
        handler_config = config.handlers.get(name)
        if handler_config and handler_config.enabled:
            enabled_handlers.append(handler_class)

    # 優先順位でソート（設定値またはデフォルト値を使用）
    def get_priority(handler_class: type[FileHandler]) -> int:
        handler_name = handler_class.__name__.replace("Handler", "").lower()
        handler_config = config.handlers.get(handler_name)
        if handler_config and handler_config.priority is not None:
            return handler_config.priority
        return handler_class.priority()

    return sorted(enabled_handlers, key=get_priority, reverse=True)
```

### 4. バリデーション

設定ファイル読み込み時に以下をチェック：

- `enabled` フィールドがboolean型であること
- `priority` フィールドが整数型であること（指定されている場合）
- 不明なハンドラー名が指定されている場合は警告を出力
- `directory` と `default` ハンドラーの無効化を試みた場合は警告を出力して無視

### 5. エラーハンドリング

- 設定ファイルが存在しない場合: デフォルト設定を使用（エラーなし）
- TOMLパースエラー: 警告を出力してデフォルト設定を使用
- 無効な設定値: 警告を出力してその項目をスキップ

## Phase 2への準備

Phase 2 (#24) では以下の機能が追加される予定：

- デフォルト設定の外部化
- 設定値のバリデーション強化
- 設定ファイルのスキーマバージョニング

これを考慮して、以下を準備：

- `version` フィールドの追加（将来の互換性のため）
- 拡張可能なデータ構造設計
- バリデーション機能の基盤整備

## テスト戦略

### 単体テスト

1. **設定ファイルのパース**
   - 有効な TOML ファイルの読み込み
   - 無効な TOML ファイルのエラーハンドリング
   - 部分的な設定のマージ

2. **設定のマージ**
   - デフォルト設定のみ
   - 一部の設定をオーバーライド
   - すべての設定をオーバーライド

3. **ハンドラーフィルタリング**
   - 有効なハンドラーのみが含まれること
   - 優先順位が正しくソートされること
   - 無効化されたハンドラーが除外されること

### 統合テスト

1. **設定ファイルを使用した `l` コマンドの実行**
   - カスタム設定での各ハンドラーの動作確認
   - 無効化されたハンドラーがスキップされること
   - 優先順位の変更が反映されること

2. **フォールバック動作**
   - 設定ファイルが存在しない場合のデフォルト動作
   - パースエラー時のフォールバック

## セキュリティ考慮事項

1. **ファイルパーミッション**
   - 設定ファイルの読み込み時に適切なパーミッションをチェック
   - 他のユーザーが書き込み可能な設定ファイルの場合は警告

2. **パストラバーサル対策**
   - 設定ファイルのパスは絶対パスまたはホームディレクトリ基準のみ許可

3. **リソース制限**
   - 設定ファイルのサイズ制限（1MB以下など）

## 今後の拡張可能性

Phase 2以降で追加可能な機能：

1. **ハンドラー固有の設定**
   ```toml
   [handlers.json.options]
   max_size_mb = 10
   use_jq = true
   ```

2. **カラーテーマのカスタマイズ**
   ```toml
   [appearance]
   color_scheme = "solarized"
   ```

3. **エイリアス機能**
   ```toml
   [aliases]
   ll = ["l", "--long"]
   ```

## 参考資料

- [TOML仕様](https://toml.io/)
- [Python tomllib ドキュメント](https://docs.python.org/3/library/tomllib.html)
- Issue #22: 親Issue（設定機能全般）
- Issue #24: Phase 2（デフォルト設定の外部化とバリデーション）

## 変更履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|-----------|---------|--------|
| 2025-10-26 | 1.0 | 初版作成 | Claude Code |
