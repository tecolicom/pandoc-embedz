# Pandocでのデータ駆動ドキュメント生成：既存ソリューションとの比較

## 背景

報告書作成において、外部データ（CSV、JSON等）からテーブルやリストを自動生成したい
というニーズは一般的です。手動でデータを転記すると、更新時のミスや作業負荷が問題になります。

このドキュメントでは、Pandocでこの問題を解決する既存の方法と、
pandoc-embedz の位置づけを比較分析します。

## 既存のソリューション

### 1. pandoc-csv2table

CSVをテーブルに変換する専用フィルタ（Haskell実装）。

**使用例:**
````markdown
```{.table file="data.csv" type="grid"}
```
````

**特徴:**
- ✅ テーブル生成が簡単
- ✅ 複数のテーブル形式をサポート（simple、multiline、pipe、grid）
- ❌ テンプレート機能なし（テーブルのみ生成可能）
- ❌ ループ・条件分岐不可
- ❌ データの加工・フィルタリング不可
- ❌ リスト等の他の形式に変換不可
- ⚠️ メンテナンスに課題あり（ビルドエラー報告、大きな依存関係）
- ⚠️ 新しい代替ツール（pantable）への移行が推奨されている

**結論:** 単純なCSVテーブル挿入には使えるが、メンテナンス状況に注意が必要。


### 2. pantable

CSV/TSVをテーブルに変換する高機能なPythonフィルタ。

**使用例:**
````markdown
```{.pantable file="data.csv"}
```
````

**特徴:**
- ✅ テーブル生成が簡単で高機能
- ✅ CSV専用に最適化
- ✅ Pandoc Table ASTを完全サポート
- ✅ CSV ↔ Pandoc Table の双方向変換
- ✅ ライブラリとしても使用可能
- ✅ 比較的活発に保守されている（最終更新: 2022年）
- ❌ テンプレート機能なし（テーブルのみ生成可能）
- ❌ ループ・条件分岐不可
- ❌ データの加工・フィルタリング不可
- ❌ リスト等の他の形式に変換不可

**結論:** 単純なCSVテーブル挿入には最適だが、柔軟性に欠ける。pandoc-csv2tableよりも推奨される。


### 3. pandoc-jinja

Pandoc メタデータを**ドキュメント全体**に展開する Jinja2 ベースのフィルタ。

**使用例:**
````markdown
---
title: Report
author: John
year: 2024
---

# {{ title | upper }}
By {{ author }} ({{ year }})
````

**特徴:**
- ✅ メタデータ変数の展開（ドキュメント全体）
- ✅ Jinja2 フィルタ（upper, lower等）
- ✅ コマンドラインからの変数指定（`--metadata`）
- ❌ **ループと条件分岐が非対応**（公式ドキュメントで明記）
- ❌ 外部データファイル（CSV/JSON等）の読み込み不可
- ❌ データ駆動のドキュメント生成には不向き
- ❌ コードブロック単位の処理は不可
- ❌ 動作が遅い（開発者自身が言及）
- ⚠️ **プロジェクトは非活発状態**（最終更新: 2024年5月、週間DL数: 約74件）

**用途の違い:** pandoc-jinja は**ドキュメント全体**のメタデータ展開が目的。
pandoc-embedz は**コードブロック内**でのデータ駆動コンテンツ生成が目的。
両者は目的が異なるため、併用も可能。

**結論:** メタデータの変数展開には便利だが、外部データからテーブル・リストを
生成するには使えない。プロジェクトの活動状況にも注意が必要。


### 4. Pandoc Lua フィルタ

Lua スクリプトでカスタムフィルタを作成。

**使用例:**
```lua
function CodeBlock(block)
  if block.classes:includes('data') then
    -- CSV読み込み処理を自分で実装
    -- テーブル生成処理を自分で実装
    return pandoc.Table(...)
  end
end
```

**特徴:**
- ✅ 完全にカスタマイズ可能
- ✅ Pandoc標準機能（追加インストール不要）
- ❌ 毎回スクリプトを書く必要がある
- ❌ Jinja2のような強力なテンプレートエンジンがない
- ❌ CSV/JSON等のパーサーを自分で実装
- ❌ 学習コストが高い

**結論:** 柔軟だが、毎回コードを書くのは非効率。再利用性が低い。


### 5. R Markdown / Quarto

R/Python のコードチャンクでテーブル生成。

**使用例:**
````markdown
```{r}
data <- read.csv("data.csv")
knitr::kable(data)
```
````

