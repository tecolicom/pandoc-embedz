# Global 変数での式評価による型保持の提案

## 問題の背景

pandoc-embedz 0.9.3 で `global` セクションからデータを参照できるようになったが、
テンプレート展開結果が常に文字列になるため、辞書やリストを `global` に保存して
後からプロパティアクセスすることができない。

### 現状の動作

```yaml
global:
  first_row: "{{ data | first }}"
```

結果:
```python
GLOBAL_VARS['first_row'] = "{'name': 'Alice', 'value': 100}"  # 文字列
```

そのため `{{ first_row.name }}` は動作しない。

### 期待する動作

```python
GLOBAL_VARS['first_row'] = {'name': 'Alice', 'value': 100}  # 辞書
```

これにより `{{ first_row.name }}` でアクセス可能になる。

## 解決策

### 基本方針

**`global:` セクション内に `bind:` サブセクションを導入し、式を評価して型を保持する。**

通常の変数はテンプレート展開（常に文字列）、`bind:` 内の変数は式として評価（型保持）。

### 構文

```yaml
global:
  # 通常の変数（テンプレート展開 → 文字列）
  date_str: "{{ year }}-01-01"
  query: "SELECT * FROM data WHERE value > {{ threshold }}"

  # 式を評価して束縛（型保持）
  bind:
    first_row: data | first
    total: data | sum(attribute='value')
    high_values: |
      data
      | selectattr('value', 'gt', 50)
      | list
```

### 処理順序

**出現順に処理される。** 記述順 = 処理順。

```yaml
global:
  year: 2024                        # 1. 処理
  start_date: "{{ year }}-01-01"    # 2. year を参照可能
  bind:
    total: data | sum(attribute='value')  # 3. year, start_date を参照可能
    first: data | first                    # 4. total も参照可能
  end_date: "{{ year }}-12-31"      # 5. total, first を参照可能
```

### なぜ `bind` か

| 名前 | ニュアンス |
|------|-----------|
| `expr` | 「これは式です」（結果については言及しない） |
| `eval` | 「これを評価します」（Python eval の連想、セキュリティ懸念） |
| `bind` | 「結果を変数に束縛します」（型保持を暗示、関数型言語の概念） |

`bind` は「式を評価して、その結果（型を含めて）を変数に結びつける」という動作を最もよく表現している。

## 実装方法

### Jinja2 の評価方法

Jinja2 には2つの評価方法がある:

1. `template.render()` - 常に文字列を返す
2. `env.compile_expression()` - 式の結果をそのまま返す（型を保持）

`bind:` セクションでは `compile_expression()` を使用する。

### 実装コード

```python
def _evaluate_bind_expression(
    expr_str: str,
    context: Dict[str, Any],
    env: Environment
) -> Any:
    """Evaluate expression and preserve type.

    Args:
        expr_str: Jinja2 expression (without {{ }})
        context: Template rendering context
        env: Jinja2 Environment

    Returns:
        Evaluated value with original type preserved
    """
    try:
        compiled = env.compile_expression(expr_str)
        result = compiled(**context)
        _debug("Evaluated bind expression '%s' -> %r (type: %s)",
               expr_str, result, type(result).__name__)
        return result
    except Exception as e:
        _debug("Bind expression evaluation failed for '%s': %s", expr_str, e)
        raise


def _expand_global_variables(
    config: Dict[str, Any],
    with_vars: Dict[str, Any],
    data: Optional[Any] = None
) -> None:
    """Expand global variables with access to loaded data.

    Processes variables in order of appearance. Regular variables are
    template-expanded (string result), bind variables are expression-evaluated
    (type preserved).
    """
    if 'global' not in config:
        return

    env = _get_jinja_env()

    for key, value in config['global'].items():
        if key == 'bind' and isinstance(value, dict):
            # Process bind section: evaluate expressions with type preservation
            for bind_key, bind_expr in value.items():
                context = _build_render_context(with_vars, data)
                expr_str = bind_expr.strip() if isinstance(bind_expr, str) else str(bind_expr)
                result = _evaluate_bind_expression(expr_str, context, env)
                GLOBAL_VARS[bind_key] = result
                _debug("Bound '%s': %r (type: %s)", bind_key, result, type(result).__name__)
        elif isinstance(value, str) and _has_template_syntax(value):
            # Regular variable: template expansion (string result)
            context = _build_render_context(with_vars, data)
            rendered = _render_template(value, context)
            value = rendered.lstrip('\n')
            GLOBAL_VARS[key] = value
            _debug("Expanded global variable '%s': %s", key, value)
        else:
            # Plain value
            GLOBAL_VARS[key] = value

    _debug("Global variables: %s", GLOBAL_VARS)
```

