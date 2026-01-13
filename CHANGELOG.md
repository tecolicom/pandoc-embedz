# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.17.0] - 2026-01-13

### Added
- Variable references in YAML `data:` section for multi-table format
  - `data: {t1: my_variable, t2: file.csv}` now supports mixing variables and file paths
  - Variables from `bind:` can be referenced alongside file paths
  - SQL queries work with mixed variable/file sources
- Warning when `format` is specified but data section is missing
  - Helps detect missing third `---` separator

## [0.16.0] - 2026-01-04

### Added
- Japanese translation of README (README.JA.md)
- `regex_search` custom Jinja2 filter for pattern matching
  - Compatible with Ansible's `regex_search` filter
  - Returns the matched substring, or empty string if no match
  - Supports `ignorecase` and `multiline` parameters
  - Empty string is falsy, making it easy to use in conditionals
  - Example: `{{ value | regex_search("error|warning") }}` returns matched keyword

### Changed
- Update copyright year to 2025-2026

### Fixed
- Strip leading newline from rendered output when preamble is used
- Fix extra empty line when preamble ends with newline

## [0.15.0] - 2025-12-10

### Added
- `columns` parameter for SSV format
  - Specifies fixed column count, preserving spaces in the last column
  - Useful for data with free-form text fields: `format: ssv` with `columns: 3`
  - Example: `"1 Alice Software engineer"` → `["1", "Alice", "Software engineer"]`

## [0.14.0] - 2025-12-05

### Added
- `regex_replace` custom Jinja2 filter for regular expression substitution
  - Compatible with Ansible's `regex_replace` filter
  - Supports `ignorecase`, `multiline`, and `count` parameters
  - Unicode property support (`\p{P}`, `\p{Ps}`, `\p{Pe}`, etc.) via `regex` module
  - Example: `{{ value | regex_replace("\\p{Ps}|\\p{Pe}", "") }}` removes all brackets
- `regex` module as a dependency for Unicode property support in regular expressions
- Validation for code block parsing results
  - Detects when Pandoc fails to parse fenced code blocks due to problematic identifiers
  - Raises clear error message when identifier contains characters like full-width parentheses
  - Helps catch template issues early instead of producing corrupted output

## [0.13.1] - 2025-12-04

### Changed
- Documentation: Use `key=` keyword argument in `to_dict` examples for clarity

## [0.13.0] - 2025-12-04

### Added
- Query support for variable data references
  - `query:` can now be applied when `data=` references a variable
  - Enables data transformation pipelines: load once, derive multiple aggregations
  - Dict variables (from `to_dict`) are automatically converted to list before query execution

## [0.12.0] - 2025-12-04

### Added
- `transpose` option for `to_dict` filter
  - Adds column-keyed dictionaries for dual access patterns
  - Example: `data | to_dict('year', transpose=True)` enables both `result[2023].value` and `result.value[2023]`
- `raise` filter for template validation
  - Raises error with custom message: `{{ "error message" | raise }}`
  - Useful for enforcing required parameters in templates

### Changed
- Variable reference in `data=` now supports dot notation for nested access
  - Example: `data=by_year.value` resolves nested dictionary values
  - Resolution rules simplified: starts with `./` or `/` → file path; otherwise try variable lookup first

## [0.11.0] - 2025-12-03

### Added
- Variable reference in `data=` attribute
  - Reference `bind:` variables (dict/list) directly instead of loading from file
  - Resolution: contains `/` or `.` → file path; exists in GLOBAL_VARS as dict/list → variable
  - Use `./filename` to force file loading when variable name conflicts

## [0.10.2] - 2025-12-03

### Changed
- `to_dict` filter now defaults to strict mode
  - Raises `ValueError` on duplicate keys by default
  - Use `strict=False` to allow duplicates (last value wins)
  - Example: `data | to_dict('year')` raises error if duplicate years exist

### Improved
- Documentation for code block content interpretation rules
  - Added table explaining how content is parsed based on attributes and `---` presence
  - Documented `data=` (empty value) for YAML configuration without loading data
  - Fixed heading levels for proper hierarchy in Reference section

### Fixed
- Windows test failures by specifying UTF-8 encoding

## [0.10.1] - 2025-12-02

### Added
- Multi-document YAML support for config files
  - Config files can contain multiple YAML documents separated by `---`
  - Documents are merged in order, with later documents overriding earlier ones
  - Sections can be written in any order; processing order is fixed
  - Enables logical grouping of settings within a single file

## [0.10.0] - 2025-11-30

### Added
- New `bind:` section for type-preserving expression evaluation
  - Evaluates Jinja2 expressions and preserves result type (dict, list, int, bool, None)
  - Enables property access on bound variables: `{{ first_row.name }}`
  - Supports nested structures with recursive expression evaluation
  - Example:
    ```yaml
    bind:
      first: data | first
      stats:
        name: first.name
        value: first.value
        is_high: first.value > 100
    ```
