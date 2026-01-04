# pandoc-embedz

[![Tests](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml/badge.svg)](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/pandoc-embedz.svg)](https://badge.fury.io/py/pandoc-embedz)
[![Python Versions](https://img.shields.io/pypi/pyversions/pandoc-embedz.svg)](https://pypi.org/project/pandoc-embedz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful [Pandoc](https://pandoc.org/) filter for embedding data-driven content in Markdown documents using Jinja2 templates. Transform your data into beautiful documents with minimal setup.

## Features

- 🔄 **Full [Jinja2](https://jinja.palletsprojects.com/) Support**: Loops, conditionals, filters, macros, and all template features
- 📊 **8 Data Formats**: CSV, TSV, SSV/Spaces (whitespace-separated), lines, JSON, YAML, TOML, SQLite
- 🎯 **Auto-Detection**: Automatically detects format from file extension
- 📝 **Inline & External Data**: Support both inline data blocks and external files
- 🗄️ **SQL Queries**: Filter, aggregate, and transform CSV/TSV data using SQL
- 🔗 **Multi-Table SQL**: Load multiple files and combine with JOIN operations
- 📦 **Multi-Table Direct Access**: Load multiple datasets and access each independently
- ⚡ **Flexible Syntax**: YAML headers and code block attributes
- 🔁 **Template Reuse**: Define templates once, use them multiple times
- 🧩 **Template Inclusion**: Nest templates within templates with `{% include %}`
- 🎨 **Jinja2 Macros**: Create parameterized template functions
- 📋 **Preamble Section**: Define control structures (macros, variables) for entire document
- 🌐 **Variable Scoping**: Local (`with:`), global (`global:`), type-preserving (`bind:`), and preamble (`preamble:`) management
- 🔑 **Custom Filters**: `to_dict` for list-to-dictionary conversion, `raise` for template validation, `regex_replace` for pattern substitution, `regex_search` for pattern matching, `alias` for alternative key names
- 🏗️ **Structured Data**: Full support for nested JSON/YAML structures
- 🧾 **Standalone Rendering**: `pandoc-embedz --standalone file1.tex file2.md` expands whole templates (Markdown/LaTeX) without running full Pandoc

## tl;dr

**Install:**
```bash
pip install pandoc-embedz
```

**Basic usage:**
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

**With template reuse:**
````markdown
```{.embedz define=item-list}
## {{ title }}
{% for item in data %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
```

```{.embedz data=products.csv as=item-list}
with:
  title: Product List
```
````

_Note: `as=` is shorthand. In YAML headers, `template:` is preferred. See [Template Reuse](#template-reuse) for details._

**Render:**
```bash
pandoc report.md --filter pandoc-embedz -o output.pdf
```

Works with CSV, JSON, YAML, TOML, SQLite and more. See [Basic Usage](#basic-usage) to get started, or jump to [Advanced Features](#advanced-features) for SQL queries, multi-table operations, and database access.

## Table of Contents

- [tl;dr](#tldr)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
  - [CSV File (Auto-detected)](#csv-file-auto-detected)
  - [JSON Structure](#json-structure)
  - [Inline Data](#inline-data)
  - [Conditionals](#conditionals)
  - [Template Reuse](#template-reuse)
- [Code Block Syntax](#code-block-syntax)
  - [Basic Structure](#basic-structure)
  - [Content Interpretation Rules](#content-interpretation-rules)
  - [Block Types](#block-types)
- [Variable Scoping](#variable-scoping)
  - [Local Variables with `with:`](#local-variables-with-with)
  - [Global Variables with `global:`](#global-variables-with-global)
  - [Type-Preserving Bindings with `bind:`](#type-preserving-bindings-with-bind)
  - [Alias Feature](#alias-feature)
- [Advanced Features](#advanced-features)
  - [SQL Queries on CSV/TSV](#sql-queries-on-csvtsv)
  - [SQLite Database](#sqlite-database)
  - [Multi-Table Data](#multi-table-data)
  - [Template Macros](#template-macros)
  - [Preamble & Macro Sharing](#preamble--macro-sharing)
- [Standalone Rendering](#standalone-rendering)
  - [External Config Files](#external-config-files)
- [Reference](#reference)
  - [Usage Patterns](#usage-patterns)
    - [Template Inclusion](#template-inclusion)
  - [Supported Formats](#supported-formats)
  - [Configuration Options](#configuration-options)
  - [Data Variable](#data-variable)
  - [Template Content](#template-content)
  - [Jinja2 Filters](#jinja2-filters)
    - [Builtin Filters](#builtin-filters)
    - [Custom Filters](#custom-filters)
- [Best Practices](#best-practices)
  - [CSV Output Escaping](#csv-output-escaping)
  - [File Extension Recommendations](#file-extension-recommendations)
  - [Pipeline Processing Pattern](#pipeline-processing-pattern)
- [Debugging](#debugging)
- [Related Tools](#related-tools)
- [Documentation](#documentation)
- [License](#license)
- [Author](#author)
- [Contributing](#contributing)

## Installation

Install from PyPI (stable release):

```bash
pip install pandoc-embedz
```

Or grab the latest main branch directly from GitHub:

```bash
pip install git+https://github.com/tecolicom/pandoc-embedz.git
```

Dependencies: `panflute`, `jinja2`, `pandas`, `pyyaml`

**Note**: Requires [Pandoc](https://pandoc.org/installing.html) to be installed separately. See [Pandoc documentation](https://pandoc.org/MANUAL.html) for usage.

## Basic Usage

These examples cover the most common use cases. Start here to learn the basics.

### CSV File (Auto-detected)

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

### JSON Structure

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

### Inline Data

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

### Conditionals

Use Jinja2 `if`/`elif`/`else` to show different content based on data values:

````markdown
```embedz
---
data: alerts.csv
---
{% for row in data %}
{% if row.severity == 'high' %}
- ⚠️ **URGENT**: {{ row.title }} ({{ row.count }} cases)
{% elif row.severity == 'medium' %}
- ⚡ {{ row.title }} - {{ row.count }} reported
{% else %}
- {{ row.title }}
{% endif %}
{% endfor %}
```
````

### Template Reuse

Define templates once with `define`, then reuse them with `template` (or `as` for short). Perfect for consistent formatting across multiple data sources:

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
  title: Product List
---
```

Or more concisely with attribute syntax:

```{.embedz data=services.csv as=item-list}
with:
  title: Service List
```
````

See [Block Types](#block-types) for more details on template definition, usage with inline data, and other block patterns.

## Code Block Syntax

Understanding the structure of embedz code blocks helps you use all features effectively.

### Basic Structure

An embedz code block can have up to three sections separated by `---`:

````markdown
```embedz
---
YAML configuration
---
Jinja2 template
---
Inline data (optional)
```
````

- **First `---`**: Opens YAML header
- **Second `---`**: Closes YAML header, begins template section
- **Third `---`**: Separates template from inline data (optional)

### Content Interpretation Rules

How content is interpreted depends on whether `---` is present and what attributes are specified:

| Attributes | Has `---` | Content Interpretation |
|------------|-----------|------------------------|
| (any) | Yes | Standard: YAML → template → data |
| `data` + `template`/`as` | No | **YAML configuration** |
| `data=` + `template`/`as` | No | **YAML configuration** (no data loaded) |
| `template`/`as` only | No | Inline data |
| `define` | No | Template definition |
| (none) or `data` only | No | Template |

**Key point**: When both `data` and `template`/`as` are specified as attributes, the block content (without `---`) is parsed as YAML configuration. This enables concise syntax:

````markdown
```{.embedz data=products.csv as=item-list}
with:
  title: Product Catalog
```
````

This is equivalent to:

````markdown
```embedz
---
data: products.csv
template: item-list
with:
  title: Product Catalog
---
```
````

**Tip**: Use `data=` (empty value) when you want YAML configuration without loading any data file:

````markdown
```{.embedz data= as=report}
with:
  title: Quarterly Report
  year: 2024
```
````

### Block Types

#### 1. Data Processing Block (most common)

Loads data and renders it with a template:

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

**Processing**: Loads `file.csv` → makes it available as `data` → renders template → outputs result

#### 2. Template Definition

Defines a reusable template with `define:`:

````markdown
```{.embedz define=my-template}
{% for item in data %}
- {{ item.value }}
{% endfor %}
```
````

**Processing**: Stores template as "my-template" → no output

#### 3. Template Usage

Uses a previously defined template with `template:` (or `as:` for short):

````markdown
```embedz
---
data: file.csv
template: my-template
---
```
````

Or with attribute syntax (using `as=` for brevity):

````markdown
```{.embedz data=file.csv as=my-template}
```
````

With YAML configuration via attributes:

````markdown
```{.embedz data=file.csv as=my-template}
with:
  title: Report
```
````

**With inline data** (note the three `---` separators):

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

The structure is: YAML header → first `---` → (empty template section) → second `---` → inline data.

**Processing**: Loads data → applies "my-template" → outputs result

#### 4. Inline Data

Data embedded directly in the block:

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

**Processing**: Parses inline JSON → makes it available as `data` → renders template → outputs result

#### 5. Variable Definition

Sets global variables without output:

````markdown
```embedz
---
global:
  author: John Doe
  version: 1.0
---
```
````

**Processing**: Sets global variables → no output

Need to render a snippet that just uses globals/locals? Simply omit `data:`—any `.embedz`
block with template content now renders even when no dataset is provided:

````markdown
```embedz
---
with:
  author: Jane Doe
---
Prepared by {{ author }}
```
````

## Variable Scoping

Understanding how variables work is essential for building complex templates. pandoc-embedz provides four mechanisms for managing variables:

| Mechanism | Scope | Type Handling | Use Case |
|-----------|-------|---------------|----------|
| `with:` | Block-local | As-is | Input parameters, local constants |
| `bind:` | Document-wide | Type-preserving (dict, list, int, bool) | Extracting data, computations |
| `global:` | Document-wide | String (templates expanded) | Labels, messages, query strings |
| `alias:` | Document-wide | Key aliasing | Alternative key names for dicts |
| `preamble:` | Document-wide | Jinja2 control structures | Macros, `{% set %}` variables |

**Processing order**: preamble → with → query → data load → bind → global → alias → render

- `with:` variables are available in `query:` and all subsequent stages
- `bind:` evaluates after data loading, preserving expression result types
- `global:` evaluates after `bind:`, can reference both data and bind results
- All document-wide variables persist across blocks

### Local Variables with `with:`

Block-scoped variables for parameters and constants:

````markdown
```embedz
---
data: products.csv
with:
  tax_rate: 0.08
  currency: USD
---
{% for item in data %}
- {{ item.name }}: {{ currency }} {{ (item.price * (1 + tax_rate)) | round(2) }}
{% endfor %}
```
````

### Global Variables with `global:`

Document-wide variables. Values containing `{{` or `{%` are expanded as templates; the result is always a **string**.

````markdown
# Set global variables
```embedz
---
global:
  author: John Doe
  version: 1.0
---
```

# Use in any subsequent block
```embedz
---
data: report.csv
---
# Report by {{ global.author }}
Version {{ global.version }}

{% for row in data %}
- {{ row.item }}
{% endfor %}
```
````

> **Note**: The `global.` prefix is optional. You can use `{{ author }}` instead of `{{ global.author }}`.

> **Important**: All `global:` values become strings after expansion. For type-preserving values (dict, list, int, bool), use `bind:` instead.

### Type-Preserving Bindings with `bind:`

Evaluate expressions while preserving their result types (dict, list, int, bool):

````markdown
```embedz
---
format: csv
bind:
  first_row: data | first
  total: data | sum(attribute='value')
  has_data: data | length > 0
---
Name: {{ first_row.name }}, Total: {{ total }}, Has data: {{ has_data }}
---
name,value
Alice,100
Bob,200
```
````

Unlike `global:` which converts values to strings, `bind:` preserves the original type, enabling property access like `{{ first_row.name }}`.

**Nested structures** are supported:

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
{{ stats.name }}: {{ stats.value }} (doubled: {{ stats.doubled }})
---
name,value
Alice,100
```
````

**Dot notation** for setting nested values:

````markdown
```embedz
---
format: csv
bind:
  record: data | first
  record.note: "'Added by bind'"   # Adds 'note' key to record dict
global:
  record.label: Description        # Adds 'label' key (no quotes needed)
---
{{ record.name }}: {{ record.note }}, {{ record.label }}
---
name,value
Alice,100
```
````

> **Note**: In `bind:`, values are Jinja2 expressions (quotes needed for string literals).
> In `global:`, values are plain strings unless they contain `{{` or `{%`.

### Alias Feature

The `alias:` section adds alternative keys to all dictionaries:

````markdown
```embedz
---
format: csv
bind:
  item:
    label: |-
      "Item description"
    value: 100
alias:
  description: label  # 'description' becomes an alias for 'label'
---
{{ item.description }}: {{ item.value }}
---
name,value
dummy,0
```
````

Aliases are applied recursively to all nested dictionaries and do not overwrite existing keys.

## Advanced Features

These features enable powerful data processing, database access, and complex document generation workflows.

### SQL Queries on CSV/TSV

Filter, aggregate, and transform CSV/TSV data using SQL. Perfect for quarterly reports, data analysis, and working with large datasets:

````markdown
```embedz
---
data: transactions.csv
query: SELECT * FROM data WHERE date BETWEEN '2024-01-01' AND '2024-03-31' ORDER BY amount DESC
---
## Q1 2024 Transactions

{% for row in data %}
- {{ row.date }}: ${{ row.amount }} - {{ row.description }}
{% endfor %}
```
````

Aggregation example for reports:

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
| Product | Quantity | Sales |
|---------|----------|-------|
{% for row in data -%}
| {{ row.product }} | {{ row.total_quantity }} | ${{ row.total_sales }} |
{% endfor -%}
```
````

**Note**: Table name is always `data`. CSV/TSV data is loaded into an in-memory SQLite database for querying.

#### Query Template Variables

Share SQL query logic across multiple embedz blocks using Jinja2 template variables. This is useful when you need to apply the same filter criteria to different datasets:

**Define global variables for queries:**
````markdown
```{.embedz}
---
global:
  start_date: 2024-01-01
  end_date: 2024-03-31
---
```
````

**Use variables in queries:**
````markdown
```{.embedz data=sales.csv}
---
query: SELECT * FROM data WHERE date BETWEEN '{{ global.start_date }}' AND '{{ global.end_date }}'
---
## Sales ({{ global.start_date }} to {{ global.end_date }})
{% for row in data %}
- {{ row.product }}: ${{ row.amount }}
{% endfor %}
```

```{.embedz data=expenses.csv}
---
query: SELECT * FROM data WHERE date BETWEEN '{{ global.start_date }}' AND '{{ global.end_date }}'
---
## Expenses ({{ global.start_date }} to {{ global.end_date }})
{% for row in data %}
- {{ row.category }}: ${{ row.amount }}
{% endfor %}
```
````

> **Note:** The `global.` prefix is optional. You can use `{{ start_date }}` instead of `{{ global.start_date }}`. The prefix is available for clarity when you have both global and local variables.

**Store complete queries as variables:**
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
## High-Value Transactions
{% for row in data %}
- {{ row.date }}: ${{ row.amount }}
{% endfor %}
```
````

**Nested variable references:**

Global variables can reference other global variables, allowing you to build complex queries from reusable components:

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
## {{ global.year }} Sales Report
{% for row in data %}
- {{ row.date }}: ${{ row.amount }}
{% endfor %}
```
````

Variables are expanded in definition order, so later variables can reference earlier ones.

Template expansion works with `global` and `with` variables, and supports all query features (CSV, TSV, SSV, and SQLite databases).

### SQLite Database

Query SQLite database files directly. Use the `table` parameter to specify which table to read from the database:

````markdown
```embedz
---
data: users.db
table: users
---
{% for user in data %}
- {{ user.name }} ({{ user.email }})
{% endfor %}
```
````

Or use a custom SQL query (the `query` parameter overrides `table`):

````markdown
```embedz
---
data: analytics.db
query: SELECT category, COUNT(*) as count FROM events WHERE date >= '2024-01-01' GROUP BY category
---
## Event Statistics

| Category | Count |
|----------|-------|
{% for row in data -%}
| {{ row.category }} | {{ row.count }} |
{% endfor -%}
```
````

### Multi-Table Data

Load multiple data files and access them directly or combine with SQL:

**Direct access (no SQL):**
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

**SQL JOIN (with query):**
````markdown
```embedz
---
data:
  products: products.csv  # Table name in SQL
  sales: sales.csv        # Table name in SQL
query: |
  SELECT p.product_name, SUM(s.quantity) as total
  FROM sales s            # Use table names here
  JOIN products p ON s.product_id = p.product_id
  GROUP BY p.product_name
---
{% for row in data %}     <!-- Result is in 'data' -->
- {{ row.product_name }}: {{ row.total }}
{% endfor %}
```
````

**Inline data (no external files):**
````markdown
```embedz
---
data:
  config:
    format: yaml
    data: |
      title: "Sales Report"
  sales: |              # Multi-line string = inline CSV
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

**See [MULTI_TABLE.md](MULTI_TABLE.md) for comprehensive examples and documentation.**

### Template Macros

Create reusable template functions with parameters using Jinja2 macros. More flexible than `{% include %}` for complex formatting:

````markdown
# Define macros
```{.embedz define=formatters}
{% macro format_item(title, date) -%}
**{{ title }}** ({{ date }})
{%- endmacro %}

{% macro severity_badge(level) -%}
  {% if level == "high" -%}
    🔴 High
  {%- elif level == "medium" -%}
    🟡 Medium
  {%- else -%}
    🟢 Low
  {%- endif %}
{%- endmacro %}
```

# Use macros with import
```embedz
---
data: vulnerabilities.csv
---
{% from 'formatters' import format_item, severity_badge %}

## Vulnerability Report
{% for item in data %}
- {{ format_item(item.title, item.date) -}}
  {{- " - " -}}
  {{- severity_badge(item.severity) }}
{% endfor %}
```
````

**Macro vs Include**:
- **Macros**: Accept parameters, more flexible, explicit imports required
- **Include**: Simpler, uses current context automatically, no parameters

See [Template Inclusion](#template-inclusion) for detailed `{% include %}` examples.

### Preamble & Macro Sharing

Use the `preamble` section and named templates to define reusable control structures that every embedz block can access.

> **Note**: Variables defined in `preamble` with `{% set %}` are Jinja2 template variables, different from `global` variables which are stored as Python data. Use `preamble` for control flow and `global` for data storage.

**Sharing macros** across variables within a `global` section (alternative approach):

````markdown
# Define macros in a named template
```{.embedz define=sql-macros}
{%- macro BETWEEN(start, end) -%}
SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
{%- endmacro -%}
```

# Import and use macros in global variables
```embedz
---
global:
  fiscal_year: 2024
  start_date: "{{ fiscal_year }}-04-01"
  end_date: "{{ fiscal_year + 1 }}-03-31"

  # Import macros from named template
  # Variable name can be anything; imports are recognized by the {% from ... %} syntax
  _import: "{% from 'sql-macros' import BETWEEN %}"

  # Use imported macro
  yearly_query: "{{ BETWEEN(start_date, end_date) }}"
---
```

# Use the generated query
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

This pattern is useful for:
- **Query builders**: Define SQL query macros once, use across multiple global variables
- **Date calculations**: Create date range macros for fiscal periods, quarters, etc.
- **Complex transformations**: Encapsulate multi-step logic in reusable macros

## Reference

Technical specifications and syntax details.

### Usage Patterns

Focused guides for composing complex templates.

#### Template Inclusion

Break complex layouts into smaller fragments and stitch them together with `{% include %}`. Define each fragment with `define` and reuse it inside loops so formatting stays centralized.

````markdown
# Define formatting fragments
```{.embedz define=date-format}
📅 {{ item.date }}
```

```{.embedz define=title-format}
**{{ item.title }}**
```

# Compose fragments inside a loop
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

The `with context` clause forwards the current loop variables so included templates can read `item`. You can also layer includes, for example:

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
## Vulnerabilities
{% for item in data %}
- {% include 'severity-badge' with context %} {{ item.title }}
{% endfor %}
```
````

### Supported Formats

| Format     | Extension        | Description                                                               |
|------------|------------------|---------------------------------------------------------------------------|
| CSV        | `.csv`           | Comma-separated values (header support)                                   |
| TSV        | `.tsv`           | Tab-separated values (header support)                                     |
| SSV/Spaces | -                | Space/whitespace-separated values (via `format: ssv` or `format: spaces`) |
| Lines      | `.txt`           | One item per line (plain text)                                            |
| JSON       | `.json`          | Structured data (lists and objects)                                       |
| YAML       | `.yaml`, `.yml`  | Structured data with hierarchies                                          |
| TOML       | `.toml`          | Structured data (similar to YAML/JSON)                                    |
| SQLite     | `.db`, `.sqlite` | Database files (also `.sqlite3`; requires `table` or `query` parameter)   |

**Note**: SSV (Space-Separated Values) treats consecutive spaces and tabs as a single delimiter, making it ideal for manually aligned data. Both `ssv` and `spaces` can be used interchangeably.

**SSV with fixed columns**: Use the `columns` parameter to preserve spaces in the last column:

````markdown
```{.embedz format=spaces columns=3}
ID  Name   Description
1   Alice  Software engineer
2   Bob    Project manager with team
```
````

When `columns=3` is specified, the data is split into exactly 3 columns. The last column captures all remaining content including spaces, which is useful for free-form text fields.

### Configuration Options

#### YAML Header

| Key | Description | Example |
|-----|-------------|---------|
| `data` | Data source: file path (string), multiple files (dict), or inline data (multi-line string or dict with `data` key) | `data: stats.csv` or `data: {sales: sales.csv}` or `data: \|<br>  name,value<br>  ...` |
| `format` | Data format: `csv`, `tsv`, `ssv`/`spaces`, `json`, `yaml`, `toml`, `sqlite`, `lines` (auto-detected from extension) | `format: json` |
| `define` | Template name (for definition) | `define: report-template` |
| `template` (or `as`) | Template to use (both aliases work, `template` preferred in YAML, `as` shorter for attributes) | `template: report-template` or `as: report-template` |
| `with` | Local variables (block-scoped) | `with: {threshold: 100}` |
| `bind` | Type-preserving bindings (evaluates expressions, preserves dict/list/int/bool types) | `bind: {first: data \| first}` |
| `global` | Global variables (document-scoped, string values) | `global: {author: "John"}` |
| `alias` | Add alternative keys to all dicts (applied after bind/global) | `alias: {description: label}` |
| `preamble` | Control structures for entire document (macros, `{% set %}`, imports) | `preamble: \|`<br>`  {% set title = 'Report' %}` |
| `header` | CSV/TSV has header row (default: true) | `header: false` |
| `columns` | Fixed column count for SSV format (last column gets remaining content) | `columns: 3` |
| `table` | SQLite table name (required for sqlite format) | `table: users` |
| `query` | SQL query for SQLite, CSV/TSV filtering, or multi-table JOINs (required for multi-table mode) | `query: SELECT * FROM data WHERE active=1` |
| `config` | External YAML config file(s) merged before inline settings (string or list) | `config: config/base.yaml` |

**Backward Compatibility:**
- `name` parameter (deprecated): Still works but shows a warning. Use `define` instead.

#### Attribute Syntax

Attributes can be used instead of or in combination with YAML:

```markdown
{.embedz data=file.csv as=template}
{.embedz define=template}
{.embedz global.author="John"}
```

**Precedence**: YAML configuration overrides attribute values when both are specified.

Need to avoid repeating YAML headers? Attributes also accept `config=/path/file.yaml` (repeat as needed) to load shared settings outside the block body.

### Data Variable

The `data` variable provides access to loaded data in templates.

#### Data Sources

Data can be loaded from:

- **File**: `data=products.csv` loads from file
- **Inline**: Data section after the second `---` delimiter
- **Variable reference**: `data=varname` uses a `bind:` variable (dict or list)
- **SQL query**: `query:` filters/transforms loaded data via SQL

#### Data Structure

The structure of `data` depends on the source:

- Single file/inline: `data` is a list of rows (or dict for JSON/YAML)
- Multi-table without query: `data` is a dict, access via `data.table_name`
- Multi-table with query: `data` is a list of SQL query results
- Variable reference: Same structure as the referenced variable

#### Variable Reference

You can reference `bind:` variables (dict or list) directly in the `data=` attribute:

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
2024 value: {{ data[2024].value }}
```
````

**Resolution rules:**

1. If `data=` contains `/` or `.` → treated as file path
2. If the name exists in `bind:` variables as dict or list → use that variable
3. Otherwise → attempt to load as file

**Use cases:**

- **Reuse processed data**: Load data once, transform with `to_dict`, use in multiple blocks
- **Share data across templates**: Define data structure in one block, reference in others
- **Avoid redundant file loading**: Process large datasets once, reference the result

**Applying query to variable data:**

You can apply `query:` to variable data, enabling powerful data transformation pipelines:

````markdown
<!-- Load raw data once -->
```{.embedz data=sales.csv}
---
bind:
  raw_sales: data
---
```

<!-- Create monthly summary from raw data -->
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

<!-- Create yearly summary from the same raw data -->
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

This allows you to:
- Load a file once and derive multiple aggregations
- Apply different SQL queries to the same source data
- Build complex data pipelines without redundant file I/O

> **Note**: If the variable contains a dict (e.g., from `to_dict`), it is automatically converted to a list of values before applying the query.

> **Note**: Variable reference and inline data cannot be combined. Use either `data=varname` or inline data after `---`, not both.

#### Other Variables

Template content can also access:

- Variables from `with:` (local scope)
- Variables from `global:` (document scope)
- Variables from `bind:` (type-preserving, document scope)

### Template Content

Uses Jinja2 syntax with full feature support:

- Variables: `{{ variable }}`
- Loops: `{% for item in data %} ... {% endfor %}`
- Conditionals: `{% if condition %} ... {% endif %}`
- Filters: `{{ value | filter }}`
- Macros: `{% macro name(args) %} ... {% endmacro %}`
- Include: `{% include 'template-name' %}`

For detailed Jinja2 template syntax and features, see the [Jinja2 documentation](https://jinja.palletsprojects.com/).

**Note on output format:**
- **Filter mode** (`.embedz` code blocks): Template output is interpreted as Markdown and passed back to Pandoc for further processing. You can use Markdown syntax (`**bold**`, `- lists`, `[links]()`, etc.) and LaTeX commands (`\textbf{}`, etc.) in your templates.
- **Standalone mode** (`-s` flag): Template output is plain text and not processed. Use this for generating CSV, JSON, configuration files, or any non-Markdown content.

### Jinja2 Filters

Filters transform values using the pipe (`|`) syntax: `{{ value | filter }}`.

#### Builtin Filters

Jinja2 provides many useful filters. Here are common ones for data processing:

| Filter | Description | Example |
|--------|-------------|---------|
| `first` | First item of a list | `{{ data \| first }}` |
| `last` | Last item of a list | `{{ data \| last }}` |
| `length` | Number of items | `{{ data \| length }}` |
| `sum` | Sum of values | `{{ data \| sum(attribute='value') }}` |
| `sort` | Sort a list | `{{ data \| sort(attribute='name') }}` |
| `selectattr` | Filter by attribute | `{{ data \| selectattr('active', 'true') }}` |
| `map` | Extract attribute | `{{ data \| map(attribute='name') \| list }}` |
| `join` | Join items | `{{ items \| join(', ') }}` |
| `default` | Default value | `{{ value \| default('N/A') }}` |
| `round` | Round number | `{{ price \| round(2) }}` |

**Examples:**

```jinja2
{# Get total sales #}
{{ data | sum(attribute='amount') }}

{# Filter high-value items #}
{% for item in data | selectattr('value', 'gt', 100) %}
- {{ item.name }}: {{ item.value }}
{% endfor %}

{# Sort by date descending #}
{% for row in data | sort(attribute='date', reverse=true) %}
- {{ row.date }}: {{ row.title }}
{% endfor %}

{# Format number with comma #}
{{ amount | int | string | default('0') }}
```

See [Jinja2 Builtin Filters](https://jinja.palletsprojects.com/en/latest/templates/#builtin-filters) for the complete list.

#### Custom Filters

pandoc-embedz provides additional filters:

**`to_dict(key, strict=True, transpose=False)`** - convert a list of dictionaries to a dictionary keyed by a specified field.

This is useful when you need to access specific records by key (e.g., year, ID, name) instead of iterating through the entire list. Common use cases:

- **Year-over-year comparisons**: Access this year's and last year's data directly
- **Lookup tables**: Create a mapping from ID to record for quick access
- **Cross-referencing**: Join data from different sources by a common key

```jinja2
{{ data | to_dict(key='year') }}
{# Input:  [{'year': 2023, 'value': 100}, {'year': 2024, 'value': 200}]
   Output: {2023: {'year': 2023, 'value': 100}, 2024: {'year': 2024, 'value': 200}} #}

{# Shorthand without keyword (also valid): #}
{{ data | to_dict(key='year') }}
```

**Example - Year-over-year comparison:**

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
2024: {{ current.value }} ({{ growth | round(1) }}% vs 2023)
---
year,value
2023,100
2024,120
```
````

**Strict mode** (default): Raises `ValueError` if duplicate keys are found, ensuring data integrity:

```jinja2
data | to_dict(key='id')                {# raises error if duplicate IDs exist #}
data | to_dict(key='id', strict=False)  {# allows duplicates, last value wins #}
```

**Transpose mode**: Adds column-keyed dictionaries for dual access patterns:

```jinja2
{{ data | to_dict(key='year', transpose=True) }}
{# Input:  [{'year': 2023, 'value': 100}, {'year': 2024, 'value': 200}]
   Output: {2023: {'year': 2023, 'value': 100},
            2024: {'year': 2024, 'value': 200},
            'value': {2023: 100, 2024: 200}} #}
```

This enables both access patterns:
- `result[2023].value` - access by year, then column
- `result.value[2023]` - access by column, then year (useful for passing to templates)

---

**`raise`** - raise an error with a custom message. Useful for validating required parameters in templates:

```jinja2
{%- if label is not defined -%}
{{ "Template error: label is required" | raise }}
{%- endif -%}
```

---

**`regex_replace(pattern, replacement='', ignorecase=False, multiline=False, count=0)`** - replace substring using regular expression. Compatible with Ansible's `regex_replace` filter.

```jinja2
{# Basic replacement #}
{{ "Hello World" | regex_replace("World", "Universe") }}
{# Output: Hello Universe #}

{# Pattern with capture groups #}
{{ "ansible" | regex_replace("^a.*i(.*)$", "a\\1") }}
{# Output: able #}

{# Remove characters (empty replacement) #}
{{ "Hello（World）" | regex_replace("[（）]", "") }}
{# Output: HelloWorld #}

{# Case-insensitive matching #}
{{ "Hello WORLD" | regex_replace("world", "Universe", ignorecase=true) }}
{# Output: Hello Universe #}

{# Multiline mode (^ matches start of each line) #}
{{ "foo\nbar\nbaz" | regex_replace("^b", "B", multiline=true) }}
{# Output: foo\nBar\nBaz #}

{# Limit replacements #}
{{ "foo=bar=baz" | regex_replace("=", ":", count=1) }}
{# Output: foo:bar=baz #}

{# Unicode properties (requires regex module) #}
{{ "Hello（World）" | regex_replace("\\p{Ps}|\\p{Pe}", "") }}
{# Output: HelloWorld - removes all open/close brackets #}
```

**Parameters:**
- `pattern`: Regular expression pattern to match
- `replacement`: Replacement string (default: empty string for removal)
- `ignorecase`: Case-insensitive matching (default: False)
- `multiline`: Multiline mode where `^` matches start of each line (default: False)
- `count`: Maximum number of replacements, 0 means unlimited (default: 0)

**Returns:** String with all matching substrings replaced.

**Unicode Properties:** When the `regex` module is installed, Unicode property escapes like `\p{P}` (punctuation), `\p{L}` (letters), `\p{Ps}` (open brackets), `\p{Pe}` (close brackets) are supported. Install with `pip install regex`.

---

**`regex_search(pattern, ignorecase=False, multiline=False)`** - search for a pattern and return the matched string. Compatible with Ansible's `regex_search` filter.

```jinja2
{# Basic search #}
{{ "Hello World" | regex_search("World") }}
{# Output: World #}

{# No match returns empty string #}
{{ "Hello World" | regex_search("Foo") }}
{# Output: (empty string) #}

{# Pattern with alternation #}
{{ "備考: 保留中です" | regex_search("保留|済|喪中") }}
{# Output: 保留 #}

{# Case-insensitive search #}
{{ "Hello WORLD" | regex_search("world", ignorecase=true) }}
{# Output: WORLD #}

{# Use in conditionals (empty string is falsy) #}
{% if value | regex_search("error|warning") %}
  Found issue: {{ value }}
{% endif %}
```

**Parameters:**
- `pattern`: Regular expression pattern to search for
- `ignorecase`: Case-insensitive matching (default: False)
- `multiline`: Multiline mode where `^` matches start of each line (default: False)

**Returns:** The first matched substring, or an empty string if no match is found. The empty string is falsy in Jinja2 conditionals, making it easy to use in `{% if %}` statements.

## Standalone Rendering

Need to render Markdown or LaTeX files without running a full Pandoc conversion? Use the built-in renderer:

```bash
pandoc-embedz --standalone templates/report.tex charts.tex --config config/base.yaml -o build/report.tex
```

**Command-line options:**

- `--standalone` (or `-s`) enables standalone mode
- `--template TEXT` (or `-t`) specifies template text directly (instead of template file)
- `--format FORMAT` (or `-f`) specifies data format (csv, json, yaml, lines, etc.)
- `--config FILE` (or `-c`) loads external YAML config file(s) (repeatable)
- `--output FILE` (or `-o`) writes output to file (default: stdout)
- `--debug` (or `-d`) enables debug output to stderr (see [Debugging](#debugging) for details)

**Behavior:**

- When using template files: entire file content is treated as the template body; multiple files are rendered in order and their outputs are concatenated
- Optional YAML front matter at the top is parsed the same way as code blocks
- Inline data sections (`---` separator) are **not** interpreted—use `data:` blocks or external files instead
- **Stdin auto-detection:**
  - When using `-t` option: data is read from stdin **only if** `-f` is specified
  - When using template files: if no `data:` is specified and stdin is available (piped/redirected), data is automatically read from stdin
  - **Limitation:** Stdin auto-detection is disabled when processing multiple template files (stdin can only be read once). Use explicit `data: "-"` in the first file if needed.
- **Empty input:** Empty or whitespace-only input is treated as an empty list `[]` for JSON and CSV formats
- If no data sources are defined, the template renders as-is (handy for LaTeX front matter that only needs global variables or static content); files that only define front matter/preamble produce no output

**Quick data formatting examples:**

```bash
# Format CSV data (requires -f to read from stdin)
cat data.csv | pandoc-embedz -s -t '{% for row in data %}{{ row.name }}\n{% endfor %}' -f csv

# Format with specific format
seq 10 | pandoc-embedz -s -t '{% for n in data %}- {{ n }}\n{% endfor %}' -f lines

# Static template without data (no stdin reading)
pandoc-embedz -s -t 'Static content'

# Use template file (data auto-read from stdin for single file)
cat data.csv | pandoc-embedz -s template.md

# Multiple files with explicit data source
pandoc-embedz -s file1.md file2.md  # No stdin auto-detection
```

Because the renderer simply expands templates, it works with Markdown, LaTeX, or any other plaintext format that Pandoc would normally consume later in the toolchain.

### External Config Files

Both the Pandoc filter and the standalone renderer can now load shared configuration files. Add them via `config` in YAML/attributes or from the CLI:

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

- Each config file must be a YAML mapping (can define `data`, `format`, `with`, `global`, `preamble`, etc.)
- Files are merged in order; later files override earlier ones, and inline YAML still takes precedence
- Paths honor the same security checks as normal data files (`validate_file_path`)
- Use a single file path or a list for `config:`; attributes support `config=path.yaml`

This makes it easy to share data sources, variable defaults, and macro preambles between Pandoc runs and standalone rendering jobs.

> **Note:** Inline data via a third `---` separator only works inside `.embedz` code
> blocks. Standalone templates should provide inline data through `data: |` YAML blocks or
> external files, because everything after the front matter is treated as template text.

#### Multi-Document YAML Files

Config files support multiple YAML documents separated by `---`. Documents are merged in order, with later documents overriding earlier ones:

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

Since the processing order is fixed (`preamble → with → query → data → bind → global → alias → render`), you can write sections in any order within the file. In this example, `bind:` can reference `fiscal_year` from `global:`, and both can use macros from `preamble:`, regardless of document order. This allows organizing settings into logical groups within a single file.

### Why Not a Generic Jinja CLI?

Compared to one-off “render this template with Jinja” tools, `pandoc-embedz` is purpose-built for document pipelines:

- **Pandoc-native integration** – filter mode writes straight into the AST, so numbering, ToC, citations, and other filters keep working without extra glue.
- **Rich data loading** – CSV/TSV/SSV/lines/JSON/YAML/TOML/SQLite, multi-table joins, inline data, and query templating are all first-class features.
- **Inline configuration** – every `.embedz` block (or front matter) carries its own YAML config, globals, and macros, making documents self-contained.
- **Shared workflow** – standalone mode reuses the exact filter pipeline, so Markdown/LaTeX templates and Pandoc documents can share templates, configs, and debugging behavior.

If you only need to expand a single template file once, a simple Jinja CLI might suffice. But for reproducible reports, multi-dataset embeds, or pipelines that already rely on Pandoc, `pandoc-embedz` keeps the whole workflow aligned.

### Working with LaTeX Templates

LaTeX documents often contain literal `{{`, `}}`, or lots of `{`/`}` pairs (e.g., `{{{ year }}}`). Jinja2 will treat these as template delimiters, so either wrap those sections in `{% raw %}...{% endraw %}` or escape them explicitly:

```tex
{% raw %}{{ setcounter{section}{0} }}{% endraw %}
\section*{ {{ title }} }
{{ '{{' }} macro {{ '}}' }}  % literal braces
```

If your LaTeX template has many literal braces, consider defining helper macros or switching Jinja2 delimiters (via `variable_start_string`/`variable_end_string`) so the syntax stays readable.

## Best Practices

### CSV Output Escaping

When outputting CSV format from templates, ensure proper escaping of special characters (commas, quotes, newlines). Use a Jinja2 macro for consistent handling:

> **Note**: In standalone mode (`-s`), template output is treated as plain text and not interpreted as Markdown. This makes it safe for generating CSV, JSON, or other structured formats without unwanted formatting changes.

````markdown
---
format: csv
query: SELECT * FROM data WHERE active = 1
---
{# CSV field escaping macro #}
{%- macro csv_escape(value) -%}
  {%- set v = value | string -%}
  {%- if ',' in v or '"' in v or '\n' in v -%}
    "{{ v | replace('"', '""') }}"
  {%- else -%}
    {{ v }}
  {%- endif -%}
{%- endmacro -%}

{# Output header #}
{% for key in data[0].keys() -%}
{{ csv_escape(key) }}{{ '' if loop.last else ',' }}
{%- endfor %}

{# Output data rows #}
{% for row in data -%}
{% for key in row.keys() -%}
{{ csv_escape(row[key]) }}{{ '' if loop.last else ',' }}
{%- endfor %}
{% endfor -%}
````

**How it works:**
- Fields containing `,`, `"`, or newlines are automatically quoted
- Double quotes inside fields are escaped as `""`
- Normal fields remain unquoted for readability

### File Extension Recommendations

For standalone templates that output non-Markdown content:

- **`.emz`** - Recommended short extension for pandoc-embedz templates (3 characters, memorable)
- **`.embedz`** - Alternative if you prefer descriptive names
- **`.md`** - Use only when the template generates actual Markdown content

**Example:**
```bash
# Good naming
csv_transform.emz
normalize_data.emz
format_report.embedz

# Use .md only for Markdown output
report_template.md
```

### Pipeline Processing Pattern

Combine pandoc-embedz with other command-line tools for data transformation pipelines:

```bash
# Extract → Transform → Format pipeline
extract_tool database table --columns 1-10 | \
  pandoc-embedz -s transform.emz | \
  post_process_tool > output.csv

# Multi-stage transformations
cat raw_data.csv | \
  pandoc-embedz -s stage1_normalize.emz | \
  pandoc-embedz -s stage2_aggregate.emz | \
  pandoc-embedz -s stage3_format.emz > final.csv
```

**Tips:**
- Use `-s` (standalone mode) for pipeline processing
- Data flows through stdin/stdout naturally
- Each `.emz` file handles one transformation step
- Keep transformations focused and reusable

## Debugging

Enable debug output to see detailed processing information including configuration merging, data loading, and template rendering.

**Using environment variable** (works in both filter and standalone modes):

```bash
# Filter mode
PANDOC_EMBEDZ_DEBUG=1 pandoc input.md --filter pandoc-embedz -o output.pdf

# Standalone mode
PANDOC_EMBEDZ_DEBUG=1 pandoc-embedz -s template.md
```

**Using command-line option** (standalone mode only):

```bash
pandoc-embedz -s -d template.md
pandoc-embedz --standalone --debug template.md
```

The environment variable accepts `1`, `true`, or `yes` as valid values.

## Related Tools

### Similar Pandoc Filters (on PyPI)

- **[pantable](https://pypi.org/project/pantable/)** - CSV/TSV to table with powerful options, table-focused
- **[pandoc-jinja](https://pypi.org/project/pandoc-jinja/)** - Document-wide metadata expansion, not for code blocks
- **[pandoc-include](https://pypi.org/project/pandoc-include/)** - Include external files with template support
- **[pandoc-pyrun](https://pypi.org/project/pandoc-pyrun/)** - Execute Python code in code blocks

### Additional Tools

- **[pandoc-csv2table](https://github.com/baig/pandoc-csv2table)** (Haskell) - CSV to table conversion only
- **[Quarto](https://quarto.org/)** - Comprehensive publishing system based on Pandoc. Excellent for data science and technical documents, but requires dedicated environment and workflow
- **[R Markdown](https://rmarkdown.rstudio.com/)** - Similar to Quarto, requires R environment
- **[Lua Filters](https://pandoc.org/lua-filters.html)** - Requires custom Lua scripting for each use case

### Why pandoc-embedz?

pandoc-embedz fills a unique niche:
- ✅ Full Jinja2 templating (loops, conditionals, filters)
- ✅ Multiple data formats (CSV, JSON, YAML, TOML, SQLite, etc.)
- ✅ Code block level processing (not document-wide)
- ✅ Lightweight - no heavy dependencies
- ✅ Works with existing Pandoc workflow

See [COMPARISON.md](COMPARISON.md) for detailed comparison.

## Documentation

For complete documentation, see:
- [MULTI_TABLE.md](MULTI_TABLE.md) - Multi-table SQL queries (advanced)
- [COMPARISON.md](COMPARISON.md) - Comparison with alternatives
- [examples/](examples/) - Usage examples

## License

MIT License

Copyright © 2025-2026 Office TECOLI, LLC and Kazumasa Utashiro

See [LICENSE](LICENSE) file for details.

## Author

Kazumasa Utashiro

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Development Setup

#### Using uv (Recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/tecolicom/pandoc-embedz.git
cd pandoc-embedz

# Install dependencies and setup development environment
uv sync --all-extras

# Run tests
uv run pytest tests/
```

#### Using pip

```bash
# Clone the repository
git clone https://github.com/tecolicom/pandoc-embedz.git
cd pandoc-embedz

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e .[dev]

# Run tests
pytest tests/
```

For detailed development guidelines, see [AGENTS.md](AGENTS.md).
