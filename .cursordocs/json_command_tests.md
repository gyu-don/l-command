# JSON/jqコマンド動作確認結果

## 環境情報

- jqコマンドバージョン: 1.7.1
- lessコマンドバージョン: 668 (PCRE2対応)

## 確認結果

### jqコマンドの基本機能

```bash
# 基本的なJSON整形
$ uv run python -c "import json; print(json.dumps({'name': 'test', 'value': 123}))" | jq .
{
  "name": "test",
  "value": 123
}
```

### jqコマンドのカラー出力

jqコマンドは`--color-output`オプションでカラー出力が可能。lessコマンドの`-R`オプションと組み合わせることでパイプ後もカラー表示が維持できる。

```bash
$ uv run python -c "import json; print(json.dumps({'name': 'test', 'value': 123}))" | jq --color-output . | less -R
```

### JSON構文チェック

`jq empty`コマンドを使用してJSON構文の妥当性を高速にチェックできる：

```bash
# 有効なJSONの場合
$ echo '{"valid": "json"}' | jq empty > /dev/null; echo $?
0

# 無効なJSONの場合
$ echo '{"invalid": json}' | jq empty > /dev/null; echo $?
jq: parse error: Invalid numeric literal at line 1, column 17
5
```

有効なJSONの場合は終了コード0、無効なJSONの場合は終了コード5が返される。
これを利用して、JSONが有効かどうかをチェックし、無効な場合は通常のファイル表示処理にフォールバックできる。

### カラー出力の注意点

- `jq --color-output`または`jq -C`でカラー出力を強制できる
- lessに渡す場合は`less -R`オプションが必要
- 環境によってカラー対応が異なる場合があるため、環境変数`LESS`も適切に設定する必要がある可能性がある

## 実装に向けた考察

- JSON処理のフローは以下の通り実装する:
  1. ファイル拡張子または内容からJSONかどうかを判定
  2. `jq empty`でJSON構文チェック (終了コード確認)
  3. ファイルサイズに応じて処理分岐:
     - 小さいJSONファイル: `jq . [file]`で直接表示
     - 中程度のJSONファイル: `jq --color-output . [file] | less -R`でページング表示
     - 大きいJSONファイル: 通常のファイル表示にフォールバックまたは`jq '.[:10]'`など部分表示
  4. 不正なJSON: 通常のファイル表示にフォールバック