## 動作例

### 入力

```yaml
---
format: csv
global:
  year: 2024
  date_str: "{{ year }}-01-01"
  bind:
    first_row: data | first
    total: data | sum(attribute='value')
    count: data | length
    high_values: |
      data
      | selectattr('value', 'gt', 50)
      | list
---
First: {{ first_row.name }} ({{ first_row.value }})
Total: {{ total }}
Count: {{ count }}
High value count: {{ high_values | length }}
---
name,value
Alice,100
Bob,30
Charlie,80
```

### 結果

```python
GLOBAL_VARS = {
    'year': 2024,                    # int (YAML parsing)
    'date_str': '2024-01-01',        # str (template expansion)
    'first_row': {'name': 'Alice', 'value': 100},  # dict (bind)
    'total': 210,                    # int (bind)
    'count': 3,                      # int (bind)
    'high_values': [                 # list (bind)
        {'name': 'Alice', 'value': 100},
        {'name': 'Charlie', 'value': 80}
    ],
}
```

出力:
```
First: Alice (100)
Total: 210
Count: 3
High value count: 2
```

## ユースケース

### ユースケース 1: データ行へのアクセス

現在の回避策:
```yaml
---
{%- set 今年度 = data | selectattr('年度', 'eq', '今年度') | first -%}
{%- set 前年度 = data | selectattr('年度', 'eq', '前年度') | first -%}
報告件数: {{ 今年度.報告件数 }}
```

提案後:
```yaml
global:
  bind:
    今年度: data | selectattr('年度', 'eq', '今年度') | first
    前年度: data | selectattr('年度', 'eq', '前年度') | first
---
報告件数: {{ 今年度.報告件数 }}
```

### ユースケース 2: 複数ブロックでのデータ共有

```yaml
# Block 1: Load and store summary
---
format: csv
global:
  bind:
    summary: data | first
    total: data | sum(attribute='value')
---
---
name,value
Alice,100
Bob,200
```

```yaml
# Block 2: Use stored data (no data loading needed)
---
---
Summary name: {{ summary.name }}
Total value: {{ total }}
```

### ユースケース 3: 条件分岐で使用

```yaml
global:
  bind:
    has_data: data | length > 0
    first_item: data | first | default(none)
---
{% if has_data %}
First item: {{ first_item.name }}
{% else %}
No data available.
{% endif %}
```

## 後方互換性

### 影響

- **既存のコード**: 影響なし（`bind:` は新機能）
- **`global:` の通常変数**: 動作変更なし（常に文字列）

### `bind` という変数名を使いたい場合

```yaml
global:
  bind: "some string"  # 値が辞書でないので、変数として扱われる
```

判定ルール: `bind` キーの値が辞書（mapping）の場合のみ特別扱い。

## エッジケースの考慮

### 1. None や空リストの結果

```yaml
global:
  bind:
    empty_result: data | selectattr('value', 'gt', 1000) | first | default(none)
```

`None` がそのまま保持され、テンプレートで `{% if empty_result %}` で判定可能。

### 2. 複数行の式

```yaml
global:
  bind:
    complex_filter: |
      data
      | selectattr('category', 'eq', 'A')
      | selectattr('value', 'gt', 50)
      | sort(attribute='value', reverse=true)
      | list
```

YAML のリテラルブロック (`|`) で複数行の式を記述可能。

### 3. マクロの使用

```yaml
global:
  bind:
    result: MY_MACRO(data)  # preamble や named template で定義されたマクロ
```

`compile_expression()` はマクロを直接評価できない可能性がある。
その場合はエラーを発生させ、テンプレート本文で `{% set %}` を使用するよう案内する。

## テスト計画

1. **基本機能**
   - `bind:` で辞書が保持される
   - `bind:` でリストが保持される
   - `bind:` で整数が保持される
   - `bind:` で None が保持される

2. **処理順序**
   - 通常変数 → bind の順で参照可能
   - bind 内で先に定義した変数を参照可能

3. **後方互換性**
   - 通常の `global:` 変数は文字列のまま
   - `bind:` がない場合は従来通り動作

4. **エッジケース**
   - `bind: "string"` は変数として扱われる
   - 複数行の式が正しく評価される
   - エラー時に適切なメッセージ

## 次のステップ

1. `_evaluate_bind_expression()` 関数を実装
2. `_expand_global_variables()` を修正
3. テストを追加
4. ドキュメント（README.md, CLAUDE.md）を更新
5. CHANGELOG を更新
