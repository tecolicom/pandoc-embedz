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

**純粋な式（`{{ expr }}` のみ）の場合は `compile_expression()` で評価し、型を保持する。**

Jinja2 には2つの評価方法がある:

1. `template.render()` - 常に文字列を返す
2. `env.compile_expression()` - 式の結果をそのまま返す（型を保持）

### 判定ロジック

```python
import re

def _extract_pure_expression(template_str: str) -> Optional[str]:
    """Extract expression from pure expression template.

    A pure expression is a template containing only a single {{ expr }} with
    no surrounding text or control structures.

    Args:
        template_str: Template string to analyze

    Returns:
        The expression string if pure expression, None otherwise

    Examples:
        "{{ data | first }}" -> "data | first"
        "{{ year }}-01-01" -> None (has surrounding text)
        "{{ a }} {{ b }}" -> None (multiple expressions)
        "{%- set x = 1 -%}{{ x }}" -> None (has control structure)
    """
    stripped = template_str.strip()

    # Reject if contains control structures
    if '{%' in stripped:
        return None

    # Count delimiters (simple count is sufficient for well-formed templates)
    if stripped.count('{{') != 1 or stripped.count('}}') != 1:
        return None

    # Match entire string as single expression
    match = re.match(r'^{{\s*(.+?)\s*}}$', stripped, re.DOTALL)
    if match:
        return match.group(1)
    return None
```

### 評価関数

```python
def _evaluate_global_value(
    value_str: str,
    context: Dict[str, Any],
    env: Environment
) -> Any:
    """Evaluate global variable value with type preservation.

    Processing logic:
    1. Non-string values: return as-is
    2. Plain strings (no template syntax): return as-is
    3. Pure expressions ({{ expr }} only): evaluate and preserve type
    4. Compound templates: render as string

    Args:
        value_str: Value to evaluate (may contain Jinja2 syntax)
        context: Template rendering context
        env: Jinja2 Environment

    Returns:
        Evaluated value with appropriate type
    """
    if not isinstance(value_str, str):
        return value_str

    if not _has_template_syntax(value_str):
        return value_str

    # Check for pure expression
    expr_str = _extract_pure_expression(value_str)
    if expr_str:
        try:
            # Prepend control structures for macro access
            control_structures_str = '\n'.join(CONTROL_STRUCTURES_PARTS)
            if control_structures_str:
                # For expressions using macros, we need to render first
                # to make macros available, then compile the expression
                pass  # Fall through to compile_expression

            compiled = env.compile_expression(expr_str)
            result = compiled(**context)
            _debug("Evaluated pure expression '%s' -> %r (type: %s)",
                   expr_str, result, type(result).__name__)
            return result
        except Exception as e:
            _debug("Expression evaluation failed for '%s': %s, falling back to render",
                   expr_str, e)
            # Fall through to template rendering

    # Compound template: render as string
    return _render_template(value_str, context).lstrip('\n')
```

## 動作例

### 純粋な式（型を保持）

| 入力 | 結果 | 型 |
|------|------|-----|
| `{{ data \| first }}` | `{'name': 'Alice', 'value': 100}` | dict |
| `{{ data \| length }}` | `2` | int |
| `{{ data }}` | `[...]` | list |
| `{{ year }}` | `2024` | int |
| `{{ data \| sum(attribute='value') }}` | `300` | int |

### 複合テンプレート（文字列）

| 入力 | 結果 | 型 |
|------|------|-----|
| `{{ year }}-01-01` | `'2024-01-01'` | str |
| `Hello {{ name }}` | `'Hello World'` | str |
| `{{ a }} and {{ b }}` | `'Alice and Bob'` | str |
| `{%- set x = 1 -%}{{ x }}` | `'1'` | str |

### プレーン文字列

| 入力 | 結果 | 型 |
|------|------|-----|
| `plain string` | `'plain string'` | str |
| `2024-01-01` | `'2024-01-01'` | str |

## ユースケース

### ユースケース 1: データ行へのアクセス

現在の回避策:
```yaml
# テンプレート本文内で {% set %} を使用
---
{%- set 今年度 = data | selectattr('年度', 'eq', '今年度') | first -%}
{%- set 前年度 = data | selectattr('年度', 'eq', '前年度') | first -%}
報告件数: {{ 今年度.報告件数 }}
```

提案後:
```yaml
global:
  今年度: "{{ data | selectattr('年度', 'eq', '今年度') | first }}"
  前年度: "{{ data | selectattr('年度', 'eq', '前年度') | first }}"
---
報告件数: {{ 今年度.報告件数 }}
```

