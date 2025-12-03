# サンプルドキュメント

pandoc-embedz の基本的な使い方を示すサンプルです。

## CSV ファイルの読み込み

```embedz
---
data: sample_data.csv
---
| 名前 | 値 |
|:-----|---:|
{% for row in data -%}
| {{ row.name }} | {{ row.value }} |
{% endfor %}
```

## インライン JSON データ

```embedz
---
format: json
---
### 商品リスト

{% for product in data %}
- **{{ product.name }}**: ¥{{ product.price }}
  {% if product.tags %}
  - タグ: {{ product.tags | join(', ') }}
  {% endif %}
{% endfor %}
---
[
  {"name": "りんご", "price": 150, "tags": ["果物", "新鮮"]},
  {"name": "バナナ", "price": 80, "tags": ["果物"]},
  {"name": "にんじん", "price": 120, "tags": ["野菜", "新鮮"]}
]
```

## 条件分岐

`with:` でローカル変数を定義し、条件分岐で表示を制御します。

```embedz
---
data: sample_data.csv
with:
  threshold: 50
---
### 高い値 (> {{ threshold }})

{% for row in data %}
{% if row.value | int > threshold %}
- {{ row.name }}: {{ row.value }}
{% endif %}
{% endfor %}
```

## フィルターの使用

Jinja2 のビルトインフィルターを使った例です。

```embedz
---
data: sample_data.csv
---
### 統計情報

- 件数: {{ data | length }}
- 最大値: {{ data | map(attribute='value') | map('int') | max }}
- 最小値: {{ data | map(attribute='value') | map('int') | min }}

### ソート済みリスト（値の降順）

{% for row in data | sort(attribute='value', reverse=true) %}
1. {{ row.name }} ({{ row.value }})
{% endfor %}
```

## 変換コマンド

```bash
# PDF に変換
pandoc simple.md --filter pandoc-embedz -o simple.pdf

# HTML に変換
pandoc simple.md --filter pandoc-embedz -o simple.html

# Markdown として確認
pandoc simple.md --filter pandoc-embedz -t markdown
```
