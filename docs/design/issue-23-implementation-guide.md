# Issue #23: 実装ガイド

## 概要

このドキュメントは Issue #23 (Phase 1: Add Configuration File Override Capability) の実装手順を示します。

## 実装タスク一覧

### Phase 1: 基本構造の実装

#### Task 1: Python要件の確認と設定

**目的**: Python 3.11+の標準ライブラリ`tomllib`が使用可能であることを確認し、プロジェクト要件を明示

**要件**: Python 3.11以上

**実装内容**:

1. **Python バージョン確認**:
```bash
python --version  # 3.11以上であることを確認
```

2. **pyproject.toml の更新** (必要に応じて):
```toml
[project]
requires-python = ">=3.11"
```

**ファイル**:
- `pyproject.toml` (Python要件の明示)
- 変更なし（標準ライブラリの`tomllib`を使用）

**検証方法**:
```bash
uv run python -c "import tomllib; print('tomllib available')"
```

**注意**:
- Python 3.11未満の環境では設定ファイル機能は利用できません
- 設定ファイルが使えない場合は、デフォルト設定で動作します（下位互換性）

---

#### Task 2: 設定データ構造の実装

**目的**: 設定を表現するデータクラスを作成

**ファイル**: `src/l_command/config.py` (新規作成)

**実装内容**:
```python
"""Configuration management for l-command."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class HandlerConfig:
    """Configuration for a single handler.

    Attributes:
        enabled: Whether the handler is enabled.
        priority: Priority of the handler (higher is evaluated first).
                  If None, use the handler's default priority.
        options: Handler-specific options (arbitrary key-value pairs).
    """

    enabled: bool = True
    priority: Optional[int] = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneralConfig:
    """General configuration.

    Attributes:
        version: Configuration file schema version for future compatibility.
                 Format: "{major}.{minor}" (e.g., "1.0", "1.1", "2.0")
    """

    version: str = "1.0"


@dataclass
class Config:
    """Complete configuration for l-command.

    Attributes:
        general: General configuration.
        handlers: Dictionary mapping handler names to their configurations.
    """

    general: GeneralConfig = field(default_factory=GeneralConfig)
    handlers: dict[str, HandlerConfig] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "Config":
        """Return the default configuration.

        Returns:
            Default configuration with all handlers enabled at their default priorities.
        """
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
            },
        )
```

**テスト**: `tests/test_config.py`
```python
def test_default_config():
    config = Config.default()
    assert config.general.version == "1.0"
    assert len(config.handlers) == 12
    assert config.handlers["json"].enabled is True
    assert config.handlers["json"].priority == 50
    assert config.handlers["json"].options == {}
```

---

#### Task 3: 設定ファイル検索機能の実装

**目的**: 設定ファイルを標準的な場所から検索する

**ファイル**: `src/l_command/config.py` (追加)

**実装内容**:
```python
import os


def find_config_file() -> Optional[Path]:
    """Find the configuration file in standard locations.

    Search order:
    1. $XDG_CONFIG_HOME/l-command/config.toml
    2. ~/.config/l-command/config.toml
    3. ~/.l-command/config.toml
    4. ./l-command.toml (current directory)

    Returns:
        Path to the configuration file if found, None otherwise.
    """
    search_paths = []

    # 1. XDG_CONFIG_HOME
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        search_paths.append(Path(xdg_config_home) / "l-command" / "config.toml")

    # 2. ~/.config/l-command/config.toml
    home = Path.home()
    search_paths.append(home / ".config" / "l-command" / "config.toml")

    # 3. ~/.l-command/config.toml
    search_paths.append(home / ".l-command" / "config.toml")

    # 4. ./l-command.toml
    search_paths.append(Path.cwd() / "l-command.toml")

    for path in search_paths:
        if path.exists() and path.is_file():
            return path

    return None
```

**テスト**: `tests/test_config.py`
```python
def test_find_config_file_not_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert find_config_file() is None


def test_find_config_file_in_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / ".config" / "l-command"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text("[general]\nversion = \"1.0\"\n")

    found = find_config_file()
    assert found == config_file
```

---

#### Task 4: TOMLパース機能の実装

**目的**: TOMLファイルを読み込んで設定オブジェクトに変換

**ファイル**: `src/l_command/config.py` (追加)

