# pandoc-embedz

[![Tests](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml/badge.svg)](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/pandoc-embedz.svg)](https://badge.fury.io/py/pandoc-embedz)
[![Python Versions](https://img.shields.io/pypi/pyversions/pandoc-embedz.svg)](https://pypi.org/project/pandoc-embedz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Jinja2 テンプレートを使用して、Markdown ドキュメントにデータ駆動コンテンツを埋め込むための強力な [Pandoc](https://pandoc.org/) フィルター。最小限のセットアップでデータを美しいドキュメントに変換できます。

## 機能

- [Jinja2](https://jinja.palletsprojects.com/) 完全サポート: ループ、条件分岐、フィルター、マクロ、すべてのテンプレート機能
- 9種類のデータ形式: CSV、TSV、SSV、lines、JSON、YAML、TOML、SQLite、Excel
- ファイル拡張子からフォーマットを自動検出
- インラインデータブロックと外部ファイルの両方をサポート
- SQL クエリによるフィルタリング、集計、マルチテーブル JOIN
- `define`/`template` と `{% include %}` によるテンプレート再利用
- 変数スコープ: ローカル（`with:`）、グローバル（`global:`）、型保持（`bind:`）、プリアンブル
- カスタムフィルター: `to_dict`、`raise`、`regex_replace`、`regex_search`、`alias`
- シェルパイプラインや非 Markdown 出力のためのスタンドアロンレンダリングモード

## 概要

**インストール:**
```bash
pip install pandoc-embedz
```

**基本的な使い方:**
````markdown
```embedz
---
data: data.csv
---
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```
````

**テンプレート再利用:**
````markdown
```{.embedz define=item-list}
## {{ title }}
{% for item in data %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
```

```{.embedz data=products.csv as=item-list}
with:
  title: 商品リスト
```
````

_注意: `as=` は短縮形です。YAML ヘッダーでは `template:` が推奨されます。詳細は[テンプレート再利用](#テンプレート再利用)を参照してください。_

**レンダリング:**
```bash
pandoc report.md --filter pandoc-embedz -o output.pdf
```

CSV、JSON、YAML、TOML、SQLite、Excel などで動作します。始めるには[基本的な使い方](#基本的な使い方)を、SQLクエリ、マルチテーブル操作、データベースアクセスについては[高度な機能](#高度な機能)を参照してください。

## インストール

PyPI からインストール（安定版リリース）:

```bash
pip install pandoc-embedz
```

または GitHub から最新の main ブランチを直接取得:

```bash
pip install git+https://github.com/tecolicom/pandoc-embedz.git
```

依存関係: `panflute`, `jinja2`, `pandas`, `pyyaml`

**注意**: [Pandoc](https://pandoc.org/installing.html) を別途インストールする必要があります。インストール後、`man pandoc-embedz` で包括的なリファレンスマニュアルを参照できます。

## 基本的な使い方

以下の例は最も一般的なユースケースをカバーしています。ここから基本を学び始めてください。

### CSVファイル（自動検出）

````markdown
```embedz
---
data: data.csv
---
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```
````

### JSON構造

````markdown
```embedz
---
data: report.json
---
# {{ data.title }}

{% for section in data.sections %}
## {{ section.name }}
{% for item in section['items'] %}
- {{ item }}
{% endfor %}
{% endfor %}
```
````

### インラインデータ

````markdown
```embedz
---
format: json
---
{% for item in data %}
- {{ item.name }}: {{ item.count }}
{% endfor %}
---
[
  {"name": "Apple", "count": 10},
  {"name": "Banana", "count": 5}
]
```
````

### 条件分岐

Jinja2 の `if`/`elif`/`else` を使用して、データの値に基づいて異なるコンテンツを表示:

````markdown
```embedz
---
data: alerts.csv
---
{% for row in data %}
{% if row.severity == 'high' %}
- **緊急**: {{ row.title }}（{{ row.count }} 件）
{% elif row.severity == 'medium' %}
- {{ row.title }} - {{ row.count }} 件報告
{% else %}
- {{ row.title }}
{% endif %}
{% endfor %}
```
````

### テンプレート再利用

`define` でテンプレートを一度定義し、`template`（または短縮形の `as`）で再利用します。複数のデータソースで一貫したフォーマットを維持するのに最適です:

````markdown
```{.embedz define=item-list}
## {{ title }}
{% for item in data %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
```

```embedz
---
data: products.csv
template: item-list
with:
  title: 商品リスト
---
```

または属性構文でより簡潔に:

```{.embedz data=services.csv as=item-list}
with:
  title: サービスリスト
```
````

## コードブロック構文

embedz コードブロックは `---` で区切られた最大3つのセクションを持つことができます:

````markdown
```embedz
---
YAML設定
---
Jinja2テンプレート
---
インラインデータ（オプション）
```
````

- **最初の `---`**: YAMLヘッダーを開始
- **2番目の `---`**: YAMLヘッダーを閉じ、テンプレートセクションを開始
- **3番目の `---`**: テンプレートとインラインデータを分離（オプション）

### ブロックタイプ

**データ処理**（最も一般的） --- データを読み込み、テンプレートでレンダリング:

````markdown
```{.embedz data=file.csv}
{% for row in data %}
- {{ row.name }}
{% endfor %}
```
````

**テンプレート定義** --- 名前付きテンプレートを保存（出力なし）:

````markdown
```{.embedz define=my-template}
{% for item in data %}
- {{ item.value }}
{% endfor %}
```
````

**テンプレート使用** --- 以前に定義したテンプレートを適用:

````markdown
```{.embedz data=file.csv as=my-template}
```
````

属性経由で YAML 設定を使用:

````markdown
```{.embedz data=file.csv as=my-template}
with:
  title: レポート
```
````

**インラインデータを使用する場合**（3つの `---` セパレータに注意）:

````markdown
```embedz
---
template: my-template
format: json
---
---
[{"value": "item1"}, {"value": "item2"}]
```
````

構造は: YAMLヘッダー -> （空のテンプレートセクション） -> インラインデータ

**変数定義** --- 出力なしでグローバル変数を設定:

````markdown
```embedz
---
global:
  author: John Doe
  version: 1.0
---
```
````

### コンテンツ解釈（`---` なしの場合）

`---` セパレータがないブロックでは、属性に基づいてコンテンツが解釈されます:

| 属性 | コンテンツの解釈 |
|------|------------------|
| `data` + `template`/`as` | YAML設定 |
| `template`/`as` のみ | インラインデータ |
| `define` | テンプレート定義 |
| （なし）または `data` のみ | テンプレート |

`---` がある場合は、属性に関係なく標準の3セクション構造が適用されます。

> 設定オプションの完全なリファレンスは `man pandoc-embedz` を参照してください。

## 変数スコープ

pandoc-embedz は変数を管理するための5つのメカニズムを提供します:

| メカニズム | スコープ | 型の扱い | 用途 |
|------------|----------|----------|------|
| `with:` | ブロックローカル | そのまま | 入力パラメータ、ローカル定数 |
| `bind:` | ドキュメント全体 | 型保持（dict, list, int, bool） | データ抽出、計算 |
| `global:` | ドキュメント全体 | 文字列（テンプレート展開） | ラベル、メッセージ、クエリ文字列 |
| `alias:` | ドキュメント全体 | キーのエイリアス | 辞書の代替キー名 |
| `preamble:` | ドキュメント全体 | Jinja2制御構造 | マクロ、`{% set %}` 変数 |

**処理順序**: `preamble -> with -> query -> データ読み込み -> bind -> global -> alias -> レンダリング`

### with: によるローカル変数

パラメータと定数のためのブロックスコープ変数:

````markdown
```embedz
---
data: products.csv
with:
  tax_rate: 0.08
  currency: JPY
---
{% for item in data %}
- {{ item.name }}: {{ currency }} {{ (item.price * (1 + tax_rate)) | round(2) }}
{% endfor %}
```
````

### global: によるグローバル変数

ドキュメント全体の変数。`{{` または `{%` を含む値はテンプレートとして展開され、結果は常に**文字列**になります。

````markdown
```embedz
---
global:
  author: John Doe
  version: 1.0
---
```

```embedz
---
data: report.csv
---
# {{ author }} によるレポート

{% for row in data %}
- {{ row.item }}
{% endfor %}
```
````

> **注意**: `global.` プレフィックスはオプションです。型を保持した値（dict, list, int, bool）が必要な場合は、代わりに `bind:` を使用してください。

### bind: による型保持バインディング

式を評価しながら結果の型を保持:

````markdown
```embedz
---
format: csv
bind:
  first_row: data | first
  total: data | sum(attribute='value')
  has_data: data | length > 0
---
名前: {{ first_row.name }}, 合計: {{ total }}, データあり: {{ has_data }}
---
name,value
Alice,100
Bob,200
```
````

**ドット記法**によるネスト値の設定は `bind:` と `global:` の両方でサポート:

```yaml
bind:
  record: data | first
  record.note: "'bind で追加'"
global:
  record.label: 説明
```

> `alias:` と `preamble:` の詳細、ネスト構造やドット記法については `man pandoc-embedz` を参照してください。

## 高度な機能

強力なデータ処理、データベースアクセス、複雑なドキュメント生成ワークフローを実現する機能です。

### CSV/TSVへのSQLクエリ

SQL を使用して CSV/TSV データのフィルタリング、集計、変換:

````markdown
```embedz
---
data: sales.csv
query: |
  SELECT
    product,
    SUM(quantity) as total_quantity,
    SUM(amount) as total_sales
  FROM data
  GROUP BY product
  ORDER BY total_sales DESC
---
| 商品 | 数量 | 売上 |
|------|------|------|
{% for row in data -%}
| {{ row.product }} | {{ row.total_quantity }} | ¥{{ row.total_sales }} |
{% endfor -%}
```
````

**注意**: テーブル名は常に `data` です。CSV/TSV データはクエリのためにインメモリの SQLite データベースに読み込まれます。

#### クエリテンプレート変数

グローバル変数を使用して複数のブロック間で SQL クエリロジックを共有:

````markdown
```{.embedz}
---
global:
  year: 2024
  start_date: "{{ year }}-01-01"
  end_date: "{{ year }}-12-31"
  date_filter: date BETWEEN '{{ start_date }}' AND '{{ end_date }}'
---
```

```{.embedz data=sales.csv}
---
query: "SELECT * FROM data WHERE {{ date_filter }}"
---
{% for row in data %}
- {{ row.date }}: ¥{{ row.amount }}
{% endfor %}
```
````

変数は定義順に展開されるため、後の変数は前の変数を参照できます。

### SQLiteデータベース

SQLite データベースファイルを直接クエリ:

````markdown
```embedz
---
data: analytics.db
query: SELECT category, COUNT(*) as count FROM events WHERE date >= '2024-01-01' GROUP BY category
---
| カテゴリ | 件数 |
|----------|------|
{% for row in data -%}
| {{ row.category }} | {{ row.count }} |
{% endfor -%}
```
````

カスタムクエリなしで特定テーブルの全行を読み込む場合は `table` パラメータを使用します。

### Excelファイル

`.xlsx` / `.xls` ファイルを直接読み込みます。`openpyxl` が必要です（`pip install pandoc-embedz[excel]`）。先頭の空白行および全空列は自動的にスキップされます。

````markdown
```embedz
---
data: report.xlsx
table: Sheet2
---
{% for row in data %}
- {{ row.item }}
{% endfor %}
```
````

先頭に説明行がある場合は `startrow` でデータ開始行を指定します。整数（1-indexed）、文字列（自動検索）、リスト（AND条件）を指定可能:

````markdown
```{.embedz data=report.xlsx startrow="氏名"}
{% for row in data %}
- {{ row.氏名 }}: {{ row.値 }}
{% endfor %}
```
````

ヘッダーが最初の列に並んでいる場合は `transpose: true`、ヘッダー行がない場合は `header: false` を使用します。

> `startrow` の全構文や Excel 固有の詳細は `man pandoc-embedz` を参照してください。

### マルチテーブルデータ

複数のデータファイルを読み込み、直接アクセスまたは SQL で結合:

**直接アクセス（SQLなし）:**
````markdown
```embedz
---
data:
  config: config.yaml
  sales: sales.csv
---
# {{ data.config.title }}
{% for row in data.sales %}
- {{ row.date }}: {{ row.amount }}
{% endfor %}
```
````

**SQL JOIN（クエリを使用）:**
````markdown
```embedz
---
data:
  products: products.csv
  sales: sales.csv
query: |
  SELECT p.product_name, SUM(s.quantity) as total
  FROM sales s
  JOIN products p ON s.product_id = p.product_id
  GROUP BY p.product_name
---
{% for row in data %}
- {{ row.product_name }}: {{ row.total }}
{% endfor %}
```
````

**パラメータ付き `file:` dict（Excel シートなど）:**
````markdown
```embedz
---
data:
  incidents:
    file: data/report.xlsx
    table: Incidents
  phishing:
    file: data/report.xlsx
    table: Phishing
    startrow: year
query: |
  SELECT i.month, i.count, p.domestic
  FROM incidents i
  JOIN phishing p ON i.month = p.month
---
{% for row in data %}
- {{ row.month }}: {{ row.count }} (domestic: {{ row.domestic }})
{% endfor %}
```
````

変数参照、ファイルパス、インラインデータは `data:` dict 内で自由に混在できます。

**包括的な例とドキュメントについては [MULTI_TABLE.md](MULTI_TABLE.md) を参照してください。**

### テンプレートマクロ

Jinja2 マクロで再利用可能なテンプレート関数を作成:

````markdown
```{.embedz define=formatters}
{% macro format_item(title, date) -%}
**{{ title }}**（{{ date }}）
{%- endmacro %}
```

```embedz
---
data: vulnerabilities.csv
---
{% from 'formatters' import format_item %}

{% for item in data %}
- {{ format_item(item.title, item.date) }}
{% endfor %}
```
````

### プリアンブルとマクロ共有

`preamble` セクションで全ブロックで使用できる再利用可能な制御構造を定義。名前付きテンプレートも `{% from ... import %}` でマクロを共有可能:

````markdown
```{.embedz define=sql-macros}
{%- macro BETWEEN(start, end) -%}
SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
{%- endmacro -%}
```

```embedz
---
global:
  fiscal_year: 2024
  start_date: "{{ fiscal_year }}-04-01"
  end_date: "{{ fiscal_year + 1 }}-03-31"
  _import: "{% from 'sql-macros' import BETWEEN %}"
  yearly_query: "{{ BETWEEN(start_date, end_date) }}"
---
```
````

### CSV/TSV/SSV のコメント

`#` で始まる行はデフォルトでコメントとしてスキップされます。`comment` パラメータで動作を制御: `line`（デフォルト）、`head`、`inline`、`none`。

````markdown
```{.embedz data=data.csv comment=head}
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```
````

## スタンドアロンレンダリング

完全な Pandoc を実行せずに Markdown や LaTeX ファイルをレンダリング:

```bash
pandoc-embedz --standalone templates/report.tex -c config/base.yaml -o build/report.tex
```

**コマンドラインオプション:**

- `--standalone`（`-s`）スタンドアロンモードを有効化
- `--template TEXT`（`-t`）テンプレートテキストを直接指定
- `--format FORMAT`（`-f`）標準入力のデータ形式を指定
- `--config FILE`（`-c`）外部 YAML 設定ファイルを読み込み（繰り返し可能）
- `--output FILE`（`-o`）出力をファイルに書き込み（デフォルト: stdout）
- `--debug`（`-d`）stderr へのデバッグ出力を有効化

**クイック例:**

```bash
# 標準入力から CSV データをフォーマット
cat data.csv | pandoc-embedz -s -t '{% for row in data %}{{ row.name }}\n{% endfor %}' -f csv

# テンプレートファイルを使用（標準入力から自動読み取り）
cat data.csv | pandoc-embedz -s template.md

# データなしの静的テンプレート
pandoc-embedz -s -t '静的コンテンツ'
```

### 外部設定ファイル

フィルターモードとスタンドアロンモードの両方で共有設定を読み込み可能:

````markdown
```embedz
---
config:
  - config/base.yaml
  - config/overrides.yaml
---
```
````

```bash
pandoc-embedz -s report.md -c config/base.yaml -c config/latex.yaml
```

設定ファイルは `---` で区切られた複数の YAML ドキュメントをサポートし、論理的なグループ分けが可能です。

> 標準入力の動作、マルチドキュメント YAML、設定のマージの詳細は `man pandoc-embedz` を参照してください。

## ベストプラクティス

### CSV出力のエスケープ

テンプレートから CSV を生成する場合、適切なエスケープ用マクロを使用:

````markdown
{%- macro csv_escape(value) -%}
  {%- set v = value | string -%}
  {%- if ',' in v or '"' in v or '\n' in v -%}
    "{{ v | replace('"', '""') }}"
  {%- else -%}
    {{ v }}
  {%- endif -%}
{%- endmacro -%}
````

### ファイル拡張子の推奨

- **`.emz`** - スタンドアロンテンプレートの推奨拡張子（非 Markdown 出力）
- **`.embedz`** - 説明的な名前を好む場合の代替
- **`.md`** - テンプレートが Markdown を生成する場合のみ使用

### パイプライン処理

pandoc-embedz を他のツールと組み合わせてデータ変換パイプラインを構築:

```bash
extract_tool database table --columns 1-10 | \
  pandoc-embedz -s transform.emz | \
  post_process_tool > output.csv
```

パイプライン処理には `-s`（スタンドアロンモード）を使用。各 `.emz` ファイルが1つの変換ステップを処理します。

## デバッグ

`PANDOC_EMBEDZ_DEBUG` 環境変数（`1`、`true`、`yes` を受け付け）またはスタンドアロンモードの `-d` フラグでデバッグ出力を有効化:

```bash
PANDOC_EMBEDZ_DEBUG=1 pandoc input.md --filter pandoc-embedz -o output.pdf
pandoc-embedz -s -d template.md
```

## 関連ツール

### 類似の Pandoc フィルター（PyPI 上）

- **[pantable](https://pypi.org/project/pantable/)** - 強力なオプションを持つ CSV/TSV からテーブルへの変換、テーブルに特化
- **[pandoc-jinja](https://pypi.org/project/pandoc-jinja/)** - ドキュメント全体のメタデータ展開、コードブロック用ではない
- **[pandoc-include](https://pypi.org/project/pandoc-include/)** - テンプレートサポートを持つ外部ファイルのインクルード
- **[pandoc-pyrun](https://pypi.org/project/pandoc-pyrun/)** - コードブロック内で Python コードを実行

### その他のツール

- **[pandoc-csv2table](https://github.com/baig/pandoc-csv2table)**（Haskell）- CSV からテーブルへの変換のみ
- **[Quarto](https://quarto.org/)** - Pandoc ベースの包括的な出版システム。データサイエンスや技術文書に優れているが、専用の環境とワークフローが必要
- **[R Markdown](https://rmarkdown.rstudio.com/)** - Quarto に類似、R 環境が必要
- **[Lua フィルター](https://pandoc.org/lua-filters.html)** - 各ユースケースにカスタム Lua スクリプトが必要

### なぜ pandoc-embedz なのか？

pandoc-embedz は独自のニッチを埋めます:
- 完全な Jinja2 テンプレート（ループ、条件分岐、フィルター）
- 複数のデータ形式（CSV、JSON、YAML、TOML、SQLite、Excel など）
- コードブロックレベルの処理（ドキュメント全体ではない）
- 軽量 - 重い依存関係なし
- 既存の Pandoc ワークフローで動作

詳細な比較については [COMPARISON.md](COMPARISON.md) を参照してください。

## ドキュメント

- `man pandoc-embedz` --- 包括的なリファレンスマニュアル（オプション、構文、データ形式、変数スコープ、カスタムフィルター）
- [MULTI_TABLE.md](MULTI_TABLE.md) --- マルチテーブル SQL クエリの例
- [COMPARISON.md](COMPARISON.md) --- 代替ツールとの比較

## ライセンス

MIT ライセンス

Copyright © 2025-2026 Office TECOLI, LLC および Kazumasa Utashiro

詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 作者

Kazumasa Utashiro

## 貢献

貢献を歓迎します！イシューやプルリクエストをお気軽に提出してください。

### 開発環境のセットアップ

#### uv を使用（推奨）

```bash
# uv をインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# リポジトリをクローン
git clone https://github.com/tecolicom/pandoc-embedz.git
cd pandoc-embedz

# 依存関係をインストールし、開発環境をセットアップ
uv sync --all-extras

# テストを実行
uv run pytest tests/
```

#### pip を使用

```bash
# リポジトリをクローン
git clone https://github.com/tecolicom/pandoc-embedz.git
cd pandoc-embedz

# 仮想環境を作成
python -m venv .venv
source .venv/bin/activate  # Windows の場合: .venv\Scripts\activate

# 開発依存関係と共に編集可能モードでインストール
pip install -e .[dev]

# テストを実行
pytest tests/
```

詳細な開発ガイドラインについては [AGENTS.md](AGENTS.md) を参照してください。
