# Jinja2 マクロの使い方

このドキュメントでは、pandoc-embedz で Jinja2 マクロを使用して、パラメータ化された再利用可能なテンプレート関数を作成する方法を説明します。

## マクロとは

マクロはプログラミングの関数のようなもので、パラメータを受け取って整形された出力を返します。`{% include %}` よりも強力で、呼び出すたびに異なる値を渡すことができます。

## 基本的なマクロ

シンプルな書式設定マクロを定義します：

```embedz
---
define: basic-formatters
---
{% macro bold(text) -%}
**{{ text }}**
{%- endmacro %}

{% macro italic(text) -%}
*{{ text }}*
{%- endmacro %}

{% macro code(text) -%}
`{{ text }}`
{%- endmacro %}
```

異なるパラメータで使用します：

```embedz
---
format: json
---
{% from 'basic-formatters' import bold, italic, code %}

## 書式設定の例

{% for item in data %}
- {{ bold(item.name) }}: {{ italic(item.description) }} - {{ code(item.command) }}
{% endfor %}
---
[
  {"name": "インストール", "description": "パッケージをインストール", "command": "pip install pandoc-embedz"},
  {"name": "実行", "description": "フィルターを実行", "command": "pandoc --filter pandoc-embedz"},
  {"name": "テスト", "description": "テストを実行", "command": "pytest"}
]
```

## 条件分岐を含むマクロ

条件ロジックを含むマクロを作成します：

```embedz
---
define: status-macros
---
{% macro severity_badge(level) -%}
{% if level == "high" or level == "critical" %}🔴 重大
{%- elif level == "medium" %}🟡 中程度
{%- elif level == "low" %}🟢 軽微
{%- else %}⚪ 不明
{%- endif %}
{%- endmacro %}

{% macro status_icon(status) -%}
{% if status == "resolved" %}✅
{%- elif status == "investigating" %}🔍
{%- elif status == "pending" %}⏳
{%- else %}❓
{%- endif %}
{%- endmacro %}
```

組み合わせて使用します：

```embedz
---
format: json
---
{% from 'status-macros' import severity_badge, status_icon %}

## セキュリティ問題

| 状態 | 重要度 | タイトル |
|:----:|:-------|:---------|
{% for issue in data -%}
| {{ status_icon(issue.status) }} | {{ severity_badge(issue.severity) }} | {{ issue.title }} |
{% endfor %}
---
[
  {"title": "SQLインジェクション脆弱性", "severity": "critical", "status": "resolved"},
  {"title": "ユーザー入力のXSS", "severity": "high", "status": "investigating"},
  {"title": "CSRFトークンの欠落", "severity": "medium", "status": "pending"},
  {"title": "情報漏洩", "severity": "low", "status": "resolved"}
]
```

## 複数パラメータのマクロ

デフォルト値を持つ複数のパラメータを受け取るマクロ：

```embedz
---
define: advanced-formatters
---
{% macro format_date(date, prefix="日付: ") -%}
{{ prefix }}{{ date }}
{%- endmacro %}

{% macro link(url, text="", title="") -%}
{% if text %}[{{ text }}]({{ url }}{% if title %} "{{ title }}"{% endif %})
{%- else %}[{{ url }}]({{ url }})
{%- endif %}
{%- endmacro %}

{% macro badge(text, color="blue") -%}
![{{ text }}](https://img.shields.io/badge/{{ text }}-{{ color }})
{%- endmacro %}
```

異なるパラメータの組み合わせで使用します：

```embedz
---
format: json
---
{% from 'advanced-formatters' import format_date, link, badge %}

## プロジェクトリンク

{% for project in data %}
### {{ project.name }} {{ badge(project.status) }}

{{ format_date(project.date, "リリース日: ") }}

{{ link(project.url, project.name, "プロジェクトのホームページへ") }}

{% endfor %}
---
[
  {"name": "プロジェクトアルファ", "date": "2024-01-15", "url": "https://example.com/alpha", "status": "stable"},
  {"name": "プロジェクトベータ", "date": "2024-02-20", "url": "https://example.com/beta", "status": "beta"}
]
```

## ネストしたマクロ呼び出し

マクロから他のマクロを呼び出すことができます：

```embedz
---
define: composite-macros
---
{% macro format_priority(priority) -%}
{% if priority == 1 %}⚡ 緊急
{%- elif priority == 2 %}🔥 高
{%- elif priority == 3 %}📌 通常
{%- else %}📋 低
{%- endif %}
{%- endmacro %}

{% macro format_task(title, priority, assignee) -%}
- {{ format_priority(priority) }} **{{ title }}** (担当: {{ assignee }})
{%- endmacro %}
```

合成マクロを使用します：

```embedz
---
format: json
---
{% from 'composite-macros' import format_task %}

## タスクリスト

{% for task in data %}
{{ format_task(task.title, task.priority, task.assignee) }}
{% endfor %}
---
[
  {"title": "重大なバグ修正", "priority": 1, "assignee": "田中"},
  {"title": "新機能の実装", "priority": 2, "assignee": "鈴木"},
  {"title": "ドキュメントの更新", "priority": 3, "assignee": "佐藤"},
  {"title": "古いコードのリファクタリング", "priority": 4, "assignee": "山田"}
]
```

## マクロと Include の比較

### Include を使う場合（シンプルだが柔軟性が低い）

```embedz
---
define: simple-item
---
- {{ item.name }}: {{ item.value }}
```

```embedz
---
format: json
---
{% for item in data %}
{% include 'simple-item' with context %}
{% endfor %}
---
[{"name": "A", "value": 1}, {"name": "B", "value": 2}]
```

### マクロを使う場合（パラメータで柔軟に対応）

```embedz
---
define: macro-item
---
{% macro format_item(name, value, prefix="項目 ") -%}
- {{ prefix }}{{ name }}: {{ value }}
{%- endmacro %}
```

```embedz
---
format: json
---
{% from 'macro-item' import format_item %}
{% for item in data %}
{{ format_item(item.name, item.value, "エントリ ") }}
{% endfor %}
---
[{"name": "A", "value": 1}, {"name": "B", "value": 2}]
```

## 使い分けの指針

**マクロを使う場合**:
- 呼び出しごとに異なるパラメータを渡す必要がある
- デフォルトのパラメータ値が欲しい
- 複数の場所から異なる引数で呼び出す
- ロジックが自己完結していて再利用可能

**Include を使う場合**:
- テンプレートの断片を再利用するだけでよい
- すべてのデータが現在のコンテキストから取得できる
- 柔軟性よりもシンプルさを優先

## 変換コマンド

```bash
pandoc macros.md --filter pandoc-embedz -o macros.pdf
pandoc macros.md --filter pandoc-embedz -o macros.html
```