**特徴:**
- ✅ データ処理が非常に強力
- ✅ 統計分析・可視化も可能
- ✅ 活発に開発されている（Quarto 1.4: 2024年1月、Quarto 1.5: 2024年7月）
- ✅ Python、R、Julia、Observable JS をサポート
- ✅ ダッシュボード、Manuscript、インタラクティブコンテンツに対応
- ❌ R/Python 環境が必須
- ❌ IDE（RStudio/VS Code）のセットアップが必要
- ❌ Pandoc単体では動かない
- ❌ 学習コストが高い
- ❌ 依存関係が多い（knitr, rmarkdown等）
- ❌ **単純な報告書には重すぎる**

**結論:** データ分析・科学論文には最適だが、単にデータから表を生成したいだけなら
オーバーキル。


### 6. 前処理アプローチ（Jinja2 CLI → Pandoc）

Markdownファイル自体をJinja2で生成してからPandocに渡す。

**使用例:**
```bash
jinja2 report.md.j2 data.yml | pandoc -o report.pdf
```

**特徴:**
- ✅ Jinja2 の全機能が使える
- ✅ 柔軟
- ❌ 2段階の処理が必要
- ❌ Markdown内で直接データを扱えない
- ❌ ワークフローが複雑
- ❌ Pandocのフィルタチェーンに組み込めない

**結論:** 動作するが、ワークフローが煩雑。Pandocの統合性が失われる。


## pandoc-embedz の特徴

### 設計思想

- Pandocフィルタとして動作（単一ツールで完結）
- Jinja2 の強力なテンプレート機能を提供
- 複数のデータフォーマットをサポート
- Markdownに埋め込んで使える（通常のPandocワークフロー）

### 主要機能

**1. 完全な Jinja2 サポート**
````markdown
```embedz
---
data: incidents.csv
---
{% for row in data %}
{% if row.count > 100 %}
- **{{ row.title }}**: {{ row.count }}件（要注意）
{% else %}
- {{ row.title }}: {{ row.count }}件
{% endif %}
{% endfor %}
```
````

**2. 8種類のデータフォーマット**
- CSV（カンマ区切り）
- TSV（タブ区切り）
- SSV/Spaces（空白・タブ区切り、手動整形に最適）
- lines（1行1要素）
- JSON（構造化データ）
- YAML（構造化データ）
- TOML（構造化データ）
- SQLite（データベースファイル）

拡張子による自動判定、または明示的な format 指定が可能。`ssv` と `spaces` は同義語として使用可能。

**3. 外部ファイルとインラインデータ**
````markdown
# 外部ファイル
```embedz
---
data: monthly_stats.csv
---
{% for row in data %}...{% endfor %}
```

# インラインデータ
```embedz
---
format: json
---
{% for item in data %}...{% endfor %}
---
[{"name": "Item1", "count": 10}]
```
````

**4. テンプレートの再利用**
````markdown
# テンプレート定義
```embedz
---
define: incident-list
data: data1.csv
---
{% for row in data %}
- {{ row.date }}: {{ row.title }}
{% endfor %}
```

# テンプレート再利用
```embedz
---
template: incident-list
data: data2.csv
---
```
````

**5. 変数スコープ管理**
````markdown
# グローバル変数（ドキュメント全体）
```embedz
---
global:
  threshold: 100
---
```

# ローカル変数（ブロック内のみ）
```embedz
---
data: data.csv
with:
  prefix: "事例"
---
{% for row in data %}
- {{ prefix }}-{{ row.id }}: {{ row.title }}
{% endfor %}
```
````

**6. 構造化データ対応**
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

**7. SQLクエリ対応**
````markdown
# CSV/TSVデータにSQLクエリを実行
```embedz
---
data: sales.csv
query: SELECT product, SUM(amount) as total FROM data WHERE date >= '2024-01-01' GROUP BY product ORDER BY total DESC
---
| 製品 | 売上合計 |
|------|----------|
{% for row in data -%}
| {{ row.product }} | ¥{{ "{:,}".format(row.total|int) }} |
{% endfor -%}
```
````

**8. マルチテーブル対応**
````markdown
# 複数のデータソースを読み込み、SQL JOINで結合
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
- {{ row.product_name }}: {{ row.total }}個
{% endfor %}
```

# 複数のデータソースに直接アクセス（SQL不要）
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

**9. SQLiteデータベース対応**
````markdown
# SQLiteデータベースから直接データを読み込み
```embedz
---
data: analytics.db
table: users
---
{% for user in data %}
- {{ user.name }} ({{ user.email }})
{% endfor %}
```

# カスタムクエリで集計
```embedz
---
data: analytics.db
query: SELECT category, COUNT(*) as count FROM events WHERE date >= '2024-01-01' GROUP BY category
---
{% for row in data %}
- {{ row.category }}: {{ row.count }}件
{% endfor %}
```
````

**10. 簡潔な記法（エレガント構文）**

属性とYAMLパラメータを組み合わせた自然な記法：

````markdown
# デリミタなしでYAMLパラメータを指定
```{.embedz data=file.csv as=template}
with:
  title: "レポートタイトル"
  year: 2024
