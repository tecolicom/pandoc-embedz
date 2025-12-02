# Repository Guidelines

Quick reference for developers working on pandoc-embedz.

## Quick Reference

### Common Commands
```bash
# Development setup
uv sync --all-extras              # Install dependencies

# Testing
uv run pytest tests/              # Run all tests (REQUIRED before commit)
uv run pytest tests/test_*.py     # Run specific test file
PANDOC_EMBEDZ_DEBUG=1 pandoc ...  # Enable debug output

# Build and release
uv build                          # Build package
make release-n                    # Preview release (dry run)
make release                      # Execute release

# Manual testing
pandoc report.md --filter pandoc-embedz -o output.pdf
```

### Project Structure
```
pandoc_embedz/
├── filter.py           # Pandoc filter entry point
├── data_loader.py      # Data format loaders (CSV, JSON, SQLite, etc.)
├── config.py           # Configuration parsing and validation
└── main.py             # CLI entry point (standalone mode)

tests/
├── test_attributes.py  # Attribute parsing
├── test_load_data.py   # Data loading
├── test_template.py    # Template functionality
├── test_variables.py   # Variable scoping
├── test_standalone.py  # Standalone mode
└── fixtures/           # Test data files

examples/               # Runnable examples
CODE_ANALYSIS.md        # Code quality analysis
```

---

## Development Workflow

### Setup

**With uv (Recommended):**
```bash
uv sync --all-extras        # Install dependencies + dev tools
uv add <package>            # Add dependency
uv remove <package>         # Remove dependency
```

**With pip (Alternative):**
```bash
pip install -e .[dev]       # Editable install with dev dependencies
python -m build             # Build package
```

### Testing

**CRITICAL:** Always run full test suite before committing:
```bash
uv run pytest tests/        # Run ALL tests (not individual files)
```

Running individual test files may miss failures in other suites.

**Debug Mode:**
```bash
PANDOC_EMBEDZ_DEBUG=1 pandoc report.md --filter pandoc-embedz -o output.pdf
```

Debug output includes:
- Configuration parsing (attributes and YAML)
- Template operations (save/load)
- Variable preparation (global/local)
- Data loading and SQL queries
- Template rendering context

All debug messages are prefixed with `[DEBUG]` and written to stderr.

---

## Code Guidelines

### Style & Conventions
- **PEP 8 compliant**: 4-space indentation, `snake_case` functions, `CONSTANT_CASE` for module constants
- **Type hints**: Use explicit typing for function signatures
- **Docstrings**: Document public functions and complex logic
- **Security**: Always use `validate_file_path()` for file operations
- **Comments**: Use English for all comments (international collaboration)

### Testing
- Tests in `tests/` with `Test*` classes and `test_*` functions
- Store fixtures in `tests/fixtures/`
- Add tests for new features and bug fixes
- Verify actual content, not just types:
  ```python
  # Good
  assert isinstance(result, list)
  markdown = pf.convert_text(result, input_format='panflute', output_format='markdown')
  assert 'expected content' in markdown

  # Insufficient
  assert isinstance(result, list)  # Doesn't verify rendering
  ```

### Security
- **Path traversal protection**: Use `validate_file_path()` (in `config.py`)
- **SQL injection protection**: Parameterized queries via pandas/sqlite3
- **Template security**: Jinja2 templates can execute Python code - only process trusted templates

---

## Commit & Release

### Commit Guidelines
- Run `uv run pytest tests/` before committing
- Follow current git log style: capitalized verb phrase, no terminal periods
- PRs should target `main` with summary and test results
- Before modifying files: summarize plan, wait for confirmation, then proceed
- Tag commits with assistant info: `(via Claude Code / Sonnet 4.5)`

### Release Process (Minilla-style)

**Workflow:**
1. Edit code and add CHANGELOG entry:
   ```markdown
   ## [0.9.0] - 2025-11-26

   ### Added
   - New feature description
   ```

2. Preview release: `make release-n` (dry run, shows commands)

3. Execute release: `make release`
   - Extracts version from CHANGELOG.md (single source of truth)
   - Auto-updates `pyproject.toml` and `__init__.py`
   - Runs all tests
   - Commits with `git add -u` (includes all tracked changes)
   - Creates annotated tag with release notes
   - Pushes to GitHub
   - GitHub Actions publishes to PyPI

**Key Features:**
- CHANGELOG.md is single source of truth for version
- Automatic version number updates
- Dirty check prevents releases with uncommitted changes
- Dry run support for safe preview

**Post-Release:**
```bash
pip index versions pandoc-embedz  # Verify PyPI
pip install --no-cache-dir --upgrade pandoc-embedz
```

---

## Technical Details

### Filter Chaining

