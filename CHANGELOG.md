# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2025-11-21

### Added
- Standalone renderer mode via `pandoc-embedz --render` (supports LaTeX/Markdown files, `--config`, and `--output`)
- External YAML configuration files for both code blocks (`config:`) and the standalone renderer (share data/global/preamble definitions)
- `.embedz` blocks without `data:` now render their template content using global/with variables, so simple substitutions work without dummy datasets

## [0.4.1] - 2025-11-20

### Added
- Debug mode with `PANDOC_EMBEDZ_DEBUG` environment variable (accepts `1`, `true`, `yes`)
- Detailed debug output for all processing steps (configuration, templates, variables, data, rendering)
- `--help` / `-h` command-line option for comprehensive usage information
- `--version` / `-v` command-line option for version display
- Help message with examples, environment variables, and documentation links
- Debug mode documentation in AGENTS.md

### Changed
- Improved README structure with Usage Patterns and Tables & Options subsections
- Enhanced preamble section examples with practical fiscal year scenarios
- Changed installation priority to PyPI (stable) over GitHub (development)
- Updated argument handling to allow Pandoc's internal format arguments

### Fixed
- Code block nesting in AGENTS.md (changed outer blocks from ``` to ```` for proper nesting)
- Argument handling to prevent errors when Pandoc passes format arguments to filter

## [0.4.0] - 2025-11-20

### Added
- `preamble` section for document-wide control structures (macros, `{% set %}`, imports)
- Unified template environment: all templates evaluated in single global Jinja2 environment
- Direct macro usage in queries and global variables without explicit import
- `_get_jinja_env()` function for global environment management
- `_render_template()` function for unified template rendering

### Changed
- Refactored template evaluation to use single shared environment (GLOBAL_ENV)
- Simplified `_prepare_variables()`: reduced from ~35 to ~20 lines (40% reduction)
- Changed CONTROL_STRUCTURES from List[str] to CONTROL_STRUCTURES_STR (str)
- All template expansions now use unified `_render_template()` function
- Removed keyword-based control structure detection from global variables (use `preamble` instead)
- Macros defined in named templates are automatically added to global control structures
- Improved documentation with preamble section explanation and examples

### Fixed
- Empty preamble strings no longer add unnecessary newlines

## [0.3.0] - 2025-11-19

### Added
- Macro sharing across global variables using `{% from 'template-name' import MACRO %}`
- Template inclusion support in global variable processing via Jinja2 Environment
- Automatic recognition of control structures (macros, imports, includes)
- Smart leading newline removal from control structures while preserving intentional whitespace

### Changed
- Refactored global variable processing for better code organization
- Improved documentation with macro sharing examples and use cases

### Fixed
- Leading newlines from non-output-producing control structures are now properly removed
- Intentional leading/trailing spaces and tabs in template variables are now preserved

## [0.2.0] - 2025-11-17

### Added
- SQLite database support with `table` and `query` parameters
- TOML format support
- SQL query support for CSV, TSV, and SSV formats using pandas
- Multi-table SQL support for joining multiple data sources
- Inline data support for multi-table SQL queries
- Query template variable expansion with Jinja2
- Nested global variable references (variables can reference other variables)
- Attribute-based configuration using dot notation (e.g., `with.title="Example"`)
- Support for arbitrary attribute namespaces beyond `global` and `with`

### Changed
- Variable prefix (`global.`, `with.`) is now optional in templates and queries
- Improved documentation structure with Basic/Advanced separation
- Better error messages and examples throughout documentation

### Fixed
- Test suite now runs all tests before committing
- Table alignment in multi-table documentation

## [0.1.0] - 2025-11-14

### Added
- Initial release
- Support for 6 data formats: CSV, TSV, SSV, lines, JSON, YAML
- Full Jinja2 template support (loops, conditionals, filters)
- Auto-detection of format from file extension
- Template reuse functionality
- Local and global variable scoping
- Support for `.embedz` code block class
- Inline and external data sources
- Structured data support (nested JSON/YAML)
- User-friendly error messages with helpful hints

[Unreleased]: https://github.com/tecolicom/pandoc-embedz/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/tecolicom/pandoc-embedz/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tecolicom/pandoc-embedz/releases/tag/v0.1.0
