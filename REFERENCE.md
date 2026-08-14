---
title: pandoc-embedz
section: 1
header: User Manual
footer: pandoc-embedz 0.22.3
date: 2026-03-28
---

# NAME

pandoc-embedz - Pandoc filter for embedding data-driven content using Jinja2 templates

# SYNOPSIS

**pandoc** *input.md* **--filter pandoc-embedz** [**-o** *output*]

**pandoc-embedz** **-s** [**-c** *config*] [**-o** *output*] [*file* ...]

**pandoc-embedz** **-s** **-t** *template* [**-f** *format*] [**-o** *output*]

# DESCRIPTION

**pandoc-embedz** loads data from various formats (CSV, JSON, YAML, SQLite,
Excel, etc.) and renders it through Jinja2 templates, either as a Pandoc
filter embedded in Markdown documents or as a standalone template renderer.

A minimal example in Markdown:

````
```embedz
---
data: sales.csv
---
{% for row in data %}
- {{ row.product }}: {{ row.amount }}
{% endfor %}
```
````

When processed with **pandoc --filter pandoc-embedz**, the code block is
replaced by the rendered output.

The tool operates in two modes:

**Filter mode** (default)
:   Runs as a Pandoc filter. Processes `.embedz` code blocks in Markdown
    documents. Output is interpreted as Markdown and fed back into
    Pandoc's pipeline. Use this for generating documents.
    To output raw format content (e.g. LaTeX), use Pandoc's raw
    attribute syntax (`` ```{=latex} ``) within the template output.
    Use `{{ "` `` ``` `` `" }}` to emit backtick fences from Jinja2
    without interfering with the embedz code block parser.

**Standalone mode** (**-s**)
:   Renders template files directly without Pandoc. Output is plain text.
    Use this for generating CSV, configuration files, or pre-processing
    templates in shell pipelines.

# OPTIONS

These options apply to standalone mode. In filter mode, **pandoc-embedz**
is invoked automatically by Pandoc and accepts no options (except **-d**
via environment variable).

**-s**, **--standalone**
:   Enable standalone mode.

**-t**, **--template** *TEXT*
:   Use *TEXT* as the template instead of a file. When **-f** is also
    given, data is read from stdin.

**-f**, **--format** *FORMAT*
:   Data format for stdin input: **csv**, **tsv**, **ssv**, **json**,
    **yaml**, **toml**, **lines**.

**-c**, **--config** *FILE*
:   Load external YAML config file. Can be repeated. Files are merged
    in order; later files override earlier ones.

**-o**, **--output** *FILE*
:   Write output to *FILE* (default: stdout).

**-d**, **--debug**
:   Enable debug output to stderr.

**-h**, **--help**
:   Show help message.

**-v**, **--version**
:   Show version information.

# CODE BLOCK SYNTAX

An embedz code block has up to three sections separated by `---`:

````
```embedz
---
YAML configuration
---
Jinja2 template
---
Inline data (optional)
```
````

## Block types

**Data processing** --- load data and render with a template:

````
```{.embedz data=file.csv}
{% for row in data %}
- {{ row.name }}
{% endfor %}
```
````

**Template definition** --- store a named template for later reuse:

````
```{.embedz define=my-list}
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```
````

**Template usage** --- apply a named template to data:

````
```{.embedz data=file.csv as=my-list}
```
````

**Variable definition** --- set document-wide variables:

````
```{.embedz}
---
global:
  author: John Doe
---
```
````

## Content interpretation

When a block has no `---` separator, the content is interpreted based on
the attributes present:

`data` + `template`/`as`
:   Content is **YAML configuration**.

`template`/`as` only
:   Content is **inline data**.

`define`
:   Content is a **template definition**.

none, or `data` only
:   Content is a **template**.

When `---` is present, the standard three-section structure applies
regardless of attributes.

# CONFIGURATION OPTIONS

The following keys can be used in the YAML header or as code block
attributes.

## Data loading

**data**
:   Data source. A file path (string), multiple sources (dict), or
    inline data. In a dict, each key becomes a SQL table name.
    Supports `file:` dict for per-source parameters.
    Can also reference a `bind:` variable by name.

**format**
:   Data format override: **csv**, **tsv**, **ssv** (or **spaces**),
    **json**, **yaml**, **toml**, **sqlite**, **excel**, **lines**.
    Auto-detected from file extension when omitted.

**header**
:   Whether data has a header row (CSV/TSV/SSV/Excel). Default: **true**.
    See *DATA FORMATS* for details.

**comment**
:   Comment handling for `#` lines (CSV/TSV/SSV). Default: **line**.
    See *DATA FORMATS* for modes.

**columns**
:   Fixed column count (SSV only). See *DATA FORMATS*.

**table**
:   Sheet name (Excel) or table name (SQLite).

**startrow**
:   Row to start reading from (Excel). Accepts integer, string, or list.
    See *DATA FORMATS* for the full syntax.

**transpose**
:   Swap rows and columns (Excel). Default: **false**.

**query**
:   SQL query to filter or transform data. The table name in SQL is
    `data` for single-source blocks. For multi-table blocks, use
    the keys from the `data:` dict.

**config**
:   External YAML config file path(s) to merge before inline settings.

## Templates

**define**
:   Define a named template. The block produces no output.

**template** (or **as**)
:   Use a previously defined template. In YAML headers, `template` is
    preferred; in attributes, `as` is shorter.

## Variables

**with**
:   Block-local variables. Available in the current block only.

**bind**
:   Type-preserving bindings (document-wide). Values are Jinja2
    expressions; result types (dict, list, int, bool) are preserved.

**global**
:   Document-wide variables. Values are strings; those containing
    `{{` or `{%` are expanded as Jinja2 templates.

**alias**
:   Add alternative keys to all dictionaries. Does not overwrite
    existing keys.

**preamble**
:   Jinja2 control structures (macros, `{% set %}`) shared across all
    subsequent blocks.

## Attribute syntax

Dot notation sets nested values without a YAML header:

    ```{.embedz data=file.csv as=template with.key=value}
    ```

YAML configuration overrides attribute values when both are specified.

## Processing order

    preamble → with → query → data load → bind → global → alias → render

Variables from earlier stages are available in later stages within the
same block.

# DATA FORMATS

The data format is auto-detected from file extension. Use **format** to
override. The following formats are supported:

**csv** (`.csv`), **tsv** (`.tsv`), **ssv**/**spaces**, **lines** (`.txt`),
**json** (`.json`), **yaml** (`.yaml`, `.yml`), **toml** (`.toml`),
**sqlite** (`.db`, `.sqlite`), **excel** (`.xlsx`, `.xls`).

JSON, YAML, and TOML files are loaded as-is into the `data` variable
(lists, dicts, or nested structures). Lines format produces a simple list
of strings. The remaining formats have additional parameters described
below.

## CSV, TSV, and SSV

These tabular formats share the following parameters:

**header** (default: **true**)
:   When true, the first row is used as column names and each subsequent
    row becomes a dict (`row.name`). When false, rows are lists
    accessed by index (`row[0]`).

**comment** (default: **line**)
:   Controls how lines starting with `#` are handled.
    **line**: skip all `#` lines anywhere in the file.
    **head**: skip leading `#` lines only (preserves `#` in data rows).
    **inline**: skip from unquoted `#` to end of line.
    **none** or **false**: disable comment handling.
    Blank lines are always ignored regardless of this setting.

**query**
:   SQL query to filter or transform the data. Data is loaded into an
    in-memory SQLite database; the table name in SQL is `data`.

SSV (space-separated values) treats consecutive ASCII spaces as a
single delimiter. Non-breaking spaces (NBSP, `U+00A0`) and full-width
spaces (`U+3000`) are **not** treated as delimiters, so they can be
used within fields. There is no default file extension; specify
`format: ssv` or `format: spaces` explicitly.

**columns** (SSV only)
:   Fixed column count. Data is split into exactly this many columns;
    the last column captures all remaining content including spaces.
    Useful for free-form text in the last field.

## Excel

Requires the `openpyxl` package (`pip install 'pandoc-embedz[excel]'`).

**table**
:   Sheet name to read. Defaults to the first sheet.

**header** (default: **true**)
:   Same as CSV. With `header: false`, rows are lists.

**startrow**
:   Skip leading rows before reading data. Accepts multiple forms:

    *integer* (1-indexed)
    :   Start reading from this row number. Example: `startrow: 3`.

    *string*
    :   Search for a row containing a cell that exactly matches the
        string, and use that row as the header (or first data row with
        `header: false`). Example: `startrow: name`.

    *"N:text"*
    :   Match only in column N (1-based). Example: `startrow: "1:year"`.

    *list*
    :   All patterns must match in the same row (AND logic). Each element
        can be a plain string or `"N:text"`. Example:
        `startrow: [year, month]`.

**transpose** (default: **false**)
:   Swap rows and columns. Useful when headers run down the first column
    instead of across the first row. Can be combined with
    `header: false`.

The following automatic cleanup is applied:

- Leading blank rows and all-blank columns are removed.
- Empty cells in the header row get auto-generated names (`column_0`,
  `column_2`, etc., based on position).
- Duplicate header names get a numeric suffix (`score`, `score_1`,
  `score_2`, ...).
- Empty cells in data rows become empty strings.
- Empty sheets return an empty list `[]` with a warning to stderr.

**query** works the same way as CSV (in-memory SQLite).

## SQLite

Reads SQLite database files directly.

**table**
:   Table name to read. All rows and columns are loaded.

**query**
:   SQL query to execute against the database. When both **table** and
    **query** are specified, **query** takes precedence.

# VARIABLE SCOPING

**with** --- block-local, as-is type
:   Input parameters and local constants.

**bind** --- document-wide, type-preserving
:   Computed values and data access. Result types (dict, list, int,
    bool) are preserved.

**global** --- document-wide, string type
:   Labels, query strings. Values containing `{{` or `{%` are expanded
    as Jinja2 templates.

**alias** --- document-wide, key aliasing
:   Alternative key names for dictionaries. Does not overwrite existing
    keys.

**preamble** --- document-wide, Jinja2 control structures
:   Macros and `{% set %}` variables shared across all subsequent blocks.

**bind:** values are Jinja2 expressions (string literals require quotes:
`"'hello'"`). **global:** values are plain strings unless they contain
`{{` or `{%`.

Dot notation works in both **bind:** and **global:** to set nested values:

```yaml
bind:
  record: data | first
  record.note: "'Added by bind'"
global:
  record.label: Description text
```

# CUSTOM FILTERS

**to_dict**(*key*, *strict=True*, *transpose=False*)
:   Convert a list of dicts to a dict keyed by the given field.
    With *strict=True* (default), duplicate keys raise an error.
    With *transpose=True*, column-keyed dicts are added for dual access:
    `result[2023].value` and `result.value[2023]`.

**raise**
:   Raise an error with a custom message. Useful for template validation.

        {{ "label is required" | raise }}

**regex_replace**(*pattern*, *replacement=""*, *ignorecase=False*, *multiline=False*, *count=0*)
:   Replace substrings matching a regular expression.

        {{ text | regex_replace("[（）]", "") }}

**regex_search**(*pattern*, *ignorecase=False*, *multiline=False*)
:   Return the first match of a pattern, or empty string if none.
    The empty string is falsy in Jinja2 conditionals.

        {% if value | regex_search("error|warning") %}...{% endif %}

# MULTI-TABLE DATA

Load multiple sources and combine them with SQL:

```yaml
data:
  products: products.csv
  sales: sales.csv
query: |
  SELECT p.name, SUM(s.qty) as total
  FROM sales s JOIN products p ON s.id = p.id
  GROUP BY p.name
```

Without a `query`, each table is accessed via `data.tablename`.

The `file:` dict syntax passes per-source parameters:

```yaml
data:
  sheet1:
    file: report.xlsx
    table: Sheet1
  sheet2:
    file: report.xlsx
    table: Sheet2
    startrow: year
```

Variable references, file paths, and inline data can be mixed freely
within a `data:` dict.

# EXAMPLES

## Basic CSV rendering

````
```{.embedz data=scores.csv}
{% for row in data %}
- {{ row.name }}: {{ row.score }}
{% endfor %}
```
````

## Template reuse

````
```{.embedz define=item-list}
## {{ title }}
{% for row in data %}
- {{ row.name }}: {{ row.value }}
{% endfor %}
```

```{.embedz data=products.csv as=item-list}
with:
  title: Product List
```
````

## SQL aggregation

````
```{.embedz data=sales.csv}
---
query: |
  SELECT product, SUM(amount) as total
  FROM data GROUP BY product
  ORDER BY total DESC
---
| Product | Total |
|---------|-------|
{% for row in data -%}
| {{ row.product }} | {{ row.total }} |
{% endfor %}
```
````

## Standalone pipeline

```
cat data.csv | pandoc-embedz -s transform.emz > output.csv
```

## External config

```
pandoc-embedz -s report.tex -c config/base.yaml -o build/report.tex
```

Config files support multiple YAML documents separated by `---` for
logical grouping.

# ENVIRONMENT

**PANDOC_EMBEDZ_DEBUG**
:   Enable debug output. Accepts **1**, **true**, or **yes**. Works in
    both filter and standalone modes.

# FILES

*.emz*
:   Recommended extension for standalone templates (non-Markdown output).

*.embedz*
:   Alternative extension for standalone templates.

# SEE ALSO

**pandoc**(1)

Jinja2 template documentation: <https://jinja.palletsprojects.com/>

This manual covers the complete reference for syntax, configuration,
data formats, and filters. The project README provides installation
instructions, tutorial examples, and related tools:

<https://github.com/tecolicom/pandoc-embedz#readme>

# AUTHOR

Kazumasa Utashiro

# BUGS

Report bugs at <https://github.com/tecolicom/pandoc-embedz/issues>.
