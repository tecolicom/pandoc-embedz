# pandoc-embedz

[![Tests](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml/badge.svg)](https://github.com/tecolicom/pandoc-embedz/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/pandoc-embedz.svg)](https://badge.fury.io/py/pandoc-embedz)
[![Python Versions](https://img.shields.io/pypi/pyversions/pandoc-embedz.svg)](https://pypi.org/project/pandoc-embedz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Pandoc filter for embedding data-driven content in Markdown documents using Jinja2 templates. Transform your data into beautiful documents with minimal setup.

## Features

- 🔄 **Full Jinja2 Support**: Loops, conditionals, filters, and all template features
- 📊 **6 Data Formats**: CSV, TSV, SSV (space-separated), lines, JSON, YAML
- 🎯 **Auto-Detection**: Automatically detects format from file extension
- 📝 **Inline & External Data**: Support both inline data blocks and external files
- 🔁 **Template Reuse**: Define templates once, use them multiple times
- 🌐 **Variable Scoping**: Local and global variable management
- 🏗️ **Structured Data**: Full support for nested JSON/YAML structures

## Installation

```bash
pip install pandoc-embedz
```

Dependencies: `panflute`, `jinja2`, `pandas`, `pyyaml`

## Quick Start

Create a markdown file with a data block:

```markdown
# Monthly Report

​```{.embedz}
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
​```{.embedz}
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
​```{.embedz}
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
​```{.embedz}
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

### Conditionals

```markdown
​```{.embedz}
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

```markdown
# Define template
​```{.embedz}
---
name: incident-list
data: january.csv
---
{% for row in data %}
- {{ row.date }}: {{ row.title }}
{% endfor %}
​```

# Reuse template
​```{.embedz}
---
template: incident-list
data: february.csv
---
​```
```

## Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| CSV | `.csv` | Comma-separated values (header support) |
| TSV | `.tsv` | Tab-separated values (header support) |
| SSV | - | Space-separated values (via `format: ssv`) |
| Lines | `.txt` | One item per line (plain text) |
| JSON | `.json` | Structured data (lists and objects) |
| YAML | `.yaml`, `.yml` | Structured data with hierarchies |

## Variable Scoping

### Local Variables (Block-scoped)

```markdown
​```{.embedz}
---
data: data.csv
local:
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

```markdown
​```{.embedz}
---
global:
  threshold: 100
---
​```

# Later blocks can use 'threshold'
​```{.embedz}
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