**実装内容**:
```python
import logging
import sys

logger = logging.getLogger(__name__)


def parse_toml_file(path: Path) -> dict:
    """Parse a TOML file.

    Args:
        path: Path to the TOML file.

    Returns:
        Parsed TOML data as a dictionary.

    Raises:
        ValueError: If the file cannot be parsed.
    """
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Failed to parse TOML file {path}: {e}") from e
    except OSError as e:
        raise ValueError(f"Failed to read file {path}: {e}") from e


def validate_handler_config(name: str, data: dict) -> Optional[HandlerConfig]:
    """Validate and convert handler configuration data.

    Args:
        name: Handler name.
        data: Raw configuration data.

    Returns:
        HandlerConfig object if valid, None if invalid.
    """
    if not isinstance(data, dict):
        logger.warning(f"Invalid handler config for '{name}': expected dict, got {type(data)}")
        return None

    enabled = data.get("enabled", True)
    if not isinstance(enabled, bool):
        logger.warning(f"Invalid 'enabled' value for handler '{name}': expected bool, got {type(enabled)}")
        enabled = True

    priority = data.get("priority")
    if priority is not None and not isinstance(priority, int):
        logger.warning(f"Invalid 'priority' value for handler '{name}': expected int, got {type(priority)}")
        priority = None

    # Parse handler-specific options
    options = data.get("options", {})
    if not isinstance(options, dict):
        logger.warning(f"Invalid 'options' value for handler '{name}': expected dict, got {type(options)}")
        options = {}

    return HandlerConfig(enabled=enabled, priority=priority, options=options)


def load_config_from_dict(data: dict) -> Config:
    """Load configuration from parsed TOML data.

    Args:
        data: Parsed TOML data.

    Returns:
        Config object with merged settings.
    """
    config = Config.default()

    # Parse general section
    if "general" in data and isinstance(data["general"], dict):
        general_data = data["general"]
        if "version" in general_data and isinstance(general_data["version"], str):
            config.general.version = general_data["version"]

    # Parse handlers section
    if "handlers" in data and isinstance(data["handlers"], dict):
        handlers_data = data["handlers"]
        for name, handler_data in handlers_data.items():
            handler_config = validate_handler_config(name, handler_data)
            if handler_config is not None:
                # Merge with default config
                if name in config.handlers:
                    default_config = config.handlers[name]
                    # Override only specified values
                    if handler_config.priority is None:
                        handler_config.priority = default_config.priority
                    config.handlers[name] = handler_config
                else:
                    logger.warning(f"Unknown handler '{name}' in configuration file")

    return config


def load_config(path: Optional[Path] = None) -> Config:
    """Load configuration from file or return default.

    Args:
        path: Path to configuration file. If None, search standard locations.

    Returns:
        Loaded configuration or default if no file found.
    """
    if path is None:
        path = find_config_file()

    if path is None:
        logger.debug("No configuration file found, using defaults")
        return Config.default()

    try:
        logger.debug(f"Loading configuration from {path}")
        data = parse_toml_file(path)
        return load_config_from_dict(data)
    except ValueError as e:
        logger.warning(f"Failed to load configuration: {e}. Using defaults.")
        return Config.default()
```

**テスト**: `tests/test_config.py`
```python
def test_parse_toml_file_valid(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[general]\nversion = \"1.0\"\n")

    data = parse_toml_file(config_file)
    assert data == {"general": {"version": "1.0"}}


def test_load_config_with_overrides(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[handlers.json]
enabled = false
priority = 70

[handlers.json.options]
jq_args = ["--indent", "2"]
max_size_mb = 20

[handlers.pdf]
priority = 100
""")

    config = load_config(config_file)
    assert config.handlers["json"].enabled is False
    assert config.handlers["json"].priority == 70
    assert config.handlers["json"].options == {"jq_args": ["--indent", "2"], "max_size_mb": 20}
    assert config.handlers["pdf"].enabled is True
    assert config.handlers["pdf"].priority == 100
    assert config.handlers["pdf"].options == {}
```

---

#### Task 5: ハンドラーレジストリの変更

**目的**: 設定に基づいてハンドラーをフィルタリング・ソート

**ファイル**: `src/l_command/handlers/__init__.py`

**変更内容**:
```python
from typing import Optional
from l_command.config import Config


def get_handlers(config: Optional[Config] = None) -> list[type[FileHandler]]:
    """Return all available handlers in priority order.

    Args:
        config: Configuration object. If None, use default configuration.

    Returns:
        List of enabled handlers sorted by priority (highest first).
    """
    if config is None:
        from l_command.config import Config
        config = Config.default()

    # Handler name to class mapping
    handler_map: dict[str, type[FileHandler]] = {
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

    # Filter enabled handlers
    enabled_handlers: list[type[FileHandler]] = []
    for name, handler_class in handler_map.items():
        handler_config = config.handlers.get(name)
        if handler_config is None or handler_config.enabled:
            enabled_handlers.append(handler_class)

    # Sort by priority
    def get_priority(handler_class: type[FileHandler]) -> int:
        # Convert class name to handler name (e.g., "JsonHandler" -> "json")
        handler_name = handler_class.__name__.replace("Handler", "").lower()
        handler_config = config.handlers.get(handler_name)
        if handler_config and handler_config.priority is not None:
            return handler_config.priority
        return handler_class.priority()

    return sorted(enabled_handlers, key=get_priority, reverse=True)
```

