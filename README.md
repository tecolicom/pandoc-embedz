# pandoc-embedz

[![Tests](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml/badge.svg)](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/pandoc-embedz.svg)](https://badge.fury.io/py/pandoc-embedz)
[![Python Versions](https://img.shields.io/pypi/pyversions/pandoc-embedz.svg)](https://pypi.org/project/pandoc-embedz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Pandoc filter for embedding data-driven content in Markdown documents using Jinja2 templates. Transform your data into beautiful documents with minimal setup.

## Features

- 🔄 **Full Jinja2 Support**: Loops, conditionals, filters, macros, and all template features
- 📊 **6 Data Formats**: CSV, TSV, SSV/Spaces (whitespace-separated), lines, JSON, YAML
- 🎯 **Auto-Detection**: Automatically detects format from file extension
- 📝 **Inline & External Data**: Support both inline data blocks and external files
- ⚡ **Flexible Syntax**: YAML headers, code block attributes, and dot notation for variables
- ✨ **Elegant Syntax**: `{.embedz data=file.csv as=template}` with optional YAML delimiters
- 🔁 **Template Reuse**: Define templates once, use them multiple times
- 🧩 **Template Inclusion**: Nest templates within templates with `{% include %}`
- 🎨 **Jinja2 Macros**: Create parameterized template functions
- 🌐 **Variable Scoping**: Local (`with:`) and global (`global:`) variable management
- 🔧 **Dot Notation**: Simple variables via attributes: `with.title="Title"` `global.author="John"`
- 🏗️ **Structured Data**: Full support for nested JSON/YAML structures

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

## Quick Start

Create a markdown file with a data block:

```markdown
# Monthly Report

​```embedz
---
data: stats.csv
---
| Month | Count |
|:------|------:|
{% for row in data %}
| {{ row.month }} | {{ row.count }} |
{% endfor %}
​```
```

Convert with Pandoc:

```bash
pandoc report.md --filter pandoc-embedz -o report.pdf
```

## Usage Examples

### CSV File (Auto-detected)

```markdown
​```embedz
---
data: data.csv
---
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
​```
```

### JSON Structure

```markdown
​```embedz
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
​```
```

### Inline Data

```markdown
​```embedz
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
​```
```

### Attribute Syntax

Code block attributes provide a concise way to specify configuration:

```markdown
​```{.embedz data=data.csv}
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
​```
```

#### Elegant Syntax: Combining Attributes with YAML

Attributes and YAML work together naturally. When you use `data` and `as` attributes, you can write YAML configuration without `---` delimiters:

```markdown
# Define template
​```{.embedz name=product-list}
{% for item in data %}
- {{ item.product }}: ${{ item.price }}
{% endfor %}
​```

# Use template with parameters - no --- delimiters needed
​```{.embedz data=products.csv as=product-list}
with:
  title: "Product List"
  tax_rate: 0.08
​```
```

This reads naturally: "use products.csv as product-list template, with these parameters"

#### Dot Notation for Variables

For simple scalar values, use dot notation in attributes:

```markdown
# with.* for template parameters (replaces YAML with:)
​```{.embedz data=data.csv as=template with.title="Report" with.year="2024"}

# global.* for document-wide variables
​```{.embedz global.author="John" global.version="1.0"}

# Accessible in templates as {{ title }} or {{ with.title }}
​```
```

**Dot notation supports**:
- Single-level nesting: `with.key="value"` ✅
- Multi-level nesting: `with.nested.key` ❌ (use YAML for complex structures)
- Boolean conversion: `with.debug="true"` → `True`
- Works with any key: `with.*`, `global.*`, or custom keys

#### Using Templates with Inline Data

```markdown
# Use template with inline CSV data
​```{.embedz as=product-list format=csv}
product,price
Widget,19.99
Gadget,29.99
​```
```

Using `header=false` for data without header row:

```markdown
​```{.embedz as=product-list format=csv header=false}
Widget,19.99
Gadget,29.99
Tool,39.99
​```
```

In this case, `data` will be a list of lists instead of a list of dictionaries.

**Note**: YAML configuration takes precedence over attributes. If both are specified, YAML values override attribute values.

### Conditionals

```markdown
​```embedz
---
data: incidents.csv
---
{% for row in data %}
{% if row.severity == 'high' %}
- ⚠️ **{{ row.title }}**: {{ row.count }} incidents
{% else %}
- {{ row.title }}: {{ row.count }} incidents
{% endif %}
{% endfor %}
​```
```

### Template Reuse

Name a block with `name` so you can treat it as a reusable template. Provide the default dataset inside the same block or leave it empty and supply fresh data when you reuse it.

```markdown
# Define template
```embedz
---
name: incident-list
data: january.csv
---
{% for row in data %}
- {{ row.date }}: {{ row.title }}
{% endfor %}
```

# Reuse template with new data
```embedz
---
as: incident-list
data: february.csv
---
```
```
### Template Inclusion (Nested Templates)

Break complex layouts into smaller fragments and stitch them together with `{% include %}`. Define each fragment with `name` and reuse it inside loops so formatting stays centralized.

```markdown
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
- {% include 'date-format' with context %} {% include 'title-format' with context %}
{% endfor %}
```
```

The `with context` clause forwards the current loop variables so included templates can read `item`. You can also layer includes, for example:

```markdown
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
```
### Template Macros (Advanced)

Jinja2 macros allow you to define reusable template functions with parameters, providing even more flexibility than `{% include %}` when you need parameterized helpers.

```markdown
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
- {{ format_item(item.title, item.date) }} - {{ severity_badge(item.severity) }}
{% endfor %}
```
```

**Macro vs Include**:
- **Macros**: Accept parameters, more flexible, explicit imports required
- **Include**: Simpler, uses current context automatically, no parameters

## Template Whitespace Handling

Templates preserve leading whitespace but remove trailing newlines, similar to shell `$(...)` behavior. The example below shows how an indented snippet keeps its spacing without accumulating extra blank lines.

```markdown
​```embedz
---
name: indented-code
---
    def hello():
        print("Hello")
​```
```

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

```markdown
​```embedz
---
data: data.csv
with:
  threshold: 100
  label: "High"
---
{% for row in data %}
{% if row.count > threshold %}
- {{ label }}: {{ row.name }}
{% endif %}
{% endfor %}
​```
```

### Global Variables (Document-scoped)

Values under `global:` stay available to every embed block that follows a definition, enabling document-wide configuration.

```markdown
​```embedz
---
global:
  threshold: 100
---
​```

# Later blocks can use 'threshold'
​```embedz
---
data: data.csv
---
{% for row in data if row.count > threshold %}
- {{ row.name }}
{% endfor %}
​```
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
- **R Markdown** - Similar to Quarto, requires R environment
- **Lua Filters** - Requires custom Lua scripting for each use case

### Why pandoc-embedz?

pandoc-embedz fills a unique niche:
- ✅ Full Jinja2 templating (loops, conditionals, filters)
- ✅ Multiple data formats (CSV, JSON, YAML, etc.)
- ✅ Code block level processing (not document-wide)
- ✅ Lightweight - no heavy dependencies
- ✅ Works with existing Pandoc workflow

See [COMPARISON.md](COMPARISON.md) for detailed comparison.

## Code Block Class Name

The filter recognizes code blocks with the `.embedz` class.

## Documentation

For complete documentation, see:
- [COMPARISON.md](COMPARISON.md) - Comparison with alternatives
- [examples/](examples/) - Usage examples

## License

MIT License

Copyright © 2025 Office TECOLI, LLC

Copyright © 2025 Kazumasa Utashiro

See [LICENSE](LICENSE) file for details.

## Author

Kazumasa Utashiro

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