- Dot notation support for `bind:` and `global:` keys
  - Set nested values using dot-separated keys: `record.note: "'note'"`
  - Adds keys to existing dictionaries created by earlier bindings
  - Creates intermediate dictionaries if not present
  - Example:
    ```yaml
    bind:
      record: data | first
      record.note: "'Added note'"
    global:
      record.label: Description
    ```
- Global variables can now reference loaded data
  - `global:` section is expanded after data loading
  - Enables expressions like `{{ data | length }}` in global variables
  - Recursive template expansion in nested structures
- Custom Jinja2 filter `to_dict` for list-to-dictionary conversion
  - Converts list of dicts to a dictionary keyed by specified field
  - Example: `data | to_dict('year')` converts `[{'year': 2023, ...}]` to `{2023: {...}}`
  - Useful for accessing data by key instead of iterating with `selectattr`
- New `alias:` section for adding alternative keys to dictionaries
  - Adds alias keys to all dicts in GLOBAL_VARS recursively
  - Example: `alias: {description: label}` makes `item.description` work when `item.label` exists
  - Does not overwrite existing keys
  - Applied after bind and global processing
- Processing order: preamble → with → query → data load → bind → global → alias → render
  - `with:` variables are available in `query:` and all subsequent stages
  - `bind:` evaluates after data loading, preserving result types
  - `global:` evaluates after `bind:`, can reference data and bind results
  - `alias:` adds alternative keys to all dicts after global processing

## [0.9.2] - 2025-11-28

### Added
- Best Practices section in README.md covering CSV output handling, file extensions, and pipeline patterns
- Real-World Usage Patterns section in AGENTS.md with standalone mode examples and filter/standalone mode distinctions
- CLAUDE.md symlink to AGENTS.md for Claude Code integration

### Improved
- Refactored Makefile dirty check with list variable and function for better maintainability
- Simplified AGENTS.md project structure by removing line counts
- Enhanced SQL injection protection with `_quote_identifier()` for safe table name handling
- Unified TOML loader to use `_read_source()` helper for consistency
- Variable initialization moved before try blocks to avoid locals() checks

## [0.9.1] - 2025-11-27

### Performance
- Optimized debug string formatting with lazy evaluation (reduces overhead when DEBUG=False)
- Replaced O(n*m) nested loop in normalize_config with O(1) dict lookup
- Converted CONTROL_STRUCTURES from string concatenation to list append for better efficiency
- Eliminated redundant file reads in data loaders

### Code Quality
- Extracted duplicate StringIO handling to `_read_source()` helper function
- Consolidated pandas read_kwargs logic into `_build_csv_read_kwargs()` helper
- Added `_has_template_syntax()` helper to reduce code duplication (3 uses)
- Simplified `_split_template_and_newlines()` by removing redundant conditional check

### Improved
- Better maintainability with less code duplication (~30-40 lines reduced)
- More consistent patterns across similar operations
- All optimizations preserve existing functionality (162/162 tests passing)

## [0.9.0] - 2025-11-27

### Added
- Stdin support for reading data from standard input
  - `data: "-"` explicitly reads from stdin
  - Auto-detection in standalone mode when data is not specified and stdin is not a tty
  - Multiple files disable auto-detection to prevent stdin consumption issues
- `-t/--template` option for inline template text (standalone mode)
- `-f/--format` option for explicitly specifying data format (standalone mode)
- `-d/--debug` option for enabling debug output via command line (standalone mode)
- 8 new test cases for stdin handling and empty input (162 total tests)

### Fixed
- Stdin consumption bug when processing multiple template files
  - Auto-detection now disabled for multiple files
  - Prevents first file from consuming stdin, leaving subsequent files empty
- `-t` option behavior: now only reads stdin when `-f` is specified
  - `-t` without `-f` renders template without reading stdin
- Empty JSON/CSV input handling
  - Empty or whitespace-only input now returns empty list `[]` instead of error
  - More robust pipeline handling

### Improved
- Lines format now preserves empty lines as empty strings
- Debug output shows rendered results with repr() for better visibility
- Documentation updated with stdin auto-detection behavior and limitations
- More intuitive and predictable `-t` option behavior

## [0.8.1] - 2025-11-26

### Fixed
- Corrected test structure in `test_use_saved_template` and `test_use_nonexistent_template_fails` to use proper 3-separator format for template usage with inline data
- Fixed README.md documentation: corrected separator count description from "two" to "three" for template usage with inline data
- Added content verification assertions to `test_use_saved_template` to prevent false positives

### Changed
- Replaced Japanese comments with English in `config.py` for better international collaboration
- Removed duplicate dependency definitions from `pyproject.toml` (consolidated to `[dependency-groups]`)
- Removed unnecessary Python 3.7 compatibility code from `main.py` (project requires Python 3.8+)

### Improved
- Updated CODE_ANALYSIS.md with completion status for Phase 1 and Phase 2 improvements
- Enhanced test quality with actual content verification instead of type-only checks

## [0.8.0] - 2025-11-26

