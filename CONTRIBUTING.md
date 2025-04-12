# 開発ガイドライン

## 言語要件
- プロダクトコードとユーザー向けドキュメント: 英語
- 設計ドキュメント: 日本語/英語/混合可

## 環境セットアップ

### 必要なツール
- Python 3.12以上
- uv (Pythonパッケージマネージャー)
- Git

### 開発環境構築
```bash
# リポジトリのクローン
git clone https://github.com/your-username/the-l-command.git
cd the-l-command

# uvのインストール（まだ持っていない場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存関係のインストール
uv sync

# pre-commitフックのインストール
uv run pre-commit install
```

### 開発コマンド
```bash
# テストの実行
uv run pytest tests/

# カバレッジ付きテスト
uv run pytest --cov=src/l_command tests/

# リントチェック
uv run ruff check .

# コードフォーマット
uv run ruff format .

# pre-commitフックの手動実行（全ファイル）
uv run pre-commit run --all-files
```

### pre-commitの使用方法
pre-commitは以下のタイミングで自動的に実行されます：
- コミット時
- プッシュ時（オプション）

手動で実行する場合：
```bash
# 全ファイルに対して実行
uv run pre-commit run --all-files

# 特定のファイルに対して実行
uv run pre-commit run --files <ファイル名>
```

pre-commitフックは以下のチェックを行います：
- ruffによるコードフォーマットとリント
- 大きなファイルのチェック
- 大文字小文字の競合チェック
- JSON/YAMLファイルの構文チェック
- ファイル末尾の空白チェック

## コーディング規約

### コードスタイル
- ruffをフォーマッターとリンターとして使用
- タイプヒントは必須
- 関数とクラスにはdocstringを記述する（Google styleを推奨）

### ruffの設定
`pyproject.toml`に以下の設定を追加:

```toml
[tool.ruff]
target-version = "py38"
line-length = 88
select = ["E", "F", "I", "N", "UP", "ANN", "B", "A", "C4", "SIM", "TD"]
ignore = []

[tool.ruff.lint.isort]
known-first-party = ["l_command"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.ruff.lint.pydocstyle]
convention = "google"
```

### 型ヒントの使用例
```python
from typing import Optional, List, Dict, Any, Union, Tuple

def analyze_path(path: Optional[str]) -> int:
    """
    Analyze a path and display it with the appropriate command.

    Args:
        path: Path to display. If None, process stdin.

    Returns:
        Exit code
    """
    # 実装
```

## Gitコミットメッセージのルール

### 基本構造
```
<type>(<scope>): <subject>

<body>

<footer>
```

### タイプ
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメントのみの変更
- `style`: コードの意味に影響しない変更（空白、フォーマット、セミコロンの欠落など）
- `refactor`: バグ修正でも機能追加でもないコード変更
- `test`: 不足しているテストの追加や既存のテストの修正
- `chore`: ビルドプロセスや補助ツールの変更

### ルール
1. 件名行は50文字以内
2. 件名行は大文字で始めない
3. 件名行は命令形で書く（"変更した"ではなく"変更する"）
4. 件名行の末尾にピリオドをつけない
5. 本文は72文字で折り返す
6. 本文では「何を」「なぜ」を説明する（「どのように」は省略可）

### 例
```
feat(cli): add version flag support

Add -v and --version flags to display the current version of the tool.
This resolves the user feedback issue #42.
```

## 品質保証

### テスト
- pytestを使用してユニットテストとインテグレーションテストを作成
- テストカバレッジ80%以上を目標

### GitHub CI設定
`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh

    - name: Install dependencies
      run: |
        uv pip install -e ".[dev]"

    - name: Lint with ruff
      run: ruff check .

    - name: Format check with ruff
      run: ruff format --check .

    - name: Test with pytest
      run: pytest
```

## 開発ワークフロー

1. 新機能やバグ修正のためのブランチを作成
2. 変更を実装（型ヒント含む）
3. テストを追加・実行
4. コードをフォーマット: `ruff format .`
5. リントを実行: `ruff check .`
6. PRを作成

## プロジェクト構造（拡張版）
```
l-command/
├── README.md
├── LICENSE
├── CONTRIBUTING.md           # この開発ガイドラインを含む
├── pyproject.toml           # プロジェクトメタデータ、ビルド設定
├── setup.py                 # 後方互換性のため
├── src/
│   └── l_command/
│       ├── __init__.py
│       ├── cli.py           # CLIエントリーポイント
│       ├── core.py          # コアロジック
│       ├── constants.py     # 定数
│       └── handlers/        # 各種ハンドラ
│           ├── __init__.py
│           ├── file.py
│           ├── directory.py
│           └── stdin.py
├── tests/
│   ├── unit/               # 単体テスト
│   └── integration/        # 統合テスト
└── docs/                   # プロジェクトドキュメント
```

## 依存関係管理

このプロジェクトでは依存関係管理に`uv`を使用しています。

```bash
uv sync
```

## パッケージング

```bash
# ビルド
uv pip install build
python -m build

# PyPIにアップロード
uv pip install twine
python -m twine upload dist/*
```
