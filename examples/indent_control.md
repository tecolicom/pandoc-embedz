# インデントレベルの制御

このドキュメントは、同じテンプレートを異なるインデントレベルで使用する方法を示します。

## 方法1: ローカル変数でインデント制御

テンプレートを定義：

```embedz
---
name: simple-item
---
{{ indent }}{{ item.text }}
```

インデントレベル0で使用：

```embedz
---
format: json
local:
  indent: ""
---
{% for item in data -%}
{% include 'simple-item' with context %}
{% endfor -%}
---
[{"text": "- Top item 1"}, {"text": "- Top item 2"}]
```

インデントレベル1（スペース2つ）で使用：

```embedz
---
format: json
local:
  indent: "  "
---
{% for item in data -%}
{% include 'simple-item' with context %}
{% endfor -%}
---
[{"text": "- Nested item 1"}, {"text": "- Nested item 2"}]
```

## 方法2: マクロのパラメータでレベル指定（推奨）

インデント可能なマクロを定義：

```embedz
---
name: indent-macros
---
{% macro list_item(text, level=0) -%}
{{ '  ' * level }}- {{ text }}
{%- endmacro %}

{% macro code_line(text, level=0) -%}
{{ '    ' * level }}{{ text }}
{%- endmacro %}
```

データにレベル情報を含めて使用：

```embedz
---
format: json
---
{% from 'indent-macros' import list_item %}

## タスク階層

{% for task in data -%}
{{ list_item(task.name, task.level) }}
{% endfor -%}
---
[
  {"name": "プロジェクト計画", "level": 0},
  {"name": "要件定義", "level": 1},
  {"name": "機能リスト作成", "level": 2},
  {"name": "優先順位付け", "level": 2},
  {"name": "設計", "level": 1},
  {"name": "アーキテクチャ設計", "level": 2},
  {"name": "データベース設計", "level": 2},
  {"name": "実装", "level": 1}
]
```

## 方法3: 再帰マクロでネスト構造（最も強力）

構造化データ用の再帰マクロ：

```embedz
---
name: tree-renderer
---
{% macro render_tree(item, level=0) -%}
{{ '  ' * level }}- {{ item.name }}
{%- if item.children %}
{%- for child in item.children %}
{{ render_tree(child, level + 1) }}
{%- endfor %}
{%- endif %}
{%- endmacro %}
```

階層データを自動的にレンダリング：

```embedz
---
format: json
---
{% from 'tree-renderer' import render_tree %}

## ファイル構造

{% for item in data -%}
{{ render_tree(item) }}
{%- endfor %}
---
[
  {
    "name": "src/",
    "children": [
      {
        "name": "components/",
        "children": [
          {"name": "Header.tsx"},
          {"name": "Footer.tsx"}
        ]
      },
      {
        "name": "utils/",
        "children": [
          {"name": "format.ts"},
          {"name": "validate.ts"}
        ]
      },
      {"name": "App.tsx"}
    ]
  },
  {
    "name": "tests/",
    "children": [
      {"name": "unit/"},
      {"name": "integration/"}
    ]
  }
]
```

## 方法4: 計算されたインデント

アイテムのプロパティから動的に計算：

```embedz
---
name: dynamic-indent
---
{% macro priority_item(item) -%}
{{ '  ' * (3 - item.priority) }}- [P{{ item.priority }}] {{ item.task }}
{%- endmacro %}
```

優先度が高いほどインデントが少ない：

```embedz
---
format: json
---
{% from 'dynamic-indent' import priority_item %}

## タスク（優先度順）

{% for task in data -%}
{{ priority_item(task) }}
{% endfor -%}
---
[
  {"task": "緊急バグ修正", "priority": 1},
  {"task": "新機能実装", "priority": 2},
  {"task": "パフォーマンス改善", "priority": 2},
  {"task": "ドキュメント更新", "priority": 3},
  {"task": "コードリファクタリング", "priority": 3}
]
```

## まとめ

| 方法 | 用途 | 柔軟性 |
|:-----|:-----|:-------|
| ローカル変数 | シンプルな固定インデント | ⭐ |
| マクロパラメータ | データ駆動のインデント | ⭐⭐⭐ |
| 再帰マクロ | ネスト構造の自動処理 | ⭐⭐⭐⭐⭐ |
| 計算されたインデント | プロパティベースの制御 | ⭐⭐⭐⭐ |

**推奨**: データにレベル情報がある場合は**方法2（マクロパラメータ）**、構造化データの場合は**方法3（再帰マクロ）**が最適です。
