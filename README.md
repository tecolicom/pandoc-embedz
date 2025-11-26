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
- 🌐 **Variable Scoping**: Local (`with:`), global (`global:`), and preamble (`preamble:`) management
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
- [Advanced Features](#advanced-features)
  - [SQL Queries on CSV/TSV](#sql-queries-on-csvtsv)
  - [SQLite Database](#sqlite-database)
  - [Multi-Table Data](#multi-table-data)
  - [Template Macros](#template-macros)
  - [Variable Scoping](#variable-scoping)
  - [Preamble & Macro Sharing](#preamble--macro-sharing)
- [Reference](#reference)
  - [Usage Patterns](#usage-patterns)
    - [Template Inclusion](#template-inclusion)
  - [Tables & Options](#tables--options)
    - [Supported Formats](#supported-formats)
    - [Code Block Syntax](#code-block-syntax)
    - [Configuration Options](#configuration-options)
    - [Data Variable](#data-variable)
  - [Template Content](#template-content)
- [Standalone Rendering](#standalone-rendering)
  - [External Config Files](#external-config-files)
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

**With inline data:**

````markdown
```embedz
---
template: item-list
format: json
with:
  title: Product List
---

---
[{"name": "Widget", "value": "$10"}, {"name": "Gadget", "value": "$20"}]
```
````

Note the **three `---` separators**: the first opens the YAML header, the second closes it, and the third marks the beginning of the inline data section.

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

### Variable Scoping

Control variable visibility with `with` (local) and `global` (document-wide):

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

**Local variables** with `with` are block-scoped:

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

**Preamble section** for document-wide control structures (macros, variables):

````markdown
```embedz
---
preamble: |
  {% set fiscal_year = 2024 %}
  {% set title = 'Annual Report' %}
  {% macro BETWEEN(start, end) -%}
  SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
  {%- endmacro %}
global:
  start_date: "{{ fiscal_year }}-04-01"
  end_date: "{{ fiscal_year + 1 }}-03-31"
  heading: "{{ title }} (FY{{ fiscal_year }})"
  yearly_query: "{{ BETWEEN(start_date, end_date) }}"
---
```

```embedz
---
data: sales.csv
query: "{{ yearly_query }}"
---
## {{ heading }}
{% for row in data %}
- {{ row.date }}: {{ row.amount }}
{% endfor %}
```
````

The `preamble` section defines control structures that are available throughout the entire document:
- **Macros**: Define once, use everywhere
- **Variables** (`{% set %}`): Template-level variables shared across all blocks (and can feed `global`)
- **Imports**: Import templates or macros for use in subsequent blocks

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

### Tables & Options

Reference tables for formats, syntax, and configuration knobs.

#### Supported Formats

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

#### Code Block Syntax

#### Basic Structure

An embedz code block consists of up to three parts:

````markdown
```embedz
---
YAML configuration (optional)
---
Jinja2 template
---
Inline data (optional)
```
````

Or using attribute syntax:

````markdown
```{.embedz attribute=value ...}
Jinja2 template
```
````

#### Block Interpretation

How a code block is processed depends on its configuration:

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

Or with attribute syntax (using `as=` for brevity):

```{.embedz data=file.csv as=my-template}
```
````

**With inline data** (note the two `---` separators):

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

**Processing**: Loads `file.csv` → applies "my-template" → outputs result

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

#### Configuration Options

#### YAML Header

| Key | Description | Example |
|-----|-------------|---------|
| `data` | Data source: file path (string), multiple files (dict), or inline data (multi-line string or dict with `data` key) | `data: stats.csv` or `data: {sales: sales.csv}` or `data: \|<br>  name,value<br>  ...` |
| `format` | Data format: `csv`, `tsv`, `ssv`/`spaces`, `json`, `yaml`, `toml`, `sqlite`, `lines` (auto-detected from extension) | `format: json` |
| `define` | Template name (for definition) | `define: report-template` |
| `template` (or `as`) | Template to use (both aliases work, `template` preferred in YAML, `as` shorter for attributes) | `template: report-template` or `as: report-template` |
| `with` | Local variables (block-scoped) | `with: {threshold: 100}` |
| `global` | Global variables (document-scoped) | `global: {author: "John"}` |
| `preamble` | Control structures for entire document (macros, `{% set %}`, imports) | `preamble: \|`<br>`  {% set title = 'Report' %}` |
| `header` | CSV/TSV has header row (default: true) | `header: false` |
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

#### Data Variable

Template content can access:

- `data`: The loaded dataset (from file or inline)
  - Single file: `data` is a list of rows (or dict for JSON/YAML)
  - Multi-table without query: `data` is a dict, access via `data.table_name`
  - Multi-table with query: `data` is a list of SQL query results
- Variables from `with:` (local scope)
- Variables from `global:` (document scope)

#### Template Content

Uses Jinja2 syntax with full feature support:

- Variables: `{{ variable }}`
- Loops: `{% for item in data %} ... {% endfor %}`
- Conditionals: `{% if condition %} ... {% endif %}`
- Filters: `{{ value | filter }}`
- Macros: `{% macro name(args) %} ... {% endmacro %}`
- Include: `{% include 'template-name' %}`

For detailed Jinja2 template syntax and features, see the [Jinja2 documentation](https://jinja.palletsprojects.com/).

## Standalone Rendering

Need to render Markdown or LaTeX files without running a full Pandoc conversion? Use the built-in renderer:

```bash
pandoc-embedz --standalone templates/report.tex charts.tex --config config/base.yaml -o build/report.tex
```

- `--standalone` (or `-s`) enables standalone mode and every positional argument after it is treated as a template file (use `-` to read from stdin)
- Entire file content is treated as the template body; multiple files are rendered in order and their outputs are concatenated
- Optional YAML front matter at the top is parsed the same way as code blocks
- Inline data sections (`---` separator) are **not** interpreted here—use `data:` blocks or external files instead
- Output is written to stdout unless `--output / -o` is provided
- If no data sources are defined, the template renders as-is (handy for LaTeX front matter
  that only needs global variables or static content); files that only define front matter/preamble produce no output

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

Copyright © 2025 Office TECOLI, LLC and Kazumasa Utashiro

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