### ユースケース 2: 複数ブロックでのデータ共有

```yaml
# Block 1: Load and store summary
---
format: csv
global:
  summary: "{{ data | first }}"
  total: "{{ data | sum(attribute='value') }}"
---
---
name,value
Alice,100
Bob,200
```

```yaml
# Block 2: Use stored data
---
format: json
---
Summary name: {{ summary.name }}
Total value: {{ total }}
---
[]
```

## 後方互換性

### 影響を受けるケース

従来（すべて文字列）:
```python
GLOBAL_VARS['total_count'] = '3'      # str
GLOBAL_VARS['year'] = '2024'          # str
```

新動作（型を保持）:
```python
GLOBAL_VARS['total_count'] = 3        # int
GLOBAL_VARS['year'] = 2024            # int
```

### 実用上の影響

- **テンプレート内での使用**: 影響なし（Jinja2 が自動で文字列変換）
- **Python コード内での直接参照**: 型が変わるため注意が必要
  - 例: `GLOBAL_VARS['count'] + ' items'` → TypeError

ただし、`global` 変数は通常テンプレート内で使用されるため、
Jinja2 の自動変換により実用上の問題は少ない。

### テストへの影響

`test_variables.py` の一部のアサーションを修正する必要がある:

```python
# 従来
assert GLOBAL_VARS['total_count'] == '3'

# 新動作
assert GLOBAL_VARS['total_count'] == 3
```

## エッジケースの考慮

### 1. 制御構文を含む式

```yaml
global:
  value: "{%- set x = data | first -%}{{ x }}"
```

`{%` を含むため複合テンプレートとして扱い、文字列を返す。
これは意図的な動作であり、制御構文の副作用を考慮した設計。

### 2. マクロを使用する式

```yaml
global:
  result: "{{ MY_MACRO(data) }}"
```

`compile_expression()` はマクロを直接評価できないため、
エラー時は `render()` にフォールバックして文字列を返す。

**注意**: マクロの結果で型を保持したい場合は、マクロ内で処理を完結させるか、
テンプレート本文で `{% set %}` を使用する必要がある。

### 3. 文字列リテラル内の `{{`

```yaml
global:
  msg: "{{ 'text with {{ inside' }}"
```

正規表現 `^{{\s*(.+?)\s*}}$` は最初の `}}` でマッチするため、
この場合は `compile_expression()` で評価される。
式 `'text with {{ inside'` は有効な Jinja2 文字列リテラルとして評価可能。

### 4. None や空リストの結果

```yaml
global:
  empty_result: "{{ data | selectattr('value', 'gt', 1000) | first }}"
```

`first` フィルタが `None` を返す場合、その `None` がそのまま保持される。
これは意図的な動作であり、後続のテンプレートで `{% if empty_result %}` などで
判定可能になる。

## 実装箇所

`pandoc_embedz/filter.py` の `_expand_global_variables()` 関数を修正:

```python
def _expand_global_variables(
    config: Dict[str, Any],
    with_vars: Dict[str, Any],
    data: Optional[Any] = None
) -> None:
    """Expand global variables with access to loaded data.

    Args:
        config: Configuration dictionary containing 'global' key
        with_vars: Local variables from 'with' section
        data: Loaded data (available for template expansion)

    Side effects:
        Updates GLOBAL_VARS dictionary
    """
    if 'global' not in config:
        return

    env = _get_jinja_env()
    for key, value in config['global'].items():
        if isinstance(value, str) and _has_template_syntax(value):
            context = _build_render_context(with_vars, data)
            value = _evaluate_global_value(value, context, env)
            _debug("Expanded global variable '%s': %r (type: %s)",
                   key, value, type(value).__name__)
        GLOBAL_VARS[key] = value
    _debug("Global variables: %s", GLOBAL_VARS)
```

## 結論

- **技術的に実現可能**: `compile_expression()` を使用することで型を保持できる
- **後方互換性**: 軽微な影響があるが、実用上は問題ない
- **ユーザー体験の向上**: `global` でデータ構造を共有でき、コードがシンプルになる
- **自然な動作**: 「式として評価すればいい」という直感的な期待に沿う
- **堅牢性**: エラー時はフォールバック、デバッグモードで詳細出力

## 次のステップ

1. `_extract_pure_expression()` 関数を実装
2. `_evaluate_global_value()` 関数を実装
3. `_expand_global_variables()` を修正
4. テストを追加・修正
   - 型保持のテスト（dict, list, int, None）
   - フォールバックのテスト
   - エッジケースのテスト
5. CHANGELOG を更新
