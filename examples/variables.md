# 変数の使い方

このドキュメントでは、pandoc-embedz における変数の定義と使用方法を説明します。

## 変数の種類

| 種類 | スコープ | 型の扱い | 用途 |
|:-----|:---------|:---------|:-----|
| `with:` | ブロック内 | そのまま | 入力パラメータ、ローカル定数 |
| `bind:` | ドキュメント全体 | 型を保持 | データ抽出、計算結果 |
| `global:` | ドキュメント全体 | 文字列 | ラベル、メッセージ |
| `alias:` | ドキュメント全体 | キーの別名 | 別名でのアクセス |

## with: ローカル変数

ブロック内でのみ有効な変数を定義します。

```embedz
---
format: csv
with:
  tax_rate: 0.1
  currency: "¥"
---
### 価格表（税込）

| 商品 | 税抜価格 | 税込価格 |
|:-----|--------:|---------:|
{% for row in data -%}
| {{ row.name }} | {{ currency }}{{ row.price }} | {{ currency }}{{ (row.price | int * (1 + tax_rate)) | int }} |
{% endfor %}
---
name,price
りんご,100
バナナ,80
みかん,120
```

## global: グローバル変数

ドキュメント全体で使用できる変数を定義します。

```embedz
---
global:
  author: 山田太郎
  version: 1.0
  report_date: 2024-12-03
---
```

以降のブロックで使用できます：

```embedz
---
format: csv
---
## レポート

- 作成者: {{ author }}
- バージョン: {{ version }}
- 作成日: {{ report_date }}

### データ一覧

{% for row in data -%}
- {{ row.name }}: {{ row.value }}
{% endfor %}
---
name,value
項目A,100
項目B,200
項目C,300
```

## bind: 型を保持したバインディング

`bind:` は式の評価結果の型（辞書、リスト、数値、真偽値）を保持します。
`global:` と異なり、プロパティアクセス（`{{ item.name }}`）が可能です。

```embedz
---
format: csv
bind:
  first_row: data | first
  last_row: data | last
  total: data | sum(attribute='value')
  count: data | length
  has_data: data | length > 0
---
### 統計情報

- 件数: {{ count }}
- 合計: {{ total }}
- データあり: {{ has_data }}

### 先頭と末尾

- 先頭: {{ first_row.name }} ({{ first_row.value }})
- 末尾: {{ last_row.name }} ({{ last_row.value }})
---
name,value
Alpha,100
Beta,200
Gamma,300
Delta,400
```

### ネストした構造

`bind:` ではネストした構造も定義できます：

```embedz
---
format: csv
bind:
  first: data | first
  stats:
    name: first.name
    value: first.value
    doubled: first.value * 2
    is_high: first.value > 50
---
### 先頭データの分析

- 名前: {{ stats.name }}
- 値: {{ stats.value }}
- 2倍: {{ stats.doubled }}
- 高い値？: {{ stats.is_high }}
---
name,value
Sample,100
Other,50
```

### ドット記法

既存の辞書にキーを追加できます：

```embedz
---
format: csv
bind:
  record: data | first
  record.note: "'追加のメモ'"
  record.priority: 1
---
### レコード情報

- 名前: {{ record.name }}
- 値: {{ record.value }}
- メモ: {{ record.note }}
- 優先度: {{ record.priority }}
---
name,value
Test,999
```

## to_dict フィルター

リストを辞書に変換して、キーで直接アクセスできるようにします。

```embedz
---
format: csv
bind:
  by_year: data | to_dict('year')
  y2023: by_year[2023]
  y2024: by_year[2024]
  growth: ((y2024.sales - y2023.sales) / y2023.sales * 100) | round(1)
---
### 年次比較

| 年 | 売上 |
|:---|-----:|
| 2023 | {{ y2023.sales }} |
| 2024 | {{ y2024.sales }} |

**前年比成長率: {{ growth }}%**
---
year,sales
2023,1000
2024,1200
```

### 複数テーブルの結合

```embedz
---
format: json
bind:
  products: data | to_dict('id')
---
---
[
  {"id": 101, "name": "りんご", "price": 100},
  {"id": 102, "name": "バナナ", "price": 80}
]
```

```embedz
---
format: json
---
### 注文一覧

{% for order in data -%}
- 注文#{{ order.order_id }}: {{ products[order.product_id].name }} x {{ order.qty }}
{% endfor %}
---
[
  {"order_id": 1, "product_id": 101, "qty": 2},
  {"order_id": 2, "product_id": 102, "qty": 1},
  {"order_id": 3, "product_id": 101, "qty": 3}
]
```

## alias: 別名の定義

辞書のキーに別名を追加します。

```embedz
---
format: csv
bind:
  item: data | first
alias:
  商品名: name
  価格: value
---
### 別名でのアクセス

- name でアクセス: {{ item.name }}
- 商品名 でアクセス: {{ item.商品名 }}
- value でアクセス: {{ item.value }}
- 価格 でアクセス: {{ item.価格 }}
---
name,value
テスト商品,1500
```

## 処理順序

変数は以下の順序で処理されます：

1. `preamble` - マクロや `{% set %}` の定義
2. `with` - ローカル変数
3. `query` - SQL クエリの展開
4. データ読み込み
5. `bind` - 型を保持したバインディング
6. `global` - グローバル変数
7. `alias` - 別名の追加
8. テンプレートのレンダリング

この順序を理解すると、どの変数がどの段階で使えるかがわかります。

## 変換コマンド

```bash
pandoc variables.md --filter pandoc-embedz -o variables.pdf
pandoc variables.md --filter pandoc-embedz -o variables.html
```