### Added
- `template` parameter as preferred alias for `as` in template usage (more declarative in YAML)
- Both `template` and `as` work without warnings (context-dependent usage)
- Parameter aliasing system with preferred external names mapping to internal canonical names
- Backward compatibility tests for deprecated `name` parameter and new `template` alias (150 total tests passing)

### Changed
- Replaced `name` parameter with `define` for template definitions (more intuitive: define vs. use)
- Documentation now recommends `template:` in YAML examples and `as=` in attribute examples
- `name` parameter remains supported for backward compatibility with deprecation warnings
- Added `normalize_config()` function for parameter alias resolution
- Error messages now refer to `define=` instead of deprecated `name=`

## [0.7.3] - 2025-11-25

### Fixed
- Include missing sqlite-utils implementation code from v0.7.2 release
- v0.7.2 release commit inadvertently omitted data_loader.py changes

### Improved
- Makefile release process now follows Minilla-style approach
- Automatic version number updates from CHANGELOG (single source of truth)
- Added dirty check to prevent releases with uncommitted changes
- Use `git add -u` to include all tracked changes, preventing file omissions
- Automatic uv.lock update during release process

## [0.7.2] - 2025-11-25

### Added
- Optional sqlite-utils integration for improved SQLite database handling
- New `[sqlite]` optional dependency group for enhanced SQLite features

### Changed
- SQLite loader now uses sqlite-utils when available, falling back to standard sqlite3
- Improved SQLite query execution with cleaner API when sqlite-utils is installed

### Improved
- More efficient SQLite table row retrieval using sqlite-utils' optimized methods
- Better code maintainability in data_loader.py with optional dependency pattern

## [0.7.1] - 2025-11-25

### Fixed
- Update uv.lock to reflect v0.7.0 version (was accidentally omitted from release commit)
- Eliminate uv deprecation warning by migrating to PEP 735 dependency-groups format
- Improve Makefile release process to prevent similar issues in future releases

### Changed
- Replace `[tool.uv]` dev-dependencies with standard `[dependency-groups]` dev
- Remove `.python-version` from repository (developers can use their preferred Python 3.8+ version)
- Add `.python-version` to `.gitignore` for local development flexibility

### Improved
- Makefile now automatically includes uv.lock in release commits
- Makefile preserves markdown headings in git tag annotations (--cleanup=whitespace)
- Simplified release workflow by removing overly restrictive dirty check

## [0.7.0] - 2025-11-25

### Added
- Python 3.13 support with comprehensive testing across all platforms
- `.python-version` file for consistent Python version management (3.12)
- `[tool.uv]` section in `pyproject.toml` for uv-specific dev dependencies
- Development setup instructions in README Contributing section for both uv and pip workflows

### Changed
- Updated GitHub Actions workflows to use Python 3.12 (from 3.10) for builds and releases
- Enabled caching in publish.yml for faster CI builds
- Expanded test matrix to include Python 3.13 (now testing 3.8-3.13 across Ubuntu, macOS, Windows)
- Updated Codecov upload condition to use Python 3.12

### Improved
- Better onboarding experience for new contributors with detailed development environment setup
- Faster CI/CD execution with optimized caching strategy

## [0.6.0] - 2025-11-22

### Added
- `pandoc_embedz.main` entry point now powers the `pandoc-embedz` console script, providing a dedicated CLI surface plus the new `--standalone`/`-s` flag for rendering Markdown outside of Pandoc.

### Changed
- Standalone execution and helper logic moved out of `filter.py`, keeping the filter narrowly focused while `main.py` owns argument parsing, help/version output, and renderer orchestration.
- Template newline handling was streamlined so Jinja output preserves intentional trailing newlines consistently across filter and standalone execution, with updated tests to lock in behavior.
- Documentation now covers assistant/model tagging expectations together with the refreshed standalone CLI examples.

### Removed
- Deprecated release helper scripts and a stray `log.failed` artifact were dropped from the repository.

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

[0.16.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.15.0...v0.16.0
[0.15.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.13.1...v0.14.0
[0.13.1]: https://github.com/tecolicom/pandoc-embedz/compare/v0.13.0...v0.13.1
[0.13.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.10.2...v0.11.0
[0.10.2]: https://github.com/tecolicom/pandoc-embedz/compare/v0.10.1...v0.10.2
[0.10.1]: https://github.com/tecolicom/pandoc-embedz/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.9.2...v0.10.0
[0.9.2]: https://github.com/tecolicom/pandoc-embedz/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/tecolicom/pandoc-embedz/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.8.1...v0.9.0
[0.8.1]: https://github.com/tecolicom/pandoc-embedz/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.7.3...v0.8.0
[0.7.3]: https://github.com/tecolicom/pandoc-embedz/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/tecolicom/pandoc-embedz/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/tecolicom/pandoc-embedz/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/tecolicom/pandoc-embedz/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/tecolicom/pandoc-embedz/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tecolicom/pandoc-embedz/releases/tag/v0.1.0