Generate code blocks for subsequent filters (e.g., pantable):

````markdown
````{.embedz format=csv}
---
---
```{.table}
{% for row in data -%}
{{ row.product }},{{ row.sales }}
{% endfor -%}
```
---
product,sales
Widget,100
````
````

**Key points:**
- Use 4 backticks for outer fence to write 3 backticks inside
- Empty YAML header `---\n---` is required
- Blocks without data return empty list `[]` (by design)

### Data and Template Sections

**Three-section structure:**
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

**Critical: Template usage with inline data requires THREE `---` separators:**
````markdown
```embedz
---
template: my-template
format: json
---
(empty template section)
---
[{"data": "here"}]
```
````

Structure: YAML header → `---` → template section → `---` → data section

### Template Variables and Queries

**Global variables** are available throughout the document:
````markdown
```{.embedz}
---
global:
  year: 2024
  start_date: "{{ year }}-01-01"  # Variables can reference other globals
  query: "SELECT * FROM data WHERE date >= '{{ start_date }}'"
---
```

```{.embedz data=sales.csv}
---
query: "{{ query }}"  # Use global variable in query
---
{% for row in data %}
- {{ row.product }}: {{ row.amount }}
{% endfor %}
```
````

**Key points:**
- Global variable values are expanded if they contain `{{` or `{%`
- Variables processed in definition order (later can reference earlier)
- Prefix `global.` is optional: `{{ year }}` = `{{ global.year }}`
- Works with CSV, TSV, SSV, and SQLite

### Preamble for Shared Macros

**Preamble** defines document-wide control structures:
````markdown
```{.embedz}
---
preamble: |
  {% set fiscal_year = 2024 %}
  {% macro BETWEEN(start, end) -%}
  SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
  {%- endmacro %}
global:
  yearly_query: "{{ BETWEEN(fiscal_year ~ '-01-01', fiscal_year ~ '-12-31') }}"
---
```

```{.embedz data=sales.csv}
---
query: "{{ yearly_query }}"
---
Template here
```
````

**Alternative:** Define macros in named templates (auto-shared):
````markdown
```{.embedz define=sql-macros}
{%- macro BETWEEN(start, end) -%}
SELECT * FROM data WHERE date BETWEEN '{{ start }}' AND '{{ end }}'
{%- endmacro -%}
```
````

**Implementation:**
- All templates share single Jinja2 environment (`GLOBAL_ENV`)
- Preamble prepended to all templates via `CONTROL_STRUCTURES_STR`
- Macros from named templates auto-added to control structures

### Parameter Aliasing

**User-facing parameters:**

| Purpose | Recommended | Alternative | Deprecated |
|---------|-------------|-------------|------------|
| Template definition | `define` | - | `name` (shows warning) |
| Template usage (YAML) | `template` | `as` | - |
| Template usage (attributes) | `as` | `template` | - |

**Example:**
````markdown
```{.embedz define=my-template}
...
```

```{.embedz data=file.csv template=my-template}
```

```{.embedz data=file.csv as=my-template}
```
````

**Implementation:** `pandoc_embedz/config.py`
- `PARAMETER_PREFERRED_ALIASES`: Maps external aliases to internal names
- `DEPRECATED_DIRECT_USE`: Parameters that show warnings
- `normalize_config()`: Converts aliases and warns about deprecated usage

**Design rationale:**
- `define` vs `template`/`as` clarifies definition vs usage
- `template` is declarative (YAML), `as` is concise (attributes)
- Both `template` and `as` work without warnings (context-dependent choice)
- `name` is deprecated but still works (backward compatibility)

**Adding new aliases:**
1. Update `PARAMETER_PREFERRED_ALIASES` in `config.py`
2. Add to `DEPRECATED_DIRECT_USE` if old name should warn
3. Add tests in `tests/test_attributes.py`
4. Update documentation

---

## Known Issues

See [CODE_ANALYSIS.md](CODE_ANALYSIS.md) for:
- Test structure issues (template usage with inline data)
- Code quality improvements
- Test coverage gaps
- Prioritized action plan

**High-priority items:**
- Fix `test_use_saved_template` to use 3-separator structure
- Replace Japanese comments with English
- Enhance test assertions beyond `isinstance` checks

### Global Variable Expansion from Query Results (Implemented)

**Status:** ✅ Implemented in v0.9.3

Global variables can now reference loaded data. The processing order is:

1. Prepare preamble and with variables
2. Expand query (using existing global variables from previous blocks)
3. Load data
4. **Expand bind expressions (type-preserving)**
5. **Expand global variables (with access to loaded data and bind results)**
6. Render template

