---
title: pandoc-embedz
section: 1
header: ユーザーマニュアル
footer: pandoc-embedz 1.0.0
date: 2026-08-14
---

# NAME

pandoc-embedz - Jinja2 テンプレートによるデータ駆動コンテンツ埋め込み用 Pandoc フィルター

# SYNOPSIS

**pandoc** *input.md* **--filter pandoc-embedz** [**-o** *output*]

**pandoc-embedz** **-s** [**-c** *config*] [**-o** *output*] [*file* ...]

**pandoc-embedz** **-s** **-t** *template* [**-f** *format*] [**-o** *output*]

# DESCRIPTION

**pandoc-embedz** は CSV、JSON、YAML、SQLite、Excel などの各種フォーマットから
データを読み込み、Jinja2 テンプレートを通じてレンダリングします。Markdown
ドキュメントに埋め込む Pandoc フィルターとして、またはスタンドアロンのテンプレート
レンダラーとして動作します。

Markdown での最小例:

````
```embedz
---
data: sales.csv
---
{% for row in data %}
- {{ row.product }}: {{ row.amount }}
{% endfor %}
```
````

**pandoc --filter pandoc-embedz** で処理すると、コードブロックがレンダリング
結果に置き換えられます。

2つの動作モードがあります:

**フィルターモード**（デフォルト）
:   Pandoc フィルターとして動作します。Markdown ドキュメント内の `.embedz`
    コードブロックを処理します。出力は Markdown として解釈され、Pandoc の
    パイプラインに戻されます。ドキュメント生成に使用します。
    LaTeX 等の raw フォーマットを出力するには、テンプレート出力内で
    Pandoc の raw 属性構文（`` ```{=latex} ``）を使用します。
    embedz のコードブロックパーサーとの干渉を避けるため、バッククォート
    フェンスは `{{ "` `` ``` `` `" }}` で出力してください。

**スタンドアロンモード**（**-s**）
:   Pandoc を介さずテンプレートファイルを直接レンダリングします。出力は
    プレーンテキストです。CSV、設定ファイルの生成、またはシェルパイプライン
    でのテンプレート前処理に使用します。

# OPTIONS

以下のオプションはスタンドアロンモードに適用されます。フィルターモードでは
**pandoc-embedz** は Pandoc により自動的に呼び出され、オプションを受け付けません
（環境変数による **-d** を除く）。

**-s**, **--standalone**
:   スタンドアロンモードを有効化。

**-t**, **--template** *TEXT*
:   ファイルの代わりに *TEXT* をテンプレートとして使用。**-f** も指定された
    場合、データは標準入力から読み込まれます。

**-f**, **--format** *FORMAT*
:   標準入力のデータ形式: **csv**, **tsv**, **ssv**, **json**,
    **yaml**, **toml**, **lines**。

**-c**, **--config** *FILE*
:   外部 YAML 設定ファイルを読み込み。繰り返し指定可能。ファイルは順番に
    マージされ、後のファイルが前のファイルを上書きします。

**-o**, **--output** *FILE*
:   出力を *FILE* に書き込み（デフォルト: 標準出力）。

**-d**, **--debug**
:   標準エラー出力へのデバッグ出力を有効化。

**-h**, **--help**
:   ヘルプメッセージを表示。

**-v**, **--version**
:   バージョン情報を表示。

# CODE BLOCK SYNTAX

embedz コードブロックは `---` で区切られた最大3つのセクションを持ちます:

````
```embedz
---
YAML 設定
---
Jinja2 テンプレート
---
インラインデータ（オプション）
```
````

## ブロックタイプ

**データ処理** --- データを読み込みテンプレートでレンダリング:

````
```{.embedz data=file.csv}
{% for row in data %}
- {{ row.name }}
{% endfor %}
```
````

**テンプレート定義** --- 名前付きテンプレートを保存して後で再利用:

````
```{.embedz define=my-list}
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```
````

**テンプレート使用** --- 名前付きテンプレートをデータに適用:

````
```{.embedz data=file.csv as=my-list}
```
````

**変数定義** --- ドキュメント全体の変数を設定:

````
```{.embedz}
---
global:
  author: John Doe
