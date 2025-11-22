"""Standalone rendering helpers for pandoc-embedz."""

from __future__ import annotations

from typing import Dict, Optional, List
import argparse
import os
from pathlib import Path

from .config import validate_file_path


def _filter_module():
    """Lazy import to avoid circular dependency at module import time."""
    from . import filter as filter_module
    return filter_module


def render_standalone_text(text: str, attr_overrides: Optional[Dict[str, any]] = None) -> str:
    """Render template text outside of Pandoc."""
    template_part = ''
    config: Dict[str, any] = {}
    data_file: Optional[str] = None
    has_header = True
    data_part: Optional[str] = None
    filter_module = _filter_module()

    try:
        filter_module._debug("=" * 60)
        filter_module._debug("Processing standalone embedz template")
        config, template_part, data_part = filter_module._build_config_from_text(
            text,
            attr_overrides or {},
            allow_inline_data=False
        )
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


def _read_template_source(path_spec: str) -> str:
    """Read template contents from a file or stdin ('-')."""
    if path_spec == '-':
        return os.sys.stdin.read()
    validated_path = validate_file_path(path_spec)
    return Path(validated_path).read_text(encoding='utf-8')


def run_standalone(argv: List[str]) -> None:
    """Handle standalone CLI rendering."""
    filter_module = _filter_module()
    parser = argparse.ArgumentParser(
        prog='pandoc-embedz',
        description='Render embedz templates without invoking Pandoc'
    )
    parser.add_argument(
        '-r', '--render',
        metavar='FILE',
        required=True,
        help="Template file to render (use '-' for stdin)"
    )
    parser.add_argument(
        '-c', '--config',
        metavar='CONFIG',
        action='append',
        default=[],
        help='External YAML config file(s) merged before inline settings'
    )
    parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        help='Write rendered output to file (default: stdout)'
    )

    args = parser.parse_args(argv)

    attr_overrides: Dict[str, any] = {}
    if args.config:
        attr_overrides['config'] = args.config if len(args.config) > 1 else args.config[0]

    try:
        text = _read_template_source(args.render)
        result = render_standalone_text(text, attr_overrides)
    except filter_module.KNOWN_EXCEPTIONS:  # type: ignore[attr-defined]
        os.sys.exit(1)

    if args.output:
        Path(args.output).write_text(result, encoding='utf-8')
    else:
        os.sys.stdout.write(result)