**Example:**
```yaml
---
format: csv
query: SELECT * FROM data WHERE value > 80
global:
  filtered_count: "{{ data | length }}"
  total_value: "{{ data | sum(attribute='value') }}"
---
Filtered count: {{ filtered_count }}, Total: {{ total_value }}
---
name,value
Alice,100
Bob,80
Charlie,120
```

**Important:** Variables used in `query:` can come from:
- `with:` in the same block (input parameters)
- `global:` from a previous block

Variables in the same block's `global:` cannot be used in `query:` (they are expanded after data loading).

```yaml
# Using with: in the same block
---
format: csv
with:
  min_value: 80
query: SELECT * FROM data WHERE value >= {{ min_value }}
global:
  filtered_total: "{{ data | sum(attribute='value') }}"
---

# Or using global: from a previous block
---
global:
  min_value: 80
---
```

---

### Type-Preserving Bindings with bind:

**Status:** ✅ Implemented

The `bind:` section evaluates Jinja2 expressions while preserving their result type (dict, list, int, bool, None). Unlike `global:`, values are not converted to strings.

**Processing order:** with → query → data load → bind → global → render

**Example:**
```yaml
---
format: csv
bind:
  first: data | first           # dict type preserved
  total: data | sum(attribute='value')  # int type preserved
  has_data: data | length > 0   # bool type preserved
---
Name: {{ first.name }}, Total: {{ total }}
---
name,value
Alice,100
Bob,200
```

**Nested structures:**
```yaml
bind:
  first: data | first
  stats:
    name: first.name
    value: first.value
    doubled: first.value * 2
```

### Dot Notation for Nested Values

**Status:** ✅ Implemented

Both `bind:` and `global:` support dot notation in keys to set nested values:

```yaml
bind:
  record: data | first
  record.note: "'Added note'"    # Adds 'note' key to record dict
global:
  record.label: Description text  # Adds 'label' key (no quotes needed)
```

**Key differences:**
- `bind:` values are Jinja2 expressions (string literals need quotes)
- `global:` values are plain strings (unless containing `{{` or `{%`)

**Creates intermediate dicts:**
```yaml
global:
  config.settings.name: My App   # Creates config → settings → name
```

**Error handling:**
- Raises `ValueError` if parent exists but is not a dictionary

---

## Real-World Usage Patterns

### Standalone Mode for Data Processing

Standalone mode (`-s`) is particularly useful for CSV transformation pipelines:

```bash
# Data normalization pipeline
extract_tool database.db table --columns 1-11 | \
  pandoc-embedz -s normalize.emz | \
  other_tool > output.csv
```

**Key characteristics:**
- Output is plain text (not processed as Markdown)
- Safe for CSV, JSON, configuration files
- No Pandoc API calls - pure template rendering
- Can be chained with other Unix tools

### CSV Output Best Practices

When generating CSV output, proper escaping is critical:

```jinja2
{%- macro csv_escape(value) -%}
  {%- set v = value | string -%}
  {%- if ',' in v or '"' in v or '\n' in v -%}
    "{{ v | replace('"', '""') }}"
  {%- else -%}
    {{ v }}
  {%- endif -%}
{%- endmacro -%}
```

**Why this matters:**
- CSV fields containing `,`, `"`, or newlines must be quoted
- Double quotes inside fields must be escaped as `""`
- Without proper escaping, CSV parsers will fail

### File Naming Conventions

**Recommended extensions for standalone templates:**
- `.emz` - Short, memorable (3 characters)
- `.embedz` - Descriptive alternative
- `.md` - Only for templates that generate Markdown

**Example structure:**
```
templates/
├── normalize_data.emz       # CSV transformation
├── format_report.emz        # Data formatting
└── report_body.md           # Markdown generation
```

### Filter Mode vs Standalone Mode

**Critical distinction:**

| Aspect | Filter Mode | Standalone Mode |
|--------|-------------|-----------------|
| Invocation | `--filter pandoc-embedz` | `-s` flag |
| Output format | Markdown (to Pandoc AST) | Plain text |
| Pandoc API | Called | Not called |
| Use case | Document embedding | Data transformation |

**Implementation notes:**
- Filter mode: `filter.py` processes code blocks, returns Markdown
- Standalone mode: `main.py` renders template, outputs text
- Output format note in README.md (line 976-978) clarifies this

---

## Additional Resources

- **README.md**: User documentation and examples (includes Best Practices section)
  - Basic usage and advanced features
  - Best Practices: CSV escaping, file extensions, pipeline patterns
  - Filter mode vs standalone mode clarification
- **MULTI_TABLE.md**: Advanced multi-table SQL features
- **COMPARISON.md**: Comparison with alternative tools
- **CHANGELOG.md**: Version history and release notes
- **CODE_ANALYSIS.md**: Code quality analysis and improvement recommendations