---
```
````

## コンテンツの解釈

`---` セパレータがないブロックでは、指定された属性に基づいてコンテンツが
解釈されます:

`data` + `template`/`as`
:   コンテンツは **YAML 設定**。

`template`/`as` のみ
:   コンテンツは**インラインデータ**。

`define`
:   コンテンツは**テンプレート定義**。

なし、または `data` のみ
:   コンテンツは**テンプレート**。

`---` がある場合は、属性に関係なく標準の3セクション構造が適用されます。

# CONFIGURATION OPTIONS

以下のキーは YAML ヘッダーまたはコードブロック属性で使用できます。

## データ読み込み

**data**
:   データソース。ファイルパス（文字列）、複数ソース（dict）、または
    インラインデータ。dict では各キーが SQL テーブル名になります。
    ソースごとのパラメータ用に `file:` dict をサポート。
    `bind:` 変数を名前で参照することもできます。

**format**
:   データ形式の上書き: **csv**, **tsv**, **ssv**（または **spaces**）,
    **json**, **yaml**, **toml**, **sqlite**, **excel**, **lines**。
    省略時はファイル拡張子から自動検出。

**header**
:   データにヘッダー行があるか（CSV/TSV/SSV/Excel）。デフォルト: **true**。
    詳細は *DATA FORMATS* を参照。

**comment**
:   `#` 行のコメント処理（CSV/TSV/SSV）。デフォルト: **line**。
    モードについては *DATA FORMATS* を参照。

**columns**
:   固定カラム数（SSV のみ）。*DATA FORMATS* を参照。

**table**
:   シート名（Excel）またはテーブル名（SQLite）。

**startrow**
:   データの読み取り開始行（Excel）。整数、文字列、またはリストを受け付け。
    完全な構文は *DATA FORMATS* を参照。

**transpose**
:   行と列を入れ替え（Excel）。デフォルト: **false**。

**query**
:   データをフィルタリング・変換する SQL クエリ。SQL でのテーブル名は
    単一ソースブロックでは `data`。マルチテーブルブロックでは `data:`
    dict のキーを使用。

**config**
:   インライン設定の前にマージする外部 YAML 設定ファイルのパス。

## テンプレート

**define**
:   名前付きテンプレートを定義。ブロックは出力を生成しません。

**template**（または **as**）
:   以前に定義したテンプレートを使用。YAML ヘッダーでは `template` が
    推奨、属性では `as` がより短い。

## 変数

**with**
:   ブロックローカル変数。現在のブロック内でのみ利用可能。

**bind**
:   型保持バインディング（ドキュメント全体）。値は Jinja2 式で、
    結果の型（dict, list, int, bool）が保持されます。

**global**
:   ドキュメント全体の変数。値は文字列で、`{{` または `{%` を含む
    ものは Jinja2 テンプレートとして展開されます。

**alias**
:   すべての辞書に代替キーを追加。既存のキーは上書きしません。

**preamble**
:   Jinja2 制御構造（マクロ、`{% set %}`）を後続のすべてのブロックで共有。

## 属性構文

ドット記法で YAML ヘッダーなしにネスト値を設定:

    ```{.embedz data=file.csv as=template with.key=value}
    ```

両方が指定された場合、YAML 設定が属性値を上書きします。

## 処理順序

    preamble → with → query → データ読み込み → bind → global → alias → レンダリング

同一ブロック内で、前のステージの変数は後のステージで利用可能です。

# DATA FORMATS

データ形式はファイル拡張子から自動検出されます。上書きするには **format** を
使用してください。以下の形式がサポートされています:

