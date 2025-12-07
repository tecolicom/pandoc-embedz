"""CLI entry point for pandoc-embedz."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from importlib.metadata import version

from .config import validate_file_path


def _filter_module():
    """Lazy import to avoid circular dependency at module import time."""
    from . import filter as filter_module
    return filter_module


def _read_template_source(path_spec: str) -> str:
    """Read template contents from a file or stdin ('-')."""
    if path_spec == '-':
        return sys.stdin.read()
    validated_path = validate_file_path(path_spec)
    return Path(validated_path).read_text(encoding='utf-8')


def render_standalone_text(
    text: str,
    attr_overrides: Optional[Dict[str, object]] = None
) -> str:
    """Render template text outside of Pandoc."""
    filter_module = _filter_module()
    template_part = ''
    config: Dict[str, object] = {}
    data_file: Optional[str] = None
    has_header = True
    data_part: Optional[str] = None

    try:
        filter_module._debug("=" * 60)
        filter_module._debug("Processing standalone embedz template")

        # Extract internal flags from attr_overrides (use get, not pop, as dict is reused)
        overrides = attr_overrides or {}
        multiple_files = overrides.get('_multiple_files', False) if isinstance(overrides, dict) else False
        no_stdin_auto = overrides.get('_no_stdin_auto', False) if isinstance(overrides, dict) else False

        config, template_part, data_part = filter_module._build_config_from_text(
            text,
            overrides,
            allow_inline_data=False
        )

        # In standalone mode, if no data source is specified and stdin is available,
        # automatically read from stdin (but not in test environment, when processing multiple files,
        # or when using -t without -f)
        # Note: stdin can only be read once, so auto-detection is disabled for multiple files
        if ('data' not in config and
            not sys.stdin.isatty() and
            not os.getenv('PYTEST_CURRENT_TEST') and
            not multiple_files and
            not no_stdin_auto):
            config['data'] = '-'
            filter_module._debug("No data source specified, reading from stdin")

        result, data_file, has_header = filter_module._execute_embedz_pipeline(
            config, template_part, data_part
        )
        filter_module._debug("Processing complete")
        filter_module._debug("=" * 60)
        return result or ''
    except filter_module.KNOWN_EXCEPTIONS as e:  # type: ignore[attr-defined]
        filter_module.print_error_info(
            e, template_part, config, data_file, has_header, data_part
        )
        raise


def run_standalone(
    files: List[str],
    config_paths: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    enable_debug: bool = False,
    template_text: Optional[str] = None,
    data_format: Optional[str] = None
) -> None:
    """Handle standalone rendering for one or more files."""
    filter_module = _filter_module()

    # Enable debug mode if requested
    if enable_debug:
        filter_module.DEBUG = True

    attr_overrides: Dict[str, object] = {}
    if config_paths:
        if len(config_paths) == 1:
            attr_overrides['config'] = config_paths[0]
        else:
            attr_overrides['config'] = config_paths

    # Add data source and format overrides
    if data_format:
        attr_overrides['format'] = data_format

    # Set internal flag for multiple files to disable stdin auto-detection
    if len(files) > 1:
        attr_overrides['_multiple_files'] = True

    # Set internal flag when using -t without -f to disable stdin auto-detection
    if template_text and not data_format:
        attr_overrides['_no_stdin_auto'] = True

    outputs: List[str] = []
    try:
        if template_text:
            # Use template text from command line
            # Only read from stdin if format is specified
            front_matter_parts = []
            if data_format:
                front_matter_parts.append('data: "-"')
                front_matter_parts.append(f'format: {data_format}')

            # config_paths are handled via attr_overrides
            if front_matter_parts:
                template_content = f"""---
{chr(10).join(front_matter_parts)}
---
{template_text}"""
            else:
                # No data source, just render template as-is
                template_content = template_text

            result = render_standalone_text(template_content, attr_overrides)
            if result:
                outputs.append(result)
        else:
            # Use template files
            for template_path in files:
                text = _read_template_source(template_path)
                result = render_standalone_text(text, attr_overrides)
                if result:
                    outputs.append(result)
    except filter_module.KNOWN_EXCEPTIONS:  # type: ignore[attr-defined]
        sys.exit(1)

    combined = ''.join(outputs)
    if output_path:
        Path(output_path).write_text(combined, encoding='utf-8')
    else:
        sys.stdout.write(combined)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='pandoc-embedz',
        add_help=False
    )
    parser.add_argument('-s', '--standalone', action='store_true')
    parser.add_argument('-c', '--config', action='append', dest='configs')
    parser.add_argument('-o', '--output')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-t', '--template', dest='template_text')
    parser.add_argument('-f', '--format', dest='data_format')
    parser.add_argument('-h', '--help', action='store_true')
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('files', nargs='*')
    return parser


def print_help() -> None:
    """Print help message for CLI usage."""
    help_text = """pandoc-embedz - Pandoc filter for embedding data-driven content

