# PyPI 配布に向けたタスクリスト

## あなたが行うべきこと (MUST)

-   [x] PyPI ([https://pypi.org/](https://pypi.org/)) にアカウントを作成する
-   [x] `pyproject.toml` の `project.urls` のプレースホルダー (`https://github.com/gyu-don/l-command`) を実際のURLに更新する
-   [x] プロジェクトのバージョン (`pyproject.toml` の `version`) が適切か確認する (必要であれば更新する)
-   [x] `README.md` の内容を確認し、PyPIで表示されるのに適しているか確認する
-   [x] `LICENSE` ファイルの内容を確認する (`pyproject.toml` で `license = {text = "Apache-2.0"}` と指定していますが、実ファイルも確認してください)
-   [x] リリース前にテストを実行し、パスすることを確認する (`uv run pytest`)
-   [ ] `git tag` を使ってリリースバージョンに対応するタグを作成する (例: `git tag v0.1.0`)
-   [ ] タグをリモートリポジトリにプッシュする (例: `git push origin v0.1.0`)
-   [x] PyPIにアップロードするためのツール (`twine` など) をインストールする (`uv add --dev twine`)
-   [x] ビルドコマンドを実行して配布物 (`.whl`, `.tar.gz`) を作成する (`uv run hatch build`)
-   [x] 作成された配布物を確認する (`dist/` ディレクトリ以下)
-   [ ] `twine` を使ってTestPyPIにアップロードし、インストール可能かテストする (推奨)
    -   `uv run twine upload --repository testpypi dist/*`
    -   TestPyPIからインストールしてみる: `pip install --index-url https://test.pypi.org/simple/ --no-deps l-command`
-   [ ] `twine` を使ってPyPIにアップロードする
    -   `uv run twine upload dist/*`

## Cursorが行うこと (Done by Cursor)

-   [x] `pyproject.toml` に `project.urls`, `keywords`, 追加の `classifiers` を追記

## Optionalで行ってもいいこと (OPTIONAL)

-   [ ] `CONTRIBUTING.md` や `CODE_OF_CONDUCT.md` などのドキュメントを追加する
-   [ ] Read the Docs ([https://readthedocs.org/](https://readthedocs.org/)) などでドキュメントサイトを構築し、`project.urls.Documentation` に設定する
-   [ ] GitHub Actionsなどでリリースプロセスを自動化する (タグがプッシュされたら自動でPyPIにアップロードするなど)
-   [ ] `setuptools_scm` や `hatch-vcs` を導入して、Gitタグから自動でバージョンを決定するようにする (手動でのバージョン更新の手間が省けます)