**csv**（`.csv`）、**tsv**（`.tsv`）、**ssv**/**spaces**、**lines**（`.txt`）、
**json**（`.json`）、**yaml**（`.yaml`, `.yml`）、**toml**（`.toml`）、
**sqlite**（`.db`, `.sqlite`）、**excel**（`.xlsx`, `.xls`）。

JSON、YAML、TOML ファイルはそのまま `data` 変数に読み込まれます（リスト、
dict、またはネスト構造）。Lines 形式は文字列の単純なリストを生成します。
残りの形式には以下に説明する追加パラメータがあります。

## CSV, TSV, SSV

これらの表形式は以下のパラメータを共有します:

**header**（デフォルト: **true**）
:   true の場合、最初の行がカラム名として使用され、以降の各行は
    dict になります（`row.name`）。false の場合、行はインデックスで
    アクセスするリストになります（`row[0]`）。

**comment**（デフォルト: **line**）
:   `#` で始まる行の処理方法を制御。
    **line**: ファイル内のすべての `#` 行をスキップ。
    **head**: 先頭の連続する `#` 行のみスキップ（データ行中の `#` は保持）。
    **inline**: クォートされていない `#` から行末までスキップ。
    **none** または **false**: コメント処理を無効化。
    空白行はこの設定にかかわらず常に無視される。

**query**
:   データをフィルタリング・変換する SQL クエリ。データはインメモリの
    SQLite データベースに読み込まれ、SQL でのテーブル名は `data`。

SSV（空白区切り値）は連続する ASCII スペースを単一の区切り文字として
扱います。ノーブレークスペース（NBSP, `U+00A0`）や全角スペース
（`U+3000`）は区切り文字として扱われ**ない**ため、フィールド内で使用
できます。デフォルトのファイル拡張子はなく、`format: ssv` または
`format: spaces` を明示的に指定してください。

**columns**（SSV のみ）
:   固定カラム数。データは正確にこの数のカラムに分割され、最後のカラムは
    空白を含む残りのすべてのコンテンツをキャプチャします。最後のフィールドに
    自由形式のテキストがある場合に便利です。

## Excel

`openpyxl` パッケージが必要です（`pip install 'pandoc-embedz[excel]'`）。

**table**
:   読み込むシート名。デフォルトは最初のシート。

**header**（デフォルト: **true**）
:   CSV と同じ。`header: false` の場合、行はリストになります。

**startrow**
:   データ読み取り前に先頭行をスキップ。複数の形式を受け付けます:

    *整数*（1-indexed）
    :   この行番号から読み取りを開始。例: `startrow: 3`。

    *文字列*
    :   セルの値が文字列に完全一致する行を検索し、その行をヘッダー
        （`header: false` の場合は最初のデータ行）として使用。
        例: `startrow: name`。

    *"N:テキスト"*
    :   N 列目（1始まり）のみで検索。例: `startrow: "1:year"`。

    *リスト*
    :   すべてのパターンが同一行に一致する必要があります（AND 条件）。
        各要素はプレーン文字列または `"N:テキスト"` 形式。
        例: `startrow: [year, month]`。

**transpose**（デフォルト: **false**）
:   行と列を入れ替え。ヘッダーが最初の行ではなく最初の列に並んでいる
    場合に便利。`header: false` と組み合わせ可能。

以下の自動クリーンアップが適用されます:

- 先頭の空白行および全空列が除去されます。
- ヘッダー行の空セルには位置に基づく名前が自動生成されます（`column_0`,
  `column_2` など）。
- 重複するヘッダー名には連番が付与されます（`score`, `score_1`,
  `score_2`, ...）。
- データ行の空セルは空文字列になります。
- 空のシートは空のリスト `[]` を返し、標準エラー出力に警告を出力します。

**query** は CSV と同じ方法で動作します（インメモリ SQLite）。

## SQLite

SQLite データベースファイルを直接読み込みます。

**table**
:   読み込むテーブル名。すべての行と列が読み込まれます。

**query**
:   データベースに対して実行する SQL クエリ。**table** と **query** の
    両方が指定された場合、**query** が優先されます。

# VARIABLE SCOPING

**with** --- ブロックローカル、型そのまま
:   入力パラメータとローカル定数。

**bind** --- ドキュメント全体、型保持
:   計算値とデータアクセス。結果の型（dict, list, int, bool）が保持されます。

**global** --- ドキュメント全体、文字列型
:   ラベル、クエリ文字列。`{{` または `{%` を含む値は Jinja2 テンプレート
    として展開されます。

**alias** --- ドキュメント全体、キーのエイリアス
:   辞書の代替キー名。既存のキーは上書きしません。

**preamble** --- ドキュメント全体、Jinja2 制御構造
:   マクロと `{% set %}` 変数を後続のすべてのブロックで共有。

**bind:** の値は Jinja2 式です（文字列リテラルには引用符が必要:
`"'hello'"`）。**global:** の値は `{{` または `{%` を含まない限り
プレーン文字列です。

**bind:** と **global:** の両方でドット記法によるネスト値の設定が可能:

```yaml
bind:
  record: data | first
  record.note: "'bind で追加'"
global:
  record.label: 説明テキスト
```

# CUSTOM FILTERS

**to_dict**(*key*, *strict=True*, *transpose=False*)
:   dict のリストを指定フィールドをキーとする dict に変換。
    *strict=True*（デフォルト）の場合、重複キーでエラーを発生。
    *transpose=True* の場合、デュアルアクセス用にカラムキー付き dict を追加:
    `result[2023].value` と `result.value[2023]`。

**raise**
:   カスタムメッセージでエラーを発生。テンプレート検証に便利。

        {{ "label は必須です" | raise }}

**regex_replace**(*pattern*, *replacement=""*, *ignorecase=False*, *multiline=False*, *count=0*)
:   正規表現にマッチする部分文字列を置換。

        {{ text | regex_replace("[（）]", "") }}

**regex_search**(*pattern*, *ignorecase=False*, *multiline=False*)
:   パターンの最初のマッチを返すか、マッチしない場合は空文字列を返す。
    空文字列は Jinja2 の条件分岐で偽として評価されます。

        {% if value | regex_search("error|warning") %}...{% endif %}

# MULTI-TABLE DATA

複数のソースを読み込み SQL で結合:

```yaml
data:
  products: products.csv
  sales: sales.csv
query: |
  SELECT p.name, SUM(s.qty) as total
  FROM sales s JOIN products p ON s.id = p.id
  GROUP BY p.name
```

`query` がない場合、各テーブルは `data.tablename` でアクセスします。

`file:` dict 構文でソースごとのパラメータを指定:

```yaml
data:
  sheet1:
    file: report.xlsx
    table: Sheet1
  sheet2:
    file: report.xlsx
    table: Sheet2
    startrow: year
```

変数参照、ファイルパス、インラインデータは `data:` dict 内で自由に混在できます。

# EXAMPLES

## 基本的な CSV レンダリング

````
```{.embedz data=scores.csv}
{% for row in data %}
- {{ row.name }}: {{ row.score }}
{% endfor %}
```
````

## テンプレート再利用

````
```{.embedz define=item-list}
## {{ title }}
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```

```{.embedz data=products.csv as=item-list}
with:
  title: 商品リスト
```
````

## SQL 集計

````
```{.embedz data=sales.csv}
---
query: |
  SELECT product, SUM(amount) as total
  FROM data GROUP BY product
  ORDER BY total DESC
---
| 商品 | 合計 |
|------|------|
{% for row in data -%}
| {{ row.product }} | {{ row.total }} |
{% endfor %}
```
````

## スタンドアロンパイプライン

```
cat data.csv | pandoc-embedz -s transform.emz > output.csv
```

## 外部設定ファイル

```
pandoc-embedz -s report.tex -c config/base.yaml -o build/report.tex
```

設定ファイルは `---` で区切られた複数の YAML ドキュメントをサポートし、
論理的なグループ分けが可能です。

# ENVIRONMENT

**PANDOC_EMBEDZ_DEBUG**
:   デバッグ出力を有効化。**1**、**true**、または **yes** を受け付けます。
    フィルターモードとスタンドアロンモードの両方で動作します。

# FILES

*.emz*
:   スタンドアロンテンプレートの推奨拡張子（非 Markdown 出力）。

*.embedz*
:   スタンドアロンテンプレートの代替拡張子。

# SEE ALSO

**pandoc**(1)

Jinja2 テンプレートドキュメント: <https://jinja.palletsprojects.com/>

本マニュアルは構文、設定、データ形式、フィルターの完全なリファレンスです。
プロジェクトの README にはインストール手順、チュートリアル例、関連ツールの
情報があります:

<https://github.com/tecolicom/pandoc-embedz#readme>

# AUTHOR

Kazumasa Utashiro

# BUGS

バグ報告: <https://github.com/tecolicom/pandoc-embedz/issues>
