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
- ⚡ **Flexible Syntax**: YAML headers and code block attributes
- 🔁 **Template Reuse**: Define templates once, use them multiple times
- 🧩 **Template Inclusion**: Nest templates within templates with `{% include %}`
- 🎨 **Jinja2 Macros**: Create parameterized template functions
- 🌐 **Variable Scoping**: Local (`with:`) and global (`global:`) variable management
- 🏗️ **Structured Data**: Full support for nested JSON/YAML structures

## tl;dr

**Install:**
```bash
pip install git+https://github.com/tecolicom/pandoc-embedz.git
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
```{.embedz name=item-list}
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

**Render:**
```bash
pandoc report.md --filter pandoc-embedz -o output.pdf
```

Works with CSV, JSON, YAML, TOML, SQLite and more. See [Basic Usage](#basic-usage) to get started, or jump to [Advanced Features](#advanced-features) for SQL queries and database access.

## Table of Contents

- [tl;dr](#tldr)
- [Installation](#installation)
- [Basic Usage](#basic-usage) - Simple examples to get started
- [Advanced Features](#advanced-features) - SQL queries, databases, macros
- [Reference](#reference) - Technical details and syntax
- [Related Tools](#related-tools)
- [License](#license)

## Installation

From GitHub (recommended for now):

```bash
pip install git+https://github.com/tecolicom/pandoc-embedz.git
```

Or from PyPI (once released):

```bash
pip install pandoc-embedz
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

Define templates once with `name`, then reuse them with `as`. Perfect for consistent formatting across multiple data sources:

````markdown
```{.embedz name=item-list}
## {{ title }}
{% for item in data %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
```

```{.embedz data=products.csv as=item-list}
with:
  title: Product List
```

```{.embedz data=services.csv as=item-list}
with:
  title: Service List
```
````

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

### SQLite Database

Query SQLite database files directly:

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

With custom SQL query:

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

### Template Macros

Code block attributes provide a concise way to specify configuration:

````markdown
```{.embedz data=data.csv}
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```
````

#### Elegant Syntax: Combining Attributes with YAML

Attributes and YAML work together naturally. When you use `data` and `as` attributes, you can write YAML configuration without `---` delimiters:

````markdown
# Define template
```{.embedz name=product-list}
## {{ title }}
{% for item in data %}
{% set tax_included = (item.price * (1 + tax_rate)) | round(2) %}
- {{ item.product }}: ${{ item.price }} (with tax: ${{ tax_included }})
{% endfor %}
```

# Use template with parameters - no --- delimiters needed
```{.embedz data=products.csv as=product-list}
with:
  title: Product List
  tax_rate: 0.08
```
````

This reads naturally: "use products.csv as product-list template, with these parameters"

**Note**: For simple scalar values, you can also use dot notation in attributes (e.g., `with.title="Report"` or `global.author="John"`), though YAML is generally more readable for complex configurations.

#### Using Templates with Inline Data

````markdown
# Use template with inline CSV data
```{.embedz as=product-list format=csv}
product,price
Widget,19.99
Gadget,29.99
```
````

Using `header=false` for data without header row:

````markdown
```{.embedz as=product-list format=csv header=false}
Widget,19.99
Gadget,29.99
Tool,39.99
```
````

In this case, `data` will be a list of lists instead of a list of dictionaries.

**Note**: YAML configuration takes precedence over attributes. If both are specified, YAML values override attribute values.

### Template Inclusion

Break complex layouts into smaller fragments and stitch them together with `{% include %}`. Define each fragment with `name` and reuse it inside loops so formatting stays centralized.

````markdown
# Define formatting fragments
```embedz
---
name: date-format
---
{{ item.date }}
```

```embedz
---
name: title-format
---
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
```embedz
---
name: severity-badge
---
{% if item.severity == "high" %}🔴{% elif item.severity == "medium" %}🟡{% else %}🟢{% endif %}
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
### Template Macros (Advanced)

Jinja2 macros allow you to define reusable template functions with parameters, providing even more flexibility than `{% include %}` when you need parameterized helpers.

````markdown
# Define macros
```embedz
---
name: formatters
---
{% macro format_item(title, date) -%}
**{{ title }}** ({{ date }})
{%- endmacro %}

{% macro severity_badge(level) -%}
{% if level == "high" %}🔴 High{% elif level == "medium" %}🟡 Medium{% else %}🟢 Low{% endif %}
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

## Template Whitespace Handling

Templates preserve leading whitespace but remove trailing newlines, similar to shell `$(...)` behavior. The example below shows how an indented snippet keeps its spacing without accumulating extra blank lines.

````markdown
```embedz
---
name: indented-code
---
    def hello():
        print("Hello")
```
````

**Template storage** (used with `{% include %}` and macros):
- ✅ Leading whitespace preserved (indentation maintained)
- ✅ Internal newlines preserved (blank lines kept)
- ✅ Trailing newlines removed (enables inline composition)

**Output rendering** (top-level code blocks):
- ✅ Always ends with a newline (prevents concatenation with next paragraph)

This design allows clean template composition (`{% include %}` works inline) while ensuring document-level output is properly separated.

## Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| CSV | `.csv` | Comma-separated values (header support) |
| TSV | `.tsv` | Tab-separated values (header support) |
| SSV/Spaces | - | Space/whitespace-separated values (via `format: ssv` or `format: spaces`) |
| Lines | `.txt` | One item per line (plain text) |
| JSON | `.json` | Structured data (lists and objects) |
| YAML | `.yaml`, `.yml` | Structured data with hierarchies |

**Note**: SSV (Space-Separated Values) treats consecutive spaces and tabs as a single delimiter, making it ideal for manually aligned data. Both `ssv` and `spaces` can be used interchangeably.

## Variable Scoping

Use `with` to scope variables to a single embed block and `global` to share values across the document. The examples show block-limited and document-wide variables respectively.

### Local Variables (Block-scoped)

Put block-specific values under `with:` so subsequent content in the same code block can rely on them without leaking to other blocks.

````markdown
```embedz
---
data: data.csv
with:
  threshold: 100
  label: High
---
{% for row in data %}
{% if row.count > threshold %}
- {{ label }}: {{ row.name }}
{% endif %}
{% endfor %}
```
````

### Global Variables (Document-scoped)

Values under `global:` stay available to every embed block that follows a definition, enabling document-wide configuration.

````markdown
```embedz
---
global:
  threshold: 100
---
```

# Later blocks can use 'threshold'
```embedz
---
data: data.csv
---
{% for row in data if row.count > threshold %}
- {{ row.name }}
{% endfor %}
```
````

## Code Block Syntax

### Basic Structure

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

### Block Interpretation

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

Defines a reusable template with `name:`:

````markdown
```{.embedz name=my-template}
{% for item in data %}
- {{ item.value }}
{% endfor %}
```
````

**Processing**: Stores template as "my-template" → no output

#### 3. Template Usage

Uses a previously defined template with `as:`:

````markdown
```embedz
---
data: file.csv
as: my-template
---
```
````

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

### Configuration Options

#### YAML Header

| Key | Description | Example |
|-----|-------------|---------|
| `data` | Data source file path | `data: stats.csv` |
| `format` | Data format: `csv`, `tsv`, `ssv`/`spaces`, `json`, `yaml`, `toml`, `sqlite`, `lines` (auto-detected from extension) | `format: json` |
| `name` | Template name (for definition) | `name: report-template` |
| `as` | Template to use | `as: report-template` |
| `with` | Local variables (block-scoped) | `with: {threshold: 100}` |
| `global` | Global variables (document-scoped) | `global: {author: "John"}` |
| `header` | CSV/TSV has header row (default: true) | `header: false` |
| `table` | SQLite table name (required for sqlite format) | `table: users` |
| `query` | Custom SQL query (overrides table for sqlite) | `query: SELECT * FROM users WHERE active=1` |

#### Attribute Syntax

Attributes can be used instead of or in combination with YAML:

```markdown
{.embedz data=file.csv as=template}
{.embedz name=template}
{.embedz global.author="John"}
```

**Precedence**: YAML configuration overrides attribute values when both are specified.

### Data Variable

Template content can access:

- `data`: The loaded dataset (from file or inline)
- Variables from `with:` (local scope)
- Variables from `global:` (document scope)

### Template Content

Uses Jinja2 syntax with full feature support:

- Variables: `{{ variable }}`
- Loops: `{% for item in data %} ... {% endfor %}`
- Conditionals: `{% if condition %} ... {% endif %}`
- Filters: `{{ value | filter }}`
- Macros: `{% macro name(args) %} ... {% endmacro %}`
- Include: `{% include 'template-name' %}`

For detailed Jinja2 template syntax and features, see the [Jinja2 documentation](https://jinja.palletsprojects.com/).

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