```

# ドット記法で単純な変数を指定
```{.embedz data=file.csv as=template with.title="レポート" with.year="2024"}

# グローバル変数もドット記法で
```{.embedz global.author="山田太郎" global.version="1.0"}
````

**ドット記法の特徴**:
- `with.*` でテンプレートパラメータ
- `global.*` でドキュメント全体の変数
- 単一レベルのみ（`key.subkey` は可、`key.sub.deep` は不可）
- 複雑な構造は YAML を使用
- `with.debug="true"` のように Boolean 変換に対応


## 機能比較表

| 機能 | csv2table/pantable | pandoc-jinja | Lua | R Markdown | 前処理 | **pandoc-embedz** |
|------|---------------------|--------------|-----|------------|--------|---------------------|
| テーブル生成 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| リスト生成 | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| ループ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| 条件分岐 | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| CSV対応 | ✅ | ❌ | 自前実装 | ✅ | △ | ✅ |
| JSON/YAML対応 | ❌ | ❌ | 自前実装 | ✅ | △ | ✅ |
| SQLite対応 | ❌ | ❌ | 自前実装 | ✅ | ❌ | ✅ |
| 複数フォーマット | ❌ | ❌ | 自前実装 | △ | △ | ✅ (8種) |
| SQLクエリ | ❌ | ❌ | 自前実装 | ✅ | ❌ | ✅ |
| マルチテーブル/JOIN | ❌ | ❌ | 自前実装 | ✅ | ❌ | ✅ |
| テンプレート再利用 | ❌ | ❌ | 自前実装 | ❌ | ✅ | ✅ |
| 変数スコープ管理 | ❌ | ❌ | 自前実装 | ❌ | △ | ✅ |
| Pandoc単体で完結 | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| 学習コスト | 低 | 低 | 中 | 高 | 中 | **低** |
| セットアップ | 簡単 | 簡単 | 簡単 | 複雑 | 中 | **簡単** |

**注:** csv2table/pantableは CSV専用のテーブル変換フィルタ。pantableの方がより高機能で保守も活発なため推奨。


## ユースケース別推奨

### 単純なCSVテーブル挿入
→ **pantable**（推奨）または **pandoc-embedz**
- pantableはCSV専用に最適化された高機能フィルタ
- pandoc-csv2tableは保守に課題あり、pantableへの移行を推奨

### メタデータの変数展開のみ
→ **pandoc-jinja**（非活発状態に注意）または Pandoc組み込みテンプレート

### データからテーブル・リストを柔軟に生成（推奨）
→ **pandoc-embedz**
- ループ・条件分岐が使える
- 8種類のフォーマット対応
- テンプレート再利用可能

### データの集計・フィルタリング・結合を含むレポート作成（推奨）
→ **pandoc-embedz**
- SQLクエリでデータ処理
- 複数テーブルのJOIN操作
- SQLiteデータベース対応
- Pandoc単体で完結

### 複雑なデータ分析・可視化を含む
→ **R Markdown / Quarto**

### 高度にカスタマイズされた処理
→ **Lua フィルタ**（または pandoc-embedz で不足なら）


## 結論

pandoc-embedz は、**データ駆動のドキュメント生成**において：

1. **Pandocのワークフローに自然に統合**される
2. **Jinja2の強力なテンプレート機能**をフルに活用できる
3. **8種類のデータフォーマット**に対応（CSV、TSV、SSV、lines、JSON、YAML、TOML、SQLite）
4. **SQLクエリ機能**でデータのフィルタリング・集計・結合が可能
5. **マルチテーブル対応**で複数のデータソースを扱える
6. **簡潔で自然な記法**: `{.embedz data=file.csv as=template}` や `with.title="Title"` などの直感的な構文
7. **学習コストが低く**、すぐに使い始められる
8. **Pandoc単体で完結**し、追加の環境が不要

特に、**報告書作成で外部データからテーブル・リストを生成する**という
ユースケースにおいて、既存ソリューションのギャップを埋める
**最適なバランスのツール**と言えます。

---

**インストール:**

GitHubから直接インストール（現在はこちらを使用）:
```bash
pip install git+https://github.com/tecolicom/pandoc-embedz.git
```

または、PyPIから（リリース後）:
```bash
pip install pandoc-embedz
```

**使用:**
```bash
pandoc report.md --filter pandoc-embedz -o report.pdf
```
