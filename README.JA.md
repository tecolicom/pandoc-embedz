# pandoc-embedz

[![Tests](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml/badge.svg)](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/pandoc-embedz.svg)](https://badge.fury.io/py/pandoc-embedz)
[![Python Versions](https://img.shields.io/pypi/pyversions/pandoc-embedz.svg)](https://pypi.org/project/pandoc-embedz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Jinja2 テンプレートを使用して、Markdown ドキュメントにデータ駆動コンテンツを埋め込むための強力な [Pandoc](https://pandoc.org/) フィルター。最小限のセットアップでデータを美しいドキュメントに変換できます。

## 機能

- **[Jinja2](https://jinja.palletsprojects.com/) 完全サポート**: ループ、条件分岐、フィルター、マクロ、すべてのテンプレート機能
- **8種類のデータ形式**: CSV、TSV、SSV/Spaces（空白区切り）、lines、JSON、YAML、TOML、SQLite
- **自動検出**: ファイル拡張子からフォーマットを自動検出
- **インライン・外部データ**: インラインデータブロックと外部ファイルの両方をサポート
- **SQLクエリ**: SQL を使用して CSV/TSV データのフィルタリング、集計、変換が可能
- **マルチテーブルSQL**: 複数ファイルを読み込み、JOINで結合
- **マルチテーブル直接アクセス**: 複数データセットを読み込み、それぞれに独立してアクセス
- **柔軟な構文**: YAMLヘッダーとコードブロック属性
- **テンプレート再利用**: 一度定義して複数回使用
- **テンプレートインクルード**: `{% include %}` でテンプレートをネスト
- **Jinja2マクロ**: パラメータ化されたテンプレート関数を作成
- **プリアンブルセクション**: ドキュメント全体の制御構造（マクロ、変数）を定義
- **変数スコープ**: ローカル（`with:`）、グローバル（`global:`）、型保持（`bind:`）、プリアンブル（`preamble:`）の管理
- **カスタムフィルター**: リストを辞書に変換する `to_dict`、テンプレート検証用の `raise`、パターン置換用の `regex_replace`、パターンマッチング用の `regex_search`、代替キー名用の `alias`
- **構造化データ**: ネストされた JSON/YAML 構造を完全サポート
- **スタンドアロンレンダリング**: `pandoc-embedz --standalone file1.tex file2.md` で、完全な Pandoc を実行せずにテンプレート（Markdown/LaTeX）を展開

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

CSV、JSON、YAML、TOML、SQLite などで動作します。始めるには[基本的な使い方](#基本的な使い方)を、SQLクエリ、マルチテーブル操作、データベースアクセスについては[高度な機能](#高度な機能)を参照してください。

## 目次

- [概要](#概要)
- [インストール](#インストール)
- [基本的な使い方](#基本的な使い方)
  - [CSVファイル（自動検出）](#csvファイル自動検出)
  - [JSON構造](#json構造)
  - [インラインデータ](#インラインデータ)
  - [条件分岐](#条件分岐)
  - [テンプレート再利用](#テンプレート再利用)
- [コードブロック構文](#コードブロック構文)
  - [基本構造](#基本構造)
  - [コンテンツ解釈ルール](#コンテンツ解釈ルール)
  - [ブロックタイプ](#ブロックタイプ)
- [変数スコープ](#変数スコープ)
  - [with: によるローカル変数](#with-によるローカル変数)
  - [global: によるグローバル変数](#global-によるグローバル変数)
  - [bind: による型保持バインディング](#bind-による型保持バインディング)
  - [エイリアス機能](#エイリアス機能)
- [高度な機能](#高度な機能)
  - [CSV/TSVへのSQLクエリ](#csvtsvへのsqlクエリ)
  - [SQLiteデータベース](#sqliteデータベース)
  - [マルチテーブルデータ](#マルチテーブルデータ)
  - [テンプレートマクロ](#テンプレートマクロ)
  - [プリアンブルとマクロ共有](#プリアンブルとマクロ共有)
- [スタンドアロンレンダリング](#スタンドアロンレンダリング)
  - [外部設定ファイル](#外部設定ファイル)
- [リファレンス](#リファレンス)
  - [使用パターン](#使用パターン)
    - [テンプレートインクルード](#テンプレートインクルード)
  - [サポートされるフォーマット](#サポートされるフォーマット)
  - [設定オプション](#設定オプション)
  - [data変数](#data変数)
  - [テンプレートコンテンツ](#テンプレートコンテンツ)
  - [Jinja2フィルター](#jinja2フィルター)
    - [組み込みフィルター](#組み込みフィルター)
    - [カスタムフィルター](#カスタムフィルター)
- [ベストプラクティス](#ベストプラクティス)
  - [CSV出力のエスケープ](#csv出力のエスケープ)
  - [ファイル拡張子の推奨](#ファイル拡張子の推奨)
  - [パイプライン処理パターン](#パイプライン処理パターン)
- [デバッグ](#デバッグ)
- [関連ツール](#関連ツール)
- [ドキュメント](#ドキュメント)
- [ライセンス](#ライセンス)
- [作者](#作者)
- [貢献](#貢献)

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

**注意**: [Pandoc](https://pandoc.org/installing.html) を別途インストールする必要があります。使い方については [Pandoc ドキュメント](https://pandoc.org/MANUAL.html) を参照してください。

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

Jinja2 の `if`/`elif`/`else` を使用して、データの値に基づいて異なるコンテンツを表示できます:

````markdown
```embedz
---
data: alerts.csv
---
{% for row in data %}
{% if row.severity == 'high' %}
- ⚠️ **緊急**: {{ row.title }}（{{ row.count }} 件）
{% elif row.severity == 'medium' %}
- ⚡ {{ row.title }} - {{ row.count }} 件報告
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

テンプレート定義、インラインデータを使った利用、その他のブロックパターンの詳細は[ブロックタイプ](#ブロックタイプ)を参照してください。

## コードブロック構文

embedz コードブロックの構造を理解することで、すべての機能を効果的に使用できます。

### 基本構造

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

### コンテンツ解釈ルール

コンテンツの解釈方法は `---` の有無と指定された属性によって異なります:

| 属性 | `---` の有無 | コンテンツの解釈 |
|------|-------------|------------------|
| （任意） | あり | 標準: YAML → テンプレート → データ |
| `data` + `template`/`as` | なし | **YAML設定** |
| `data=` + `template`/`as` | なし | **YAML設定**（データ読み込みなし） |
| `template`/`as` のみ | なし | インラインデータ |
| `define` | なし | テンプレート定義 |
| （なし）または `data` のみ | なし | テンプレート |

**重要なポイント**: `data` と `template`/`as` の両方が属性として指定されている場合、ブロックコンテンツ（`---` なし）は YAML 設定として解析されます。これにより簡潔な構文が可能になります:

````markdown
```{.embedz data=products.csv as=item-list}
with:
  title: 商品カタログ
```
````

これは以下と同等です:

````markdown
```embedz
---
data: products.csv
template: item-list
with:
  title: 商品カタログ
---
```
````

**ヒント**: データファイルを読み込まずに YAML 設定が必要な場合は `data=`（空の値）を使用します:

````markdown
```{.embedz data= as=report}
with:
  title: 四半期レポート
  year: 2024
```
````

### ブロックタイプ

#### 1. データ処理ブロック（最も一般的）

データを読み込み、テンプレートでレンダリングします:

````markdown
```embedz
---
data: file.csv
---
{% for row in data %}
- {{ row.name }}
{% endfor %}
```
````

**処理**: `file.csv` を読み込む → `data` として利用可能にする → テンプレートをレンダリング → 結果を出力

#### 2. テンプレート定義

`define:` で再利用可能なテンプレートを定義します:

````markdown
```{.embedz define=my-template}
{% for item in data %}
- {{ item.value }}
{% endfor %}
```
````

**処理**: テンプレートを "my-template" として保存 → 出力なし

#### 3. テンプレート使用

`template:`（または短縮形の `as:`）で以前に定義したテンプレートを使用します:

````markdown
```embedz
---
data: file.csv
template: my-template
---
```
````

または属性構文で（簡潔に `as=` を使用）:

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

構造は: YAMLヘッダー → 最初の `---` → （空のテンプレートセクション） → 2番目の `---` → インラインデータ

**処理**: データを読み込む → "my-template" を適用 → 結果を出力

#### 4. インラインデータ

ブロック内に直接埋め込まれたデータ:

````markdown
```embedz
---
format: json
---
{% for item in data %}
- {{ item.name }}
{% endfor %}
---
[
  {"name": "Alice"},
  {"name": "Bob"}
]
```
````

**処理**: インライン JSON を解析 → `data` として利用可能にする → テンプレートをレンダリング → 結果を出力

#### 5. 変数定義

出力なしでグローバル変数を設定:

````markdown
```embedz
---
global:
  author: John Doe
  version: 1.0
---
```
````

**処理**: グローバル変数を設定 → 出力なし

グローバル/ローカル変数だけを使用するスニペットをレンダリングする必要がある場合は、`data:` を省略するだけです。データセットが提供されていなくてもテンプレートコンテンツを持つ `.embedz` ブロックはレンダリングされます:

````markdown
```embedz
---
with:
  author: Jane Doe
---
作成者: {{ author }}
```
````

## 変数スコープ

変数の動作を理解することは、複雑なテンプレートを構築するために不可欠です。pandoc-embedz は変数を管理するための4つのメカニズムを提供します:

| メカニズム | スコープ | 型の扱い | 用途 |
|------------|----------|----------|------|
| `with:` | ブロックローカル | そのまま | 入力パラメータ、ローカル定数 |
| `bind:` | ドキュメント全体 | 型保持（dict, list, int, bool） | データ抽出、計算 |
| `global:` | ドキュメント全体 | 文字列（テンプレート展開） | ラベル、メッセージ、クエリ文字列 |
| `alias:` | ドキュメント全体 | キーのエイリアス | 辞書の代替キー名 |
| `preamble:` | ドキュメント全体 | Jinja2制御構造 | マクロ、`{% set %}` 変数 |

**処理順序**: preamble → with → query → データ読み込み → bind → global → alias → レンダリング

- `with:` 変数は `query:` と後続のすべてのステージで利用可能
- `bind:` はデータ読み込み後に評価され、式の結果の型を保持
- `global:` は `bind:` の後に評価され、データと bind の結果の両方を参照可能
- すべてのドキュメント全体の変数はブロック間で永続化

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
# グローバル変数を設定
```embedz
---
global:
  author: John Doe
  version: 1.0
---
```

# 後続のブロックで使用
```embedz
---
data: report.csv
---
# {{ global.author }} によるレポート
バージョン {{ global.version }}

{% for row in data %}
- {{ row.item }}
{% endfor %}
```
````

> **注意**: `global.` プレフィックスはオプションです。`{{ global.author }}` の代わりに `{{ author }}` を使用できます。

> **重要**: すべての `global:` 値は展開後に文字列になります。型を保持した値（dict, list, int, bool）が必要な場合は、代わりに `bind:` を使用してください。

### bind: による型保持バインディング

式を評価しながら結果の型（dict, list, int, bool）を保持します:

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

値を文字列に変換する `global:` とは異なり、`bind:` は元の型を保持するため、`{{ first_row.name }}` のようなプロパティアクセスが可能です。

**ネストされた構造**もサポートされています:

````markdown
```embedz
---
format: csv
bind:
  first: data | first
  stats:
    name: first.name
    value: first.value
    doubled: first.value * 2
---
{{ stats.name }}: {{ stats.value }} (2倍: {{ stats.doubled }})
---
name,value
Alice,100
```
````

ネストされた値を設定するための**ドット記法**:

````markdown
```embedz
---
format: csv
bind:
  record: data | first
  record.note: "'bind で追加'"   # record dict に 'note' キーを追加
global:
  record.label: 説明             # 'label' キーを追加（引用符不要）
---
{{ record.name }}: {{ record.note }}, {{ record.label }}
---
name,value
Alice,100
```
````

> **注意**: `bind:` では、値は Jinja2 式です（文字列リテラルには引用符が必要）。
> `global:` では、`{{` または `{%` を含まない限り、値はプレーンな文字列です。

### エイリアス機能

`alias:` セクションはすべての辞書に代替キーを追加します:

````markdown
```embedz
---
format: csv
bind:
  item:
    label: |-
      "アイテム説明"
    value: 100
alias:
  description: label  # 'description' は 'label' のエイリアスになる
---
{{ item.description }}: {{ item.value }}
---
name,value
dummy,0
```
````

エイリアスはすべてのネストされた辞書に再帰的に適用され、既存のキーを上書きしません。

## 高度な機能

これらの機能により、強力なデータ処理、データベースアクセス、複雑なドキュメント生成ワークフローが可能になります。

### CSV/TSVへのSQLクエリ

SQL を使用して CSV/TSV データのフィルタリング、集計、変換ができます。四半期レポート、データ分析、大規模データセットの処理に最適です:

````markdown
```embedz
---
data: transactions.csv
query: SELECT * FROM data WHERE date BETWEEN '2024-01-01' AND '2024-03-31' ORDER BY amount DESC
---
## 2024年第1四半期のトランザクション

{% for row in data %}
- {{ row.date }}: ¥{{ row.amount }} - {{ row.description }}
{% endfor %}
```
````

レポート用の集計例:

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
  WHERE date >= '2024-01-01' AND date <= '2024-03-31'
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

Jinja2 テンプレート変数を使用して、複数の embedz ブロック間で SQL クエリロジックを共有します。異なるデータセットに同じフィルター条件を適用する必要がある場合に便利です:

**クエリ用のグローバル変数を定義:**
````markdown
```{.embedz}
---
global:
  start_date: 2024-01-01
  end_date: 2024-03-31
---
```
````

**クエリで変数を使用:**
````markdown
```{.embedz data=sales.csv}
---
query: SELECT * FROM data WHERE date BETWEEN '{{ global.start_date }}' AND '{{ global.end_date }}'
---
## 売上（{{ global.start_date }} ～ {{ global.end_date }}）
{% for row in data %}
- {{ row.product }}: ¥{{ row.amount }}
{% endfor %}
```

```{.embedz data=expenses.csv}
---
query: SELECT * FROM data WHERE date BETWEEN '{{ global.start_date }}' AND '{{ global.end_date }}'
---
## 経費（{{ global.start_date }} ～ {{ global.end_date }}）
{% for row in data %}
- {{ row.category }}: ¥{{ row.amount }}
{% endfor %}
```
````

> **注意:** `global.` プレフィックスはオプションです。`{{ global.start_date }}` の代わりに `{{ start_date }}` を使用できます。プレフィックスは、グローバル変数とローカル変数の両方がある場合に明確にするために使用できます。

**完全なクエリを変数として保存:**
````markdown
```{.embedz}
---
global:
  high_value_filter: SELECT * FROM data WHERE amount > 1000 ORDER BY amount DESC
---
```

```{.embedz data=transactions.csv}
---
query: "{{ global.high_value_filter }}"
---
## 高額トランザクション
{% for row in data %}
- {{ row.date }}: ¥{{ row.amount }}
{% endfor %}
```
````

**ネストされた変数参照:**

グローバル変数は他のグローバル変数を参照でき、再利用可能なコンポーネントから複雑なクエリを構築できます:

````markdown
```{.embedz}
---
global:
  year: 2024
  start_date: "{{ global.year }}-01-01"
  end_date: "{{ global.year }}-12-31"
  date_filter: date BETWEEN '{{ global.start_date }}' AND '{{ global.end_date }}'
---
```

```{.embedz data=sales.csv}
---
query: "SELECT * FROM data WHERE {{ global.date_filter }}"
---
## {{ global.year }}年売上レポート
{% for row in data %}
- {{ row.date }}: ¥{{ row.amount }}
{% endfor %}
```
````

変数は定義順に展開されるため、後の変数は前の変数を参照できます。

テンプレート展開は `global` と `with` 変数で動作し、すべてのクエリ機能（CSV、TSV、SSV、SQLite データベース）をサポートします。

### SQLiteデータベース

SQLite データベースファイルを直接クエリします。`table` パラメータを使用して、データベースから読み取るテーブルを指定します:

````markdown
```embedz
---
data: users.db
table: users
---
{% for user in data %}
- {{ user.name }}（{{ user.email }}）
{% endfor %}
```
````

またはカスタム SQL クエリを使用（`query` パラメータは `table` を上書きします）:

````markdown
```embedz
---
data: analytics.db
query: SELECT category, COUNT(*) as count FROM events WHERE date >= '2024-01-01' GROUP BY category
---
## イベント統計

| カテゴリ | 件数 |
|----------|------|
{% for row in data -%}
| {{ row.category }} | {{ row.count }} |
{% endfor -%}
```
````

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
  products: products.csv  # SQL内のテーブル名
  sales: sales.csv        # SQL内のテーブル名
query: |
  SELECT p.product_name, SUM(s.quantity) as total
  FROM sales s            # ここでテーブル名を使用
  JOIN products p ON s.product_id = p.product_id
  GROUP BY p.product_name
---
{% for row in data %}     <!-- 結果は 'data' に格納 -->
- {{ row.product_name }}: {{ row.total }}
{% endfor %}
```
````

**インラインデータ（外部ファイルなし）:**
````markdown
```embedz
---
data:
  config:
    format: yaml
    data: |
      title: "売上レポート"
  sales: |              # 複数行文字列 = インライン CSV
    product,amount
    Widget,1280
    Gadget,2480
---
# {{ data.config.title }}
{% for row in data.sales %}
- {{ row.product }}: ¥{{ "{:,}".format(row.amount|int) }}
{% endfor %}
```
````

**包括的な例とドキュメントについては [MULTI_TABLE.md](MULTI_TABLE.md) を参照してください。**

### テンプレートマクロ

Jinja2 マクロを使用して、パラメータ付きの再利用可能なテンプレート関数を作成します。複雑なフォーマットには `{% include %}` よりも柔軟です:

````markdown
# マクロを定義
```{.embedz define=formatters}
{% macro format_item(title, date) -%}
**{{ title }}**（{{ date }}）
{%- endmacro %}

{% macro severity_badge(level) -%}
  {% if level == "high" -%}
    🔴 高
  {%- elif level == "medium" -%}
    🟡 中
  {%- else -%}
    🟢 低
  {%- endif %}
{%- endmacro %}
```

# import でマクロを使用
```embedz
---
data: vulnerabilities.csv
---
{% from 'formatters' import format_item, severity_badge %}

## 脆弱性レポート
{% for item in data %}
- {{ format_item(item.title, item.date) -}}
  {{- " - " -}}
  {{- severity_badge(item.severity) }}
{% endfor %}
```
````

**マクロ vs インクルード**:
- **マクロ**: パラメータを受け取り、より柔軟、明示的なインポートが必要
- **インクルード**: よりシンプル、現在のコンテキストを自動的に使用、パラメータなし

詳細な `{% include %}` の例については[テンプレートインクルード](#テンプレートインクルード)を参照してください。

### プリアンブルとマクロ共有

`preamble` セクションと名前付きテンプレートを使用して、すべての embedz ブロックがアクセスできる再利用可能な制御構造を定義します。

> **注意**: `preamble` で `{% set %}` を使用して定義された変数は Jinja2 テンプレート変数であり、Python データとして保存される `global` 変数とは異なります。制御フローには `preamble` を、データストレージには `global` を使用してください。

**マクロを共有する**（`global` セクション内の変数間で共有する別のアプローチ）:

````markdown
# 名前付きテンプレートでマクロを定義
```{.embedz define=sql-macros}
{%- macro BETWEEN(start, end) -%}
SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
{%- endmacro -%}
```

# グローバル変数でマクロをインポートして使用
```embedz
---
global:
  fiscal_year: 2024
  start_date: "{{ fiscal_year }}-04-01"
  end_date: "{{ fiscal_year + 1 }}-03-31"

  # 名前付きテンプレートからマクロをインポート
  # 変数名は任意。インポートは {% from ... %} 構文で認識される
  _import: "{% from 'sql-macros' import BETWEEN %}"

  # インポートしたマクロを使用
  yearly_query: "{{ BETWEEN(start_date, end_date) }}"
---
```

# 生成されたクエリを使用
```embedz
---
data: events.csv
query: "{{ yearly_query }}"
---
{% for event in data %}
- {{ event.name }}: {{ event.date }}
{% endfor %}
```
````

このパターンは以下に便利です:
- **クエリビルダー**: SQL クエリマクロを一度定義し、複数のグローバル変数で使用
- **日付計算**: 会計期間、四半期などの日付範囲マクロを作成
- **複雑な変換**: 複数ステップのロジックを再利用可能なマクロにカプセル化

## リファレンス

技術仕様と構文の詳細。

### 使用パターン

複雑なテンプレートを構成するための集中ガイド。

#### テンプレートインクルード

複雑なレイアウトを小さなフラグメントに分割し、`{% include %}` でつなぎ合わせます。各フラグメントを `define` で定義し、ループ内で再利用することで、フォーマットを一元管理できます。

````markdown
# フォーマットフラグメントを定義
```{.embedz define=date-format}
📅 {{ item.date }}
```

```{.embedz define=title-format}
**{{ item.title }}**
```

# ループ内でフラグメントを構成
```embedz
---
data: incidents.csv
---
{% for item in data %}
- {% include 'date-format' with context -%}
  {{- " " -}}
  {%- include 'title-format' with context %}
{% endfor %}
```
````

`with context` 句は現在のループ変数を転送するため、インクルードされたテンプレートは `item` を読み取ることができます。インクルードをレイヤー化することもできます。例:

````markdown
```{.embedz define=severity-badge}
{% if item.severity == "high" -%}
  🔴
{%- elif item.severity == "medium" -%}
  🟡
{%- else -%}
  🟢
{%- endif %}
```

```embedz
---
data: vulnerabilities.csv
---
## 脆弱性
{% for item in data %}
- {% include 'severity-badge' with context %} {{ item.title }}
{% endfor %}
```
````

### サポートされるフォーマット

| フォーマット | 拡張子 | 説明 |
|--------------|--------|------|
| CSV | `.csv` | カンマ区切り値（ヘッダーサポート） |
| TSV | `.tsv` | タブ区切り値（ヘッダーサポート） |
| SSV/Spaces | - | 空白区切り値（`format: ssv` または `format: spaces` で指定） |
| Lines | `.txt` | 1行に1アイテム（プレーンテキスト） |
| JSON | `.json` | 構造化データ（リストとオブジェクト） |
| YAML | `.yaml`, `.yml` | 階層構造を持つ構造化データ |
| TOML | `.toml` | 構造化データ（YAML/JSON に類似） |
| SQLite | `.db`, `.sqlite` | データベースファイル（`.sqlite3` も可。`table` または `query` パラメータが必要） |

**注意**: SSV（空白区切り値）は連続する空白とタブを単一の区切り文字として扱うため、手動で整列されたデータに最適です。`ssv` と `spaces` は同じ意味で使用できます。

**固定カラム数の SSV**: `columns` パラメータを使用して、最後のカラムの空白を保持:

````markdown
```{.embedz format=spaces columns=3}
ID  Name   Description
1   Alice  Software engineer
2   Bob    Project manager with team
```
````

`columns=3` を指定すると、データは正確に3カラムに分割されます。最後のカラムは空白を含む残りのすべての内容をキャプチャし、自由形式のテキストフィールドに便利です。

### 設定オプション

#### YAMLヘッダー

| キー | 説明 | 例 |
|------|------|-----|
| `data` | データソース: ファイルパス（文字列）、複数ファイル（dict）、またはインラインデータ（複数行文字列または `data` キーを持つdict） | `data: stats.csv` または `data: {sales: sales.csv}` または `data: \|<br>  name,value<br>  ...` |
| `format` | データ形式: `csv`, `tsv`, `ssv`/`spaces`, `json`, `yaml`, `toml`, `sqlite`, `lines`（拡張子から自動検出） | `format: json` |
| `define` | テンプレート名（定義用） | `define: report-template` |
| `template`（または `as`） | 使用するテンプレート（両方のエイリアスが動作、YAML では `template` 推奨、属性では `as` が短い） | `template: report-template` または `as: report-template` |
| `with` | ローカル変数（ブロックスコープ） | `with: {threshold: 100}` |
| `bind` | 型保持バインディング（式を評価し、dict/list/int/bool 型を保持） | `bind: {first: data \| first}` |
| `global` | グローバル変数（ドキュメントスコープ、文字列値） | `global: {author: "John"}` |
| `alias` | すべての dict に代替キーを追加（bind/global の後に適用） | `alias: {description: label}` |
| `preamble` | ドキュメント全体の制御構造（マクロ、`{% set %}`、インポート） | `preamble: \|`<br>`  {% set title = 'Report' %}` |
| `header` | CSV/TSV/SSV にヘッダー行がある（デフォルト: true） | `header: false` |
| `columns` | SSV フォーマットの固定カラム数（最後のカラムが残りの内容を取得） | `columns: 3` |
| `table` | SQLite テーブル名（sqlite フォーマットに必須） | `table: users` |
| `query` | SQLite、CSV/TSV フィルタリング、またはマルチテーブル JOIN 用の SQL クエリ（マルチテーブルモードに必須） | `query: SELECT * FROM data WHERE active=1` |
| `config` | インライン設定の前にマージされる外部 YAML 設定ファイル（文字列またはリスト） | `config: config/base.yaml` |

**後方互換性:**
- `name` パラメータ（非推奨）: まだ動作しますが警告が表示されます。代わりに `define` を使用してください。

#### 属性構文

属性は YAML の代わりに、または YAML と組み合わせて使用できます:

```markdown
{.embedz data=file.csv as=template}
{.embedz define=template}
{.embedz data=file.csv as=template with.threshold=100}
{.embedz global.author="John"}
```

ドット記法（例: `with.key=value`、`global.key=value`）はネストされた辞書値を設定します。これは YAML ヘッダーを書かずにテンプレートにパラメータを渡す場合に特に便利です。

**優先順位**: 両方が指定された場合、YAML 設定が属性値を上書きします。

YAML ヘッダーの繰り返しを避けたい場合は、属性で `config=/path/file.yaml`（必要に応じて繰り返し）を使用して、ブロック本体の外で共有設定を読み込むこともできます。

### data変数

`data` 変数はテンプレート内で読み込まれたデータへのアクセスを提供します。

#### データソース

データは以下から読み込めます:

- **ファイル**: `data=products.csv` はファイルから読み込み
- **インライン**: 2番目の `---` 区切り文字の後のデータセクション
- **変数参照**: `data=varname` は `bind:` 変数（dict または list）を使用
- **SQLクエリ**: `query:` は SQL 経由で読み込んだデータをフィルタリング/変換

#### データ構造

`data` の構造はソースによって異なります:

- 単一ファイル/インライン: `data` は行のリスト（JSON/YAML の場合は dict）
- クエリなしのマルチテーブル: `data` は dict、`data.table_name` でアクセス
- クエリありのマルチテーブル: `data` は SQL クエリ結果のリスト
- 変数参照: 参照される変数と同じ構造

#### 変数参照

`bind:` 変数（dict または list）を `data=` 属性で直接参照できます:

````markdown
```embedz
---
format: csv
bind:
  by_year: data | to_dict(key='year')
---
---
year,value
2023,100
2024,200
```

```{.embedz data=by_year}
2024の値: {{ data[2024].value }}
```
````

**解決ルール:**

1. `data=` に `/` または `.` が含まれる → ファイルパスとして扱う
2. 名前が `bind:` 変数に dict または list として存在する → その変数を使用
3. それ以外 → ファイルとして読み込みを試みる

**ユースケース:**

- **処理済みデータの再利用**: 一度データを読み込み、`to_dict` で変換し、複数のブロックで使用
- **テンプレート間でデータを共有**: 1つのブロックでデータ構造を定義し、他のブロックで参照
- **冗長なファイル読み込みを回避**: 大きなデータセットを一度処理し、結果を参照

**変数データへのクエリ適用:**

変数データに `query:` を適用でき、強力なデータ変換パイプラインが可能になります:

````markdown
<!-- 生データを一度読み込む -->
```{.embedz data=sales.csv}
---
bind:
  raw_sales: data
---
```

<!-- 生データから月次サマリーを作成 -->
```{.embedz data=raw_sales}
---
query: |
  SELECT month, SUM(amount) as total
  FROM data
  GROUP BY month
bind:
  monthly: data | to_dict(key='month')
---
```

<!-- 同じ生データから年次サマリーを作成 -->
```{.embedz data=raw_sales}
---
query: |
  SELECT year, SUM(amount) as total
  FROM data
  GROUP BY year
bind:
  yearly: data | to_dict(key='year')
---
```
````

これにより以下が可能になります:
- 一度ファイルを読み込み、複数の集計を導出
- 同じソースデータに異なる SQL クエリを適用
- 冗長なファイル I/O なしで複雑なデータパイプラインを構築

> **注意**: 変数が dict（例: `to_dict` から）を含む場合、クエリを適用する前に自動的に値のリストに変換されます。

> **注意**: 変数参照とインラインデータは組み合わせできません。`data=varname` または `---` の後のインラインデータのいずれかを使用してください。両方は使用できません。

#### その他の変数

テンプレートコンテンツは以下にもアクセスできます:

- `with:` からの変数（ローカルスコープ）
- `global:` からの変数（ドキュメントスコープ）
- `bind:` からの変数（型保持、ドキュメントスコープ）

### テンプレートコンテンツ

Jinja2 構文を完全な機能サポートで使用:

- 変数: `{{ variable }}`
- ループ: `{% for item in data %} ... {% endfor %}`
- 条件分岐: `{% if condition %} ... {% endif %}`
- フィルター: `{{ value | filter }}`
- マクロ: `{% macro name(args) %} ... {% endmacro %}`
- インクルード: `{% include 'template-name' %}`

Jinja2 テンプレート構文と機能の詳細については、[Jinja2 ドキュメント](https://jinja.palletsprojects.com/) を参照してください。

**出力形式に関する注意:**
- **フィルターモード**（`.embedz` コードブロック）: テンプレート出力は Markdown として解釈され、さらなる処理のために Pandoc に戻されます。テンプレート内で Markdown 構文（`**太字**`、`- リスト`、`[リンク]()`など）や LaTeX コマンド（`\textbf{}`など）を使用できます。
- **スタンドアロンモード**（`-s` フラグ）: テンプレート出力はプレーンテキストで、処理されません。CSV、JSON、設定ファイル、その他の非 Markdown コンテンツの生成に使用します。

### Jinja2フィルター

フィルターはパイプ（`|`）構文を使用して値を変換します: `{{ value | filter }}`。

#### 組み込みフィルター

Jinja2 は多くの便利なフィルターを提供しています。以下はデータ処理によく使うものです:

| フィルター | 説明 | 例 |
|------------|------|-----|
| `first` | リストの最初の項目 | `{{ data \| first }}` |
| `last` | リストの最後の項目 | `{{ data \| last }}` |
| `length` | 項目数 | `{{ data \| length }}` |
| `sum` | 値の合計 | `{{ data \| sum(attribute='value') }}` |
| `sort` | リストをソート | `{{ data \| sort(attribute='name') }}` |
| `selectattr` | 属性でフィルタリング | `{{ data \| selectattr('active', 'true') }}` |
| `map` | 属性を抽出 | `{{ data \| map(attribute='name') \| list }}` |
| `join` | 項目を結合 | `{{ items \| join(', ') }}` |
| `default` | デフォルト値 | `{{ value \| default('N/A') }}` |
| `round` | 数値を丸める | `{{ price \| round(2) }}` |

**例:**

```jinja2
{# 合計売上を取得 #}
{{ data | sum(attribute='amount') }}

{# 高額アイテムをフィルタリング #}
{% for item in data | selectattr('value', 'gt', 100) %}
- {{ item.name }}: {{ item.value }}
{% endfor %}

{# 日付で降順ソート #}
{% for row in data | sort(attribute='date', reverse=true) %}
- {{ row.date }}: {{ row.title }}
{% endfor %}

{# カンマ付き数値フォーマット #}
{{ amount | int | string | default('0') }}
```

完全なリストは [Jinja2 組み込みフィルター](https://jinja.palletsprojects.com/en/latest/templates/#builtin-filters) を参照してください。

#### カスタムフィルター

pandoc-embedz は追加のフィルターを提供します:

**`to_dict(key, strict=True, transpose=False)`** - 辞書のリストを指定されたフィールドをキーとする辞書に変換します。

これは、リスト全体を反復処理する代わりに、特定のキー（年、ID、名前など）でレコードにアクセスする必要がある場合に便利です。一般的なユースケース:

- **前年比比較**: 今年と昨年のデータに直接アクセス
- **ルックアップテーブル**: 迅速なアクセスのために ID からレコードへのマッピングを作成
- **相互参照**: 共通キーで異なるソースからデータを結合

```jinja2
{{ data | to_dict(key='year') }}
{# 入力:  [{'year': 2023, 'value': 100}, {'year': 2024, 'value': 200}]
   出力: {2023: {'year': 2023, 'value': 100}, 2024: {'year': 2024, 'value': 200}} #}

{# キーワードなしの短縮形（これも有効）: #}
{{ data | to_dict(key='year') }}
```

**例 - 前年比比較:**

````markdown
```embedz
---
format: csv
bind:
  by_year: data | to_dict(key='year')
  current: by_year[2024]
  previous: by_year[2023]
  growth: (current.value - previous.value) / previous.value * 100
---
2024: {{ current.value }}（2023比 {{ growth | round(1) }}%）
---
year,value
2023,100
2024,120
```
````

**strictモード**（デフォルト）: 重複キーが見つかった場合に `ValueError` を発生させ、データの整合性を保証:

```jinja2
data | to_dict(key='id')                {# 重複IDがあるとエラー #}
data | to_dict(key='id', strict=False)  {# 重複を許可、最後の値が優先 #}
```

**transposeモード**: デュアルアクセスパターン用にカラムキー付き辞書を追加:

```jinja2
{{ data | to_dict(key='year', transpose=True) }}
{# 入力:  [{'year': 2023, 'value': 100}, {'year': 2024, 'value': 200}]
   出力: {2023: {'year': 2023, 'value': 100},
          2024: {'year': 2024, 'value': 200},
          'value': {2023: 100, 2024: 200}} #}
```

これにより両方のアクセスパターンが可能になります:
- `result[2023].value` - 年でアクセスし、次にカラム
- `result.value[2023]` - カラムでアクセスし、次に年（テンプレートに渡すのに便利）

---

**`raise`** - カスタムメッセージでエラーを発生させます。テンプレートで必須パラメータを検証するのに便利:

```jinja2
{%- if label is not defined -%}
{{ "テンプレートエラー: label は必須です" | raise }}
{%- endif -%}
```

---

**`regex_replace(pattern, replacement='', ignorecase=False, multiline=False, count=0)`** - 正規表現を使用して部分文字列を置換します。Ansible の `regex_replace` フィルターと互換性があります。

```jinja2
{# 基本的な置換 #}
{{ "Hello World" | regex_replace("World", "Universe") }}
{# 出力: Hello Universe #}

{# キャプチャグループ付きパターン #}
{{ "ansible" | regex_replace("^a.*i(.*)$", "a\\1") }}
{# 出力: able #}

{# 文字を削除（空の置換） #}
{{ "Hello（World）" | regex_replace("[（）]", "") }}
{# 出力: HelloWorld #}

{# 大文字小文字を区別しないマッチング #}
{{ "Hello WORLD" | regex_replace("world", "Universe", ignorecase=true) }}
{# 出力: Hello Universe #}

{# マルチラインモード（^ は各行の先頭にマッチ） #}
{{ "foo\nbar\nbaz" | regex_replace("^b", "B", multiline=true) }}
{# 出力: foo\nBar\nBaz #}

{# 置換回数を制限 #}
{{ "foo=bar=baz" | regex_replace("=", ":", count=1) }}
{# 出力: foo:bar=baz #}

{# Unicode プロパティ（regex モジュールが必要） #}
{{ "Hello（World）" | regex_replace("\\p{Ps}|\\p{Pe}", "") }}
{# 出力: HelloWorld - すべての開き/閉じ括弧を削除 #}
```

**パラメータ:**
- `pattern`: マッチする正規表現パターン
- `replacement`: 置換文字列（デフォルト: 削除用の空文字列）
- `ignorecase`: 大文字小文字を区別しないマッチング（デフォルト: False）
- `multiline`: `^` が各行の先頭にマッチするマルチラインモード（デフォルト: False）
- `count`: 最大置換回数、0 は無制限（デフォルト: 0）

**戻り値:** マッチした部分文字列がすべて置換された文字列。

**Unicodeプロパティ:** `regex` モジュールがインストールされている場合、`\p{P}`（句読点）、`\p{L}`（文字）、`\p{Ps}`（開き括弧）、`\p{Pe}`（閉じ括弧）などの Unicode プロパティエスケープがサポートされます。`pip install regex` でインストールしてください。

---

**`regex_search(pattern, ignorecase=False, multiline=False)`** - パターンを検索してマッチした文字列を返します。Ansible の `regex_search` フィルターと互換性があります。

```jinja2
{# 基本的な検索 #}
{{ "Hello World" | regex_search("World") }}
{# 出力: World #}

{# マッチしない場合は空文字列 #}
{{ "Hello World" | regex_search("Foo") }}
{# 出力: （空文字列） #}

{# 選択パターン #}
{{ "備考: 保留中です" | regex_search("保留|済|喪中") }}
{# 出力: 保留 #}

{# 大文字小文字を区別しない検索 #}
{{ "Hello WORLD" | regex_search("world", ignorecase=true) }}
{# 出力: WORLD #}

{# 条件分岐での使用（空文字列は偽） #}
{% if value | regex_search("error|warning") %}
  問題を検出: {{ value }}
{% endif %}
```

**パラメータ:**
- `pattern`: 検索する正規表現パターン
- `ignorecase`: 大文字小文字を区別しないマッチング（デフォルト: False）
- `multiline`: `^` が各行の先頭にマッチするマルチラインモード（デフォルト: False）

**戻り値:** 最初にマッチした部分文字列、またはマッチしない場合は空文字列。空文字列は Jinja2 の条件分岐で偽として評価されるため、`{% if %}` 文で簡単に使用できます。

## スタンドアロンレンダリング

完全な Pandoc 変換を実行せずに Markdown または LaTeX ファイルをレンダリングする必要がある場合は、組み込みのレンダラーを使用します:

```bash
pandoc-embedz --standalone templates/report.tex charts.tex --config config/base.yaml -o build/report.tex
```

**コマンドラインオプション:**

- `--standalone`（または `-s`）はスタンドアロンモードを有効化
- `--template TEXT`（または `-t`）はテンプレートテキストを直接指定（テンプレートファイルの代わり）
- `--format FORMAT`（または `-f`）はデータ形式を指定（csv, json, yaml, lines など）
- `--config FILE`（または `-c`）は外部 YAML 設定ファイルを読み込み（繰り返し可能）
- `--output FILE`（または `-o`）は出力をファイルに書き込み（デフォルト: stdout）
- `--debug`（または `-d`）は stderr へのデバッグ出力を有効化（詳細は[デバッグ](#デバッグ)を参照）

**動作:**

- テンプレートファイルを使用する場合: ファイル内容全体がテンプレート本体として扱われ、複数ファイルは順番にレンダリングされ出力が連結される
- 先頭のオプションの YAML フロントマターはコードブロックと同じ方法で解析される
- インラインデータセクション（`---` セパレータ）は解釈**されない**—代わりに `data:` ブロックまたは外部ファイルを使用
- **標準入力の自動検出:**
  - `-t` オプション使用時: `-f` が指定された場合**のみ**標準入力からデータを読み取る
  - テンプレートファイル使用時: `data:` が指定されておらず標準入力が利用可能（パイプ/リダイレクト）な場合、標準入力から自動的にデータを読み取る
  - **制限:** 複数のテンプレートファイルを処理する場合、標準入力の自動検出は無効（標準入力は一度しか読み取れない）。必要に応じて最初のファイルで明示的に `data: "-"` を使用
- **空の入力:** 空または空白のみの入力は、JSON と CSV 形式では空のリスト `[]` として扱われる
- データソースが定義されていない場合、テンプレートはそのままレンダリングされる（グローバル変数や静的コンテンツのみを必要とする LaTeX フロントマターに便利）。フロントマター/プリアンブルのみを定義するファイルは出力を生成しない

**クイックデータフォーマット例:**

```bash
# CSV データをフォーマット（標準入力から読み取るには -f が必要）
cat data.csv | pandoc-embedz -s -t '{% for row in data %}{{ row.name }}\n{% endfor %}' -f csv

# 特定のフォーマットでフォーマット
seq 10 | pandoc-embedz -s -t '{% for n in data %}- {{ n }}\n{% endfor %}' -f lines

# データなしの静的テンプレート（標準入力読み取りなし）
pandoc-embedz -s -t '静的コンテンツ'

# テンプレートファイルを使用（単一ファイルでは標準入力から自動読み取り）
cat data.csv | pandoc-embedz -s template.md

# 明示的なデータソースを持つ複数ファイル
pandoc-embedz -s file1.md file2.md  # 標準入力の自動検出なし
```

レンダラーは単にテンプレートを展開するだけなので、Pandoc が後でツールチェーンで通常消費する Markdown、LaTeX、その他のプレーンテキスト形式で動作します。

### 外部設定ファイル

Pandoc フィルターとスタンドアロンレンダラーの両方で、共有設定ファイルを読み込めるようになりました。YAML/属性の `config` または CLI から追加します:

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
pandoc-embedz --standalone report.md appendix.tex --config config/base.yaml --config config/latex.yaml
```

- 各設定ファイルは YAML マッピングである必要がある（`data`, `format`, `with`, `global`, `preamble` などを定義可能）
- ファイルは順番にマージされ、後のファイルが前のファイルを上書きし、インライン YAML が引き続き優先
- パスは通常のデータファイルと同じセキュリティチェック（`validate_file_path`）を適用
- `config:` には単一のファイルパスまたはリストを使用。属性は `config=path.yaml` をサポート

これにより、Pandoc 実行とスタンドアロンレンダリングジョブ間でデータソース、変数のデフォルト、マクロプリアンブルを簡単に共有できます。

> **注意:** 3番目の `---` セパレータを介したインラインデータは `.embedz` コードブロック内でのみ動作します。スタンドアロンテンプレートでは、フロントマターの後はすべてテンプレートテキストとして扱われるため、`data: |` YAML ブロックまたは外部ファイルを通じてインラインデータを提供する必要があります。

#### マルチドキュメント YAML ファイル

設定ファイルは `---` で区切られた複数の YAML ドキュメントをサポートします。ドキュメントは順番にマージされ、後のドキュメントが前のドキュメントを上書きします:

```yaml
# config/settings.yaml
---
global:
  fiscal_year: 2024
---
bind:
  prev_year: fiscal_year - 1
---
preamble: |
  {% macro format_yen(n) %}{{ "{:,}".format(n) }}円{% endmacro %}
---
```

処理順序は固定（`preamble → with → query → data → bind → global → alias → レンダリング`）なので、ファイル内のセクションは任意の順序で記述できます。この例では、`bind:` は `global:` の `fiscal_year` を参照でき、両方とも `preamble:` のマクロを使用できます（ドキュメントの順序に関係なく）。これにより、単一ファイル内で設定を論理的なグループに整理できます。

### なぜ汎用 Jinja CLI ではないのか？

一般的な「このテンプレートを Jinja でレンダリング」ツールと比較して、`pandoc-embedz` はドキュメントパイプライン向けに特化しています:

- **Pandocネイティブ統合** – フィルターモードは AST に直接書き込むため、番号付け、目次、引用、その他のフィルターが追加のグルーなしで動作し続けます。
- **豊富なデータ読み込み** – CSV/TSV/SSV/lines/JSON/YAML/TOML/SQLite、マルチテーブル結合、インラインデータ、クエリテンプレートがすべてファーストクラス機能です。
- **インライン設定** – 各 `.embedz` ブロック（またはフロントマター）は独自の YAML 設定、グローバル、マクロを持ち、ドキュメントを自己完結型にします。
- **共有ワークフロー** – スタンドアロンモードは正確なフィルターパイプラインを再利用するため、Markdown/LaTeX テンプレートと Pandoc ドキュメントがテンプレート、設定、デバッグ動作を共有できます。

単一のテンプレートファイルを一度展開するだけなら、シンプルな Jinja CLI で十分かもしれません。しかし、再現可能なレポート、マルチデータセット埋め込み、または Pandoc に依存するパイプラインでは、`pandoc-embedz` がワークフロー全体を統一します。

### LaTeX テンプレートでの作業

LaTeX ドキュメントにはリテラルの `{{`、`}}`、または多くの `{`/`}` ペア（例: `{{{ year }}}`）が含まれることがよくあります。Jinja2 はこれらをテンプレート区切り文字として扱うため、それらのセクションを `{% raw %}...{% endraw %}` でラップするか、明示的にエスケープしてください:

```tex
{% raw %}{{ setcounter{section}{0} }}{% endraw %}
\section*{ {{ title }} }
{{ '{{' }} macro {{ '}}' }}  % リテラルの波括弧
```

LaTeX テンプレートに多くのリテラルの波括弧がある場合は、ヘルパーマクロを定義するか、Jinja2 の区切り文字（`variable_start_string`/`variable_end_string` 経由）を切り替えて、構文を読みやすく保つことを検討してください。

## ベストプラクティス

### CSV出力のエスケープ

テンプレートから CSV 形式を出力する場合、特殊文字（カンマ、引用符、改行）の適切なエスケープを確保してください。一貫した処理のために Jinja2 マクロを使用します:

> **注意**: スタンドアロンモード（`-s`）では、テンプレート出力はプレーンテキストとして扱われ、Markdown として解釈されません。これにより、不要なフォーマット変更なしに CSV、JSON、その他の構造化フォーマットを安全に生成できます。

````markdown
---
format: csv
query: SELECT * FROM data WHERE active = 1
---
{# CSV フィールドエスケープマクロ #}
{%- macro csv_escape(value) -%}
  {%- set v = value | string -%}
  {%- if ',' in v or '"' in v or '\n' in v -%}
    "{{ v | replace('"', '""') }}"
  {%- else -%}
    {{ v }}
  {%- endif -%}
{%- endmacro -%}

{# ヘッダーを出力 #}
{% for key in data[0].keys() -%}
{{ csv_escape(key) }}{{ '' if loop.last else ',' }}
{%- endfor %}

{# データ行を出力 #}
{% for row in data -%}
{% for key in row.keys() -%}
{{ csv_escape(row[key]) }}{{ '' if loop.last else ',' }}
{%- endfor %}
{% endfor -%}
````

**動作の仕組み:**
- `,`、`"`、または改行を含むフィールドは自動的に引用符で囲まれる
- フィールド内のダブルクォートは `""` としてエスケープされる
- 通常のフィールドは読みやすさのために引用符なしのまま

### ファイル拡張子の推奨

非 Markdown コンテンツを出力するスタンドアロンテンプレートの場合:

- **`.emz`** - pandoc-embedz テンプレートの推奨される短い拡張子（3文字、覚えやすい）
- **`.embedz`** - 説明的な名前を好む場合の代替
- **`.md`** - テンプレートが実際の Markdown コンテンツを生成する場合のみ使用

**例:**
```bash
# 良い命名
csv_transform.emz
normalize_data.emz
format_report.embedz

# Markdown 出力の場合のみ .md を使用
report_template.md
```

### パイプライン処理パターン

pandoc-embedz を他のコマンドラインツールと組み合わせてデータ変換パイプラインを構築:

```bash
# 抽出 → 変換 → フォーマットパイプライン
extract_tool database table --columns 1-10 | \
  pandoc-embedz -s transform.emz | \
  post_process_tool > output.csv

# 多段階変換
cat raw_data.csv | \
  pandoc-embedz -s stage1_normalize.emz | \
  pandoc-embedz -s stage2_aggregate.emz | \
  pandoc-embedz -s stage3_format.emz > final.csv
```

**ヒント:**
- パイプライン処理には `-s`（スタンドアロンモード）を使用
- データは標準入出力を通じて自然に流れる
- 各 `.emz` ファイルは1つの変換ステップを処理
- 変換は集中的で再利用可能に保つ

## デバッグ

設定のマージ、データ読み込み、テンプレートレンダリングを含む詳細な処理情報を確認するには、デバッグ出力を有効にします。

**環境変数を使用**（フィルターモードとスタンドアロンモードの両方で動作）:

```bash
# フィルターモード
PANDOC_EMBEDZ_DEBUG=1 pandoc input.md --filter pandoc-embedz -o output.pdf

# スタンドアロンモード
PANDOC_EMBEDZ_DEBUG=1 pandoc-embedz -s template.md
```

**コマンドラインオプションを使用**（スタンドアロンモードのみ）:

```bash
pandoc-embedz -s -d template.md
pandoc-embedz --standalone --debug template.md
```

環境変数は `1`、`true`、または `yes` を有効な値として受け入れます。

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
- 複数のデータ形式（CSV、JSON、YAML、TOML、SQLite など）
- コードブロックレベルの処理（ドキュメント全体ではない）
- 軽量 - 重い依存関係なし
- 既存の Pandoc ワークフローで動作

詳細な比較については [COMPARISON.md](COMPARISON.md) を参照してください。

## ドキュメント

完全なドキュメントについては以下を参照:
- [MULTI_TABLE.md](MULTI_TABLE.md) - マルチテーブル SQL クエリ（高度）
- [COMPARISON.md](COMPARISON.md) - 代替ツールとの比較
- [examples/](examples/) - 使用例

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
