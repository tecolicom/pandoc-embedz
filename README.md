# pandoc-embedz

[![Tests](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml/badge.svg)](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/pandoc-embedz.svg)](https://badge.fury.io/py/pandoc-embedz)
[![Python Versions](https://img.shields.io/pypi/pyversions/pandoc-embedz.svg)](https://pypi.org/project/pandoc-embedz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful [Pandoc](https://pandoc.org/) filter for embedding data-driven content in Markdown documents using Jinja2 templates. Transform your data into beautiful documents with minimal setup.

## Features

- Full [Jinja2](https://jinja.palletsprojects.com/) support: loops, conditionals, filters, macros, and all template features
- 9 data formats: CSV, TSV, SSV, lines, JSON, YAML, TOML, SQLite, Excel
- Auto-detection of format from file extension
- Inline and external data sources
- SQL queries for filtering, aggregation, and multi-table JOINs
- Template reuse with `define`/`template` and `{% include %}`
- Variable scoping: local (`with:`), global (`global:`), type-preserving (`bind:`), and preamble
- Custom filters: `to_dict`, `raise`, `regex_replace`, `regex_search`, `alias`
- Standalone rendering mode for shell pipelines and non-Markdown output

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

Works with CSV, JSON, YAML, TOML, SQLite, Excel and more. See [Basic Usage](#basic-usage) to get started, or jump to [Advanced Features](#advanced-features) for SQL queries, multi-table operations, and database access.

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

**Note**: Requires [Pandoc](https://pandoc.org/installing.html) to be installed separately. A comprehensive reference manual is available via `man pandoc-embedz` after installation.

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
- **URGENT**: {{ row.title }} ({{ row.count }} cases)
{% elif row.severity == 'medium' %}
- {{ row.title }} - {{ row.count }} reported
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

## Code Block Syntax

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

### Block Types

**Data processing** (most common) --- loads data and renders with a template:

````markdown
```{.embedz data=file.csv}
{% for row in data %}
- {{ row.name }}
{% endfor %}
```
````

**Template definition** --- stores a named template for reuse (no output):

````markdown
```{.embedz define=my-template}
{% for item in data %}
- {{ item.value }}
{% endfor %}
```
````

**Template usage** --- applies a previously defined template:

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

The structure is: YAML header -> (empty template section) -> inline data.

**Variable definition** --- sets global variables without output:

````markdown
```embedz
---
global:
  author: John Doe
  version: 1.0
---
```
````

### Content Interpretation (without `---`)

When a block has no `---` separator, the content is interpreted based on attributes:

| Attributes | Content Interpretation |
|------------|------------------------|
| `data` + `template`/`as` | YAML configuration |
| `template`/`as` only | Inline data |
| `define` | Template definition |
| (none) or `data` only | Template |

When `---` is present, the standard three-section structure applies regardless of attributes.

> See `man pandoc-embedz` for the complete configuration options reference.

## Variable Scoping

pandoc-embedz provides five mechanisms for managing variables:

| Mechanism | Scope | Type Handling | Use Case |
|-----------|-------|---------------|----------|
| `with:` | Block-local | As-is | Input parameters, local constants |
| `bind:` | Document-wide | Type-preserving (dict, list, int, bool) | Extracting data, computations |
| `global:` | Document-wide | String (templates expanded) | Labels, messages, query strings |
| `alias:` | Document-wide | Key aliasing | Alternative key names for dicts |
| `preamble:` | Document-wide | Jinja2 control structures | Macros, `{% set %}` variables |

**Processing order**: `preamble -> with -> query -> data load -> bind -> global -> alias -> render`

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
```embedz
---
global:
  author: John Doe
  version: 1.0
---
```

```embedz
---
data: report.csv
---
# Report by {{ author }}

{% for row in data %}
- {{ row.item }}
{% endfor %}
```
````

> **Note**: The `global.` prefix is optional. For type-preserving values (dict, list, int, bool), use `bind:` instead.

### Type-Preserving Bindings with `bind:`

Evaluate expressions while preserving their result types:

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

**Dot notation** for setting nested values is supported in both `bind:` and `global:`:

```yaml
bind:
  record: data | first
  record.note: "'Added by bind'"
global:
  record.label: Description
```

> See `man pandoc-embedz` for details on `alias:` and `preamble:`, as well as nested structures and dot notation.

## Advanced Features

These features enable powerful data processing, database access, and complex document generation workflows.

### SQL Queries on CSV/TSV

Filter, aggregate, and transform CSV/TSV data using SQL:

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

Share SQL query logic across multiple blocks using global variables:

````markdown
```{.embedz}
---
global:
  year: 2024
  start_date: "{{ year }}-01-01"
  end_date: "{{ year }}-12-31"
  date_filter: date BETWEEN '{{ start_date }}' AND '{{ end_date }}'
---
```

```{.embedz data=sales.csv}
---
query: "SELECT * FROM data WHERE {{ date_filter }}"
---
{% for row in data %}
- {{ row.date }}: ${{ row.amount }}
{% endfor %}
```
````

Variables are expanded in definition order, so later variables can reference earlier ones.

### SQLite Database

Query SQLite database files directly:

````markdown
```embedz
---
data: analytics.db
query: SELECT category, COUNT(*) as count FROM events WHERE date >= '2024-01-01' GROUP BY category
---
| Category | Count |
|----------|-------|
{% for row in data -%}
| {{ row.category }} | {{ row.count }} |
{% endfor -%}
```
````

Use the `table` parameter to read all rows from a specific table without a custom query.

### Excel Files

Read `.xlsx` / `.xls` files directly. Requires `openpyxl` (`pip install pandoc-embedz[excel]`). Leading blank rows and all-blank columns are automatically skipped.

````markdown
```embedz
---
data: report.xlsx
table: Sheet2
---
{% for row in data %}
- {{ row.item }}
{% endfor %}
```
````

Use `startrow` to skip leading description rows. Accepts an integer (1-indexed), a string to find automatically, or a list (AND logic):

````markdown
```{.embedz data=report.xlsx startrow="name"}
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```
````

Use `transpose: true` when headers run down the first column. Use `header: false` when there is no header row.

> See `man pandoc-embedz` for the full `startrow` syntax and Excel-specific details.

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
  products: products.csv
  sales: sales.csv
query: |
  SELECT p.product_name, SUM(s.quantity) as total
  FROM sales s
  JOIN products p ON s.product_id = p.product_id
  GROUP BY p.product_name
---
{% for row in data %}
- {{ row.product_name }}: {{ row.total }}
{% endfor %}
```
````

**`file:` dict with parameters (e.g., Excel sheets):**
````markdown
```embedz
---
data:
  incidents:
    file: data/report.xlsx
    table: Incidents
  phishing:
    file: data/report.xlsx
    table: Phishing
    startrow: year
query: |
  SELECT i.month, i.count, p.domestic
  FROM incidents i
  JOIN phishing p ON i.month = p.month
---
{% for row in data %}
- {{ row.month }}: {{ row.count }} (domestic: {{ row.domestic }})
{% endfor %}
```
````

Variable references, file paths, and inline data can be mixed freely within a `data:` dict.

**See [MULTI_TABLE.md](MULTI_TABLE.md) for comprehensive examples and documentation.**

### Template Macros

Create reusable template functions with Jinja2 macros:

````markdown
```{.embedz define=formatters}
{% macro format_item(title, date) -%}
**{{ title }}** ({{ date }})
{%- endmacro %}
```

```embedz
---
data: vulnerabilities.csv
---
{% from 'formatters' import format_item %}

{% for item in data %}
- {{ format_item(item.title, item.date) }}
{% endfor %}
```
````

### Preamble & Macro Sharing

Use the `preamble` section to define reusable control structures across all blocks. Named templates can also share macros via `{% from ... import %}`:

````markdown
```{.embedz define=sql-macros}
{%- macro BETWEEN(start, end) -%}
SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
{%- endmacro -%}
```

```embedz
---
global:
  fiscal_year: 2024
  start_date: "{{ fiscal_year }}-04-01"
  end_date: "{{ fiscal_year + 1 }}-03-31"
  _import: "{% from 'sql-macros' import BETWEEN %}"
  yearly_query: "{{ BETWEEN(start_date, end_date) }}"
---
```
````

### Comments in CSV/TSV/SSV

Lines starting with `#` are treated as comments and skipped by default. The `comment` parameter controls behavior: `line` (default), `head`, `inline`, or `none`.

````markdown
```{.embedz data=data.csv comment=head}
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```
````

## Standalone Rendering

Render Markdown or LaTeX files without running full Pandoc:

```bash
pandoc-embedz --standalone templates/report.tex -c config/base.yaml -o build/report.tex
```

**Command-line options:**

- `--standalone` (`-s`) enables standalone mode
- `--template TEXT` (`-t`) specifies template text directly
- `--format FORMAT` (`-f`) specifies data format for stdin
- `--config FILE` (`-c`) loads external YAML config file(s) (repeatable)
- `--output FILE` (`-o`) writes output to file (default: stdout)
- `--debug` (`-d`) enables debug output to stderr

**Quick examples:**

```bash
# Format CSV data from stdin
cat data.csv | pandoc-embedz -s -t '{% for row in data %}{{ row.name }}\n{% endfor %}' -f csv

# Use template file (data auto-read from stdin)
cat data.csv | pandoc-embedz -s template.md

# Static template without data
pandoc-embedz -s -t 'Static content'
```

### External Config Files

Both filter and standalone modes can load shared configuration:

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
pandoc-embedz -s report.md -c config/base.yaml -c config/latex.yaml
```

Config files support multiple YAML documents separated by `---` for logical grouping.

> See `man pandoc-embedz` for details on stdin behavior, multi-document YAML, and config merging.

## Best Practices

### CSV Output Escaping

When generating CSV from templates, use a macro for proper escaping:

````markdown
{%- macro csv_escape(value) -%}
  {%- set v = value | string -%}
  {%- if ',' in v or '"' in v or '\n' in v -%}
    "{{ v | replace('"', '""') }}"
  {%- else -%}
    {{ v }}
  {%- endif -%}
{%- endmacro -%}
````

### File Extension Recommendations

- **`.emz`** - Recommended for standalone templates (non-Markdown output)
- **`.embedz`** - Descriptive alternative
- **`.md`** - Only for templates that generate Markdown

### Pipeline Processing

Combine pandoc-embedz with other tools for data transformation:

```bash
extract_tool database table --columns 1-10 | \
  pandoc-embedz -s transform.emz | \
  post_process_tool > output.csv
```

Use `-s` (standalone mode) for pipeline processing. Each `.emz` file handles one transformation step.

## Debugging

Enable debug output with the `PANDOC_EMBEDZ_DEBUG` environment variable (accepts `1`, `true`, or `yes`) or the `-d` flag in standalone mode:

```bash
PANDOC_EMBEDZ_DEBUG=1 pandoc input.md --filter pandoc-embedz -o output.pdf
pandoc-embedz -s -d template.md
```

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
- Full Jinja2 templating (loops, conditionals, filters)
- Multiple data formats (CSV, JSON, YAML, TOML, SQLite, Excel, etc.)
- Code block level processing (not document-wide)
- Lightweight - no heavy dependencies
- Works with existing Pandoc workflow

See [COMPARISON.md](COMPARISON.md) for detailed comparison.

## Documentation

- [REFERENCE.md](REFERENCE.md) --- comprehensive reference manual (options, syntax, data formats, variable scoping, custom filters); also available via `man pandoc-embedz`
- [MULTI_TABLE.md](MULTI_TABLE.md) --- multi-table SQL query examples
- [COMPARISON.md](COMPARISON.md) --- comparison with alternative tools

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