USAGE:
    pandoc input.md --filter pandoc-embedz -o output.pdf

Standalone rendering (Markdown, LaTeX, etc.):
    pandoc-embedz --standalone template.tex --config config/base.yaml -o output.tex

OPTIONS:
    -h, --help            Show this help message
    -v, --version         Show version information
    -s, --standalone      Render one or more template files directly
    -t, --template TEXT   Template text (use instead of template file)
    -f, --format FORMAT   Data format (csv, tsv, json, yaml, lines, etc.)
    -c, --config FILE     External YAML config file (repeatable, applies to standalone mode)
    -o, --output FILE     Write standalone render result to file (default: stdout)
    -d, --debug           Enable debug output

DESCRIPTION:
    A Pandoc filter that embeds data from various formats (CSV, JSON, YAML,
    TOML, SQLite) into Markdown/LaTeX documents using Jinja2 templates. The
    standalone renderer shares the same syntax and configuration pipeline.

    Supports:
    - Multiple data formats with auto-detection
    - SQL queries on CSV/TSV files
    - Template reuse and macros
    - Global and local variables
    - Multi-table operations
    - External config files shared between Pandoc runs and standalone rendering

ENVIRONMENT:
    PANDOC_EMBEDZ_DEBUG    Enable debug output (1, true, or yes)

DOCUMENTATION:
    https://github.com/tecolicom/pandoc-embedz#readme

REPORT BUGS:
    https://github.com/tecolicom/pandoc-embedz/issues
"""
    print(help_text)


def print_version() -> None:
    """Print version information."""
    try:
        pkg_version = version('pandoc-embedz')
    except Exception:  # pragma: no cover
        pkg_version = 'unknown'
    print(f"pandoc-embedz {pkg_version}")


def main() -> None:
    parser = _build_parser()
    argv = sys.argv[1:]
    args, unknown = parser.parse_known_args(argv)

    if args.help:
        print_help()
        sys.exit(0)

    if args.version:
        print_version()
        sys.exit(0)

    if args.standalone:
        # Check for conflicting options
        if args.template_text and args.files:
            sys.stderr.write("pandoc-embedz: cannot specify both -t/--template and template files\n")
            sys.exit(1)

        # If template text is provided, files are optional
        if not args.template_text and not args.files:
            sys.stderr.write("pandoc-embedz: --standalone/-s requires at least one file or --template/-t option\n")
            sys.exit(1)

        run_standalone(
            args.files,
            args.configs,
            args.output,
            enable_debug=args.debug,
            template_text=args.template_text,
            data_format=args.data_format
        )
        return

    # Enable debug mode for filter mode if requested
    if args.debug:
        os.environ['PANDOC_EMBEDZ_DEBUG'] = '1'

    # Defer to Pandoc filter mode
    filter_module = _filter_module()
    filter_module.pf.run_filter(filter_module.process_embedz)


if __name__ == '__main__':  # pragma: no cover
    main()