**テスト**: `tests/test_handlers_init.py` (新規作成)
```python
from l_command.config import Config, HandlerConfig
from l_command.handlers import get_handlers
from l_command.handlers.json import JsonHandler
from l_command.handlers.pdf import PDFHandler


def test_get_handlers_with_default_config():
    handlers = get_handlers()
    assert len(handlers) == 12


def test_get_handlers_with_disabled_handler():
    config = Config.default()
    config.handlers["json"] = HandlerConfig(enabled=False)

    handlers = get_handlers(config)
    assert JsonHandler not in handlers


def test_get_handlers_with_custom_priority():
    config = Config.default()
    config.handlers["json"] = HandlerConfig(enabled=True, priority=100)

    handlers = get_handlers(config)
    # JSON should now be first (or second after DirectoryHandler)
    assert handlers[0].__name__ in ["DirectoryHandler", "JsonHandler"]
```

---

#### Task 6: CLI統合

**目的**: CLIエントリーポイントで設定を読み込む

**ファイル**: `src/l_command/cli.py`

**変更内容**:
```python
from l_command.config import load_config


def main() -> None:
    """Main entry point for the l command."""
    # ... 既存のargparse処理 ...

    # Load configuration
    config = load_config()

    # Get handlers with configuration
    handlers = get_handlers(config)

    # ... 既存の処理 ...
```

---

### Phase 2: テストとドキュメント

#### Task 7: テストの追加

**ファイル**:
- `tests/test_config.py`
- `tests/test_handlers_init.py`
- `tests/integration/test_config_integration.py`

**カバレッジ目標**: 90%以上

---

#### Task 8: ドキュメント作成

**ファイル**:
- `docs/configuration.md` (ユーザー向け設定ガイド)
- `README.md` の更新（設定機能の説明を追加）

---

## 実装順序

1. **Day 1**: Task 1-2（依存関係とデータ構造）
2. **Day 2**: Task 3-4（ファイル検索とパース）
3. **Day 3**: Task 5-6（ハンドラー統合とCLI統合）
4. **Day 4**: Task 7（テスト）
5. **Day 5**: Task 8（ドキュメント）

## チェックリスト

### 実装前

- [ ] Issue #23の要件を理解
- [ ] 設計ドキュメントのレビュー
- [ ] 現在のコードベースの理解

### 実装中

- [ ] Task 1: 依存関係の追加
- [ ] Task 2: データ構造の実装
- [ ] Task 3: ファイル検索機能
- [ ] Task 4: TOMLパース機能
- [ ] Task 5: ハンドラーレジストリの変更
- [ ] Task 6: CLI統合
- [ ] Task 7: テストの追加
- [ ] Task 8: ドキュメント作成

### 実装後

- [ ] すべてのテストが通過
- [ ] カバレッジ90%以上
- [ ] Lintエラーなし（`uv run ruff check .`）
- [ ] フォーマット済み（`uv run ruff format .`）
- [ ] ドキュメント完成
- [ ] Pre-commitフック通過

### リリース前

- [ ] 手動テスト（各種設定ファイルでの動作確認）
- [ ] エッジケースの確認
- [ ] パフォーマンステスト
- [ ] ドキュメントの最終確認

## トラブルシューティング

### Python バージョン問題

- **要件**: Python 3.11以上が必須
- Python 3.11未満の環境では設定ファイル機能は利用できません
- バージョンチェックを実装し、3.11未満の場合は警告を表示してデフォルト設定を使用

### パーミッション問題

- 設定ファイルが読み込めない場合はデフォルトにフォールバック
- 適切なエラーメッセージを表示

### パフォーマンス

- 設定ファイルの読み込みは起動時の1回のみ
- キャッシュは不要（十分に高速）

## 参考実装例

類似プロジェクトの設定実装：

- **ripgrep**: `.ripgreprc`
- **bat**: `config`ファイル
- **fd**: 設定ファイルなし（コマンドライン引数のみ）

## Phase 2への準備事項

- `version`フィールドを活用した後方互換性チェック
- バリデーション機能の拡張ポイント
- ハンドラー固有設定の追加準備
- `options`セクションの各ハンドラーでの実装

## 追加の考慮事項

### Python 3.11 要件の明示

プロジェクトの`pyproject.toml`で Python 3.11以上を要求することを推奨：

```toml
[project]
requires-python = ">=3.11"
```

ただし、設定ファイル機能が使えない場合でも基本機能は動作するよう、graceful degradationを実装：

```python
import sys

def load_config(path: Optional[Path] = None) -> Config:
    """Load configuration from file or return default."""
    if sys.version_info < (3, 11):
        logger.warning("Configuration file support requires Python 3.11+. Using defaults.")
        return Config.default()

    # ... 通常の処理 ...
```

### ハンドラー固有オプションの実装

Phase 1では`options`を辞書として格納し、Phase 2以降で各ハンドラーが解釈します：

```python
# Phase 2 以降の実装例（JSONHandler）
class JsonHandler(FileHandler):
    @classmethod
    def handle(cls, path: Path, options: dict[str, Any] = None) -> None:
        if options is None:
            options = {}

        # オプションから設定を取得
        jq_args = options.get("jq_args", [])
        max_size_mb = options.get("max_size_mb", 10)

        # オプションを使用した処理
        # ...
```
