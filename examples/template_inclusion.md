# テンプレートインクルードの使い方

このドキュメントでは、テンプレートを他のテンプレート内にネストして、よりモジュラーなコンテンツ生成を行う方法を説明します。

## 基本的な例

まず、再利用可能な書式テンプレートを定義します：

```embedz
---
define: date-format
---
{{ item.date }}
```

```embedz
---
define: title-format
---
**{{ item.title }}**
```

これらを組み合わせて整形されたエントリを作成します：

```embedz
---
format: json
---
## インシデントレポート
{% for item in data %}
- {% include 'date-format' with context %} - {% include 'title-format' with context %}
{% endfor %}
---
[
  {"date": "2024-01-15", "title": "Apache HTTP Server の脆弱性"},
  {"date": "2024-01-20", "title": "OpenSSL 証明書検証の問題"},
  {"date": "2024-02-03", "title": "WordPress プラグインの XSS 脆弱性"}
]
```

## 条件分岐を含むテンプレート

条件分岐を使用するテンプレートを定義します：

```embedz
---
define: severity-badge
---
{% if item.severity == "high" %}🔴 高{% elif item.severity == "medium" %}🟡 中{% else %}🟢 低{% endif %}
```

重要度レベルを表示するために使用します：

```embedz
---
format: json
---
### 脆弱性リスト
{% for item in data %}
- {% include 'severity-badge' with context %} - {{ item.title }}
{% endfor %}
---
[
  {"title": "重大なメモリ破壊", "severity": "high"},
  {"title": "情報漏洩", "severity": "medium"},
  {"title": "軽微な設定エラー", "severity": "low"}
]
```

## ネストしたテンプレート構成

複数レベルのテンプレート構成を作成します：

```embedz
---
define: status-icon
---
{% if item.status == "resolved" %}✅{% elif item.status == "investigating" %}🔍{% else %}⏳{% endif %}
```

```embedz
---
define: incident-entry
---
{% include 'status-icon' with context %} {{ item.date }} - {{ item.title }}
```

合成テンプレートを使用します：

```embedz
---
format: json
---
## インシデント追跡
{% for item in data %}
- {% include 'incident-entry' with context %}
{% endfor %}
---
[
  {"date": "2024-01-10", "title": "データベースパフォーマンス問題", "status": "resolved"},
  {"date": "2024-01-15", "title": "API レート制限", "status": "investigating"},
  {"date": "2024-01-20", "title": "メール配信遅延", "status": "pending"}
]
```

## テーブルの書式設定

テーブル行用のテンプレートを定義します：

```embedz
---
define: table-row
---
{{ "| " }}{{ item.name }}{{ " | " }}{{ item.count }}{{ " | " }}{{ item.percentage }}{{ "% |" }}
```

テーブルを生成します：

```embedz
---
format: json
---
| カテゴリ | 件数 | 割合 |
|:---------|-----:|-----:|
{% for item in data -%}
{% include 'table-row' with context %}
{% endfor -%}
---
[
  {"name": "Web アプリケーション", "count": 45, "percentage": 35},
  {"name": "ネットワークサービス", "count": 32, "percentage": 25},
  {"name": "オペレーティングシステム", "count": 28, "percentage": 22},
  {"name": "IoT デバイス", "count": 23, "percentage": 18}
]
```

## with context について

`{% include 'template-name' with context %}` の `with context` 句は、現在のループ変数（`item` など）をインクルードされるテンプレートに渡します。これがないと、テンプレート内で `item` を参照できません。

## 変換コマンド

```bash
# PDF に変換
pandoc template_inclusion.md --filter pandoc-embedz -o template_inclusion.pdf

# HTML に変換
pandoc template_inclusion.md --filter pandoc-embedz -o template_inclusion.html
```
